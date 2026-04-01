import { apiClient } from '@common/api/client'
import type {
  Requirement,
  TestCase,
  TestStep,
  TestRun,
  TestResult,
  IntegrityCheckResult,
  UserStory,
  UserStoryStats,
  SyncRequest,
  SyncResponse,
  Sprint,
  ProjectIntegrationInfo,
  GenerateTestsRequest,
  GenerateTestsResponse,
} from '../types'

// Requirements API
export const requirementsApi = {
  list: (projectId: string) =>
    apiClient.get<{ items: Requirement[]; total: number }>(`/functional/requirements`, { 
      params: { project_id: projectId } 
    }),

  get: (id: string) =>
    apiClient.get<Requirement>(`/functional/requirements/${id}`),

  upload: (data: FormData) =>
    apiClient.post<Requirement>(`/functional/requirements/upload`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  create: (data: FormData) =>
    apiClient.post<Requirement>(`/functional/requirements`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  delete: (id: string) =>
    apiClient.delete(`/functional/requirements/${id}`),

  generateTestCases: (requirementId: string) =>
    apiClient.post<{ test_cases_created: number }>(
      `/functional/requirements/${requirementId}/generate-test-cases`
    ),

  importFromJira: (projectId: string, issueKey: string) =>
    apiClient.post<Requirement>(`/functional/requirements/import-jira`, {
      project_id: projectId,
      issue_key: issueKey,
    }),
}

// Test Cases API  
export const testCasesApi = {
  list: (projectId: number, params?: { 
    status?: string
    priority?: string
    category?: string
    user_story_id?: number
    search?: string
    page_size?: number 
  }) =>
    apiClient.get<PaginatedResponse<TestCase>>(`/functional/test-cases/`, { 
      params: { project_id: projectId, ...params } 
    }),

  get: (id: number) =>
    apiClient.get<TestCase>(`/functional/test-cases/${id}`),

  getWithSteps: (id: number) =>
    apiClient.get<TestCase>(`/functional/test-cases/${id}`),

  create: (data: Partial<TestCase>) =>
    apiClient.post<TestCase>(`/functional/test-cases/`, data),

  update: (id: number, data: Partial<TestCase>) =>
    apiClient.put<TestCase>(`/functional/test-cases/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/functional/test-cases/${id}`),

  generate: (requirementId: number) =>
    apiClient.post<TestCase[]>(`/functional/test-cases/generate`, {
      requirement_id: requirementId,
    }),

  regenerateSteps: (testCaseId: number) =>
    apiClient.post<{ success: boolean; steps_created: number; error?: string }>(
      `/functional/test-cases/${testCaseId}/regenerate-steps`
    ),
}

// Test Steps API
export const testStepsApi = {
  list: (testCaseId: number) =>
    apiClient.get<TestStep[]>(`/functional/test-steps/${testCaseId}`),

  create: (data: Partial<TestStep> & { test_case_id: number }) =>
    apiClient.post<TestStep>(`/functional/test-steps/`, data),

  update: (stepId: number, data: Partial<TestStep>) =>
    apiClient.put<TestStep>(`/functional/test-steps/${stepId}`, data),

  delete: (stepId: number) =>
    apiClient.delete(`/functional/test-steps/${stepId}`),

  reorder: (data: { step_ids: number[] }) =>
    apiClient.post(`/functional/test-steps/reorder`, data),
}

// Test Runs API
export const testRunsApi = {
  list: (projectId: number) =>
    apiClient.get<{ items: TestRun[]; total: number }>(`/functional/test-runs/`, {
      params: { project_id: projectId },
    }),

  get: (id: number) =>
    apiClient.get<TestRun>(`/functional/test-runs/${id}`),

  create: (data: import('../types').TestRunCreateRequest) =>
    apiClient.post<import('../types').TestRunStartResponse>(`/functional/test-runs/`, data),

  getLiveProgress: (id: number) =>
    apiClient.get<import('../types').LiveProgressResponse>(`/functional/test-runs/${id}/live`),

  cancel: (id: number) =>
    apiClient.post(`/functional/test-runs/${id}/cancel`),

  getResults: (id: number) =>
    apiClient.get<TestResult[]>(`/functional/test-runs/${id}/results`),

  syncStep: (resultId: number, stepNumber: number) =>
    apiClient.post(`/functional/test-runs/results/${resultId}/steps/${stepNumber}/sync`),
}

// Integrity Check API
export const integrityCheckApi = {
  /** Start an async run — returns run_id immediately */
  startRun: (data: {
    project_id: number
    app_url: string
    credentials?: { username?: string; password?: string }
    use_google_signin?: boolean
  }) =>
    apiClient.post<import('../types').RunStartResponse>(`/functional/integrity-check/run`, data),

  /** Poll live progress by run_id */
  getStatus: (runId: string) =>
    apiClient.get<import('../types').RunStatusResponse>(`/functional/integrity-check/${runId}/status`),

  getHistory: (projectId: string) =>
    apiClient.get<import('../types').RunStatusResponse[]>(`/functional/integrity-check/history/${projectId}`),

  getPreview: (projectId: number) =>
    apiClient.get<import('../types').IntegrityCheckPreview>(`/functional/integrity-check/preview/${projectId}`),
}

// User Stories API
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export const userStoriesApi = {
  list: (projectId: number, params?: { status?: string; item_type?: string; search?: string }) =>
    apiClient.get<PaginatedResponse<UserStory>>(`/functional/user-stories/${projectId}`, { params }),

  get: (projectId: number, storyId: number) =>
    apiClient.get<UserStory>(`/functional/user-stories/${projectId}/${storyId}`),

  create: (projectId: number, data: Partial<UserStory>) =>
    apiClient.post<UserStory>(`/functional/user-stories/${projectId}`, data),

  update: (projectId: number, storyId: number, data: Partial<UserStory>) =>
    apiClient.put<UserStory>(`/functional/user-stories/${projectId}/${storyId}`, data),

  delete: (projectId: number, storyId: number) =>
    apiClient.delete<{ message: string; test_cases_deleted: number }>(`/functional/user-stories/${projectId}/${storyId}`),

  getStats: (projectId: number) =>
    apiClient.get<UserStoryStats>(`/functional/user-stories/${projectId}/stats`),

  sync: (projectId: number, data: SyncRequest) =>
    apiClient.post<SyncResponse>(`/functional/user-stories/${projectId}/sync`, data),

  getSprints: (projectId: number, integrationType: string = 'jira') =>
    apiClient.get<Sprint[]>(`/functional/user-stories/${projectId}/sprints`, {
      params: { integration_type: integrationType }
    }),

  getIntegrations: (projectId: number) =>
    apiClient.get<ProjectIntegrationInfo[]>(`/functional/integrations/${projectId}`),

  generateTests: (projectId: number, storyId: number, data: GenerateTestsRequest = { include_steps: true }) =>
    apiClient.post<GenerateTestsResponse>(`/functional/user-stories/${projectId}/${storyId}/generate-tests`, data),
}
