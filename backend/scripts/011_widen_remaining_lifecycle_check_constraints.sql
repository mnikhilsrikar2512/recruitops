-- 011: widen two more lifecycle CHECK constraints that migration 010 missed,
-- allowing states the app already writes but that were never added to the
-- constraint when the feature shipped.
--
-- CK_candidate_stage_history_source_type -- app/repositories/pipeline.py
-- logs 'reopen' as the source_type when a withdrawn application is
-- reopened, alongside the six source types the constraint already allowed
-- (five original plus 'stage-list-change', added by migration 010).
--
-- CK_candidates_resume_parsing_status -- app/services/candidate_erasure.py
-- sets resume_parsing_status 'erased' when a privacy erase request is
-- fulfilled (Phase 5.3), alongside the four statuses the constraint
-- already allowed.
--
-- Both are real, deliberately-added terminal/intermediate states from
-- already-shipped features, not typos -- the constraints just never caught
-- up. Idempotent -- safe to re-run (DROP/ADD unconditionally, which is a
-- no-op in effect if the widened definition is already in place, and the
-- verification block below confirms the end state either way).

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_candidate_stage_history_source_type' AND parent_object_id = OBJECT_ID('dbo.candidate_stage_history'))
    ALTER TABLE dbo.candidate_stage_history DROP CONSTRAINT [CK_candidate_stage_history_source_type];
ALTER TABLE dbo.candidate_stage_history ADD CONSTRAINT [CK_candidate_stage_history_source_type]
    CHECK ([source_type] = N'interview' OR [source_type] = N'screening' OR [source_type] = N'client-feedback' OR [source_type] = N'automation' OR [source_type] = N'manual' OR [source_type] = N'stage-list-change' OR [source_type] = N'reopen');

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_candidates_resume_parsing_status' AND parent_object_id = OBJECT_ID('dbo.candidates'))
    ALTER TABLE dbo.candidates DROP CONSTRAINT [CK_candidates_resume_parsing_status];
ALTER TABLE dbo.candidates ADD CONSTRAINT [CK_candidates_resume_parsing_status]
    CHECK ([resume_parsing_status] = N'failed' OR [resume_parsing_status] = N'needs-review' OR [resume_parsing_status] = N'parsed' OR [resume_parsing_status] = N'pending' OR [resume_parsing_status] = N'erased');

-- Verify: each constraint now accepts its new value (query the definition
-- text rather than attempting a live insert, so this script never mutates
-- data on top of its own schema change).
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_candidate_stage_history_source_type' AND definition LIKE '%reopen%'
)
    RAISERROR('011 failed: CK_candidate_stage_history_source_type does not allow reopen', 16, 1);
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_candidates_resume_parsing_status' AND definition LIKE '%erased%'
)
    RAISERROR('011 failed: CK_candidates_resume_parsing_status does not allow erased', 16, 1);
PRINT '011 OK: candidate_stage_history.source_type now allows reopen, and candidates.resume_parsing_status now allows erased';
