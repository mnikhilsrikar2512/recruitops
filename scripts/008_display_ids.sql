SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 008_display_ids.sql — Badge-Based Visual ID system (Concept 1)
--
-- Per-branch sequential human display IDs:
--   Requisitions: REQ-101, REQ-102, ...   (3+ digits, global-unique text per branch)
--   Candidates:   CND-1001, CND-1002, ... (4+ digits)
-- The location rides as a visual badge resolved from dbo.branches, never
-- inside the ID string, so moving a requisition to another branch does not
-- rewrite URLs, audit logs, or external references.
--
-- Idempotent: safe to re-run. Backfill only touches NULL codes once and
-- only when the sequence table says no allocation has happened yet.

/* 1 ─ Sequence table. tenant_scope exists so the migration to real
   multi-tenancy (PRD §8.1) can widen the PK without a format change. */
IF OBJECT_ID(N'dbo.display_id_sequences', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.display_id_sequences (
    entity        NVARCHAR(20)  NOT NULL,
    branch_id     BIGINT        NOT NULL,
    tenant_scope  NVARCHAR(40)  NOT NULL CONSTRAINT DF_display_id_seq_scope DEFAULT (N'DEFAULT'),
    next_value    BIGINT        NOT NULL,
    CONSTRAINT PK_display_id_sequences PRIMARY KEY CLUSTERED (entity, branch_id, tenant_scope),
    CONSTRAINT FK_display_id_seq_branch FOREIGN KEY (branch_id) REFERENCES dbo.branches (id)
  );
END;
GO

/* 2 ─ Per-branch sequences. Requisitions start at 101 (first allocation
   returns 101), candidates at 1001. Seeding is idempotent. */
MERGE dbo.display_id_sequences AS target
USING (SELECT id AS branch_id FROM dbo.branches) AS src
ON target.entity = N'REQ' AND target.branch_id = src.branch_id AND target.tenant_scope = N'DEFAULT'
WHEN NOT MATCHED THEN
  INSERT (entity, branch_id, tenant_scope, next_value) VALUES (N'REQ', src.branch_id, N'DEFAULT', 101);

MERGE dbo.display_id_sequences AS target
USING (SELECT id AS branch_id FROM dbo.branches) AS src
ON target.entity = N'CND' AND target.branch_id = src.branch_id AND target.tenant_scope = N'DEFAULT'
WHEN NOT MATCHED THEN
  INSERT (entity, branch_id, tenant_scope, next_value) VALUES (N'CND', src.branch_id, N'DEFAULT', 1001);
GO

/* 3 ─ Candidates need their own branch context (badge + sequence scope).
   Owned by the creator's branch; nullable until owners exist. */
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'dbo.candidates') AND name = N'branch_id')
  ALTER TABLE dbo.candidates ADD branch_id BIGINT NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_candidates_branch')
  ALTER TABLE dbo.candidates ADD CONSTRAINT FK_candidates_branch
    FOREIGN KEY (branch_id) REFERENCES dbo.branches (id);
GO
/* Backfill candidate branch: creator's location first, then the branch of
   the candidate's most recent application (users seeded without a location
   still get a badge scope from where they were applied). Idempotent. */
UPDATE c SET c.branch_id = u.location_id
FROM dbo.candidates AS c
JOIN dbo.users AS u ON u.id = c.created_by_user_id
WHERE c.branch_id IS NULL AND u.location_id IS NOT NULL;
GO
UPDATE c SET c.branch_id = x.branch_id
FROM dbo.candidates AS c
JOIN (
  SELECT a.candidate_id, r.branch_id,
         ROW_NUMBER() OVER (PARTITION BY a.candidate_id ORDER BY a.created_at DESC, a.id DESC) AS rn
  FROM dbo.candidate_applications a
  JOIN dbo.requisitions r ON r.id = a.requisition_id
  WHERE r.branch_id IS NOT NULL
) x ON x.candidate_id = c.id AND x.rn = 1
WHERE c.branch_id IS NULL;
GO
/* Last-resort scope: rows with no creator/applicant location join the
   tenant's primary (first-created) branch so no row is left unscoped. */
IF EXISTS (SELECT 1 FROM dbo.candidates WHERE branch_id IS NULL)
BEGIN
  DECLARE @primary_branch BIGINT = (SELECT TOP 1 id FROM dbo.branches ORDER BY id);
  UPDATE dbo.candidates SET branch_id = @primary_branch WHERE branch_id IS NULL;
END
GO

/* 3b ─ Requisitions with no branch adopt their creator's branch so every
   row lands in a sequence scope (idempotent). */
UPDATE r SET r.branch_id = u.location_id
FROM dbo.requisitions AS r
JOIN dbo.users AS u ON u.id = r.created_by_user_id
WHERE r.branch_id IS NULL AND u.location_id IS NOT NULL;
GO

/* 4 ─ Backfill display IDs oldest-first, per branch, and advance each
   sequence past the highest allocated value. The whole backfill runs once:
   rows that already have a code are never rewritten. */
