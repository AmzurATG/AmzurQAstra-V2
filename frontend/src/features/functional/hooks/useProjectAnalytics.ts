import { useCallback, useEffect, useState } from 'react'

import { analyticsApi } from '../api'
import type { AnalyticsWindow, ProjectAnalytics } from '../types'

export function useProjectAnalytics(
  projectId: string | undefined,
  window: AnalyticsWindow,
  source: string = 'functional'
) {
  const [data, setData] = useState<ProjectAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await analyticsApi.getProject(Number(projectId), {
        window,
        source,
      })
      setData(res)
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? String(
              (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
                'Failed to load analytics'
            )
          : 'Failed to load analytics'
      setError(msg)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [projectId, window, source])

  useEffect(() => {
    let cancelled = false
    if (!projectId) {
      setLoading(false)
      setData(null)
      return
    }
    setLoading(true)
    setError(null)
    analyticsApi
      .getProject(Number(projectId), { window, source })
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          const msg =
            e && typeof e === 'object' && 'response' in e
              ? String(
                  (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
                    'Failed to load analytics'
                )
              : 'Failed to load analytics'
          setError(msg)
          setData(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectId, window, source])

  return { data, loading, error, reload: load }
}
