# Property-Management

A small web app for private landlords to keep track of their rental properties and the
maintenance work on each one (broken boiler, leaking tap, gutters to clean...).
Built for Software Development and DevOps: a Flask monolith in Assignment 1, split into two
services, containerised and deployed to Azure in Assignment 2.

**Target user:** a private landlord with roughly 5-20 rental units who currently tracks
repair requests in WhatsApp chats and notes, and loses track of what is still open.

**Live:** https://rjpenningieu2024ui.z1.web.core.windows.net/

## Architecture

```
browser ── ui/ (static HTML/JS) ──┬──▶ property service ──▶ SQL database "property" (users, properties)
                                  └──▶ tasks service ────▶ SQL database "tasks" (tasks)
                                          └──HTTP──▶ property: GET /properties/{id} when a task is added
```

| Service | Folder | Owns | Talks to |
|---|---|---|---|
| property | `services/property/` | users, login, properties | its own database |
| tasks | `services/tasks/` | maintenance tasks per property | its own database; property over HTTP (`PROPERTY_URL`, 2 s timeout) |
| UI | `ui/` | static pages | both services from the browser (`ui/config.js`) |

The seam is the one from ADR-2: in Assignment 1 `task.py` imported `get_property()`; now tasks asks
the property service over HTTP. Login: property signs a token, tasks checks it with the same
`SECRET_KEY`, so tasks keeps serving its own data while property is down. If property is down,
adding a task answers 503 "Property service unavailable" within the timeout. Decisions: `ADR.md` 6-10.
Machine-readable description: `system.yaml` and `services/<name>/openapi.yaml`.

## Run the whole system locally

Needs Docker Desktop. On Apple Silicon, enable "Use Rosetta for x86_64/amd64 emulation" in
Docker Desktop (SQL Server has no ARM image).

```bash
cp .env.example .env    # then fill in the four values (instructions in the file)
docker compose up --build
```

- UI: http://localhost:8080
- property: http://localhost:8001/health
- tasks: http://localhost:8002/health

Compose starts SQL Server, waits for its healthcheck, runs `db/init.sql` once (`db-init`: one database
and one login per service, safe to re-run), then both services (each applies its pending migrations at
startup) and nginx serving `ui/`.

Try a partial failure: `docker compose stop property`, then add a task in the UI (clear error) and
see that the task list still loads. `docker compose start property` brings it back.

`docker compose down` keeps the data; `docker compose down -v` deletes it.

## Run a single service

Each service needs a SQL Server and its env vars. With the compose SQL Server running
(`docker compose up -d sqlserver db-init`):

```bash
cd services/tasks
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
DATABASE_URL="mssql://tasks_user:<TASKS_DB_PASSWORD>@localhost:1433/tasks" \
SECRET_KEY="<same as in .env>" PORT=8002 python app.py
```

Or only its container: `docker compose up --build tasks` (starts its dependencies too).

## Configuration

| Variable | Service | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | both | none (secret) | `mssql://user:password@host:1433/database` |
| `SECRET_KEY` | both | none (secret) | signs login tokens; must be the same in both |
| `PORT` | both | `8000` | port to listen on |
| `CORS_ORIGIN` | both | `http://localhost:8080` | the only browser origin allowed to call the service |
| `GIT_SHA` | both | `dev` | version reported by `/health` |
| `DB_CONNECT_ATTEMPTS` | both | `8` | connection retries with backoff (SQL Server start, Azure SQL resume) |
| `PROPERTY_URL` | tasks | `http://property:8000` | base URL of the property service |
| `PROPERTY_TIMEOUT_S` | tasks | `2` | timeout of every call to property |

## Database migrations

Each service has `migrations/NNN_name.sql`. At startup `src/migrations.py` applies every file not yet
listed in the `schema_migrations` table, in name order, each in one transaction with its record, and
logs `applied migration <file>`. A second start applies nothing. Applied files are never edited; a
change is a new file. Two migrations changed tables that already held data on Azure:

- tasks `002_add_task_updated_at.sql`: adds a column, backfills it from `created_at`, then makes it NOT NULL.
- property `002_add_property_units.sql`: adds `units INT NOT NULL DEFAULT 1` (1-500), so every existing
  property keeps its data and gets 1 unit in the same statement.

Each has a test that replays `001`, inserts a row, applies `002` and checks the row survived.

## Tests and coverage

Unit tests run against a real SQL Server (tests that need one are skipped without it):

