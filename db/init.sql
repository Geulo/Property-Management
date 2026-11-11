-- Creates one database and one login per service on the local SQL Server.
-- Run by the db-init service in docker-compose.yml on every `docker compose up`, so every
-- statement checks first and the script is safe to run again (idempotent).
-- $(PROPERTY_DB_PASSWORD) and $(TASKS_DB_PASSWORD) are sqlcmd variables, read from the
-- environment of the db-init container, which gets them from .env.

IF DB_ID('property') IS NULL CREATE DATABASE property;
GO
IF DB_ID('tasks') IS NULL CREATE DATABASE tasks;
GO

-- Logins live on the server. ALTER on a re-run keeps the password in step with .env.
IF SUSER_ID('property_user') IS NULL
    CREATE LOGIN property_user WITH PASSWORD = '$(PROPERTY_DB_PASSWORD)';
ELSE
    ALTER LOGIN property_user WITH PASSWORD = '$(PROPERTY_DB_PASSWORD)';
GO
IF SUSER_ID('tasks_user') IS NULL
    CREATE LOGIN tasks_user WITH PASSWORD = '$(TASKS_DB_PASSWORD)';
ELSE
    ALTER LOGIN tasks_user WITH PASSWORD = '$(TASKS_DB_PASSWORD)';
GO

-- Each login becomes a user in its own database only. It owns that database (it creates
-- its own tables at startup) and has no user, so no access, in the other one.
USE property;
IF USER_ID('property_user') IS NULL CREATE USER property_user FOR LOGIN property_user;
ALTER ROLE db_owner ADD MEMBER property_user;
GO
USE tasks;
IF USER_ID('tasks_user') IS NULL CREATE USER tasks_user FOR LOGIN tasks_user;
ALTER ROLE db_owner ADD MEMBER tasks_user;
GO
