# Data preparation scripts

Helpers that turn the planning spreadsheets into data the web app uses.

| File | Purpose |
| --- | --- |
| `data/line.xlsx` | The rotation schedule: one row per month, one column per line (`1A`, `1B`, ... `18B`). |
| `data/line_divided.xlsx` | The same schedule with the department repeated in every line's column instead of one wide merged cell, so each line has its own cell. |
| `data/line.html`, `data/line_divided.html` | HTML exports of the two sheets (converted with <https://convertio.co/>). `line_divided.html` is trimmed to the 37 rows that matter - the full export is 31 MB of empty rows. |
| `data/capacity.xlsx` | Seats per line / unit / hospital - loaded into the `Capacity` table. |
| `data/shared.xlsx` | Which units share the seats of another unit - loaded into the `Shared` table. |
| `build_line_table.py` | Spreadsheet export -> JSON table for the pages. |
| `test_build_line_table.py` | Tests, including a check that the tables shipped with the app can be rebuilt from these sources. |

## Loading capacity into the database

```bash
cd ../myworld
python manage.py load_capacity            # reads python/data/capacity.xlsx and shared.xlsx
python manage.py load_capacity --replace  # wipe both tables first
```

## Rebuilding the line tables

```bash
# selection page table = first 37 rows of the divided export
python build_line_table.py data/line_divided.html --rows 37 \
    -o ../myworld/line/data/line_table_select.json

# capacity page table
python build_line_table.py data/line.html -o output/line_table.json
```

The script runs in two steps: `add_cell_ids` gives every schedule cell an `id`
and a `title` such as `جراحی-1A`, then `html_to_rows` turns the HTML rows into
`{id, class, cells: [...]}` dictionaries. The shipped `line_table_select.json` is reproduced byte for byte;
`line_table_capacity.json` differs from the second command only in the CSS
class numbers (the capacity page has its own stylesheet).

## Tests

```bash
python -m unittest discover -s .
```
