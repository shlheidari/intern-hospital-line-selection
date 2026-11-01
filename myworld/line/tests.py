"""Tests for the line-selection app.

They run on the SQLite fallback (no PostgreSQL needed):

    SECRET_KEY=test python manage.py test

The auto-logout timer started when a student logs in is patched out so the
tests are fast and deterministic.
"""
import csv
import json
import re
from datetime import datetime
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from . import services, views
from .line_tables import load_line_table
from .models import Capacity, Members, Selection, Shared

PAST_START, PAST_END = '2000-01-01 08:00:00', '2000-01-01 09:00:00'
OPEN_START, OPEN_END = '2000-01-01 00:00:00', '2999-12-31 23:59:59'
PASSWORD = 'pw12345!'
BLANK_UNITS = {f: '' for f in (
    'internal', 'pediatrics', 'gynocology', 'emergency', 'elective_one',
    'elective_two', 'elective_three', 'orthopedix', 'cardiology')}


def make_member(student_id, num=1, start=PAST_START, end=PAST_END, **extra):
    """Create a Members row plus the matching login User."""
    User.objects.create_user(username=student_id, password=PASSWORD)
    return Members.objects.create(
        num=num, name=f'Student {student_id}', student_id=student_id,
        start_time=start, end_time=end, **extra)


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type='application/json')


