/* =====================================================================
   015_mfa.sql — Phase 3.6: TOTP multi-factor authentication.
   - dbo.user_mfa: one authenticator per user. enabled_at NULL = enrolment
     started but not confirmed (the secret is not trusted until a code from
     the app has been verified).
   - dbo.user_mfa_recovery_codes: 10 single-use codes per enrolment, hashed.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.user_mfa', N'U') IS NULL
  CREATE TABLE dbo.user_mfa (
    user_id BIGINT NOT NULL CONSTRAINT PK_user_mfa PRIMARY KEY
      CONSTRAINT FK_user_mfa_user REFERENCES dbo.users (id),
    totp_secret NVARCHAR(64) NOT NULL,
    enabled_at DATETIME2 NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_user_mfa_created DEFAULT (SYSUTCDATETIME()),
    last_used_step BIGINT NULL
  );
GO

IF OBJECT_ID(N'dbo.user_mfa_recovery_codes', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.user_mfa_recovery_codes (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_user_mfa_recovery_codes PRIMARY KEY,
    user_id BIGINT NOT NULL CONSTRAINT FK_user_mfa_recovery_user REFERENCES dbo.users (id),
    code_hash NVARCHAR(128) NOT NULL,
    used_at DATETIME2 NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_user_mfa_recovery_created DEFAULT (SYSUTCDATETIME())
  );
  CREATE INDEX IX_user_mfa_recovery_user ON dbo.user_mfa_recovery_codes (user_id);
END;
GO
