/**
 * Persists PM sync scope chosen in "Sync from Integration" so "Sync now" uses the same integration, issue types, and Jira sprint scope.
 * Server also stores `sync_scope` on the integration after each successful sync (cross-browser).
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

/** Comma-separated sprint ids for GET list/stats, or undefined when showing all stories. */
export function sprintIdsQueryFromPrefs(prefs: PmSyncPreferences | null): string | undefined {
  if (!prefs || prefs.integration_type !== 'jira') return undefined
  if (prefs.all_sprints === true) return undefined
  if (prefs.sprint_ids && prefs.sprint_ids.length > 0) {
    return prefs.sprint_ids.map(String).join(',')
  }
  if (prefs.sprint_id != null) {
    return String(prefs.sprint_id)
  }
  return undefined
}

/**
 * Jira: user did not choose "All sprints" and has not selected any sprint yet.
 * The list must not fall back to an unfiltered query (which would show every sprint's stories).
 */
export function isJiraScopedWithoutSprintSelection(
  prefs: PmSyncPreferences | null
): boolean {
  if (!prefs || prefs.integration_type !== 'jira') return false
  if (prefs.all_sprints === true) return false
  if (prefs.sprint_ids && prefs.sprint_ids.length > 0) return false
  if (prefs.sprint_id != null) return false
  return true
}

/** True when integration config has enough sync_scope for quick sync / hydration. */
export function hasValidSyncScopeForQuickSync(
  config: Record<string, unknown> | null | undefined
): boolean {
  const raw = config?.sync_scope as { issue_types?: string[] } | undefined
  return !!(raw && Array.isArray(raw.issue_types) && raw.issue_types.length > 0)
}

/** Restore Jira sprint UI from prefs. No prefs ⇒ user must opt in (nothing selected). */
export function jiraSprintStateFromPrefs(prefs: PmSyncPreferences | null): {
  allSprints: boolean
  selectedIds: number[]
} {
  if (!prefs || prefs.integration_type !== 'jira') {
    return { allSprints: false, selectedIds: [] }
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
  return { allSprints: false, selectedIds: [] }
}

type IntegrationRow = {
  integration_type: string
  is_enabled: boolean
  config?: Record<string, unknown> | null
}

/** Apply server `config.sync_scope` to localStorage so Sync now works on any device. Returns true if applied. */
export function hydratePmSyncPreferencesFromIntegrations(
  projectId: number,
  integrations: IntegrationRow[]
): boolean {
  const pm = integrations
    .filter(
      (i) =>
        i.is_enabled && ['jira', 'redmine', 'azure_devops'].includes(i.integration_type)
    )
    .sort((a, b) => {
      // Prefer Jira with a usable sync_scope so sprint prefs hydrate reliably when multiple PM tools exist
      const score = (x: IntegrationRow) => {
        if (x.integration_type !== 'jira') return 1
        return hasValidSyncScopeForQuickSync(x.config as Record<string, unknown> | null)
          ? 0
          : 1
      }
      return score(a) - score(b)
    })
  for (const i of pm) {
    const raw = i.config?.sync_scope as
      | {
          integration_type?: string
          issue_types?: string[]
          force_full_sync?: boolean
          all_sprints?: boolean
          sprint_ids?: number[] | null
        }
      | undefined
    if (!raw || !Array.isArray(raw.issue_types) || raw.issue_types.length === 0) {
      continue
    }
    const it = raw.integration_type || i.integration_type
    const base: PmSyncPreferences = {
      integration_type: it,
      issue_types: [...raw.issue_types],
      force_full_sync: raw.force_full_sync ?? true,
    }
    if (it === 'jira') {
      if (raw.all_sprints === true) {
        base.all_sprints = true
      } else if (raw.sprint_ids && raw.sprint_ids.length > 0) {
        base.all_sprints = false
        base.sprint_ids = raw.sprint_ids.map((n) => Number(n))
      } else {
        // Server payload missing sprint list — do not assume "all sprints" (that overwrote scoped prefs)
        base.all_sprints = false
      }
    }
    setPmSyncPreferences(projectId, base)
    return true
  }
  return false
}
