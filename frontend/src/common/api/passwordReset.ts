import apiClient from './client'

export interface SecurityQuestion {
  id: number
  question: string
}

export interface InitiateResponse {
  email: string
  security_questions: SecurityQuestion[]
}

export interface VerifySecurityResponse {
  message: string
  reset_token: string | null
}

export interface ResetPasswordResponse {
  message: string
}

export const passwordResetApi = {
  initiate: async (email: string): Promise<InitiateResponse> => {
    const response = await apiClient.post('/auth/forgot-password/initiate', { email })
    return response.data
  },

  verifySecurity: async (
    email: string,
    answers: { id: number; answer: string }[]
  ): Promise<VerifySecurityResponse> => {
    const response = await apiClient.post('/auth/forgot-password/verify-security', {
      email,
      answers,
    })
    return response.data
  },

  resetPassword: async (
    email: string,
    reset_token: string,
    new_password: string,
    confirm_password: string
  ): Promise<ResetPasswordResponse> => {
    const response = await apiClient.post('/auth/forgot-password/reset', {
      email,
      reset_token,
      new_password,
      confirm_password,
    })
    return response.data
  },
}
