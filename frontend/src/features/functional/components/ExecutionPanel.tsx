import React from 'react'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { StopIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import type { LiveProgressResponse, ExecutionPlanGroup } from '../types'

interface ExecutionPanelProps {
  progress: LiveProgressResponse | null
  isRunning: boolean
  isCreating: boolean
  error: string | null
  isDone: boolean
  onCancel: () => void
  onViewDetails: () => void
}

/** Groups ExecutionPlanGroup entries by browser_lane number. */
function groupByLane(groups: ExecutionPlanGroup[]): Map<number, ExecutionPlanGroup[]> {
  const map = new Map<number, ExecutionPlanGroup[]>()
  for (const g of groups) {
    const lane = g.browser_lane
    if (!map.has(lane)) map.set(lane, [])
    map.get(lane)!.push(g)
  }
  return map
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

  // Planning phase — AI is building the execution plan
  if (status === 'planning') {
    return (
      <Card className="border-blue-100 bg-blue-50/40">
        <div className="flex items-center gap-3">
          <ArrowPathIcon className="w-5 h-5 animate-spin text-blue-500" />
          <div>
            <p className="text-sm font-medium text-gray-700">
              {progress.current_test_case_title || 'AI is building execution plan…'}
            </p>
            {progress.current_step_info && (
              <p className="text-xs text-gray-500 mt-0.5">{progress.current_step_info}</p>
            )}
          </div>
        </div>
      </Card>
    )
  }

  const pct = progress.percentage ?? 0
  const passedCount = progress.completed_results.filter(r => r.status === 'passed').length
  const failedCount = progress.completed_results.filter(r => r.status !== 'passed' && r.status !== 'skipped').length

  const statusLabel = isDone
    ? `Run complete — ${passedCount} passed, ${failedCount} failed`
    : `Running: ${progress.current_test_case_title || 'Starting…'} (${progress.current_test_case_index + 1}/${progress.total_test_cases})`

  const planGroups = progress.execution_plan?.groups
  const laneMap = planGroups ? groupByLane(planGroups) : null

  return (
    <Card className="border-primary-100 bg-primary-50/30">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{statusLabel}</span>
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
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${
            isDone && failedCount > 0
              ? 'bg-red-500'
              : isDone
              ? 'bg-green-500'
              : 'bg-primary-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Lane grid — shown when a grouped_parallel plan is active */}
      {laneMap && laneMap.size > 0 && (
        <div className="mt-1 flex flex-wrap gap-2">
          {Array.from(laneMap.entries()).map(([lane, groups]) => (
            <div
              key={lane}
              className="flex flex-col gap-1 rounded border border-primary-100 bg-white px-3 py-2 text-xs min-w-[140px]"
            >
              <span className="font-semibold text-primary-700">Lane {lane}</span>
              {groups.map(g => (
                <div key={g.group_id} className="flex items-center gap-1.5">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      g.session_type === 'shared'
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {g.session_type}
                  </span>
                  <span className="text-gray-600 truncate max-w-[110px]">{g.label}</span>
                  <span className="text-gray-400 ml-auto whitespace-nowrap">{g.ordered_cases.length}tc</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
