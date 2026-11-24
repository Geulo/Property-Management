# Architecture Decision Records

## 1. Python + Flask as the backend
Date: 2026-09-25
Status: Decided
Context: I needed a backend I could write and explain myself that serves a few HTML forms, keeps a login session and talks to SQLite, all in one process. Python is the language I use in every other course repo.
Decision: Python with Flask, Jinja2 templates rendered by the same process, and the standard-library `sqlite3` module instead of an ORM.
Alternatives considered: Django: its ORM, admin and migrations are built for much bigger apps, and with three tables I would be configuring more than I build. FastAPI: designed for JSON APIs with async and Pydantic models; my app is server-rendered forms, so I would still need to add templating and sessions myself.
Consequences: Very little framework code, and every SQL query is visible and explainable. The cost is that I write validation and schema creation by hand, and there is no migration tool if the schema changes later.

## 2. Properties and maintenance tasks as two separable domains
Date: 2026-10-12
Status: Decided
Context: The app needs two feature domains that could later become separate services. My first version only had accounts + properties, and accounts is really a supporting concern rather than a feature a landlord uses.
Decision: The two feature domains are properties (`src/property.py`) and maintenance tasks (`src/task.py`), each its own Flask blueprint with its own table and logic functions. Tasks only reach into properties through one function, `get_property()`, to check that the logged-in user owns the property.
Alternatives considered: Accounts + properties as the two domains: rejected because login has no business rules of its own and would be replaced by an identity provider rather than become a service. One combined module for properties and tasks: simpler, but then there is no seam to cut along later.
Consequences: Splitting later means replacing the `get_property()` import with an HTTP call to a property service and moving the tasks table into its own database. Until then, the tasks table still has a real foreign key to properties, which the split would have to replace with a stored id.

## 3. One-to-many schema: users -> properties -> tasks with cascading deletes
Date: 2026-10-12
Status: Superseded by 7
Context: My first schema put a `property_id` column on `users`, which only allows one property per user, plus `roles` and `credentials` tables. It also had syntax errors and never actually ran.
Decision: Three tables. `properties.user_id` references `users`, and `tasks.property_id` references `properties`, both `ON DELETE CASCADE`. Task `status` and `priority` are TEXT columns with `CHECK` constraints, and foreign keys are switched on per connection with `PRAGMA foreign_keys = ON`.
Alternatives considered: Lookup tables for statuses and priorities: more joins for three fixed values that only change when the code changes. Deleting a property's tasks in Python code: easy to forget, and it would make the property module know about the tasks table.
Consequences: A landlord can own many properties and each property many tasks, and deleting a property cleanly removes its tasks. Adding a new status means changing both the `CHECK` constraint and `STATUSES` in `task.py`, and SQLite can only change a `CHECK` by rebuilding the table.

## 4. Test the logic layer directly against in-memory SQLite
Date: 2026-10-12
Status: Superseded by 9
Context: The 70% coverage target is about core business logic, but my original route functions mixed SQL, validation and Flask `request`/`session` together, so they could only be tested through HTTP.
Decision: Every domain has plain functions that take a `connection` as their first argument (`add_property`, `update_status`, `authenticate`...), and the routes are thin wrappers around them. Tests create a fresh `:memory:` database with `create_schema()` for every test (fixture in `tests/conftest.py`). On top of that there is one smoke-test file through Flask's test client.
Alternatives considered: Testing only through the Flask test client: it also gets coverage, but a failing test then doesn't tell you whether the rule or the wiring is broken, and every test needs signup + login first. Mocking the database: hides real behaviour like the `UNIQUE` email constraint and `ON DELETE CASCADE`, which are exactly the rules I wanted to check.
Consequences: I prioritised validation, ownership isolation (user A can't see or delete user B's property), cascade delete and the status transition table, which reached 99% of `src/`. Left thinner on purpose: the HTML templates (only checked for a few strings), bcrypt itself, and concurrent writes to SQLite.

