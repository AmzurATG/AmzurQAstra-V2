import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  DocumentArrowDownIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  StopIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { useProjectStore } from '@common/store/projectStore'

import { testRunsApi, testRunReportsApi } from '../api'
import { TestRunDetailView } from '../components/TestRunDetailView'
import EmailReportDialog from '../components/EmailReportDialog'
import { useActiveTestRun } from '../context/ActiveTestRunProvider'
import { isTerminalStatus, pollingProgressSource } from '../live/progressSource'
import type { LiveProgressResponse } from '../types'
import { displayRunStatus } from '../utils/runStatusDisplay'

type ReportJobState = 'idle' | 'generating' | 'ready' | 'failed'

/**
 * Full-page run detail. Two modes:
 *
 * 1. The Functional Testing shell is a parent → we read the live snapshot
 *    from the active-run context when the URL's runId matches. No duplicate
 *    poller.
 * 2. Direct deep-link (e.g. someone shared `/history/:runId`) → we subscribe
 *    our own ProgressSource so the page renders even without the shell.
 */
export default function TestRunDetail() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  const navigate = useNavigate()
  const currentProject = useProjectStore((s) => s.currentProject)
  const activeRun = useActiveTestRun()

  const numRunId = Number(runId)
  const projectDisplayName =
    projectId && currentProject?.id === Number(projectId) ? currentProject.name : null

  const useContextSnapshot =
    activeRun && activeRun.activeRunId === numRunId && activeRun.progress

  const [localProgress, setLocalProgress] = useState<LiveProgressResponse | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  // Report generation
  const [reportJob, setReportJob] = useState<ReportJobState>('idle')
  const [emailOpen, setEmailOpen] = useState(false)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startReportPolling = useCallback(() => {
    if (pollTimerRef.current) return
    pollTimerRef.current = setInterval(async () => {
      try {
        const { data } = await testRunReportsApi.getStatus(numRunId)
        if (data.status === 'ready') {
          clearInterval(pollTimerRef.current!)
          pollTimerRef.current = null
          setReportJob('ready')
          toast.success('Report is ready — click Download PDF.')
        } else if (data.status === 'failed') {
          clearInterval(pollTimerRef.current!)
          pollTimerRef.current = null
          setReportJob('failed')
          toast.error(`Report generation failed: ${data.error || 'unknown error'}`)
        }
      } catch { /* network hiccup */ }
    }, 3000)
  }, [numRunId])

  const handleGenerateReport = useCallback(
    async (format: 'short' | 'long' = 'short') => {
      setReportJob('generating')
      try {
        const { data } = await testRunReportsApi.generate(numRunId, true, format)
        if (data.status === 'ready') {
          setReportJob('ready')
          toast.success(`${format === 'short' ? 'Short' : 'Long'} report ready — download below.`)
        } else if (data.status === 'generating') {
          startReportPolling()
          toast.success(`Generating ${format} report…`)
        } else {
          setReportJob('failed')
          toast.error(data.message || 'Failed to start report generation.')
        }
      } catch {
        setReportJob('failed')
        toast.error('Failed to start report generation.')
      }
    },
    [numRunId, startReportPolling],
  )

  const handleDownloadReport = useCallback(
    async (format: 'short' | 'long' = 'short') => {
      try {
        const { data } = await testRunReportsApi.download(numRunId, format)
        const url = URL.createObjectURL(
          new Blob([data as unknown as BlobPart], { type: 'application/pdf' }),
        )
        const a = document.createElement('a')
        a.href = url
        a.download = `QAstra_TestRun_${numRunId}_${format}_Report.pdf`
        a.click()
        URL.revokeObjectURL(url)
      } catch {
        toast.error('Download failed. Try regenerating the report.')
      }
    },
    [numRunId],
  )

  // Check if report already exists on mount (for revisited completed runs)
  useEffect(() => {
    if (!Number.isFinite(numRunId)) return
    testRunReportsApi.getStatus(numRunId).then(({ data }) => {
      if (data.status === 'ready') setReportJob('ready')
    }).catch(() => {/* ignore */})
  }, [numRunId])

  useEffect(() => {
    if (!Number.isFinite(numRunId) || useContextSnapshot) {
      return
    }
    unsubscribeRef.current?.()
    unsubscribeRef.current = pollingProgressSource.subscribe(numRunId, (snapshot) => {
      setLocalProgress(snapshot)
    })
    return () => {
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
    }
  }, [numRunId, useContextSnapshot])

  const progress = useContextSnapshot ? activeRun.progress : localProgress
  const isDone = progress ? isTerminalStatus(progress.status) : false

  const handleCancel = useCallback(async () => {
    if (activeRun && activeRun.activeRunId === numRunId) {
      await activeRun.cancelRun()
      return
    }
    try {
      await testRunsApi.cancel(numRunId)
    } catch {
      /* ignore */
    }
  }, [activeRun, numRunId])

  if (!progress) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const passed = progress.completed_results.filter((r) => r.status === 'passed').length
  const failed = progress.completed_results.filter((r) => r.status !== 'passed').length
  const display = displayRunStatus(progress.status, {
    passed,
    failed,
    total: progress.total_tests || passed + failed,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() =>
              navigate(`/projects/${projectId}/functional-testing/history`)
            }
            className="text-gray-400 hover:text-gray-600"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Test Run #{progress.run_number ?? runId}
            </h1>
            <p className="text-gray-500 text-sm">
              {isDone
                ? `${display.label} — ${passed} passed, ${failed} failed (${display.passRate}%)`
                : progress.current_test_case_title || 'Starting…'}
            </p>
            <p className="text-gray-400 text-xs mt-0.5">
              <span className="font-mono">Internal ref {numRunId}</span>
              {projectId && (
                <span className="text-gray-500">
                  {' '}
                  · {projectDisplayName ?? `Project #${projectId}`}
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {isDone && reportJob === 'generating' && (
            <Button variant="outline" size="sm" disabled>
              <ArrowPathIcon className="w-4 h-4 mr-1 animate-spin" />
              Generating…
            </Button>
          )}
          {isDone && reportJob !== 'generating' && (
            <>
              <Button variant="outline" size="sm" onClick={() => handleGenerateReport('short')}>
                <DocumentTextIcon className="w-4 h-4 mr-1" />
                Short PDF
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleGenerateReport('long')}>
                Long PDF
              </Button>
            </>
          )}
          {isDone && reportJob === 'ready' && (
            <>
              <Button variant="outline" size="sm" onClick={() => handleDownloadReport('short')}>
                <DocumentArrowDownIcon className="w-4 h-4 mr-1" />
                DL short
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleDownloadReport('long')}>
                DL long
              </Button>
              <Button variant="outline" size="sm" onClick={() => setEmailOpen(true)}>
                <EnvelopeIcon className="w-4 h-4 mr-1" />
                Email
              </Button>
            </>
          )}
          {!isDone && (
            <Button
              variant="outline"
              className="text-red-600 border-red-200"
              onClick={handleCancel}
            >
              <StopIcon className="w-4 h-4 mr-1" /> Cancel
            </Button>
          )}
        </div>
      </div>

      <TestRunDetailView progress={progress} runId={numRunId} />

      <EmailReportDialog
        isOpen={emailOpen}
        onClose={() => setEmailOpen(false)}
        projectId={projectId ?? ''}
        runId={numRunId}
        kind="testRun"
        reportLabel="Test Run Report"
      />
    </div>
  )
}
