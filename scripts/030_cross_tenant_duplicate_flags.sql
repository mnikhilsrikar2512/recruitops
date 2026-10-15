/* =====================================================================
   030_cross_tenant_duplicate_flags.sql — Lightweight cross-company
   duplicate-submission flag.

   Problem: two separate RecruitOps companies (tenants) can both be
   working the same end client and submit the same candidate to them at
   the same time. Each company's candidate data is intentionally walled
   off from every other company's (that is the whole point of tenancy),
   so we cannot show company B the record company A already submitted.
   What we CAN safely do is tell company B "someone else already
   submitted a profile that looks like this one, to a client with this
   name, recently" — without ever naming the other company or handing
   over any of its data.

   dbo.cross_tenant_submission_signals stores only salted hashes of the
   candidate's email/phone (never the raw value), a normalized client
   name, and the tenant that submitted — enough to flag a probable
   overlap, not enough to reconstruct who the candidate is. One row is
   written every time a candidate is finalized into a requisition
   (services/candidates.py: finalize_candidate_service); new writes are
   checked against existing rows from OTHER tenants with a matching
   hash and a matching normalized client name from the last 90 days.

   This table is intentionally NOT exported with a company's data (it
   is not "their" data — see tenant_data.EXPORT_SKIP) and IS purged by
   tenant_id when a company is purged (027). Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.cross_tenant_submission_signals', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.cross_tenant_submission_signals (
    id BIGINT NOT NULL IDENTITY(1,1),
    tenant_id BIGINT NOT NULL,
    candidate_id BIGINT NOT NULL,
    requisition_id BIGINT NULL,
    application_id BIGINT NULL,
    email_hash CHAR(64) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
    phone_hash CHAR(64) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
    client_name_norm NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT PK_cross_tenant_submission_signals PRIMARY KEY CLUSTERED (id)
  );
END
GO

/* Lookup path: "has anyone else submitted this email/phone to a
   client with this name recently?" — one index per hash column, both
   leading with the client name so a scan never has to cross clients. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_cross_tenant_signals_email' AND object_id = OBJECT_ID(N'dbo.cross_tenant_submission_signals'))
  CREATE NONCLUSTERED INDEX IX_cross_tenant_signals_email ON dbo.cross_tenant_submission_signals (client_name_norm, email_hash, created_at) WHERE email_hash IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_cross_tenant_signals_phone' AND object_id = OBJECT_ID(N'dbo.cross_tenant_submission_signals'))
  CREATE NONCLUSTERED INDEX IX_cross_tenant_signals_phone ON dbo.cross_tenant_submission_signals (client_name_norm, phone_hash, created_at) WHERE phone_hash IS NOT NULL;
GO

/* Purge path (027): remove a company's own rows by tenant_id. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_cross_tenant_signals_tenant' AND object_id = OBJECT_ID(N'dbo.cross_tenant_submission_signals'))
  CREATE NONCLUSTERED INDEX IX_cross_tenant_signals_tenant ON dbo.cross_tenant_submission_signals (tenant_id);
GO

IF OBJECT_ID(N'dbo.cross_tenant_submission_signals', N'U') IS NULL
  THROW 51030, N'030: dbo.cross_tenant_submission_signals missing', 1;
GO
