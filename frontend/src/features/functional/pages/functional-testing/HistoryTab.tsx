import { type ComponentType, useCallback, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowPathIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { Card } from '@common/components/ui/Card'
import { PaginationBar } from '@common/components/ui/PaginationBar'
import { formatDateTimeIST } from '@common/utils/dateTime'
import { formatDisplayLabel } from '@common/utils/formatDisplayLabel'

import { testRunReportsApi } from '../../api'
import { useTestRunsList } from '../../hooks/useTestRunsList'
import type { TestRun } from '../../types'
import EmailReportDialog from '../../components/EmailReportDialog'

type StatusCfg = {
  icon: ComponentType<{ className?: string }>
  color: string
  bg: string
}

const STATUS_CFG: Record<string, StatusCfg> = {
  passed: { icon: CheckCircleIcon, color: 'text-green-500', bg: 'bg-green-50' },
  failed: { icon: XCircleIcon, color: 'text-red-500', bg: 'bg-red-50' },
  running: { icon: ArrowPathIcon, color: 'text-blue-500', bg: 'bg-blue-50' },
  pending: { icon: ClockIcon, color: 'text-gray-500', bg: 'bg-gray-50' },
  cancelled: { icon: XMarkIcon, color: 'text-gray-500', bg: 'bg-gray-50' },
  error: { icon: XCircleIcon, color: 'text-red-500', bg: 'bg-red-50' },
}

const FILTER_VALUES = ['all', 'passed', 'failed', 'running', 'cancelled'] as const

/** Per-run report generation state tracked in memory (keyed by run id). */
type ReportJobState = 'idle' | 'generating' | 'ready' | 'failed'

/**
 * Functional Testing → History tab.
 *
 * Pure read model over past runs. Execution dispatch lives on the Cases tab;
 * live watching is on the Live tab. We just list, filter, and navigate to the
 * run detail page for a given row.
 */
export default function HistoryTab() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const raw = searchParams.get('status_filter') ?? 'all'
  const filter = FILTER_VALUES.includes(raw as (typeof FILTER_VALUES)[number]) ? raw : 'all'

  const setFilter = (f: string) => {
    const next = new URLSearchParams(searchParams)
    if (f === 'all') next.delete('status_filter')
    else next.set('status_filter', f)
    setSearchParams(next, { replace: true })
  }
  const { runs, summary, loading, page, setPage, meta, pageSize, reload } =
    useTestRunsList(projectId, filter)

  // Report generation state
  const [reportJobs, setReportJobs] = useState<Record<number, ReportJobState>>({})
  const [emailRunId, setEmailRunId] = useState<number | null>(null)
  const pollTimers = useRef<Record<number, ReturnType<typeof setInterval>>>({})

  const setJobState = useCallback((runId: number, state: ReportJobState) => {
    setReportJobs((prev) => ({ ...prev, [runId]: state }))
  }, [])

  const startPolling = useCallback(
    (runId: number) => {
      if (pollTimers.current[runId]) return
      pollTimers.current[runId] = setInterval(async () => {
        try {
          const { data } = await testRunReportsApi.getStatus(runId)
          if (data.status === 'ready') {
            clearInterval(pollTimers.current[runId])
            delete pollTimers.current[runId]
            setJobState(runId, 'ready')
            toast.success(`Report for Run #${runId} is ready — click Download.`)
          } else if (data.status === 'failed') {
            clearInterval(pollTimers.current[runId])
            delete pollTimers.current[runId]
            setJobState(runId, 'failed')
            toast.error(`Report generation failed: ${data.error || 'unknown error'}`)
          }
        } catch {
          // network hiccup — keep polling
        }
      }, 3000)
    },
    [setJobState],
  )

  const handleGenerateReport = useCallback(
    async (e: React.MouseEvent, runId: number) => {
      e.stopPropagation()
      setJobState(runId, 'generating')
      try {
        const { data } = await testRunReportsApi.generate(runId)
        if (data.status === 'ready') {
          setJobState(runId, 'ready')
          toast.success('Report is already generated — click Download.')
        } else if (data.status === 'generating') {
          startPolling(runId)
        } else {
          setJobState(runId, 'failed')
          toast.error(data.message || 'Failed to start report generation.')
        }
      } catch {
        setJobState(runId, 'failed')
        toast.error('Failed to start report generation.')
      }
    },
    [setJobState, startPolling],
  )

  const handleDownload = useCallback(async (e: React.MouseEvent, runId: number) => {
    e.stopPropagation()
    try {
      const { data } = await testRunReportsApi.download(runId)
      const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `QAstra_TestRun_${runId}_Report.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Download failed. Try regenerating the report.')
    }
  }, [])

  const handleEmailClick = useCallback((e: React.MouseEvent, runId: number) => {
    e.stopPropagation()
    setEmailRunId(runId)
  }, [])

  const base = `/projects/${projectId}/functional-testing`

  const stats = summary
    ? {
        total: summary.total,
        passed: summary.passed,
        failed: summary.failed,
        avgPassRate: summary.avg_pass_rate,
      }
    : { total: 0, passed: 0, failed: 0, avgPassRate: 0 }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Run History</h2>
          <p className="text-sm text-gray-500">
            Past executions and their reports. Click a row to open full details.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => reload()}>
            <ArrowPathIcon className="w-4 h-4 mr-1" /> Refresh
          </Button>
          <Button onClick={() => navigate(`${base}/cases`)}>Run New Tests</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 flex items-center gap-4">
          <div className="p-2 bg-blue-50 rounded-lg">
            <ChartBarIcon className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Total Runs</p>
            <p className="text-xl font-bold">{stats.total}</p>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4">
          <div className="p-2 bg-green-50 rounded-lg">
            <CheckCircleIcon className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Passed</p>
            <p className="text-xl font-bold text-green-600">{stats.passed}</p>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4">
          <div className="p-2 bg-red-50 rounded-lg">
            <XCircleIcon className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Failed / Error</p>
            <p className="text-xl font-bold text-red-600">{stats.failed}</p>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4">
          <div className="p-2 bg-primary-50 rounded-lg">
            <div className="w-6 h-6 flex items-center justify-center font-bold text-primary-600 text-sm">
              {stats.avgPassRate}%
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Avg Pass Rate</p>
            <p className="text-xl font-bold text-primary-600">
              {stats.avgPassRate}%
            </p>
          </div>
        </Card>
      </div>

      <div className="flex gap-2 flex-wrap">
        {['all', 'passed', 'failed', 'running', 'cancelled'].map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filter === f
                ? 'bg-primary-600 text-white'
                : 'bg-white text-gray-600 border hover:bg-gray-50'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <Card padding="none">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-300" />
          </div>
        ) : runs.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            No test runs found matching the filter.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b text-xs font-semibold text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 w-14 text-center">#</th>
                    <th className="px-4 py-3 w-24">Run #</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Run Name</th>
                    <th className="px-6 py-3 text-center">Results</th>
                    <th className="px-6 py-3">Started</th>
                    <th className="px-6 py-3 text-center">Report</th>
                    <th className="px-6 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {runs.map((run: TestRun, index: number) => {
                    const cfg = STATUS_CFG[run.status] || STATUS_CFG.pending
                    const Icon = cfg.icon
                    const rowNum = (page - 1) * pageSize + index + 1
                    const isDone = ['passed', 'failed', 'error', 'cancelled'].includes(run.status)
                    const jobState: ReportJobState = reportJobs[run.id] ?? 'idle'

                    return (
                      <tr
                        key={run.id}
                        className="hover:bg-gray-50 cursor-pointer group"
                        onClick={() => navigate(`${base}/history/${run.id}`)}
                      >
                        <td className="px-4 py-4 text-center text-sm font-medium text-gray-500 tabular-nums">
                          {rowNum}
                        </td>
                        <td className="px-4 py-4">
                          <span className="inline-flex items-center justify-center min-w-[2.5rem] px-2 py-1 rounded-md bg-gray-100 text-sm font-bold text-gray-900 tabular-nums">
                            #{run.run_number ?? run.id}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full ${cfg.bg}`}
                          >
                            <Icon
                              className={`w-3 h-3 ${cfg.color} ${
                                run.status === 'running' ? 'animate-spin' : ''
                              }`}
                            />
                            <span
                              className={`text-[10px] font-bold uppercase ${cfg.color}`}
                            >
                              {formatDisplayLabel(run.status)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p className="text-sm font-medium text-gray-900">
                            {run.name}
                          </p>
                          <p className="text-xs text-gray-500 capitalize">
                            {run.browser}
                          </p>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center gap-3">
                            <span className="text-xs text-green-600 font-semibold">
                              {run.passed_tests}✓
                            </span>
                            <span className="text-xs text-red-600 font-semibold">
                              {run.failed_tests}✗
                            </span>
                            <span className="text-xs text-gray-400">
                              {run.total_tests} total
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-xs text-gray-500">
                          {run.started_at ? formatDateTimeIST(run.started_at) : '-'}
                        </td>

                        {/* Report actions column */}
                        <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                          {!isDone ? (
                            <span className="text-xs text-gray-400">Run in progress</span>
                          ) : jobState === 'idle' ? (
                            <button
                              type="button"
                              onClick={(e) => handleGenerateReport(e, run.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
                            >
                              <DocumentTextIcon className="w-3.5 h-3.5" />
                              Generate Report
                            </button>
                          ) : jobState === 'generating' ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs text-blue-600 font-medium">
                              <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                              Generating…
                            </span>
                          ) : jobState === 'ready' ? (
                            <div className="flex items-center gap-1.5">
                              <button
                                type="button"
                                onClick={(e) => handleDownload(e, run.id)}
                                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 transition-colors"
                              >
                                <DocumentArrowDownIcon className="w-3.5 h-3.5" />
                                Download
                              </button>
                              <button
                                type="button"
                                onClick={(e) => handleEmailClick(e, run.id)}
                                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-gray-50 text-gray-600 hover:bg-gray-100 transition-colors"
                              >
                                <EnvelopeIcon className="w-3.5 h-3.5" />
                                Email
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => handleGenerateReport(e, run.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                            >
                              Retry Report
                            </button>
                          )}
                        </td>

                        <td className="px-6 py-4 text-right">
                          <ChevronRightIcon className="w-4 h-4 text-gray-300 group-hover:text-primary-500 transition-colors" />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <PaginationBar
              page={page}
              totalPages={meta.total_pages}
              hasPrev={meta.has_prev}
              hasNext={meta.has_next}
              onPageChange={setPage}
            />
          </>
        )}
      </Card>

      <EmailReportDialog
        isOpen={emailRunId !== null}
        onClose={() => setEmailRunId(null)}
        projectId={projectId ?? ''}
        runId={emailRunId}
        kind="testRun"
        reportLabel="Test Run Report"
      />
    </div>
  )
}
