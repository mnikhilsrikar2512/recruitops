/* =====================================================================
   016_metric_buckets.sql — Phase 4.5 (P0): reports read metric buckets,
   never raw stage labels.

   - dbo.metric_buckets: the fixed platform enum (8 buckets, ordered).
     'submitted' is added to the spec's 7 so "profiles with the client" can
     be counted by bucket too (decision recorded in phase-4 status doc).
   - dbo.stage_bucket_map: label -> bucket. tenant_id NULL = platform
     defaults; a company row overrides the default for that company.
   - pipeline_template_stages.metric_bucket / is_terminal.
   - dbo.fn_metric_bucket / dbo.fn_application_stage_bucket: the ONE place a
     label is resolved: template stage -> company map -> platform map ->
     name heuristic -> 'interview'.
   - candidate_stage_history.from_bucket / to_bucket, snapshotted at insert
     by trg_stage_history_fill_buckets and backfilled here.
   - trg_stage_history_append_only: history rows cannot be edited or
     deleted. The only exemptions: filling NULL buckets, and a session that
     sets SESSION_CONTEXT 'recruitops.history_maintenance' = 1 (governed
     purge / test cleanup).
   - dbo.vw_application_metric_state: current bucket per application.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.metric_buckets', N'U') IS NULL
  CREATE TABLE dbo.metric_buckets (
    code NVARCHAR(20) NOT NULL CONSTRAINT PK_metric_buckets PRIMARY KEY,
    label NVARCHAR(60) NOT NULL,
    sort_order INT NOT NULL,
    is_terminal BIT NOT NULL CONSTRAINT DF_metric_buckets_terminal DEFAULT (0)
  );
GO

MERGE dbo.metric_buckets AS t
USING (VALUES
  (N'sourced',   N'Sourced',   10, 0),
  (N'screened',  N'Screened',  20, 0),
  (N'submitted', N'Submitted', 30, 0),
  (N'interview', N'Interview', 40, 0),
  (N'offer',     N'Offer',     50, 0),
  (N'joined',    N'Joined',    60, 1),
  (N'rejected',  N'Rejected',  70, 1),
  (N'withdrawn', N'Withdrawn', 80, 1)
) AS s (code, label, sort_order, is_terminal)
ON t.code = s.code
WHEN MATCHED THEN UPDATE SET label = s.label, sort_order = s.sort_order, is_terminal = s.is_terminal
WHEN NOT MATCHED THEN INSERT (code, label, sort_order, is_terminal) VALUES (s.code, s.label, s.sort_order, s.is_terminal);
GO

IF OBJECT_ID(N'dbo.stage_bucket_map', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.stage_bucket_map (
    id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_stage_bucket_map PRIMARY KEY,
    tenant_id BIGINT NULL CONSTRAINT FK_stage_bucket_map_tenant REFERENCES dbo.tenants (id),
    stage_key NVARCHAR(50) NOT NULL,          -- normalised: lower-case, '-' for ' ' and '_'
    metric_bucket NVARCHAR(20) NOT NULL CONSTRAINT FK_stage_bucket_map_bucket REFERENCES dbo.metric_buckets (code),
    updated_by_user_id BIGINT NULL CONSTRAINT FK_stage_bucket_map_user REFERENCES dbo.users (id),
    created_at DATETIME2 NOT NULL CONSTRAINT DF_stage_bucket_map_created DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_stage_bucket_map_updated DEFAULT (SYSUTCDATETIME())
  );
  CREATE UNIQUE INDEX UX_stage_bucket_map_platform ON dbo.stage_bucket_map (stage_key) WHERE tenant_id IS NULL;
  CREATE UNIQUE INDEX UX_stage_bucket_map_tenant ON dbo.stage_bucket_map (tenant_id, stage_key) WHERE tenant_id IS NOT NULL;
END;
GO

MERGE dbo.stage_bucket_map AS t
USING (VALUES
  (N'sourced', N'sourced'), (N'new', N'sourced'), (N'applied', N'sourced'), (N'identified', N'sourced'),
  (N'screening', N'screened'), (N'screened', N'screened'), (N'internal-screening', N'screened'),
  (N'shortlisted', N'screened'), (N'recruiter-screen', N'screened'),
  (N'submitted', N'submitted'), (N'submitted-to-client', N'submitted'), (N'client-review', N'submitted'),
  (N'interview', N'interview'), (N'technical-interview', N'interview'), (N'executive-review', N'interview'),
  (N'client-interview', N'interview'),
  (N'offer', N'offer'), (N'offered', N'offer'), (N'offer-accepted', N'offer'),
  (N'joined', N'joined'), (N'hired', N'joined'),
  (N'rejected', N'rejected'), (N'client-rejected', N'rejected'),
  (N'withdrawn', N'withdrawn')
) AS s (stage_key, metric_bucket)
ON t.tenant_id IS NULL AND t.stage_key = s.stage_key
WHEN NOT MATCHED THEN INSERT (tenant_id, stage_key, metric_bucket) VALUES (NULL, s.stage_key, s.metric_bucket);
GO

IF COL_LENGTH(N'dbo.pipeline_template_stages', N'metric_bucket') IS NULL
  ALTER TABLE dbo.pipeline_template_stages ADD metric_bucket NVARCHAR(20) NULL;
IF COL_LENGTH(N'dbo.pipeline_template_stages', N'is_terminal') IS NULL
  ALTER TABLE dbo.pipeline_template_stages ADD is_terminal BIT NOT NULL
    CONSTRAINT DF_pts_is_terminal DEFAULT (0);
GO

IF OBJECT_ID(N'dbo.CK_pts_metric_bucket', N'C') IS NULL
  ALTER TABLE dbo.pipeline_template_stages ADD CONSTRAINT CK_pts_metric_bucket
    CHECK (metric_bucket IS NULL OR metric_bucket IN (N'sourced', N'screened', N'submitted', N'interview',
                                                      N'offer', N'joined', N'rejected', N'withdrawn'));
GO

IF COL_LENGTH(N'dbo.candidate_stage_history', N'from_bucket') IS NULL
  ALTER TABLE dbo.candidate_stage_history ADD from_bucket NVARCHAR(20) NULL;
IF COL_LENGTH(N'dbo.candidate_stage_history', N'to_bucket') IS NULL
  ALTER TABLE dbo.candidate_stage_history ADD to_bucket NVARCHAR(20) NULL;
GO

/* Label normaliser + resolver. NULL stage -> NULL bucket. */
CREATE OR ALTER FUNCTION dbo.fn_stage_key (@stage NVARCHAR(100))
RETURNS NVARCHAR(100)
WITH SCHEMABINDING
AS
BEGIN
  RETURN LOWER(REPLACE(REPLACE(LTRIM(RTRIM(@stage)), N'_', N'-'), N' ', N'-'));
