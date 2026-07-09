import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardTitle } from '@common/components/ui/Card'
import toast from 'react-hot-toast'

import { testRunsApi } from '../api'
import { isTerminalStatus } from '../live/progressSource'
import type { CompletedCaseResult, LiveProgressResponse, LogEntry } from '../types'
import { displayRunStatus } from '../utils/runStatusDisplay'
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

type ResultFilter = 'all' | 'failed' | 'passed'

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

function formatEta(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '—'
  if (seconds < 60) return `~${Math.max(1, Math.round(seconds))}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  if (m < 60) return `~${m}m ${s}s`
  const h = Math.floor(m / 60)
  return `~${h}h ${m % 60}m`
}

/**
 * Presentational view of a single test run (live or completed).
 *
 * Intentionally dumb: no polling, no routing, no header/back button. Owners
 * of this component (TestRunDetail page, Live tab) bring their own data +
 * chrome. Keeps the same UI rendering in both "watching live" and "reviewing
 * history" states so they never visually drift.
 */
export function TestRunDetailView({ progress, runId }: TestRunDetailViewProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [syncing, setSyncing] = useState<Record<string, boolean>>({})
  const [filter, setFilter] = useState<ResultFilter>('all')
  const startedAtRef = useRef<number | null>(null)

  useEffect(() => {
    if (!progress) return
    if (startedAtRef.current == null && !isTerminalStatus(progress.status)) {
      startedAtRef.current = Date.now()
    }
  }, [progress])

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

  const stats = useMemo(() => {
    if (!progress) {
      return {
        passed: 0,
        failed: 0,
        done: 0,
        total: 0,
        remaining: 0,
        ratePerMin: null as number | null,
        etaSec: null as number | null,
        inferred: 0,
        lanes: 0,
      }
    }
    const results = progress.completed_results
    const passed = results.filter((r) => r.status === 'passed').length
    const failed = results.filter((r) => r.status !== 'passed').length
    const done = results.length
    const total = progress.total_test_cases
    const remaining = Math.max(0, total - done)
    const elapsedMs = startedAtRef.current ? Date.now() - startedAtRef.current : 0
    const ratePerMin =
      done > 0 && elapsedMs > 5_000 ? done / (elapsedMs / 60_000) : null
    const etaSec =
      ratePerMin && ratePerMin > 0 && remaining > 0
        ? (remaining / ratePerMin) * 60
        : null
    const inferred = results.filter((r) => r.has_inferred_verdicts).length
    const lanes = progress.execution_plan?.parallelism ?? 0
    return { passed, failed, done, total, remaining, ratePerMin, etaSec, inferred, lanes }
  }, [progress])

  const filteredResults = useMemo(() => {
    if (!progress) return [] as CompletedCaseResult[]
    const list = progress.completed_results
    if (filter === 'failed') return list.filter((r) => r.status !== 'passed')
    if (filter === 'passed') return list.filter((r) => r.status === 'passed')
    return list
  }, [progress, filter])

  // For large runs, prefer the Failed filter once failures appear (demo triage).
  const autoFailedRef = useRef(false)
  useEffect(() => {
    if (!progress || autoFailedRef.current) return
    if (stats.failed > 0 && stats.total >= 20) {
      setFilter('failed')
      autoFailedRef.current = true
    }
  }, [progress, stats.failed, stats.total])

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
  const { passed, failed, total, ratePerMin, etaSec, inferred, lanes, remaining } = stats
  const passRate = total ? Math.round((passed / total) * 100) : 0
  const runDisplay = displayRunStatus(progress.status, { passed, failed, total })
  // Progress fill: green when healthy, amber when mixed, red only when mostly failing.
  const barColor = !isDone
    ? 'bg-primary-500'
    : failed === 0
      ? 'bg-green-500'
      : passRate >= 80
        ? 'bg-green-500'
        : passRate >= 50
          ? 'bg-amber-500'
          : 'bg-red-500'
  const planNote =
    total < 6
      ? 'Small run — cases execute directly (no AI grouping delay).'
      : lanes
        ? `Grouped parallel · ${lanes} browser lane${lanes === 1 ? '' : 's'}`
        : progress.execution_plan
          ? 'Grouped parallel execution'
          : null

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between mb-2 gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-700">
              {isDone
                ? 'Execution Summary'
                : `Running ${progress.current_test_case_index} of ${total} completed`}
            </span>
            {isDone && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  runDisplay.tone === 'success'
                    ? 'bg-green-50 text-green-700'
                    : runDisplay.tone === 'danger'
                      ? 'bg-red-50 text-red-700'
                      : 'bg-gray-50 text-gray-600'
                }`}
              >
                {runDisplay.label}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            {!isDone && ratePerMin != null && (
              <span className="text-gray-500 tabular-nums">
                {ratePerMin.toFixed(1)} cases/min · ETA {formatEta(etaSec)}
              </span>
            )}
            <span className="font-semibold text-primary-600">{pct}%</span>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          {isDone && failed > 0 && passed > 0 ? (
            <div className="flex h-3 w-full">
              <div
                className="h-3 bg-green-500 transition-all duration-500"
                style={{ width: `${passRate}%` }}
                title={`${passed} passed`}
              />
              <div
                className="h-3 bg-red-500 transition-all duration-500"
                style={{ width: `${100 - passRate}%` }}
                title={`${failed} failed`}
              />
            </div>
          ) : (
            <div
              className={`h-3 rounded-full transition-all duration-500 ${barColor}`}
              style={{ width: `${pct}%` }}
            />
          )}
        </div>
        {isDone && (
          <p className="mt-2 text-xs text-gray-500">
            {passed} passed · {failed} failed · {passRate}% success
            {failed > 0 && passRate >= 80
              ? ' — mostly successful; review failures below.'
              : ''}
          </p>
        )}
        {!isDone && progress.current_test_case_title && (
          <p className="mt-3 text-sm text-gray-600">
            <span className="font-medium">{progress.current_test_case_title}</span>
            {progress.current_step_info && (
              <span className="text-gray-500"> — {progress.current_step_info}</span>
            )}
          </p>
        )}
        {planNote && (
          <p className="mt-2 text-xs text-gray-400">{planNote}</p>
        )}
      </Card>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="text-center p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Total</p>
          <p className="text-xl font-bold tabular-nums">{total}</p>
        </Card>
        <Card className="text-center p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Passed</p>
          <p className="text-xl font-bold text-green-600 tabular-nums">{passed}</p>
        </Card>
        <Card className="text-center p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Failed</p>
          <p className="text-xl font-bold text-red-600 tabular-nums">{failed}</p>
        </Card>
        <Card className="text-center p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Remaining</p>
          <p className="text-xl font-bold text-gray-700 tabular-nums">
            {isDone ? 0 : remaining}
          </p>
        </Card>
        <Card className="text-center p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Success</p>
          <p className="text-xl font-bold text-primary-600 tabular-nums">
            {total ? Math.round((passed / total) * 100) : 0}%
          </p>
        </Card>
        <Card className="text-center p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Inferred</p>
          <p
            className="text-xl font-bold text-amber-600 tabular-nums"
            title="Cases with at least one step lacking an explicit STEP_VERDICT"
          >
            {inferred}
          </p>
        </Card>
      </div>

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
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <CardTitle>Test Case Results</CardTitle>
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-0.5 text-xs font-medium">
            {(
              [
                ['all', `All (${progress.completed_results.length})`],
                ['failed', `Failed (${failed})`],
                ['passed', `Passed (${passed})`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  filter === key
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {progress.completed_results.length === 0 && !isDone && (
          <p className="text-sm text-gray-400 py-4">
            Waiting for first test case to complete…
          </p>
        )}
        {filteredResults.length === 0 && progress.completed_results.length > 0 && (
          <p className="text-sm text-gray-400 py-4">No cases match this filter.</p>
        )}
        {filteredResults.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm max-h-[70vh] overflow-y-auto">
            <table className="w-full text-left min-w-[56rem]">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide sticky top-0 z-10">
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
                {filteredResults.map((r, index) => (
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
