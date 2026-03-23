-- QAstra Database Setup Script
-- Run this script in DBeaver to create the database and all tables

-- =====================================================
-- CREATE DATABASE (run this separately if needed)
-- =====================================================
-- CREATE DATABASE qastra;

-- =====================================================
-- CONNECT TO qastra DATABASE BEFORE RUNNING BELOW
-- =====================================================

-- Create ENUM types
DO $$
BEGIN
    -- User Role
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
        CREATE TYPE userrole AS ENUM ('admin', 'manager', 'tester', 'viewer');
    END IF;
    
    -- Requirement Source Type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'requirementsourcetype') THEN
        CREATE TYPE requirementsourcetype AS ENUM ('upload', 'jira', 'azure_devops', 'confluence', 'manual');
    END IF;
    
    -- Test Case Priority
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'testcasepriority') THEN
        CREATE TYPE testcasepriority AS ENUM ('critical', 'high', 'medium', 'low');
    END IF;
    
    -- Test Case Category
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'testcasecategory') THEN
        CREATE TYPE testcasecategory AS ENUM ('smoke', 'regression', 'e2e', 'integration', 'sanity');
    END IF;
    
    -- Test Case Status
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'testcasestatus') THEN
        CREATE TYPE testcasestatus AS ENUM ('draft', 'ready', 'deprecated');
    END IF;
    
    -- Test Step Action
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'teststepaction') THEN
        CREATE TYPE teststepaction AS ENUM (
            'navigate', 'click', 'type', 'fill', 'select', 'check', 'uncheck',
            'hover', 'screenshot', 'wait', 'assert_text', 'assert_visible',
            'assert_url', 'assert_title', 'custom'
        );
    END IF;
    
    -- Test Run Status
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'testrunstatus') THEN
        CREATE TYPE testrunstatus AS ENUM ('pending', 'running', 'passed', 'failed', 'cancelled', 'error');
    END IF;
    
    -- Test Result Status
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'testresultstatus') THEN
        CREATE TYPE testresultstatus AS ENUM ('passed', 'failed', 'skipped', 'error');
    END IF;
END$$;

-- =====================================================
-- ORGANIZATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role userrole DEFAULT 'tester' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- =====================================================
-- PROJECTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    app_url VARCHAR(500),
    app_credentials JSONB,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    organization_id INTEGER REFERENCES organizations(id),
    jira_project_key VARCHAR(50),
    azure_devops_project VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- =====================================================
-- REQUIREMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source_type requirementsourcetype DEFAULT 'manual',
    source_url VARCHAR(1000),
    source_id VARCHAR(100),
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_requirements_project ON requirements(project_id);

