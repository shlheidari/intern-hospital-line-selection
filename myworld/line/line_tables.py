"""The line-schedule tables rendered by the selection and capacity pages.

The tables are generated from the planning spreadsheet by the scripts in the
top-level ``python/`` folder and stored as JSON next to the code. Each table is
a list of rows: ``{id, class, cells: [{id, title, class, colspan, rowspan, content}, ...]}``.
"""
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'data'


@lru_cache(maxsize=None)
def load_line_table(name):
    """Return ``line_table_<name>.json`` parsed (shared object - do not mutate)."""
    with open(DATA_DIR / f'line_table_{name}.json', encoding='utf-8') as f:
        return json.load(f)
