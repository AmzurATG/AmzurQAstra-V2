import { useCallback, useEffect, useState } from 'react'
import { dashboardApi } from '@features/functional/api'
import type { DashboardOverview } from '@features/functional/types'

export function useDashboardOverview() {
  const [data, setData] = useState<DashboardOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const overview = await dashboardApi.overview()
      setData(overview)
    } catch {
      setError('Failed to load dashboard')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, reload: load }
}
