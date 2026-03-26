import { useState, useCallback } from 'react'
import { integrityCheckApi } from '../api'
import type { IntegrityCheckResult, IntegrityCheckRun } from '../types'

interface RunParams {
  projectId: number
  appUrl: string
  username?: string
  password?: string
  loginUrl?: string
  loginMode?: 'app_form' | 'google_sso'
  browserEngine?: 'playwright' | 'steel'
}

export function useIntegrityCheck() {
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<IntegrityCheckResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<IntegrityCheckRun[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)

  const runCheck = useCallback(async (params: RunParams) => {
    setIsRunning(true)
    setError(null)
    setResult(null)

    try {
      const response = await integrityCheckApi.run({
        project_id: params.projectId,
        app_url: params.appUrl,
        login_mode: params.loginMode ?? 'app_form',
        browser_engine: params.browserEngine,
        credentials:
          params.username || params.password
            ? {
                username: params.username,
                password: params.password,
                login_url: params.loginUrl || undefined,
              }
            : undefined,
      })
      setResult(response.data)
      return response.data
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Check failed'
      setError(msg)
      return null
    } finally {
      setIsRunning(false)
    }
  }, [])

  const loadHistory = useCallback(async (projectId: number) => {
    setIsLoadingHistory(true)
    try {
      const response = await integrityCheckApi.getHistory(projectId)
      setHistory(response.data)
    } catch {
      setHistory([])
    } finally {
      setIsLoadingHistory(false)
    }
  }, [])

  const clearResult = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return {
    isRunning,
    result,
    error,
    history,
    isLoadingHistory,
    runCheck,
    loadHistory,
    clearResult,
  }
}
