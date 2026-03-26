import { useState, useCallback, useEffect } from 'react'
import { authSessionsApi } from '../api'
import type { AuthSession, AuthMethod } from '../types'
import toast from 'react-hot-toast'

export function useAuthSession(projectId: number | undefined) {
  const [authMethod, setAuthMethod] = useState<AuthMethod>('none')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [savedSession, setSavedSession] = useState<AuthSession | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isCapturingOAuth, setIsCapturingOAuth] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!projectId) return
    setIsLoading(true)
    authSessionsApi
      .get(projectId)
      .then((r) => {
        if (r.data) {
          setSavedSession(r.data)
          // OAuth capture removed from integrity check — prompt user to use credentials
          if (r.data.auth_type === 'google_oauth') {
            setAuthMethod('none')
          } else {
            setAuthMethod(r.data.auth_type as AuthMethod)
          }
        }
      })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [projectId])

  const saveSession = useCallback(async () => {
    if (!projectId || !username || !password) return
    setIsSaving(true)
    try {
      const r = await authSessionsApi.save(projectId, username, password)
      setSavedSession(r.data)
      toast.success('Credentials saved securely')
    } catch {
      toast.error('Failed to save credentials')
    } finally {
      setIsSaving(false)
    }
  }, [projectId, username, password])

  const captureGoogleOAuth = useCallback(async (loginUrl: string) => {
    if (!projectId || !loginUrl) {
      toast.error('Enter the application URL first')
      return
    }
    setIsCapturingOAuth(true)
    const toastId = toast.loading(
      'A browser window is opening on the server. Sign in to Google, then wait...',
      { duration: 200_000 },
    )
    try {
      const r = await authSessionsApi.captureGoogleOAuth(projectId, loginUrl)
      setSavedSession(r.data)
      setAuthMethod('google_oauth')
      toast.success('Google session captured and saved!', { id: toastId })
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to capture Google session'
      toast.error(msg, { id: toastId })
    } finally {
      setIsCapturingOAuth(false)
    }
  }, [projectId])

  const clearSession = useCallback(async () => {
    if (!projectId) return
    try {
      await authSessionsApi.delete(projectId)
      setSavedSession(null)
      setAuthMethod('none')
      setUsername('')
      setPassword('')
      toast.success('Session cleared')
    } catch {
      toast.error('Failed to clear session')
    }
  }, [projectId])

  return {
    authMethod,
    setAuthMethod,
    username,
    setUsername,
    password,
    setPassword,
    savedSession,
    isSaving,
    isCapturingOAuth,
    isLoading,
    saveSession,
    captureGoogleOAuth,
    clearSession,
  }
}
