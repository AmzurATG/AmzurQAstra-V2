import apiClient from './client'

export interface IntegrationConfig {
  integration_type: string
  name?: string
  config: Record<string, unknown>
  is_enabled?: boolean
}

export interface IntegrationResponse {
  id: number
  project_id: number
  integration_type: string
  integration_category: string
  name: string | null
  config: Record<string, string> | null  // Config with sensitive fields redacted
  is_enabled: boolean
  last_sync_at: string | null
  sync_status: string
  last_sync_error: string | null
  items_synced: number
  created_at: string
  updated_at: string
}

export interface TestConnectionRequest {
  config: Record<string, unknown>
}

export interface RemoteProject {
  key: string
  name: string
  description?: string
}

export interface TestConnectionResponse {
  success: boolean
  message: string
  projects?: RemoteProject[]
}

export interface IntegrationMetadata {
  type: string
  name: string
  category: string
  icon: string
  description: string
  features: string[]
  config_fields: Array<{
    name: string
    label: string
    type: string
    required: boolean
    description: string
  }>
}

// List available integration types
export const getAvailableIntegrations = async (category?: string): Promise<IntegrationMetadata[]> => {
  const params = category ? { category } : {}
  const response = await apiClient.get('/functional/integrations/available', { params })
  return response.data
}

// List project integrations
export const getProjectIntegrations = async (projectId: number): Promise<IntegrationResponse[]> => {
  const response = await apiClient.get(`/functional/integrations/${projectId}`)
  return response.data
}

// Get a specific integration
export const getProjectIntegration = async (
  projectId: number,
  integrationType: string
): Promise<IntegrationResponse> => {
  const response = await apiClient.get(`/functional/integrations/${projectId}/${integrationType}`)
  return response.data
}

// Create/save integration
export const createProjectIntegration = async (
  projectId: number,
  data: IntegrationConfig
): Promise<IntegrationResponse> => {
  const response = await apiClient.post(`/functional/integrations/${projectId}`, data)
  return response.data
}

// Update integration
export const updateProjectIntegration = async (
  projectId: number,
  integrationType: string,
  data: Partial<IntegrationConfig>
): Promise<IntegrationResponse> => {
  const response = await apiClient.put(`/functional/integrations/${projectId}/${integrationType}`, data)
  return response.data
}

// Delete integration
export const deleteProjectIntegration = async (
  projectId: number,
  integrationType: string
): Promise<void> => {
  await apiClient.delete(`/functional/integrations/${projectId}/${integrationType}`)
}

// Test connection (without saving)
export const testIntegrationConnection = async (
  projectId: number,
  integrationType: string,
  config: Record<string, unknown>
): Promise<TestConnectionResponse> => {
  const response = await apiClient.post(
    `/functional/integrations/${projectId}/${integrationType}/test`,
    { config }
  )
  return response.data
}

// List remote projects from external tool
export const getRemoteProjects = async (
  projectId: number,
  integrationType: string
): Promise<RemoteProject[]> => {
  const response = await apiClient.get(
    `/functional/integrations/${projectId}/${integrationType}/projects`
  )
  return response.data.projects
}
