import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  StopIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ArrowLeftIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import { testRunsApi } from '../api'
import type { LiveProgressResponse, CompletedCaseResult, LogEntry } from '../types'
import toast from 'react-hot-toast'

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

  const numRunId = Number(runId)
  const isDone = progress ? TERMINAL_STATES.includes(progress.status) : false

  const poll = useCallback(async () => {
    try {
      const res = await testRunsApi.getLiveProgress(numRunId)
      setProgress(res.data)
      if (TERMINAL_STATES.includes(res.data.status) && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch { /* retry next tick */ }
  }, [numRunId])

  useEffect(() => {
    poll()
    if (!isDone) {
      pollRef.current = setInterval(poll, POLL_MS)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [poll, isDone])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [progress?.logs?.length])

  const handleCancel = async () => {
    try {
      await testRunsApi.cancel(numRunId)
      poll()
    } catch { /* ignore */ }
  }

  const handleSyncStep = async (resultId: number, stepNumber: number, tcId: number) => {
    const key = `${resultId}-${stepNumber}`
    setSyncing(prev => ({ ...prev, [key]: true }))
    try {
      await testRunsApi.syncStep(resultId, stepNumber)
      toast.success(`Step ${stepNumber} synced to Test Case #${tcId}`)
    } catch (err) {
      toast.error('Failed to sync step')
    } finally {
      setSyncing(prev => ({ ...prev, [key]: false }))
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
  const passed = progress.completed_results.filter(r => r.status === 'passed').length
  const failed = progress.completed_results.filter(r => r.status !== 'passed').length
  const total = progress.total_test_cases

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(`/projects/${projectId}/test-runs`)} className="text-gray-400 hover:text-gray-600">
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Test Run #{runId}</h1>
            <p className="text-gray-500 text-sm">
              {isDone ? `Completed — ${passed} passed, ${failed} failed` : progress.current_test_case_title || 'Starting…'}
            </p>
          </div>
        </div>
        {!isDone && (
          <Button variant="outline" className="text-red-600 border-red-200" onClick={handleCancel}>
            <StopIcon className="w-4 h-4 mr-1" /> Cancel
          </Button>
        )}
      </div>

      {/* Progress bar */}
      <Card>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {isDone ? 'Execution Summary' : `Running test case ${progress.current_test_case_index + 1} of ${total}`}
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

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="text-center p-4"><p className="text-xs text-gray-500 uppercase">Total</p><p className="text-xl font-bold">{total}</p></Card>
        <Card className="text-center p-4"><p className="text-xs text-gray-500 uppercase">Passed</p><p className="text-xl font-bold text-green-600">{passed}</p></Card>
        <Card className="text-center p-4"><p className="text-xs text-gray-500 uppercase">Failed</p><p className="text-xl font-bold text-red-600">{failed}</p></Card>
        <Card className="text-center p-4"><p className="text-xs text-gray-500 uppercase">Success Rate</p><p className="text-xl font-bold text-primary-600">{total ? Math.round((passed/total)*100) : 0}%</p></Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Test case results */}
        <div className="lg:col-span-3 space-y-2">
          <CardTitle>Test Case Results</CardTitle>
          {progress.completed_results.length === 0 && !isDone && (
            <p className="text-sm text-gray-400 py-4">Waiting for first test case to complete…</p>
          )}
          {progress.completed_results.map(r => (
            <TestCaseAccordion
              key={r.test_case_id}
              result={r}
              isExpanded={!!expanded[r.test_case_id]}
              onToggle={() => setExpanded(prev => ({ ...prev, [r.test_case_id]: !prev[r.test_case_id] }))}
              onSync={handleSyncStep}
              syncing={syncing}
            />
          ))}
        </div>

        {/* Terminal log */}
        <div className="lg:col-span-2">
          <CardTitle>Execution Log</CardTitle>
          <div className="bg-gray-900 rounded-lg p-4 h-[500px] overflow-y-auto font-mono text-[10px] leading-relaxed shadow-xl border border-gray-800">
            {progress.logs.length === 0 && <span className="text-gray-500 italic">Waiting for logs…</span>}
            {progress.logs.map((l, i) => {
              const ts = l.timestamp.split('T')[1]?.slice(0, 8) || ''
              const color = l.message.startsWith('✓') ? 'text-green-400'
                : l.message.startsWith('✗') ? 'text-red-400'
                : l.message.startsWith('▶') ? 'text-blue-400'
                : l.message.includes('⚠') ? 'text-yellow-400'
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

function TestCaseAccordion({ result, isExpanded, onToggle, onSync, syncing }: { 
  result: CompletedCaseResult; 
  isExpanded: boolean; 
  onToggle: () => void;
  onSync: (resId: number, stepNum: number, tcId: number) => void;
  syncing: Record<string, boolean>;
}) {
  const ok = result.status === 'passed'
  const hasAdaptations = result.adapted_steps && result.adapted_steps.length > 0

  return (
    <div className={`border rounded-lg overflow-hidden transition-all ${ok ? 'border-green-100' : 'border-red-100'}`}>
      <button onClick={onToggle} className={`w-full flex items-center justify-between px-4 py-3 text-left ${ok ? 'bg-green-50/50 hover:bg-green-50' : 'bg-red-50/50 hover:bg-red-50'}`}>
        <div className="flex items-center gap-2">
          {ok ? <CheckCircleIcon className="w-5 h-5 text-green-500" /> : <XCircleIcon className="w-5 h-5 text-red-500" />}
          <span className="font-medium text-sm text-gray-900">{result.title}</span>
          {hasAdaptations && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold rounded-full uppercase">
              <SparklesIcon className="w-3 h-3" /> AI Adapted
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{result.steps_passed}/{result.steps_total} steps</span>
          <span>{Math.round(result.duration_ms / 1000)}s</span>
          {isExpanded ? <ChevronDownIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 space-y-3 bg-white border-t border-gray-50">
          {result.step_results?.map((s, i) => {
            const isAdapted = s.adaptation;
            const syncKey = `${result.test_case_id}-${s.step_number}`; // Simplified key
            return (
              <div key={i} className="flex items-start gap-3 text-sm">
                {s.status === 'passed'
                  ? <CheckCircleIcon className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                  : <XCircleIcon className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-700">Step {s.step_number}</span>
                    {isAdapted && (
                      <Button 
                        size="xs" 
                        variant="outline" 
                        className="text-purple-600 border-purple-200 hover:bg-purple-50"
                        onClick={() => onSync(result.test_case_id, s.step_number, result.test_case_id)}
                        isLoading={syncing[syncKey]}
                      >
                        <SparklesIcon className="w-3 h-3 mr-1" /> Sync to Case
                      </Button>
                    )}
                  </div>
                  
                  {/* Original Step Description */}
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
                          <p className="text-[10px] text-purple-400 uppercase font-bold">Original Intent</p>
                          <p className="text-purple-700 italic">"{s.description}"</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-purple-400 uppercase font-bold">AI Correction</p>
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
