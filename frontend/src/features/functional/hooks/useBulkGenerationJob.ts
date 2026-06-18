import { useCallback, useEffect, useRef, useState } from 'react'
import { userStoriesApi } from '../api'
import type { GenerationJobStatusResponse } from '../types'

const POLL_INTERVAL_MS = 3000
const TERMINAL_STATUSES = new Set(['completed', 'failed'])

type Options = {
  onComplete?: (report: GenerationJobStatusResponse) => void
  onError?: (msg: string) => void
}

type State = {
  job: GenerationJobStatusResponse | null
  isPolling: boolean
  error: string | null
}

/**
 * Polls a bulk generation job until it reaches a terminal status.
 *
 * Usage:
 *   const { job, isPolling, startPolling } = useBulkGenerationJob(projectId, options)
 *   startPolling(jobId)          // call after POST /bulk-generate-tests returns job_id
 */
export function useBulkGenerationJob(
  projectId: number | undefined,
  { onComplete, onError }: Options = {},
) {
  const [state, setState] = useState<State>({ job: null, isPolling: false, error: null })
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const jobIdRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setState((prev) => ({ ...prev, isPolling: false }))
  }, [])

  const poll = useCallback(async () => {
    if (!projectId || jobIdRef.current === null) return
    try {
      const res = await userStoriesApi.getBulkGenerationStatus(projectId, jobIdRef.current)
      const data = res.data
      setState({ job: data, isPolling: !TERMINAL_STATUSES.has(data.status), error: null })

      if (TERMINAL_STATUSES.has(data.status)) {
        stopPolling()
        if (data.status === 'completed') {
          onComplete?.(data)
        } else if (data.status === 'failed') {
          const msg = data.error_message || 'Bulk generation failed.'
          onError?.(msg)
        }
      }
    } catch {
      const msg = 'Failed to fetch generation job status.'
      setState((prev) => ({ ...prev, isPolling: false, error: msg }))
      stopPolling()
      onError?.(msg)
    }
  }, [projectId, stopPolling, onComplete, onError])

  const startPolling = useCallback(
    (jobId: number) => {
      jobIdRef.current = jobId
      setState({ job: null, isPolling: true, error: null })
      // Immediate first fetch, then interval
      void poll()
      intervalRef.current = setInterval(poll, POLL_INTERVAL_MS)
    },
    [poll],
  )

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling])

  return {
    job: state.job,
    isPolling: state.isPolling,
    error: state.error,
    startPolling,
    stopPolling,
  }
}
