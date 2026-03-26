import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/solid'
import { LLMDiagnosisCard } from './LLMDiagnosisCard'
import { ScreenshotFilmstrip } from './ScreenshotFilmstrip'
import type { StepCheckResult, TestCaseCheckResult } from '../types'

interface Props {
  testCaseResults: TestCaseCheckResult[]
  isRunning: boolean
}

function formatMs(ms: number) {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

function StepStatusIcon({ status }: { status: string }) {
  if (status === 'passed')
    return <CheckCircleIcon className="h-4 w-4 flex-shrink-0 text-emerald-500" />
  if (status === 'failed' || status === 'error')
    return <XCircleIcon className="h-4 w-4 flex-shrink-0 text-red-500" />
  return (
    <span className="inline-block h-4 w-4 flex-shrink-0 animate-spin rounded-full border-2 border-primary-400 border-t-transparent" />
  )
}

function ActionBadge({ action }: { action: string }) {
  const colours: Record<string, string> = {
    navigate: 'bg-blue-100 text-blue-700',
    click: 'bg-violet-100 text-violet-700',
    fill: 'bg-teal-100 text-teal-700',
    type: 'bg-teal-100 text-teal-700',
    assert_visible: 'bg-orange-100 text-orange-700',
    assert_text: 'bg-orange-100 text-orange-700',
    assert_url: 'bg-orange-100 text-orange-700',
    wait: 'bg-gray-100 text-gray-600',
    screenshot: 'bg-pink-100 text-pink-700',
  }
  const cls = colours[action] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${cls}`}>
      {action}
    </span>
  )
}

function StepRow({ step, tcTitle }: { step: StepCheckResult; tcTitle: string }) {
  const failed = step.status === 'failed' || step.status === 'error'
  return (
    <div
      className={`rounded-md border px-3 py-2 transition-all ${
        failed
          ? 'border-red-200 bg-red-50'
          : step.status === 'passed'
          ? 'border-emerald-100 bg-emerald-50/50'
          : 'border-gray-100 bg-white'
      }`}
    >
      {/* Main row */}
      <div className="flex items-center gap-2 text-sm">
        <StepStatusIcon status={step.status} />
        <span className="w-6 flex-shrink-0 text-right text-xs text-gray-400">
          #{step.step_number}
        </span>
        <ActionBadge action={step.action} />
        <span className="min-w-0 flex-1 truncate text-gray-700">
          {step.description || step.action}
        </span>
        <span className="flex-shrink-0 text-xs text-gray-400">{formatMs(step.duration_ms)}</span>
      </div>

      {/* Error message */}
      {step.error && (
        <p className="mt-1 ml-6 text-xs text-red-600">{step.error}</p>
      )}

      {/* Screenshot thumbnail */}
      {step.screenshot_path && (
        <div className="mt-2 ml-6">
          <ScreenshotFilmstrip
            screenshots={[{ url: step.screenshot_path, label: `#${step.step_number}` }]}
          />
        </div>
      )}

      {/* LLM Diagnosis */}
      {failed && step.llm_diagnosis && (
        <LLMDiagnosisCard
          diagnosis={step.llm_diagnosis}
          stepNumber={step.step_number}
          action={step.action}
        />
      )}
    </div>
  )
}

function TestCaseBlock({ tc, isRunning }: { tc: TestCaseCheckResult; isRunning: boolean }) {
  const isPassed = tc.status === 'passed'
  const isFailed = tc.status === 'failed' || tc.status === 'error'
  const isActive = isRunning && tc.step_results.length > 0 && !isFailed && !isPassed

  return (
    <div
      className={`overflow-hidden rounded-xl border transition-all ${
        isPassed
          ? 'border-emerald-200'
          : isFailed
          ? 'border-red-200'
          : isActive
          ? 'border-primary-300 ring-1 ring-primary-200'
          : 'border-gray-200'
      }`}
    >
      {/* Test case header */}
      <div
        className={`flex items-center justify-between px-4 py-3 ${
          isPassed
            ? 'bg-emerald-50'
            : isFailed
            ? 'bg-red-50'
            : isActive
            ? 'bg-primary-50'
            : 'bg-gray-50'
        }`}
      >
        <div className="flex items-center gap-2">
          {isPassed ? (
            <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
          ) : isFailed ? (
            <XCircleIcon className="h-5 w-5 text-red-500" />
          ) : (
            <ClockIcon className="h-5 w-5 text-primary-400" />
          )}
          <span className="font-medium text-gray-900 text-sm">{tc.title}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>
            {tc.steps_passed}/{tc.steps_total} steps
          </span>
          <span>{formatMs(tc.duration_ms)}</span>
        </div>
      </div>

      {/* Steps */}
      {tc.step_results.length > 0 && (
        <div className="space-y-1.5 p-3">
          {tc.step_results.map((s) => (
            <StepRow key={s.step_number} step={s} tcTitle={tc.title} />
          ))}
        </div>
      )}
    </div>
  )
}

export function StepTimeline({ testCaseResults, isRunning }: Props) {
  if (testCaseResults.length === 0) {
    if (!isRunning) return null
    return (
      <div className="flex items-center gap-3 rounded-xl border border-primary-200 bg-primary-50 px-4 py-3">
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        <span className="text-sm text-primary-700">Launching browser and navigating to app...</span>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {testCaseResults.map((tc) => (
        <TestCaseBlock key={tc.test_case_id} tc={tc} isRunning={isRunning} />
      ))}
    </div>
  )
}
