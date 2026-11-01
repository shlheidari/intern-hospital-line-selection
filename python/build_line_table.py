#!/usr/bin/env python3
"""Turn the line-schedule spreadsheet into the JSON table the web pages render.

Pipeline
--------
1. Export ``data/line.xlsx`` to an HTML table (any spreadsheet-to-HTML
   converter works; the checked-in ``data/line.html`` came from
   https://convertio.co/).
2. ``add_cell_ids`` gives every schedule cell an ``id`` and a ``title`` such as
   ``"جراحی-1A"`` (department + line) so the page can address it.
3. ``html_to_rows`` converts the HTML rows into a list of dictionaries
   ``{id, class, cells: [{id, title, class, colspan, rowspan, content}, ...]}``.
4. The result is written as JSON, one table row per line. Copy it to
   ``myworld/line/data/`` to use it in the app.

Usage::

    python build_line_table.py                       # data/line.html -> output/line_table.json
    python build_line_table.py data/line_divided.html --rows 37 -o table.json
"""
import argparse
import io
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

CELL_ATTRIBUTES = ('id', 'title', 'class', 'colspan', 'rowspan')

# Cells that are labels, not schedule slots, are left untouched.
SKIPPED_MARKERS = ('column0', '***', 'آزمون')


def line_suffix(column):
    """Spreadsheet column number -> line name: 1 -> 1A, 2 -> 1B, 3 -> 2A, ..."""
    return f"{(column + 1) // 2}{'A' if column % 2 else 'B'}"


def add_cell_ids(html):
    """Add ``id="<n>"`` and ``title="<text>-<line>"`` to every schedule ``<td>``."""
    out = [' ']
    number = 0
    for raw in io.StringIO(html):
        line = raw.strip()
        if line.startswith('<td') and not any(marker in line for marker in SKIPPED_MARKERS):
            column = re.search(r'column(\d+) ', line)
            if column:
                number += 1
                text = line.split('>')[1].split('<')[0]
                title = f'{text}-{line_suffix(int(column.group(1)))}'
                line = line.replace('<td', f'<td id="{number}" title="{title}"')
        out.append(line + '\n')
    return ''.join(out)


def parse_cell(chunk):
    cell = {}
    for attribute in CELL_ATTRIBUTES:
        found = re.findall(f'{attribute}="(.*?)"', chunk)
        if found:
            cell[attribute] = found[0]
    content = re.findall('>(.*?)</td>', chunk)
    if content:
        cell['content'] = content[0]
    return cell


def parse_row(chunk, number):
    parts = chunk.split('<td')
    return {
        'id': number,
        'class': re.findall('class="(.*?)"', parts[0])[0],
        'cells': [parse_cell(part) for part in parts[1:]],
    }


def html_to_rows(html):
    """One dictionary per ``<tr>`` of the table."""
    chunks, current = [], ''
    for raw in io.StringIO(html):
        current += raw.strip() + '\n'
        if raw.strip().startswith('</tr'):
            chunks.append(current)
            current = ''
    return [parse_row(chunk, number) for number, chunk in enumerate(chunks, start=1)]


def write_json(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ',\n'.join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(f'[\n{body}\n]\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('source', nargs='?', type=Path, default=HERE / 'data' / 'line.html',
                        help='HTML export of the spreadsheet (default: data/line.html)')
    parser.add_argument('-o', '--output', type=Path, default=HERE / 'output' / 'line_table.json',
                        help='JSON file to write (default: output/line_table.json)')
    parser.add_argument('--rows', type=int, metavar='N',
                        help='keep only the first N rows (exports of the full sheet end with '
                             'thousands of empty rows)')
    parser.add_argument('--ids-html', type=Path,
                        help='also save the intermediate HTML with cell ids')
    args = parser.parse_args(argv)

    html = args.source.read_text(encoding='utf-8', errors='ignore')
    with_ids = add_cell_ids(html)
    if args.ids_html:
        args.ids_html.parent.mkdir(parents=True, exist_ok=True)
        args.ids_html.write_text(with_ids, encoding='utf-8')
    rows = html_to_rows(with_ids)[:args.rows]
    write_json(rows, args.output)
    print(f'{len(rows)} rows -> {args.output}')


if __name__ == '__main__':
    main()
