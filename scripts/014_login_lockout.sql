/* =====================================================================
   014_login_lockout.sql — Phase 3.5: lockout/backoff after repeated failed
   sign-ins. After LOGIN_LOCKOUT_THRESHOLD (5) wrong passwords in a row the
   account refuses sign-in for LOGIN_LOCKOUT_MINUTES (15); a correct sign-in
   resets the counter. Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.users', N'failed_login_count') IS NULL
  ALTER TABLE dbo.users ADD failed_login_count INT NOT NULL CONSTRAINT DF_users_failed_login_count DEFAULT (0);
IF COL_LENGTH(N'dbo.users', N'locked_until') IS NULL
  ALTER TABLE dbo.users ADD locked_until DATETIME2 NULL;
GO
