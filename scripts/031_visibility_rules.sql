/* =====================================================================
   031_visibility_rules.sql — field-level visibility rules for
   commercial/financial terms (requisitions.margin_percent/bill_rate,
   client_companies.default_bill_rate/markup_percent): which roles can
   see each field, company-wide (not per-branch).

   Replaces the visibility-rules.html stub that only re-listed roles —
   the visibility_rules.write permission already existed in the RBAC
   catalog with no table/endpoint behind it until now.

   dbo.visibility_rules: one row per gated field, allowed_role_codes a
   comma-separated list of role codes (no JSON column type needed for
   4 small rows). Default seed is restrictive — admin only — until a
   company admin opens Visibility Rules and changes it.

   Idempotent: safe to re-run.
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
    entity NVARCHAR(30) NOT NULL,
    field_name NVARCHAR(100) NOT NULL,
    label NVARCHAR(150) NOT NULL,
    allowed_role_codes NVARCHAR(500) NOT NULL CONSTRAINT DF_visibility_rules_roles DEFAULT (N''),
    updated_by_user_id BIGINT NULL CONSTRAINT FK_visibility_rules_updated_by REFERENCES dbo.users (id),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_visibility_rules_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT UQ_visibility_rules_entity_field UNIQUE (entity, field_name)
  );
END;
GO

INSERT INTO dbo.visibility_rules (entity, field_name, label, allowed_role_codes)
SELECT v.entity, v.field_name, v.label, N'admin'
FROM (VALUES
  (N'requisition', N'margin_percent', N'Margin %'),
  (N'requisition', N'bill_rate', N'Bill Rate'),
  (N'client', N'default_bill_rate', N'Default Bill Rate'),
  (N'client', N'markup_percent', N'Markup %')
) AS v (entity, field_name, label)
WHERE NOT EXISTS (
  SELECT 1 FROM dbo.visibility_rules AS existing
  WHERE existing.entity = v.entity AND existing.field_name = v.field_name
);
GO
