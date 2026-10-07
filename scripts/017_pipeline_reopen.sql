/* =====================================================================
   017_pipeline_reopen.sql — Phase 4.6: the reopen permission.
   - Catalog row pipeline.stage.reopen (sensitive: it undoes a closed
     outcome). PRD §3.2: Manager-granted.
   - Granted once to every role that already manages recruiting work —
     holds pipeline.stage.move AND requisition.update (the manager shape;
     recruiters hold move only, the Admin template holds neither). Admins
     adjust it per role afterwards in the role editor.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.permissions WHERE code = N'pipeline.stage.reopen')
  INSERT INTO dbo.permissions (code, module_name, action_name, description, is_sensitive)
  VALUES (N'pipeline.stage.reopen', N'pipeline', N'stage.reopen',
          N'Reopen a rejected, withdrawn or joined application', 1);
GO

INSERT INTO dbo.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM dbo.roles AS r
CROSS JOIN dbo.permissions AS p
WHERE p.code = N'pipeline.stage.reopen'
  AND EXISTS (SELECT 1 FROM dbo.role_permissions rp JOIN dbo.permissions x ON x.id = rp.permission_id
              WHERE rp.role_id = r.id AND x.code = N'pipeline.stage.move')
  AND EXISTS (SELECT 1 FROM dbo.role_permissions rp JOIN dbo.permissions x ON x.id = rp.permission_id
              WHERE rp.role_id = r.id AND x.code = N'requisition.update')
  AND NOT EXISTS (SELECT 1 FROM dbo.role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id);
GO
