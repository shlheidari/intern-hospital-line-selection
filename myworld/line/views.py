"""HTTP layer of the line-selection app.

The selection rules (capacity maths, registering a finished selection, time
windows) live in :mod:`line.services`.
"""
import csv
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import ValidationError
from django.core import serializers
from django.db import transaction
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from . import services
from .constants import (DATETIME_FORMAT, FIELD_BY_UNIT, PASSWORD_SESSION_SECONDS,
                        REQUIRED_UNITS, SESSION_CONFLICT_MESSAGE)
from .forms import FarsiPasswordChangeForm
from .line_tables import load_line_table
from .models import Capacity, Members, Selection, Shared

logger = logging.getLogger(__name__)

superuser_required = user_passes_test(lambda user: user.is_superuser)


def redirect_to_index():
    return HttpResponseRedirect(reverse('index'))


def ok_response():
    return JsonResponse({'status': 'OK'}, status=200)


def not_found_response():
    return JsonResponse({'error': 'not found'}, status=404)


def bad_request_response():
    return JsonResponse({'error': 'bad request'}, status=400)


def session_conflict_response():
    return JsonResponse({'error': 'not found', 'message': SESSION_CONFLICT_MESSAGE}, status=404)


# --- public pages ----------------------------------------------------------

def index(request):
    return render(request, 'line/index.html')


def member(request):
    """Public list of members (without their student ids, which are logins)."""
    fields = [f.name for f in Members._meta.fields if f.name != 'student_id']
    members = Members.objects.values(*fields).order_by('num')
    return render(request, 'line/member.html', {'members': members})


@ensure_csrf_cookie
def capacity(request):
    config = {
        'lineTable': load_line_table('capacity'),
        'capacity': services.build_capacity_rows(),
        'urls': {'selector': reverse('selector'), 'index': reverse('index')},
    }
    return render(request, 'line/capacity.html', {'config': config})


@require_POST
def selector(request):
    """Who picked what for a cell of the capacity board (called by the page)."""
    try:
        unit_name = json.loads(request.body)['unitName']
    except (ValueError, KeyError, TypeError):
        return bad_request_response()

    try:
        shared_unit = Shared.objects.get(unit=unit_name).shared_unit
    except Shared.DoesNotExist:
        return not_found_response()

    persons = []
    for entry in Shared.objects.filter(shared_unit=shared_unit):
        line = entry.unit.split('-')[-1]
        field = FIELD_BY_UNIT.get(entry.unit.replace('-' + line, ''))
        if field is None:
            # A line-level cell (e.g. "1 A-1A"): members on the line, no hospital.
            line = shared_unit.split('-')[-1]
            persons = [{'name': m.name, 'hospital': ''} for m in Members.objects.filter(line=line)]
            break
        persons.extend({'name': m.name, 'hospital': getattr(m, field)}
                       for m in Members.objects.filter(line=line))

    return JsonResponse({'status': 'OK', 'count': len(persons), 'persons': persons})


# --- a student's turn ------------------------------------------------------

@ensure_csrf_cookie
def select(request):
    """Log a student in (inside their window) and open the selection page."""
    if request.method != 'POST':
        messages.info(request, 'ابتدا وارد سایت شوید')
        return redirect_to_index()

    user = authenticate(request,
                        username=request.POST.get('username', ''),
                        password=request.POST.get('password', ''))
    if user is None:
        messages.error(request, 'نام کاربری یا رمز عبور اشتباه است')
        return redirect_to_index()

    try:
        student = Members.objects.get(student_id=user.get_username())
    except Members.DoesNotExist:
        messages.error(request, 'شما امکان ورود ندارید')
        return redirect_to_index()
    if not services.window_is_open(student):
        messages.error(request, 'شما امکان ورود ندارید')
        return redirect_to_index()

    login(request, user)
    services.recompute_capacity(student, first_turn=True)
    student.logged = True
    student.save(update_fields=['logged'])

    # When the window closes, store the selection and log the student out.
    end_time = services.parse_datetime(student.end_time)
    delay = (end_time - services.tehran_now()).total_seconds()
    services.run_later(delay, _finish_turn, request, student)

    return render(request, 'line/select.html',
                  {'me': student, 'config': _selection_page_config(user, student)})


