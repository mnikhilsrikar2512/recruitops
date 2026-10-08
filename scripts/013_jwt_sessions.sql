/* =====================================================================
   013_jwt_sessions.sql — Phase 3.1–3.4: JWT access + rotating refresh tokens.

   - A row in dbo.user_sessions is one sign-in (a refresh-token FAMILY):
     device, IP, last seen, absolute expiry, revocation + reason.
   - dbo.user_refresh_tokens holds every refresh token ever issued for a
     session, hashed. Each is single-use: using it marks it used and issues
     the next one. Presenting a USED token again = theft → the whole family
     (session) is revoked.
   - Access tokens are short-lived JWTs (sub, tenant_id, sid); every request
     still checks the session row, so revocation is immediate.
   - One-release cutover (D-08): every pre-JWT session is revoked here, so
     old opaque tokens answer 401 and everyone signs in again once.

   Idempotent; verifies itself.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.user_sessions', N'revoked_reason') IS NULL
  ALTER TABLE dbo.user_sessions ADD revoked_reason NVARCHAR(40) NULL;
IF COL_LENGTH(N'dbo.user_sessions', N'auth_kind') IS NULL
  ALTER TABLE dbo.user_sessions ADD auth_kind NVARCHAR(20) NOT NULL CONSTRAINT DF_user_sessions_auth_kind DEFAULT (N'opaque');
GO

IF OBJECT_ID(N'dbo.user_refresh_tokens', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.user_refresh_tokens (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_user_refresh_tokens PRIMARY KEY,
    session_id BIGINT NOT NULL CONSTRAINT FK_user_refresh_tokens_session REFERENCES dbo.user_sessions (id),
    token_hash NVARCHAR(128) NOT NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_user_refresh_tokens_created DEFAULT (SYSUTCDATETIME()),
    expires_at DATETIME2 NOT NULL,
    used_at DATETIME2 NULL,
    CONSTRAINT UQ_user_refresh_tokens_hash UNIQUE (token_hash)
  );
  CREATE INDEX IX_user_refresh_tokens_session ON dbo.user_refresh_tokens (session_id);
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_user_sessions_user_active' AND object_id = OBJECT_ID(N'dbo.user_sessions'))
  CREATE INDEX IX_user_sessions_user_active ON dbo.user_sessions (user_id, revoked_at);
GO

/* cutover: every pre-JWT (opaque) session ends now */
UPDATE dbo.user_sessions
SET revoked_at = SYSUTCDATETIME(), revoked_reason = N'jwt-cutover', updated_at = SYSUTCDATETIME()
WHERE revoked_at IS NULL AND auth_kind = N'opaque';
GO

IF EXISTS (SELECT 1 FROM dbo.user_sessions WHERE revoked_at IS NULL AND auth_kind = N'opaque')
  THROW 51013, N'013_jwt_sessions: opaque sessions remain active', 1;
GO
