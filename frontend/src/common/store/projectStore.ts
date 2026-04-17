import { create } from 'zustand'
import { Project } from '@common/types'
import { projectsApi } from '@common/api/projects'

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  isLoading: boolean
  error: string | null
  
  fetchProjects: () => Promise<void>
  fetchProject: (projectId: string, options?: { force?: boolean }) => Promise<void>
  setCurrentProject: (project: Project) => void
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

  fetchProject: async (projectId: string, options?: { force?: boolean }) => {
    const id = parseInt(projectId, 10)
    const current = get().currentProject
    if (!options?.force && current && current.id === id) {
      return
    }

    set({ isLoading: true, error: null })
    try {
      const project = await projectsApi.get(id)
      set({ currentProject: project })
    } catch {
      set({ error: 'Failed to load project', currentProject: null })
    } finally {
      set({ isLoading: false })
    }
  },

  setCurrentProject: (project: Project) => {
    set({ currentProject: project })
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
