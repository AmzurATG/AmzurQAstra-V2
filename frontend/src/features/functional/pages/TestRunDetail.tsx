import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import {
  ArrowPathIcon,
  StopIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline'
import { testRunsApi } from '../api'
import type { LiveProgressResponse } from '../types'
import toast from 'react-hot-toast'
import { TestRunCaseAccordion } from '../components/TestRunCaseAccordion'

const POLL_MS = 3000
const TERMINAL_STATES = ['completed', 'passed', 'failed', 'error', 'cancelled', 'not_found']

export default function TestRunDetail() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  const navigate = useNavigate()
  const [progress, setProgress] = useState<LiveProgressResponse | null>(null)
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [syncing, setSyncing] = useState<Record<string, boolean>>({})
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const numRunId = Number(runId)
  const isDone = progress ? TERMINAL_STATES.includes(progress.status) : false

  const poll = useCallback(async () => {
    try {
      const res = await testRunsApi.getLiveProgress(numRunId, { lite: true })
      setProgress(res.data)
      if (TERMINAL_STATES.includes(res.data.status) && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {
      /* retry next tick */
    }
  }, [numRunId])

  useEffect(() => {
    poll()
    if (!isDone) {
      pollRef.current = setInterval(poll, POLL_MS)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [poll, isDone])

  const handleCancel = async () => {
    try {
      await testRunsApi.cancel(numRunId)
      poll()
    } catch {
      /* ignore */
    }
  }

  const handleSyncStep = async (resultId: number, stepNumber: number, tcId: number) => {
    const key = `${resultId}-${stepNumber}`
    setSyncing((prev) => ({ ...prev, [key]: true }))
    try {
      await testRunsApi.syncStep(resultId, stepNumber)
      toast.success(`Step ${stepNumber} synced to Test Case #${tcId}`)
    } catch {
      toast.error('Failed to sync step')
    } finally {
      setSyncing((prev) => ({ ...prev, [key]: false }))
    }
  }

  if (!progress) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const pct = progress.percentage
  const passed = progress.completed_results.filter((r) => r.status === 'passed').length
  const failed = progress.completed_results.filter((r) => r.status !== 'passed').length
  const total = progress.total_test_cases

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}/test-runs`)}
            className="text-gray-400 hover:text-gray-600"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Test Run #{runId}</h1>
            <p className="text-gray-500 text-sm">
              {isDone
                ? `Completed — ${passed} passed, ${failed} failed`
                : progress.current_test_case_title || 'Starting…'}
            </p>
            <p className="text-gray-400 text-xs font-mono mt-0.5">
              Run ID {numRunId}
              {projectId ? ` · Project ${projectId}` : ''}
            </p>
          </div>
        </div>
        {!isDone && (
          <Button variant="outline" className="text-red-600 border-red-200" onClick={handleCancel}>
            <StopIcon className="w-4 h-4 mr-1" /> Cancel
          </Button>
        )}
      </div>

      <Card>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {isDone
              ? 'Execution Summary'
              : `Running test case ${progress.current_test_case_index + 1} of ${total}`}
          </span>
          <span className="text-sm font-semibold text-primary-600">{pct}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${isDone && failed > 0 ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-primary-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </Card>

      <div className="grid grid-cols-4 gap-4">
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Total</p>
          <p className="text-xl font-bold">{total}</p>
        </Card>
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Passed</p>
          <p className="text-xl font-bold text-green-600">{passed}</p>
        </Card>
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Failed</p>
          <p className="text-xl font-bold text-red-600">{failed}</p>
        </Card>
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Success Rate</p>
          <p className="text-xl font-bold text-primary-600">
            {total ? Math.round((passed / total) * 100) : 0}%
          </p>
        </Card>
      </div>

      <div className="space-y-3">
        <CardTitle>Test Case Results</CardTitle>
        {progress.completed_results.length === 0 && !isDone && (
          <p className="text-sm text-gray-400 py-4">Waiting for first test case to complete…</p>
        )}
        {progress.completed_results.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-left min-w-[56rem]">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-3 py-3 w-12 text-center">#</th>
                  <th className="px-3 py-3 whitespace-nowrap">Run ID</th>
                  <th className="px-3 py-3 whitespace-nowrap">Case #</th>
                  <th className="px-3 py-3 whitespace-nowrap">Result #</th>
                  <th className="px-3 py-3 w-14">Status</th>
                  <th className="px-3 py-3">Title</th>
                  <th className="px-3 py-3 whitespace-nowrap">Steps</th>
                  <th className="px-3 py-3 whitespace-nowrap">Duration</th>
                  <th className="px-3 py-3 w-10" aria-label="Expand" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {progress.completed_results.map((r, index) => (
                  <TestRunCaseAccordion
                    key={r.test_result_id}
                    runId={numRunId}
                    result={r}
                    rowNumber={index + 1}
                    isExpanded={!!expanded[r.test_result_id]}
                    onToggle={() =>
                      setExpanded((prev) => ({
                        ...prev,
                        [r.test_result_id]: !prev[r.test_result_id],
                      }))
                    }
                    onSync={handleSyncStep}
                    syncing={syncing}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
