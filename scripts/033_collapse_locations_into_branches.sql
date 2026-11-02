-- 033: dbo.branches is the only office table (Phase 6 — least-privilege DB login).
--
-- dbo.locations was a parallel copy of dbo.branches with the same ids. Every
-- new office had to be mirrored with SET IDENTITY_INSERT, which needs ALTER
-- permission on the table, so the app could not run on a least-privilege
-- login. This migration:
--   1. refuses to run if the two tables disagree (a location with no branch of
--      the same id and company, or a row pointing at such a location);
--   2. copies location-only details (city, targets, head, ...) onto the branch
--      where the branch has none;
--   3. re-points every foreign key that referenced dbo.locations(id) at
--      dbo.branches(id), keeping each key's name;
--   4. drops the table and puts a read-only view of the same name and columns
--      over dbo.branches, so existing reads keep working.
-- All of 2–4 runs in one transaction. Idempotent: does nothing once
-- dbo.locations is a view.

SET XACT_ABORT ON;
GO

IF OBJECT_ID(N'dbo.locations', N'U') IS NOT NULL
BEGIN
    DECLARE @bad NVARCHAR(MAX) = N'';

    -- (1a) every location has a branch with the same id and company
    SELECT @bad = @bad + CONCAT(N' location ', l.id, N' (', l.code, N')')
    FROM dbo.locations AS l
    LEFT JOIN dbo.branches AS b ON b.id = l.id AND b.tenant_id = l.tenant_id
    WHERE b.id IS NULL;
    IF LEN(@bad) > 0
    BEGIN
        SET @bad = N'033 stopped: these offices exist in dbo.locations with no matching dbo.branches row (same id and company):' + @bad;
        THROW 51033, @bad, 1;
    END;

    -- (1b) every row that references dbo.locations points at an existing branch
    DECLARE @check NVARCHAR(MAX) = N'';
    SELECT @check = @check + N'
        IF EXISTS (SELECT 1 FROM ' + QUOTENAME(OBJECT_SCHEMA_NAME(fk.parent_object_id)) + N'.' + QUOTENAME(OBJECT_NAME(fk.parent_object_id))
            + N' AS c WHERE c.' + QUOTENAME(pc.name) + N' IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.branches AS b WHERE b.id = c.' + QUOTENAME(pc.name) + N'))'
            + N' SET @out = @out + N'' ' + OBJECT_NAME(fk.parent_object_id) + N'.' + pc.name + N''';'
    FROM sys.foreign_keys AS fk
    JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id = fk.object_id
    JOIN sys.columns AS pc ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
    WHERE fk.referenced_object_id = OBJECT_ID(N'dbo.locations');
    EXEC sp_executesql @check, N'@out NVARCHAR(MAX) OUTPUT', @out = @bad OUTPUT;
    IF LEN(@bad) > 0
    BEGIN
        SET @bad = N'033 stopped: these columns hold office ids that are not in dbo.branches:' + @bad;
        THROW 51033, @bad, 1;
    END;

    -- keys we can't re-point automatically (composite) stop the migration too
    IF EXISTS (
        SELECT 1 FROM sys.foreign_keys AS fk
        WHERE fk.referenced_object_id = OBJECT_ID(N'dbo.locations')
          AND (SELECT COUNT(*) FROM sys.foreign_key_columns AS k WHERE k.constraint_object_id = fk.object_id) <> 1)
        THROW 51033, N'033 stopped: a multi-column foreign key references dbo.locations; re-point it by hand.', 1;

    BEGIN TRANSACTION;

    -- (2) carry location-only details onto the branch, never overwriting it
    UPDATE b SET
        manager_user_id         = COALESCE(b.manager_user_id, l.location_head_user_id),
        address                 = COALESCE(b.address, l.address),
        city                    = COALESCE(b.city, l.city),
        state_name              = COALESCE(b.state_name, l.state_name),
        country_name            = COALESCE(b.country_name, l.country_name),
        branch_mapping_type     = COALESCE(b.branch_mapping_type, l.location_mapping_type),
        monthly_target_internal = COALESCE(b.monthly_target_internal, l.monthly_target_internal),
        monthly_target_external = COALESCE(b.monthly_target_external, l.monthly_target_external),
        weekly_target_internal  = COALESCE(b.weekly_target_internal, l.weekly_target_internal),
        weekly_target_external  = COALESCE(b.weekly_target_external, l.weekly_target_external)
    FROM dbo.branches AS b
    JOIN dbo.locations AS l ON l.id = b.id AND l.tenant_id = b.tenant_id;

    -- (3) re-point every foreign key at dbo.branches, same name, same column
    DECLARE @fks TABLE (fk_name SYSNAME, child_schema SYSNAME, child SYSNAME, col SYSNAME);
    INSERT INTO @fks
    SELECT fk.name, OBJECT_SCHEMA_NAME(fk.parent_object_id), OBJECT_NAME(fk.parent_object_id), pc.name
    FROM sys.foreign_keys AS fk
    JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id = fk.object_id
    JOIN sys.columns AS pc ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
    WHERE fk.referenced_object_id = OBJECT_ID(N'dbo.locations');

    DECLARE @sql NVARCHAR(MAX) = N'';
    SELECT @sql = @sql + N'ALTER TABLE ' + QUOTENAME(child_schema) + N'.' + QUOTENAME(child)
                       + N' DROP CONSTRAINT ' + QUOTENAME(fk_name) + N';' + CHAR(10)
    FROM @fks;
    SELECT @sql = @sql + N'ALTER TABLE ' + QUOTENAME(child_schema) + N'.' + QUOTENAME(child)
                       + N' WITH CHECK ADD CONSTRAINT ' + QUOTENAME(fk_name) + N' FOREIGN KEY (' + QUOTENAME(col)
                       + N') REFERENCES dbo.branches (id);' + CHAR(10)
    FROM @fks;
    EXEC sp_executesql @sql;

    -- (4) the table goes; a read-only view with the old shape takes its name
    DROP TABLE dbo.locations;
    EXEC (N'CREATE VIEW dbo.locations AS
        SELECT b.id, b.name, b.code, b.location, b.address, b.status,
               b.manager_user_id AS location_head_user_id,
               b.monthly_target_internal, b.monthly_target_external,
               b.weekly_target_internal, b.weekly_target_external,
               b.created_at, b.updated_at, b.city, b.state_name, b.country_name,
               b.branch_mapping_type AS location_mapping_type, b.tenant_id
        FROM dbo.branches AS b;');
    -- reads only: block writes through the view so nothing can delete a
    -- branch by deleting a "location"
    EXEC (N'CREATE TRIGGER dbo.trg_locations_read_only ON dbo.locations
        INSTEAD OF INSERT, UPDATE, DELETE AS
        BEGIN
            THROW 51034, N''dbo.locations is a read-only view over dbo.branches (033); write to dbo.branches.'', 1;
        END;');

    COMMIT TRANSACTION;
END;
GO

-- self-check
IF OBJECT_ID(N'dbo.locations', N'V') IS NULL
    RAISERROR('033 failed: dbo.locations is not a view', 16, 1);
IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE referenced_object_id = OBJECT_ID(N'dbo.locations'))
    RAISERROR('033 failed: a foreign key still references dbo.locations', 16, 1);
GO
