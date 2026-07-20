import { Link, useParams } from 'react-router-dom'
import { PlayIcon, ClockIcon } from '@heroicons/react/24/outline'

import { Button } from '@common/components/ui/Button'
import { Card } from '@common/components/ui/Card'

import { TestRunDetailView } from '../../components/TestRunDetailView'
import { LaneBoard } from '../../components/LaneBoard'
import { useRequiredActiveTestRun } from '../../context/ActiveTestRunProvider'
import { isTerminalStatus } from '../../live/progressSource'

/**
 * Functional Testing → Live tab.
 *
 * When a run is active (or just completed and still pinned) the same
 * TestRunDetailView used by the full Run Detail page renders here. When
 * nothing is active, we show an empty state that points users at the Cases
 * tab and offers a shortcut to History.
 */
export default function LiveTab() {
  const { projectId } = useParams<{ projectId: string }>()
  const { activeRunId, progress, isCreating } = useRequiredActiveTestRun()
  const base = `/projects/${projectId}/functional-testing`

  if (!activeRunId && !isCreating) {
    return (
      <Card className="py-12 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
          <PlayIcon className="h-6 w-6 text-gray-400" />
        </div>
        <h3 className="mt-4 text-base font-semibold text-gray-900">
          No active test run
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Go to Run All, upload your CSV, and start execution. Watch live lane progress here.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2">
          <Link to={`${base}/run-all`}>
            <Button>
              <PlayIcon className="mr-2 h-4 w-4" /> Go to Run All
            </Button>
          </Link>
          <Link to={`${base}/history`}>
            <Button variant="outline">
              <ClockIcon className="mr-2 h-4 w-4" /> View History
            </Button>
          </Link>
        </div>
      </Card>
    )
  }

  if (!progress) {
    return (
      <Card className="py-12 text-center">
        <p className="text-sm text-gray-500">Starting test run…</p>
      </Card>
    )
  }

  const isDone = isTerminalStatus(progress.status)

  return (
    <div className="space-y-4">
      {isDone && activeRunId && (
        <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 px-4 py-3">
          <p className="text-sm font-medium text-green-800">
            Run complete. Open the full report for screenshots and logs.
          </p>
          <Link to={`${base}/history/${activeRunId}/report`}>
            <Button size="sm" variant="outline">
              View full report
            </Button>
          </Link>
        </div>
      )}
      {!isDone && (progress.active_lanes?.length || progress.groups?.length) ? (
        <Card className="p-4">
          <LaneBoard
            lanes={progress.active_lanes || []}
            groups={progress.groups}
            laneTarget={6}
            completed={progress.completed_results?.length ?? 0}
            total={progress.total_test_cases}
          />
        </Card>
      ) : null}
      <TestRunDetailView progress={progress} runId={activeRunId ?? 0} />
    </div>
  )
}
