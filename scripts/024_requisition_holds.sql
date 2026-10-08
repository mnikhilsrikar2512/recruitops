/* =====================================================================
   024_requisition_holds.sql — Phase 4.12 (decision D-4.12): a client can
   put a requisition on hold for many reasons.

   While a requisition is on hold its candidates are frozen where they are:
   no stage moves forward or back, no new candidates, offers or interviews.
   Withdrawing or rejecting a candidate is still allowed. The clocks pause:
   on resume the hold's days are added to requisitions.hold_days_total
   (time-to-fill subtracts them) and the target close date moves out by the
   same number of days.

   requisition_holds keeps every hold (reason code, note, who/when, expected
   resume date, who/when resumed). At most one open hold per requisition.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.requisition_holds', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.requisition_holds (
    id BIGINT NOT NULL IDENTITY(1,1) CONSTRAINT PK_requisition_holds PRIMARY KEY,
    requisition_id BIGINT NOT NULL CONSTRAINT FK_requisition_holds_requisition REFERENCES dbo.requisitions (id),
    reason_code NVARCHAR(40) NOT NULL,
    reason_note NVARCHAR(1000) NULL,
    previous_status NVARCHAR(30) NOT NULL,
    expected_resume_date DATE NULL,
    held_by_user_id BIGINT NOT NULL,
    held_at DATETIME2 NOT NULL CONSTRAINT DF_requisition_holds_held_at DEFAULT (SYSUTCDATETIME()),
    resumed_by_user_id BIGINT NULL,
    resumed_at DATETIME2 NULL,
    resume_note NVARCHAR(1000) NULL,
    hold_days INT NULL
  );
  CREATE UNIQUE INDEX UX_requisition_holds_open ON dbo.requisition_holds (requisition_id) WHERE resumed_at IS NULL;
END;
GO

IF COL_LENGTH(N'dbo.requisitions', N'hold_days_total') IS NULL
  ALTER TABLE dbo.requisitions ADD hold_days_total INT NOT NULL
    CONSTRAINT DF_requisitions_hold_days_total DEFAULT (0);
GO

/* Requisitions already marked on-hold before this migration get an open
   hold row so they can be resumed through the new flow. */
INSERT INTO dbo.requisition_holds (requisition_id, reason_code, reason_note, previous_status, held_by_user_id, held_at)
SELECT r.id, N'other', N'On hold before hold tracking existed', N'open', r.owner_user_id, r.updated_at
FROM dbo.requisitions AS r
WHERE r.status = N'on-hold'
  AND NOT EXISTS (SELECT 1 FROM dbo.requisition_holds AS h WHERE h.requisition_id = r.id AND h.resumed_at IS NULL);
GO
