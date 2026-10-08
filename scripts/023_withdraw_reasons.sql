/* =====================================================================
   023_withdraw_reasons.sql — Phase 4.11 (decision D-4.11): candidates can
   withdraw at any point, including after an offer is approved, and often
   without saying why.

   candidate_applications.withdrawal_reason holds a code from a short list
   (app/core/withdrawal.py); 'no_reason_given' is a valid answer, so a
   recruiter is never forced to invent one, and reports can still count
   why people drop out. A note is optional (required only for 'other').
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.candidate_applications', N'withdrawal_reason') IS NULL
  ALTER TABLE dbo.candidate_applications ADD withdrawal_reason NVARCHAR(40) NULL;
GO

IF COL_LENGTH(N'dbo.candidate_applications', N'withdrawn_at') IS NULL
  ALTER TABLE dbo.candidate_applications ADD withdrawn_at DATETIME2 NULL;
GO

/* Withdrawals recorded before this migration: reason unknown. */
UPDATE dbo.candidate_applications
SET withdrawal_reason = N'no_reason_given'
WHERE application_status = N'withdrawn' AND withdrawal_reason IS NULL;
GO