END;
GO

CREATE OR ALTER FUNCTION dbo.fn_metric_bucket (@template_id BIGINT, @tenant_id BIGINT, @stage NVARCHAR(100))
RETURNS NVARCHAR(20)
AS
BEGIN
  IF @stage IS NULL RETURN NULL;
  DECLARE @key NVARCHAR(100) = dbo.fn_stage_key(@stage);
  DECLARE @bucket NVARCHAR(20) = NULL;

  IF @template_id IS NOT NULL
    SELECT TOP (1) @bucket = s.metric_bucket
    FROM dbo.pipeline_template_stages AS s
    WHERE s.pipeline_template_id = @template_id
      AND dbo.fn_stage_key(s.stage_code) = @key
      AND s.metric_bucket IS NOT NULL;
  IF @bucket IS NOT NULL RETURN @bucket;

  IF @tenant_id IS NOT NULL
    SELECT TOP (1) @bucket = m.metric_bucket FROM dbo.stage_bucket_map AS m
    WHERE m.tenant_id = @tenant_id AND m.stage_key = @key;
  IF @bucket IS NOT NULL RETURN @bucket;

  SELECT TOP (1) @bucket = m.metric_bucket FROM dbo.stage_bucket_map AS m
  WHERE m.tenant_id IS NULL AND m.stage_key = @key;
  IF @bucket IS NOT NULL RETURN @bucket;

  RETURN CASE
    WHEN @key LIKE N'%withdr%' OR @key LIKE N'%pulled-out%' THEN N'withdrawn'
    WHEN @key LIKE N'%reject%' OR @key LIKE N'%declin%' OR @key LIKE N'%no-fit%' THEN N'rejected'
    WHEN @key LIKE N'%join%' OR @key LIKE N'%hired%' OR @key LIKE N'%onboard%' OR @key LIKE N'%placed%' THEN N'joined'
    WHEN @key LIKE N'%offer%' THEN N'offer'
    WHEN @key LIKE N'%interview%' OR @key LIKE N'%review%' OR @key LIKE N'%panel%' OR @key LIKE N'%assessment%' THEN N'interview'
    WHEN @key LIKE N'%submit%' THEN N'submitted'
    WHEN @key LIKE N'%screen%' OR @key LIKE N'%shortlist%' THEN N'screened'
    WHEN @key LIKE N'%sourc%' THEN N'sourced'
    ELSE N'interview'
  END;
