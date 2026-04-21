import { testRunsApi } from '../api'
import type { LiveProgressResponse } from '../types'

/**
 * Transport-agnostic live progress feed.
 *
 * Today: HTTP polling (below). Future drop-ins without any consumer change:
 *   - websocketProgressSource (SaaS real-time via a /ws/runs/:id socket)
 *   - electronIpcProgressSource (desktop shell, no network hop)
 *
 * The `ActiveTestRunProvider` is the sole consumer.
 */
export interface ProgressSource {
  /**
   * Begin streaming updates for `runId`.
   * @param onUpdate Called each time a fresh snapshot arrives.
   * @param onError  Called when a fetch/transport error occurs. Callers use this
   *                 to drive `connectionStatus` (consecutive failures → degraded/lost).
   * @returns Unsubscribe function; must be idempotent.
   */
  subscribe(
    runId: number,
    onUpdate: (progress: LiveProgressResponse) => void,
    onError?: (err: unknown) => void
  ): () => void
}

const ACTIVE_POLL_MS = 3_000
const HIDDEN_POLL_MS = 15_000

const TERMINAL_STATES = new Set([
  'completed',
  'passed',
  'failed',
  'error',
  'cancelled',
  'not_found',
])

export const isTerminalStatus = (status: string | undefined | null): boolean =>
  !!status && TERMINAL_STATES.has(status)

/**
 * HTTP polling implementation. Visibility-aware: backs off to 15s while the
 * document is hidden (background tab) and snaps back to 3s on focus.
 * Stops polling automatically when the run enters a terminal state.
 */
export const pollingProgressSource: ProgressSource = {
  subscribe(runId, onUpdate, onError) {
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | null = null
    let lastStatus: string | undefined

    const currentDelay = (): number => {
      if (typeof document === 'undefined') return ACTIVE_POLL_MS
      return document.visibilityState === 'hidden' ? HIDDEN_POLL_MS : ACTIVE_POLL_MS
    }

    const tick = async () => {
      if (stopped) return
      try {
        const res = await testRunsApi.getLiveProgress(runId, { lite: true })
        if (stopped) return
        lastStatus = res.data.status
        onUpdate(res.data)
        if (isTerminalStatus(res.data.status)) {
          stopped = true
          return
        }
      } catch (err) {
        if (!stopped) onError?.(err)
      }
      if (!stopped) {
        timer = setTimeout(tick, currentDelay())
      }
    }

    const handleVisibilityChange = () => {
      if (stopped || isTerminalStatus(lastStatus)) return
      if (document.visibilityState === 'visible') {
        if (timer) clearTimeout(timer)
        tick()
      }
    }

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', handleVisibilityChange)
    }

    tick()

    return () => {
      stopped = true
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibilityChange)
      }
    }
  },
}
