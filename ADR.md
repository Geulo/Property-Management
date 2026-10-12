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
Status: Decided
Context: My first schema put a `property_id` column on `users`, which only allows one property per user, plus `roles` and `credentials` tables. It also had syntax errors and never actually ran.
Decision: Three tables. `properties.user_id` references `users`, and `tasks.property_id` references `properties`, both `ON DELETE CASCADE`. Task `status` and `priority` are TEXT columns with `CHECK` constraints, and foreign keys are switched on per connection with `PRAGMA foreign_keys = ON`.
Alternatives considered: Lookup tables for statuses and priorities: more joins for three fixed values that only change when the code changes. Deleting a property's tasks in Python code: easy to forget, and it would make the property module know about the tasks table.
Consequences: A landlord can own many properties and each property many tasks, and deleting a property cleanly removes its tasks. Adding a new status means changing both the `CHECK` constraint and `STATUSES` in `task.py`, and SQLite can only change a `CHECK` by rebuilding the table.

## 4. Test the logic layer directly against in-memory SQLite
Date: 2026-10-12
Status: Decided
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
