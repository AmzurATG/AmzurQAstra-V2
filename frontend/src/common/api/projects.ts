import apiClient from './client'
import { Project, ProjectCreate, ProjectUpdate, PaginatedResponse } from '@common/types'

export const projectsApi = {
  list: async (params?: { search?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<Project>> => {
    const response = await apiClient.get('/projects', { params })
    return response.data
  },

  get: async (projectId: number): Promise<Project> => {
    const response = await apiClient.get(`/projects/${projectId}`)
    return response.data
  },

  create: async (data: ProjectCreate): Promise<Project> => {
    const response = await apiClient.post('/projects', data)
    return response.data
  },

  update: async (projectId: number, data: ProjectUpdate): Promise<Project> => {
    const response = await apiClient.put(`/projects/${projectId}`, data)
    return response.data
  },

  delete: async (projectId: number): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`)
  },
}
