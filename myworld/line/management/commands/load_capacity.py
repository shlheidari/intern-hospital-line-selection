"""Load the Capacity and Shared tables from the planning spreadsheets.

    python manage.py load_capacity            # uses ../python/data/*.xlsx
    python manage.py load_capacity --replace  # wipe both tables first
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from line.models import Capacity, Shared

DATA_DIR = Path(settings.BASE_DIR).parent / 'python' / 'data'
CAPACITY_HEADER = ['line', 'unit', 'hospital', 'capacity']
SHARED_HEADER = ['unit', 'shared unit']


def read_rows(path, expected_header):
    """Rows of the first sheet (without the header), skipping empty lines."""
    workbook = load_workbook(path, read_only=True)
    rows = workbook.active.iter_rows(values_only=True)
    header = [str(cell).strip() if cell is not None else '' for cell in next(rows)]
    if header[:len(expected_header)] != expected_header:
        raise CommandError(f'{path}: expected columns {expected_header}, found {header}')
    return [row[:len(expected_header)] for row in rows if any(cell is not None for cell in row)]


class Command(BaseCommand):
    help = 'Load Capacity and Shared rows from capacity.xlsx and shared.xlsx.'

    def add_arguments(self, parser):
        parser.add_argument('--capacity', type=Path, default=DATA_DIR / 'capacity.xlsx')
        parser.add_argument('--shared', type=Path, default=DATA_DIR / 'shared.xlsx')
        parser.add_argument('--replace', action='store_true',
                            help='delete existing Capacity and Shared rows first')

    def handle(self, *args, capacity, shared, replace, **options):
        for path in (capacity, shared):
            if not path.exists():
                raise CommandError(f'File not found: {path}')
        if not replace and (Capacity.objects.exists() or Shared.objects.exists()):
            raise CommandError('Capacity/Shared already contain data - use --replace to overwrite.')

        capacity_rows = read_rows(capacity, CAPACITY_HEADER)
        shared_rows = read_rows(shared, SHARED_HEADER)

        with transaction.atomic():
            Capacity.objects.all().delete()
            Shared.objects.all().delete()
            Capacity.objects.bulk_create([
                Capacity(line=str(line), unit=str(unit), hospital=str(hospital),
                         full=int(seats), reserved=0, remain=int(seats), gender='', common='')
                for line, unit, hospital, seats in capacity_rows
            ])
            Shared.objects.bulk_create([
                Shared(unit=str(unit), shared_unit=str(shared_unit))
                for unit, shared_unit in shared_rows
            ])

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {len(capacity_rows)} capacity rows and {len(shared_rows)} shared units.'))
