import { NavLink, Outlet, useParams } from 'react-router-dom'
import {
  ClipboardDocumentListIcon,
  PlayIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  SignalSlashIcon,
} from '@heroicons/react/24/outline'

import { ExecutionPanel } from '../components/ExecutionPanel'
import { useRequiredActiveTestRun } from '../context/ActiveTestRunProvider'
import { isTerminalStatus } from '../live/progressSource'
import { useNavigate } from 'react-router-dom'

/**
 * Functional Testing workspace shell.
 *
 * Single project-scoped home for: authoring active ("ready") cases, watching
 * the live run, and browsing history. The pinned ExecutionPanel + connection
 * banner live above the tab strip so they persist across tab switches — that
 * was the missing piece when execution state was owned locally by
 * TestCases.tsx.
 */
export default function FunctionalTesting() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const {
    progress,
    isCreating,
    isRunning,
    activeRunId,
    error,
    connectionStatus,
    cancelRun,
  } = useRequiredActiveTestRun()

  const base = `/projects/${projectId}/functional-testing`
  const hasActiveOrRecentRun = !!progress || isCreating || !!error
  const liveDotVisible = isRunning || isCreating
  const liveCount =
    progress && !isTerminalStatus(progress.status) && progress.total_test_cases > 0
      ? `${Math.min(progress.current_test_case_index + 1, progress.total_test_cases)}/${progress.total_test_cases}`
      : null

  const tabClass = ({ isActive }: { isActive: boolean }) =>
    `relative px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
      isActive
        ? 'border-primary-500 text-primary-700'
        : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-200'
    }`

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Functional Testing</h1>
        <p className="text-gray-600">
          Promote reviewed cases, execute them, and review past runs — all in one place.
        </p>
      </div>

      {connectionStatus !== 'ok' && (
        <div
          className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
            connectionStatus === 'lost'
              ? 'border-red-200 bg-red-50 text-red-700'
              : 'border-amber-200 bg-amber-50 text-amber-800'
          }`}
          role="status"
        >
          {connectionStatus === 'lost' ? (
            <SignalSlashIcon className="h-4 w-4" />
          ) : (
            <ExclamationTriangleIcon className="h-4 w-4" />
          )}
          <span>
            {connectionStatus === 'lost'
              ? 'Lost connection to the run service. Retrying in the background.'
              : 'Connection is unstable — progress updates may be delayed.'}
          </span>
        </div>
      )}

      {hasActiveOrRecentRun && (
        <ExecutionPanel
          progress={progress}
          isRunning={isRunning}
          isCreating={isCreating}
          error={error}
          isDone={!!progress && isTerminalStatus(progress.status)}
          onCancel={cancelRun}
          onViewDetails={() => {
            if (activeRunId) {
              navigate(`${base}/history/${activeRunId}`)
            }
          }}
        />
      )}

      <div className="flex gap-1 border-b border-gray-200">
        <NavLink to={`${base}/cases`} className={tabClass}>
          <span className="inline-flex items-center gap-1.5">
            <ClipboardDocumentListIcon className="h-4 w-4" />
            Test Cases
          </span>
        </NavLink>
        <NavLink to={`${base}/live`} className={tabClass}>
          <span className="inline-flex items-center gap-1.5">
            <PlayIcon className="h-4 w-4" />
            Live Run
            {liveDotVisible && (
              <span
                className="ml-1 inline-block h-2 w-2 rounded-full bg-primary-500 animate-pulse"
                aria-hidden
              />
            )}
            {liveCount && (
              <span className="ml-1 rounded bg-primary-100 px-1.5 py-0.5 text-[10px] font-semibold text-primary-700 tabular-nums">
                {liveCount}
              </span>
            )}
          </span>
        </NavLink>
        <NavLink to={`${base}/history`} className={tabClass}>
          <span className="inline-flex items-center gap-1.5">
            <ClockIcon className="h-4 w-4" />
            History
          </span>
        </NavLink>
      </div>

      <Outlet />
    </div>
  )
}