```bash
cd services/property    # or services/tasks
pip install -r requirements-dev.txt
TEST_DATABASE_URL="mssql://sa:<SA_PASSWORD>@localhost:1433/property_test" \
  python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=70
```

Integration test across the seam, against the running compose stack:

```bash
pip install -r tests/integration/requirements.txt
python -m pytest tests/integration -v
```

Last local run (24 Nov): property 45 passed, 96% of `src/`; tasks 42 passed, 98% of `src/`.

## CI/CD

`.github/workflows/`:

- `ci.yml`, every push and pull request: ruff and pytest per service against a throwaway SQL Server
  (password generated in the run), coverage gate of 70% per service, the integration test on the
  compose stack, and both images built. On `main` only, the images are pushed to GHCR as
  `ghcr.io/geulo/pm-<service>:<commit sha>`.
- `contracts.yml`, every push and pull request: `system.yaml` against `system.schema.json`, each
  `openapi.yaml` against the OpenAPI specification.
- `deploy.yml`, after CI succeeds on `main`: signs in to Azure with OIDC (no stored password), deploys
  the images of exactly that commit to Container Apps, publishes `ui/` with a generated `config.js`,
  and fails unless both `/health` endpoints answer 200 with that commit's SHA as `version`
  within 3 minutes.

Changes reach `main` through pull requests, so CI runs before CD.

## Deployment on Azure

| Resource | Name |
|---|---|
| Resource group | `rjpenning-ieu2024-rg` (Germany West Central) |
| Container Apps (Consumption, 0-1 replicas) | `rjpenning-ieu2024-property`, `rjpenning-ieu2024-tasks` in `rjpenning-ieu2024-env` |
| Azure SQL serverless (0.5-1 vCore, auto-pause) | `rjpenning-ieu2024-property-db`, `rjpenning-ieu2024-tasks-db` on `rjpenning-ieu2024-sql` |
| UI (Storage static website) | `rjpenningieu2024ui` |
| Deploy identity (OIDC from GitHub `main`) | `rjpenning-ieu2024-deploy` |

**Deviation from the brief (§7):** the course's service principal was never provided, so everything
runs in my own Azure for Students subscription, with my own resource group and deploy identity.
Names and settings otherwise follow §7. See ADR-8.

**Second deviation, the UI host:** the UI is an Azure Storage static website instead of Static Web Apps.
The subscription's region policy allows only Spain Central, Norway East, Germany West Central, Italy North
and Poland Central, and Static Web Apps exist only in Central US, East US 2, West US 2, West Europe and East
Asia (`az provider show -n Microsoft.Web`), so no allowed region has them. The static website serves the same
files over HTTPS, costs only its storage, and gets `config.js` from the deploy the same way.

### Reproduce the initial setup

Once, from a terminal with the Azure CLI, `gh` and `sqlcmd`:

```bash
az login
bash infra/setup.sh
```

The script picks a region the subscription allows, creates the resource group, the SQL server (SQL
authentication on, firewall "allow Azure services"), both serverless databases, one database user per
service with access to its own database only, the Container Apps environment, the storage account for
the UI and the deploy identity with an OIDC trust for `main`, then stores the GitHub secrets
(`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `PROPERTY_DATABASE_URL`,
`TASKS_DATABASE_URL`, `SECRET_KEY`). The GHCR packages `pm-property` and `pm-tasks` must be public.
After that, nothing is changed by hand: every deploy comes from the pipeline.

## Project structure

```
services/property/   app.py, src/ (user, property, auth, database, migrations, observability),
                     migrations/, tests/, openapi.yaml, Dockerfile, requirements*.txt
services/tasks/      app.py, src/ (task, property_client, auth, database, migrations, observability),
                     migrations/, tests/, openapi.yaml, Dockerfile, requirements*.txt
ui/                  static pages, app.js, config.js (overwritten at deploy)
db/init.sql          local databases and logins for compose
infra/setup.sh       one-time Azure setup
tests/integration/   cross-seam test on the compose stack
docker-compose.yml   the whole system locally
system.yaml          system description, validated against system.schema.json
ADR.md               architecture decisions (1-5 Assignment 1, 6-10 Assignment 2)
AI_USAGE.md          AI usage log
```

## Process note

Most of Assignment 2 was built on 11 and 24 November, so the commit history does not meet the
"6 distinct days" cadence asked for in §6.

## AI disclosure

AI tools were used as described in `AI_USAGE.md` (ONEchat in Assignment 1, Claude Code in both).
Every row lists my prompt, what I kept or changed, and how the result works in my own words.
