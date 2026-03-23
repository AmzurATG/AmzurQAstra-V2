import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { useProjectStore } from '@common/store/projectStore'
import { projectsApi } from '@common/api/projects'
import { ArrowRightIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export default function ProjectSettings() {
  const { projectId } = useParams<{ projectId: string }>()
  const { currentProject, fetchProject } = useProjectStore()
  
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [appUrl, setAppUrl] = useState('')
  const [appUsername, setAppUsername] = useState('')
  const [appPassword, setAppPassword] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (currentProject) {
      setName(currentProject.name || '')
      setDescription(currentProject.description || '')
      setAppUrl(currentProject.app_url || '')
      setAppUsername(currentProject.app_username || '')
      // Don't populate password - it's not returned from backend for security
      setAppPassword('')
    }
  }, [currentProject])

  const handleSave = async () => {
    if (!projectId || !name.trim()) {
      toast.error('Project name is required')
      return
    }

    setIsSaving(true)
    try {
      const updateData: any = {
        name: name.trim(),
        description: description.trim() || undefined,
        app_url: appUrl.trim() || undefined,
      }
      
      // Only include credentials if username or password is provided
      if (appUsername.trim() || appPassword) {
        updateData.app_credentials = {
          username: appUsername.trim() || undefined,
          password: appPassword || undefined,
        }
      }
      
      await projectsApi.update(Number(projectId), updateData)
      toast.success('Project settings saved successfully')
      // Clear password field after save
      setAppPassword('')
      // Refresh the project in store
      await fetchProject(projectId)
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to save settings'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Project Settings</h1>
        <p className="text-gray-600">Configure your project and integrations</p>
      </div>

      {/* General Settings */}
      <Card>
        <CardTitle>General</CardTitle>
        <div className="mt-4 space-y-4">
          <Input
            label="Project Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Project name"
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Project description"
            />
          </div>
        </div>
      </Card>

      {/* Target Application */}
      <Card>
        <CardTitle>Target Application</CardTitle>
        <p className="text-sm text-gray-500 mb-4">
          Configure the application URL and credentials for testing
        </p>
        <div className="space-y-4">
          <Input
            label="Application URL"
            value={appUrl}
            onChange={(e) => setAppUrl(e.target.value)}
            placeholder="https://app.example.com"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Username"
              value={appUsername}
              onChange={(e) => setAppUsername(e.target.value)}
              placeholder="test@example.com"
            />
            <div>
              <Input
                label="Password"
                type="password"
                value={appPassword}
                onChange={(e) => setAppPassword(e.target.value)}
                placeholder={currentProject?.has_credentials ? '••••••••' : 'Enter password'}
              />
              {currentProject?.has_credentials && !appPassword && (
                <p className="mt-1 text-xs text-gray-500">Leave blank to keep existing password</p>
              )}
            </div>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-700">
              These credentials will be used automatically for login steps when running Playwright tests.
            </p>
          </div>
        </div>
      </Card>

      {/* Integrations Link */}
      <Card>
        <CardTitle>Integrations</CardTitle>
        <p className="text-sm text-gray-500 mb-4">
          Connect this project to Jira, Azure DevOps, and other services
        </p>
        <Link
          to={`/projects/${projectId}/integrations`}
          className="inline-flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
        >
          Manage Integrations
          <ArrowRightIcon className="w-4 h-4" />
        </Link>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving} isLoading={isSaving}>
          Save Settings
        </Button>
      </div>

      {/* Danger Zone */}
      <Card className="border-red-200">
        <CardTitle className="text-red-600">Danger Zone</CardTitle>
        <p className="text-sm text-gray-500 mt-2 mb-4">
          Permanently delete this project and all its data
        </p>
        <Button variant="outline" className="border-red-300 text-red-600 hover:bg-red-50">
          Delete Project
        </Button>
      </Card>
    </div>
  )
}
