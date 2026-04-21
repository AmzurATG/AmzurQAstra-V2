import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useParams } from 'react-router-dom'

import { useProjectStore } from '@common/store/projectStore'
import { testRunsApi } from '../api'
import { isTerminalStatus, pollingProgressSource } from '../live/progressSource'
import type {
  LiveProgressResponse,
  TestRunCreateRequest,
} from '../types'

/**
 * Application-state orchestrator for the single in-flight test run belonging
 * to the currently-viewed project.
 *
 * Why a context (not another hook): multiple UI surfaces need the same truth
 * simultaneously — the pinned run strip on every Functional Testing tab, the
 * Live tab body, the "Run" buttons on the Cases tab, and (optionally) the
 * TestRunDetail page. Hosting the poller once here also prevents the double
 * polling we had when TestCases.tsx and TestRunDetail.tsx both subscribed.
 *
 * The transport (today: HTTP polling) is injected as a ProgressSource so the
 * SaaS WebSocket swap / Electron IPC swap is a one-file change.
 */

export type ConnectionStatus = 'ok' | 'degraded' | 'lost'

export interface ActiveTestRunContextValue {
  activeRunId: number | null
  progress: LiveProgressResponse | null
  isCreating: boolean
  isRunning: boolean
  error: string | null
  connectionStatus: ConnectionStatus
  /** Start a new run. Resolves with the new run id on success. */
  startRun: (data: TestRunCreateRequest) => Promise<number | null>
  cancelRun: () => Promise<void>
  /** Clear a completed/failed run from the strip so it stops showing. */
  dismissCompletedRun: () => void
  /**
   * Guard consumers use before dispatching a run so the provider can nag the
   * user to set an app URL. Returns true if the project has a usable app URL.
   */
  ensureProjectHasAppUrl: () => Promise<boolean>
}

const ActiveTestRunContext = createContext<ActiveTestRunContextValue | null>(null)

const DEGRADED_AFTER_FAILURES = 3
const LOST_AFTER_FAILURES = 10

interface ProviderProps {
  children: ReactNode
}

export function ActiveTestRunProvider({ children }: ProviderProps) {
  const { projectId } = useParams<{ projectId: string }>()

  const [activeRunId, setActiveRunId] = useState<number | null>(null)
  const [progress, setProgress] = useState<LiveProgressResponse | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('ok')

  const createInFlightRef = useRef(false)
  const unsubscribeRef = useRef<(() => void) | null>(null)
  const consecutiveFailuresRef = useRef(0)

  const stopSubscription = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current()
      unsubscribeRef.current = null
    }
  }, [])

  const attachSubscription = useCallback(
    (runId: number) => {
      stopSubscription()
      consecutiveFailuresRef.current = 0
      setConnectionStatus('ok')
      unsubscribeRef.current = pollingProgressSource.subscribe(
        runId,
        (snapshot) => {
          consecutiveFailuresRef.current = 0
          setConnectionStatus('ok')
          setProgress(snapshot)
          if (isTerminalStatus(snapshot.status)) {
            stopSubscription()
          }
        },
        () => {
          consecutiveFailuresRef.current += 1
          if (consecutiveFailuresRef.current >= LOST_AFTER_FAILURES) {
            setConnectionStatus('lost')
          } else if (consecutiveFailuresRef.current >= DEGRADED_AFTER_FAILURES) {
            setConnectionStatus('degraded')
          }
        }
      )
    },
    [stopSubscription]
  )

  // Tear down subscription when the user leaves the project or unmounts.
  useEffect(() => {
    return () => stopSubscription()
  }, [stopSubscription])

  // Scope the active run to the current project: switching projects resets.
  useEffect(() => {
    return () => {
      stopSubscription()
      setActiveRunId(null)
      setProgress(null)
      setError(null)
      setConnectionStatus('ok')
    }
  }, [projectId, stopSubscription])

  const ensureProjectHasAppUrl = useCallback(async (): Promise<boolean> => {
    if (!projectId) return false
    const store = useProjectStore.getState()
    if (store.currentProject?.app_url) return true
    await store.revalidateProject(projectId)
    return !!useProjectStore.getState().currentProject?.app_url
  }, [projectId])

  const startRun = useCallback(
    async (data: TestRunCreateRequest): Promise<number | null> => {
      if (createInFlightRef.current) return null

      // Single-active-run guard: refuse to kick off a second run while one is
      // still mid-flight. Cancelling is explicit via cancelRun().
      if (activeRunId && progress && !isTerminalStatus(progress.status)) {
        setError('A test run is already in progress. Cancel it before starting a new one.')
        return null
      }

      createInFlightRef.current = true
      setIsCreating(true)
      setError(null)
      setProgress(null)

      try {
        const res = await testRunsApi.create(data)
        const id = res.data.run_id
        setActiveRunId(id)
        attachSubscription(id)
        return id
      } catch (err) {
        const typed = err as { response?: { data?: { detail?: string } }; message?: string }
        setError(typed?.response?.data?.detail || typed?.message || 'Failed to start test run')
        return null
      } finally {
        createInFlightRef.current = false
        setIsCreating(false)
      }
    },
    [activeRunId, attachSubscription, progress]
  )

  const cancelRun = useCallback(async () => {
    if (!activeRunId) return
    try {
      await testRunsApi.cancel(activeRunId)
      // Optimistically mark as cancelling; keep the poller running so the
      // backend's eventual terminal "cancelled" wins.
      setProgress((prev) => (prev ? { ...prev, status: 'cancelling' } : prev))
      attachSubscription(activeRunId)
    } catch {
      // ignore — poller will keep trying
    }
  }, [activeRunId, attachSubscription])

  const dismissCompletedRun = useCallback(() => {
    if (progress && !isTerminalStatus(progress.status)) return
    stopSubscription()
    setActiveRunId(null)
    setProgress(null)
    setError(null)
  }, [progress, stopSubscription])

  const isRunning = !!progress && !isTerminalStatus(progress.status)

  const value = useMemo<ActiveTestRunContextValue>(
    () => ({
      activeRunId,
      progress,
      isCreating,
      isRunning,
      error,
      connectionStatus,
      startRun,
      cancelRun,
      dismissCompletedRun,
      ensureProjectHasAppUrl,
    }),
    [
      activeRunId,
      progress,
      isCreating,
      isRunning,
      error,
      connectionStatus,
      startRun,
      cancelRun,
      dismissCompletedRun,
      ensureProjectHasAppUrl,
    ]
  )

  return (
    <ActiveTestRunContext.Provider value={value}>
      {children}
    </ActiveTestRunContext.Provider>
  )
}

/**
 * Read active-run state/actions. Returns `null` when used outside the
 * provider (e.g. the Dashboard page) so callers can render a fallback instead
 * of crashing.
 */
export function useActiveTestRun(): ActiveTestRunContextValue | null {
  return useContext(ActiveTestRunContext)
}

/**
 * Strict variant for surfaces that must live inside the provider
 * (Functional Testing shell + tabs). Throws a clear error in dev if wired
 * incorrectly, instead of a cryptic undefined-access deeper in the tree.
 */
export function useRequiredActiveTestRun(): ActiveTestRunContextValue {
  const ctx = useContext(ActiveTestRunContext)
  if (!ctx) {
    throw new Error('useRequiredActiveTestRun must be used inside <ActiveTestRunProvider>')
  }
  return ctx
}
