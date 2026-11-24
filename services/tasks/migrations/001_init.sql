-- 001: the tasks service's first schema. property_id is a plain id: the property lives in the
-- property service's database, so there is no foreign key across the seam. user_id is the owner,
-- copied from the login token, so listing and changing tasks never needs the property service.
-- Each CREATE checks first, so a database made before migrations existed is adopted as it is.

IF OBJECT_ID('tasks', 'U') IS NULL
CREATE TABLE tasks (
    task_id INT IDENTITY(1, 1) PRIMARY KEY,
    task_name NVARCHAR(80) NOT NULL,
    description NVARCHAR(1000),
    status NVARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'done')),
    priority NVARCHAR(20) NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'urgent')),
    property_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- one row that /health updates, to prove the service can write to its database
IF OBJECT_ID('health_probe', 'U') IS NULL
CREATE TABLE health_probe (
    probe_id INT PRIMARY KEY,
    checked_at DATETIME2 NOT NULL
);

IF NOT EXISTS (SELECT 1 FROM health_probe)
INSERT INTO health_probe (probe_id, checked_at) VALUES (1, SYSUTCDATETIME());
