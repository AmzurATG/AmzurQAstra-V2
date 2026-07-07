import { useCallback, useEffect, useRef, useState } from 'react'
import { Card, CardTitle } from '@common/components/ui/Card'
import toast from 'react-hot-toast'

import { testRunsApi } from '../api'
import { isTerminalStatus } from '../live/progressSource'
import type { LiveProgressResponse, LogEntry } from '../types'
import { TestRunCaseAccordion } from './TestRunCaseAccordion'

export interface TestRunDetailViewProps {
  /**
   * Current run snapshot. `null` while the first poll is in flight; the
   * caller decides what to render in that state (we render a skeleton).
   */
  progress: LiveProgressResponse | null
  /**
   * Numeric run id used for screenshot fetches / step sync calls. When
   * progress is null we fall back to this to keep URLs well-formed.
   */
  runId: number
}

/**
 * Presentational view of a single test run (live or completed).
 *
 * Intentionally dumb: no polling, no routing, no header/back button. Owners
 * of this component (TestRunDetail page, Live tab) bring their own data +
 * chrome. Keeps the same UI rendering in both "watching live" and "reviewing
 * history" states so they never visually drift.
 */
/** Scrollable console that auto-scrolls to the newest log entry. */
function LiveLogConsole({ logs }: { logs: LogEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  useEffect(() => {
    if (isAtBottom && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, isAtBottom])

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setIsAtBottom(atBottom)
  }

  const levelColor = (level: string) => {
    if (level === 'error') return 'text-red-400'
    if (level === 'warn' || level === 'warning') return 'text-yellow-400'
    return 'text-green-400'
  }

  const levelPrefix = (level: string) => {
    if (level === 'error') return '✗'
    if (level === 'warn' || level === 'warning') return '⚠'
    return '›'
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="h-52 overflow-y-auto rounded-lg bg-gray-950 p-3 font-mono text-xs leading-5 space-y-0.5"
    >
      {logs.length === 0 ? (
        <p className="text-gray-500 italic">Waiting for agent activity…</p>
      ) : (
        logs.map((log, i) => {
          const ts = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''
          return (
            <div key={i} className="flex gap-2">
              <span className="shrink-0 text-gray-600">{ts}</span>
              <span className={`shrink-0 w-3 ${levelColor(log.level)}`}>
                {levelPrefix(log.level)}
              </span>
              <span className="text-gray-200 break-all">{log.message}</span>
            </div>
          )
        })
      )}
      <div ref={bottomRef} />
    </div>
  )
}

export function TestRunDetailView({ progress, runId }: TestRunDetailViewProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [syncing, setSyncing] = useState<Record<string, boolean>>({})

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
  const passed = progress.completed_results.filter((r) => r.status === 'passed').length
  const failed = progress.completed_results.filter((r) => r.status !== 'passed').length
  const total = progress.total_test_cases

  return (
    <div className="space-y-6">
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

      {/* Live activity log — shown during execution and when logs are present */}
      {(progress.logs.length > 0 || !isDone) && (
        <Card>
          <div className="flex items-center justify-between mb-2">
            <CardTitle>Live Activity</CardTitle>
            {progress.logs.length > 0 && (
              <span className="text-xs text-gray-400">{progress.logs.length} entries</span>
            )}
          </div>
          <LiveLogConsole logs={progress.logs} />
        </Card>
      )}

      <div className="space-y-3">
        <CardTitle>Test Case Results</CardTitle>
        {progress.completed_results.length === 0 && !isDone && (
          <p className="text-sm text-gray-400 py-4">
            Waiting for first test case to complete…
          </p>
        )}
        {progress.completed_results.length > 0 && (
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
                {progress.completed_results.map((r, index) => (
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
