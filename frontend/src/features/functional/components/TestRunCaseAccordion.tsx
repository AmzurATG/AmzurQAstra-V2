import React from 'react'
import { Button } from '@common/components/ui/Button'
import {
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  SparklesIcon,
  PhotoIcon,
} from '@heroicons/react/24/outline'
import type { CompletedCaseResult } from '../types'
import { AgentStepsStrip } from './AgentStepsStrip'

function screenshotEvidenceCount(r: CompletedCaseResult): number {
  const logs = r.agent_logs ?? []
  const n = logs.filter((l) => l.screenshot_path).length
  if (n > 0) return n
  return r.screenshot_path ? 1 : 0
}

interface TestRunCaseAccordionProps {
  runId: number
  result: CompletedCaseResult
  isExpanded: boolean
  onToggle: () => void
  onSync: (resultId: number, stepNum: number, tcId: number) => void
  syncing: Record<string, boolean>
}

export const TestRunCaseAccordion: React.FC<TestRunCaseAccordionProps> = ({
  runId,
  result,
  isExpanded,
  onToggle,
  onSync,
  syncing,
}) => {
  const ok = result.status === 'passed'
  const hasAdaptations = result.adapted_steps && result.adapted_steps.length > 0
  const shotCount = screenshotEvidenceCount(result)
  const hasScreenshots = shotCount > 0

  return (
    <div
      className={`border rounded-lg overflow-hidden transition-all ${ok ? 'border-green-100' : 'border-red-100'}`}
    >
      <button
        type="button"
        onClick={onToggle}
        className={`w-full flex items-center justify-between px-4 py-3 text-left ${ok ? 'bg-green-50/50 hover:bg-green-50' : 'bg-red-50/50 hover:bg-red-50'}`}
      >
        <div className="flex items-center gap-2">
          {ok ? (
            <CheckCircleIcon className="w-5 h-5 text-green-500" />
          ) : (
            <XCircleIcon className="w-5 h-5 text-red-500" />
          )}
          <span className="font-medium text-sm text-gray-900">{result.title}</span>
          {hasAdaptations && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold rounded-full uppercase">
              <SparklesIcon className="w-3 h-3" /> AI Adapted
            </span>
          )}
          {hasScreenshots && (
            <span
              className="flex items-center gap-1 px-1.5 py-0.5 bg-sky-100 text-sky-800 text-[10px] font-semibold rounded-full"
              title={isExpanded ? '' : 'Expand to view screenshots'}
            >
              <PhotoIcon className="w-3 h-3 shrink-0" />
              {shotCount} screenshot{shotCount === 1 ? '' : 's'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>
            {result.steps_passed}/{result.steps_total} steps
          </span>
          <span>{Math.round(result.duration_ms / 1000)}s</span>
          {isExpanded ? (
            <ChevronDownIcon className="w-4 h-4" />
          ) : (
            <ChevronRightIcon className="w-4 h-4" />
          )}
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 space-y-3 bg-white border-t border-gray-50">
          <AgentStepsStrip
            runId={runId}
            testResultId={result.test_result_id}
            agentLogs={result.agent_logs}
            primaryScreenshotPath={result.screenshot_path ?? undefined}
          />
          {result.step_results?.map((s, i) => {
            const isAdapted = s.adaptation
            const syncKey = `${result.test_result_id}-${s.step_number}`
            return (
              <div key={i} className="flex items-start gap-3 text-sm">
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
        </div>
      )}
    </div>
  )
}
