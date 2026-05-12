import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { useProjectStore } from '@common/store/projectStore'
import { integrityCheckApi } from '../api'
import toast from 'react-hot-toast'
import {
  ShieldCheckIcon,
  PlayIcon,
  EnvelopeIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  EyeIcon,
} from '@heroicons/react/24/outline'
import type { RunStatusResponse, IntegrityCheckPreview } from '../types'
import IntegrityCheckProgress from './IntegrityCheckProgress'
import IntegrityCheckResults from './IntegrityCheckResults'
import IntegrityCheckExecutionPreview from './IntegrityCheckExecutionPreview'
import EmailReportDialog from '../components/EmailReportDialog'

const POLL_INTERVAL_MS = 2000

type HistoryItem = {
  id: number
  run_id: string
  status: string
  app_url: string
  overall_status: string | null
  steps_total: number | null
  duration_ms: number | null
  created_at: string | null
}

function fmtDuration(ms?: number | null) {
  if (!ms) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

function fmtDate(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function OverallStatusBadge({ status }: { status: string | null }) {
  if (status === 'passed')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
        <CheckCircleIcon className="w-3.5 h-3.5" /> Passed
      </span>
    )
  if (status === 'failed')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
        <XCircleIcon className="w-3.5 h-3.5" /> Failed
      </span>
    )
  if (status === 'error')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
        <XCircleIcon className="w-3.5 h-3.5" /> Error
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
      <ClockIcon className="w-3.5 h-3.5" /> {status ?? '—'}
    </span>
  )
}

export default function IntegrityCheck() {
  const { projectId } = useParams<{ projectId: string }>()
  const { currentProject, fetchProject } = useProjectStore()

  const [appUrl, setAppUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [progress, setProgress] = useState<RunStatusResponse | null>(null)
  const [result, setResult] = useState<RunStatusResponse | null>(null)
  const [preview, setPreview] = useState<IntegrityCheckPreview | null>(null)
  const [expandedStories, setExpandedStories] = useState<Set<number>>(new Set())
  const [expandedTcs, setExpandedTcs] = useState<Set<number>>(new Set())
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)

  const [history, setHistory] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadHistory = useCallback(async () => {
    if (!projectId) return
    setHistoryLoading(true)
    try {
      const res = await integrityCheckApi.getHistory(projectId, { limit: 20 })
      setHistory(res.data)
    } catch {
      // silent — history is supplementary
    } finally {
      setHistoryLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (projectId) {
      fetchProject(projectId)
      loadPreview()
      loadHistory()
    }
  }, [projectId, loadHistory])

  useEffect(() => {
    if (currentProject) {
      if (currentProject.app_url) setAppUrl(currentProject.app_url)
      if (currentProject.app_username) setUsername(currentProject.app_username)
      if (currentProject.app_password) setPassword(currentProject.app_password)
    }
  }, [currentProject])

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
          loadHistory()
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
        credentials: username || password ? { username, password } : undefined,
      })
      setActiveRunId(res.data.run_id)
      startPolling(res.data.run_id)
      toast.success('Check started — Chrome browser is opening…')
    } catch (err: unknown) {
      const msg =
        err &&
        typeof err === 'object' &&
        'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(msg || 'Failed to start integrity check')
      setIsRunning(false)
    }
  }

  const handleViewHistoryRun = async (run: HistoryItem) => {
    setLoadingRunId(run.run_id)
    try {
      const res = await integrityCheckApi.getStatus(run.run_id)
      setResult(res.data)
      setActiveRunId(run.run_id)
      // Scroll to results
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch {
      toast.error('Failed to load run results')
    } finally {
      setLoadingRunId(null)
    }
  }

  const toggleStory = (id: number) =>
    setExpandedStories(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleTc = (id: number) =>
    setExpandedTcs(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })

  const resultRunId = result?.run_id ?? activeRunId

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
            <Input label="Username (optional)" value={username}
              onChange={e => setUsername(e.target.value)} placeholder="you@company.com" disabled={isRunning} />
            <Input label="Password (optional)" type="password" value={password}
              onChange={e => setPassword(e.target.value)} placeholder="••••••••" disabled={isRunning} />
          </div>
          <Button onClick={handleRunCheck} isLoading={isRunning} disabled={!appUrl || isRunning}>
            <PlayIcon className="w-4 h-4 mr-2" />
            {isRunning ? 'Check Running…' : 'Run Integrity Check'}
          </Button>
        </div>
      </Card>

      {/* Live progress */}
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

      {isRunning && !progress && (
        <Card>
          <div className="flex flex-col items-center py-8 gap-3 text-gray-500">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm">Opening Chrome browser…</p>
          </div>
        </Card>
      )}

      {/* Current / selected result */}
      {result && !isRunning && (
        <>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {(result.status === 'completed' || result.status === 'error') && projectId && (
              <Button type="button" variant="outline" onClick={() => setEmailDialogOpen(true)}>
                <EnvelopeIcon className="w-4 h-4 mr-2" />
                Email report + screenshots
              </Button>
            )}
          </div>
          <IntegrityCheckResults result={result} />
          <EmailReportDialog
            isOpen={emailDialogOpen}
            onClose={() => setEmailDialogOpen(false)}
            projectId={projectId ?? ''}
            runId={resultRunId ?? ''}
            kind="bic"
            reportLabel="build integrity check report"
          />
        </>
      )}

      {!isRunning && !result && (
        <IntegrityCheckExecutionPreview
          preview={preview}
          expandedStories={expandedStories}
          expandedTcs={expandedTcs}
          onToggleStory={toggleStory}
          onToggleTc={toggleTc}
        />
      )}

      {/* Run history */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Run History</h2>
            <p className="text-sm text-gray-500">Past integrity check runs for this project. Click View to load any result.</p>
          </div>
          <Button variant="outline" size="sm" onClick={loadHistory} disabled={historyLoading}>
            <ArrowPathIcon className={`w-4 h-4 mr-1.5 ${historyLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {historyLoading ? (
          <div className="flex justify-center py-8">
            <ArrowPathIcon className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : history.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">No runs yet. Run your first integrity check above.</p>
        ) : (
          <div className="overflow-x-auto -mx-6 px-6">
            <table className="w-full min-w-[560px]">
              <thead className="bg-gray-50 border-y border-gray-200">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-10">#</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Result</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Steps</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">App URL</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((run, idx) => (
                  <tr
                    key={run.run_id}
                    className={`hover:bg-gray-50/80 transition-colors ${resultRunId === run.run_id ? 'bg-blue-50/40' : ''}`}
                  >
                    <td className="px-4 py-3 text-sm text-gray-500">{idx + 1}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{fmtDate(run.created_at)}</td>
                    <td className="px-4 py-3">
                      <OverallStatusBadge status={run.overall_status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{run.steps_total ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{fmtDuration(run.duration_ms)}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 truncate max-w-[180px]" title={run.app_url}>
                      {run.app_url}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {resultRunId === run.run_id ? (
                        <span className="text-xs text-blue-600 font-medium">Viewing</span>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewHistoryRun(run)}
                          isLoading={loadingRunId === run.run_id}
                          disabled={loadingRunId !== null || isRunning}
                        >
                          <EyeIcon className="w-4 h-4 mr-1" />
                          View
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
