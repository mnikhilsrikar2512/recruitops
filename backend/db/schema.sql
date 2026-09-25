-- RecruitOps schema dump (tables only, no data)
--
-- Pass 1: tables (FKs deferred to pass 2 so circular dependencies replay)
--
-- Required SET options for filtered/computed indexes (sqlcmd defaults differ):
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;

CREATE TABLE backend_sql_executions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	script_key NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	file_path NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	checksum_sha256 CHAR(64) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	script_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	executed_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__backend___3213E83F62E930FB] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_backend_sql_executions_script_key] ON backend_sql_executions (script_key);

CREATE TABLE company_entities (
	id BIGINT NOT NULL IDENTITY(1,1), 
	display_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	legal_name NVARCHAR(250) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	company_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	company_type_code NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	hq_city NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	hq_state NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	country_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	time_zone NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	support_email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	support_phone NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	website_url NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	founded_on DATE NULL, 
	registered_address NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	internal_notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	is_primary BIT NOT NULL DEFAULT ((0)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	logo_data NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	CONSTRAINT [PK__company___3213E83FC196E6AC] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_company_entities_status_primary] ON company_entities (status, is_primary, display_name);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_company_entities_company_code] ON company_entities (company_code);

CREATE TABLE locations (
	id BIGINT NOT NULL IDENTITY(1,1), 
	name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	location NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	address NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	location_head_user_id BIGINT NULL, 
	monthly_target_internal INTEGER NULL, 
	monthly_target_external INTEGER NULL, 
	weekly_target_internal INTEGER NULL, 
	weekly_target_external INTEGER NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	city NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	state_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	country_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	location_mapping_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	CONSTRAINT [PK__location__3213E83F5740DBDD] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_locations_code] ON locations (code);

CREATE TABLE master_data_categories (
	id BIGINT NOT NULL IDENTITY(1,1), 
	code NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	is_system BIT NOT NULL DEFAULT ((1)), 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__master_d__3213E83F40C7E74B] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_master_data_categories_code] ON master_data_categories (code);

CREATE TABLE meeting_attendees (
	id BIGINT NOT NULL IDENTITY(1,1), 
	meeting_id BIGINT NOT NULL, 
	attendee_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'internal-user'), 
	user_id BIGINT NULL, 
	client_contact_id BIGINT NULL, 
	attendance_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__meeting___3213E83F4E44FB43] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE meetings (
	id BIGINT NOT NULL IDENTITY(1,1), 
	location_id BIGINT NOT NULL, 
	client_id BIGINT NOT NULL, 
	end_client_id BIGINT NULL, 
	meeting_owner_user_id BIGINT NOT NULL, 
	title NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	meeting_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	scheduled_at DATETIME2 NULL, 
	attendance_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	outcome_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	agenda NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	minutes_of_meeting NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	decision_summary NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	next_steps NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	follow_up_owner_user_id BIGINT NULL, 
	follow_up_due_date DATE NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__meetings__3213E83FC26CF66C] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE notifications (
	id BIGINT NOT NULL IDENTITY(1,1), 
	location_id BIGINT NULL, 
	user_id BIGINT NOT NULL, 
	title NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	message NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	module_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	entity_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	entity_id BIGINT NULL, 
	priority NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'normal'), 
	status NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'unread'), 
	action_url NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	read_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	event_type NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	source_type NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	source_id BIGINT NULL, 
	CONSTRAINT [PK__notifica__3213E83F499454AF] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE permissions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	code NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	module_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	action_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	is_sensitive BIT NOT NULL DEFAULT ((0)), 
	CONSTRAINT [PK__permissi__3213E83F0357F59C] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_permissions_code] ON permissions (code);

CREATE TABLE role_templates (
	id BIGINT NOT NULL IDENTITY(1,1), 
	code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(300) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	is_protected BIT NOT NULL DEFAULT ((1)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__role_tem__3213E83FE86E6BE2] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_role_templates_code] ON role_templates (code);

CREATE TABLE roles (
	id BIGINT NOT NULL IDENTITY(1,1), 
	code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	is_system_role BIT NOT NULL DEFAULT ((0)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_by_user_id BIGINT NULL, 
	CONSTRAINT [PK__roles__3213E83F12E9F382] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_roles_code] ON roles (code);

CREATE TABLE users (
	id BIGINT NOT NULL IDENTITY(1,1), 
	employee_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	full_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	phone NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	password_hash NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	password_setup_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending-setup'), 
	password_changed_at DATETIME2 NULL, 
	force_password_change_on_first_login BIT NOT NULL DEFAULT ((1)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	default_role_id BIGINT NOT NULL, 
	reporting_manager_user_id BIGINT NULL, 
	hierarchy_level NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	last_login_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	location_id BIGINT NULL, 
	primary_role_id BIGINT NULL, 
	business_title NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_by_user_id BIGINT NULL, 
	CONSTRAINT [PK__users__3213E83F483BB8ED] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_users_email] ON users (email);
CREATE NONCLUSTERED INDEX [IX_users_location_role] ON users (location_id, primary_role_id);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_users_email] ON users (email);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_users_employee_code] ON users (employee_code);

CREATE TABLE approvals (
	id BIGINT NOT NULL IDENTITY(1,1), 
	location_id BIGINT NOT NULL, 
	approval_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	related_entity_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	related_entity_id BIGINT NOT NULL, 
	title NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	priority NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT ('standard'), 
	status NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT ('pending'), 
	requester_user_id BIGINT NOT NULL, 
	assigned_reviewer_user_id BIGINT NULL, 
	decision_user_id BIGINT NULL, 
	decision_at DATETIME2 NULL, 
	decision_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	sla_deadline DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__approval__3213E83FF74C44DB] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_approvals_location] ON approvals (location_id);
CREATE NONCLUSTERED INDEX [IX_approvals_requester] ON approvals (requester_user_id);
CREATE NONCLUSTERED INDEX [IX_approvals_status] ON approvals (status);
CREATE NONCLUSTERED INDEX [IX_approvals_type] ON approvals (approval_type);

CREATE TABLE agent_runs (
	id BIGINT NOT NULL IDENTITY(1,1), 
	agent_id NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	actor_user_id BIGINT NOT NULL, 
	location_id BIGINT NULL, 
	input_refs_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	output_draft_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	output_summary NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	decided_by_user_id BIGINT NULL, 
	decided_at DATETIME2 NULL, 
	decision_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__agent_ru__3213E83F1A2B3C4D] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_agent_runs_actor] ON agent_runs (actor_user_id, created_at);
