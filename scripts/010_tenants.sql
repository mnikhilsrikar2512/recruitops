/* =====================================================================
   010_tenants.sql — Phase 2.1: companies (tenants) as the isolation root.

   Decisions (docs/decisions-2026-10-06.md):
   - A tenant is a COMPANY. It owns a head office and branches in
     different locations; its admin manages all of them (I-5).
   - Every office in an existing database belongs to ONE company, so the
     backfill puts all existing rows under a single default tenant.
   - Login stays email-only; the email identifies the company (D-02).

   Shape:
   - dbo.tenants (id, slug UNIQUE, display_name, status)
   - tenant_id NOT NULL on dbo.branches, dbo.locations (offices) and
     dbo.users; tenant_id NULL on dbo.roles means a system role shared by
     all companies (the Admin template, read-only to companies); every
     other role belongs to exactly one company.
   - Office codes are unique per company, not globally.
   Everything else (clients, requisitions, candidates' applications,
   approvals, meetings, …) already hangs off an office (branch_id /
   location_id), so its tenant is derived through the office; the API
   filters every list and direct-id read by the caller's tenant.

   Idempotent: safe to re-run. Verifies itself at the end.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.tenants', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.tenants (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_tenants PRIMARY KEY,
    slug NVARCHAR(63) NOT NULL,
    display_name NVARCHAR(200) NOT NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_tenants_status DEFAULT (N'active'),
    created_at DATETIME2 NOT NULL CONSTRAINT DF_tenants_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_tenants_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT UQ_tenants_slug UNIQUE (slug),
    CONSTRAINT CK_tenants_status CHECK (status IN (N'pending', N'active', N'suspended', N'archived'))
  );
END;
GO

/* ---- columns (nullable first so existing rows can be backfilled) ---- */
IF COL_LENGTH(N'dbo.branches', N'tenant_id') IS NULL ALTER TABLE dbo.branches ADD tenant_id BIGINT NULL;
IF COL_LENGTH(N'dbo.locations', N'tenant_id') IS NULL ALTER TABLE dbo.locations ADD tenant_id BIGINT NULL;
IF COL_LENGTH(N'dbo.users', N'tenant_id') IS NULL ALTER TABLE dbo.users ADD tenant_id BIGINT NULL;
IF COL_LENGTH(N'dbo.roles', N'tenant_id') IS NULL ALTER TABLE dbo.roles ADD tenant_id BIGINT NULL;
GO

/* ---- backfill: everything that exists today is one company ---- */
IF EXISTS (SELECT 1 FROM dbo.branches WHERE tenant_id IS NULL)
   OR EXISTS (SELECT 1 FROM dbo.locations WHERE tenant_id IS NULL)
   OR EXISTS (SELECT 1 FROM dbo.users WHERE tenant_id IS NULL)
BEGIN
  IF NOT EXISTS (SELECT 1 FROM dbo.tenants WHERE slug = N'default')
    INSERT INTO dbo.tenants (slug, display_name, status) VALUES (N'default', N'Default Company', N'active');

  DECLARE @default_tenant BIGINT = (SELECT id FROM dbo.tenants WHERE slug = N'default');

  UPDATE dbo.branches SET tenant_id = @default_tenant WHERE tenant_id IS NULL;
  /* locations mirror branches by id; fall back to the default company */
  UPDATE l SET l.tenant_id = COALESCE(b.tenant_id, @default_tenant)
  FROM dbo.locations AS l LEFT JOIN dbo.branches AS b ON b.id = l.id
  WHERE l.tenant_id IS NULL;
  /* users: company of their primary office, else the default company */
  UPDATE u SET u.tenant_id = COALESCE(pb.tenant_id, ul.tenant_id, @default_tenant)
  FROM dbo.users AS u
  OUTER APPLY (
    SELECT TOP 1 b.tenant_id FROM dbo.user_branch_roles AS ubr
    JOIN dbo.branches AS b ON b.id = ubr.branch_id
    WHERE ubr.user_id = u.id AND ubr.is_primary = 1
  ) AS pb
  LEFT JOIN dbo.locations AS ul ON ul.id = u.location_id
  WHERE u.tenant_id IS NULL;
  /* existing custom roles belong to that company; only the Admin
     template stays shared (tenant_id NULL = system role, read-only) */
  UPDATE dbo.roles SET tenant_id = @default_tenant WHERE tenant_id IS NULL AND code <> N'admin';
