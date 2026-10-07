/* =====================================================================
   021_file_pipeline.sql — Phase 4.1/4.2: storage keys, scan results,
   quarantine log, idempotent uploads.

   - candidate_documents: storage_key (tenant-prefixed object key),
     content_type, size_bytes, sha256, scan_status/scan_signature/scanned_at.
     Rows created before this migration have no storage_key and are never
     handed out as links.
   - upload_quarantine: every upload that failed the malware scan. The bytes
     stay under quarantine/ in storage; nothing links to them.
   - upload_idempotency: Idempotency-Key -> the document it created, so a
     retried upload returns the first result instead of a second copy.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.candidate_documents', N'storage_key') IS NULL
  ALTER TABLE dbo.candidate_documents ADD storage_key NVARCHAR(500) NULL;
IF COL_LENGTH(N'dbo.candidate_documents', N'content_type') IS NULL
  ALTER TABLE dbo.candidate_documents ADD content_type NVARCHAR(150) NULL;
IF COL_LENGTH(N'dbo.candidate_documents', N'size_bytes') IS NULL
  ALTER TABLE dbo.candidate_documents ADD size_bytes BIGINT NULL;
IF COL_LENGTH(N'dbo.candidate_documents', N'sha256') IS NULL
  ALTER TABLE dbo.candidate_documents ADD sha256 CHAR(64) NULL;
IF COL_LENGTH(N'dbo.candidate_documents', N'scan_status') IS NULL
  ALTER TABLE dbo.candidate_documents ADD scan_status NVARCHAR(20) NULL;
IF COL_LENGTH(N'dbo.candidate_documents', N'scan_signature') IS NULL
  ALTER TABLE dbo.candidate_documents ADD scan_signature NVARCHAR(200) NULL;
IF COL_LENGTH(N'dbo.candidate_documents', N'scanned_at') IS NULL
  ALTER TABLE dbo.candidate_documents ADD scanned_at DATETIME2 NULL;
GO

IF OBJECT_ID(N'dbo.upload_quarantine', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.upload_quarantine (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_upload_quarantine PRIMARY KEY,
    tenant_id BIGINT NULL CONSTRAINT FK_upload_quarantine_tenant REFERENCES dbo.tenants (id),
    uploaded_by_user_id BIGINT NULL CONSTRAINT FK_upload_quarantine_user REFERENCES dbo.users (id),
    entity_type NVARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    file_name NVARCHAR(255) NOT NULL,
    storage_key NVARCHAR(500) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    signature NVARCHAR(200) NULL,
    scanner NVARCHAR(30) NOT NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_upload_quarantine_created DEFAULT (SYSUTCDATETIME())
  );
  CREATE INDEX IX_upload_quarantine_tenant ON dbo.upload_quarantine (tenant_id, created_at);
END;
GO

IF OBJECT_ID(N'dbo.upload_idempotency', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.upload_idempotency (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_upload_idempotency PRIMARY KEY,
    user_id BIGINT NOT NULL CONSTRAINT FK_upload_idempotency_user REFERENCES dbo.users (id),
    idem_key NVARCHAR(100) NOT NULL,
    entity_type NVARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_upload_idempotency_created DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT UQ_upload_idempotency UNIQUE (user_id, idem_key)
  );
END;
GO
