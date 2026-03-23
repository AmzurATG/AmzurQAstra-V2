export interface Project {
  id: number
  name: string
  description?: string
  app_url?: string
  is_active: boolean
  owner_id: number
  organization_id?: number
  jira_project_key?: string
  azure_devops_project?: string
  has_credentials?: boolean
  app_username?: string
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  app_url?: string
}

export interface ProjectUpdate {
  name?: string
  description?: string
  app_url?: string
  app_credentials?: {
    username?: string
    password?: string
  }
  is_active?: boolean
  jira_project_key?: string
  azure_devops_project?: string
}
