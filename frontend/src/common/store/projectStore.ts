import { create } from 'zustand'
import { Project } from '@common/types'
import { projectsApi } from '@common/api/projects'

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  isLoading: boolean
  error: string | null
  page: number
  totalPages: number
  total: number
  hasNext: boolean
  hasPrev: boolean
  
  fetchProjects: (page?: number) => Promise<void>
  fetchProject: (projectId: string, options?: { force?: boolean }) => Promise<void>
  /** Merge server project payload (e.g. after PUT) without an extra GET. */
  setCurrentProject: (project: Project) => void
  /** GET project by id and update store; does not toggle isLoading (safe under ProjectLayout). */
  revalidateProject: (projectId: string) => Promise<void>
  selectProject: (projectId: number) => Promise<void>
  clearCurrentProject: () => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,
  page: 1,
  totalPages: 1,
  total: 0,
  hasNext: false,
  hasPrev: false,

  fetchProjects: async (page = 1) => {
    set({ isLoading: true, error: null })
    try {
      const response = await projectsApi.list({ page, page_size: 9 })
      set({
        projects: response.items,
        page: response.page,
        totalPages: response.total_pages,
        total: response.total,
        hasNext: response.has_next,
        hasPrev: response.has_prev,
      })
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

  revalidateProject: async (projectId: string) => {
    const id = parseInt(projectId, 10)
    if (Number.isNaN(id)) return
    try {
      const project = await projectsApi.get(id)
      set({ currentProject: project })
    } catch {
      // Keep existing store state on silent refresh failure
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