class PublicPagesTests(TestCase):
    def test_index_page_renders(self):
        self.assertEqual(self.client.get(reverse('index')).status_code, 200)

    def test_member_page_lists_members_without_student_ids(self):
        make_member('9900000001')
        response = self.client.get(reverse('member'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student 9900000001')
        # student ids are the login usernames - they must not leak on the public page
        rows = list(response.context['members'])
        self.assertTrue(rows)
        self.assertNotIn('student_id', rows[0])

    def test_capacity_page_renders_with_data(self):
        Capacity.objects.create(line='1A', unit='1 A-1A', hospital='All', full=6, reserved=0, remain=6)
        Shared.objects.create(unit='1 A-1A', shared_unit='1 A-1A')
        response = self.client.get(reverse('capacity'))
        self.assertEqual(response.status_code, 200)
        capacity = response.context['config']['capacity']
        self.assertEqual([(row['unit'], row['hospital']) for row in capacity], [('1 A-1A', 'All')])

    def test_capacity_page_renders_with_an_empty_database(self):
        response = self.client.get(reverse('capacity'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['config']['capacity'], [])

    def test_capacity_page_sets_the_csrf_cookie_its_script_needs(self):
        response = self.client.get(reverse('capacity'))
        self.assertIn('csrftoken', response.cookies)

    def test_selector_lists_members_with_their_hospital(self):
        Shared.objects.create(unit='جراحی-1A', shared_unit='جراحی-1A')
        make_member('9900000001', line='1A', surgery='Hospital X', **BLANK_UNITS)
        response = post_json(self.client, reverse('selector'), {'unitName': 'جراحی-1A'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['persons'], [{'name': 'Student 9900000001', 'hospital': 'Hospital X'}])

    def test_selector_for_a_line_cell_has_no_hospital(self):
        Shared.objects.create(unit='1 A-1A', shared_unit='1 A-1A')
        make_member('9900000001', line='1A', **BLANK_UNITS)
        data = post_json(self.client, reverse('selector'), {'unitName': '1 A-1A'}).json()
        self.assertEqual(data['persons'], [{'name': 'Student 9900000001', 'hospital': ''}])

    def test_selector_rejects_bad_requests(self):
        self.assertEqual(self.client.get(reverse('selector')).status_code, 405)
        self.assertEqual(post_json(self.client, reverse('selector'), {}).status_code, 400)
        self.assertEqual(
            post_json(self.client, reverse('selector'), {'unitName': 'nope'}).status_code, 404)


class LineTableTests(TestCase):
    def test_tables_have_the_same_shape(self):
        select_table = load_line_table('select')
        capacity_table = load_line_table('capacity')
        self.assertEqual(len(select_table), len(capacity_table))
        for table in (select_table, capacity_table):
            for row in table:
                self.assertEqual(set(row), {'id', 'class', 'cells'})
                self.assertTrue(all(isinstance(cell, dict) for cell in row['cells']))

    def test_cell_ids_are_unique_numbers(self):
        for name in ('select', 'capacity'):
            ids = [cell['id'] for row in load_line_table(name) for cell in row['cells'] if 'id' in cell]
            self.assertEqual(len(ids), len(set(ids)), name)
            self.assertTrue(all(i.isdigit() for i in ids), name)


class SelectLoginTests(TestCase):
    """POST /select/ is the entry point of a student's turn."""

    def post_login(self, username, password):
        return self.client.post(reverse('select'), {'username': username, 'password': password})

    def assert_not_logged_in(self):
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_get_redirects_to_index(self):
        response = self.client.get(reverse('select'))
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)

    def test_wrong_password_is_rejected(self):
        make_member('9900000001', start=OPEN_START, end=OPEN_END)
        response = self.post_login('9900000001', 'wrong')
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        self.assert_not_logged_in()

    def test_login_outside_time_window_is_rejected(self):
        make_member('9900000001', start=PAST_START, end=PAST_END)
        response = self.post_login('9900000001', PASSWORD)
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        self.assert_not_logged_in()

    def test_user_without_a_member_profile_is_rejected(self):
        User.objects.create_user('staff-user', password=PASSWORD)
        response = self.post_login('staff-user', PASSWORD)
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        self.assert_not_logged_in()

    def test_login_inside_time_window_opens_selection_page(self):
        student = make_member('9900000001', start=OPEN_START, end=OPEN_END)
        with patch.object(services, 'run_later') as run_later:
            response = self.post_login('9900000001', PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertIn('_auth_user_id', self.client.session)
        student.refresh_from_db()
        self.assertTrue(student.logged)
        self.assertTrue(student.first)
        run_later.assert_called_once()  # the auto-logout timer

        config = response.context['config']
        self.assertEqual(config['user'], '9900000001')
        self.assertEqual(config['student'], {'startTime': OPEN_START, 'endTime': OPEN_END})
        self.assertEqual(config['lineTable'], load_line_table('select'))
        self.assertEqual(config['saved'], [])
        self.assertEqual(config['unitKeys']['جراحی'], 'surgery')
        self.assertEqual(set(config['urls']),
                         {'selected', 'concurrentLogin', 'validate', 'options', 'finish', 'index'})
        self.assertIn('csrftoken', response.cookies)
        self.assertContains(response, 'id="page-config"')
        self.assertContains(response, 'Student 9900000001')

    def test_page_config_carries_a_selection_in_progress(self):
        make_member('9900000001', start=OPEN_START, end=OPEN_END)
        Selection.objects.create(item_fa='user', item_en='user', choice='9900000001', iden='9900000001', line_c='')
        Selection.objects.create(item_fa='line', item_en='line', choice='1A', iden='1A', line_c='1A')
        with patch.object(services, 'run_later'):
            response = self.post_login('9900000001', PASSWORD)
        self.assertEqual([row['choice'] for row in response.context['config']['saved']], ['9900000001', '1A'])


class TimeWindowTests(TestCase):
    def test_window_is_open_only_between_start_and_end(self):
        student = Members(start_time='2024-05-01 10:00:00', end_time='2024-05-01 11:00:00')
        self.assertFalse(services.window_is_open(student, datetime(2024, 5, 1, 9, 59, 59)))
        self.assertTrue(services.window_is_open(student, datetime(2024, 5, 1, 10, 30)))
        self.assertFalse(services.window_is_open(student, datetime(2024, 5, 1, 11, 0, 1)))

    def test_garbage_times_close_the_window(self):
        self.assertFalse(services.window_is_open(Members(start_time='soon', end_time='later')))


class RegisterTests(TestCase):
    """register_selection() copies a student's finished selection onto their Members row."""

    def make_selection(self, owner='9900000001'):
        # row 0 = whose turn it is, row 1 = chosen line, rest = unit choices
        Selection.objects.create(item_fa='user', item_en='user', choice=owner, iden=owner, line_c='')
        Selection.objects.create(item_fa='line', item_en='line', choice='1A', iden='', line_c='')
        Selection.objects.create(item_fa='جراحی', item_en='surgery', choice='Hospital X', iden='', line_c='')
        Selection.objects.create(item_fa='داخلی', item_en='internal', choice='Hospital Y', iden='', line_c='')

    def test_register_saves_choices_clears_selection_and_updates_capacity(self):
        student = make_member('9900000001')
        Capacity.objects.create(line='1A', unit='1 A-1A', hospital='All', full=6, reserved=0, remain=6)
        self.make_selection()

        services.register_selection(student)

        student.refresh_from_db()
        self.assertEqual(student.line, '1A')
        self.assertEqual(student.surgery, 'Hospital X')
        self.assertEqual(student.internal, 'Hospital Y')
        self.assertTrue(student.last)
        self.assertEqual(Selection.objects.count(), 0)
        capacity = Capacity.objects.get()
        self.assertEqual((capacity.reserved, capacity.remain), (1, 5))

    def test_register_ignores_selection_of_another_student(self):
        student = make_member('9900000001')
        self.make_selection(owner='9900000002')

        services.register_selection(student)

        student.refresh_from_db()
        self.assertFalse(student.line)  # untouched
        self.assertEqual(Selection.objects.count(), 0)  # but the working selection is cleared

    def test_register_with_no_selection_is_a_no_op(self):
        student = make_member('9900000001')
        services.register_selection(student)
        student.refresh_from_db()
        self.assertFalse(student.line)

    def test_manual_logout_registers_and_closes_the_window(self):
        student = make_member('9900000001', start=OPEN_START, end=OPEN_END)
        self.client.login(username='9900000001', password=PASSWORD)
        self.make_selection()

        response = self.client.get(reverse('loggedout_manual'))

        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        student.refresh_from_db()
        self.assertEqual(student.line, '1A')
        self.assertLess(student.end_time, OPEN_END)  # the window was closed early
        self.assertNotIn('_auth_user_id', self.client.session)


class CapacityTests(TestCase):
    def setUp(self):
        Capacity.objects.create(line='1A', unit='1 A-1A', hospital='All', full=6, reserved=0, remain=6)
        Capacity.objects.create(line='1A', unit='جراحی-1A', hospital='Hospital X', full=3, reserved=0, remain=3)
        Shared.objects.create(unit='جراحی-1A', shared_unit='جراحی-1A')

    def test_reserved_and_remain_follow_members_choices(self):
        chooser = make_member('9900000001', num=1, line='1A', surgery='Hospital X', **BLANK_UNITS)
        make_member('9900000002', num=2, line='', surgery='', **BLANK_UNITS)  # has not chosen yet

        services.recompute_capacity(chooser, first_turn=True)

        line_cap = Capacity.objects.get(unit='1 A-1A')
        unit_cap = Capacity.objects.get(unit='جراحی-1A')
        self.assertEqual((line_cap.reserved, line_cap.remain), (1, 5))
        self.assertEqual((unit_cap.reserved, unit_cap.remain), (1, 2))
        chooser.refresh_from_db()
        self.assertTrue(chooser.first)
        self.assertFalse(chooser.last)

    def test_recompute_discards_stale_numbers(self):
        Capacity.objects.filter(unit='جراحی-1A').update(reserved=3, remain=0)
        nobody = make_member('9900000001', line='', **BLANK_UNITS)

        services.recompute_capacity(nobody, first_turn=True)

        unit_cap = Capacity.objects.get(unit='جراحی-1A')
        self.assertEqual((unit_cap.reserved, unit_cap.remain), (0, 3))

    def test_recompute_survives_a_choice_without_capacity_row(self):
        chooser = make_member('9900000001', line='1A', surgery='Unknown Hospital', **BLANK_UNITS)
        services.recompute_capacity(chooser, first_turn=True)  # must not raise
        self.assertEqual(Capacity.objects.get(unit='جراحی-1A').reserved, 0)

    def test_capacity_rows_are_shown_under_the_displayed_unit(self):
        Shared.objects.create(unit='داخلی-1A', shared_unit='جراحی-1A')  # shares surgery's seats
        rows = services.build_capacity_rows()
        displayed = sorted((row['unit'], row['hospital']) for row in rows)
        self.assertEqual(displayed, [('جراحی-1A', 'Hospital X'), ('داخلی-1A', 'Hospital X')])

    def test_line_unit_name(self):
        self.assertEqual(services.line_unit_name('1A'), '1 A-1A')
        self.assertEqual(services.line_unit_name('12B'), '12 B-12B')
        self.assertIsNone(services.line_unit_name('x'))


class SelectionApiTests(TestCase):
    """The JSON API the selection page uses while a student's window is open."""

    URL = None

    def setUp(self):
        self.url = reverse('selected')
        Capacity.objects.create(line='1A', unit='1 A-1A', hospital='All', full=2, reserved=0, remain=2)
        Capacity.objects.create(line='1A', unit='جراحی-1A', hospital='Hospital X', full=1, reserved=0, remain=1)
        Capacity.objects.create(line='1A', unit='جراحی-1A', hospital='Hospital Full', full=1, reserved=1, remain=0)
        Shared.objects.create(unit='جراحی-1A', shared_unit='جراحی-1A')

    def login_open_student(self):
        make_member('9900000001', start=OPEN_START, end=OPEN_END)
        self.client.login(username='9900000001', password=PASSWORD)

    def choose_line(self, line='1A'):
        return post_json(self.client, self.url, {'final': [{'line': line}]})

    def choose_surgery(self, hospital, previous=''):
        item = {'a': 'جراحی', 'b': hospital, 'c': previous, 'd': 'surgery', 'i': 'surgery', 'line_c': '1A'}
        return post_json(self.client, self.url, {'sel': [item]})

    def test_full_selection_flow(self):
        self.login_open_student()

        self.assertEqual(self.choose_line().status_code, 200)
        self.assertEqual(list(Selection.objects.order_by('id').values_list('item_en', 'choice')),
                         [('user', '9900000001'), ('line', '1A')])

        self.assertEqual(self.choose_surgery('Hospital X').status_code, 200)
        self.assertEqual(Selection.objects.get(item_fa='جراحی').choice, 'Hospital X')

        self.assertEqual(self.choose_surgery('Hospital Full', previous='Hospital X').status_code, 404)
        self.assertEqual(Selection.objects.get(item_fa='جراحی').choice, 'Hospital X')

        self.assertEqual(self.choose_surgery('', previous='Hospital X').status_code, 200)
        self.assertFalse(Selection.objects.filter(item_fa='جراحی').exists())

    def test_a_full_hospital_cannot_be_chosen(self):
        self.login_open_student()
        self.choose_line()
        self.assertEqual(self.choose_surgery('Hospital Full').status_code, 404)
        self.assertFalse(Selection.objects.filter(item_fa='جراحی').exists())

    def test_a_full_line_cannot_be_chosen(self):
        Capacity.objects.filter(unit='1 A-1A').update(remain=0)
        self.login_open_student()
        self.assertEqual(self.choose_line().status_code, 404)

    def test_choosing_no_line_just_clears_the_selection(self):
        self.login_open_student()
        self.choose_line()
        self.assertEqual(self.choose_line('N').status_code, 200)
        self.assertEqual(Selection.objects.count(), 0)

    def test_anonymous_visitors_cannot_wipe_the_working_selection(self):
        Selection.objects.create(item_fa='user', item_en='user', choice='9900000001', iden='9900000001', line_c='')
        session = self.client.session
        session['anything'] = 1
        session.save()
        self.client.cookies['sessionid'] = session.session_key

        response = self.choose_line('N')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Selection.objects.count(), 1)

    def test_students_outside_their_window_cannot_touch_the_selection(self):
        Selection.objects.create(item_fa='user', item_en='user', choice='9900000002', iden='9900000002', line_c='')
        make_member('9900000001', start=PAST_START, end=PAST_END)
        self.client.login(username='9900000001', password=PASSWORD)

        response = self.choose_line('N')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Selection.objects.count(), 1)

    def test_another_students_turn_clears_the_working_selection(self):
        self.login_open_student()
        Selection.objects.create(item_fa='user', item_en='user', choice='9900000002', iden='9900000002', line_c='')
        self.assertEqual(self.choose_surgery('Hospital X').status_code, 404)
        self.assertEqual(Selection.objects.count(), 0)

    def test_malformed_bodies_are_bad_requests(self):
        self.login_open_student()
        for payload in ({}, {'sel': []}, {'sel': [{}]}, {'unknown': [{}]}, []):
            with self.subTest(payload=payload):
                self.assertEqual(post_json(self.client, self.url, payload).status_code, 400)
        response = self.client.post(self.url, data='not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_unknown_actions_are_bad_requests(self):
        self.login_open_student()
        self.assertEqual(post_json(self.client, self.url, {'sessionkey': [{}]}).status_code, 400)

    def test_get_is_not_allowed(self):
        self.login_open_student()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_selected_without_a_session_is_rejected(self):
        self.assertEqual(self.choose_line().status_code, 404)

    def test_validate_selections_requires_login(self):
        self.assertEqual(self.client.get(reverse('validate_selections')).status_code, 401)

    def test_get_selected_options_requires_login(self):
        self.assertEqual(self.client.get(reverse('get_selected_options')).status_code, 401)

    def test_validate_selections_reports_missing_units(self):
        self.login_open_student()
        data = self.client.get(reverse('validate_selections')).json()
        self.assertFalse(data['valid'])
        self.assertIn('جراحی', data['message'])

    def test_validate_selections_accepts_a_complete_selection(self):
        self.login_open_student()
        for unit in views.REQUIRED_UNITS:
            Selection.objects.create(item_fa=unit, item_en=unit, choice='H', iden='', line_c='')
        self.assertTrue(self.client.get(reverse('validate_selections')).json()['valid'])

    def test_get_selected_options_hides_internal_rows(self):
        self.login_open_student()
        Selection.objects.create(item_fa='user', item_en='user', choice='9900000001', iden='x', line_c='')
        Selection.objects.create(item_fa='جراحی', item_en='surgery', choice='Hospital X', iden='', line_c='')
        options = self.client.get(reverse('get_selected_options')).json()['options']
        self.assertIn('جراحی: Hospital X', options)
        self.assertNotIn('user', options)

    def test_concurrent_login_check_for_anonymous_user(self):
        self.assertEqual(self.client.get(reverse('concurrentlogincheck')).status_code, 404)


class AdminOnlyEndpointsTests(TestCase):
    PROTECTED = ('userdata', 'get_real_time_data', 'get_selection_data', 'realtime_data_page')

    def login_boss(self):
        User.objects.create_superuser('boss', password=PASSWORD)
        self.client.login(username='boss', password=PASSWORD)

    def update_cell(self, **change):
        return post_json(self.client, reverse('update_real_time_data'), change)

    def test_anonymous_and_regular_users_are_redirected(self):
        User.objects.create_user('student', password=PASSWORD)
        for name in self.PROTECTED + ('update_real_time_data',):
            with self.subTest(name=name, user='anonymous'):
                self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        self.client.login(username='student', password=PASSWORD)
        for name in self.PROTECTED + ('update_real_time_data',):
            with self.subTest(name=name, user='student'):
                self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_import_template_is_for_staff_only(self):
        url = reverse('admin_download_template')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.login_boss()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('ImportTemplate.xlsx', response['Content-Disposition'])

    def test_superuser_can_open_realtime_page(self):
        self.login_boss()
        response = self.client.get(reverse('realtime_data_page'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['config']['urls']), {'members', 'selection', 'update'})

    def test_live_data_lists_the_model_columns_and_rows(self):
        member = make_member('9900000001', line='1A')
        Selection.objects.create(item_fa='جراحی', item_en='surgery', choice='X', iden='1', line_c='')
        self.login_boss()

        members = self.client.get(reverse('get_real_time_data')).json()
        self.assertEqual(members['columns'][:3], ['id', 'num', 'name'])
        self.assertIn('elective_one', members['columns'])
        self.assertNotIn('urology_one', members['columns'])  # a column of the old model
        self.assertEqual(members['rows'][0]['id'], member.id)
        self.assertEqual(members['rows'][0]['line'], '1A')

        selection = self.client.get(reverse('get_selection_data')).json()
        self.assertEqual(selection['columns'], ['id', 'item_fa', 'item_en', 'choice', 'iden', 'line_c'])
        self.assertEqual(selection['rows'][0]['choice'], 'X')

    def test_superuser_can_edit_a_cell(self):
        member = make_member('9900000001')
        selection = Selection.objects.create(item_fa='a', item_en='a', choice='x', iden='1', line_c='')
        self.login_boss()

        response = self.update_cell(table='members', id=member.id, column='name', value='Renamed')
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.name, 'Renamed')

        self.update_cell(table='selection', id=selection.id, column='choice', value='y')
        selection.refresh_from_db()
        self.assertEqual(selection.choice, 'y')

    def test_cell_edit_rejects_bad_requests(self):
        member = make_member('9900000001')
        self.login_boss()
        good = dict(table='members', id=member.id, column='name', value='x')
        cases = [
            ({**good, 'column': 'id'}, 400),               # the primary key is not editable
            ({**good, 'column': '__class__'}, 400),
            ({**good, 'column': 'nope'}, 400),
            ({**good, 'table': 'auth_user'}, 400),         # only the live tables
            ({**good, 'id': 9999}, 404),
            ({**good, 'id': 'abc'}, 400),
            ({**good, 'column': 'num', 'value': 'not a number'}, 400),
            ({'table': 'members'}, 400),
        ]
        for change, expected in cases:
            with self.subTest(change=change):
                self.assertEqual(self.update_cell(**change).status_code, expected)
        self.assertEqual(self.client.get(reverse('update_real_time_data')).status_code, 405)
        member.refresh_from_db()
        self.assertEqual(member.name, 'Student 9900000001')

    def test_userdata_bulk_creates_users_from_sample_csv(self):
        self.login_boss()

        response = self.client.get(reverse('userdata'))

        self.assertEqual(response.status_code, 200)
        csv_path = views.settings.BASE_DIR / 'line' / 'data' / 'sample_users.csv'
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = [r for r in csv.reader(f) if r]
        self.assertGreater(len(rows), 1)
        self.assertEqual(response.json(), {'created': len(rows), 'skipped': 0})
        self.assertEqual(User.objects.exclude(username='boss').count(), len(rows))
        username, password = rows[0]
        user = User.objects.get(username=username)
        self.assertNotEqual(user.password, password)  # stored hashed
        self.assertTrue(user.check_password(password))

    def test_userdata_can_be_run_twice(self):
        self.login_boss()
        first = self.client.get(reverse('userdata')).json()
        second = self.client.get(reverse('userdata')).json()
        self.assertEqual(second, {'created': 0, 'skipped': first['created']})


class LoadCapacityCommandTests(TestCase):
    """`manage.py load_capacity` seeds Capacity and Shared from the spreadsheets."""

    def run_command(self, *args):
        out = StringIO()
        call_command('load_capacity', *args, stdout=out)
        return out.getvalue()

    def test_loads_the_bundled_spreadsheets(self):
        output = self.run_command()
        self.assertEqual(Capacity.objects.count(), 1335)
        self.assertEqual(Shared.objects.count(), 576)
        self.assertIn('1335 capacity rows', output)
        row = Capacity.objects.get(unit='1 A-1A')
        self.assertEqual((row.line, row.hospital, row.reserved), ('1A', 'All', 0))
        self.assertEqual(row.remain, row.full)

    def test_refuses_to_overwrite_existing_data(self):
        Shared.objects.create(unit='x', shared_unit='x')
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertEqual(Shared.objects.count(), 1)

    def test_replace_overwrites_existing_data(self):
        Shared.objects.create(unit='x', shared_unit='x')
        self.run_command('--replace')
        self.assertFalse(Shared.objects.filter(unit='x').exists())
        self.assertEqual(Shared.objects.count(), 576)

    def test_loaded_data_drives_the_capacity_page(self):
        self.run_command()
        rows = self.client.get(reverse('capacity')).context['config']['capacity']
        self.assertGreater(len(rows), 1000)


class StaticAssetsTests(TestCase):
    """The pages load built CSS/JS from static files - they must all exist."""

    def referenced_assets(self, response):
        html = response.content.decode()
        return re.findall(r'(?:src|href)="/static/([^"]+)"', html)

    def test_every_asset_a_page_references_exists(self):
        make_member('9900000001', start=OPEN_START, end=OPEN_END)
        User.objects.create_superuser('boss', password=PASSWORD)
        pages = [self.client.get(reverse(name)) for name in ('index', 'member', 'capacity')]
        with patch.object(services, 'run_later'):
            pages.append(self.client.post(reverse('select'), {'username': '9900000001', 'password': PASSWORD}))
        self.client.login(username='boss', password=PASSWORD)
        pages.append(self.client.get(reverse('realtime_data_page')))
        pages.append(self.client.get(reverse('pas')))  # redirects; the password page needs a login
        self.client.login(username='9900000001', password=PASSWORD)
        pages.append(self.client.get('/pas/change_password/'))

        checked = set()
        for response in pages:
            if response.status_code != 200:
                continue
            for asset in self.referenced_assets(response):
                with self.subTest(asset=asset):
                    self.assertIsNotNone(finders.find(asset), asset)
                checked.add(asset)
        self.assertTrue({'line/js/select.js', 'line/js/capacity.js', 'line/js/members.js',
                         'line/js/index.js', 'line/js/realtime.js', 'line/js/password.js'} <= checked)

    def test_pages_do_not_depend_on_a_cdn(self):
        make_member('9900000001', start=OPEN_START, end=OPEN_END)
        with patch.object(services, 'run_later'):
            pages = [self.client.get(reverse(name)) for name in ('index', 'member', 'capacity')]
            pages.append(self.client.post(reverse('select'), {'username': '9900000001', 'password': PASSWORD}))
        for response in pages:
            self.assertEqual(response.status_code, 200)
            self.assertNotRegex(response.content.decode(), r'(?:src|href)="https?://')


class SeedDemoCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command('seed_demo', *args, stdout=out)
        return out.getvalue()

    def test_refuses_to_run_with_debug_off(self):
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=True)
    def test_creates_an_admin_and_students_with_sequential_windows(self):
        output = self.run_command('--students', '3', '--minutes', '30')

        self.assertTrue(User.objects.get(username='admin').is_superuser)
        students = list(Members.objects.order_by('num'))
        self.assertEqual([m.student_id for m in students], ['9900000' + n for n in ('01', '02', '03')])
        self.assertTrue(services.window_is_open(students[0]))
        self.assertFalse(services.window_is_open(students[1]))
        # windows follow each other without overlapping
        self.assertEqual(students[0].end_time, students[1].start_time)
        self.assertEqual(Capacity.objects.count(), 1335)  # seat tables were loaded
        self.assertIn('Demo data ready', output)

    @override_settings(DEBUG=True)
    def test_first_student_can_log_in_and_it_can_be_repeated(self):
        self.run_command()
        self.run_command()  # idempotent
        self.assertEqual(Members.objects.count(), 5)
        with patch.object(services, 'run_later'):
            response = self.client.post(reverse('select'),
                                        {'username': '990000001', 'password': 'demo-pass-123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Demo Student 1')