;WITH numbered_reqs AS (
  SELECT id, branch_id,
         ROW_NUMBER() OVER (PARTITION BY branch_id ORDER BY created_at, id) - 1 AS offset_n
  FROM dbo.requisitions
  WHERE requisition_code IS NULL AND branch_id IS NOT NULL
), req_alloc AS (
  SELECT n.id, n.branch_id,
         s.next_value + n.offset_n AS new_n
  FROM numbered_reqs n
  JOIN dbo.display_id_sequences s
    ON s.entity = N'REQ' AND s.branch_id = n.branch_id AND s.tenant_scope = N'DEFAULT'
)
UPDATE r SET r.requisition_code = CONCAT(N'REQ-', ra.new_n)
FROM dbo.requisitions r
JOIN req_alloc ra ON ra.id = r.id;
GO

UPDATE s SET s.next_value = s.next_value + x.allocated
FROM dbo.display_id_sequences s
JOIN (
  SELECT branch_id, COUNT(*) AS allocated
  FROM dbo.requisitions
  WHERE requisition_code IS NOT NULL AND branch_id IS NOT NULL
  GROUP BY branch_id
) x ON x.branch_id = s.branch_id
WHERE s.entity = N'REQ' AND s.tenant_scope = N'DEFAULT'
  AND s.next_value < 101 + x.allocated;
GO

;WITH numbered_cands AS (
  SELECT id, branch_id,
         ROW_NUMBER() OVER (PARTITION BY branch_id ORDER BY created_at, id) - 1 AS offset_n
  FROM dbo.candidates
  WHERE candidate_code IS NULL AND branch_id IS NOT NULL
), cand_alloc AS (
  SELECT n.id, n.branch_id,
         s.next_value + n.offset_n AS new_n
  FROM numbered_cands n
  JOIN dbo.display_id_sequences s
    ON s.entity = N'CND' AND s.branch_id = n.branch_id AND s.tenant_scope = N'DEFAULT'
)
UPDATE c SET c.candidate_code = CONCAT(N'CND-', ca.new_n)
FROM dbo.candidates c
JOIN cand_alloc ca ON ca.id = c.id;
GO

UPDATE s SET s.next_value = s.next_value + x.allocated
FROM dbo.display_id_sequences s
JOIN (
  SELECT branch_id, COUNT(*) AS allocated
  FROM dbo.candidates
  WHERE candidate_code IS NOT NULL AND branch_id IS NOT NULL
  GROUP BY branch_id
) x ON x.branch_id = s.branch_id
WHERE s.entity = N'CND' AND s.tenant_scope = N'DEFAULT'
  AND s.next_value < 1001 + x.allocated;
GO

/* 5 ─ Uniqueness scoped per branch (concept: HYD's REQ-101 and MUM's
   REQ-101 are distinct rows; the badge disambiguates in UI). Filtered
   unique indexes keep NULL rows out of the constraint. The existing
   global-unique candidate index is replaced by the branch-scoped one. */
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_candidates_candidate_code' AND object_id = OBJECT_ID('dbo.candidates'))
  DROP INDEX UX_candidates_candidate_code ON dbo.candidates;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_requisitions_branch_code' AND object_id = OBJECT_ID('dbo.requisitions'))
  CREATE UNIQUE INDEX UX_requisitions_branch_code
    ON dbo.requisitions (branch_id, requisition_code)
    WHERE requisition_code IS NOT NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_candidates_branch_code' AND object_id = OBJECT_ID('dbo.candidates'))
  CREATE UNIQUE INDEX UX_candidates_branch_code
    ON dbo.candidates (branch_id, candidate_code)
    WHERE candidate_code IS NOT NULL;
GO

/* 6 ─ Search helper indexes. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_requisitions_code' AND object_id = OBJECT_ID('dbo.requisitions'))
  CREATE NONCLUSTERED INDEX IX_requisitions_code ON dbo.requisitions (requisition_code);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_candidates_code' AND object_id = OBJECT_ID('dbo.candidates'))
  CREATE NONCLUSTERED INDEX IX_candidates_code ON dbo.candidates (candidate_code);
GO

/* 7 ─ Immutability guard: display IDs are write-once. Assigning a code to
   a previously NULL row is allowed (initial backfill/creation); changing
   or clearing an assigned code throws (branch moves never touch it). */
IF OBJECT_ID(N'dbo.trg_requisitions_display_id_immutable', N'TR') IS NOT NULL
  DROP TRIGGER dbo.trg_requisitions_display_id_immutable;
GO
EXEC(N'CREATE TRIGGER dbo.trg_requisitions_display_id_immutable ON dbo.requisitions
AFTER UPDATE AS
BEGIN
  SET NOCOUNT ON;
  IF EXISTS (SELECT 1 FROM inserted i JOIN deleted d ON i.id = d.id
             WHERE d.requisition_code IS NOT NULL
               AND ISNULL(i.requisition_code, N'''') <> ISNULL(d.requisition_code, N''''))
    THROW 51000, N''requisition_code is immutable once assigned'', 1;
END;');
GO
IF OBJECT_ID(N'dbo.trg_candidates_display_id_immutable', N'TR') IS NOT NULL
  DROP TRIGGER dbo.trg_candidates_display_id_immutable;
GO
EXEC(N'CREATE TRIGGER dbo.trg_candidates_display_id_immutable ON dbo.candidates
AFTER UPDATE AS
BEGIN
  SET NOCOUNT ON;
  IF EXISTS (SELECT 1 FROM inserted i JOIN deleted d ON i.id = d.id
             WHERE d.candidate_code IS NOT NULL
               AND ISNULL(i.candidate_code, N'''') <> ISNULL(d.candidate_code, N''''))
    THROW 51000, N''candidate_code is immutable once assigned'', 1;
END;');
GO
