import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { User } from '@common/types/auth'
import { authApi } from '@common/api/auth'
import { clearAllPmSyncPreferences } from '@features/functional/utils/pmSyncPreferences'

const STORAGE_KEY = 'qastra-auth'
const REMEMBER_KEY = 'qastra-remember'

/** Returns the appropriate storage based on prior remember-me choice. */
function getStorage() {
  if (localStorage.getItem(REMEMBER_KEY) === '1') {
    return localStorage
  }
  return sessionStorage
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>
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

      login: async (email: string, password: string, rememberMe = false) => {
        set({ isLoading: true })
        try {
          const response = await authApi.login({ email, password, remember_me: rememberMe })

          // Persist remember-me preference and migrate storage if needed
          if (rememberMe) {
            localStorage.setItem(REMEMBER_KEY, '1')
            // Move persisted state to localStorage
            sessionStorage.removeItem(STORAGE_KEY)
          } else {
            localStorage.removeItem(REMEMBER_KEY)
            // Move persisted state to sessionStorage
            localStorage.removeItem(STORAGE_KEY)
          }

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
        clearAllPmSyncPreferences()
        localStorage.removeItem(REMEMBER_KEY)
        localStorage.removeItem(STORAGE_KEY)
        sessionStorage.removeItem(STORAGE_KEY)
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
      name: STORAGE_KEY,
      storage: createJSONStorage(() => getStorage()),
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
