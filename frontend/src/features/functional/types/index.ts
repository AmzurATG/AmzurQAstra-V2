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

// Gap analysis (BRD vs user stories)
export type GapAnalysisRunStatus = 'pending' | 'completed' | 'failed'

export interface GapAnalysisGapItem {
  type?: string
  detail?: string
  related_story_key?: string | null
}

export interface GapAnalysisSuggestedStory {
  title: string
  description?: string
  acceptance_criteria?: string
  rationale?: string
}

export interface GapAnalysisResultJson {
  summary?: string
  coverage_estimate_percent?: number | null
  gaps?: GapAnalysisGapItem[]
  suggested_user_stories?: GapAnalysisSuggestedStory[]
  notes?: string
  _export_warnings?: string[]
}

export interface GapAnalysisRun {
  id: number
  project_id: number
  requirement_id: number
  created_by?: number | null
  status: GapAnalysisRunStatus
  result_json?: GapAnalysisResultJson | null
  error_message?: string | null
  pdf_path?: string | null
  requirement_title?: string | null
  requirement_file_name?: string | null
  created_at: string
  updated_at: string
}

export interface AcceptGapSuggestionsResponse {
  created: number
  errors: string[]
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
export type TestRunStatus = 'pending' | 'running' | 'passed' | 'failed' | 'cancelled' | 'error'
export type BrowserType = 'chromium' | 'firefox' | 'webkit'

export interface TestRun {
  id: number
  project_id: number
  name: string
  description?: string
  status: TestRunStatus
  browser: BrowserType
  total_tests: number
  passed_tests: number
  failed_tests: number
  skipped_tests: number
  triggered_by?: number
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
}

/** Project-wide aggregates from GET /functional/test-runs/summary */
export interface TestRunSummary {
  total: number
  passed: number
  failed: number
  running: number
  pending: number
  cancelled: number
  avg_pass_rate: number
}

/** GET /functional/dashboard/overview */
export interface DashboardRecentRun {
  id: number
  project_id: number
  project_name: string
  name?: string | null
  description?: string | null
  status: string
  created_at: string
}

export interface DashboardRecentProject {
  id: number
  name: string
  description?: string | null
  updated_at: string
}

export interface DashboardActivityDay {
  date: string
  passed: number
  failed: number
  other: number
}

export interface DashboardOverview {
  project_count: number
  test_cases_total: number
  runs_total: number
  runs_passed: number
  runs_failed: number
  runs_running: number
  runs_pending: number
  runs_cancelled: number
  avg_pass_rate: number
  recent_runs: DashboardRecentRun[]
  recent_projects: DashboardRecentProject[]
  activity_by_day: DashboardActivityDay[]
}

export interface TestRunStartResponse {
  run_id: number
  status: string
}

export interface TestRunCreateRequest {
  project_id: number
  name?: string
  description?: string
  test_case_ids?: number[]
  app_url?: string
  credentials?: { username?: string; password?: string }
  use_google_signin?: boolean
  browser?: string
  headless?: boolean
}

// Test Result Types
export interface TestResult {
  id: number
  test_run_id: number
  test_case_id: number
  status: 'passed' | 'failed' | 'skipped' | 'error'
  error_message?: string
  failed_step?: number
  screenshot_path?: string
  step_results?: TestStepResult[]
  agent_logs?: AgentLogEntry[]
  duration_ms?: number
  started_at?: string
  completed_at?: string
}

export interface TestStepResult {
  step_number: number
  status: 'passed' | 'failed' | 'error' | 'skipped'
  actual_result?: string
  description?: string
  adaptation?: string | null
}

export interface AgentLogEntry {
  timestamp: string
  agent_step: number
  description: string
  adaptation?: string | null
  screenshot_path?: string | null
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

// Live Progress (polling)
export interface LogEntry {
  timestamp: string
  level: string
  message: string
  test_case_id?: number
}

export interface CompletedCaseResult {
  test_result_id: number
  test_case_id: number
  title: string
  status: string
  steps_total: number
  steps_passed: number
  steps_failed: number
  duration_ms: number
  step_results?: TestStepResult[]
  adapted_steps?: TestStepResult[]
  original_steps?: Record<string, unknown>[]
  agent_logs?: AgentLogEntry[]
  /** Stored as `/screenshots/<file>`; load via authenticated API */
  screenshot_path?: string | null
  /** From lite /live when agent_logs omitted */
  agent_screenshot_count?: number | null
  /** From lite /live when adapted_steps omitted */
  has_adaptations?: boolean | null
}

export interface LiveProgressResponse {
  run_id: number
  status: string
  percentage: number
  current_test_case_index: number
  total_test_cases: number
  current_test_case_title?: string
  current_step_info?: string
  completed_results: CompletedCaseResult[]
  logs: LogEntry[]
  error?: string
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

// ── Async run types ───────────────────────────────────────────────────────────

export interface RunStartResponse {
  run_id: string
  status: 'pending'
}

export interface AgentStepData {
  step_number: number
  description?: string
  screenshot_path?: string
}

export type RunStatus = 'pending' | 'running' | 'completed' | 'error' | 'not_found'

export interface RunStatusResponse {
  run_id: string
  status: RunStatus
  percentage: number
  current_step?: string
  overall_status?: 'passed' | 'failed' | 'error'
  screenshots: string[]
  steps: AgentStepData[]
  steps_total: number
  steps_passed: number
  steps_failed: number
  summary?: string
  error?: string
  duration_ms?: number
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
  /** LLM-generated test cases (duplicate guard uses this, not manual cases) */
  generated_test_cases?: number
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
  /** Explicit cursor; usually omitted so the server uses last successful sync time */
  updated_since?: string
  sprint_id?: number | null // null for all sprints
  /** When true, ignore last sync and fetch all matching remote issues */
  force_full_sync?: boolean
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
  /** When true, existing story test cases are removed before generating */
  force_regenerate?: boolean
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
  /** e.g. already_exists when duplicate generation was blocked */
  code?: string | null
}
