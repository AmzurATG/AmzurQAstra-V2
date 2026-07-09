import React, { useEffect, useMemo, useState } from 'react'
import { Button } from '@common/components/ui/Button'
import {
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  SparklesIcon,
  PhotoIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import type { CompletedCaseResult, TestResult } from '../types'
import { AgentStepsStrip } from './AgentStepsStrip'
import { testRunsApi } from '../api'
import { formatStepDisplayValue } from '../utils/formatStepDisplayValue'
import {
  actionsForStep,
  formatActionDescription,
  groupAgentLogsByStep,
} from '../utils/groupAgentLogsByStep'

const DETAIL_COL_SPAN = 9

function screenshotEvidenceCount(
  r: CompletedCaseResult,
  detailSteps?: { screenshot_path?: string | null }[] | null
): number {
  // Match the expanded strip: one evidence slot per step that has a screenshot
  // (same file reused across merged steps still counts once per step in the UI).
  const steps = detailSteps ?? r.step_results
  if (steps && steps.length > 0) {
    const n = steps.filter((s) => !!s.screenshot_path).length
    if (n > 0) return n
  }
  if (typeof r.agent_screenshot_count === 'number' && r.agent_screenshot_count > 0) {
    return r.agent_screenshot_count
  }
  const fromLogs = (r.agent_logs ?? []).filter((l) => l.screenshot_path).length
  if (fromLogs > 0) return fromLogs
  return r.screenshot_path ? 1 : 0
}

interface TestRunCaseAccordionProps {
  runId: number
  /** Per-project run index for display (optional; falls back to `runId`). */
  runNumber?: number | null
  result: CompletedCaseResult
  isExpanded: boolean
  onToggle: () => void
  onSync: (resultId: number, stepNum: number, tcId: number) => void
  syncing: Record<string, boolean>
  /** 1-based row index in the run results table */
  rowNumber: number
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
}) => {
  const ok = result.status === 'passed'
  const hasAdaptations =
    !!result.has_adaptations ||
    (!!result.adapted_steps && result.adapted_steps.length > 0)
  const [detail, setDetail] = useState<TestResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(false)

  const shotCount = screenshotEvidenceCount(result, detail?.step_results)
  const hasScreenshots = shotCount > 0

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
  const agentLogGroups = useMemo(
    () => groupAgentLogsByStep(detail?.agent_logs ?? result.agent_logs),
    [detail?.agent_logs, result.agent_logs]
  )

  return (
    <>
      <tr
        className={`cursor-pointer border-b border-gray-100 transition-colors ${ok ? 'bg-green-50/60 hover:bg-green-50' : 'bg-red-50/60 hover:bg-red-50'}`}
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
          {ok ? (
            <CheckCircleIcon className="w-5 h-5 text-green-500" title="Passed" />
          ) : (
            <XCircleIcon className="w-5 h-5 text-red-500" title="Failed" />
          )}
        </td>
        <td className="px-3 py-3 min-w-0 max-w-md">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-sm text-gray-900">{result.title}</span>
            {hasAdaptations && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold rounded-full uppercase shrink-0">
                <SparklesIcon className="w-3 h-3" /> AI Adapted
              </span>
            )}
            {result.has_inferred_verdicts && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded-full uppercase shrink-0"
                title="At least one step lacked an explicit STEP_VERDICT — result was inferred"
              >
                Inferred
              </span>
            )}
            {result.shared_session && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-slate-100 text-slate-700 text-[10px] font-bold rounded-full uppercase shrink-0"
                title={
                  result.group_duration_ms
                    ? `Shared browser session — group wall time ${Math.round(result.group_duration_ms / 1000)}s; duration shown is this case's share`
                    : 'Shared browser session with other cases in this group'
                }
              >
                Shared
              </span>
            )}
            {!ok && result.failure_reason && (
              <span
                className="text-[11px] text-red-700/90 truncate max-w-[14rem]"
                title={result.failure_reason}
              >
                {result.failed_step != null ? `Step ${result.failed_step}: ` : ''}
                {result.failure_reason}
              </span>
            )}
            {hasScreenshots && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-sky-100 text-sky-800 text-[10px] font-semibold rounded-full shrink-0"
                title="Expand to load screenshots"
              >
                <PhotoIcon className="w-3 h-3 shrink-0" />
                {shotCount} screenshot{shotCount === 1 ? '' : 's'}
              </span>
            )}
          </div>
        </td>
        <td className="px-3 py-3 text-xs text-gray-600 tabular-nums whitespace-nowrap">
          {result.steps_passed}/{result.steps_total} steps
        </td>
        <td className="px-3 py-3 text-xs text-gray-600 tabular-nums whitespace-nowrap">
          <span title={
            result.shared_session && result.group_duration_ms
              ? `Case share of shared group (${Math.round(result.group_duration_ms / 1000)}s wall)`
              : undefined
          }>
            {Math.round(result.duration_ms / 1000)}s
            {result.shared_session ? (
              <span className="text-gray-400 font-normal"> · share</span>
            ) : null}
          </span>
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
                  {stepRows?.map((s, i) => {
                    const descText = formatStepDisplayValue(s.description)
                    const actualText = formatStepDisplayValue(s.actual_result)
                    const adaptText = formatStepDisplayValue(s.adaptation)
                    const isAdapted = adaptText.length > 0
                    const syncKey = `${result.test_result_id}-${s.step_number}`
                    const stepActionsFromResult = (s.agent_actions ?? []).filter(Boolean)
                    const stepActionsFromLogs = actionsForStep(agentLogGroups, s.step_number)
                    const stepActionTexts =
                      stepActionsFromResult.length > 0
                        ? stepActionsFromResult
                        : stepActionsFromLogs.map((a) => formatActionDescription(a.description))
                    const statusLabel =
                      s.status === 'passed'
                        ? 'Passed'
                        : s.status === 'failed'
                          ? 'Failed'
                          : s.status === 'error'
                            ? 'Error'
                            : s.status === 'skipped'
                              ? 'Skipped'
                              : s.status
                    const verdictSrc = s.verdict_source || ''
                    const isInferred = verdictSrc.startsWith('inferred')
                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 text-sm"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {s.status === 'passed' ? (
                          <CheckCircleIcon className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                        ) : (
                          <XCircleIcon className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-gray-700">
                              Step {s.step_number}
                              <span className="ml-2 text-[10px] font-bold uppercase tracking-wide text-gray-400">
                                {statusLabel}
                              </span>
                              {isInferred && (
                                <span className="ml-2 text-[10px] font-bold uppercase tracking-wide text-amber-600">
                                  Inferred
                                </span>
                              )}
                              {verdictSrc === 'explicit' && (
                                <span className="ml-2 text-[10px] font-bold uppercase tracking-wide text-emerald-600">
                                  Explicit
                                </span>
                              )}
                            </span>
                            {isAdapted && (
                              <Button
                                size="xs"
                                variant="outline"
                                className="text-purple-600 border-purple-200 hover:bg-purple-50"
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
                            Original: {descText || '—'}
                          </div>

                          <div className="mt-1.5">
                            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">
                              Result
                            </p>
                            <p className="text-gray-700 mt-0.5 text-sm leading-snug">
                              {actualText || '—'}
                            </p>
                          </div>

                          {stepActionTexts.length > 0 && (
                            <div className="mt-2 rounded-md border border-gray-100 bg-gray-50/80 px-2.5 py-2">
                              <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400 mb-1">
                                Browser actions ({stepActionTexts.length})
                              </p>
                              <ul className="space-y-1">
                                {stepActionTexts.map((text, ai) => (
                                  <li
                                    key={`${s.step_number}-${ai}`}
                                    className="text-xs text-gray-600 leading-snug flex gap-1.5"
                                  >
                                    <span className="text-gray-300 shrink-0 select-none">•</span>
                                    <span className="min-w-0 break-words">{text}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {isAdapted && (
                            <div className="mt-2 p-3 bg-purple-50 rounded-lg border border-purple-100 text-xs shadow-sm">
                              <div className="flex items-center gap-2 text-purple-800 font-bold mb-1">
                                <SparklesIcon className="w-3.5 h-3.5" />
                                AI INTELLIGENCE: STEP ADAPTATION
                              </div>
                              <div className="grid grid-cols-2 gap-4 mt-2">
                                <div>
                                  <p className="text-[10px] text-purple-400 uppercase font-bold">
                                    Original Intent
                                  </p>
                                  <p className="text-purple-700 italic">&quot;{descText}&quot;</p>
                                </div>
                                <div>
                                  <p className="text-[10px] text-purple-400 uppercase font-bold">
                                    AI Correction
                                  </p>
                                  <p className="text-purple-900 font-medium">{adaptText}</p>
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
