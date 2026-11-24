-- 001: the property service's first schema (Assignment 1's users and properties, ported to SQL Server).
-- Each CREATE checks first, so a database made before migrations existed (by the old schema.py)
-- is adopted as it is instead of failing.

IF OBJECT_ID('users', 'U') IS NULL
CREATE TABLE users (
    user_id INT IDENTITY(1, 1) PRIMARY KEY,
    username NVARCHAR(100) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    password_hash NVARCHAR(100) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

IF OBJECT_ID('properties', 'U') IS NULL
CREATE TABLE properties (
    property_id INT IDENTITY(1, 1) PRIMARY KEY,
    property_name NVARCHAR(50) NOT NULL,
    address NVARCHAR(255) NOT NULL,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
);

-- one row that /health updates, to prove the service can write to its database
IF OBJECT_ID('health_probe', 'U') IS NULL
CREATE TABLE health_probe (
    probe_id INT PRIMARY KEY,
    checked_at DATETIME2 NOT NULL
);

IF NOT EXISTS (SELECT 1 FROM health_probe)
INSERT INTO health_probe (probe_id, checked_at) VALUES (1, SYSUTCDATETIME());
