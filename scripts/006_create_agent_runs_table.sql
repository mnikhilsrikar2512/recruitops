-- 006_create_agent_runs_table.sql
-- Creates the agent_runs table for V1 AI agent drafts + audits (PRD §4.16).
-- Agents propose; humans confirm. Every run is persisted here (status =
-- pending/ accepted / rejected) and mirrored to dbo.audit_logs.

IF OBJECT_ID(N'dbo.agent_runs', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.agent_runs (
    id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    agent_id NVARCHAR(100) NOT NULL,           -- registry id: resume_screener / daily_brief / inbox_triage
    actor_user_id BIGINT NOT NULL,             -- who triggered the run
    location_id BIGINT NULL,                   -- tenant scope of the run
    input_refs_json NVARCHAR(MAX) NULL,        -- light input references (candidate_id, requisition_id, scope, status)
    output_draft_json NVARCHAR(MAX) NULL,      -- agent draft output (JSON), pending until accepted
    output_summary NVARCHAR(MAX) NULL,         -- human-readable one-line summary for audit
    status NVARCHAR(30) NOT NULL DEFAULT 'pending', -- pending / accepted / rejected / failed
    decided_by_user_id BIGINT NULL,            -- who accepted/rejected (human-in-the-loop)
    decided_at DATETIME2 NULL,
    decision_notes NVARCHAR(1000) NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_agent_runs_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_agent_runs_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_agent_runs_actor FOREIGN KEY (actor_user_id) REFERENCES dbo.users(id),
    CONSTRAINT FK_agent_runs_decided_by FOREIGN KEY (decided_by_user_id) REFERENCES dbo.users(id),
    CONSTRAINT FK_agent_runs_location FOREIGN KEY (location_id) REFERENCES dbo.locations(id)
  );

  CREATE INDEX IX_agent_runs_actor ON dbo.agent_runs(actor_user_id, created_at);
  CREATE INDEX IX_agent_runs_agent_status ON dbo.agent_runs(agent_id, status, created_at);
END;
GO