END;
GO

/* ---- constraints ---- */
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'dbo.branches') AND name = N'tenant_id' AND is_nullable = 0)
  ALTER TABLE dbo.branches ALTER COLUMN tenant_id BIGINT NOT NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'dbo.locations') AND name = N'tenant_id' AND is_nullable = 0)
  ALTER TABLE dbo.locations ALTER COLUMN tenant_id BIGINT NOT NULL;
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'dbo.users') AND name = N'tenant_id' AND is_nullable = 0)
BEGIN
  /* an index on email depends on nothing here; tenant_id can tighten safely */
  ALTER TABLE dbo.users ALTER COLUMN tenant_id BIGINT NOT NULL;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_branches_tenant')
  ALTER TABLE dbo.branches ADD CONSTRAINT FK_branches_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_locations_tenant')
  ALTER TABLE dbo.locations ADD CONSTRAINT FK_locations_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_users_tenant')
  ALTER TABLE dbo.users ADD CONSTRAINT FK_users_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_roles_tenant')
  ALTER TABLE dbo.roles ADD CONSTRAINT FK_roles_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_branches_tenant' AND object_id = OBJECT_ID(N'dbo.branches'))
  CREATE INDEX IX_branches_tenant ON dbo.branches (tenant_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_users_tenant' AND object_id = OBJECT_ID(N'dbo.users'))
  CREATE INDEX IX_users_tenant ON dbo.users (tenant_id);
GO

/* Older databases enforce these as UNIQUE constraints, newer ones as
   unique indexes; drop whichever exists. */
/* Office codes unique per company (two companies may both have "HYD"). */
IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_branches_code' AND parent_object_id = OBJECT_ID(N'dbo.branches'))
  ALTER TABLE dbo.branches DROP CONSTRAINT UQ_branches_code;
ELSE IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_branches_code' AND object_id = OBJECT_ID(N'dbo.branches'))
  DROP INDEX UQ_branches_code ON dbo.branches;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_branches_tenant_code' AND object_id = OBJECT_ID(N'dbo.branches'))
  CREATE UNIQUE INDEX UQ_branches_tenant_code ON dbo.branches (tenant_id, code);
IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_locations_code' AND parent_object_id = OBJECT_ID(N'dbo.locations'))
  ALTER TABLE dbo.locations DROP CONSTRAINT UQ_locations_code;
ELSE IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_locations_code' AND object_id = OBJECT_ID(N'dbo.locations'))
  DROP INDEX UQ_locations_code ON dbo.locations;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_locations_tenant_code' AND object_id = OBJECT_ID(N'dbo.locations'))
  CREATE UNIQUE INDEX UQ_locations_tenant_code ON dbo.locations (tenant_id, code);
GO

/* Role codes: system roles (tenant_id NULL) are unique among themselves;
   company roles are unique within their company. The service also refuses a
   company role whose code equals a system role's. */
IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_roles_code' AND parent_object_id = OBJECT_ID(N'dbo.roles'))
  ALTER TABLE dbo.roles DROP CONSTRAINT UQ_roles_code;
ELSE IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_roles_code' AND object_id = OBJECT_ID(N'dbo.roles'))
  DROP INDEX UQ_roles_code ON dbo.roles;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_roles_system_code' AND object_id = OBJECT_ID(N'dbo.roles'))
  CREATE UNIQUE INDEX UQ_roles_system_code ON dbo.roles (code) WHERE tenant_id IS NULL;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_roles_tenant_code' AND object_id = OBJECT_ID(N'dbo.roles'))
  CREATE UNIQUE INDEX UQ_roles_tenant_code ON dbo.roles (tenant_id, code) WHERE tenant_id IS NOT NULL;
GO

/* ---- verify ---- */
IF EXISTS (SELECT 1 FROM dbo.branches WHERE tenant_id IS NULL)
   OR EXISTS (SELECT 1 FROM dbo.users WHERE tenant_id IS NULL)
   OR EXISTS (SELECT 1 FROM dbo.locations WHERE tenant_id IS NULL)
  THROW 51010, N'010_tenants: rows without tenant_id remain', 1;
GO
