/* =====================================================================
   018_row_versions.sql — Phase 4.3: optimistic locking.
   A version number on candidates, requisitions and applications. Every
   write bumps it (version = version + 1 in each UPDATE); an edit that
   carries the version it was loaded with is refused with 409 when the row
   has moved on (app/repositories/versioning.py).
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.candidates', N'version') IS NULL
  ALTER TABLE dbo.candidates ADD version INT NOT NULL CONSTRAINT DF_candidates_version DEFAULT (1);
IF COL_LENGTH(N'dbo.requisitions', N'version') IS NULL
  ALTER TABLE dbo.requisitions ADD version INT NOT NULL CONSTRAINT DF_requisitions_version DEFAULT (1);
IF COL_LENGTH(N'dbo.candidate_applications', N'version') IS NULL
  ALTER TABLE dbo.candidate_applications ADD version INT NOT NULL CONSTRAINT DF_candidate_applications_version DEFAULT (1);
GO
