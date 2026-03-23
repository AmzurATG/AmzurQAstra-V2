import { useParams, Link } from 'react-router-dom'
import { Card } from '@common/components/ui/Card'
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'

// Integration card data
const integrations = [
  {
    id: 'jira',
    name: 'Jira',
    description: 'Import requirements from Jira issues and sync test results',
    logo: '🎫',
    color: 'bg-blue-500',
    features: ['Import stories/epics', 'Sync test results', 'Link test cases to issues'],
  },
  {
    id: 'azure-devops',
    name: 'Azure DevOps',
    description: 'Connect to Azure DevOps for work items and test management',
    logo: '🔷',
    color: 'bg-blue-600',
    features: ['Import work items', 'Sync test plans', 'Pipeline integration'],
  },
  {
    id: 'redmine',
    name: 'Redmine',
    description: 'Import issues from Redmine as requirements',
    logo: '🔴',
    color: 'bg-red-500',
    features: ['Import issues', 'Sync status', 'Custom fields support'],
    comingSoon: true,
  },
  {
    id: 'github',
    name: 'GitHub Issues',
    description: 'Import GitHub issues and link to test cases',
    logo: '🐙',
    color: 'bg-gray-800',
    features: ['Import issues', 'PR comments', 'Actions integration'],
    comingSoon: true,
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Get notifications about test runs and failures',
    logo: '💬',
    color: 'bg-purple-500',
    features: ['Test run notifications', 'Failure alerts', 'Daily summaries'],
    comingSoon: true,
  },
  {
    id: 'confluence',
    name: 'Confluence',
    description: 'Import requirements from Confluence pages',
    logo: '📘',
    color: 'bg-blue-400',
    features: ['Import pages', 'Parse requirements', 'Link documentation'],
    comingSoon: true,
  },
]

export default function ProjectIntegrations() {
  const { projectId } = useParams<{ projectId: string }>()

  // Mock configured integrations - replace with actual API call
  const configuredIntegrations: Record<string, boolean> = {
    jira: false,
    'azure-devops': false,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-gray-600">
          Connect external tools to import requirements and sync test results
        </p>
      </div>

      {/* Integration Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrations.map((integration) => {
          const isConfigured = configuredIntegrations[integration.id]
          const isComingSoon = integration.comingSoon

          return (
            <div key={integration.id} className="relative">
              {isComingSoon && (
                <div className="absolute top-3 right-3 z-10">
                  <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                    Coming Soon
                  </span>
                </div>
              )}
              
              <Card
                className={`h-full transition-all ${
                  isComingSoon
                    ? 'opacity-60 cursor-not-allowed'
                    : 'hover:shadow-lg cursor-pointer'
                }`}
              >
                {!isComingSoon ? (
                  <Link
                    to={`/projects/${projectId}/integrations/${integration.id}`}
                    className="block"
                  >
                    <IntegrationCardContent
                      integration={integration}
                      isConfigured={isConfigured}
                    />
                  </Link>
                ) : (
                  <IntegrationCardContent
                    integration={integration}
                    isConfigured={false}
                  />
                )}
              </Card>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function IntegrationCardContent({
  integration,
  isConfigured,
}: {
  integration: typeof integrations[0]
  isConfigured: boolean
}) {
  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-12 h-12 ${integration.color} rounded-lg flex items-center justify-center text-2xl`}
          >
            {integration.logo}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{integration.name}</h3>
            {isConfigured ? (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircleIcon className="w-3 h-3" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-gray-400">
                <XCircleIcon className="w-3 h-3" />
                Not configured
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 mb-4">{integration.description}</p>

      {/* Features */}
      <div className="space-y-1">
        {integration.features.map((feature, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm text-gray-500">
            <span className="w-1 h-1 bg-gray-400 rounded-full" />
            {feature}
          </div>
        ))}
      </div>
    </>
  )
}