END;
GO

CREATE OR ALTER FUNCTION dbo.fn_application_stage_bucket (@application_id BIGINT, @stage NVARCHAR(100))
RETURNS NVARCHAR(20)
AS
BEGIN
  DECLARE @template_id BIGINT, @tenant_id BIGINT;
  SELECT @template_id = COALESCE(ca.pipeline_template_id, r.pipeline_template_id),
         @tenant_id = b.tenant_id
  FROM dbo.candidate_applications AS ca
  INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
  LEFT JOIN dbo.branches AS b ON b.id = r.branch_id
  WHERE ca.id = @application_id;
  RETURN dbo.fn_metric_bucket(@template_id, @tenant_id, @stage);
END;
GO

/* Backfill before the guard exists. */
UPDATE dbo.candidate_stage_history
SET from_bucket = COALESCE(from_bucket, dbo.fn_application_stage_bucket(candidate_application_id, from_stage)),
    to_bucket = COALESCE(to_bucket, dbo.fn_application_stage_bucket(candidate_application_id, to_stage))
WHERE to_bucket IS NULL OR (from_bucket IS NULL AND from_stage IS NOT NULL);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_candidate_stage_history_app_bucket')
  CREATE INDEX IX_candidate_stage_history_app_bucket
    ON dbo.candidate_stage_history (candidate_application_id, to_bucket, changed_at);
GO

/* Append-only guard. */
CREATE OR ALTER TRIGGER dbo.trg_stage_history_append_only
ON dbo.candidate_stage_history
AFTER UPDATE, DELETE
AS
BEGIN
  SET NOCOUNT ON;
  IF NOT EXISTS (SELECT 1 FROM deleted) RETURN;
  IF CAST(SESSION_CONTEXT(N'recruitops.history_maintenance') AS INT) = 1 RETURN;

  -- An UPDATE that only fills buckets that were still empty is allowed
  -- (the insert-time snapshot below, and the 016 backfill).
  IF EXISTS (SELECT 1 FROM inserted)
     AND NOT (UPDATE(candidate_application_id) OR UPDATE(from_stage) OR UPDATE(to_stage)
              OR UPDATE(change_reason) OR UPDATE(changed_by_user_id) OR UPDATE(changed_at)
              OR UPDATE(source_type) OR UPDATE(created_at))
     AND NOT EXISTS (
       SELECT 1 FROM deleted AS d INNER JOIN inserted AS i ON i.id = d.id
       WHERE (d.to_bucket IS NOT NULL AND (i.to_bucket IS NULL OR i.to_bucket <> d.to_bucket))
          OR (d.from_bucket IS NOT NULL AND (i.from_bucket IS NULL OR i.from_bucket <> d.from_bucket)))
    RETURN;

  ROLLBACK TRANSACTION;
  THROW 51000, N'candidate_stage_history is append-only; history rows cannot be edited or deleted.', 1;
END;
GO

/* Snapshot buckets at insert time, whoever inserts. */
CREATE OR ALTER TRIGGER dbo.trg_stage_history_fill_buckets
ON dbo.candidate_stage_history
AFTER INSERT
AS
BEGIN
  SET NOCOUNT ON;
  IF NOT EXISTS (SELECT 1 FROM inserted WHERE to_bucket IS NULL OR (from_bucket IS NULL AND from_stage IS NOT NULL))
    RETURN;
  UPDATE h
  SET from_bucket = COALESCE(h.from_bucket, dbo.fn_application_stage_bucket(h.candidate_application_id, h.from_stage)),
      to_bucket = COALESCE(h.to_bucket, dbo.fn_application_stage_bucket(h.candidate_application_id, h.to_stage))
  FROM dbo.candidate_stage_history AS h
  INNER JOIN inserted AS i ON i.id = h.id
  WHERE h.to_bucket IS NULL OR (h.from_bucket IS NULL AND h.from_stage IS NOT NULL);
END;
GO

CREATE OR ALTER VIEW dbo.vw_application_metric_state
AS
SELECT
  ca.id AS application_id,
  ca.requisition_id,
  r.branch_id,
  b.tenant_id,
  ca.current_stage,
  dbo.fn_metric_bucket(COALESCE(ca.pipeline_template_id, r.pipeline_template_id), b.tenant_id, ca.current_stage) AS current_bucket,
  ca.application_status,
  ca.stage_updated_at
FROM dbo.candidate_applications AS ca
INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
LEFT JOIN dbo.branches AS b ON b.id = r.branch_id;
GO