## 5. No roles for tenants or contractors
Date: 2026-10-12
Status: Decided
Context: My early schema had `roles` and `credentials` tables so tenants could report issues and contractors could update tasks themselves.
Decision: Only one kind of user, the landlord, who owns their properties and tasks. I removed the `roles` and `credentials` tables.
Alternatives considered: Building the roles now: it needs a permission check on every route and an invite flow to link tenants to properties, roughly doubling the auth code for a user story my target user (one landlord with ~10 units) does not need yet.
Consequences: Ownership is enforced by one rule, every query filters on `user_id`, which is simple to test. Adding tenants later means a new `memberships` table between users and properties, and changing that ownership check.

## 6. The split: tasks asks property over HTTP, nothing else crosses the seam
Date: 2026-11-11
Status: Decided
Context: Assignment 2 splits the monolith into one service per domain. ADR-2 put the seam at `get_property()`: `task.py` imported it from `property.py` to check that a property belongs to the logged-in user before adding a task.
Decision: Two services. property owns users, login and properties; tasks owns tasks. The `get_property()` import became one HTTP call, `GET {PROPERTY_URL}/properties/{id}` with a 2 second timeout, made only when a task is added. Login moved with the users table into property, which signs a token (itsdangerous, 8 hours). tasks checks the signature itself with the same `SECRET_KEY`, and stores the `user_id` on each task, so listing, changing and deleting tasks never call property. When property is down or too slow, adding a task fails fast with `503 "Property service unavailable, try adding the task again later"`; the rest of tasks keeps working and its `/health` stays 200, because it only reports its own database.
Alternatives considered: Accepting the task without the check while property is down: then a task could be attached to a property that isn't yours, so an honest error is safer and the user can simply try again. Retrying: makes the user wait longer and ends in the same error when property is really down. tasks asking property to verify every token instead of sharing the key: one extra call on every request, and all of tasks would stop working whenever property is down.
Consequences: ADR-2 held: the seam did not move, one import became one HTTP call, and only one question crosses it. The shared `SECRET_KEY` is the price: it lives in two services, so a leak from either lets anyone make a valid login token, and changing it means updating both at once. It is a GitHub secret passed to Container Apps as a secret, never in the repo.

## 7. One SQL Server database per service, versioned migrations at startup
Date: 2026-11-24
Status: Decided
Context: The monolith had one SQLite file with a foreign key and `ON DELETE CASCADE` from tasks to properties (ADR-3). The brief asks for SQL Server, one database per service, and versioned migrations that can change a table that already holds data.
Decision: Two databases, `property` and `tasks`, each with its own login that has no access to the other. The SQL moved from SQLite to SQL Server (`INT IDENTITY`, `NVARCHAR`, `%s` placeholders, `OUTPUT INSERTED.<id>` instead of `lastrowid`); this replaces the SQLite part of ADR-1. Migrations are numbered SQL files per service (`migrations/001_init.sql`, `002_...`), applied at startup by a small runner (`src/migrations.py`): each new file runs once, in name order, in one transaction together with its row in `schema_migrations`. Both `002` migrations changed tables that already held data on Azure, and the data was kept: tasks got `updated_at` (backfilled from `created_at`), properties got `units` (existing rows got 1).
Alternatives considered: Alembic: it is built around SQLAlchemy models, which I don't have (ADR-1 chose plain SQL), and a 40-line runner does what I need and I can explain every line. Keeping the cross-database link with a trigger or a shared database: the brief forbids a shared database, and SQL Server cannot enforce a foreign key across databases.
Consequences: The foreign key from tasks to properties is gone. The HTTP check in ADR-6 replaces it when a task is added. Not compensated on purpose: deleting a property leaves its tasks in the tasks database. Nobody can reach them, because property ids are never reused and every task query also filters on `user_id`; a cleanup call or event (ADR-10) would fix it if it mattered. Recovery plan for a bad migration (forward-only): a migration that fails is rolled back with its transaction, so the database is unchanged, the new version never becomes healthy and the old revision keeps serving; I fix it with a new numbered file and never edit an applied one. A migration that ran but was wrong is fixed the same way, and Azure SQL's point-in-time restore is the last resort if data was lost.

