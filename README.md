# Property-Management

A small web app for private landlords to keep track of their rental properties and the
maintenance work on each one (broken boiler, leaking tap, gutters to clean...).
Built for the first assignment of Software Development and DevOps.

**Target user:** a private landlord with roughly 5-20 rental units who currently tracks
repair requests in WhatsApp chats and notes, and loses track of what is still open.

## Feature domains

| Domain | Module | What it does |
|---|---|---|
| Properties | `src/property.py` | Add, list and delete the properties you own. Every query is scoped to the logged-in user. |
| Maintenance tasks | `src/task.py` | Per property: add tasks with a priority, move them `pending -> in_progress -> done` (or reopen), delete them, and see a summary of open/urgent work. |
| Accounts (supporting) | `src/user.py` | Sign up / log in / log out with bcrypt-hashed passwords and a Flask session. |

The task domain only talks to the property domain through one function, `get_property()`
(see the comment at the top of `src/task.py`). That import is where the split would go
if tasks became its own service.

## Requirements

- Python 3.11+ (developed on 3.14)
- No external services: storage is a single SQLite file

## Setup and run

```bash
git clone https://github.com/Geulo/Property-Management.git
cd Property-Management
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Then open http://localhost:5000, create an account and log in.

The database and its tables are created automatically on first start. There is no
migration or setup step.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5000` | Port to listen on (always binds `0.0.0.0`) |
| `DATA_DIR` | `data` | Directory for the SQLite file. The database lives at `$DATA_DIR/property_management.db` |
| `SECRET_KEY` | random per start | Signs the session cookie. Set it in deployment, otherwise everyone is logged out on restart |
| `FLASK_DEBUG` | `0` | Set to `1` for the Flask debugger / auto-reload during development |

Example: `PORT=8080 DATA_DIR=/var/lib/pm SECRET_KEY=change-me python main.py`

## Tests and coverage

```bash
python -m pytest --cov=src --cov-report=term-missing
```

Result (2026-10-12): **52 passed, 99% coverage of `src/`** (221 statements, 1 missed).

- `tests/test_user.py`, `tests/test_property.py` and `tests/test_task.py` unit-test the business
  logic directly against a fresh in-memory SQLite database per test.
- `tests/test_routes.py` is a small smoke test through the Flask test client, one happy path
  per domain plus the main error cases.

## Project structure

```
main.py              app factory: config from env, registers blueprints, creates schema
src/database.py      SQLite connection (DATA_DIR path, row factory, foreign keys on)
src/schema.py        CREATE TABLE statements for users, properties, tasks
src/user.py          accounts domain: create_user, authenticate + routes
src/property.py      properties domain: add/list/get/delete + routes
src/task.py          tasks domain: add/list/update_status/delete/summarize + routes
src/util.py          bcrypt password hashing
templates/           Jinja2 pages (login, signup, property list, property detail)
static/styles.css    styling
tests/               pytest suite
ADR.md               architecture decision log
AI_USAGE.md          AI usage log
```
