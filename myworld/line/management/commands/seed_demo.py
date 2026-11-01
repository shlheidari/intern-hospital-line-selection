"""Create demo data so the app can be tried right away (development only).

    python manage.py seed_demo

* loads the seat tables if they are empty (see ``load_capacity``)
* creates a superuser ``admin`` and a few students with sequential selection
  windows - the first student can log in now
* prints the logins

Students pick one after another (the app keeps a single working selection), so
the windows do not overlap. Run it again to open the first window anew.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from line import services
from line.constants import DATETIME_FORMAT, UNIT_FIELDS
from line.models import Capacity, Members, Selection

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin-demo-pass'
STUDENT_PASSWORD = 'demo-pass-123'
STUDENT_PREFIX = '9900000'  # obviously fake student ids: 990000001, 990000002, ...


class Command(BaseCommand):
    help = 'Create demo students, an admin and the seat tables (DEBUG only).'

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=5, help='how many students (default 5)')
        parser.add_argument('--minutes', type=int, default=30,
                            help='length of each selection window (default 30)')

    def handle(self, *args, students, minutes, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo creates accounts with well-known passwords; '
                               'it only runs with DEBUG=True.')
        if not Capacity.objects.exists():
            call_command('load_capacity', stdout=self.stdout)

        User.objects.update_or_create(
            username=ADMIN_USERNAME,
            defaults={'is_staff': True, 'is_superuser': True},
        )
        admin = User.objects.get(username=ADMIN_USERNAME)
        admin.set_password(ADMIN_PASSWORD)
        admin.save()

        Selection.objects.all().delete()
        first_start = services.tehran_now() - timedelta(minutes=1)
        logins = []
        for number in range(1, students + 1):
            student_id = f'{STUDENT_PREFIX}{number:02d}'
            user, _ = User.objects.get_or_create(username=student_id)
            user.set_password(STUDENT_PASSWORD)
            user.save()
            start = first_start + timedelta(minutes=minutes * (number - 1))
            Members.objects.update_or_create(student_id=student_id, defaults={
                'num': number,
                'name': f'Demo Student {number}',
                'start_time': start.strftime(DATETIME_FORMAT),
                'end_time': (start + timedelta(minutes=minutes)).strftime(DATETIME_FORMAT),
                'logged': False, 'first': False, 'last': False,
                'line': '', **{field: '' for field in UNIT_FIELDS},
            })
            logins.append((student_id, start))

        self.stdout.write(self.style.SUCCESS(f'Demo data ready ({students} students).'))
        self.stdout.write(f'  admin:    {ADMIN_USERNAME} / {ADMIN_PASSWORD}   (http://127.0.0.1:8000/admin/)')
        self.stdout.write(f'  students: <id> / {STUDENT_PASSWORD}')
        for student_id, start in logins:
            window = 'open now' if start <= services.tehran_now() else f'opens {start:%H:%M} (Tehran)'
            self.stdout.write(f'    {student_id}  {window}')
