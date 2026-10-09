/* =====================================================================
   029_setup_checklist.sql — Frontend cleanup F.1: the prototype
   onboarding wizard is replaced by a setup checklist on Home for a new
   company's admins. Each item is worked out from the company's own data
   (offices, team, clients, stage list, requisitions); the only stored
   state is when an admin hid the checklist.

   tenants.setup_checklist_dismissed_at — NULL = show it to admins
   Existing companies are marked dismissed: they are already set up.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.tenants', N'setup_checklist_dismissed_at') IS NULL
BEGIN
  ALTER TABLE dbo.tenants ADD setup_checklist_dismissed_at DATETIME2 NULL;
  EXEC (N'UPDATE dbo.tenants SET setup_checklist_dismissed_at = SYSUTCDATETIME();');
END
GO

IF COL_LENGTH(N'dbo.tenants', N'setup_checklist_dismissed_at') IS NULL
  THROW 51029, N'029: tenants.setup_checklist_dismissed_at missing', 1;
GO
