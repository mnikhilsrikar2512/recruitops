/* =====================================================================
   027_privacy.sql — Phase 5.3 (decisions D-5b, D-5c): privacy requests.

   privacy_requests — one row per request:
     company_export   all of the company's data as a zip (admin, immediate)
     company_delete   purge the company; a second admin approves (or a sole
                      admin re-confirms with two-step verification), then a
                      7-day cooling-off during which it can be cancelled
     candidate_export one candidate's data as a zip
     candidate_erase  wipe one candidate's personal data (pipeline counts
                      stay, anonymised)
     User ids here are plain numbers, not foreign keys: the row must outlive
     a company purge as the record that the purge happened.
   privacy_audit_hold — audit and legal-acceptance rows of a purged company,
     kept as JSON until hold_until (default 90 days), then deleted (PRD §12).
   tenants.purged_at, candidates.erased_at mark the end states.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.privacy_requests', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.privacy_requests (
    id BIGINT NOT NULL IDENTITY(1,1) CONSTRAINT PK_privacy_requests PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    request_type NVARCHAR(30) NOT NULL,
    candidate_id BIGINT NULL,
    status NVARCHAR(30) NOT NULL,
    reason NVARCHAR(1000) NULL,
    requested_by_user_id BIGINT NOT NULL,
    requested_by_name NVARCHAR(200) NULL,
    requested_at DATETIME2 NOT NULL CONSTRAINT DF_privacy_requests_requested DEFAULT (SYSUTCDATETIME()),
    approval_id BIGINT NULL,
    approved_by_user_id BIGINT NULL,
    approved_at DATETIME2 NULL,
    approval_method NVARCHAR(30) NULL,
    execute_after DATETIME2 NULL,
    cancelled_by_user_id BIGINT NULL,
    cancelled_at DATETIME2 NULL,
    started_at DATETIME2 NULL,
    completed_at DATETIME2 NULL,
    result_storage_key NVARCHAR(500) NULL,
    result_bytes BIGINT NULL,
    result_expires_at DATETIME2 NULL,
    summary_json NVARCHAR(MAX) NULL,
    error NVARCHAR(2000) NULL,
    CONSTRAINT CK_privacy_requests_type CHECK (request_type IN (N'company_export', N'company_delete', N'candidate_export', N'candidate_erase')),
    CONSTRAINT CK_privacy_requests_status CHECK (status IN (N'pending_approval', N'scheduled', N'processing', N'completed',
                                                          N'cancelled', N'rejected', N'failed'))
  );
  CREATE INDEX IX_privacy_requests_tenant ON dbo.privacy_requests (tenant_id, requested_at DESC);
  CREATE INDEX IX_privacy_requests_due ON dbo.privacy_requests (status, execute_after);
END;
GO

IF OBJECT_ID(N'dbo.privacy_audit_hold', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.privacy_audit_hold (
    id BIGINT NOT NULL IDENTITY(1,1) CONSTRAINT PK_privacy_audit_hold PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    privacy_request_id BIGINT NOT NULL,
    source_table NVARCHAR(64) NOT NULL,
    source_id BIGINT NOT NULL,
    row_json NVARCHAR(MAX) NOT NULL,
    held_at DATETIME2 NOT NULL CONSTRAINT DF_privacy_audit_hold_held DEFAULT (SYSUTCDATETIME()),
    hold_until DATETIME2 NOT NULL
  );
  CREATE INDEX IX_privacy_audit_hold_until ON dbo.privacy_audit_hold (hold_until);
END;
GO

IF COL_LENGTH(N'dbo.tenants', N'purged_at') IS NULL
  ALTER TABLE dbo.tenants ADD purged_at DATETIME2 NULL;
GO

IF COL_LENGTH(N'dbo.tenants', N'audit_hold_days') IS NULL
  ALTER TABLE dbo.tenants ADD audit_hold_days INT NOT NULL CONSTRAINT DF_tenants_audit_hold_days DEFAULT (90);
GO

IF COL_LENGTH(N'dbo.candidates', N'erased_at') IS NULL
  ALTER TABLE dbo.candidates ADD erased_at DATETIME2 NULL;
GO