CREATE NONCLUSTERED INDEX [IX_agent_runs_agent_status] ON agent_runs (agent_id, status, created_at);

CREATE TABLE audit_log_access_events (
	id BIGINT NOT NULL IDENTITY(1,1), 
	actor_user_id BIGINT NOT NULL, 
	accessed_user_id BIGINT NULL, 
	location_id BIGINT NULL, 
	access_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	source_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	source_id BIGINT NULL, 
	access_notes NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__audit_lo__3213E83FB98273FD] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_audit_log_access_events_actor_created] ON audit_log_access_events (actor_user_id, created_at);

CREATE TABLE automation_jobs (
	id BIGINT NOT NULL IDENTITY(1,1), 
	job_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	scope_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	scope_id BIGINT NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'queued'), 
	triggered_by_user_id BIGINT NULL, 
	input_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	output_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	warning_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	error_message NVARCHAR(2000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	started_at DATETIME2 NULL, 
	completed_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__automati__3213E83F8A4509B1] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE branches (
	id BIGINT NOT NULL IDENTITY(1,1), 
	name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	location NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	address NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	manager_user_id BIGINT NULL, 
	monthly_target_internal INTEGER NULL, 
	monthly_target_external INTEGER NULL, 
	weekly_target_internal INTEGER NULL, 
	weekly_target_external INTEGER NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	city NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	state_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	country_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	branch_mapping_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	CONSTRAINT [PK__branches__3213E83FE00A9463] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_branches_code] ON branches (code);

CREATE TABLE candidates (
	id BIGINT NOT NULL IDENTITY(1,1), 
	full_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	phone NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	current_location NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	source NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	source_portal NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	profile_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'draft'), 
	intake_stage NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'uploaded'), 
	total_experience_years DECIMAL(5, 2) NULL, 
	notice_period_days INTEGER NULL, 
	current_ctc DECIMAL(18, 2) NULL, 
	expected_ctc DECIMAL(18, 2) NULL, 
	candidate_score DECIMAL(10, 2) NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_by_user_id BIGINT NOT NULL, 
	primary_owner_user_id BIGINT NULL, 
	resume_file_name NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	resume_file_path NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	resume_uploaded_at DATETIME2 NULL, 
	resume_parsing_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	resume_parsing_confidence DECIMAL(5, 2) NULL, 
	resume_last_parsed_at DATETIME2 NULL, 
	duplicate_check_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'not-started'), 
	profile_expires_at DATETIME2 NULL, 
	finalized_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	candidate_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	current_company NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	current_designation NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	preferred_location_text NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	source_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	source_detail NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	social_profiles_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	source_owner_user_id BIGINT NULL, 
	CONSTRAINT [PK__candidat__3213E83FCB8B82B4] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_candidates_lookup] ON candidates (email, phone, intake_stage);
CREATE UNIQUE NONCLUSTERED INDEX [UX_candidates_candidate_code] ON candidates (candidate_code) WHERE ([candidate_code] IS NOT NULL);

CREATE TABLE clients (
	id BIGINT NOT NULL IDENTITY(1,1), 
	location_id BIGINT NOT NULL, 
	parent_client_id BIGINT NULL, 
	client_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	relationship_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	industry NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	business_source_owner_user_id BIGINT NULL, 
	client_owner_user_id BIGINT NULL, 
	primary_contact_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	primary_contact_email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	primary_contact_phone NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_by_user_id BIGINT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__clients__3213E83F5AC41D04] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UX_clients_client_code] ON clients (client_code) WHERE ([client_code] IS NOT NULL);

CREATE TABLE master_data_values (
	id BIGINT NOT NULL IDENTITY(1,1), 
	category_id BIGINT NOT NULL, 
	code NVARCHAR(120) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	sort_order INTEGER NOT NULL DEFAULT ((1)), 
	parent_value_id BIGINT NULL, 
	is_active BIT NOT NULL DEFAULT ((1)), 
	numeric_value_int INTEGER NULL, 
	numeric_value_decimal DECIMAL(10, 2) NULL, 
	text_value NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	metadata_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__master_d__3213E83F25DD59C5] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_master_data_values_category_active_sort] ON master_data_values (category_id, is_active, sort_order, name);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_master_data_values_category_code] ON master_data_values (category_id, code);

CREATE TABLE password_reset_tokens (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	token_hash NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	purpose NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	expires_at DATETIME2 NOT NULL, 
	used_at DATETIME2 NULL, 
	issued_by_user_id BIGINT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__password__3213E83F597E4AF1] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE role_permissions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	role_id BIGINT NOT NULL, 
	permission_id BIGINT NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__role_per__3213E83FD61FBB36] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_role_permissions] ON role_permissions (role_id, permission_id);

CREATE TABLE role_scope_rules (
	id BIGINT NOT NULL IDENTITY(1,1), 
	role_id BIGINT NOT NULL, 
	resource_code NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	scope_value NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__role_sco__3213E83FD3F66B0C] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_role_scope_rules] ON role_scope_rules (role_id, resource_code);

CREATE TABLE role_template_permissions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	role_template_id BIGINT NOT NULL, 
	permission_id BIGINT NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__role_tem__3213E83F9C636C67] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_role_template_permissions] ON role_template_permissions (role_template_id, permission_id);

CREATE TABLE user_extra_permissions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	permission_id BIGINT NOT NULL, 
	granted_by_user_id BIGINT NOT NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__user_ext__3213E83FFE1B8654] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_user_extra_permissions] ON user_extra_permissions (user_id, permission_id);

CREATE TABLE user_invitations (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	invite_email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	credential_setup_method NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	credential_delivery_method NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	temporary_password_hash NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	password_valid_until DATETIME2 NULL, 
	setup_token NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	setup_token_expires_at DATETIME2 NULL, 
	invite_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'draft'), 
	sent_by_user_id BIGINT NOT NULL, 
	sent_at DATETIME2 NULL, 
	accepted_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__user_inv__3213E83F2E23B5FC] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_user_invitations_user_status] ON user_invitations (user_id, invite_status);

CREATE TABLE user_location_roles (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	location_id BIGINT NOT NULL, 
	role_id BIGINT NOT NULL, 
	is_primary BIT NOT NULL DEFAULT ((0)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	start_date DATE NOT NULL, 
	end_date DATE NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__user_loc__3213E83F896D98A3] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_user_location_roles_location_role] ON user_location_roles (location_id, role_id);

