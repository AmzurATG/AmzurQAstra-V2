// Requirement Types
export interface Requirement {
  id: string
  project_id: string | number
  title: string
  content?: string
  description?: string
  source_type?: 'upload' | 'jira' | 'azure_devops' | 'confluence' | 'manual'
  source: 'upload' | 'jira' | 'azure_devops' | 'manual'
  source_url?: string
  source_id?: string
  source_reference?: string
  file_path?: string
  file_name?: string
  file_type?: string
  status: 'pending' | 'processed' | 'error'
  test_cases_count: number
  created_at: string
  updated_at: string
}

// Test Case Types
export type TestCasePriority = 'critical' | 'high' | 'medium' | 'low'
export type TestCaseCategory = 'smoke' | 'regression' | 'e2e' | 'integration' | 'sanity'
export type TestCaseStatus = 'draft' | 'ready' | 'deprecated'

export interface UserStoryBrief {
  id: number
  external_key: string | null
  title: string
  item_type: string
}

export interface TestCase {
  id: number
  project_id: number
  requirement_id?: number
  user_story_id?: number
  user_story?: UserStoryBrief
  title: string
  description: string
  preconditions?: string
  priority: TestCasePriority
  category: TestCaseCategory
  status: TestCaseStatus
  is_generated: boolean
  is_automated: boolean
  integrity_check: boolean
  tags?: string
  jira_key?: string
  steps_count: number
  steps?: TestStep[]
  created_at: string
  updated_at: string
}

// Test Step Types
export type TestStepAction = 
  | 'navigate'
  | 'click'
  | 'fill'
  | 'type'
  | 'select'
  | 'check'
  | 'uncheck'
  | 'hover'
  | 'wait'
  | 'screenshot'
  | 'assert_visible'
  | 'assert_text'
  | 'assert_url'
  | 'assert_title'
  | 'custom'

export interface TestStep {
  id: number
  test_case_id: number
  step_number: number
  action: TestStepAction
  target?: string
  value?: string
  description?: string
  expected_result?: string
  playwright_code?: string
  selector_type?: string
  selector_confidence?: number
  created_at: string
  updated_at: string
}

// Test Run Types
export type TestRunStatus = 'pending' | 'running' | 'passed' | 'failed' | 'cancelled'
export type BrowserType = 'chromium' | 'firefox' | 'webkit'

export interface TestRun {
  id: string
  project_id: string
  name: string
  status: TestRunStatus
  browser: BrowserType
  total_tests: number
  passed_tests: number
  failed_tests: number
  skipped_tests: number
  duration_ms?: number
  started_at?: string
  completed_at?: string
  created_at: string
}

// Test Result Types
export interface TestResult {
  id: string
  test_run_id: string
  test_case_id: string
  test_case_title: string
  status: 'passed' | 'failed' | 'skipped'
  error_message?: string
  error_stack?: string
  screenshot_path?: string
  video_path?: string
  step_results: StepResult[]
  duration_ms: number
  started_at: string
  completed_at: string
}

export interface StepResult {
  step_id: string
  step_order: number
  action: TestStepAction
  status: 'passed' | 'failed' | 'skipped'
  error_message?: string
  screenshot_path?: string
  duration_ms: number
}

// Integrity Check Types
export interface StepCheckResult {
  step_number: number
  action: string
  description?: string
  status: 'passed' | 'failed' | 'error'
  duration_ms: number
  error?: string
  screenshot_path?: string
}

export interface TestCaseCheckResult {
  test_case_id: number
  title: string
  status: 'passed' | 'failed' | 'error'
  steps_total: number
  steps_passed: number
  steps_failed: number
  step_results: StepCheckResult[]
  duration_ms: number
  error?: string
}

export interface IntegrityCheckResult {
  project_id: number
  status: 'passed' | 'failed' | 'error'
  app_reachable: boolean
  login_successful?: boolean
  // Test case results (new)
  test_cases_total: number
  test_cases_passed: number
  test_cases_failed: number
  test_case_results: TestCaseCheckResult[]
  // Legacy page results
  pages_checked: number
  pages_passed: number
  pages_failed: number
  page_results: PageCheckResult[]
  screenshots: string[]
  duration_ms: number
  checked_at: string
  error?: string
}

export interface PageCheckResult {
  name: string
  url: string
  status: 'passed' | 'failed'
  load_time_ms?: number
  error?: string
  screenshot_path?: string
  missing_elements?: string[]
}

// Integrity Check Preview types
export interface PreviewStep {
  step_number: number
  action: string
  target?: string
  value?: string
  description?: string
  expected_result?: string
}

export interface PreviewTestCase {
  id: number
  title: string
  description?: string
  priority?: string
  integrity_check: boolean
  steps: PreviewStep[]
}

export interface PreviewUserStory {
  id: number
  title: string
  external_key?: string
  status: string
  priority: string
  item_type: string
  integrity_check: boolean
  test_cases: PreviewTestCase[]
}

export interface IntegrityCheckPreview {
  user_stories: PreviewUserStory[]
  standalone_test_cases: PreviewTestCase[]
  total_user_stories: number
  total_test_cases: number
  total_steps: number
}


// =============================================================================
// User Story Types
// =============================================================================

export type UserStoryStatus = 'open' | 'in_progress' | 'done' | 'blocked' | 'closed'
export type UserStoryPriority = 'low' | 'medium' | 'high' | 'critical'
export type UserStorySource = 'jira' | 'redmine' | 'azure_devops' | 'manual'
export type UserStoryItemType = 'epic' | 'story' | 'bug' | 'task' | 'subtask' | 'feature' | 'requirement'

export interface UserStory {
  id: number
  project_id: number
  external_id?: string
  external_key?: string
  title: string
  description?: string
  acceptance_criteria?: string
  status: UserStoryStatus
  priority: UserStoryPriority
  source: UserStorySource
  item_type: UserStoryItemType
  parent_key?: string
  story_points?: number
  assignee?: string
  reporter?: string
  labels: string[]
  sprint_id?: string
  sprint_name?: string
  external_url?: string
  integrity_check: boolean
  linked_requirements: number
  linked_test_cases: number
  synced_at?: string
  created_at: string
  updated_at: string
}

export interface UserStoryStats {
  total: number
  open: number
  in_progress: number
  done: number
  blocked: number
}

export interface SyncRequest {
  integration_type: string
  project_key?: string
  issue_types?: string[]
  updated_since?: string
  sprint_id?: number | null  // null for all sprints
}

export interface SyncResponse {
  status: string
  message: string
  items_synced: number
  errors: string[]
}

export interface Sprint {
  id: number
  name: string
  state: string
  start_date?: string | null
  end_date?: string | null
}

export interface ProjectIntegrationInfo {
  id: number
  integration_type: string
  name: string | null
  config: {
    project_key?: string
    project_name?: string
    [key: string]: string | undefined
  } | null
  is_enabled: boolean
  last_sync_at: string | null
  items_synced: number
}

// =============================================================================
// Test Generation Types
// =============================================================================

export interface GenerateTestsRequest {
  include_steps: boolean
}

export interface GeneratedTestCaseInfo {
  id: number
  title: string
  priority: string
  category: string
}

export interface GenerateTestsResponse {
  success: boolean
  user_story_id: number
  user_story_key: string | null
  test_cases_created: number
  test_cases: GeneratedTestCaseInfo[]
  error: string | null
}
