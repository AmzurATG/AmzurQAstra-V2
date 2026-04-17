import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { ArrowLeftIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  testIntegrationConnection,
  createProjectIntegration,
  getProjectIntegration,
  updateProjectIntegration,
  RemoteProject,
} from '@common/api/integrations'

function sortJiraProjectsByKey(projects: RemoteProject[]): RemoteProject[] {
  return [...projects].sort((a, b) =>
    a.key.localeCompare(b.key, undefined, { sensitivity: 'base' })
  )
}

export default function JiraIntegration() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  
  const [config, setConfig] = useState({
    base_url: '',
    email: '',
    api_token: '',
    project_key: '',
    project_name: '',
  })
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [existingIntegration, setExistingIntegration] = useState<boolean>(false)
  const [jiraProjects, setJiraProjects] = useState<RemoteProject[]>([])

  // Load existing integration if any
  useEffect(() => {
    const loadExisting = async () => {
      if (!projectId) return
      try {
        const integration = await getProjectIntegration(Number(projectId), 'jira')
        if (integration && integration.config) {
          setExistingIntegration(true)
          setConfig({
            base_url: integration.config.base_url || '',
            email: integration.config.email || '',
            api_token: '', // API token is redacted by backend, user must re-enter to update
            project_key: integration.config.project_key || '',
            project_name: integration.config.project_name || '',
          })
          setIsConnected(true)
        }
      } catch {
        // Integration doesn't exist yet, that's fine
      }
    }
    loadExisting()
  }, [projectId])

  const handleTestConnection = async () => {
    if (!config.base_url || !config.email || !config.api_token) {
      toast.error('Please fill in all required fields')
      return
    }

    setIsConnecting(true)
    try {
      const result = await testIntegrationConnection(
        Number(projectId),
        'jira',
        {
          base_url: config.base_url,
          email: config.email,
          api_token: config.api_token,
        }
      )
      
      if (result.success) {
        setIsConnected(true)
        // Store projects if returned
        if (result.projects && result.projects.length > 0) {
          setJiraProjects(sortJiraProjectsByKey(result.projects))
        }
        toast.success('Successfully connected to Jira!')
      } else {
        toast.error(result.message || 'Failed to connect to Jira')
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to connect to Jira'
      toast.error(message)
    } finally {
      setIsConnecting(false)
    }
  }

  const handleSave = async () => {
    if (!config.project_key) {
      toast.error('Please select a Jira project')
      return
    }

    setIsSaving(true)
    try {
      const integrationData = {
        integration_type: 'jira',
        name: 'Jira',
        config: {
          base_url: config.base_url,
          email: config.email,
          api_token: config.api_token,
          project_key: config.project_key,
          project_name: config.project_name,
        },
        is_enabled: true,
      }

      if (existingIntegration) {
        await updateProjectIntegration(Number(projectId), 'jira', integrationData)
      } else {
        await createProjectIntegration(Number(projectId), integrationData)
      }
      
      toast.success('Jira integration saved!')
      navigate(`/projects/${projectId}/integrations`)
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to save integration'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to={`/projects/${projectId}/integrations`}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeftIcon className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <span className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center text-xl">
              🎫
            </span>
            Jira Integration
          </h1>
          <p className="text-gray-600">Connect to Jira to import requirements and sync results</p>
        </div>
      </div>

      {/* Connection Settings */}
      <Card>
        <CardTitle>Connection Settings</CardTitle>
        <p className="text-sm text-gray-500 mb-4">
          Enter your Jira Cloud credentials. You can find your API token at{' '}
          <a
            href="https://id.atlassian.com/manage-profile/security/api-tokens"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:underline"
          >
            Atlassian Account Settings
          </a>
        </p>

        <div className="space-y-4">
          <Input
            id="jira-base-url"
            label="Jira Base URL"
            required
            value={config.base_url}
            onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
            placeholder="https://your-company.atlassian.net"
          />
          
          <Input
            id="jira-email"
            label="Email"
            type="email"
            required
            value={config.email}
            onChange={(e) => setConfig({ ...config, email: e.target.value })}
            placeholder="your-email@company.com"
          />
          
          <div>
            <Input
              id="jira-api-token"
              label={existingIntegration ? 'API Token (enter to update)' : 'API Token'}
              type="password"
              required={!existingIntegration}
              value={config.api_token}
              onChange={(e) => setConfig({ ...config, api_token: e.target.value })}
              placeholder={existingIntegration ? "Enter token to re-authenticate" : "Your Jira API token"}
            />
            {existingIntegration && !config.api_token && (
              <p className="text-xs text-amber-600 mt-1">
                Token is saved but hidden for security. Enter a new token to update or test connection.
              </p>
            )}
          </div>

          <Button
            onClick={handleTestConnection}
            isLoading={isConnecting}
            variant={isConnected ? 'outline' : 'primary'}
          >
            {isConnected ? (
              <>
                <CheckCircleIcon className="w-4 h-4 mr-2 text-green-500" />
                Connected
              </>
            ) : (
              'Test Connection'
            )}
          </Button>
        </div>
      </Card>

      {/* Project Mapping - only show after successful connection */}
      {isConnected && (
        <Card>
          <CardTitle>Project Mapping</CardTitle>
          <p className="text-sm text-gray-500 mb-4">
            Select which Jira project to sync with this QAstra project
          </p>

          <div className="space-y-4">
            {jiraProjects.length > 0 ? (
              <div>
                <label htmlFor="jira-project-select" className="block text-sm font-medium text-gray-700 mb-1">
                  Jira Project
                  <span className="text-red-500 ml-0.5" aria-hidden="true">
                    *
                  </span>
                </label>
                <select
                  id="jira-project-select"
                  value={config.project_key}
                  onChange={(e) => {
                    const selectedProject = jiraProjects.find(p => p.key === e.target.value)
                    setConfig({
                      ...config,
                      project_key: e.target.value,
                      project_name: selectedProject?.name || '',
                    })
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select a project...</option>
                  {jiraProjects.map((project) => (
                    <option key={project.key} value={project.key}>
                      {project.key} - {project.name}
                    </option>
                  ))}
                </select>
              </div>
            ) : existingIntegration && config.project_key ? (
              // Show saved project info for existing integration
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm font-medium text-gray-700">Selected Project</p>
                <p className="text-base text-gray-900">
                  {config.project_key}{config.project_name && ` - ${config.project_name}`}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Test connection again to change the project
                </p>
              </div>
            ) : (
              <>
                <Input
                  id="jira-project-key"
                  label="Jira Project Key"
                  required
                  value={config.project_key}
                  onChange={(e) => setConfig({ ...config, project_key: e.target.value, project_name: '' })}
                  placeholder="e.g., PROJ, TEST, MYPROJECT"
                />
                <p className="text-xs text-gray-500 -mt-2">
                  The project key is the prefix used in issue IDs (e.g., PROJ-123)
                </p>
              </>
            )}
          </div>
        </Card>
      )}

      {/* Import Options */}
      {isConnected && config.project_key && (
        <Card>
          <CardTitle>Import Options</CardTitle>
          <p className="text-sm text-gray-500 mb-4">
            Configure what to import from Jira
          </p>

          <div className="space-y-3">
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Import Stories as Requirements</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Import Epics as Requirement Groups</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Import Bugs for Regression Testing</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Sync Test Results back to Jira</span>
            </label>
          </div>
        </Card>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button
          variant="outline"
          onClick={() => navigate(`/projects/${projectId}/integrations`)}
        >
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={!isConnected || !config.project_key} isLoading={isSaving}>
          Save Integration
        </Button>
      </div>
    </div>
  )
}
