import apiClient from './client'

export interface SignupData {
  first_name: string
  last_name: string
  company_name: string
  email: string
  country_code?: string
  phone_number?: string
  password: string
  confirm_password: string
  security_questions: { question: string; answer: string }[]
}

export interface CheckEmailResponse {
  exists: boolean
  email: string
}

export interface SignupResponse {
  message: string
  email: string
}

export interface OTPVerifyResponse {
  detail: string
  success: boolean
}

export const signupApi = {
  checkEmail: async (email: string): Promise<CheckEmailResponse> => {
    const response = await apiClient.post('/auth/check-email', { email })
    return response.data
  },

  signup: async (data: SignupData): Promise<SignupResponse> => {
    const response = await apiClient.post('/auth/signup', data)
    return response.data
  },

  verifyOtp: async (email: string, otp: string): Promise<OTPVerifyResponse> => {
    const response = await apiClient.post('/auth/verify-otp', { email, otp })
    return response.data
  },

  resendOtp: async (email: string): Promise<SignupResponse> => {
    const response = await apiClient.post('/auth/resend-otp', { email })
    return response.data
  },
}
