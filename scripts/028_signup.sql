/* =====================================================================
   028_signup.sql — Phase 5.2 (decision D-01 revised): self-serve signup
   and ops provisioning.

   A company signs itself up: company + head office + first Admin are
   created with tenants.status = 'pending'. The admin verifies their email
   (a 'signup-verify' token in password_reset_tokens, 24 h), then sets up
   two-step verification; only then does the company become 'active'
   (app/services/tenants.activate_tenant, D-09).

   users.email_verified_at  — when the address was proven (signup link or
                               an ops-issued password setup)
   tenants.onboarding        — 'self_serve' | 'ops' | NULL (existing companies)
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.users', N'email_verified_at') IS NULL
  ALTER TABLE dbo.users ADD email_verified_at DATETIME2 NULL;
GO

IF COL_LENGTH(N'dbo.tenants', N'onboarding') IS NULL
  ALTER TABLE dbo.tenants ADD onboarding NVARCHAR(20) NULL;
GO
