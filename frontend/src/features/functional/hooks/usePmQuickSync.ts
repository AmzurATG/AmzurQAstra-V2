import { useCallback, useState } from 'react'
import toast from 'react-hot-toast'
import { userStoriesApi } from '../api'
import { DEFAULT_SYNC_ISSUE_TYPES } from '../constants/userStoryUi'

/**
 * One-click sync using the first enabled PM integration and default issue types.
 */
export function usePmQuickSync(
  projectId: string | undefined,
  onSuccess: () => void
) {
  const [isQuickSyncing, setIsQuickSyncing] = useState(false)

  const syncNow = useCallback(async () => {
    if (!projectId) return
    setIsQuickSyncing(true)
    try {
      const integrationsRes = await userStoriesApi.getIntegrations(Number(projectId))
      const pmIntegrations = integrationsRes.data.filter(
        (i) => i.is_enabled && ['jira', 'redmine', 'azure_devops'].includes(i.integration_type)
      )
      if (pmIntegrations.length === 0) {
        toast.error('No project management integration connected. Add one under Integrations.')
        return
      }
      const integration = pmIntegrations[0]
      const syncResponse = await userStoriesApi.sync(Number(projectId), {
        integration_type: integration.integration_type,
        issue_types: [...DEFAULT_SYNC_ISSUE_TYPES],
        force_full_sync: false,
      })
      if (syncResponse.data.status === 'success') {
        const n = syncResponse.data.items_synced
        if (n === 0) {
          toast.success('Already up to date — no new or changed issues.')
        } else {
          toast.success(`Synced ${n} item${n === 1 ? '' : 's'}.`)
        }
        onSuccess()
      } else {
        toast.error(syncResponse.data.message || 'Sync completed with errors')
      }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to sync')
    } finally {
      setIsQuickSyncing(false)
    }
  }, [projectId, onSuccess])

  return { isQuickSyncing, syncNow }
}