def _selection_page_config(user, student):
    """Everything the selection page script needs (rendered with json_script)."""
    return {
        'user': user.get_username(),
        'student': {'startTime': student.start_time, 'endTime': student.end_time},
        'lineTable': load_line_table('select'),
        'capacity': services.build_capacity_rows(),
        # a selection in progress, restored when the student reloads the page
        'saved': list(Selection.objects.order_by('id')
                      .values('item_fa', 'item_en', 'choice', 'iden', 'line_c')),
        'unitKeys': FIELD_BY_UNIT,
        'urls': {
            'selected': reverse('selected'),
            'concurrentLogin': reverse('concurrentlogincheck'),
            'validate': reverse('validate_selections'),
            'options': reverse('get_selected_options'),
            'finish': reverse('loggedout_manual'),
            'index': reverse('index'),
        },
    }


def _finish_turn(request, student):
    services.register_selection(student)
    logout(request)


def loggedout_manual(request):
    """The student ended their turn early."""
    try:
        student = Members.objects.get(student_id=request.user.get_username())
    except Members.DoesNotExist:
        messages.error(request, 'مشکلی در ثبت انتخاب های شما رخ داد')
        return redirect_to_index()

    services.register_selection(student)
    student.end_time = services.tehran_now().strftime(DATETIME_FORMAT)
    student.save(update_fields=['end_time'])
    logout(request)
    messages.success(request, 'انتخاب های شما با موفقیت ثبت شد')
    return redirect_to_index()


def selected(request):
    """JSON API the selection page calls on every change.

    Body ``{"sel": [{...}]}``  sets, changes or clears the hospital of one unit.
    Body ``{"final": [{"line": ...}]}`` restarts the selection with a new line
    (``"N"`` means no line).
    """
    # Only the student whose window is open may touch the working selection.
    if request.session.session_key is None or not request.user.is_authenticated:
        return session_conflict_response()
    if request.method != 'POST':
        return not_found_response()

    try:
        body = json.loads(request.body)
        action = next(iter(body))
        payload = body[action][0]
    except (ValueError, TypeError, KeyError, IndexError, StopIteration):
        return bad_request_response()

    try:
        student = Members.objects.get(student_id=request.user.get_username())
    except Members.DoesNotExist:
        return not_found_response()
    if not services.window_is_open(student):
        return session_conflict_response()

    try:
        if action == 'sel':
            return _change_unit_choice(request, payload)
        if action == 'final':
            return _choose_line(request, payload)
    except KeyError:
        return bad_request_response()
    return bad_request_response()


def _change_unit_choice(request, item):
    """Handle ``sel``: ``a`` unit (fa), ``b`` new hospital, ``c`` previous hospital,
    ``d`` unit (en), ``i`` id, ``line_c`` line."""
    unit, hospital, previous = item['a'], item['b'], item['c']

    turn_holder = Selection.objects.filter(item_en='user').first()
    if turn_holder is None or turn_holder.iden != request.user.username:
        Selection.objects.all().delete()
        return not_found_response()

    if previous == '':                     # a first choice for this unit
        if hospital == '':
            return ok_response()
        if not services.hospital_has_room(unit, hospital):
            return not_found_response()
        Selection.objects.create(item_fa=unit, item_en=item['d'], choice=hospital,
                                 iden=item['i'], line_c=item['line_c'])
        return ok_response()

    if hospital == '':                       # the choice was cleared
        deleted, _ = Selection.objects.filter(item_fa=unit).delete()
        return ok_response() if deleted else not_found_response()

    if not services.hospital_has_room(unit, hospital):   # the choice was changed
        return not_found_response()
    with transaction.atomic():
        try:
            row = Selection.objects.select_for_update().get(item_fa=unit)
        except Selection.DoesNotExist:
            return not_found_response()
        row.choice = hospital
        row.save(update_fields=['choice'])
    return ok_response()


def _choose_line(request, item):
    """Handle ``final``: start over with the given line."""
    Selection.objects.all().delete()
    line = item['line']
    if line == 'N':
        return ok_response()

    try:
        line_capacity = Capacity.objects.get(line=line, hospital='All')
    except (Capacity.DoesNotExist, Capacity.MultipleObjectsReturned):
        return not_found_response()
    if int(line_capacity.remain) <= 0:
        return not_found_response()

    username = request.user.get_username()
    with transaction.atomic():
        Selection.objects.create(item_fa='user', item_en='user', choice=username,
                                 iden=username, line_c=username)
        Selection.objects.create(item_fa='line', item_en='line', choice=line,
                                 iden=line, line_c=line)
    return ok_response()


def concurrentlogincheck(request):
    """Polled by the selection page: is this still the account's only session?"""
    visitor = getattr(request.user, 'visitor', None)
    if visitor is not None and visitor.session_key == request.session.session_key:
        return ok_response()
    return session_conflict_response()


