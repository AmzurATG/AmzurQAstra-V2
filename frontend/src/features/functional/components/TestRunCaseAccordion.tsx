import React, { useEffect, useState } from 'react'
import { Button } from '@common/components/ui/Button'
import {
  CheckCircleIcon,
  XCircleIcon,
  MinusCircleIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  SparklesIcon,
  PhotoIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import type { CompletedCaseResult, TestResult, TestStepResult } from '../types'
import { AgentStepsStrip } from './AgentStepsStrip'
import { testRunsApi } from '../api'
import { formatStepDisplayValue } from '../utils/formatStepDisplayValue'
import { formatDurationMs } from '../utils/formatDurationMs'

const DETAIL_COL_SPAN = 9

function screenshotEvidenceCount(r: CompletedCaseResult): number {
  const fromAi = (r.ai_modified as Record<string, unknown> | null | undefined)
    ?.evidence_screenshot_count
  if (typeof fromAi === 'number' && fromAi > 0) return fromAi
  const n =
    r.agent_screenshot_count ??
    (r.agent_logs ?? []).filter((l) => l.screenshot_path && l.evidence !== false).length
  if (n > 0) return Math.min(n, 8)
  return r.screenshot_path ? 1 : 0
}

function isInfraCase(r: CompletedCaseResult): boolean {
  if (r.infra_error) return true
  if (r.status === 'error') return true
  const ai = r.ai_modified as Record<string, unknown> | null | undefined
  return Boolean(ai?.infra_error)
}

function isSharedSetupStep(s: TestStepResult): boolean {
  if (s.shared_setup) return true
  const actual = String(s.actual_result || '')
  return (
    actual.startsWith('Already signed in') ||
    actual === 'Shared group setup'
  )
}

function isInfraStep(s: TestStepResult): boolean {
  return Boolean((s as { infra_blocked?: boolean }).infra_blocked) || s.status === 'error'
}

function StepStatusIcon({ step }: { step: TestStepResult }) {
  if (isSharedSetupStep(step) || step.status === 'skipped') {
    return (
      <MinusCircleIcon
        className="w-4 h-4 text-slate-400 mt-0.5 shrink-0"
        title="Completed via existing session"
      />
    )
  }
  if (isInfraStep(step)) {
    return (
      <ExclamationTriangleIcon
        className="w-4 h-4 text-amber-500 mt-0.5 shrink-0"
        title="Not executed — infrastructure"
      />
    )
  }
  if (step.status === 'passed') {
    return <CheckCircleIcon className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
  }
  return <XCircleIcon className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
}

function CaseStatusIcon({ result }: { result: CompletedCaseResult }) {
  if (isInfraCase(result)) {
    return (
      <ExclamationTriangleIcon
        className="w-5 h-5 text-amber-500"
        title="Blocked — not an app failure"
      />
    )
  }
  if (result.status === 'passed') {
    return <CheckCircleIcon className="w-5 h-5 text-green-500" title="Passed" />
  }
  return <XCircleIcon className="w-5 h-5 text-red-500" title="Failed" />
}

interface TestRunCaseAccordionProps {
  runId: number
  runNumber?: number | null
  result: CompletedCaseResult
  isExpanded: boolean
  onToggle: () => void
  onSync: (resultId: number, stepNum: number, tcId: number) => void
  syncing: Record<string, boolean>
  rowNumber: number
  onLogToJira?: () => void
}

export const TestRunCaseAccordion: React.FC<TestRunCaseAccordionProps> = ({
  runId,
  runNumber,
  result,
  isExpanded,
  onToggle,
  onSync,
  syncing,
  rowNumber,
  onLogToJira,
}) => {
  const ok = result.status === 'passed'
  const infra = isInfraCase(result)
  const canLogJira = !ok && !infra && result.status === 'failed' && !!onLogToJira
  const hasAdaptations =
    !!result.has_adaptations ||
    (!!result.adapted_steps && result.adapted_steps.length > 0)
  const shotCount = screenshotEvidenceCount(result)
  const hasScreenshots = shotCount > 0
  const userMsg =
    result.user_message ||
    ((result.ai_modified as Record<string, unknown> | null | undefined)?.user_message as
      | string
      | undefined) ||
    result.error_message

  const [detail, setDetail] = useState<TestResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(false)
  const [showAiModified, setShowAiModified] = useState(true)

  useEffect(() => {
    if (!isExpanded) return
    if (detail) return
    let cancelled = false
    setDetailLoading(true)
    setDetailError(false)
    testRunsApi
      .getResult(runId, result.test_result_id)
      .then((res) => {
        if (!cancelled) setDetail(res.data)
      })
      .catch(() => {
        if (!cancelled) setDetailError(true)
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isExpanded, runId, result.test_result_id, detail])

  const stepRows = detail?.step_results ?? result.step_results
  const rowBg = ok
    ? 'bg-green-50/60 hover:bg-green-50'
    : infra
      ? 'bg-amber-50/70 hover:bg-amber-50'
      : 'bg-red-50/60 hover:bg-red-50'

  return (
    <>
      <tr
        className={`cursor-pointer border-b border-gray-100 transition-colors ${rowBg}`}
        onClick={onToggle}
      >
        <td className="px-3 py-3 text-center text-sm font-medium text-gray-600 tabular-nums whitespace-nowrap">
          {rowNumber}
        </td>
        <td className="px-3 py-3 whitespace-nowrap">
          <span className="inline-flex items-center justify-center min-w-[2.25rem] px-2 py-1 rounded-md bg-white/80 border border-gray-200 text-sm font-bold text-gray-900 tabular-nums shadow-sm">
            #{runNumber ?? runId}
          </span>
        </td>
        <td className="px-3 py-3 whitespace-nowrap">
          <span className="inline-flex items-center justify-center min-w-[2.25rem] px-2 py-1 rounded-md bg-primary-50 border border-primary-100 text-sm font-bold text-primary-800 tabular-nums">
            #{result.test_case_id}
          </span>
        </td>
        <td className="px-3 py-3 text-xs text-gray-500 font-mono tabular-nums whitespace-nowrap">
          #{result.test_result_id}
        </td>
        <td className="px-3 py-3 whitespace-nowrap">
          <CaseStatusIcon result={result} />
        </td>
        <td className="px-3 py-3 min-w-0 max-w-md">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-sm text-gray-900">{result.title}</span>
            {infra && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-semibold rounded shrink-0">
                Blocked
              </span>
            )}
            {hasAdaptations && !infra && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-violet-50 text-violet-700 text-[10px] font-semibold rounded shrink-0">
                <SparklesIcon className="w-3 h-3" /> Adapted
              </span>
            )}
            {hasScreenshots && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-slate-100 text-slate-700 text-[10px] font-medium rounded shrink-0"
                title="Evidence screenshots"
              >
                <PhotoIcon className="w-3 h-3 shrink-0" />
                {shotCount} evidence
              </span>
            )}
            {result.jira_bug_key && (
              <a
                href={result.jira_bug_url || undefined}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center px-1.5 py-0.5 bg-sky-50 text-sky-800 text-[10px] font-semibold rounded shrink-0 hover:underline"
                title="Opened in Jira"
              >
                {result.jira_bug_key}
              </a>
            )}
          </div>
          {infra && userMsg && (
            <p className="mt-1 text-[11px] text-amber-800 line-clamp-2">{userMsg}</p>
          )}
        </td>
        <td className="px-3 py-3 text-xs text-gray-600 tabular-nums whitespace-nowrap">
          {infra
            ? `\u2014/${result.steps_total} blocked`
            : `${result.steps_passed}/${result.steps_total} steps`}
        </td>
        <td className="px-3 py-3 text-xs text-gray-600 tabular-nums whitespace-nowrap">
          {result.duration_display || formatDurationMs(result.duration_ms)}
        </td>
        <td className="px-3 py-3 text-right whitespace-nowrap">
          {isExpanded ? (
            <ChevronDownIcon className="w-4 h-4 text-gray-500 inline" />
          ) : (
            <ChevronRightIcon className="w-4 h-4 text-gray-500 inline" />
          )}
        </td>
      </tr>
      {isExpanded && (
        <tr className="bg-white border-b border-gray-100">
          <td colSpan={DETAIL_COL_SPAN} className="px-4 py-3 min-w-0 w-full align-top">
            <div className="space-y-3 min-w-0 max-w-full">
              {canLogJira && (
                <div className="flex items-center justify-between gap-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
                  <p className="text-xs text-gray-600">
                    File this failure as a Jira bug with repro steps and screenshots.
                  </p>
                  {result.jira_bug_key ? (
                    <a
                      href={result.jira_bug_url || undefined}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-semibold text-sky-700 hover:underline whitespace-nowrap"
                    >
                      {result.jira_bug_key}
                    </a>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation()
                        onLogToJira?.()
                      }}
                    >
                      Log to Jira
                    </Button>
                  )}
                </div>
              )}
              {infra && userMsg && (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  {userMsg}
                </div>
              )}
              {detailLoading && (
                <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                  Loading case details…
                </div>
              )}
              {detailError && !detailLoading && (
                <p className="text-xs text-red-600">Could not load full result details.</p>
              )}
              {detail && (
                <>
                  <AgentStepsStrip
                    enabled
                    runId={runId}
                    testResultId={result.test_result_id}
                    agentLogs={detail.agent_logs}
                    primaryScreenshotPath={detail.screenshot_path ?? undefined}
                    stepResults={detail.step_results ?? result.step_results}
                  />
                  {stepRows && stepRows.length > 0 && (
                    <div className="flex items-center justify-end mb-2">
                      <label className="inline-flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={showAiModified}
                          onChange={(e) => setShowAiModified(e.target.checked)}
                          className="rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                        />
                        Show AI-modified steps
                      </label>
                    </div>
                  )}
                  {stepRows?.map((s, i) => {
                    const descText = formatStepDisplayValue(s.description)
                    const actualText = formatStepDisplayValue(s.actual_result)
                    const adaptText = formatStepDisplayValue(s.adaptation)
                    const isAdapted = adaptText.length > 0
                    const shared = isSharedSetupStep(s)
                    const syncKey = `${result.test_result_id}-${s.step_number}`
                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 text-sm"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <StepStatusIcon step={s} />
                        <div className="flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-gray-700">
                              Step {s.step_number}
                              {shared && (
                                <span className="ml-2 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                                  Session login
                                </span>
                              )}
                            </span>
                            {isAdapted && (
                              <Button
                                size="xs"
                                variant="outline"
                                className="text-violet-600 border-violet-200 hover:bg-violet-50"
                                onClick={() =>
                                  onSync(result.test_result_id, s.step_number, result.test_case_id)
                                }
                                isLoading={syncing[syncKey]}
                              >
                                <SparklesIcon className="w-3 h-3 mr-1" />
                              </Button>
                            )}
                          </div>
                          <div className="mt-1 text-gray-500 italic text-xs">
                            {descText || '—'}
                          </div>
                          <p className="text-gray-600 mt-1">{actualText || '—'}</p>
                          {isAdapted && showAiModified && (
                            <div className="mt-2 p-3 bg-violet-50 rounded-lg border border-violet-100 text-xs">
                              <div className="flex items-center gap-2 text-violet-800 font-semibold mb-1">
                                <SparklesIcon className="w-3.5 h-3.5" />
                                AI modified this step
                              </div>
                              <div className="grid grid-cols-2 gap-4 mt-2">
                                <div>
                                  <p className="text-[10px] text-violet-400 uppercase font-semibold">
                                    Original Intent
                                  </p>
                                  <p className="text-violet-700 italic">&quot;{descText}&quot;</p>
                                </div>
                                <div>
                                  <p className="text-[10px] text-violet-400 uppercase font-semibold">
                                    AI Correction
                                  </p>
                                  <p className="text-violet-900 font-medium">{adaptText}</p>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
