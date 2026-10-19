-- 010: widen three lifecycle CHECK constraints to allow states the app
-- already writes but that were never added to the constraint when the
-- feature shipped.
--
-- CK_password_reset_tokens_purpose -- app/services/signup.py uses purpose
-- 'signup-verify' for the self-serve signup email-verification token
-- (Phase 5.2), alongside the three purposes the constraint already allowed.
--
-- CK_candidate_stage_history_source_type -- app/repositories/stage_lists.py
-- logs 'stage-list-change' as the source_type when a client's stage list
-- change remaps an application's stage (Phase 4.10-4.13), alongside the
-- five source types the constraint already allowed.
--
-- CK_candidates_status -- app/services/candidate_erasure.py sets status
-- 'erased' when a privacy erase request is fulfilled (Phase 5.3), alongside
-- the five statuses the constraint already allowed.
--
-- All three are real, deliberately-added terminal/intermediate states from
-- already-shipped features, not typos -- the constraints just never caught
-- up. Idempotent -- safe to re-run (DROP/ADD unconditionally, which is a
-- no-op in effect if the widened definition is already in place, and the
-- verification block below confirms the end state either way).

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_password_reset_tokens_purpose' AND parent_object_id = OBJECT_ID('dbo.password_reset_tokens'))
    ALTER TABLE dbo.password_reset_tokens DROP CONSTRAINT [CK_password_reset_tokens_purpose];
ALTER TABLE dbo.password_reset_tokens ADD CONSTRAINT [CK_password_reset_tokens_purpose]
    CHECK ([purpose] = N'admin-reset' OR [purpose] = N'first-password-setup' OR [purpose] = N'forgot-password' OR [purpose] = N'signup-verify');

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_candidate_stage_history_source_type' AND parent_object_id = OBJECT_ID('dbo.candidate_stage_history'))
    ALTER TABLE dbo.candidate_stage_history DROP CONSTRAINT [CK_candidate_stage_history_source_type];
ALTER TABLE dbo.candidate_stage_history ADD CONSTRAINT [CK_candidate_stage_history_source_type]
    CHECK ([source_type] = N'interview' OR [source_type] = N'screening' OR [source_type] = N'client-feedback' OR [source_type] = N'automation' OR [source_type] = N'manual' OR [source_type] = N'stage-list-change');

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_candidates_status' AND parent_object_id = OBJECT_ID('dbo.candidates'))
    ALTER TABLE dbo.candidates DROP CONSTRAINT [CK_candidates_status];
ALTER TABLE dbo.candidates ADD CONSTRAINT [CK_candidates_status]
    CHECK ([status] = N'on-hold' OR [status] = N'hired' OR [status] = N'rejected' OR [status] = N'inactive' OR [status] = N'active' OR [status] = N'erased');

-- Verify: each constraint now accepts its new value (query the definition
-- text rather than attempting a live insert, so this script never mutates
-- data on top of its own schema change).
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_password_reset_tokens_purpose' AND definition LIKE '%signup-verify%'
)
    RAISERROR('010 failed: CK_password_reset_tokens_purpose does not allow signup-verify', 16, 1);
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_candidate_stage_history_source_type' AND definition LIKE '%stage-list-change%'
)
    RAISERROR('010 failed: CK_candidate_stage_history_source_type does not allow stage-list-change', 16, 1);
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_candidates_status' AND definition LIKE '%erased%'
)
    RAISERROR('010 failed: CK_candidates_status does not allow erased', 16, 1);
PRINT '010 OK: password_reset_tokens.purpose, candidate_stage_history.source_type, and candidates.status now allow their already-shipped-but-unconstrained values';
