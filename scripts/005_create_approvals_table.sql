-- 005_create_approvals_table.sql
-- Creates the approvals table for the approval workflow system

IF OBJECT_ID(N'dbo.approvals', N'U') IS NULL
BEGIN
  CREATE TABLE dbo.approvals (
    id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    location_id BIGINT NOT NULL,
    approval_type NVARCHAR(50) NOT NULL,          -- 'requisition', 'offer', 'exception', 'change_request'
    related_entity_type NVARCHAR(50) NOT NULL,     -- 'requisition', 'offer', 'candidate_application'
    related_entity_id BIGINT NOT NULL,             -- ID of the related record
    title NVARCHAR(200) NOT NULL,                  -- Display title
    description NVARCHAR(1000) NULL,               -- Optional description
    priority NVARCHAR(20) NOT NULL DEFAULT 'standard',  -- 'critical', 'high', 'standard'
    status NVARCHAR(20) NOT NULL DEFAULT 'pending',     -- 'pending', 'approved', 'rejected', 'cancelled'
    requester_user_id BIGINT NOT NULL,             -- Who submitted the request
    assigned_reviewer_user_id BIGINT NULL,         -- Who should review (null = any admin)
    decision_user_id BIGINT NULL,                  -- Who made the decision
    decision_at DATETIME2(0) NULL,                 -- When the decision was made
    decision_notes NVARCHAR(1000) NULL,            -- Notes from the reviewer
    sla_deadline DATETIME2(0) NULL,                -- When the review is due
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_approvals_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2(0) NOT NULL CONSTRAINT DF_approvals_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_approvals_location FOREIGN KEY (location_id) REFERENCES dbo.locations(id),
    CONSTRAINT FK_approvals_requester FOREIGN KEY (requester_user_id) REFERENCES dbo.users(id),
    CONSTRAINT FK_approvals_reviewer FOREIGN KEY (assigned_reviewer_user_id) REFERENCES dbo.users(id),
    CONSTRAINT FK_approvals_decision FOREIGN KEY (decision_user_id) REFERENCES dbo.users(id)
  );

  CREATE INDEX IX_approvals_status ON dbo.approvals(status);
  CREATE INDEX IX_approvals_location ON dbo.approvals(location_id);
  CREATE INDEX IX_approvals_requester ON dbo.approvals(requester_user_id);
  CREATE INDEX IX_approvals_type ON dbo.approvals(approval_type);
END;
GO

-- Seed sample approvals for demo
IF NOT EXISTS (SELECT 1 FROM dbo.approvals WHERE title = N'New Requisition: Senior Data Engineer')
BEGIN
  INSERT INTO dbo.approvals (location_id, approval_type, related_entity_type, related_entity_id, title, description, priority, status, requester_user_id, assigned_reviewer_user_id, sla_deadline)
  VALUES
    (1, N'requisition', N'requisition', 7, N'New Requisition: Senior Data Engineer', N'Opening a new senior data engineering role for TechNova Solutions. Requires approval from hiring manager.', N'high', N'pending', 2, 1, DATEADD(DAY, 2, SYSUTCDATETIME())),
    (1, N'offer', N'candidate_application', 1, N'Offer Approval: Elena Rostova', N'Offer for Senior Frontend Engineer position at TechNova Solutions. CTC: $145,000.', N'critical', N'pending', 5, 1, DATEADD(DAY, 1, SYSUTCDATETIME())),
    (2, N'exception', N'requisition', 9, N'Budget Exception: Risk Analyst', N'Requesting above-band compensation for Risk Analyst role at Apex Finserve.', N'standard', N'pending', 6, 3, DATEADD(DAY, 3, SYSUTCDATETIME())),
    (1, N'change_request', N'requisition', 8, N'Requisition Update: TA Specialist', N'Updating job description and openings count for internal TA role.', N'standard', N'approved', 5, 1, NULL),
    (3, N'requisition', N'requisition', 12, N'New Requisition: Branch Coordinator', N'Opening branch coordination role for Vizag office.', N'standard', N'approved', 7, 4, NULL),
    (2, N'offer', N'candidate_application', 2, N'Offer Approval: Megha Kulkarni', N'Offer for Risk Analyst position. CTC: $72,000.', N'high', N'rejected', 6, 3, NULL),
    (1, N'exception', N'requisition', 7, N'SLA Extension: Java Developer', N'Requesting 5-day SLA extension for senior Java developer screening.', N'standard', N'pending', 2, 1, DATEADD(DAY, 5, SYSUTCDATETIME())),
    (3, N'change_request', N'requisition', 11, N'On-Hold Release: Production Planner', N'Requesting to release Production Planner requisition from on-hold status.', N'high', N'pending', 7, 4, DATEADD(DAY, 1, SYSUTCDATETIME()));
END;
GO
