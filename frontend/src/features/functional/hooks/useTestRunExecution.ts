import { useState, useEffect, useRef, useCallback } from 'react'
import { testRunsApi } from '../api'
import type { LiveProgressResponse, TestRunCreateRequest } from '../types'

const POLL_INTERVAL = 3000

interface UseTestRunExecutionReturn {
  isCreating: boolean
  runId: number | null
  progress: LiveProgressResponse | null
  error: string | null
  startRun: (data: TestRunCreateRequest) => Promise<void>
  cancelRun: () => Promise<void>
  reset: () => void
}

export function useTestRunExecution(): UseTestRunExecutionReturn {
  const [isCreating, setIsCreating] = useState(false)
  const [runId, setRunId] = useState<number | null>(null)
  const [progress, setProgress] = useState<LiveProgressResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const poll = useCallback(async (id: number) => {
    try {
      const res = await testRunsApi.getLiveProgress(id, { lite: true })
      const data = res.data
      setProgress(data)

      if (['completed', 'passed', 'failed', 'error', 'cancelled', 'not_found'].includes(data.status)) {
        stopPolling()
      }
    } catch {
      // Silently retry on next interval
    }
  }, [stopPolling])

  const startPolling = useCallback((id: number) => {
    stopPolling()
    poll(id)
    pollRef.current = setInterval(() => poll(id), POLL_INTERVAL)
  }, [poll, stopPolling])

  const startRun = useCallback(async (data: TestRunCreateRequest) => {
    setIsCreating(true)
    setError(null)
    setProgress(null)
    try {
      const res = await testRunsApi.create(data)
      const id = res.data.run_id
      setRunId(id)
      startPolling(id)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to start test run'
      setError(msg)
    } finally {
      setIsCreating(false)
    }
  }, [startPolling])

  const cancelRun = useCallback(async () => {
    if (!runId) return
    try {
      await testRunsApi.cancel(runId)
      stopPolling()
      setProgress((prev) => prev ? { ...prev, status: 'cancelled' } : prev)
    } catch {
      // ignore
    }
  }, [runId, stopPolling])

  const reset = useCallback(() => {
    stopPolling()
    setRunId(null)
    setProgress(null)
    setError(null)
  }, [stopPolling])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  return { isCreating, runId, progress, error, startRun, cancelRun, reset }
}
