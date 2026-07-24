import { useCallback, useEffect, useMemo, useState } from 'react'
import { Card, CardTitle } from '@common/components/ui/Card'
import toast from 'react-hot-toast'

import { testRunsApi } from '../api'
import { isTerminalStatus } from '../live/progressSource'
import type { CompletedCaseResult, LiveProgressResponse } from '../types'
import { TestRunCaseAccordion } from './TestRunCaseAccordion'
import { LogToJiraModal } from './LogToJiraModal'
import { formatDurationMs } from '../utils/formatDurationMs'

type ResultTab = 'all' | 'passed' | 'failed' | 'blocked'

function isBlocked(r: CompletedCaseResult): boolean {
  if (r.infra_error || r.status === 'error') return true
  const ai = r.ai_modified as Record<string, unknown> | null | undefined
  return Boolean(ai?.infra_error)
}

function isFailedApp(r: CompletedCaseResult): boolean {
  return r.status === 'failed' && !isBlocked(r)
}

export interface TestRunDetailViewProps {
  progress: LiveProgressResponse | null
  runId: number
  /** QAstra project id — required for Log to Jira */
  projectId?: number
}

export function TestRunDetailView({ progress, runId, projectId }: TestRunDetailViewProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [syncing, setSyncing] = useState<Record<string, boolean>>({})
  const [tab, setTab] = useState<ResultTab>('all')
  const [autoTabbed, setAutoTabbed] = useState(false)
  const [jiraTarget, setJiraTarget] = useState<CompletedCaseResult | null>(null)
  const [jiraOverrides, setJiraOverrides] = useState<
    Record<number, { jira_bug_key: string; jira_bug_url?: string | null }>
  >({})

  const handleSyncStep = useCallback(
    async (resultId: number, stepNumber: number, tcId: number) => {
      const key = `${resultId}-${stepNumber}`
      setSyncing((prev) => ({ ...prev, [key]: true }))
      try {
        await testRunsApi.syncStep(resultId, stepNumber)
        toast.success(`Step ${stepNumber} synced to Test Case #${tcId}`)
      } catch (error: unknown) {
        const message =
          error && typeof error === 'object' && 'response' in error
            ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined
        toast.error(message || 'Failed to sync step')
      } finally {
        setSyncing((prev) => ({ ...prev, [key]: false }))
      }
    },
    []
  )

  const resultsWithOverrides = useMemo(() => {
    if (!progress) return []
    return progress.completed_results.map((r) => {
      const o = jiraOverrides[r.test_result_id]
      if (!o) return r
      return { ...r, jira_bug_key: o.jira_bug_key, jira_bug_url: o.jira_bug_url }
    })
  }, [progress, jiraOverrides])

  const counts = useMemo(() => {
    const all = resultsWithOverrides
    const passed = all.filter((r) => r.status === 'passed').length
    const failed = all.filter(isFailedApp).length
    const blocked = all.filter(isBlocked).length
    return { all: all.length, passed, failed, blocked }
  }, [resultsWithOverrides])

  useEffect(() => {
    if (autoTabbed || !progress) return
    if (counts.failed > 0) {
      setTab('failed')
      setAutoTabbed(true)
    }
  }, [progress, counts.failed, autoTabbed])

  useEffect(() => {
    setAutoTabbed(false)
    setTab('all')
    setJiraOverrides({})
  }, [progress?.run_id])

  const filtered = useMemo(() => {
    switch (tab) {
      case 'passed':
        return resultsWithOverrides.filter((r) => r.status === 'passed')
      case 'failed':
        return resultsWithOverrides.filter(isFailedApp)
      case 'blocked':
        return resultsWithOverrides.filter(isBlocked)
      default:
        return resultsWithOverrides
    }
  }, [resultsWithOverrides, tab])

  if (!progress) {
    return (
      <Card>
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-1/3 rounded bg-gray-200" />
          <div className="h-3 w-full rounded bg-gray-200" />
          <div className="h-3 w-5/6 rounded bg-gray-200" />
        </div>
      </Card>
    )
  }

  const isDone = isTerminalStatus(progress.status)
  const pct = progress.percentage
  const passed = counts.passed
  const failed = counts.failed
  const total = progress.total_test_cases

  const tabs: { id: ResultTab; label: string; count: number }[] = [
    { id: 'all', label: 'All', count: counts.all },
    { id: 'passed', label: 'Passed', count: counts.passed },
    { id: 'failed', label: 'Failed', count: counts.failed },
    { id: 'blocked', label: 'Blocked', count: counts.blocked },
  ]

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {isDone
              ? 'Execution Summary'
              : `Running test case ${progress.current_test_case_index + 1} of ${total}`}
          </span>
          <div className="flex items-center gap-3">
            {(progress.elapsed_display || progress.elapsed_ms != null) && (
              <span className="text-xs text-gray-500 tabular-nums">
                {progress.elapsed_display || formatDurationMs(progress.elapsed_ms)}
              </span>
            )}
            <span className="text-sm font-semibold text-primary-600">{pct}%</span>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              isDone && failed > 0
                ? 'bg-red-500'
                : isDone
                  ? 'bg-green-500'
                  : 'bg-primary-500'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {!isDone && progress.current_test_case_title && (
          <p className="mt-3 text-sm text-gray-600">
            <span className="font-medium">{progress.current_test_case_title}</span>
            {progress.current_step_info && (
              <span className="text-gray-500"> — {progress.current_step_info}</span>
            )}
          </p>
        )}
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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>Test Case Results</CardTitle>
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-0.5 text-xs font-medium">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`rounded-md px-3 py-1.5 transition-colors ${
                  tab === t.id
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                {t.label}
                <span className="ml-1.5 tabular-nums opacity-80">{t.count}</span>
              </button>
            ))}
          </div>
        </div>

        {progress.completed_results.length === 0 && !isDone && (
          <p className="text-sm text-gray-400 py-4">
            Waiting for first test case to complete…
          </p>
        )}
        {filtered.length === 0 && progress.completed_results.length > 0 && (
          <p className="text-sm text-gray-400 py-4">No cases in this tab.</p>
        )}
        {filtered.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-left min-w-[56rem]">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-3 py-3 w-12 text-center">#</th>
                  <th className="px-3 py-3 whitespace-nowrap">Run #</th>
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
                {filtered.map((r, index) => (
                  <TestRunCaseAccordion
                    key={r.test_result_id}
                    runId={runId}
                    runNumber={progress.run_number}
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
                    onLogToJira={
                      projectId
                        ? () => setJiraTarget(r)
                        : undefined
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {projectId && jiraTarget && (
        <LogToJiraModal
          isOpen={!!jiraTarget}
          onClose={() => setJiraTarget(null)}
          projectId={projectId}
          runId={runId}
          runNumber={progress.run_number}
          result={jiraTarget}
          onLogged={({ key, url }) => {
            setJiraOverrides((prev) => ({
              ...prev,
              [jiraTarget.test_result_id]: { jira_bug_key: key, jira_bug_url: url },
            }))
          }}
        />
      )}
    </div>
  )
}