CREATE TABLE user_notification_preferences (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	email_enabled BIT NOT NULL DEFAULT ((1)), 
	in_app_enabled BIT NOT NULL DEFAULT ((1)), 
	report_ready_enabled BIT NOT NULL DEFAULT ((1)), 
	approval_alert_enabled BIT NOT NULL DEFAULT ((1)), 
	meeting_follow_up_enabled BIT NOT NULL DEFAULT ((1)), 
	portal_slot_enabled BIT NOT NULL DEFAULT ((1)), 
	daily_update_reminder_enabled BIT NOT NULL DEFAULT ((1)), 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__user_not__3213E83F4FE409D3] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_user_notification_preferences_user] ON user_notification_preferences (user_id);

CREATE TABLE user_sessions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	session_token_hash NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	refresh_token_hash NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	ip_address NVARCHAR(64) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	user_agent NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	expires_at DATETIME2 NOT NULL, 
	revoked_at DATETIME2 NULL, 
	last_seen_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__user_ses__3213E83FBC91D666] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE workflow_action_items (
	id BIGINT NOT NULL IDENTITY(1,1), 
	action_key NVARCHAR(120) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	source NVARCHAR(80) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	title NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	description NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	priority NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'normal'), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'open'), 
	location_id BIGINT NULL, 
	entity_type NVARCHAR(80) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	entity_id BIGINT NULL, 
	age_label NVARCHAR(40) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	primary_action_label NVARCHAR(80) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	secondary_action_label NVARCHAR(80) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	route_href NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	overlay_key NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	assigned_user_id BIGINT NULL, 
	assigned_role_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	due_at DATETIME2 NULL, 
	resolved_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	row_version TIMESTAMP NOT NULL, 
	CONSTRAINT [PK__workflow__3213E83F2E067BDA] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_workflow_action_items_assigned_user] ON workflow_action_items (assigned_user_id, status, due_at);
CREATE NONCLUSTERED INDEX [IX_workflow_action_items_scope_status] ON workflow_action_items (location_id, status, source, priority);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_workflow_action_items_action_key] ON workflow_action_items (action_key);

CREATE TABLE approval_requests (
	id BIGINT NOT NULL IDENTITY(1,1), 
	branch_id BIGINT NOT NULL, 
	request_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	source_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	source_id BIGINT NOT NULL, 
	requested_by_user_id BIGINT NOT NULL, 
	assigned_to_user_id BIGINT NULL, 
	priority NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'medium'), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	decision NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	decision_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	decided_by_user_id BIGINT NULL, 
	decided_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__approval__3213E83F3AE4235A] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_approval_requests_status_priority] ON approval_requests (status, priority);

CREATE TABLE audit_logs (
	id BIGINT NOT NULL IDENTITY(1,1), 
	actor_user_id BIGINT NOT NULL, 
	branch_id BIGINT NULL, 
	entity_type NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	entity_id BIGINT NOT NULL, 
	action_type NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	old_values_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	new_values_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	ip_address NVARCHAR(64) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	user_agent NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__audit_lo__3213E83FB9B89052] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE candidate_documents (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	document_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	file_name NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	file_path NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	verification_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	uploaded_by_user_id BIGINT NOT NULL, 
	verified_by_user_id BIGINT NULL, 
	verified_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83F211D328B] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE candidate_location_transfer_requests (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	from_location_id BIGINT NOT NULL, 
	to_location_id BIGINT NOT NULL, 
	requested_by_user_id BIGINT NOT NULL, 
	approval_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	approved_by_user_id BIGINT NULL, 
	approval_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83F6AE51B3A] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_candidate_location_transfer_requests_status] ON candidate_location_transfer_requests (approval_status, to_location_id);

CREATE TABLE candidate_resume_parse_logs (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	source_document_id BIGINT NULL, 
	parse_job_uuid UNIQUEIDENTIFIER NOT NULL, 
	parser_version NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	raw_text_path NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	parsed_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	field_confidence_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	duplicate_summary_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	review_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	reviewed_by_user_id BIGINT NULL, 
	reviewed_at DATETIME2 NULL, 
	failure_reason NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83FECD99E93] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE candidate_skills (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	skill_name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	experience_years DECIMAL(5, 2) NULL, 
	last_used_year INTEGER NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83F12D81AF2] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE client_access_requests (
	id BIGINT NOT NULL IDENTITY(1,1), 
	client_id BIGINT NOT NULL, 
	requested_by_user_id BIGINT NOT NULL, 
	requesting_location_id BIGINT NOT NULL, 
	approval_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	approved_by_user_id BIGINT NULL, 
	approval_notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__client_a__3213E83F0EAC47A4] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE client_companies (
	id BIGINT NOT NULL IDENTITY(1,1), 
	branch_id BIGINT NOT NULL, 
	parent_client_company_id BIGINT NULL, 
	name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	relationship_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	industry NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	account_manager_user_id BIGINT NULL, 
	primary_contact_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	primary_contact_email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	primary_contact_phone NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	placement_fee_pct DECIMAL(5, 2) NULL, 
	CONSTRAINT [PK__client_c__3213E83F78D7782D] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE pipeline_templates (
	id BIGINT NOT NULL IDENTITY(1,1), 
	client_id BIGINT NULL, 
	location_id BIGINT NULL, 
	template_name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	stage_scope NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'client'), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_by_user_id BIGINT NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__pipeline__3213E83F6CCF6BB0] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE portal_accounts (
	id BIGINT NOT NULL IDENTITY(1,1), 
	branch_id BIGINT NOT NULL, 
	platform_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	account_name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	login_identifier NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	ownership_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	owned_by_user_id BIGINT NULL, 
	is_shared BIT NOT NULL DEFAULT ((1)), 
	has_full_access BIT NOT NULL DEFAULT ((0)), 
	daily_usage_limit_hours DECIMAL(5, 2) NULL, 
	notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__portal_a__3213E83FA0E9EB9A] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE recruiter_daily_updates (
	id BIGINT NOT NULL IDENTITY(1,1), 
	branch_id BIGINT NOT NULL, 
	submitted_by_user_id BIGINT NOT NULL, 
	update_date DATE NOT NULL, 
	summary NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	blockers NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	planned_next_actions NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	portal_usage_summary NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	high_priority_roles_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	candidate_movements_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	internal_call_count INTEGER NULL, 
	profiles_escalated_count INTEGER NULL, 
	hiring_type_summary_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	submitted_at DATETIME2 NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__recruite__3213E83F8D103064] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_recruiter_daily_updates_user_date] ON recruiter_daily_updates (submitted_by_user_id, update_date);

