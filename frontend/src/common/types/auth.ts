export interface User {
  id: number
  email: string
  full_name?: string
  role: 'admin' | 'manager' | 'tester' | 'viewer'
  is_active: boolean
  is_superuser: boolean
  organization_id?: number
  created_at: string
  updated_at: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}
