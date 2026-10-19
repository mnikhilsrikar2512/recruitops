-- 009: scope branch/location office codes per tenant, not globally.
--
-- dbo.branches.code and dbo.locations.code were each unique across the
-- WHOLE database (UQ_branches_code, UQ_locations_code), so two different
-- companies could never both use a code like 'HO' or 'HYD01' for their
-- head office -- a hard blocker for a product meant to serve many
-- companies. app/services/provisioning.py already works around this by
-- generating tenant-suffixed codes (f"HO{tenant_id}"), and
-- tests/test_company_isolation_db.py asserts the intended behavior
-- directly ("Same office code as company A's first office is allowed
-- (per-company codes)") -- which the old constraint made impossible.
--
-- Safe to run against an existing database: a composite (tenant_id, code)
-- unique index is always satisfied by data that already passed a
-- single-column unique index on code alone, so no cleanup is needed first.
-- Idempotent -- safe to re-run.
--
-- Each old unique may have been created as a bare CREATE UNIQUE INDEX or
-- as an ALTER TABLE ... ADD CONSTRAINT ... UNIQUE (a constraint owns its
-- backing index and refuses a plain DROP INDEX on it -- "is being used
-- for UNIQUE KEY constraint enforcement"), so check sys.key_constraints
-- first and use the matching drop for whichever form is actually there.

IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'UQ_branches_code' AND parent_object_id = OBJECT_ID('dbo.branches'))
    ALTER TABLE dbo.branches DROP CONSTRAINT [UQ_branches_code];
ELSE IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_branches_code' AND object_id = OBJECT_ID('dbo.branches'))
    DROP INDEX [UQ_branches_code] ON dbo.branches;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_branches_tenant_code' AND object_id = OBJECT_ID('dbo.branches'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_branches_tenant_code] ON dbo.branches (tenant_id, code);

IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'UQ_locations_code' AND parent_object_id = OBJECT_ID('dbo.locations'))
    ALTER TABLE dbo.locations DROP CONSTRAINT [UQ_locations_code];
ELSE IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_locations_code' AND object_id = OBJECT_ID('dbo.locations'))
    DROP INDEX [UQ_locations_code] ON dbo.locations;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_locations_tenant_code' AND object_id = OBJECT_ID('dbo.locations'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_locations_tenant_code] ON dbo.locations (tenant_id, code);

-- Verify: both old global indexes gone, both new per-tenant ones present.
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name IN ('UQ_branches_code', 'UQ_locations_code'))
    RAISERROR('009 failed: an old global code index is still present', 16, 1);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_branches_tenant_code' AND object_id = OBJECT_ID('dbo.branches'))
    RAISERROR('009 failed: UQ_branches_tenant_code was not created', 16, 1);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_locations_tenant_code' AND object_id = OBJECT_ID('dbo.locations'))
    RAISERROR('009 failed: UQ_locations_tenant_code was not created', 16, 1);
PRINT '009 OK: branch/location codes are now unique per tenant, not globally';
