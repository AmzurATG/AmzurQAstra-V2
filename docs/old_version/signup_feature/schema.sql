-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (must be created first)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  company_name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  country_code TEXT, -- Country code for phone number
  phone_number TEXT,
  password TEXT NOT NULL,
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security questions table
CREATE TABLE IF NOT EXISTS security_questions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reset tokens table
CREATE TABLE IF NOT EXISTS reset_tokens (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token TEXT NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  stripe_customer_id TEXT,
  subscription_id TEXT,
  plan_id TEXT,
  status TEXT DEFAULT 'created',
  current_period_start TIMESTAMP WITH TIME ZONE,
  current_period_end TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Public subscriptions table (for non-authenticated users)
CREATE TABLE IF NOT EXISTS public_subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT NOT NULL,
  name TEXT,
  stripe_customer_id TEXT,
  subscription_id TEXT,
  plan_id TEXT,
  status TEXT DEFAULT 'created',
  current_period_end TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: ai_test_automation_sessions
CREATE TABLE ai_test_automation_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  app_url TEXT NOT NULL,
  test_tool TEXT NOT NULL,
  framework TEXT NOT NULL,
  language TEXT NOT NULL,
  jira_connected BOOLEAN DEFAULT FALSE,
  jira_url TEXT,
  document_upload_method TEXT, -- 'jira' or 'upload'
  document_filename TEXT,
  document_storage_path TEXT,
  status TEXT DEFAULT 'initiated' -- initiated, processing, completed, failed
);

-- Table: ai_uploaded_documents
CREATE TABLE ai_uploaded_documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID REFERENCES ai_test_automation_sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  source TEXT, -- 'jira' or 'upload'
  content_type TEXT,
  file_size BIGINT,
  status TEXT DEFAULT 'uploaded'
);

-- Table: user_stories
-- Enhanced with versioning, content hashing, and diff checker support
CREATE TABLE user_stories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  identifier_id TEXT, -- Optional identifier for grouping/filtering stories
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  story_title TEXT,
  story_description TEXT,
  acceptance_criteria JSONB,
  raw_json JSONB,
  llm_model TEXT,
  status TEXT DEFAULT 'generated',
  source TEXT, -- Data source: 'jira', 'upload', 'generated', 'brd'
  display_order INTEGER, -- Preserves JIRA backlog rank order (ORDER BY Rank ASC)
  -- Diff checker and versioning fields
  content_hash VARCHAR(64), -- SHA-256 hash for diff detection
  version INTEGER DEFAULT 1, -- Track story versions
  original_id VARCHAR(100) -- Link to original story for version tracking
);

-- Table: ai_test_scripts
CREATE TABLE ai_test_scripts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID REFERENCES ai_test_automation_sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  script_language TEXT,
  framework TEXT,
  script_content TEXT,
  user_story_id UUID REFERENCES user_stories(id) ON DELETE SET NULL,
  llm_model TEXT,
  status TEXT DEFAULT 'generated'
);

-- Table: test_cases
-- Enhanced with versioning, content hashing, and diff checker support
CREATE TABLE IF NOT EXISTS test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier_id TEXT, -- Optional identifier for grouping/filtering test cases
    user_story_id VARCHAR(100),
    name VARCHAR(500) NOT NULL,
    description TEXT,
    steps JSONB,
    expected_result TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    priority VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    client_id VARCHAR(100), -- Original client-provided ID
    -- Diff checker and versioning fields
    content_hash VARCHAR(64), -- SHA-256 hash for diff detection
    version INTEGER DEFAULT 1, -- Track test case versions
    original_story_id VARCHAR(100), -- Link to original user story for tracking
    replaced_by UUID REFERENCES test_cases(id), -- Link to newer version if deprecated
    deprecated_at TIMESTAMP WITH TIME ZONE -- When this test case was deprecated
);

-- Index for faster lookup by identifier
CREATE INDEX IF NOT EXISTS idx_test_cases_identifier_id ON test_cases(identifier_id);

-- Diff checker performance indexes
-- User stories indexes for fast diff operations
CREATE INDEX IF NOT EXISTS idx_user_stories_content_hash ON user_stories(content_hash);
CREATE INDEX IF NOT EXISTS idx_user_stories_identifier_content ON user_stories(identifier_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_user_stories_original_id ON user_stories(original_id);
CREATE INDEX IF NOT EXISTS idx_user_stories_version ON user_stories(original_id, version);
CREATE INDEX IF NOT EXISTS idx_user_stories_display_order ON user_stories(identifier_id, display_order);

-- Test cases indexes for fast retrieval and diff operations
CREATE INDEX IF NOT EXISTS idx_test_cases_content_hash ON test_cases(content_hash);
CREATE INDEX IF NOT EXISTS idx_test_cases_user_story_id ON test_cases(user_story_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_identifier_story ON test_cases(identifier_id, user_story_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status) WHERE status != 'deprecated';
CREATE INDEX IF NOT EXISTS idx_test_cases_replaced_by ON test_cases(replaced_by) WHERE replaced_by IS NOT NULL;

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_security_questions_user_id ON security_questions(user_id);
CREATE INDEX idx_reset_tokens_user_id ON reset_tokens(user_id);
CREATE INDEX idx_reset_tokens_token ON reset_tokens(token);
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe_customer_id ON user_subscriptions(stripe_customer_id);
CREATE INDEX idx_user_subscriptions_subscription_id ON user_subscriptions(subscription_id);
CREATE INDEX idx_ai_sessions_user_id ON ai_test_automation_sessions(user_id);
CREATE INDEX idx_ai_docs_session_id ON ai_uploaded_documents(session_id);
CREATE INDEX idx_stories_identifier_id ON user_stories(identifier_id);
CREATE INDEX idx_ai_scripts_session_id ON ai_test_scripts(session_id);

-- RLS (Row Level Security) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_test_automation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_uploaded_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_test_scripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_cases ENABLE ROW LEVEL SECURITY;

-- Policy for users to only see and edit their own data
CREATE POLICY users_policy ON users 
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Policy for security questions
CREATE POLICY security_questions_policy ON security_questions
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy for reset tokens
CREATE POLICY reset_tokens_policy ON reset_tokens
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy for user subscriptions
CREATE POLICY user_subscriptions_policy ON user_subscriptions
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy for AI test automation sessions
CREATE POLICY ai_test_automation_sessions_policy ON ai_test_automation_sessions
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy for uploaded documents
CREATE POLICY ai_uploaded_documents_policy ON ai_uploaded_documents
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy for user stories
CREATE POLICY user_stories_policy ON user_stories
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy for test scripts
CREATE POLICY ai_test_scripts_policy ON ai_test_scripts
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Note: test_cases table does not have user_id column
-- Access control should be handled at application level or through session_id/user_story_id joins