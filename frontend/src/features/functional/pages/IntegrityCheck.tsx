import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { useProjectStore } from '@common/store/projectStore'
import { integrityCheckApi } from '../api'
import toast from 'react-hot-toast'
import { ShieldCheckIcon, PlayIcon } from '@heroicons/react/24/outline'
import type { RunStatusResponse, IntegrityCheckPreview } from '../types'
import IntegrityCheckProgress from './IntegrityCheckProgress'
import IntegrityCheckResults from './IntegrityCheckResults'
import IntegrityCheckExecutionPreview from './IntegrityCheckExecutionPreview'

const POLL_INTERVAL_MS = 2000

export default function IntegrityCheck() {
  const { projectId } = useParams<{ projectId: string }>()
  const { currentProject, fetchProject } = useProjectStore()

  const [appUrl, setAppUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [_runId, setRunId] = useState<string | null>(null)
  const [progress, setProgress] = useState<RunStatusResponse | null>(null)
  const [result, setResult] = useState<RunStatusResponse | null>(null)
  const [preview, setPreview] = useState<IntegrityCheckPreview | null>(null)
  const [expandedStories, setExpandedStories] = useState<Set<number>>(new Set())
  const [expandedTcs, setExpandedTcs] = useState<Set<number>>(new Set())

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (projectId) { fetchProject(projectId); loadPreview() }
  }, [projectId])

  useEffect(() => {
    if (currentProject) {
      if (currentProject.app_url) setAppUrl(currentProject.app_url)
      if (currentProject.app_username) setUsername(currentProject.app_username)
      if (currentProject.app_password) setPassword(currentProject.app_password)
    }
  }, [currentProject])

  // Cleanup polling on unmount
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const loadPreview = async () => {
    try {
      const res = await integrityCheckApi.getPreview(Number(projectId))
      setPreview(res.data)
    } catch { /* silent */ }
  }

  const startPolling = (id: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await integrityCheckApi.getStatus(id)
        setProgress(res.data)
        if (res.data.status === 'completed' || res.data.status === 'error') {
          clearInterval(pollRef.current!)
          pollRef.current = null
          setResult(res.data)
          setIsRunning(false)
          if (res.data.status === 'error') {
            toast.error('Check encountered an error')
          } else if (res.data.overall_status === 'passed') {
            toast.success('Integrity check passed.')
          } else {
            toast.error('Integrity check reported failures.')
          }
        }
      } catch {
        clearInterval(pollRef.current!)
        pollRef.current = null
        setIsRunning(false)
      }
    }, POLL_INTERVAL_MS)
  }

  const handleRunCheck = async () => {
    if (!appUrl) { toast.error('Please enter an application URL'); return }
    if (!projectId) return

    setIsRunning(true)
    setResult(null)
    setProgress(null)

    try {
      const res = await integrityCheckApi.startRun({
        project_id: parseInt(projectId),
        app_url: appUrl,
        use_google_signin: false,
        credentials:
          username || password ? { username, password } : undefined,
      })
      setRunId(res.data.run_id)
      startPolling(res.data.run_id)
      toast.success('Check started — Chrome browser is opening…')
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to start integrity check'
      toast.error(msg)
      setIsRunning(false)
    }
  }

  const toggleStory = (id: number) =>
    setExpandedStories(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleTc = (id: number) =>
    setExpandedTcs(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Build Integrity Check</h1>
        <p className="text-gray-600">Verify your application is ready for testing</p>
      </div>

      {/* Config form */}
      <Card>
        <CardTitle>Configuration</CardTitle>
        <div className="mt-4 space-y-4">
          <Input label="Application URL" value={appUrl} onChange={e => setAppUrl(e.target.value)}
            placeholder="https://app.example.com" disabled={isRunning} />
          <div
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-3"
            role="status"
            aria-label="Google Sign-In unavailable"
          >
            <p className="text-sm font-medium text-gray-800">Google Sign-In</p>
            <p className="text-xs text-gray-600 mt-1">
              This option is turned off for now. Automated Google login for Build Integrity Check is not supported yet; we plan to add it in a future release. Please use{' '}
              <span className="font-medium text-gray-800">username and password</span> when the run opens the browser.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Username (optional)"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="you@company.com"
              disabled={isRunning}
            />
            <Input
              label="Password (optional)"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={isRunning}
            />
          </div>
          <Button onClick={handleRunCheck} isLoading={isRunning} disabled={!appUrl || isRunning}>
            <PlayIcon className="w-4 h-4 mr-2" />
            {isRunning ? 'Check Running…' : 'Run Integrity Check'}
          </Button>
        </div>
      </Card>

      {/* Live progress panel */}
      {isRunning && progress && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheckIcon className="w-5 h-5 text-blue-600" />
            <CardTitle>Running Check</CardTitle>
          </div>
          <IntegrityCheckProgress
            percentage={progress.percentage}
            currentStep={progress.current_step || 'Starting…'}
            status={progress.status}
            screenshots={progress.screenshots}
          />
        </Card>
      )}

      {/* Initial spinner before first poll response */}
      {isRunning && !progress && (
        <Card>
          <div className="flex flex-col items-center py-8 gap-3 text-gray-500">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm">Opening Chrome browser…</p>
          </div>
        </Card>
      )}

      {/* Final result */}
      {result && !isRunning && <IntegrityCheckResults result={result} />}

      {!isRunning && !result && (
        <IntegrityCheckExecutionPreview
          preview={preview}
          expandedStories={expandedStories}
          expandedTcs={expandedTcs}
          onToggleStory={toggleStory}
          onToggleTc={toggleTc}
        />
      )}
    </div>
  )
}
