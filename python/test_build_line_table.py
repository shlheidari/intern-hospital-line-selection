"""Tests for build_line_table.py - run with ``python -m unittest discover python``."""
import json
import unittest
from pathlib import Path

import build_line_table as blt

HERE = Path(__file__).resolve().parent
APP_DATA = HERE.parent / 'myworld' / 'line' / 'data'

SAMPLE = """<table class="sheet0 gridlines">
<tr class="row0">
<td class="column0 style1 null"></td>
<td class="column1 style2 s">1 A</td>
<td class="column2 style2 s">1 B</td>
<td class="column3 style2 s">2 A</td>
</tr>
<tr class="row1">
<td class="column0 style3 s">ماه اول</td>
<td class="column1 style4 s" colspan="2">جراحی</td>
</tr>
"""


def without_classes(value):
    if isinstance(value, dict):
        return {k: without_classes(v) for k, v in value.items() if k != 'class'}
    if isinstance(value, list):
        return [without_classes(v) for v in value]
    return value


class SuffixTests(unittest.TestCase):
    def test_columns_map_to_lines(self):
        self.assertEqual([blt.line_suffix(n) for n in (1, 2, 3, 4, 35, 36)],
                         ['1A', '1B', '2A', '2B', '18A', '18B'])


class CellIdTests(unittest.TestCase):
    def test_schedule_cells_get_id_and_title(self):
        html = blt.add_cell_ids(SAMPLE)
        self.assertIn('<td id="1" title="1 A-1A" class="column1 style2 s">1 A</td>', html)
        self.assertIn('<td id="3" title="2 A-2A" class="column3 style2 s">2 A</td>', html)
        self.assertIn('<td id="4" title="جراحی-1A" class="column1 style4 s" colspan="2">', html)

    def test_label_column_is_left_alone(self):
        html = blt.add_cell_ids(SAMPLE)
        self.assertIn('<td class="column0 style3 s">ماه اول</td>', html)


class RowParsingTests(unittest.TestCase):
    def test_rows_and_cells(self):
        rows = blt.html_to_rows(blt.add_cell_ids(SAMPLE))
        self.assertEqual([r['id'] for r in rows], [1, 2])
        self.assertEqual(rows[0]['class'], 'sheet0 gridlines')
        self.assertEqual(rows[0]['cells'][1],
                         {'id': '1', 'title': '1 A-1A', 'class': 'column1 style2 s', 'content': '1 A'})
        self.assertEqual(rows[1]['cells'][1]['colspan'], '2')
        self.assertEqual(len(rows[0]['cells']), 4)
        self.assertEqual(len(rows[1]['cells']), 2)  # missing cells are omitted


class ShippedTablesTests(unittest.TestCase):
    """The tables the web app ships must stay reproducible from the sources."""

    def build(self, name, **kwargs):
        html = (HERE / 'data' / name).read_text(encoding='utf-8', errors='ignore')
        rows = blt.html_to_rows(blt.add_cell_ids(html))
        return rows[:kwargs.get('rows')]

    def test_select_table_matches_divided_export(self):
        shipped = json.loads((APP_DATA / 'line_table_select.json').read_text(encoding='utf-8'))
        self.assertEqual(self.build('line_divided.html', rows=37), shipped)

    def test_capacity_table_matches_line_export(self):
        shipped = json.loads((APP_DATA / 'line_table_capacity.json').read_text(encoding='utf-8'))
        # the page stylesheet uses its own CSS class numbers
        self.assertEqual(without_classes(self.build('line.html')), without_classes(shipped))


if __name__ == '__main__':
    unittest.main()
