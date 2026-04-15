import { apiClient } from '@common/api/client'
import type {
  Requirement,
  TestCase,
  TestStep,
  TestRun,
  TestRunSummary,
  TestResult,
  UserStory,
  UserStoryStats,
  SyncRequest,
  SyncResponse,
  Sprint,
  ProjectIntegrationInfo,
  GenerateTestsRequest,
  GenerateTestsResponse,
  DashboardOverview,
  GapAnalysisRun,
  AcceptGapSuggestionsResponse,
} from '../types'

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

// Dashboard (cross-project aggregates)
export const dashboardApi = {
  overview: async (): Promise<DashboardOverview> => {
    const response = await apiClient.get<DashboardOverview>('/functional/dashboard/overview')
    return response.data
  },
}

// Requirements API
export const requirementsApi = {
  list: (
    projectId: string,
    params?: { page?: number; page_size?: number }
  ) =>
    apiClient.get<PaginatedResponse<Requirement>>(`/functional/requirements`, {
      params: { project_id: projectId, ...params },
    }),

  get: (id: string) =>
    apiClient.get<Requirement>(`/functional/requirements/${id}`),

  /** Binary file stream (auth via axios); use with responseType blob for preview/download. */
  getFile: (id: string) =>
    apiClient.get<Blob>(`/functional/requirements/${id}/file`, {
      responseType: 'blob',
    }),

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

  importFromJira: (projectId: string, issueKey: string) =>
    apiClient.post<Requirement>(`/functional/requirements/import-jira`, {
      project_id: projectId,
      issue_key: issueKey,
    }),
}

export const gapAnalysisApi = {
  createRun: (projectId: number, requirementId: number) =>
    apiClient.post<GapAnalysisRun>(`/functional/gap-analysis/runs`, {
      project_id: projectId,
      requirement_id: requirementId,
    }),

  listRuns: (
    projectId: string,
    params?: { page?: number; page_size?: number }
  ) =>
    apiClient.get<PaginatedResponse<GapAnalysisRun>>(`/functional/gap-analysis/runs`, {
      params: { project_id: projectId, ...params },
    }),

  getRun: (runId: number, projectId: string) =>
    apiClient.get<GapAnalysisRun>(`/functional/gap-analysis/runs/${runId}`, {
      params: { project_id: projectId },
    }),

  getPdf: (runId: number, projectId: string, download?: boolean) =>
    apiClient.get<Blob>(`/functional/gap-analysis/runs/${runId}/pdf`, {
      params: {
        project_id: projectId,
        ...(download ? { download: true } : {}),
      },
      responseType: 'blob',
    }),

  acceptSuggestions: (runId: number, projectId: string, indices: number[]) =>
    apiClient.post<AcceptGapSuggestionsResponse>(
      `/functional/gap-analysis/runs/${runId}/accept-suggestions`,
      { indices },
      { params: { project_id: projectId } }
    ),
}

// Test Cases API  
export const testCasesApi = {
  list: (projectId: number, params?: { 
    status?: string
    priority?: string
    category?: string
    user_story_id?: number
    search?: string
    page?: number
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
  list: (
    projectId: number,
    params?: { page?: number; page_size?: number; status_filter?: string }
  ) =>
    apiClient.get<PaginatedResponse<TestRun>>(`/functional/test-runs/`, {
      params: { project_id: projectId, ...params },
    }),

  summary: (projectId: number) =>
    apiClient.get<TestRunSummary>(`/functional/test-runs/summary`, {
      params: { project_id: projectId },
    }),

  get: (id: number) =>
    apiClient.get<TestRun>(`/functional/test-runs/${id}`),

  create: (data: import('../types').TestRunCreateRequest) =>
    apiClient.post<import('../types').TestRunStartResponse>(`/functional/test-runs/`, data),

  getLiveProgress: (id: number, params?: { lite?: boolean }) =>
    apiClient.get<import('../types').LiveProgressResponse>(`/functional/test-runs/${id}/live`, {
      params: { lite: params?.lite !== false },
    }),

  getResult: (runId: number, resultId: number) =>
    apiClient.get<TestResult>(`/functional/test-runs/${runId}/results/${resultId}`),

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

  getHistory: (projectId: string, params?: { limit?: number }) =>
    apiClient.get<Array<{ created_at?: string | null }>>(`/functional/integrity-check/history/${projectId}`, {
      params,
    }),

  getPreview: (projectId: number) =>
    apiClient.get<import('../types').IntegrityCheckPreview>(`/functional/integrity-check/preview/${projectId}`),
}

// User Stories API
export const userStoriesApi = {
  list: (
    projectId: number,
    params?: {
      status?: string
      item_type?: string
      search?: string
      page?: number
      page_size?: number
      /** Comma-separated Jira sprint ids; aligns list with last sync scope */
      sprint_ids?: string
    }
  ) => apiClient.get<PaginatedResponse<UserStory>>(`/functional/user-stories/${projectId}`, { params }),

  get: (projectId: number, storyId: number) =>
    apiClient.get<UserStory>(`/functional/user-stories/${projectId}/${storyId}`),

  create: (projectId: number, data: Partial<UserStory>) =>
    apiClient.post<UserStory>(`/functional/user-stories/${projectId}`, data),

  update: (projectId: number, storyId: number, data: Partial<UserStory>) =>
    apiClient.put<UserStory>(`/functional/user-stories/${projectId}/${storyId}`, data),

  delete: (projectId: number, storyId: number) =>
    apiClient.delete<{ message: string; test_cases_deleted: number }>(`/functional/user-stories/${projectId}/${storyId}`),

  getStats: (projectId: number, params?: { sprint_ids?: string }) =>
    apiClient.get<UserStoryStats>(`/functional/user-stories/${projectId}/stats`, { params }),

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
