import React, { useEffect, useState } from 'react'
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

const DETAIL_COL_SPAN = 9

function screenshotEvidenceCount(r: CompletedCaseResult): number {
  const n =
    r.agent_screenshot_count ??
    (r.agent_logs ?? []).filter((l) => l.screenshot_path).length
  if (n > 0) return n
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
  const shotCount = screenshotEvidenceCount(result)
  const hasScreenshots = shotCount > 0

  const [detail, setDetail] = useState<TestResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(false)

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
          {Math.round(result.duration_ms / 1000)}s
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
          <td colSpan={DETAIL_COL_SPAN} className="px-4 py-3">
            <div className="space-y-3">
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
                  />
                  {stepRows?.map((s, i) => {
                    const isAdapted = s.adaptation
                    const syncKey = `${result.test_result_id}-${s.step_number}`
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
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-gray-700">Step {s.step_number}</span>
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
                                <SparklesIcon className="w-3 h-3 mr-1" /> Sync to Case
                              </Button>
                            )}
                          </div>

                          <div className="mt-1 text-gray-500 italic text-xs">
                            Original: {s.description || '—'}
                          </div>

                          <p className="text-gray-600 mt-1">{s.actual_result || '—'}</p>

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
                                  <p className="text-purple-700 italic">&quot;{s.description}&quot;</p>
                                </div>
                                <div>
                                  <p className="text-[10px] text-purple-400 uppercase font-bold">
                                    AI Correction
                                  </p>
                                  <p className="text-purple-900 font-medium">{s.adaptation}</p>
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