def validate_selections(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    chosen = set(Selection.objects.values_list('item_fa', flat=True))
    missing = [unit for unit in REQUIRED_UNITS if unit not in chosen]
    if missing:
        message = 'موارد الزامی زیر انتخاب نشده اند: ' + ', '.join(missing)
    else:
        message = 'تمام موارد الزامی انتخاب شده اند.'
    return JsonResponse({'valid': not missing, 'message': message})


def get_selected_options(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    rows = Selection.objects.exclude(item_fa__in=['user', 'line'])
    options = [f"{row.item_fa}: {row.choice or 'هیچ کدام'}" for row in rows]
    return JsonResponse({'options': '\n'.join(options)})


# --- password change --------------------------------------------------------

def pas(request):
    """Log in only to change the password (no selection window needed)."""
    if request.method != 'POST':
        messages.info(request, 'ابتدا وارد سایت شوید')
        return redirect_to_index()

    user = authenticate(request,
                        username=request.POST.get('username', ''),
                        password=request.POST.get('password', ''))
    if user is None:
        messages.error(request, 'نام کاربری یا رمز عبور اشتباه است')
        return redirect_to_index()

    login(request, user)
    services.run_later(PASSWORD_SESSION_SECONDS, logout, request)
    return HttpResponseRedirect('change_password/')


class PasswordsChangeView(PasswordChangeView):
    form_class = FarsiPasswordChangeForm
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        form.save()
        self.request.session.flush()
        logout(self.request)
        return super().form_valid(form)


# --- admin utilities --------------------------------------------------------

@staff_member_required
def download_template(request):
    path = settings.BASE_DIR / 'line' / 'static' / 'xlsx' / 'ImportTemplate.xlsx'
    return FileResponse(open(path, 'rb'), as_attachment=True, filename='ImportTemplate.xlsx')


@superuser_required
def userdata(request):
    """Create login users from ``data/sample_users.csv`` (``username,password``)."""
    csv_path = settings.BASE_DIR / 'line' / 'data' / 'sample_users.csv'
    credentials = []
    with open(csv_path, newline='', encoding='utf-8') as csv_file:
        for row in csv.reader(csv_file):
            if len(row) < 2 or not row[0]:
                break
            credentials.append((row[0], row[1]))

    existing = set(User.objects.filter(username__in=[u for u, _ in credentials])
                   .values_list('username', flat=True))
    new_users = []
    for username, password in credentials:
        if username in existing:
            continue
        user = User(username=username)
        user.set_password(password)
        new_users.append(user)
    User.objects.bulk_create(new_users)
    return JsonResponse({'created': len(new_users), 'skipped': len(existing)})


@superuser_required
def realtime_data_page(request):
    return render(request, 'line/realtime_data.html', {
        'config': {'urls': {
            'members': reverse('get_real_time_data'),
            'selection': reverse('get_selection_data'),
            'update': reverse('update_real_time_data'),
        }},
    })


# Tables shown (and editable) on the live data page, keyed by the name the page uses.
LIVE_TABLES = {'members': Members, 'selection': Selection}


def _table_payload(model):
    columns = [field.name for field in model._meta.fields]
    return {'columns': columns, 'rows': list(model.objects.order_by('id').values(*columns))}


@superuser_required
def get_real_time_data(request):
    return JsonResponse(_table_payload(Members))


@superuser_required
def get_selection_data(request):
    return JsonResponse(_table_payload(Selection))


@superuser_required
def update_real_time_data(request):
    """Edit one cell of a live data table: ``{table, id, column, value}`` (superusers only)."""
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method'}, status=405)

    try:
        change = json.loads(request.body)
        model = LIVE_TABLES[change['table']]
        column, row_id, value = change['column'], int(change['id']), change['value']
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'message': 'Bad request'}, status=400)

    if column not in {f.name for f in model._meta.fields if not f.primary_key}:
        return JsonResponse({'message': f'Unknown column: {column}'}, status=400)
    try:
        row = model.objects.get(pk=row_id)
        value = model._meta.get_field(column).to_python(value)  # validates before touching the DB
    except model.DoesNotExist:
        return JsonResponse({'message': 'Row not found'}, status=404)
    except ValidationError:
        return JsonResponse({'message': f'Invalid value for {column}'}, status=400)

    setattr(row, column, value)
    row.save(update_fields=[column])
    return JsonResponse({'message': 'Data updated successfully'})
