-- 002: how many rental units a property has (a house = 1, a small building = several).
-- Data-preserving: existing properties are kept and get 1 unit, the default, in the same statement.
-- SQL Server fills a NOT NULL column with a DEFAULT for every existing row when the column is added.

ALTER TABLE properties ADD units INT NOT NULL
    CONSTRAINT DF_properties_units DEFAULT 1
    CONSTRAINT CK_properties_units CHECK (units BETWEEN 1 AND 500);
