import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import {
  ArrowPathIcon,
  StopIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline'
import { testRunsApi } from '../api'
import type { LiveProgressResponse } from '../types'
import toast from 'react-hot-toast'
import { TestRunCaseAccordion } from '../components/TestRunCaseAccordion'

const POLL_MS = 3000
const TERMINAL_STATES = ['completed', 'passed', 'failed', 'error', 'cancelled', 'not_found']

export default function TestRunDetail() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  const navigate = useNavigate()
  const [progress, setProgress] = useState<LiveProgressResponse | null>(null)
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [syncing, setSyncing] = useState<Record<string, boolean>>({})
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)
  const expandOnceRef = useRef(false)

  const numRunId = Number(runId)

  useEffect(() => {
    expandOnceRef.current = false
  }, [numRunId])
  const isDone = progress ? TERMINAL_STATES.includes(progress.status) : false

  const poll = useCallback(async () => {
    try {
      const res = await testRunsApi.getLiveProgress(numRunId)
      setProgress(res.data)
      if (TERMINAL_STATES.includes(res.data.status) && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {
      /* retry next tick */
    }
  }, [numRunId])

  useEffect(() => {
    poll()
    if (!isDone) {
      pollRef.current = setInterval(poll, POLL_MS)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [poll, isDone])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [progress?.logs?.length])

  /** Open rows that have screenshots (or failures) so evidence is visible without an extra click. */
  useEffect(() => {
    if (!progress || !isDone || expandOnceRef.current) return
    const list = progress.completed_results
    if (list.length === 0) return
    expandOnceRef.current = true
    setExpanded((prev) => {
      const next = { ...prev }
      for (const r of list) {
        const hasShots =
          !!r.screenshot_path ||
          (r.agent_logs ?? []).some((l) => !!l.screenshot_path)
        if (hasShots || r.status !== 'passed') {
          next[r.test_result_id] = true
        }
      }
      return next
    })
  }, [progress, isDone])

  const handleCancel = async () => {
    try {
      await testRunsApi.cancel(numRunId)
      poll()
    } catch {
      /* ignore */
    }
  }

  const handleSyncStep = async (resultId: number, stepNumber: number, tcId: number) => {
    const key = `${resultId}-${stepNumber}`
    setSyncing((prev) => ({ ...prev, [key]: true }))
    try {
      await testRunsApi.syncStep(resultId, stepNumber)
      toast.success(`Step ${stepNumber} synced to Test Case #${tcId}`)
    } catch {
      toast.error('Failed to sync step')
    } finally {
      setSyncing((prev) => ({ ...prev, [key]: false }))
    }
  }

  if (!progress) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const pct = progress.percentage
  const passed = progress.completed_results.filter((r) => r.status === 'passed').length
  const failed = progress.completed_results.filter((r) => r.status !== 'passed').length
  const total = progress.total_test_cases

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}/test-runs`)}
            className="text-gray-400 hover:text-gray-600"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Test Run #{runId}</h1>
            <p className="text-gray-500 text-sm">
              {isDone
                ? `Completed — ${passed} passed, ${failed} failed`
                : progress.current_test_case_title || 'Starting…'}
            </p>
          </div>
        </div>
        {!isDone && (
          <Button variant="outline" className="text-red-600 border-red-200" onClick={handleCancel}>
            <StopIcon className="w-4 h-4 mr-1" /> Cancel
          </Button>
        )}
      </div>

      <Card>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {isDone
              ? 'Execution Summary'
              : `Running test case ${progress.current_test_case_index + 1} of ${total}`}
          </span>
          <span className="text-sm font-semibold text-primary-600">{pct}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${isDone && failed > 0 ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-primary-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </Card>

      <div className="grid grid-cols-4 gap-4">
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Total</p>
          <p className="text-xl font-bold">{total}</p>
        </Card>
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Passed</p>
          <p className="text-xl font-bold text-green-600">{passed}</p>
        </Card>
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Failed</p>
          <p className="text-xl font-bold text-red-600">{failed}</p>
        </Card>
        <Card className="text-center p-4">
          <p className="text-xs text-gray-500 uppercase">Success Rate</p>
          <p className="text-xl font-bold text-primary-600">
            {total ? Math.round((passed / total) * 100) : 0}%
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-2">
          <CardTitle>Test Case Results</CardTitle>
          {progress.completed_results.length === 0 && !isDone && (
            <p className="text-sm text-gray-400 py-4">Waiting for first test case to complete…</p>
          )}
          {progress.completed_results.map((r) => (
            <TestRunCaseAccordion
              key={r.test_result_id}
              runId={numRunId}
              result={r}
              isExpanded={!!expanded[r.test_result_id]}
              onToggle={() =>
                setExpanded((prev) => ({
                  ...prev,
                  [r.test_result_id]: !prev[r.test_result_id],
                }))
              }
              onSync={handleSyncStep}
              syncing={syncing}
            />
          ))}
        </div>

        <div className="lg:col-span-2">
          <CardTitle>Execution Log</CardTitle>
          <div className="bg-gray-900 rounded-lg p-4 h-[500px] overflow-y-auto font-mono text-[10px] leading-relaxed shadow-xl border border-gray-800">
            {progress.logs.length === 0 && (
              <span className="text-gray-500 italic">Waiting for logs…</span>
            )}
            {progress.logs.map((l, i) => {
              const ts = l.timestamp.split('T')[1]?.slice(0, 8) || ''
              const color = l.message.startsWith('✓')
                ? 'text-green-400'
                : l.message.startsWith('✗')
                  ? 'text-red-400'
                  : l.message.startsWith('▶')
                    ? 'text-blue-400'
                    : l.message.includes('⚠')
                      ? 'text-yellow-400'
                      : 'text-gray-300'
              return (
                <div key={i} className="flex gap-2 mb-0.5">
                  <span className="text-gray-600 shrink-0 select-none">[{ts}]</span>
                  <span className={color}>{l.message}</span>
                </div>
              )
            })}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>
    </div>
  )
}
