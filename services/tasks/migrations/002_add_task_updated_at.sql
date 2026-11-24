-- 002: record when a task last changed. This changes a table that already holds rows, without
-- dropping or recreating it: the column is added as NULL, existing tasks are backfilled from
-- their created_at, and only then is it made NOT NULL with a default for new tasks.

ALTER TABLE tasks ADD updated_at DATETIME2 NULL;
GO

UPDATE tasks SET updated_at = created_at WHERE updated_at IS NULL;

ALTER TABLE tasks ALTER COLUMN updated_at DATETIME2 NOT NULL;

ALTER TABLE tasks ADD CONSTRAINT DF_tasks_updated_at DEFAULT SYSUTCDATETIME() FOR updated_at;
