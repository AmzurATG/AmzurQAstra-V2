import React from 'react'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { StopIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
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
  const failedCount = progress.completed_results.filter(r => r.status !== 'passed').length

  return (
    <Card className="border-primary-100 bg-primary-50/30">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {isDone
            ? `Run complete — ${passedCount} passed, ${failedCount} failed`
            : `Running: ${progress.current_test_case_title || 'Starting…'} (${progress.current_test_case_index + 1}/${progress.total_test_cases})`
          }
        </span>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-primary-600">{pct}%</span>
          {isRunning && (
            <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50" onClick={onCancel}>
              <StopIcon className="w-3.5 h-3.5 mr-1" /> Cancel
            </Button>
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
          className={`h-2.5 rounded-full transition-all duration-500 ${isDone && failedCount > 0 ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-primary-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </Card>
  )
}