-- =====================================================
-- TEST CASES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    requirement_id INTEGER REFERENCES requirements(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    preconditions TEXT,
    priority testcasepriority DEFAULT 'medium',
    category testcasecategory DEFAULT 'regression',
    status testcasestatus DEFAULT 'draft',
    tags VARCHAR(500),
    is_automated BOOLEAN DEFAULT TRUE,
    is_generated BOOLEAN DEFAULT FALSE,
    generation_prompt TEXT,
    created_by INTEGER REFERENCES users(id),
    jira_key VARCHAR(50),
    azure_devops_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_test_cases_project ON test_cases(project_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_requirement ON test_cases(requirement_id);

-- =====================================================
-- TEST STEPS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS test_steps (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    action teststepaction NOT NULL,
    target VARCHAR(500),
    value TEXT,
    description TEXT,
    expected_result TEXT,
    playwright_code TEXT,
    selector_type VARCHAR(50),
    selector_confidence INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_test_steps_test_case ON test_steps(test_case_id);

-- =====================================================
-- TEST RUNS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS test_runs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name VARCHAR(255),
    description VARCHAR(1000),
    status testrunstatus DEFAULT 'pending',
    triggered_by INTEGER REFERENCES users(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    browser VARCHAR(50) DEFAULT 'chromium',
    headless VARCHAR(10) DEFAULT 'true',
    config JSONB,
    report_path VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_test_runs_project ON test_runs(project_id);

-- =====================================================
-- TEST RESULTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    test_run_id INTEGER NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    test_case_id INTEGER NOT NULL REFERENCES test_cases(id),
    status testresultstatus NOT NULL,
    duration_ms INTEGER,
    error_message TEXT,
    error_stack TEXT,
    failed_step INTEGER,
    screenshot_path VARCHAR(500),
    video_path VARCHAR(500),
    trace_path VARCHAR(500),
    step_results JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_test_results_run ON test_results(test_run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_test_case ON test_results(test_case_id);

-- =====================================================
-- AUDIT LOGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INTEGER,
    description TEXT,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

-- =====================================================
-- PROJECT INTEGRATIONS TABLE
-- =====================================================
DO $$
BEGIN
    -- Integration Type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integrationtype') THEN
        CREATE TYPE integrationtype AS ENUM ('jira', 'redmine', 'azure_devops', 'slack', 'confluence', 'github', 'gitlab', 'teams');
    END IF;
    
    -- Integration Category
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integrationcategory') THEN
        CREATE TYPE integrationcategory AS ENUM ('project_management', 'communication', 'documentation', 'version_control');
    END IF;
    
    -- Sync Status
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'syncstatus') THEN
        CREATE TYPE syncstatus AS ENUM ('idle', 'syncing', 'success', 'failed');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS project_integrations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    integration_type integrationtype NOT NULL,
    integration_category integrationcategory NOT NULL,
    name VARCHAR(255),
    config JSONB NOT NULL DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    last_sync_at TIMESTAMPTZ,
    sync_status syncstatus DEFAULT 'idle' NOT NULL,
    last_sync_error VARCHAR(500),
    items_synced INTEGER DEFAULT 0,
    configured_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Unique constraint: one integration type per project
    UNIQUE(project_id, integration_type)
);

CREATE INDEX IF NOT EXISTS idx_project_integrations_project ON project_integrations(project_id);
CREATE INDEX IF NOT EXISTS idx_project_integrations_type ON project_integrations(integration_type);

-- =====================================================
-- USER STORIES TABLE
-- =====================================================
DO $$
BEGIN
    -- User Story Status
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstorystatus') THEN
        CREATE TYPE userstorystatus AS ENUM ('open', 'in_progress', 'done', 'blocked', 'closed');
    END IF;
    
    -- User Story Priority
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstorypriority') THEN
        CREATE TYPE userstorypriority AS ENUM ('low', 'medium', 'high', 'critical');
    END IF;
    
    -- User Story Source
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstorysource') THEN
        CREATE TYPE userstorysource AS ENUM ('jira', 'redmine', 'azure_devops', 'manual');
    END IF;
    
    -- User Story Item Type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstoryitemtype') THEN
        CREATE TYPE userstoryitemtype AS ENUM ('epic', 'story', 'bug', 'task', 'subtask', 'feature', 'requirement', 'other');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS user_stories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- External system references
    external_id VARCHAR(100),
    external_key VARCHAR(50),
    external_url VARCHAR(500),
    
    -- Source tracking
    source userstorysource DEFAULT 'manual' NOT NULL,
    integration_id INTEGER REFERENCES project_integrations(id) ON DELETE SET NULL,
    
    -- Story content
    title VARCHAR(500) NOT NULL,
    description TEXT,
    acceptance_criteria TEXT,
    
    -- Status and priority
    status userstorystatus DEFAULT 'open' NOT NULL,
    priority userstorypriority DEFAULT 'medium' NOT NULL,
    
    -- Item type and hierarchy
    item_type userstoryitemtype DEFAULT 'story' NOT NULL,
    parent_key VARCHAR(100),  -- External key of parent (epic, feature, etc.)
    
    -- Metadata
    story_points INTEGER,
    assignee VARCHAR(255),
    reporter VARCHAR(255),
    labels VARCHAR(500)[],
    
    -- Sprint information
    sprint_id VARCHAR(50),
    sprint_name VARCHAR(255),
    
    -- Sync tracking
    last_synced_at TIMESTAMPTZ,
    external_updated_at TIMESTAMPTZ,
    external_created_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_stories_project ON user_stories(project_id);
CREATE INDEX IF NOT EXISTS idx_user_stories_external_key ON user_stories(external_key);
CREATE INDEX IF NOT EXISTS idx_user_stories_integration ON user_stories(integration_id);
CREATE INDEX IF NOT EXISTS idx_user_stories_sprint ON user_stories(sprint_id);

-- =====================================================
-- UPDATED_AT TRIGGER FUNCTION
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name IN ('organizations', 'users', 'projects', 'requirements', 
                           'test_cases', 'test_steps', 'test_runs', 'test_results', 
                           'audit_logs', 'project_integrations', 'user_stories')
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END$$;

-- =====================================================
-- INSERT DEFAULT ADMIN USER (password: admin123)
-- =====================================================
INSERT INTO users (email, hashed_password, full_name, role, is_active, is_superuser)
VALUES (
    'admin@qastra.dev',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4IjD2BxvQJOhK', -- bcrypt hash of 'admin123'
    'QAstra Admin',
    'admin',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- VERIFICATION
-- =====================================================
SELECT 'Database setup complete!' AS status;

SELECT table_name, 
       (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;
