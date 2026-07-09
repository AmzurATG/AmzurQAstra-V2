/** Display helpers for test-run status (majority-pass should not look like FAILED). */

export type RunStatusTone = 'success' | 'danger' | 'info' | 'neutral'

export interface DisplayRunStatus {
  /** Canonical status used for icons/filters */
  status: string
  /** Human label shown in badges */
  label: string
  tone: RunStatusTone
  passRate: number
  hasFailures: boolean
}

export function passRate(passed: number, total: number): number {
  if (!total || total <= 0) return 0
  return Math.round((100 * passed) / total)
}

export function majorityPassed(passed: number, failed: number, total?: number): boolean {
  const t = total ?? passed + failed
  if (t <= 0) return false
  return passed > failed && passRate(passed, t) >= 50
}

/**
 * Map stored run.status + counts to what the UI should show.
 * Historical rows stored as `failed` with e.g. 177/25 still display as Passed.
 */
export function displayRunStatus(
  status: string,
  opts: { passed?: number; failed?: number; total?: number } = {}
): DisplayRunStatus {
  const raw = (status || '').toLowerCase()
  const passed = opts.passed ?? 0
  const failed = opts.failed ?? 0
  const total = opts.total ?? passed + failed
  const rate = passRate(passed, total)

  if (['running', 'pending', 'cancelled', 'error'].includes(raw)) {
    return {
      status: raw,
      label: raw.charAt(0).toUpperCase() + raw.slice(1),
      tone:
        raw === 'error' ? 'danger' : raw === 'running' ? 'info' : 'neutral',
      passRate: rate,
      hasFailures: false,
    }
  }

  if (majorityPassed(passed, failed, total)) {
    return {
      status: 'passed',
      label: failed === 0 ? 'Passed' : `Passed (${failed} failed)`,
      tone: 'success',
      passRate: rate,
      hasFailures: failed > 0,
    }
  }

  if (failed > 0 || raw === 'failed') {
    return {
      status: 'failed',
      label: 'Failed',
      tone: 'danger',
      passRate: rate,
      hasFailures: true,
    }
  }

  return {
    status: 'passed',
    label: 'Passed',
    tone: 'success',
    passRate: rate,
    hasFailures: false,
  }
}
