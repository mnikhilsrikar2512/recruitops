/* =====================================================================
   026_legal.sql — Phase 5.1 (decision I-7a): versioned Terms of Service,
   Privacy Policy and Data Processing Addendum, and who accepted which
   version when.

   legal_documents   — platform-wide texts. One active version per type.
                       is_placeholder = 1 marks text that is NOT legal text
                       yet; production refuses to start while any active
                       document is a placeholder (app/services/legal.py).
                       New versions are published by platform ops with
                       backend/scripts/publish_legal.py.
   legal_acceptances — one row per acceptance: the user, their company,
                       the exact version, when, and from where. Terms and
                       Privacy are accepted by each user; the DPA once per
                       company by an admin on the company's behalf.

   Seeds version 1 of each document as a clearly marked placeholder.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.legal_documents', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.legal_documents (
    id BIGINT NOT NULL IDENTITY(1,1) CONSTRAINT PK_legal_documents PRIMARY KEY,
    doc_type NVARCHAR(20) NOT NULL,
    version INT NOT NULL,
    title NVARCHAR(200) NOT NULL,
    body NVARCHAR(MAX) NOT NULL,
    is_placeholder BIT NOT NULL CONSTRAINT DF_legal_documents_placeholder DEFAULT (0),
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_legal_documents_status DEFAULT (N'active'),
    effective_at DATETIME2 NOT NULL CONSTRAINT DF_legal_documents_effective DEFAULT (SYSUTCDATETIME()),
    published_by NVARCHAR(200) NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_legal_documents_created DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT CK_legal_documents_type CHECK (doc_type IN (N'tos', N'privacy', N'dpa')),
    CONSTRAINT CK_legal_documents_status CHECK (status IN (N'active', N'superseded')),
    CONSTRAINT UQ_legal_documents_version UNIQUE (doc_type, version)
  );
  CREATE UNIQUE INDEX UX_legal_documents_active ON dbo.legal_documents (doc_type) WHERE status = N'active';
END;
GO

IF OBJECT_ID(N'dbo.legal_acceptances', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.legal_acceptances (
    id BIGINT NOT NULL IDENTITY(1,1) CONSTRAINT PK_legal_acceptances PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL CONSTRAINT FK_legal_acceptances_document REFERENCES dbo.legal_documents (id),
    doc_type NVARCHAR(20) NOT NULL,
    version INT NOT NULL,
    on_behalf_of_company BIT NOT NULL CONSTRAINT DF_legal_acceptances_company DEFAULT (0),
    accepted_at DATETIME2 NOT NULL CONSTRAINT DF_legal_acceptances_at DEFAULT (SYSUTCDATETIME()),
    ip_address NVARCHAR(64) NULL,
    user_agent NVARCHAR(400) NULL
  );
  CREATE INDEX IX_legal_acceptances_user ON dbo.legal_acceptances (user_id, doc_type, version);
  CREATE INDEX IX_legal_acceptances_tenant ON dbo.legal_acceptances (tenant_id, doc_type, version);
END;
GO

DECLARE @draft NVARCHAR(400) = N'DRAFT — NOT LEGAL TEXT. This placeholder stands in until counsel supplies the final wording. It has no legal effect.';

IF NOT EXISTS (SELECT 1 FROM dbo.legal_documents WHERE doc_type = N'tos')
  INSERT INTO dbo.legal_documents (doc_type, version, title, body, is_placeholder, published_by)
  VALUES (N'tos', 1, N'Terms of Service', @draft + NCHAR(10) + NCHAR(10)
    + N'## What this document will cover' + NCHAR(10)
    + N'- Who may use RecruitOps and on whose behalf' + NCHAR(10)
    + N'- Acceptable use, accounts and security' + NCHAR(10)
    + N'- Fees, suspension and termination' + NCHAR(10)
    + N'- Liability, governing law and changes to these terms', 1, N'026_legal.sql');

IF NOT EXISTS (SELECT 1 FROM dbo.legal_documents WHERE doc_type = N'privacy')
  INSERT INTO dbo.legal_documents (doc_type, version, title, body, is_placeholder, published_by)
  VALUES (N'privacy', 1, N'Privacy Policy', @draft + NCHAR(10) + NCHAR(10)
    + N'## What this document will cover' + NCHAR(10)
    + N'- What personal data is held (users, candidates, client contacts) and why' + NCHAR(10)
    + N'- Automated tools: candidates may be scored by an automated tool; scores are advisory and never the sole reason for a rejection' + NCHAR(10)
    + N'- Where data is stored, sub-processors, and retention' + NCHAR(10)
    + N'- Export and deletion requests; audit records are kept for a limited legal-hold period (default 90 days) after a deletion' + NCHAR(10)
    + N'- Contact for privacy questions', 1, N'026_legal.sql');

IF NOT EXISTS (SELECT 1 FROM dbo.legal_documents WHERE doc_type = N'dpa')
  INSERT INTO dbo.legal_documents (doc_type, version, title, body, is_placeholder, published_by)
  VALUES (N'dpa', 1, N'Data Processing Addendum', @draft + NCHAR(10) + NCHAR(10)
    + N'## What this document will cover' + NCHAR(10)
    + N'- Roles: the customer company as controller, RecruitOps as processor' + NCHAR(10)
    + N'- Processing instructions, confidentiality and security measures' + NCHAR(10)
    + N'- Sub-processors (hosting provider and region) and how changes are notified' + NCHAR(10)
    + N'- Breach notification, assistance with data-subject requests, deletion at end of contract', 1, N'026_legal.sql');
GO