## 8. Serverless hosting on Azure, scaled to zero
Date: 2026-11-24
Status: Decided
Context: The brief asks for pay-per-use resources only. The professor's service principal was not provided, and my Azure for Students subscription only allows five European regions.
Decision: Two Container Apps on the Consumption plan (0 to 1 replica each), two Azure SQL serverless databases (0.5 to 1 vCore, auto-pause after 15 minutes, 2 GB, LRS backups), images on GHCR, and the UI as a Storage static website. Everything is in my own subscription and resource group `rjpenning-ieu2024-rg` in Germany West Central; GitHub logs in through a managed identity with OIDC, so no Azure password is stored. This is one disclosed deviation: my own subscription and resource group instead of the course's, with the same names and settings otherwise.
Alternatives considered: Waiting for the course's service principal: there was no time left. Always-on hosting (App Service, a minimum of 1 replica): a fixed monthly cost, which the brief rules out.
Consequences: When nobody uses the app it costs almost nothing, because the containers are at zero and the databases are paused; only storage is billed. The price is a slow first request after a quiet period: the container has to start and the database has to resume, which can take up to a minute. So `Database.connect` retries with growing waits (up to 8 attempts) and the deploy waits up to 3 minutes for `/health`. Running migrations at startup is safe because there is at most one replica, so two copies can never run the same migration at once. At 100x the traffic: more replicas, and then migrations have to move out of startup into one separate deploy step (or behind a database lock), a minimum of one replica to avoid cold starts, a bigger or provisioned database, and connection pooling.

## 9. CI gates everything, and the seam is tested on the real stack
Date: 2026-11-24
Status: Decided
Context: Nothing should reach Azure without being tested, and the most likely thing to break after a split is the call across the seam. ADR-4 tested against in-memory SQLite, which no longer matches the database in production.
Decision: CI runs on every push and pull request: ruff, the unit tests of each service against a throwaway SQL Server started in the job, a coverage gate of 70% per service, the integration test, the contract checks (`system.yaml` against `system.schema.json`, each `openapi.yaml` against the OpenAPI specification) and both image builds. Images are pushed to GHCR, tagged with the commit SHA, only on `main` and only after the tests pass. The deploy runs only after CI succeeded on that same commit, and fails unless both `/health` endpoints answer 200 with that SHA. The integration test (`tests/integration/test_cross_seam.py`) starts the whole compose stack, adds a task (a real call from tasks to property), tries a property that doesn't exist (404), then stops property and checks the 503, that it comes within 5 seconds, and that tasks still lists tasks and stays healthy.
Alternatives considered: Testing the seam only with a stub (a fake property service): faster, and the unit tests do that, but it can't show that the two real services agree on the API or that compose works from a clean checkout. Running tests against Azure SQL: it would wake up and bill the database on every push, so CI never touches Azure.
Consequences: Every change reached `main` through a pull request with green CI. Deliberately not tested: the UI's JavaScript (checked by hand, with screenshots), real Azure cold starts, concurrent writes, and token expiry in real time (tested with an already-expired token instead).

## 10. Not built: a message broker for property events
Date: 2026-11-24
Status: Decided
Context: Deleting a property leaves its tasks behind in the tasks database (ADR-7). The brief puts message brokers out of scope.
Decision: No broker. Property and tasks only talk through the one HTTP call in ADR-6.
Alternatives considered: A broker (for example Azure Service Bus): property would publish a "property deleted" event and tasks would delete that property's tasks when it receives it, without property having to call tasks or wait for it. A direct cleanup call from property to tasks: simpler, but then deleting a property fails or half-works when tasks is down.
Consequences: Leftover tasks stay in the database, unreachable. A broker becomes worth building when more than one service needs to react to the same events (for example a notifications or billing service), or when leftover data starts to cost money or matter for privacy; it adds a component that is always on, plus retries and duplicate messages to handle.