CREATE TABLE report_locks (
	id BIGINT NOT NULL IDENTITY(1,1), 
	report_scope NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	branch_id BIGINT NULL, 
	report_type NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	lock_status NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'open'), 
	locked_by_user_id BIGINT NULL, 
	locked_at DATETIME2 NULL, 
	reopened_by_user_id BIGINT NULL, 
	reopened_at DATETIME2 NULL, 
	notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__report_l__3213E83F9BF92391] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_report_locks_scope_period] ON report_locks (report_scope, report_type, period_start, period_end);

CREATE TABLE reports (
	id BIGINT NOT NULL IDENTITY(1,1), 
	branch_id BIGINT NULL, 
	submitted_by_user_id BIGINT NULL, 
	report_scope NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	report_type NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'draft'), 
	quality_score DECIMAL(5, 2) NULL, 
	submitted_at DATETIME2 NULL, 
	reviewed_by_user_id BIGINT NULL, 
	reviewed_at DATETIME2 NULL, 
	summary_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	generated_by_system BIT NOT NULL DEFAULT ((0)), 
	report_rules_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	generated_from_daily_inputs BIT NOT NULL DEFAULT ((1)), 
	generation_job_id BIGINT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__reports__3213E83F09532D07] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE user_branch_roles (
	id BIGINT NOT NULL IDENTITY(1,1), 
	user_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	role_id BIGINT NOT NULL, 
	is_primary BIT NOT NULL DEFAULT ((0)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	start_date DATE NOT NULL, 
	end_date DATE NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__user_bra__3213E83FB1B5B3C3] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_user_branch_roles_branch_role] ON user_branch_roles (branch_id, role_id);

CREATE TABLE workflow_action_events (
	id BIGINT NOT NULL IDENTITY(1,1), 
	action_item_id BIGINT NULL, 
	overlay_key NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	actor_user_id BIGINT NOT NULL, 
	action_type NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	event_status NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	payload_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	next_route_href NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__workflow__3213E83F524567AE] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_workflow_action_events_item] ON workflow_action_events (action_item_id, created_at);

CREATE TABLE candidate_duplicate_checks (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	parse_log_id BIGINT NULL, 
	matched_candidate_id BIGINT NOT NULL, 
	match_score DECIMAL(5, 2) NOT NULL, 
	match_level NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	match_reason_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	decision_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	decided_by_user_id BIGINT NULL, 
	decided_at DATETIME2 NULL, 
	decision_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83F563839A5] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_candidate_duplicate_checks_candidate_status] ON candidate_duplicate_checks (candidate_id, decision_status);

CREATE TABLE client_contacts (
	id BIGINT NOT NULL IDENTITY(1,1), 
	client_company_id BIGINT NOT NULL, 
	full_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	designation NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	email NVARCHAR(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	phone NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	is_primary BIT NOT NULL DEFAULT ((0)), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	location_id BIGINT NULL, 
	is_secondary BIT NOT NULL DEFAULT ((0)), 
	created_by_user_id BIGINT NULL, 
	CONSTRAINT [PK__client_c__3213E83FC2D94F05] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE pipeline_template_stages (
	id BIGINT NOT NULL IDENTITY(1,1), 
	pipeline_template_id BIGINT NOT NULL, 
	stage_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	stage_name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	stage_order INTEGER NOT NULL, 
	stage_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'normal'), 
	allows_rejection BIT NOT NULL DEFAULT ((1)), 
	reminder_rule_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__pipeline__3213E83F7B0CC4A9] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_pipeline_template_stages] ON pipeline_template_stages (pipeline_template_id, stage_code);

CREATE TABLE portal_account_slots (
	id BIGINT NOT NULL IDENTITY(1,1), 
	portal_account_id BIGINT NOT NULL, 
	assigned_user_id BIGINT NOT NULL, 
	usage_date DATE NOT NULL, 
	start_time TIME NOT NULL, 
	end_time TIME NOT NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'planned'), 
	approved_by_user_id BIGINT NULL, 
	notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__portal_a__3213E83F549DFAE7] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_portal_account_slots_account_date] ON portal_account_slots (portal_account_id, usage_date);

CREATE TABLE duplicate_review_cases (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	candidate_duplicate_check_id BIGINT NULL, 
	draft_candidate_snapshot_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	existing_candidate_snapshot_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	requested_by_user_id BIGINT NOT NULL, 
	assigned_reviewer_user_id BIGINT NULL, 
	decision_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	decision_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	approved_by_user_id BIGINT NULL, 
	approved_at DATETIME2 NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__duplicat__3213E83F228904CD] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_duplicate_review_cases_status] ON duplicate_review_cases (decision_status, requested_by_user_id);

CREATE TABLE requisitions (
	id BIGINT NOT NULL IDENTITY(1,1), 
	branch_id BIGINT NOT NULL, 
	hiring_type NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	client_company_id BIGINT NULL, 
	department_name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	title NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	owner_user_id BIGINT NOT NULL, 
	priority NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'medium'), 
	priority_score DECIMAL(10, 2) NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'draft'), 
	open_positions INTEGER NOT NULL, 
	target_close_date DATE NOT NULL, 
	sla_days INTEGER NULL, 
	criticality NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	difficulty NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	client_round_required BIT NOT NULL DEFAULT ((0)), 
	budget_min DECIMAL(18, 2) NULL, 
	budget_max DECIMAL(18, 2) NULL, 
	currency_code NVARCHAR(10) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	job_description NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	important_notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	structured_jd_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	requisition_code NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	client_id BIGINT NULL, 
	primary_owner_user_id BIGINT NULL, 
	primary_contact_id BIGINT NULL, 
	secondary_contact_id BIGINT NULL, 
	delivery_owner_user_id BIGINT NULL, 
	acceptable_career_gap_months INTEGER NULL, 
	preferred_update_time_text NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_by_user_id BIGINT NULL, 
	employment_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	work_mode NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	pipeline_template_id BIGINT NULL, 
	CONSTRAINT [PK__requisit__3213E83FEDE3C952] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_requisitions_branch_status_close_date] ON requisitions (branch_id, status, target_close_date);

