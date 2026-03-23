import { create } from 'zustand'
import { Project } from '@common/types'
import { projectsApi } from '@common/api/projects'

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  isLoading: boolean
  error: string | null
  
  fetchProjects: () => Promise<void>
  fetchProject: (projectId: string) => Promise<void>
  selectProject: (projectId: number) => Promise<void>
  clearCurrentProject: () => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await projectsApi.list()
      set({ projects: response.items })
    } catch (error) {
      set({ error: 'Failed to fetch projects' })
    } finally {
      set({ isLoading: false })
    }
  },

  fetchProject: async (projectId: string) => {
    // Skip if already loaded
    const current = get().currentProject
    if (current && current.id === parseInt(projectId)) {
      return
    }
    
    set({ isLoading: true, error: null })
    try {
      const project = await projectsApi.get(parseInt(projectId))
      set({ currentProject: project })
    } catch {
      set({ error: 'Failed to load project', currentProject: null })
    } finally {
      set({ isLoading: false })
    }
  },

  selectProject: async (projectId: number) => {
    set({ isLoading: true })
    try {
      const project = await projectsApi.get(projectId)
      set({ currentProject: project })
    } catch {
      set({ error: 'Failed to load project' })
    } finally {
      set({ isLoading: false })
    }
  },

  clearCurrentProject: () => {
    set({ currentProject: null })
  },
}))
