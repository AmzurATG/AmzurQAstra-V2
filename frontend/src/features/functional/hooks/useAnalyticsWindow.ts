import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import type { AnalyticsWindow } from '../types'

const VALID = new Set(['7d', '30d', '90d'])

export function useAnalyticsWindow() {
  const [searchParams, setSearchParams] = useSearchParams()

  const window = useMemo((): AnalyticsWindow => {
    const raw = searchParams.get('window') || '30d'
    return (VALID.has(raw) ? raw : '30d') as AnalyticsWindow
  }, [searchParams])

  const setWindow = useCallback(
    (w: AnalyticsWindow) => {
      const next = new URLSearchParams(searchParams)
      next.set('window', w)
      setSearchParams(next, { replace: true })
    },
    [searchParams, setSearchParams]
  )

  return { window, setWindow }
}
