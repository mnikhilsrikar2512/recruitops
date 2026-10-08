/* =====================================================================
   011_admin_seed.sql — Phase 2.5/2.6: the Admin template is the control plane.

   Decision D-03: the Admin system role (code 'admin', tenant_id NULL) holds
   EXACTLY the codes below — users, offices, roles, settings, approvals,
   reports, notifications, portal accounts, work assignment, governance and
   scope.company (reach over every office of the admin's own company). It no
   longer holds recruiting (execution) codes, and the API no longer lets the
   admin role code bypass permission checks: admins pass routes by grant.

   Keep in step with backend/app/core/rbac.py ADMIN_PERMISSION_CODES
   (tests/test_admin_seed.py checks it).

   Idempotent. Resets the Admin role's grants every run (the role is
   read-only to companies). Verifies itself.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET NOCOUNT ON;
GO

IF OBJECT_ID(N'tempdb..#admin_codes') IS NOT NULL DROP TABLE #admin_codes;
CREATE TABLE #admin_codes (
  code NVARCHAR(150) COLLATE DATABASE_DEFAULT NOT NULL PRIMARY KEY,
  module_name NVARCHAR(100) COLLATE DATABASE_DEFAULT NOT NULL,
  action_name NVARCHAR(100) COLLATE DATABASE_DEFAULT NOT NULL
);
INSERT INTO #admin_codes (code, module_name, action_name) VALUES
    (N'user.read', N'user', N'read'),
    (N'user.create', N'user', N'create'),
    (N'user.update', N'user', N'update'),
    (N'user.credentials.manage', N'user', N'credentials.manage'),
    (N'user.write', N'user', N'write'),
    (N'location.read', N'location', N'read'),
    (N'location.create', N'location', N'create'),
    (N'location.update', N'location', N'update'),
    (N'location.write', N'location', N'write'),
    (N'role.read', N'role', N'read'),
    (N'role.create', N'role', N'create'),
    (N'role.update', N'role', N'update'),
    (N'role.permissions.assign', N'role', N'permissions.assign'),
    (N'role.write', N'role', N'write'),
    (N'settings.read', N'settings', N'read'),
    (N'settings.create', N'settings', N'create'),
    (N'settings.update', N'settings', N'update'),
    (N'settings.write', N'settings', N'write'),
    (N'visibility_rules.write', N'visibility_rules', N'write'),
    (N'approval.read', N'approval', N'read'),
    (N'approval.decide', N'approval', N'decide'),
    (N'dashboard.view_admin', N'dashboard', N'view_admin'),
    (N'dashboard.read_pipeline_summary', N'dashboard', N'read_pipeline_summary'),
    (N'report.read', N'report', N'read'),
    (N'notification.read', N'notification', N'read'),
    (N'notification.mark_read', N'notification', N'mark_read'),
    (N'portal.read', N'portal', N'read'),
    (N'portal.create', N'portal', N'create'),
    (N'portal.update', N'portal', N'update'),
    (N'portal.assign_slot', N'portal', N'assign_slot'),
    (N'portal_accounts.write', N'portal_accounts', N'write'),
    (N'assignment.read', N'assignment', N'read'),
    (N'assignment.create', N'assignment', N'create'),
    (N'assignment.update', N'assignment', N'update'),
    (N'work_assignment.write', N'work_assignment', N'write'),
    (N'ai.policy.write', N'ai', N'policy.write'),
    (N'audit_log.read', N'audit_log', N'read'),
    (N'privacy_request.write', N'privacy_request', N'write'),
    (N'scope.company', N'scope', N'company');

/* catalog rows the template needs */
INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
SELECT a.code, a.module_name, a.action_name, a.code, 0
FROM #admin_codes AS a
WHERE NOT EXISTS (SELECT 1 FROM dbo.permissions AS p WHERE p.code = a.code);

/* the Admin template = exactly these codes (only if the role exists yet;
   a fresh database gets it from the seed) */
DECLARE @admin_role BIGINT = (SELECT TOP 1 id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL ORDER BY id);
IF @admin_role IS NOT NULL
BEGIN
  DELETE rp FROM dbo.role_permissions AS rp
  INNER JOIN dbo.permissions AS p ON p.id = rp.permission_id
  WHERE rp.role_id = @admin_role AND p.code NOT IN (SELECT code FROM #admin_codes);

  INSERT INTO dbo.role_permissions (role_id, permission_id)
  SELECT @admin_role, p.id
  FROM dbo.permissions AS p
  INNER JOIN #admin_codes AS a ON a.code = p.code
  WHERE NOT EXISTS (SELECT 1 FROM dbo.role_permissions AS rp WHERE rp.role_id = @admin_role AND rp.permission_id = p.id);

  /* verify */
  IF (SELECT COUNT(*) FROM dbo.role_permissions WHERE role_id = @admin_role)
     <> (SELECT COUNT(*) FROM #admin_codes)
    THROW 51011, N'011_admin_seed: Admin role grants do not match the template', 1;
END;

DROP TABLE #admin_codes;
GO
