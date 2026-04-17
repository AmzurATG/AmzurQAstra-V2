import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { Card } from '@common/components/ui/Card'
import { Loader } from '@common/components/ui/Loader'
import { CheckCircleIcon, XCircleIcon, PauseCircleIcon } from '@heroicons/react/24/outline'
import { getProjectIntegrations, type IntegrationResponse } from '@common/api/integrations'

interface IntegrationCard {
  id: string
  name: string
  description: string
  logo: string
  color: string
  features: readonly string[]
  comingSoon?: boolean
  /** When true, card stays disabled until this integration exists for the project (see Azure DevOps). */
  disabledUntilConfigured?: boolean
}

// Integration card data (routes use these ids — must match App.tsx paths)
const integrations: readonly IntegrationCard[] = [
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
    disabledUntilConfigured: true,
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
] as const satisfies readonly IntegrationCard[]

/** Backend `integration_type` → card `id` (see IntegrationType enum). */
const API_TYPE_TO_CARD_ID: Record<string, string> = {
  jira: 'jira',
  azure_devops: 'azure-devops',
  redmine: 'redmine',
  github: 'github',
  slack: 'slack',
  confluence: 'confluence',
}

export default function ProjectIntegrations() {
  const { projectId } = useParams<{ projectId: string }>()
  const [rows, setRows] = useState<IntegrationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const data = await getProjectIntegrations(Number(projectId))
      setRows(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error(e)
      setError('Could not load integration status.')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    load()
  }, [load])

  const byCardId = useMemo(() => {
    const m = new Map<string, IntegrationResponse>()
    for (const r of rows) {
      const cardId = API_TYPE_TO_CARD_ID[r.integration_type]
      if (cardId) m.set(cardId, r)
    }
    return m
  }, [rows])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-gray-600">
          Connect external tools to import requirements and sync test results
        </p>
      </div>

      {error && (
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
          {error}{' '}
          <button type="button" className="underline font-medium" onClick={() => load()}>
            Retry
          </button>
        </p>
      )}

      {/* Integration Cards Grid */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader size="lg" />
        </div>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrations.map((integration) => {
          const remote = byCardId.get(integration.id)
          const isConfigured = Boolean(remote)
          const isActive = Boolean(remote?.is_enabled)
          const isDisabledByFlag =
            Boolean(integration.comingSoon) ||
            (Boolean(integration.disabledUntilConfigured) && !isConfigured)

          return (
            <div key={integration.id} className="relative">
              {integration.comingSoon && (
                <div className="absolute top-3 right-3 z-10">
                  <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                    Coming Soon
                  </span>
                </div>
              )}
              {integration.disabledUntilConfigured && !isConfigured && (
                <div className="absolute top-3 right-3 z-10">
                  <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                    Not available
                  </span>
                </div>
              )}

              <Card
                className={`h-full transition-all ${
                  isDisabledByFlag
                    ? 'opacity-60 cursor-not-allowed'
                    : 'hover:shadow-lg cursor-pointer'
                }`}
              >
                {!isDisabledByFlag ? (
                  <Link
                    to={`/projects/${projectId}/integrations/${integration.id}`}
                    className="block"
                  >
                    <IntegrationCardContent
                      integration={integration}
                      remote={remote}
                      isConfigured={isConfigured}
                      isActive={isActive}
                    />
                  </Link>
                ) : (
                  <IntegrationCardContent
                    integration={integration}
                    remote={integration.comingSoon ? undefined : remote}
                    isConfigured={isConfigured}
                    isActive={isActive}
                  />
                )}
              </Card>
            </div>
          )
        })}
      </div>
      )}
    </div>
  )
}

function IntegrationCardContent({
  integration,
  remote,
  isConfigured,
  isActive,
}: {
  integration: (typeof integrations)[number]
  remote: IntegrationResponse | undefined
  isConfigured: boolean
  isActive: boolean
}) {
  return (
    <>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-12 h-12 ${integration.color} rounded-lg flex items-center justify-center text-2xl shrink-0`}
          >
            {integration.logo}
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900">{integration.name}</h3>
            {isConfigured ? (
              isActive ? (
                <span className="flex items-center gap-1 text-xs text-green-600">
                  <CheckCircleIcon className="w-3 h-3 shrink-0" />
                  Connected
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-amber-600">
                  <PauseCircleIcon className="w-3 h-3 shrink-0" />
                  Disabled
                </span>
              )
            ) : (
              <span className="flex items-center gap-1 text-xs text-gray-400">
                <XCircleIcon className="w-3 h-3 shrink-0" />
                Not configured
              </span>
            )}
            {remote?.last_sync_at && isActive && (
              <p className="text-xs text-gray-500 mt-0.5 truncate" title={remote.last_sync_at}>
                Last sync{' '}
                {formatDistanceToNow(new Date(remote.last_sync_at), { addSuffix: true })}
              </p>
            )}
          </div>
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-4">{integration.description}</p>

      <div className="space-y-1">
        {integration.features.map((feature, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm text-gray-500">
            <span className="w-1 h-1 bg-gray-400 rounded-full shrink-0" />
            {feature}
          </div>
        ))}
      </div>

      {isConfigured && isActive && (
        <p className="mt-4 text-xs font-medium text-primary-600">Open to manage →</p>
      )}
    </>
  )
}