CREATE TABLE candidate_applications (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_id BIGINT NOT NULL, 
	requisition_id BIGINT NOT NULL, 
	owner_user_id BIGINT NOT NULL, 
	current_stage NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	screening_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'pending'), 
	application_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	stage_reason NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	applied_at DATETIME2 NOT NULL, 
	stage_updated_at DATETIME2 NOT NULL, 
	expected_joining_date DATE NULL, 
	rejection_side NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'none'), 
	rejection_stage NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	rejection_reason NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	rejected_by_user_id BIGINT NULL, 
	client_feedback_status NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	client_feedback_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	client_feedback_received_at DATETIME2 NULL, 
	client_feedback_recorded_by_user_id BIGINT NULL, 
	profiles_escalated_at DATETIME2 NULL, 
	client_duplicate_flag BIT NOT NULL DEFAULT ((0)), 
	client_duplicate_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	risk_flags_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	submitted_by_user_id BIGINT NULL, 
	last_activity_at DATETIME2 NULL, 
	stale_after_days INTEGER NULL, 
	offer_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	offered_ctc DECIMAL(18, 2) NULL, 
	offer_currency NVARCHAR(10) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	signing_bonus DECIMAL(18, 2) NULL, 
	offer_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	offer_created_at DATETIME2 NULL, 
	offer_sent_at DATETIME2 NULL, 
	pipeline_template_id BIGINT NULL, 
	CONSTRAINT [PK__candidat__3213E83F5DB103C2] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_candidate_applications_requisition_stage] ON candidate_applications (requisition_id, current_stage);

CREATE TABLE daily_updates (
	id BIGINT NOT NULL IDENTITY(1,1), 
	location_id BIGINT NOT NULL, 
	submitted_by_user_id BIGINT NOT NULL, 
	requisition_id BIGINT NULL, 
	update_date DATE NOT NULL, 
	summary NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	profiles_sourced_count INTEGER NULL, 
	profiles_screened_count INTEGER NULL, 
	profiles_submitted_count INTEGER NULL, 
	interviews_scheduled_count INTEGER NULL, 
	offers_closed_count INTEGER NULL, 
	blockers NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	planned_next_actions NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	portal_usage_summary NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	high_priority_roles_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	candidate_movements_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	internal_call_count INTEGER NULL, 
	profiles_escalated_count INTEGER NULL, 
	hiring_type_summary_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	submission_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'submitted'), 
	reviewed_by_user_id BIGINT NULL, 
	reviewed_at DATETIME2 NULL, 
	submitted_at DATETIME2 NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__daily_up__3213E83F37D6E63C] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_daily_updates_requisition_date] ON daily_updates (requisition_id, update_date);
CREATE NONCLUSTERED INDEX [IX_daily_updates_user_date] ON daily_updates (submitted_by_user_id, update_date);

CREATE TABLE requisition_assignments (
	id BIGINT NOT NULL IDENTITY(1,1), 
	location_id BIGINT NOT NULL, 
	requisition_id BIGINT NOT NULL, 
	assigned_user_id BIGINT NOT NULL, 
	assignment_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	assigned_by_user_id BIGINT NOT NULL, 
	assigned_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'active'), 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__requisit__3213E83FAB13707E] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UX_requisition_assignments_active_unique] ON requisition_assignments (requisition_id, assigned_user_id, assignment_type) WHERE ([status]=N'active');

CREATE TABLE requisition_documents_required (
	id BIGINT NOT NULL IDENTITY(1,1), 
	requisition_id BIGINT NOT NULL, 
	document_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	is_mandatory BIT NOT NULL DEFAULT ((1)), 
	notes NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__requisit__3213E83FD6B67007] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE requisition_end_clients (
	id BIGINT NOT NULL IDENTITY(1,1), 
	requisition_id BIGINT NOT NULL, 
	client_company_id BIGINT NOT NULL, 
	end_client_company_id BIGINT NOT NULL, 
	is_primary BIT NOT NULL DEFAULT ((0)), 
	notes NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__requisit__3213E83F8B69165C] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_requisition_end_clients] ON requisition_end_clients (requisition_id, end_client_company_id);

CREATE TABLE requisition_screening_rules (
	id BIGINT NOT NULL IDENTITY(1,1), 
	requisition_id BIGINT NOT NULL, 
	allowed_gap_min_months INTEGER NULL, 
	allowed_gap_max_months INTEGER NULL, 
	max_notice_period_days INTEGER NULL, 
	document_rules_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	compensation_rules_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	location_rules_json NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	custom_notes NVARCHAR(max) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__requisit__3213E83F4A0D5CBB] PRIMARY KEY CLUSTERED (id)
);
CREATE UNIQUE NONCLUSTERED INDEX [UQ_requisition_screening_rules_requisition] ON requisition_screening_rules (requisition_id);

CREATE TABLE requisition_skill_requirements (
	id BIGINT NOT NULL IDENTITY(1,1), 
	requisition_id BIGINT NOT NULL, 
	skill_name NVARCHAR(150) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	skill_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	priority_order INTEGER NOT NULL DEFAULT ((1)), 
	notes NVARCHAR(500) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__requisit__3213E83F779918DD] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE candidate_screening_checks (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_application_id BIGINT NOT NULL, 
	check_type NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	expected_value NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	actual_value NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	result NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	checked_by_user_id BIGINT NOT NULL, 
	checked_at DATETIME2 NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83FABD1B3A4] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE candidate_stage_history (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_application_id BIGINT NOT NULL, 
	from_stage NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	to_stage NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	change_reason NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	changed_by_user_id BIGINT NOT NULL, 
	changed_at DATETIME2 NOT NULL, 
	source_type NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__candidat__3213E83F44867EE0] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE interview_rounds (
	id BIGINT NOT NULL IDENTITY(1,1), 
	candidate_application_id BIGINT NOT NULL, 
	round_type NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	round_name NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	scheduled_at DATETIME2 NULL, 
	interviewer_name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	interviewer_user_id BIGINT NULL, 
	status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL DEFAULT (N'scheduled'), 
	feedback_status NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	decision NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	feedback_notes NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	created_by_user_id BIGINT NOT NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__intervie__3213E83F61D3965E] PRIMARY KEY CLUSTERED (id)
);

