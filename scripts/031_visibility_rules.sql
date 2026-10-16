/* =====================================================================
   031_visibility_rules.sql — field-level visibility rules for
   commercial/financial terms (requisitions.margin_percent/bill_rate,
   client_companies.default_bill_rate/markup_percent): which roles can
   see each field, company-wide (not per-branch) — and per COMPANY,
   since this is a multi-tenant product and one company's policy must
   never apply to another's (plan 2.3, app/core/tenancy.py).

   Replaces the visibility-rules.html stub that only re-listed roles —
   the visibility_rules.write permission already existed in the RBAC
   catalog with no table/endpoint behind it until now.

   dbo.visibility_rules: one row per (company, gated field).
   tenant_id NULL = the shared platform default (admin-only) every
   company starts from, same convention as dbo.roles' Admin template
   (010_tenants.sql) — a company's own saved choice is a tenant_id-
   scoped row that overrides the default for that company only, never
   written by anyone else. allowed_role_codes is a comma-separated list
   of role codes (no JSON column type needed for 4 small rows per
   company).

   Idempotent: safe to re-run, including after the table already exists
   (adds tenant_id + swaps the unique constraint on an older copy of
   this table that predates the tenant_id column).
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.requisitions', N'margin_percent') IS NULL
  ALTER TABLE dbo.requisitions ADD margin_percent DECIMAL(5, 2) NULL;
GO
IF COL_LENGTH(N'dbo.requisitions', N'bill_rate') IS NULL
  ALTER TABLE dbo.requisitions ADD bill_rate DECIMAL(18, 2) NULL;
GO

IF COL_LENGTH(N'dbo.client_companies', N'default_bill_rate') IS NULL
  ALTER TABLE dbo.client_companies ADD default_bill_rate DECIMAL(18, 2) NULL;
GO
IF COL_LENGTH(N'dbo.client_companies', N'markup_percent') IS NULL
  ALTER TABLE dbo.client_companies ADD markup_percent DECIMAL(5, 2) NULL;
GO

IF OBJECT_ID(N'dbo.visibility_rules', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.visibility_rules (
    id BIGINT NOT NULL IDENTITY(1,1) CONSTRAINT PK_visibility_rules PRIMARY KEY,
    tenant_id BIGINT NULL CONSTRAINT FK_visibility_rules_tenant REFERENCES dbo.tenants (id),
    entity NVARCHAR(30) NOT NULL,
    field_name NVARCHAR(100) NOT NULL,
    label NVARCHAR(150) NOT NULL,
    allowed_role_codes NVARCHAR(500) NOT NULL CONSTRAINT DF_visibility_rules_roles DEFAULT (N''),
    updated_by_user_id BIGINT NULL CONSTRAINT FK_visibility_rules_updated_by REFERENCES dbo.users (id),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_visibility_rules_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT UQ_visibility_rules_tenant_entity_field UNIQUE (tenant_id, entity, field_name)
  );
END;
GO

/* ---- tenant_id backfill for a copy of this table created before this
   column existed (same nullable-first idiom as 010_tenants.sql) ---- */
IF COL_LENGTH(N'dbo.visibility_rules', N'tenant_id') IS NULL
  ALTER TABLE dbo.visibility_rules ADD tenant_id BIGINT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_visibility_rules_tenant')
  ALTER TABLE dbo.visibility_rules ADD CONSTRAINT FK_visibility_rules_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
GO

IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_visibility_rules_entity_field')
  ALTER TABLE dbo.visibility_rules DROP CONSTRAINT UQ_visibility_rules_entity_field;
GO

IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_visibility_rules_tenant_entity_field')
  ALTER TABLE dbo.visibility_rules ADD CONSTRAINT UQ_visibility_rules_tenant_entity_field UNIQUE (tenant_id, entity, field_name);
GO

/* ---- seed: the shared platform default (tenant_id NULL), admin-only
   until a company admin opens Visibility Rules and saves their own
   company-scoped override ---- */
INSERT INTO dbo.visibility_rules (tenant_id, entity, field_name, label, allowed_role_codes)
SELECT NULL, v.entity, v.field_name, v.label, N'admin'
FROM (VALUES
  (N'requisition', N'margin_percent', N'Margin %'),
  (N'requisition', N'bill_rate', N'Bill Rate'),
  (N'client', N'default_bill_rate', N'Default Bill Rate'),
  (N'client', N'markup_percent', N'Markup %')
) AS v (entity, field_name, label)
WHERE NOT EXISTS (
  SELECT 1 FROM dbo.visibility_rules AS existing
  WHERE existing.tenant_id IS NULL AND existing.entity = v.entity AND existing.field_name = v.field_name
);
GO
