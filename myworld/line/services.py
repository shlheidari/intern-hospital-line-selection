"""Business logic for line selection, kept apart from the HTTP layer.

Data model in short
-------------------
* ``Members``   - one row per student: their time window and saved choices.
* ``Capacity``  - seats per (line, unit, hospital); ``reserved``/``remain`` are
  derived from the members' saved choices.
* ``Shared``    - maps a displayed unit to the unit whose capacity it shares.
* ``Selection`` - the *working* selection of the student whose turn it is
  (row 0: whose turn, row 1: chosen line, then one row per unit).
"""
import logging
import re
import threading
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import close_old_connections, transaction
from django.db.models import F

from .constants import DATETIME_FORMAT, TEHRAN_TZ, UNIT_FIELDS
from .models import Capacity, Members, Selection, Shared

logger = logging.getLogger(__name__)


# --- time helpers --------------------------------------------------------

def tehran_now():
    """Current wall-clock time in Tehran as a naive datetime."""
    return datetime.now(ZoneInfo(TEHRAN_TZ)).replace(tzinfo=None, microsecond=0)


def parse_datetime(value):
    """Parse the ``YYYY-MM-DD HH:MM:SS`` strings stored on Members."""
    return datetime.strptime(str(value)[:19], DATETIME_FORMAT)


def window_is_open(member, now=None):
    """True while ``now`` is inside the member's selection window."""
    now = now or tehran_now()
    try:
        return parse_datetime(member.start_time) < now < parse_datetime(member.end_time)
    except ValueError:
        logger.warning('Member %s has an unparsable time window', member.student_id)
        return False


def run_later(delay_seconds, func, *args):
    """Run ``func`` once after a delay on a daemon thread.

    The timers only live as long as the process, so the app is meant to run as
    a single worker.
    """
    def runner():
        try:
            func(*args)
        except Exception:
            logger.exception('Scheduled task %s failed', getattr(func, '__name__', func))
        finally:
            close_old_connections()

    timer = threading.Timer(max(delay_seconds, 0), runner)
    timer.daemon = True
    timer.start()
    return timer


# --- capacity ------------------------------------------------------------

def build_capacity_rows():
    """Capacity rows as the pages display them.

    Every ``Shared`` entry shows the capacity of the unit it shares with, so
    those rows are copied under the displayed unit name. Only the fields the
    pages use are sent.
    """
    rows_by_unit = defaultdict(list)
    for row in Capacity.objects.order_by('id').values('id', 'line', 'unit', 'hospital', 'full', 'remain'):
        rows_by_unit[row['unit']].append(row)

    rows = []
    for shared in Shared.objects.order_by('id'):
        for row in rows_by_unit.get(shared.shared_unit, []):
            rows.append({**row, 'unit': shared.unit})
    return rows


def line_unit_name(line):
    """'1A' -> '1 A-1A' (the Capacity unit that holds a line's total seats)."""
    match = re.match(r'(\d+)(\D+)', line)
    if not match:
        return None
    return f'{match.group(1)} {match.group(2)}-{line}'


def recompute_capacity(member, *, first_turn):
    """Rebuild ``reserved`` / ``remain`` of every Capacity row from saved choices.

    ``member`` is flagged ``first`` (their turn started) or ``last`` (their turn
    ended) once the numbers are up to date.
    """
    shared_unit_of = {shared.unit: shared.shared_unit for shared in Shared.objects.all()}
    line_counts = Counter()
    unit_counts = Counter()

    for saved in Members.objects.exclude(line__isnull=True).exclude(line=''):
        line_counts[saved.line] += 1
        for field, unit_name in UNIT_FIELDS.items():
            hospital = getattr(saved, field)
            if not hospital:
                continue
            shared_unit = shared_unit_of.get(f'{unit_name}-{saved.line}')
            if shared_unit is None:
                logger.warning('No shared unit for %s-%s', unit_name, saved.line)
                continue
            unit_counts[(shared_unit.split('-')[-1], shared_unit, hospital)] += 1

    with transaction.atomic():
        Capacity.objects.update(reserved=0, remain=F('full'))
        for line, count in line_counts.items():
            unit = line_unit_name(line)
            updated = Capacity.objects.filter(line=line, unit=unit).update(
                reserved=count, remain=F('full') - count)
            if not updated:
                logger.warning('No capacity row for line %s', line)
        for (line, unit, hospital), count in unit_counts.items():
            updated = Capacity.objects.filter(line=line, unit=unit, hospital=hospital).update(
                reserved=count, remain=F('full') - count)
            if not updated:
                logger.warning('No capacity row for %s / %s / %s', line, unit, hospital)

    flag = 'first' if first_turn else 'last'
    setattr(member, flag, True)
    member.save(update_fields=[flag])


def hospital_has_room(department, hospital):
    """Is a seat left in ``hospital`` for ``department`` on the chosen line?"""
    try:
        line = Selection.objects.get(item_en='line').choice
        shared_unit = Shared.objects.get(unit=f'{department}-{line}').shared_unit
        capacity = Capacity.objects.get(
            line=shared_unit.split('-')[-1], unit=shared_unit, hospital=hospital)
    except (Selection.DoesNotExist, Shared.DoesNotExist, Capacity.DoesNotExist,
            Capacity.MultipleObjectsReturned):
        return False
    return int(capacity.remain or 0) > 0


# --- registering a finished selection -------------------------------------

def register_selection(member):
    """Save the working selection onto ``member`` and clear it.

    Only a selection that belongs to ``member`` is stored; the working
    selection is cleared either way so the next student starts clean.
    """
    rows = list(Selection.objects.order_by('id').values('item_en', 'choice'))
    if not rows or rows[0]['choice'] != member.student_id:
        logger.info('Selection does not belong to %s - nothing to save', member.student_id)
        Selection.objects.all().delete()
        return

    changed = []
    if len(rows) > 1:
        member.line = rows[1]['choice']
        changed.append('line')
    for row in rows[2:]:
        if row['item_en'] in UNIT_FIELDS:
            setattr(member, row['item_en'], row['choice'])
            changed.append(row['item_en'])
    if changed:
        member.save(update_fields=changed)
    Selection.objects.all().delete()
    recompute_capacity(member, first_turn=False)
