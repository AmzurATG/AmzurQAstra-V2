/**
 * Maps API / enum snake_case values to user-facing labels (Title Case).
 * Prefer explicit entries for product terms (e.g. Azure DevOps, E2E).
 */
const KNOWN_LABELS: Record<string, string> = {
  // Requirement source
  upload: 'Upload',
  jira: 'Jira',
  azure_devops: 'Azure DevOps',
  confluence: 'Confluence',
  manual: 'Manual',
  redmine: 'Redmine',
  // Processing / run status
  pending: 'Pending',
  processed: 'Processed',
  completed: 'Completed',
  running: 'Running',
  failed: 'Failed',
  error: 'Error',
  cancelled: 'Cancelled',
  canceled: 'Canceled',
  // User story / workflow
  open: 'Open',
  in_progress: 'In Progress',
  done: 'Done',
  blocked: 'Blocked',
  closed: 'Closed',
  // Test case
  draft: 'Draft',
  ready: 'Ready',
  deprecated: 'Deprecated',
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  smoke: 'Smoke',
  regression: 'Regression',
  e2e: 'E2E',
  integration: 'Integration',
  sanity: 'Sanity',
  // Test run outcomes
  passed: 'Passed',
  skipped: 'Skipped',
  // Sources
  ai: 'AI',
  csv: 'CSV',
}

/**
 * Converts a machine value (often snake_case) to a display label.
 * Unknown values are split on `_`, `-`, and spaces and title-cased.
 */
export function formatDisplayLabel(value: string | null | undefined): string {
  if (value == null || value === '') return '—'
  const trimmed = value.trim()
  const key = trimmed.toLowerCase()
  const known = KNOWN_LABELS[key]
  if (known) return known

  return key
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((word) => {
      if (word === 'e2e') return 'E2E'
      if (word === 'ai') return 'AI'
      if (word === 'csv') return 'CSV'
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    })
    .join(' ')
}

export function getDisplayLabel(
  value: string | null | undefined,
  config: Record<string, { label: string }>
): string {
  if (value == null || value === '') return '—'
  const key = value.trim().toLowerCase()
  return config[key]?.label ?? formatDisplayLabel(value)
}
