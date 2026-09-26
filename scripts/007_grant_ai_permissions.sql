-- 007_grant_ai_permissions.sql
-- Adds the V1 AI-agent permission codes (PRD §4.16) to the permission catalog
-- and grants them to non-admin roles so the agents API
-- (backend/app/api/v1/agents.py) is reachable without the admin check bypass.
--   ai.use                  — base gate for any agent invocation
--   ai.agent.resume_screener / .daily_brief / .inbox_triage — per-agent access
--
-- Admin keeps its blanket grant via backend/scripts/seed_ci.py (grant-all loop)
-- or the role admin UI. Here grants are derived from the closest operational
-- permission a role already holds, so one-off/test roles with no real
-- permissions are not widened:
--   ai.use / .resume_screener / .inbox_triage ← candidate.read
--       (resume review, candidate detail, notification triage users)
--   ai.agent.daily_brief ← daily_update.read
--       (daily brief summarizes daily updates / my-work queue)
--
-- Idempotent: safe to re-run; only inserts what is missing.

-- 1. Permission catalog rows -----------------------------------------------
INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
SELECT p.code, p.module_name, p.action_name, p.code, 0
FROM (VALUES
  (N'ai.use',                   N'ai', N'use'),
  (N'ai.agent.resume_screener', N'ai', N'agent.resume_screener'),
  (N'ai.agent.daily_brief',     N'ai', N'agent.daily_brief'),
  (N'ai.agent.inbox_triage',    N'ai', N'agent.inbox_triage')
) AS p(code, module_name, action_name)
WHERE NOT EXISTS (
  SELECT 1 FROM dbo.permissions WHERE code = p.code
);
GO

-- 2. Grants to existing roles (via closest operational permission) -----------
INSERT INTO dbo.role_permissions (role_id, permission_id)
SELECT rp.role_id, p.id
FROM (VALUES
  (N'ai.use',                   N'candidate.read'),
  (N'ai.agent.resume_screener', N'candidate.read'),
  (N'ai.agent.daily_brief',     N'daily_update.read'),
  (N'ai.agent.inbox_triage',    N'candidate.read')
) AS m(agent_code, via_code)
JOIN dbo.permissions p ON p.code = m.agent_code
JOIN dbo.permissions via_p ON via_p.code = m.via_code
JOIN dbo.role_permissions rp ON rp.permission_id = via_p.id
WHERE NOT EXISTS (
  SELECT 1 FROM dbo.role_permissions rp2
  WHERE rp2.role_id = rp.role_id AND rp2.permission_id = p.id
);
GO

-- 3. Verification ------------------------------------------------------------
DECLARE @missing NVARCHAR(MAX) = N'';
IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = N'ai.use')
  SET @missing = @missing + N'ai.use ';
IF (SELECT COUNT(*) FROM dbo.permissions
    WHERE code IN (N'ai.agent.resume_screener', N'ai.agent.daily_brief', N'ai.agent.inbox_triage')) < 3
  SET @missing = @missing + N'ai.agent.* ';
IF (SELECT COUNT(*) FROM dbo.role_permissions rp
    JOIN dbo.permissions p ON p.id = rp.permission_id
    WHERE p.code = N'ai.use') = 0
  SET @missing = @missing + N'ai.use role grants ';
IF LEN(@missing) > 0
BEGIN
  RAISERROR(N'007_grant_ai_permissions verification failed: missing %s', 16, 1, @missing);
  RETURN;
END;
PRINT N'007_grant_ai_permissions: ai.* catalog rows + role grants verified.';
GO
