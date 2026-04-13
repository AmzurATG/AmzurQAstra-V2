import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '@common/types/auth'
import { authApi } from '@common/api/auth'

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  setToken: (token: string) => void
  setTokens: (access: string, refresh: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        try {
          const response = await authApi.login({ email, password })
          set({
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
          })
          await get().fetchUser()
        } finally {
          set({ isLoading: false })
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      fetchUser: async () => {
        try {
          const user = await authApi.getCurrentUser()
          set({ user })
        } catch {
          get().logout()
        }
      },

      setToken: (token: string) => {
        set({ token, isAuthenticated: true })
      },

      setTokens: (access: string, refresh: string) => {
        set({ token: access, refreshToken: refresh, isAuthenticated: true })
      },
    }),
    {
      name: 'qastra-auth',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
