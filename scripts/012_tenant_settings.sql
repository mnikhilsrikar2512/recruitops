/* =====================================================================
   012_tenant_settings.sql — Phase 2.3: company settings belong to a company.

   - dbo.company_entities (company profile, letterhead, logo): one primary
     profile PER COMPANY (tenant_id). Before this, every company read and
     edited the same single row.
   - dbo.master_data_values (business titles and other pick-lists):
     tenant_id NULL = a shared TEMPLATE value (never shown directly);
     a company's own list is its rows with its tenant_id, copied from the
     templates the first time the company opens a list, then editable.
     Codes are unique among templates and within each company.
   Portal accounts need no column: they hang off an office (branch_id).

   Idempotent; verifies itself.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.company_entities', N'tenant_id') IS NULL
  ALTER TABLE dbo.company_entities ADD tenant_id BIGINT NULL;
IF COL_LENGTH(N'dbo.master_data_values', N'tenant_id') IS NULL
  ALTER TABLE dbo.master_data_values ADD tenant_id BIGINT NULL;
GO

/* existing profiles belong to the default company (the one 010 created) */
UPDATE dbo.company_entities
SET tenant_id = COALESCE(
  (SELECT id FROM dbo.tenants WHERE slug = N'default'),
  (SELECT TOP 1 id FROM dbo.tenants ORDER BY id))
WHERE tenant_id IS NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_company_entities_tenant')
  ALTER TABLE dbo.company_entities ADD CONSTRAINT FK_company_entities_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_master_data_values_tenant')
  ALTER TABLE dbo.master_data_values ADD CONSTRAINT FK_master_data_values_tenant FOREIGN KEY (tenant_id) REFERENCES dbo.tenants (id);
GO

/* one primary profile per company */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_company_entities_tenant_primary' AND object_id = OBJECT_ID(N'dbo.company_entities'))
  AND NOT EXISTS (SELECT tenant_id FROM dbo.company_entities WHERE is_primary = 1 AND tenant_id IS NOT NULL GROUP BY tenant_id HAVING COUNT(*) > 1)
  CREATE UNIQUE INDEX UQ_company_entities_tenant_primary ON dbo.company_entities (tenant_id) WHERE is_primary = 1 AND tenant_id IS NOT NULL;
GO

/* value codes: unique among templates, and within a company */
IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_master_data_values_category_code' AND parent_object_id = OBJECT_ID(N'dbo.master_data_values'))
  ALTER TABLE dbo.master_data_values DROP CONSTRAINT UQ_master_data_values_category_code;
ELSE IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_master_data_values_category_code' AND object_id = OBJECT_ID(N'dbo.master_data_values'))
  DROP INDEX UQ_master_data_values_category_code ON dbo.master_data_values;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_master_data_values_template_code' AND object_id = OBJECT_ID(N'dbo.master_data_values'))
  CREATE UNIQUE INDEX UQ_master_data_values_template_code ON dbo.master_data_values (category_id, code) WHERE tenant_id IS NULL;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UQ_master_data_values_tenant_code' AND object_id = OBJECT_ID(N'dbo.master_data_values'))
  CREATE UNIQUE INDEX UQ_master_data_values_tenant_code ON dbo.master_data_values (tenant_id, category_id, code) WHERE tenant_id IS NOT NULL;
GO

/* verify */
IF EXISTS (SELECT 1 FROM dbo.company_entities WHERE tenant_id IS NULL)
  AND EXISTS (SELECT 1 FROM dbo.tenants)
  THROW 51012, N'012_tenant_settings: company profiles without a company remain', 1;
GO
