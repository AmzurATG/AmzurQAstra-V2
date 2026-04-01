import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@common/store/authStore'
import { useUIStore } from '@common/store/uiStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean }

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

let activeRequests = 0

const updateLoadingState = (delta: number) => {
  activeRequests += delta
  useUIStore.getState().setIsLoading(activeRequests > 0)
}

async function postRefresh(refreshToken: string) {
  const { data } = await axios.post<{
    access_token: string
    refresh_token: string
    token_type: string
  }>(
    `${API_BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { 'Content-Type': 'application/json' } }
  )
  return data
}

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (reason: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((p) => {
    if (error) p.reject(error)
    else if (token) p.resolve(token)
  })
  failedQueue = []
}

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    updateLoadingState(1)
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    updateLoadingState(-1)
    return Promise.reject(error)
  }
)

// Response interceptor: refresh on 401 once, then retry or logout
apiClient.interceptors.response.use(
  (response) => {
    updateLoadingState(-1)
    return response
  },
  async (error: AxiosError) => {
    updateLoadingState(-1)
    const originalRequest = error.config as RetriableConfig | undefined
    const status = error.response?.status

    if (status !== 401 || !originalRequest) {
      return Promise.reject(error)
    }

    const url = String(originalRequest.url || '')
    if (url.includes('/auth/login') || url.includes('/auth/register')) {
      return Promise.reject(error)
    }

    if (originalRequest._retry) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    const refreshToken = useAuthStore.getState().refreshToken
    if (!refreshToken) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest._retry = true
          originalRequest.headers.Authorization = `Bearer ${token}`
          return apiClient(originalRequest)
        })
        .catch((err) => Promise.reject(err))
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const data = await postRefresh(refreshToken)
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token)
      processQueue(null, data.access_token)
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`
      return apiClient(originalRequest)
    } catch (refreshErr) {
      processQueue(refreshErr, null)
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  }
)

export default apiClient
