# Intern Hospital Line Selection

[![tests](https://github.com/shlheidari/intern-hospital-line-selection/actions/workflows/tests.yml/badge.svg)](https://github.com/shlheidari/intern-hospital-line-selection/actions/workflows/tests.yml)

A web app that lets medical interns pick their **hospital rotation schedule
("line")** one after another, each inside their own time slot, while keeping
every unit's capacity consistent. The interface is in Persian.

Built with **Django 4.2**, PostgreSQL and a small React front end.

> Everything in this repository is sample data. The student IDs and passwords
> in `myworld/line/data/sample_users.csv` are randomly generated.

## How it works

1. An admin imports the students (rank, student ID, password, name, start/end
   time) from an Excel sheet in the Django admin. Each student gets a login and
   an individual **selection window**.
2. Inside their window a student logs in, picks a *line* (a month-by-month
   rotation plan) and then, for every department (surgery, internal medicine,
   pediatrics, gynecology, emergency, orthopedics, cardiology and three
   electives), the **hospital** they want to rotate in.
3. Capacity is tracked per line / department / hospital (some departments share
   capacity). A full unit cannot be chosen; the remaining seats are recomputed
   from everybody's saved choices. Each elective *specialty* can be taken only
   once across the three electives.
4. When the window ends - or the student logs out manually - the choices are
   saved to their record and the working selection is cleared for the next
   student.
5. Public pages show the capacity board and the list of members with their
   results. Superusers get a live data page to monitor and correct records.

## Features

- Per-student time windows enforced on the server (`Asia/Tehran` time), also on
  every call of the selection API
- Single active session per account (`django-user-sessions` +
  `django-preventconcurrentlogins`), plus a polling check that signs out a
  second login
- Capacity bookkeeping for lines, departments and hospitals, including shared
  units
- Server-side check that every required department has been chosen
- Bulk import of students from `.xlsx` through the admin, with a downloadable
  template and a per-import result log
- `manage.py load_capacity` seeds the capacity tables from the spreadsheets and
  `manage.py seed_demo` creates a ready-to-use demo (admin, students, windows)
- Superuser-only live data page with inline editing (tables and columns are
  whitelisted, values are validated before they are saved)
- Settings are environment driven and fail closed: `DEBUG` defaults to off and
  a missing `SECRET_KEY` is an error in production
- Three layers of tests: Python (61), JavaScript unit tests (26) and browser
  end-to-end tests (Playwright)

## Tech stack

| Area | Tools |
| --- | --- |
| Backend | Python 3.11, Django 4.2, openpyxl |
| Database | PostgreSQL (SQLite fallback for local use) |
| Front end | React 18 (selection and capacity pages), axios, vanilla JS elsewhere; Bootstrap 3 CSS; bundled with esbuild |
| Auth / sessions | Django auth, `django-user-sessions`, `django-preventconcurrentlogins` |
| Static files | WhiteNoise (production) |
| Tests | Django `TestCase`, `node:test`, Playwright |
| Deployment | [Liara](https://liara.ir) (`myworld/liara.json`) |

## Quick start

Requires Python 3.11. Node is only needed to change the front end - the built
bundles are committed.

```bash
git clone https://github.com/shlheidari/intern-hospital-line-selection.git
cd intern-hospital-line-selection/myworld

python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-min.txt

cp myworld/.env.example myworld/.env   # DEBUG=True and SQLite
python manage.py migrate
python manage.py seed_demo             # seats, an admin and demo students
python manage.py runserver
```

Open <http://127.0.0.1:8000/>, press **انتخاب لاین** and log in as the first
demo student (`990000001` / `demo-pass-123`; its window is open for 30 minutes
and `seed_demo` prints the others). `/capacity/` shows the capacity board and
`/admin/` the admin site (`admin` / `admin-demo-pass`). To import your own
students use **User import jobs** in the admin (the template can be downloaded
from that page).

`requirements.txt` is a full `pip freeze` of the original development machine;
`requirements-min.txt` lists only what the app imports.

### Configuration

Environment variables, optionally read from `myworld/myworld/.env` (see
`.env.example`; the real `.env` is git-ignored):

| Variable | Purpose |
| --- | --- |
| `DEBUG` | `True` / `False` (default `False`) |
| `SECRET_KEY` | Django secret key - required when `DEBUG` is off |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Comma separated, for production |
| `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Database connection; SQLite when unset. The older un-prefixed names (`ENGINE`, `NAME`, ...) still work |

### Deploying

The pages load their CSS/JS from static files, so production needs them
collected and served:

```bash
python manage.py collectstatic --noinput   # into myworld/staticfiles
```

With `DEBUG` off, WhiteNoise serves them straight from the app. Remember to set
`SECRET_KEY` and `ALLOWED_HOSTS`, and to run `migrate`.

## Front end

The selection and capacity pages are React apps; everything lives in
`frontend/src` and is bundled into `myworld/line/static/line/js` (committed, so
a deploy needs no Node):

```bash
npm ci
npm run build     # rebuild the bundles after changing frontend/src
npm run vendor    # refresh the Bootstrap CSS copied into static/
npm test          # unit tests of the pure logic (node:test)
npm run e2e       # browser tests with Playwright against a demo server
```

- `common/schedule.js` and `common/clock.js` hold the rules that are easy to
  get wrong (which column a line owns, the one-specialty-per-elective rule,
  the countdown) as small pure functions with unit tests.
- Pages get their data through Django's `json_script`, not by templating JSON
  into JavaScript, and never use `innerHTML` with server data.
- No CDN, jQuery or in-browser compilation. The selection page went from a
  7.5 MB template (React, Babel and jQuery pasted into it) to a 1 KB template,
  a 184 KB script and the page data - about 1 MB in all, and the scripts and
  styles are cached between visits.

`npm run e2e` starts its own server with demo data (set `E2E_PYTHON` to the
interpreter that has the requirements installed) and, before the first run,
needs the browsers installed with `npx playwright install chromium`.

## Running the tests

```bash
cd myworld
SECRET_KEY=test python manage.py test      # app tests (SQLite, no .env needed)
cd .. && python -m unittest discover -s python   # data pipeline tests
npm test                                   # front-end unit tests
```

## Project layout

```
myworld/
  manage.py
  myworld/            Django project (settings, urls, .env.example)
  line/               The app
    models.py         Members, Capacity, Shared, Selection, UserImportJob
    views.py          HTTP layer: pages, selection API, admin utilities
    services.py       Selection rules: time windows, capacity maths, registering a turn
    constants.py      Units, required departments, messages
    line_tables.py    Loads the schedule tables in data/
    data/             Schedule tables rendered by the pages (JSON), sample users
    admin.py          Excel import and admin tooling
    management/       load_capacity, seed_demo
    templates/line/   base.html and one template per page
    static/line/      css/, js/ (built bundles), vendor/ (Bootstrap CSS)
    pcl_migrations/   Migrations for django-preventconcurrentlogins (see below)
    tests.py
frontend/             React and vanilla JS sources, esbuild scripts, unit tests
e2e/                  Playwright tests
python/               Spreadsheets and the script that builds the schedule tables
.github/workflows/    CI
```

## Notes and limitations

- The auto-logout when a window ends uses in-process timers, so the app is
  designed to run as a **single worker process**; timers do not survive a
  restart.
- The selection API keeps one *working* selection for the student whose turn it
  is, so selection windows must not overlap.
- `DEFAULT_AUTO_FIELD` is `BigAutoField`, which differs from the third-party
  `django-preventconcurrentlogins` migrations. The follow-up migration is kept in
  `line/pcl_migrations/` (via `MIGRATION_MODULES`) so a fresh clone can run
  `migrate`.

## License

[MIT](LICENSE)
