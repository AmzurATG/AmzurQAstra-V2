/**
 * Persists PM sync scope chosen in "Sync from Integration" so "Sync now" uses the same integration, issue types, and Jira sprint scope.
 */
const STORAGE_KEY_PREFIX = 'qaastra.pmSyncPrefs.v1'

export interface PmSyncPreferences {
  integration_type: string
  issue_types: string[]
  force_full_sync: boolean
  /** Jira: when true, no sprint filter (all sprints) */
  all_sprints?: boolean
  /** Jira: when all_sprints is false, one or more sprint ids */
  sprint_ids?: number[]
  /** @deprecated use all_sprints + sprint_ids */
  sprint_id?: number | null
}

function storageKey(projectId: number): string {
  return `${STORAGE_KEY_PREFIX}:${projectId}`
}

export function getPmSyncPreferences(projectId: number): PmSyncPreferences | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(storageKey(projectId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as PmSyncPreferences
    if (
      !parsed ||
      typeof parsed.integration_type !== 'string' ||
      !Array.isArray(parsed.issue_types) ||
      parsed.issue_types.length === 0
    ) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function setPmSyncPreferences(projectId: number, prefs: PmSyncPreferences): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(storageKey(projectId), JSON.stringify(prefs))
  } catch {
    // ignore quota / private mode
  }
}

/** Build Jira sprint fields for POST /sync from saved prefs (legacy sprint_id supported). */
export function jiraSprintPayloadFromPrefs(prefs: PmSyncPreferences): { sprint_ids?: number[] } {
  if (prefs.integration_type !== 'jira') return {}
  if (prefs.all_sprints === true) return {}
  if (prefs.sprint_ids && prefs.sprint_ids.length > 0) {
    return { sprint_ids: [...prefs.sprint_ids] }
  }
  if (prefs.sprint_id != null) {
    return { sprint_ids: [prefs.sprint_id] }
  }
  return {}
}

/** Restore Jira sprint UI: all-sprints vs specific id list (legacy sprint_id). */
export function jiraSprintStateFromPrefs(prefs: PmSyncPreferences | null): {
  allSprints: boolean
  selectedIds: number[]
} {
  if (!prefs || prefs.integration_type !== 'jira') {
    return { allSprints: true, selectedIds: [] }
  }
  if (prefs.all_sprints === true) {
    return { allSprints: true, selectedIds: [] }
  }
  if (prefs.sprint_ids && prefs.sprint_ids.length > 0) {
    return { allSprints: false, selectedIds: [...prefs.sprint_ids] }
  }
  if (prefs.sprint_id != null) {
    return { allSprints: false, selectedIds: [prefs.sprint_id] }
  }
  return { allSprints: true, selectedIds: [] }
}
