import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  StopIcon,
} from '@heroicons/react/24/outline'

import { Button } from '@common/components/ui/Button'
import { useProjectStore } from '@common/store/projectStore'

import { testRunsApi } from '../api'
import { TestRunDetailView } from '../components/TestRunDetailView'
import { useActiveTestRun } from '../context/ActiveTestRunProvider'
import { isTerminalStatus, pollingProgressSource } from '../live/progressSource'
import type { LiveProgressResponse } from '../types'

/**
 * Full-page run detail. Two modes:
 *
 * 1. The Functional Testing shell is a parent → we read the live snapshot
 *    from the active-run context when the URL's runId matches. No duplicate
 *    poller.
 * 2. Direct deep-link (e.g. someone shared `/history/:runId`) → we subscribe
 *    our own ProgressSource so the page renders even without the shell.
 */
export default function TestRunDetail() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  const navigate = useNavigate()
  const currentProject = useProjectStore((s) => s.currentProject)
  const activeRun = useActiveTestRun()

  const numRunId = Number(runId)
  const projectDisplayName =
    projectId && currentProject?.id === Number(projectId) ? currentProject.name : null

  const useContextSnapshot =
    activeRun && activeRun.activeRunId === numRunId && activeRun.progress

  const [localProgress, setLocalProgress] = useState<LiveProgressResponse | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!Number.isFinite(numRunId) || useContextSnapshot) {
      return
    }
    unsubscribeRef.current?.()
    unsubscribeRef.current = pollingProgressSource.subscribe(numRunId, (snapshot) => {
      setLocalProgress(snapshot)
    })
    return () => {
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
    }
  }, [numRunId, useContextSnapshot])

  const progress = useContextSnapshot ? activeRun.progress : localProgress
  const isDone = progress ? isTerminalStatus(progress.status) : false

  const handleCancel = useCallback(async () => {
    if (activeRun && activeRun.activeRunId === numRunId) {
      await activeRun.cancelRun()
      return
    }
    try {
      await testRunsApi.cancel(numRunId)
    } catch {
      /* ignore */
    }
  }, [activeRun, numRunId])

  if (!progress) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const passed = progress.completed_results.filter((r) => r.status === 'passed').length
  const failed = progress.completed_results.filter((r) => r.status !== 'passed').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() =>
              navigate(`/projects/${projectId}/functional-testing/history`)
            }
            className="text-gray-400 hover:text-gray-600"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Test Run #{progress.run_number ?? runId}
            </h1>
            <p className="text-gray-500 text-sm">
              {isDone
                ? `Completed — ${passed} passed, ${failed} failed`
                : progress.current_test_case_title || 'Starting…'}
            </p>
            <p className="text-gray-400 text-xs mt-0.5">
              <span className="font-mono">Internal ref {numRunId}</span>
              {projectId && (
                <span className="text-gray-500">
                  {' '}
                  · {projectDisplayName ?? `Project #${projectId}`}
                </span>
              )}
            </p>
          </div>
        </div>
        {!isDone && (
          <Button
            variant="outline"
            className="text-red-600 border-red-200"
            onClick={handleCancel}
          >
            <StopIcon className="w-4 h-4 mr-1" /> Cancel
          </Button>
        )}
      </div>

      <TestRunDetailView progress={progress} runId={numRunId} />
    </div>
  )
}
