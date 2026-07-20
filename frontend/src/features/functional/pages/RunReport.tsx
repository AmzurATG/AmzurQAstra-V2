import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  EnvelopeIcon,
  SparklesIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { Card } from '@common/components/ui/Card'

import { testRunsApi } from '../api'
import { fetchScreenshotBlobUrl } from '../utils/screenshotFetch'
import type { RunReportCase, RunReportData } from '../types'

function basename(path?: string | null): string {
  if (!path) return ''
  const parts = path.split('/')
  return parts[parts.length - 1] || ''
}

function CaseShot({ runId, c }: { runId: number; c: RunReportCase }) {
  const [url, setUrl] = useState<string | null>(null)
  const filename = basename(c.screenshot_path)
  useEffect(() => {
    if (!filename) return
    let revoked: string | null = null
    let cancelled = false
    fetchScreenshotBlobUrl(runId, c.test_result_id, filename)
      .then((u) => {
        if (cancelled) return URL.revokeObjectURL(u)
        revoked = u
        setUrl(u)
      })
      .catch(() => {})
    return () => {
      cancelled = true
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [runId, c.test_result_id, filename])
  if (!filename) return null
  return url ? (
    <img src={url} alt={c.title} className="mt-2 rounded-lg border border-gray-200 max-h-72 object-contain" />
  ) : (
    <div className="mt-2 h-40 w-full max-w-md animate-pulse rounded-lg bg-gray-100" />
  )
}

function CaseRow({ runId, c }: { runId: number; c: RunReportCase }) {
  const [open, setOpen] = useState(c.status !== 'passed')
  const ok = c.status === 'passed'
  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-2 px-3 py-2.5 text-left ${ok ? 'hover:bg-green-50/50' : 'hover:bg-red-50/50'}`}
      >
        {open ? <ChevronDownIcon className="w-4 h-4 text-gray-400" /> : <ChevronRightIcon className="w-4 h-4 text-gray-400" />}
        {ok ? (
          <CheckCircleIcon className="w-5 h-5 text-green-500 shrink-0" />
        ) : (
          <XCircleIcon className="w-5 h-5 text-red-500 shrink-0" />
        )}
        <span className="font-medium text-sm text-gray-900 flex-1 truncate">{c.title}</span>
        {c.has_adaptations && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold rounded-full uppercase">
            <SparklesIcon className="w-3 h-3" /> AI
          </span>
        )}
        <span className="text-xs text-gray-500 tabular-nums">
          {c.steps_passed}/{c.steps_total} · {c.duration_ms < 1000 ? `${c.duration_ms}ms` : `${(c.duration_ms / 1000).toFixed(1)}s`}
        </span>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1 space-y-2">
          {c.error_message && (
            <p className="text-xs text-red-600">Error: {c.error_message}</p>
          )}
          {c.steps.map((s, i) => (
            <div key={i} className="text-sm">
              <div className="flex items-center gap-2">
                {s.status === 'passed' ? (
                  <CheckCircleIcon className="w-4 h-4 text-green-500 shrink-0" />
                ) : (
                  <XCircleIcon className="w-4 h-4 text-red-500 shrink-0" />
                )}
                <span className="font-semibold text-gray-700">Step {s.step_number}</span>
                <span className="text-gray-500">{s.description}</span>
              </div>
              {s.expected_result && (
                <p className="ml-6 text-xs text-gray-500">Expected: {s.expected_result}</p>
              )}
              {s.actual_result && (
                <p className="ml-6 text-xs text-gray-600">Actual: {s.actual_result}</p>
              )}
              {s.adaptation && (
                <div className="ml-6 mt-1 p-2 bg-purple-50 rounded border border-purple-100 text-xs">
                  <span className="font-bold text-purple-800 inline-flex items-center gap-1">
                    <SparklesIcon className="w-3 h-3" /> AI adaptation:
                  </span>{' '}
                  <span className="text-purple-900">{s.adaptation}</span>
                </div>
              )}
            </div>
          ))}
          <CaseShot runId={runId} c={c} />
        </div>
      )}
    </div>
  )
}

export default function RunReport() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  const navigate = useNavigate()
  const numRunId = Number(runId)
  const [report, setReport] = useState<RunReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [emailing, setEmailing] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!Number.isFinite(numRunId)) return
    setLoading(true)
    testRunsApi
      .getReport(numRunId)
      .then((res) => setReport(res.data))
      .catch(() => toast.error('Could not load report'))
      .finally(() => setLoading(false))
  }, [numRunId])

  const handleDownload = useCallback(async () => {
    setDownloading(true)
    try {
      const res = await testRunsApi.reportPdf(numRunId)
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `test-run-${report?.run_number ?? numRunId}-report.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('PDF download failed')
    } finally {
      setDownloading(false)
    }
  }, [numRunId, report?.run_number])

  const handleEmail = useCallback(async () => {
    const to = window.prompt('Send report to email:')
    if (!to) return
    setEmailing(true)
    try {
      await testRunsApi.emailReport(numRunId, to)
      toast.success('Report emailed')
    } catch (e) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Email failed')
    } finally {
      setEmailing(false)
    }
  }, [numRunId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }
  if (!report) return <div className="py-20 text-center text-gray-500">Report unavailable.</div>

  const t = report.totals
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}/functional-testing/history`)}
            className="text-gray-400 hover:text-gray-600"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Run #{report.run_number ?? report.run_id} — Full Report
            </h1>
            <p className="text-gray-500 text-sm">{report.app_url}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleEmail} isLoading={emailing}>
            <EnvelopeIcon className="w-4 h-4 mr-2" /> Email
          </Button>
          <Button onClick={handleDownload} isLoading={downloading}>
            <ArrowDownTrayIcon className="w-4 h-4 mr-2" /> Download PDF
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: 'Total', value: t.total, cls: 'text-gray-900' },
          { label: 'Passed', value: t.passed, cls: 'text-green-600' },
          { label: 'Failed', value: t.failed, cls: 'text-red-600' },
          { label: 'Success', value: `${t.success_rate}%`, cls: 'text-primary-600' },
          { label: 'AI adaptations', value: t.adaptations, cls: 'text-purple-600' },
        ].map((s) => (
          <Card key={s.label} className="text-center p-4">
            <p className="text-xs text-gray-500 uppercase">{s.label}</p>
            <p className={`text-xl font-bold ${s.cls}`}>{s.value}</p>
          </Card>
        ))}
      </div>

      {report.groups.map((g) => (
        <Card key={g.group_id} className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">{g.title}</h3>
              <p className="text-xs text-gray-500">
                {g.passed}/{g.total} passed
                {g.shared_login && ' · shared-login group (login once)'}
              </p>
            </div>
          </div>
          <div className="space-y-2">
            {g.cases.map((c) => (
              <CaseRow key={c.test_result_id} runId={numRunId} c={c} />
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}
