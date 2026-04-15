import { useCallback, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { userStoriesApi } from '../api'
import {
  getPmSyncPreferences,
  hydratePmSyncPreferencesFromIntegrations,
  jiraSprintPayloadFromPrefs,
} from '../utils/pmSyncPreferences'

/**
 * One-click sync using the same integration, issue types, and Jira sprint as the last successful "Sync from Integration".
 *
 * @param remoteQuickSyncAllowed — true when GET integrations shows a stored sync_scope (enables button before localStorage hydrate, e.g. new browser).
 */
export function usePmQuickSync(
  projectId: string | undefined,
  onSuccess: () => void,
  remoteQuickSyncAllowed = false
) {
  const [isQuickSyncing, setIsQuickSyncing] = useState(false)
  const [prefsVersion, setPrefsVersion] = useState(0)

  const preferences = useMemo(() => {
    if (!projectId) return null
    return getPmSyncPreferences(Number(projectId))
  }, [projectId, prefsVersion])

  const hasConfiguredSync = preferences !== null || remoteQuickSyncAllowed

  const refreshPreferences = useCallback(() => {
    setPrefsVersion((v) => v + 1)
  }, [])

  const syncNow = useCallback(async () => {
    if (!projectId) return
    let prefs = getPmSyncPreferences(Number(projectId))
    if (!prefs) {
      try {
        const res = await userStoriesApi.getIntegrations(Number(projectId))
        hydratePmSyncPreferencesFromIntegrations(Number(projectId), res.data)
        refreshPreferences()
        prefs = getPmSyncPreferences(Number(projectId))
      } catch {
        // fall through
      }
    }
    if (!prefs) {
      toast.error('Use Sync from Integration first to choose integration and scope.')
      return
    }
    setIsQuickSyncing(true)
    try {
      const syncResponse = await userStoriesApi.sync(Number(projectId), {
        integration_type: prefs.integration_type,
        issue_types: [...prefs.issue_types],
        force_full_sync: prefs.force_full_sync,
        ...(prefs.integration_type === 'jira' ? jiraSprintPayloadFromPrefs(prefs) : {}),
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
  }, [projectId, onSuccess, refreshPreferences])

  return {
    isQuickSyncing,
    syncNow,
    hasConfiguredSync,
    refreshPreferences,
    /** Bump when preferences change so list/stats refetch with sprint scope */
    prefsVersion,
  }
}
