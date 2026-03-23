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

export default function AzureDevOpsIntegration() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  
  const [config, setConfig] = useState({
    organization_url: '',
    personal_access_token: '',
    project_name: '',
  })
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [existingIntegration, setExistingIntegration] = useState<boolean>(false)
  const [azureProjects, setAzureProjects] = useState<RemoteProject[]>([])

  // Load existing integration if any
  useEffect(() => {
    const loadExisting = async () => {
      if (!projectId) return
      try {
        const integration = await getProjectIntegration(Number(projectId), 'azure_devops')
        if (integration && integration.config) {
          setExistingIntegration(true)
          setConfig({
            organization_url: integration.config.organization_url || '',
            personal_access_token: '', // PAT is redacted by backend, user must re-enter to update
            project_name: integration.config.project_name || '',
          })
          setIsConnected(true)
        }
      } catch {
        // Integration doesn't exist yet
      }
    }
    loadExisting()
  }, [projectId])

  const handleTestConnection = async () => {
    if (!config.organization_url || !config.personal_access_token) {
      toast.error('Please fill in all required fields')
      return
    }

    setIsConnecting(true)
    try {
      const result = await testIntegrationConnection(
        Number(projectId),
        'azure_devops',
        {
          organization_url: config.organization_url,
          personal_access_token: config.personal_access_token,
        }
      )
      
      if (result.success) {
        setIsConnected(true)
        // Store projects if returned
        if (result.projects && result.projects.length > 0) {
          setAzureProjects(result.projects)
        }
        toast.success('Successfully connected to Azure DevOps!')
      } else {
        toast.error(result.message || 'Failed to connect to Azure DevOps')
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to connect to Azure DevOps'
      toast.error(message)
    } finally {
      setIsConnecting(false)
    }
  }

  const handleSave = async () => {
    if (!config.project_name) {
      toast.error('Please enter an Azure DevOps project name')
      return
    }

    setIsSaving(true)
    try {
      const integrationData = {
        integration_type: 'azure_devops',
        name: 'Azure DevOps',
        config: {
          organization_url: config.organization_url,
          personal_access_token: config.personal_access_token,
          project_name: config.project_name,
        },
        is_enabled: true,
      }

      if (existingIntegration) {
        await updateProjectIntegration(Number(projectId), 'azure_devops', integrationData)
      } else {
        await createProjectIntegration(Number(projectId), integrationData)
      }
      
      toast.success('Azure DevOps integration saved!')
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
            <span className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-xl">
              🔷
            </span>
            Azure DevOps Integration
          </h1>
          <p className="text-gray-600">Connect to Azure DevOps for work items and test management</p>
        </div>
      </div>

      {/* Connection Settings */}
      <Card>
        <CardTitle>Connection Settings</CardTitle>
        <p className="text-sm text-gray-500 mb-4">
          Enter your Azure DevOps credentials. You can create a Personal Access Token (PAT) at{' '}
          <a
            href="https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:underline"
          >
            Azure DevOps Settings
          </a>
        </p>

        <div className="space-y-4">
          <Input
            label="Organization URL *"
            value={config.organization_url}
            onChange={(e) => setConfig({ ...config, organization_url: e.target.value })}
            placeholder="https://dev.azure.com/your-organization"
          />
          
          <div>
            <Input
              label={existingIntegration ? "Personal Access Token (PAT) * (enter to update)" : "Personal Access Token (PAT) *"}
              type="password"
              value={config.personal_access_token}
              onChange={(e) => setConfig({ ...config, personal_access_token: e.target.value })}
              placeholder={existingIntegration ? "Enter PAT to re-authenticate" : "Your Azure DevOps PAT"}
            />
            {existingIntegration && !config.personal_access_token && (
              <p className="text-xs text-amber-600 mt-1">
                PAT is saved but hidden for security. Enter a new PAT to update or test connection.
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

      {/* Project Mapping */}
      {isConnected && (
        <Card>
          <CardTitle>Project Mapping</CardTitle>
          <p className="text-sm text-gray-500 mb-4">
            Select which Azure DevOps project to sync with this QAstra project
          </p>

          <div className="space-y-4">
            {azureProjects.length > 0 ? (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Azure DevOps Project *
                </label>
                <select
                  value={config.project_name}
                  onChange={(e) => setConfig({ ...config, project_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select a project...</option>
                  {azureProjects.map((project) => (
                    <option key={project.key} value={project.name}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
            ) : existingIntegration && config.project_name ? (
              // Show saved project info for existing integration
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm font-medium text-gray-700">Selected Project</p>
                <p className="text-base text-gray-900">{config.project_name}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Test connection again to change the project
                </p>
              </div>
            ) : (
              <>
                <Input
                  label="Azure DevOps Project Name *"
                  value={config.project_name}
                  onChange={(e) => setConfig({ ...config, project_name: e.target.value })}
                  placeholder="e.g., WebApp"
                />
                <p className="text-xs text-gray-500 -mt-2">
                  Enter the exact project name from Azure DevOps
                </p>
              </>
            )}
          </div>
        </Card>
      )}

      {/* Import Options */}
      {isConnected && config.project_name && (
        <Card>
          <CardTitle>Import Options</CardTitle>
          <p className="text-sm text-gray-500 mb-4">
            Configure what to import from Azure DevOps
          </p>

          <div className="space-y-3">
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Import User Stories as Requirements</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Import Features as Requirement Groups</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Import Bugs for Regression Testing</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Sync Test Results to Test Plans</span>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Trigger Pipeline on Test Completion</span>
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
        <Button onClick={handleSave} disabled={!isConnected || !config.project_name} isLoading={isSaving}>
          Save Integration
        </Button>
      </div>
    </div>
  )
}
