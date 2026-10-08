/* =====================================================================
   025_client_stage_lists.sql — Phase 4.10 (decision D-4.10): one company
   works for many clients, and each client runs its own hiring stages.

   "Per client only": a client has ONE stage list; every requisition for
   that client uses it. Internal hiring (no client) and clients that have
   not set a list yet use the company's default list. With neither, the
   platform's built-in stages apply (today's behaviour).

   pipeline_templates gains:
     tenant_id          — the company that owns the list (backfilled from
                          its office); tenancy is now "tenant".
     client_company_id  — the client the list belongs to; NULL with
                          stage_scope = 'company' is the company default.
   One active list per client, one active default per company.

   The requisition keeps a pointer (requisitions.pipeline_template_id) that
   the app sets from the client's list at creation and re-points when a
   client or company list is first created, so the existing SQL resolver
   (dbo.fn_application_stage_bucket) keeps working unchanged.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.pipeline_templates', N'tenant_id') IS NULL
  ALTER TABLE dbo.pipeline_templates ADD tenant_id BIGINT NULL;
GO

IF COL_LENGTH(N'dbo.pipeline_templates', N'client_company_id') IS NULL
  ALTER TABLE dbo.pipeline_templates ADD client_company_id BIGINT NULL
    CONSTRAINT FK_pipeline_templates_client_company REFERENCES dbo.client_companies (id);
GO

IF COL_LENGTH(N'dbo.pipeline_templates', N'version') IS NULL
  ALTER TABLE dbo.pipeline_templates ADD version INT NOT NULL
    CONSTRAINT DF_pipeline_templates_version DEFAULT (1);
GO

UPDATE t SET tenant_id = b.tenant_id
FROM dbo.pipeline_templates AS t
INNER JOIN dbo.branches AS b ON b.id = t.location_id
WHERE t.tenant_id IS NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UX_pipeline_templates_client')
  CREATE UNIQUE INDEX UX_pipeline_templates_client ON dbo.pipeline_templates (client_company_id)
    WHERE client_company_id IS NOT NULL AND status = N'active';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UX_pipeline_templates_company_default')
  CREATE UNIQUE INDEX UX_pipeline_templates_company_default ON dbo.pipeline_templates (tenant_id)
    WHERE client_company_id IS NULL AND stage_scope = N'company' AND status = N'active';
GO
