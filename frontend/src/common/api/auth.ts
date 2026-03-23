import apiClient from './client'
import { User, LoginCredentials, Token } from '@common/types/auth'

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<Token> => {
    const response = await apiClient.post('/auth/login', credentials)
    return response.data
  },

  register: async (data: { email: string; password: string; full_name?: string }): Promise<User> => {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get('/users/me')
    return response.data
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response = await apiClient.put('/users/me', data)
    return response.data
  },
}