CREATE TABLE report_rows (
	id BIGINT NOT NULL IDENTITY(1,1), 
	report_id BIGINT NOT NULL, 
	report_scope NVARCHAR(30) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	report_type NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL, 
	row_date DATE NOT NULL, 
	recruiter_user_id BIGINT NULL, 
	hr_user_id BIGINT NULL, 
	manager_user_id BIGINT NULL, 
	candidate_id BIGINT NULL, 
	candidate_application_id BIGINT NULL, 
	client_company_id BIGINT NULL, 
	requisition_id BIGINT NULL, 
	role_title NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	employment_type NVARCHAR(20) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	current_status NVARCHAR(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	internal_screen_reject BIT NOT NULL DEFAULT ((0)), 
	client_reject BIT NOT NULL DEFAULT ((0)), 
	l1_status NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	l2_status NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	interview_mode NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	offer_letter_status NVARCHAR(50) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	date_of_joining DATE NULL, 
	remarks NVARCHAR(1000) COLLATE SQL_Latin1_General_CP1_CI_AS NULL, 
	profiles_escalated_count INTEGER NULL, 
	internal_call_count INTEGER NULL, 
	created_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	updated_at DATETIME2 NOT NULL DEFAULT (sysutcdatetime()), 
	CONSTRAINT [PK__report_r__3213E83F18295C14] PRIMARY KEY CLUSTERED (id)
);
CREATE NONCLUSTERED INDEX [IX_report_rows_report_id] ON report_rows (report_id);


-- Pass 2: foreign keys (sorted by constraint name for stable diffs)

ALTER TABLE [dbo].[approval_requests] ADD CONSTRAINT [FK_approval_requests_assigned_to] FOREIGN KEY ([assigned_to_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[approval_requests] ADD CONSTRAINT [FK_approval_requests_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[approval_requests] ADD CONSTRAINT [FK_approval_requests_decided_by] FOREIGN KEY ([decided_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[approval_requests] ADD CONSTRAINT [FK_approval_requests_requested_by] FOREIGN KEY ([requested_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[approvals] ADD CONSTRAINT [FK_approvals_decision] FOREIGN KEY ([decision_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[approvals] ADD CONSTRAINT [FK_approvals_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[approvals] ADD CONSTRAINT [FK_approvals_requester] FOREIGN KEY ([requester_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[approvals] ADD CONSTRAINT [FK_approvals_reviewer] FOREIGN KEY ([assigned_reviewer_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[agent_runs] ADD CONSTRAINT [FK_agent_runs_actor] FOREIGN KEY ([actor_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[agent_runs] ADD CONSTRAINT [FK_agent_runs_decided_by] FOREIGN KEY ([decided_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[agent_runs] ADD CONSTRAINT [FK_agent_runs_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[audit_log_access_events] ADD CONSTRAINT [FK_audit_log_access_events_accessed_user] FOREIGN KEY ([accessed_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[audit_log_access_events] ADD CONSTRAINT [FK_audit_log_access_events_actor] FOREIGN KEY ([actor_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[audit_log_access_events] ADD CONSTRAINT [FK_audit_log_access_events_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[audit_logs] ADD CONSTRAINT [FK_audit_logs_actor] FOREIGN KEY ([actor_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[audit_logs] ADD CONSTRAINT [FK_audit_logs_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[automation_jobs] ADD CONSTRAINT [FK_automation_jobs_triggered_by] FOREIGN KEY ([triggered_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[branches] ADD CONSTRAINT [FK_branches_manager_user] FOREIGN KEY ([manager_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_feedback_recorded_by] FOREIGN KEY ([client_feedback_recorded_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_owner] FOREIGN KEY ([owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_pipeline_template] FOREIGN KEY ([pipeline_template_id]) REFERENCES [dbo].[pipeline_templates] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_rejected_by] FOREIGN KEY ([rejected_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[candidate_applications] ADD CONSTRAINT [FK_candidate_applications_submitted_by] FOREIGN KEY ([submitted_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_documents] ADD CONSTRAINT [FK_candidate_documents_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_documents] ADD CONSTRAINT [FK_candidate_documents_uploaded_by] FOREIGN KEY ([uploaded_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_documents] ADD CONSTRAINT [FK_candidate_documents_verified_by] FOREIGN KEY ([verified_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_duplicate_checks] ADD CONSTRAINT [FK_candidate_duplicate_checks_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_duplicate_checks] ADD CONSTRAINT [FK_candidate_duplicate_checks_decided_by] FOREIGN KEY ([decided_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_duplicate_checks] ADD CONSTRAINT [FK_candidate_duplicate_checks_matched_candidate] FOREIGN KEY ([matched_candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_duplicate_checks] ADD CONSTRAINT [FK_candidate_duplicate_checks_parse_log] FOREIGN KEY ([parse_log_id]) REFERENCES [dbo].[candidate_resume_parse_logs] ([id]);
ALTER TABLE [dbo].[candidate_location_transfer_requests] ADD CONSTRAINT [FK_candidate_location_transfer_requests_approved_by] FOREIGN KEY ([approved_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_location_transfer_requests] ADD CONSTRAINT [FK_candidate_location_transfer_requests_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_location_transfer_requests] ADD CONSTRAINT [FK_candidate_location_transfer_requests_from_location] FOREIGN KEY ([from_location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[candidate_location_transfer_requests] ADD CONSTRAINT [FK_candidate_location_transfer_requests_requested_by] FOREIGN KEY ([requested_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_location_transfer_requests] ADD CONSTRAINT [FK_candidate_location_transfer_requests_to_location] FOREIGN KEY ([to_location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[candidate_resume_parse_logs] ADD CONSTRAINT [FK_candidate_resume_parse_logs_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_resume_parse_logs] ADD CONSTRAINT [FK_candidate_resume_parse_logs_reviewed_by] FOREIGN KEY ([reviewed_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_screening_checks] ADD CONSTRAINT [FK_candidate_screening_checks_application] FOREIGN KEY ([candidate_application_id]) REFERENCES [dbo].[candidate_applications] ([id]);
ALTER TABLE [dbo].[candidate_screening_checks] ADD CONSTRAINT [FK_candidate_screening_checks_checked_by] FOREIGN KEY ([checked_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidate_skills] ADD CONSTRAINT [FK_candidate_skills_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[candidate_stage_history] ADD CONSTRAINT [FK_candidate_stage_history_application] FOREIGN KEY ([candidate_application_id]) REFERENCES [dbo].[candidate_applications] ([id]);
ALTER TABLE [dbo].[candidate_stage_history] ADD CONSTRAINT [FK_candidate_stage_history_changed_by] FOREIGN KEY ([changed_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidates] ADD CONSTRAINT [FK_candidates_created_by] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidates] ADD CONSTRAINT [FK_candidates_primary_owner] FOREIGN KEY ([primary_owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[candidates] ADD CONSTRAINT [FK_candidates_source_owner] FOREIGN KEY ([source_owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[client_access_requests] ADD CONSTRAINT [FK_client_access_requests_approved_by] FOREIGN KEY ([approved_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[client_access_requests] ADD CONSTRAINT [FK_client_access_requests_client] FOREIGN KEY ([client_id]) REFERENCES [dbo].[clients] ([id]);
ALTER TABLE [dbo].[client_access_requests] ADD CONSTRAINT [FK_client_access_requests_requested_by] FOREIGN KEY ([requested_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[client_access_requests] ADD CONSTRAINT [FK_client_access_requests_requesting_location] FOREIGN KEY ([requesting_location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[client_companies] ADD CONSTRAINT [FK_client_companies_account_manager] FOREIGN KEY ([account_manager_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[client_companies] ADD CONSTRAINT [FK_client_companies_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[client_companies] ADD CONSTRAINT [FK_client_companies_parent] FOREIGN KEY ([parent_client_company_id]) REFERENCES [dbo].[client_companies] ([id]);
ALTER TABLE [dbo].[client_contacts] ADD CONSTRAINT [FK_client_contacts_client_company] FOREIGN KEY ([client_company_id]) REFERENCES [dbo].[client_companies] ([id]);
ALTER TABLE [dbo].[client_contacts] ADD CONSTRAINT [FK_client_contacts_created_by] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[client_contacts] ADD CONSTRAINT [FK_client_contacts_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[clients] ADD CONSTRAINT [FK_clients_business_source_owner] FOREIGN KEY ([business_source_owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[clients] ADD CONSTRAINT [FK_clients_created_by] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[clients] ADD CONSTRAINT [FK_clients_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[clients] ADD CONSTRAINT [FK_clients_owner] FOREIGN KEY ([client_owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[clients] ADD CONSTRAINT [FK_clients_parent] FOREIGN KEY ([parent_client_id]) REFERENCES [dbo].[clients] ([id]);
ALTER TABLE [dbo].[daily_updates] ADD CONSTRAINT [FK_daily_updates_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[daily_updates] ADD CONSTRAINT [FK_daily_updates_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[daily_updates] ADD CONSTRAINT [FK_daily_updates_reviewed_by] FOREIGN KEY ([reviewed_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[daily_updates] ADD CONSTRAINT [FK_daily_updates_submitted_by] FOREIGN KEY ([submitted_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[duplicate_review_cases] ADD CONSTRAINT [FK_duplicate_review_cases_approved_by] FOREIGN KEY ([approved_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[duplicate_review_cases] ADD CONSTRAINT [FK_duplicate_review_cases_assigned_reviewer] FOREIGN KEY ([assigned_reviewer_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[duplicate_review_cases] ADD CONSTRAINT [FK_duplicate_review_cases_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[duplicate_review_cases] ADD CONSTRAINT [FK_duplicate_review_cases_duplicate_check] FOREIGN KEY ([candidate_duplicate_check_id]) REFERENCES [dbo].[candidate_duplicate_checks] ([id]);
ALTER TABLE [dbo].[duplicate_review_cases] ADD CONSTRAINT [FK_duplicate_review_cases_requested_by] FOREIGN KEY ([requested_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[interview_rounds] ADD CONSTRAINT [FK_interview_rounds_application] FOREIGN KEY ([candidate_application_id]) REFERENCES [dbo].[candidate_applications] ([id]);
ALTER TABLE [dbo].[interview_rounds] ADD CONSTRAINT [FK_interview_rounds_created_by] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[interview_rounds] ADD CONSTRAINT [FK_interview_rounds_interviewer_user] FOREIGN KEY ([interviewer_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[locations] ADD CONSTRAINT [FK_locations_location_head_user] FOREIGN KEY ([location_head_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[master_data_values] ADD CONSTRAINT [FK_master_data_values_category] FOREIGN KEY ([category_id]) REFERENCES [dbo].[master_data_categories] ([id]);
ALTER TABLE [dbo].[master_data_values] ADD CONSTRAINT [FK_master_data_values_parent] FOREIGN KEY ([parent_value_id]) REFERENCES [dbo].[master_data_values] ([id]);
ALTER TABLE [dbo].[password_reset_tokens] ADD CONSTRAINT [FK_password_reset_tokens_issued_by] FOREIGN KEY ([issued_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[password_reset_tokens] ADD CONSTRAINT [FK_password_reset_tokens_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[pipeline_template_stages] ADD CONSTRAINT [FK_pipeline_template_stages_template] FOREIGN KEY ([pipeline_template_id]) REFERENCES [dbo].[pipeline_templates] ([id]);
ALTER TABLE [dbo].[pipeline_templates] ADD CONSTRAINT [FK_pipeline_templates_client] FOREIGN KEY ([client_id]) REFERENCES [dbo].[clients] ([id]);
ALTER TABLE [dbo].[pipeline_templates] ADD CONSTRAINT [FK_pipeline_templates_created_by] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[pipeline_templates] ADD CONSTRAINT [FK_pipeline_templates_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[portal_account_slots] ADD CONSTRAINT [FK_portal_account_slots_approved_by] FOREIGN KEY ([approved_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[portal_account_slots] ADD CONSTRAINT [FK_portal_account_slots_assigned_user] FOREIGN KEY ([assigned_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[portal_account_slots] ADD CONSTRAINT [FK_portal_account_slots_portal_account] FOREIGN KEY ([portal_account_id]) REFERENCES [dbo].[portal_accounts] ([id]);
ALTER TABLE [dbo].[portal_accounts] ADD CONSTRAINT [FK_portal_accounts_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[portal_accounts] ADD CONSTRAINT [FK_portal_accounts_owned_by] FOREIGN KEY ([owned_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[recruiter_daily_updates] ADD CONSTRAINT [FK_recruiter_daily_updates_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[recruiter_daily_updates] ADD CONSTRAINT [FK_recruiter_daily_updates_submitted_by] FOREIGN KEY ([submitted_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[report_locks] ADD CONSTRAINT [FK_report_locks_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[report_locks] ADD CONSTRAINT [FK_report_locks_locked_by] FOREIGN KEY ([locked_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[report_locks] ADD CONSTRAINT [FK_report_locks_reopened_by] FOREIGN KEY ([reopened_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_candidate] FOREIGN KEY ([candidate_id]) REFERENCES [dbo].[candidates] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_candidate_application] FOREIGN KEY ([candidate_application_id]) REFERENCES [dbo].[candidate_applications] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_client_company] FOREIGN KEY ([client_company_id]) REFERENCES [dbo].[client_companies] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_hr] FOREIGN KEY ([hr_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_manager] FOREIGN KEY ([manager_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_recruiter] FOREIGN KEY ([recruiter_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_report] FOREIGN KEY ([report_id]) REFERENCES [dbo].[reports] ([id]);
ALTER TABLE [dbo].[report_rows] ADD CONSTRAINT [FK_report_rows_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[reports] ADD CONSTRAINT [FK_reports_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[reports] ADD CONSTRAINT [FK_reports_generation_job] FOREIGN KEY ([generation_job_id]) REFERENCES [dbo].[automation_jobs] ([id]);
ALTER TABLE [dbo].[reports] ADD CONSTRAINT [FK_reports_reviewed_by] FOREIGN KEY ([reviewed_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[reports] ADD CONSTRAINT [FK_reports_submitted_by] FOREIGN KEY ([submitted_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisition_assignments] ADD CONSTRAINT [FK_requisition_assignments_assigned_by] FOREIGN KEY ([assigned_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisition_assignments] ADD CONSTRAINT [FK_requisition_assignments_assigned_user] FOREIGN KEY ([assigned_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisition_assignments] ADD CONSTRAINT [FK_requisition_assignments_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[requisition_assignments] ADD CONSTRAINT [FK_requisition_assignments_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[requisition_documents_required] ADD CONSTRAINT [FK_requisition_documents_required_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[requisition_end_clients] ADD CONSTRAINT [FK_requisition_end_clients_client] FOREIGN KEY ([client_company_id]) REFERENCES [dbo].[client_companies] ([id]);
ALTER TABLE [dbo].[requisition_end_clients] ADD CONSTRAINT [FK_requisition_end_clients_end_client] FOREIGN KEY ([end_client_company_id]) REFERENCES [dbo].[client_companies] ([id]);
ALTER TABLE [dbo].[requisition_end_clients] ADD CONSTRAINT [FK_requisition_end_clients_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[requisition_screening_rules] ADD CONSTRAINT [FK_requisition_screening_rules_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[requisition_skill_requirements] ADD CONSTRAINT [FK_requisition_skill_requirements_requisition] FOREIGN KEY ([requisition_id]) REFERENCES [dbo].[requisitions] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_client] FOREIGN KEY ([client_id]) REFERENCES [dbo].[clients] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_client_company] FOREIGN KEY ([client_company_id]) REFERENCES [dbo].[client_companies] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_created_by] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_delivery_owner] FOREIGN KEY ([delivery_owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_owner] FOREIGN KEY ([owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_pipeline_template] FOREIGN KEY ([pipeline_template_id]) REFERENCES [dbo].[pipeline_templates] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_primary_contact] FOREIGN KEY ([primary_contact_id]) REFERENCES [dbo].[client_contacts] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_primary_owner] FOREIGN KEY ([primary_owner_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[requisitions] ADD CONSTRAINT [FK_requisitions_secondary_contact] FOREIGN KEY ([secondary_contact_id]) REFERENCES [dbo].[client_contacts] ([id]);
ALTER TABLE [dbo].[role_permissions] ADD CONSTRAINT [FK_role_permissions_permission] FOREIGN KEY ([permission_id]) REFERENCES [dbo].[permissions] ([id]);
ALTER TABLE [dbo].[role_permissions] ADD CONSTRAINT [FK_role_permissions_role] FOREIGN KEY ([role_id]) REFERENCES [dbo].[roles] ([id]);
ALTER TABLE [dbo].[role_scope_rules] ADD CONSTRAINT [FK_role_scope_rules_role] FOREIGN KEY ([role_id]) REFERENCES [dbo].[roles] ([id]);
ALTER TABLE [dbo].[role_template_permissions] ADD CONSTRAINT [FK_role_template_permissions_permission] FOREIGN KEY ([permission_id]) REFERENCES [dbo].[permissions] ([id]);
ALTER TABLE [dbo].[role_template_permissions] ADD CONSTRAINT [FK_role_template_permissions_template] FOREIGN KEY ([role_template_id]) REFERENCES [dbo].[role_templates] ([id]);
ALTER TABLE [dbo].[roles] ADD CONSTRAINT [FK_roles_created_by_user] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_branch_roles] ADD CONSTRAINT [FK_user_branch_roles_branch] FOREIGN KEY ([branch_id]) REFERENCES [dbo].[branches] ([id]);
ALTER TABLE [dbo].[user_branch_roles] ADD CONSTRAINT [FK_user_branch_roles_role] FOREIGN KEY ([role_id]) REFERENCES [dbo].[roles] ([id]);
ALTER TABLE [dbo].[user_branch_roles] ADD CONSTRAINT [FK_user_branch_roles_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_extra_permissions] ADD CONSTRAINT [FK_user_extra_permissions_granted_by] FOREIGN KEY ([granted_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_extra_permissions] ADD CONSTRAINT [FK_user_extra_permissions_permission] FOREIGN KEY ([permission_id]) REFERENCES [dbo].[permissions] ([id]);
ALTER TABLE [dbo].[user_extra_permissions] ADD CONSTRAINT [FK_user_extra_permissions_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_invitations] ADD CONSTRAINT [FK_user_invitations_sent_by] FOREIGN KEY ([sent_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_invitations] ADD CONSTRAINT [FK_user_invitations_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_location_roles] ADD CONSTRAINT [FK_user_location_roles_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[user_location_roles] ADD CONSTRAINT [FK_user_location_roles_role] FOREIGN KEY ([role_id]) REFERENCES [dbo].[roles] ([id]);
ALTER TABLE [dbo].[user_location_roles] ADD CONSTRAINT [FK_user_location_roles_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_notification_preferences] ADD CONSTRAINT [FK_user_notification_preferences_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[user_sessions] ADD CONSTRAINT [FK_user_sessions_user] FOREIGN KEY ([user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[users] ADD CONSTRAINT [FK_users_created_by_user] FOREIGN KEY ([created_by_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[users] ADD CONSTRAINT [FK_users_default_role] FOREIGN KEY ([default_role_id]) REFERENCES [dbo].[roles] ([id]);
ALTER TABLE [dbo].[users] ADD CONSTRAINT [FK_users_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
ALTER TABLE [dbo].[users] ADD CONSTRAINT [FK_users_primary_role] FOREIGN KEY ([primary_role_id]) REFERENCES [dbo].[roles] ([id]);
ALTER TABLE [dbo].[users] ADD CONSTRAINT [FK_users_reporting_manager] FOREIGN KEY ([reporting_manager_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[workflow_action_events] ADD CONSTRAINT [FK_workflow_action_events_actor] FOREIGN KEY ([actor_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[workflow_action_events] ADD CONSTRAINT [FK_workflow_action_events_item] FOREIGN KEY ([action_item_id]) REFERENCES [dbo].[workflow_action_items] ([id]);
ALTER TABLE [dbo].[workflow_action_items] ADD CONSTRAINT [FK_workflow_action_items_assigned_user] FOREIGN KEY ([assigned_user_id]) REFERENCES [dbo].[users] ([id]);
ALTER TABLE [dbo].[workflow_action_items] ADD CONSTRAINT [FK_workflow_action_items_location] FOREIGN KEY ([location_id]) REFERENCES [dbo].[locations] ([id]);
