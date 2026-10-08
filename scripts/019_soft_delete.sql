/* =====================================================================
   019_soft_delete.sql — Phase 4.4 (decision D-07): archive instead of
   delete for candidates and clients. Hard delete is not reachable from the
   app.

   - dbo.candidate_archives: candidates are shared identity records
     (several companies can work the same person), so an archive belongs
     to ONE company: it hides the candidate from that company only. Rows
     are kept after a restore (restored_at set) as the archive history.
   - client_companies.archived_at / archived_by_user_id / archive_reason:
     a client belongs to one office, so a column is enough.
   - Permission codes candidate.delete.soft and client.delete.soft (one
     code governs archive AND restore — readiness Q17), granted once to the
     roles that already edit those records and manage requisitions (the
     manager shape). Admins adjust per role afterwards.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.candidate_archives', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.candidate_archives (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_candidate_archives PRIMARY KEY,
    tenant_id BIGINT NOT NULL CONSTRAINT FK_candidate_archives_tenant REFERENCES dbo.tenants (id),
    candidate_id BIGINT NOT NULL CONSTRAINT FK_candidate_archives_candidate REFERENCES dbo.candidates (id),
    archived_at DATETIME2 NOT NULL CONSTRAINT DF_candidate_archives_at DEFAULT (SYSUTCDATETIME()),
    archived_by_user_id BIGINT NOT NULL CONSTRAINT FK_candidate_archives_by REFERENCES dbo.users (id),
    archive_reason NVARCHAR(500) NOT NULL,
    restored_at DATETIME2 NULL,
    restored_by_user_id BIGINT NULL CONSTRAINT FK_candidate_archives_restored_by REFERENCES dbo.users (id)
  );
  CREATE UNIQUE INDEX UX_candidate_archives_open ON dbo.candidate_archives (tenant_id, candidate_id) WHERE restored_at IS NULL;
  CREATE INDEX IX_candidate_archives_candidate ON dbo.candidate_archives (candidate_id, restored_at);
END;
GO

IF COL_LENGTH(N'dbo.client_companies', N'archived_at') IS NULL
  ALTER TABLE dbo.client_companies ADD archived_at DATETIME2 NULL;
IF COL_LENGTH(N'dbo.client_companies', N'archived_by_user_id') IS NULL
  ALTER TABLE dbo.client_companies ADD archived_by_user_id BIGINT NULL
    CONSTRAINT FK_client_companies_archived_by REFERENCES dbo.users (id);
IF COL_LENGTH(N'dbo.client_companies', N'archive_reason') IS NULL
  ALTER TABLE dbo.client_companies ADD archive_reason NVARCHAR(500) NULL;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = N'candidate.delete.soft')
  INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
  VALUES (N'candidate.delete.soft', N'candidate', N'delete.soft', N'Archive and restore candidates', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = N'client.delete.soft')
  INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
  VALUES (N'client.delete.soft', N'client', N'delete.soft', N'Archive and restore clients', 1);
GO

/* one-time grants to manager-shaped roles */
INSERT INTO dbo.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM dbo.roles AS r
INNER JOIN dbo.permissions AS p ON p.code = N'candidate.delete.soft'
WHERE EXISTS (SELECT 1 FROM dbo.role_permissions rp JOIN dbo.permissions x ON x.id = rp.permission_id
              WHERE rp.role_id = r.id AND x.code = N'candidate.update')
  AND EXISTS (SELECT 1 FROM dbo.role_permissions rp JOIN dbo.permissions x ON x.id = rp.permission_id
              WHERE rp.role_id = r.id AND x.code = N'requisition.update')
  AND NOT EXISTS (SELECT 1 FROM dbo.role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id);

INSERT INTO dbo.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM dbo.roles AS r
INNER JOIN dbo.permissions AS p ON p.code = N'client.delete.soft'
WHERE EXISTS (SELECT 1 FROM dbo.role_permissions rp JOIN dbo.permissions x ON x.id = rp.permission_id
              WHERE rp.role_id = r.id AND x.code = N'client.update')
  AND EXISTS (SELECT 1 FROM dbo.role_permissions rp JOIN dbo.permissions x ON x.id = rp.permission_id
              WHERE rp.role_id = r.id AND x.code = N'requisition.update')
  AND NOT EXISTS (SELECT 1 FROM dbo.role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id);
GO
