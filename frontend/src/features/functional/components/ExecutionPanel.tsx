import React from 'react'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { StopIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { isCancellingStatus } from '../live/progressSource'
import { formatDurationMs } from '../utils/formatDurationMs'
import type { LiveProgressResponse } from '../types'

interface ExecutionPanelProps {
  progress: LiveProgressResponse | null
  isRunning: boolean
  isCreating: boolean
  error: string | null
  isDone: boolean
  onCancel: () => void
  onViewDetails: () => void
}

export const ExecutionPanel: React.FC<ExecutionPanelProps> = ({
  progress,
  isRunning,
  isCreating,
  error,
  isDone,
  onCancel,
  onViewDetails
}) => {
  if (!progress && !isCreating && !error) return null

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <div className="flex items-center justify-between">
          <p className="text-sm text-red-700 font-medium">Failed to start: {error}</p>
          <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-100" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </div>
      </Card>
    )
  }

  if (isCreating && !progress) {
    return (
      <Card className="border-primary-100 bg-primary-50/30">
        <div className="flex items-center gap-3">
          <ArrowPathIcon className="w-5 h-5 animate-spin text-primary-600" />
          <span className="text-sm font-medium text-gray-700">Initializing test execution environment...</span>
        </div>
      </Card>
    )
  }

  const status = progress?.status || ''
  const isError = status === 'error' || !!progress?.error
  const isCancelling = isCancellingStatus(status)

  if (isError) {
    return (
      <Card className="border-red-200 bg-red-50">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-red-700">
            Execution Error: {progress?.error || 'Unknown error'}
          </span>
          <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-100" onClick={() => window.location.reload()}>
            Reset
          </Button>
        </div>
      </Card>
    )
  }

  if (!progress) return null

  const pct = progress.percentage ?? 0
  const passedCount = progress.completed_results.filter(r => r.status === 'passed').length
  const failedCount = progress.completed_results.filter(r => r.status === 'failed').length
  const blockedCount = progress.completed_results.filter(
    r => r.status === 'error' || r.infra_error
  ).length
  const banner = progress.runtime_banner

  return (
    <Card className="border-primary-100 bg-primary-50/30">
      {banner?.message && (
        <div
          className={`mb-2 rounded border px-3 py-2 text-xs ${
            banner.level === 'warning'
              ? 'border-amber-200 bg-amber-50 text-amber-900'
              : 'border-sky-200 bg-sky-50 text-sky-900'
          }`}
        >
          {banner.message}
        </div>
      )}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {isDone
            ? `Run complete — ${passedCount} passed, ${failedCount} failed${blockedCount ? `, ${blockedCount} blocked` : ''}`
            : isCancelling
              ? 'Cancelling — stopping current test…'
              : progress.status === 'paused'
                ? 'Paused — waiting for AI service…'
              : `Running: ${progress.current_test_case_title || 'Starting…'} (${Math.min(progress.current_test_case_index + 1, progress.total_test_cases)}/${progress.total_test_cases})`
          }
        </span>
        <div className="flex items-center gap-3">
          {(progress.elapsed_display || progress.elapsed_ms != null) && (
            <span className="text-xs text-gray-500 tabular-nums">
              {progress.elapsed_display || formatDurationMs(progress.elapsed_ms)}
            </span>
          )}
          <span className="text-sm font-semibold text-primary-600">{pct}%</span>
          {isRunning && !isCancelling && (
            <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50" onClick={onCancel}>
              <StopIcon className="w-3.5 h-3.5 mr-1" /> Cancel
            </Button>
          )}
          {isCancelling && (
            <span className="inline-flex items-center gap-1 text-sm text-amber-700">
              <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" /> Stopping…
            </span>
          )}
          {isDone && (
            <Button variant="ghost" size="sm" onClick={onViewDetails}>
              View Details
            </Button>
          )}
        </div>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${isDone && failedCount > 0 ? 'bg-red-500' : isDone ? 'bg-green-500' : isCancelling ? 'bg-amber-500' : 'bg-primary-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {!isDone && (progress.completed_results?.length ?? 0) > 0 && (
        <p className="mt-2 text-xs text-gray-500">
          {progress.completed_results.length} of {progress.total_test_cases} cases finished
        </p>
      )}
    </Card>
  )
}
