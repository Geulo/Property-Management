-- Creates the one database user a service logs in with, inside that service's own Azure SQL database.
-- Run by infra/setup.sh once per database, connected as the SQL admin to that database.
-- $(APP_USER) and $(APP_PASSWORD) are sqlcmd variables; setup.sh passes them as environment variables
-- so the password never appears on a command line.
--
-- This is a "contained" user: it has its own password and exists only in this database. It has no
-- server login, so it cannot even connect to the other service's database (the database-per-service rule).
-- Locally, db/init.sql does the same job with server logins on the SQL Server container.

IF USER_ID('$(APP_USER)') IS NULL
    CREATE USER [$(APP_USER)] WITH PASSWORD = '$(APP_PASSWORD)';
ELSE
    -- re-running setup.sh generates a new password, so keep the user in step with it
    ALTER USER [$(APP_USER)] WITH PASSWORD = '$(APP_PASSWORD)';
GO

-- db_owner on this database only: the service creates and migrates its own tables at startup.
ALTER ROLE db_owner ADD MEMBER [$(APP_USER)];
GO
