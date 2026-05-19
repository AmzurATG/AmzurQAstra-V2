import { Fragment, useCallback, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { useNavigate } from 'react-router-dom'
import {
  XMarkIcon,
  LightBulbIcon,
  ExclamationTriangleIcon,
  ArrowDownTrayIcon,
  EnvelopeIcon,
  PlayIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid'
import { Button } from '@common/components/ui/Button'
import { Loader } from '@common/components/ui/Loader'
import { testRecommendationsApi } from '../api'
import type { TestRecommendationRun, TestRecommendationStrategyItem } from '../types'
import {
  useAcceptRecommendation,
  resolveItemAction,
  getComingSoonFeatureName,
  type AcceptPhase,
} from '../hooks/useAcceptRecommendation'
import EmailReportDialog from './EmailReportDialog'
import toast from 'react-hot-toast'
import { testCasePriorityLabel } from '../constants/testCaseUi'
import { GAP_ANALYSIS_LABEL } from '../constants/requirementUi'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Tab = 'summary' | 'pdf'

interface TestRecommendationRunModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  runId: number | null
  initialTab?: Tab
}

interface SelectedItem {
  key: string
  category?: string
  name?: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDetail(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown } } }
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(' ')
  }
  return 'Something went wrong'
}

function slugifyFilenamePart(name: string | null | undefined): string {
  if (!name) return 'requirement'
  return (
    name
      .replace(/\.[^/.]+$/, '')
      .replace(/[^a-zA-Z0-9-_]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48) || 'requirement'
  )
}

function downloadRunJson(run: TestRecommendationRun) {
  const payload = {
    exported_at: new Date().toISOString(),
    run: {
      id: run.id,
      project_id: run.project_id,
      requirement_id: run.requirement_id,
      created_by: run.created_by,
      status: run.status,
      created_at: run.created_at,
      updated_at: run.updated_at,
      requirement_title: run.requirement_title,
      requirement_file_name: run.requirement_file_name,
      result_json: run.result_json,
      error_message: run.error_message,
      pdf_path: run.pdf_path,
    },
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `test-recommendations-run-${run.id}-${slugifyFilenamePart(run.requirement_title || run.requirement_file_name)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function priorityRank(p?: string): number {
  const x = (p || '').toLowerCase()
  if (x === 'critical') return 0
  if (x === 'high') return 1
  if (x === 'medium') return 2
  return 3
}

// ---------------------------------------------------------------------------
// Priority badge
// ---------------------------------------------------------------------------

function PriorityBadge({ priority }: { priority?: string }) {
  const p = (priority || '').toLowerCase()
  const cls =
    p === 'critical'
      ? 'bg-red-100 text-red-800'
      : p === 'high'
        ? 'bg-orange-100 text-orange-800'
        : p === 'medium'
          ? 'bg-yellow-100 text-yellow-800'
          : 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${cls}`}>
      {testCasePriorityLabel(priority || '')}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Action badge (per row): shows if a category maps to functional or coming-soon
// ---------------------------------------------------------------------------

function ActionBadge({ category }: { category?: string }) {
  const action = resolveItemAction(category)
  if (action === 'functional') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <PlayIcon className="w-3 h-3" />
        Runnable
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200">
      <ClockIcon className="w-3 h-3" />
      Coming Soon
    </span>
  )
}

// ---------------------------------------------------------------------------
// HighPriorityCallout (unchanged from original)
// ---------------------------------------------------------------------------

function HighPriorityCallout({
  standard,
  recommended,
}: {
  standard: TestRecommendationStrategyItem[]
  recommended: TestRecommendationStrategyItem[]
}) {
  const all = [
    ...standard.map((r) => ({ ...r, section: 'Standard' as const })),
    ...recommended.map((r) => ({ ...r, section: 'Additional' as const })),
  ]
  const urgent = all.filter((r) => {
    const p = (r.priority || '').toLowerCase()
    return p === 'high' || p === 'critical'
  })
  if (urgent.length === 0) return null
  urgent.sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority))
  const pick = urgent.slice(0, 10)
  return (
    <div className="rounded-lg bg-white border border-amber-200/80 p-3 shadow-sm">
      <h4 className="text-sm font-semibold text-amber-950 mb-2">
        Highest priority — what to validate first
      </h4>
      <ul className="space-y-2.5 text-sm text-gray-800 list-disc pl-5 marker:text-amber-600">
        {pick.map((r, i) => (
          <li key={i} className="leading-snug">
            <span className="font-semibold text-gray-900">
              [{r.section}] {r.name}
            </span>
            {r.reason ? (
              <span className="block text-gray-700 mt-1 leading-relaxed">
                <span className="font-medium text-gray-800">Why it matters: </span>
                {r.reason}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SelectableStrategyTable — rows have checkboxes + action badge
// ---------------------------------------------------------------------------

interface SelectableStrategyTableProps {
  title: string
  items: TestRecommendationStrategyItem[]
  section: 'standard' | 'recommended'
  selectedKeys: Set<string>
  onToggle: (key: string) => void
}

function SelectableStrategyTable({
  title,
  items,
  section,
  selectedKeys,
  onToggle,
}: SelectableStrategyTableProps) {
  if (!items.length) {
    return (
      <div>
        <h4 className="text-sm font-semibold text-gray-800 mb-2">{title}</h4>
        <p className="text-sm text-gray-500">No items.</p>
      </div>
    )
  }

  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-800 mb-2">{title}</h4>
      <div className="overflow-x-auto rounded border border-gray-200">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-3 py-2 w-8" aria-label="Select" />
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Test focus</th>
              <th className="px-3 py-2">Priority</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Why it&apos;s necessary</th>
              <th className="px-3 py-2">Tailored detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((row, idx) => {
              const key = `${section}-${idx}`
              const checked = selectedKeys.has(key)
              return (
                <tr
                  key={idx}
                  className={`align-top cursor-pointer transition-colors ${
                    checked ? 'bg-amber-50/60' : 'odd:bg-white even:bg-gray-50/90 hover:bg-amber-50/30'
                  }`}
                  onClick={() => onToggle(key)}
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggle(key)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500 cursor-pointer"
                      aria-label={`Select ${row.name ?? 'test'}`}
                    />
                  </td>
                  <td className="px-3 py-2 text-gray-700">{row.category ?? '—'}</td>
                  <td className="px-3 py-2 font-medium text-gray-900">{row.name ?? '—'}</td>
                  <td className="px-3 py-2">
                    <PriorityBadge priority={row.priority} />
                  </td>
                  <td className="px-3 py-2">
                    <ActionBadge category={row.category} />
                  </td>
                  <td className="px-3 py-2 text-gray-600">{row.reason ?? '—'}</td>
                  <td className="px-3 py-2 text-gray-600 text-xs">
                    {row.detailed_guidance?.trim() ? (
                      <span className="italic text-gray-700 block whitespace-pre-wrap">
                        {row.detailed_guidance}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// AcceptLaunchBar — sticky footer shown when items are selected
// ---------------------------------------------------------------------------

interface AcceptLaunchBarProps {
  selectedItems: SelectedItem[]
  onAcceptFunctional: () => void
  onViewComingSoon: (feature: string) => void
  isDisabled: boolean
}

function AcceptLaunchBar({
  selectedItems,
  onAcceptFunctional,
  onViewComingSoon,
  isDisabled,
}: AcceptLaunchBarProps) {
  const functionalItems = selectedItems.filter((i) => resolveItemAction(i.category) === 'functional')
  const comingSoonItems = selectedItems.filter(
    (i) => resolveItemAction(i.category) === 'coming-soon'
  )

  // Deduplicate coming-soon feature names
  const comingSoonFeatures = Array.from(
    new Set(comingSoonItems.map((i) => getComingSoonFeatureName(i.category)))
  )

  if (selectedItems.length === 0) return null

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3 flex flex-wrap items-center gap-3">
      <span className="text-sm text-gray-600 font-medium">
        {selectedItems.length} test type{selectedItems.length !== 1 ? 's' : ''} selected
      </span>

      <div className="flex flex-wrap items-center gap-2 flex-1">
        {functionalItems.length > 0 && (
          <Button
            size="sm"
            onClick={onAcceptFunctional}
            disabled={isDisabled}
            className="bg-emerald-600 hover:bg-emerald-700 text-white border-0"
          >
            <PlayIcon className="w-4 h-4 mr-1.5" />
            Accept &amp; Run Functional Tests
            <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-emerald-500/40 rounded">
              {functionalItems.length}
            </span>
          </Button>
        )}

        {comingSoonFeatures.map((feature) => (
          <button
            key={feature}
            type="button"
            onClick={() => onViewComingSoon(feature)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ClockIcon className="w-3.5 h-3.5" />
            {feature}
            <ArrowRightIcon className="w-3 h-3 ml-0.5 opacity-60" />
          </button>
        ))}
      </div>

      {comingSoonFeatures.length > 0 && functionalItems.length === 0 && (
        <p className="text-xs text-slate-500 w-full">
          The selected test types are not yet available in QAstra. Click each type to see the
          upcoming roadmap.
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// FlowStep — a single step indicator in the progress panel
// ---------------------------------------------------------------------------

type StepStatus = 'waiting' | 'active' | 'done' | 'skipped'

function FlowStep({
  label,
  detail,
  status,
}: {
  label: string
  detail?: string
  status: StepStatus
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex-shrink-0">
        {status === 'done' ? (
          <CheckCircleSolid className="w-5 h-5 text-emerald-500" />
        ) : status === 'active' ? (
          <div className="w-5 h-5 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
        ) : status === 'skipped' ? (
          <CheckCircleIcon className="w-5 h-5 text-gray-300" />
        ) : (
          <div className="w-5 h-5 rounded-full border-2 border-gray-200" />
        )}
      </div>
      <div className="min-w-0">
        <p
          className={`text-sm font-medium ${
            status === 'done'
              ? 'text-emerald-700'
              : status === 'active'
                ? 'text-gray-900'
                : 'text-gray-400'
          }`}
        >
          {label}
        </p>
        {detail && status === 'active' && (
          <p className="text-xs text-gray-500 mt-0.5 truncate max-w-md">{detail}</p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// FlowProgressPanel — full-panel view during/after the accept flow
// ---------------------------------------------------------------------------

function FlowProgressPanel({
  phase,
  onRetry,
  onGoToLive,
}: {
  phase: AcceptPhase
  onRetry: () => void
  onGoToLive: () => void
}) {
  const getStepStatus = (stepPhase: AcceptPhase['type']): StepStatus => {
    const order: AcceptPhase['type'][] = [
      'checking_url',
      'fetching_stories',
      'generating',
      'promoting',
      'launching',
      'done',
    ]
    const currentIndex =
      phase.type === 'error'
        ? -1
        : order.indexOf(phase.type as AcceptPhase['type'])
    const stepIndex = order.indexOf(stepPhase)

    if (phase.type === 'error') return 'waiting'
    if (currentIndex === stepIndex) return 'active'
    if (currentIndex > stepIndex) return 'done'
    return 'waiting'
  }

  const generatingDetail =
    phase.type === 'generating'
      ? `${phase.done + 1} / ${phase.total} — ${phase.currentTitle}`
      : undefined

  const promotingDetail =
    phase.type === 'promoting' ? `Marking ${phase.count} case${phase.count !== 1 ? 's' : ''} as ready…` : undefined

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">
          {phase.type === 'done'
            ? 'Tests are running!'
            : phase.type === 'error'
              ? 'Something went wrong'
              : 'Setting up functional tests…'}
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {phase.type === 'done'
            ? 'All test cases have been generated and your run has started. Navigate to the Live tab to watch progress.'
            : phase.type === 'error'
              ? (phase as { type: 'error'; message: string }).message
              : 'This may take a moment depending on the number of user stories.'}
        </p>
      </div>

      {phase.type !== 'error' && (
        <div className="space-y-4 rounded-lg border border-gray-200 bg-gray-50/60 p-4">
          <FlowStep
            label="Verify App URL"
            status={getStepStatus('checking_url')}
          />
          <FlowStep
            label="Fetch user stories"
            status={getStepStatus('fetching_stories')}
          />
          <FlowStep
            label="Generate test cases"
            detail={generatingDetail}
            status={getStepStatus('generating')}
          />
          <FlowStep
            label="Promote cases to ready"
            detail={promotingDetail}
            status={getStepStatus('promoting')}
          />
          <FlowStep label="Start test run" status={getStepStatus('launching')} />
        </div>
      )}

      {phase.type === 'done' && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-start gap-3">
          <CheckCircleSolid className="w-6 h-6 text-emerald-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-emerald-800">Run started successfully</p>
            <p className="text-sm text-emerald-700 mt-0.5">
              All ready test cases are now executing. You&apos;ll be taken to the live view.
            </p>
            <Button
              size="sm"
              className="mt-3 bg-emerald-600 hover:bg-emerald-700 text-white border-0"
              onClick={onGoToLive}
            >
              <PlayIcon className="w-4 h-4 mr-1.5" />
              Go to Live View
            </Button>
          </div>
        </div>
      )}

      {phase.type === 'error' && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 flex items-start gap-3">
          <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-red-800">Could not complete the flow</p>
            <p className="text-sm text-red-700 mt-0.5">
              {(phase as { type: 'error'; message: string }).message}
            </p>
            <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
              Try again
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------

export default function TestRecommendationRunModal({
  isOpen,
  onClose,
  projectId,
  runId,
  initialTab = 'summary',
}: TestRecommendationRunModalProps) {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>(initialTab)
  const [run, setRun] = useState<TestRecommendationRun | null>(null)
  const [loading, setLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set())

  const { phase, accept, reset, contextRunning } = useAcceptRecommendation(projectId)

  const isFlowActive = phase.type !== 'idle'

  // ── Reset selection and flow on open/close ────────────────────────────────

  useEffect(() => {
    if (isOpen) {
      setTab(initialTab)
      setSelectedKeys(new Set())
      reset()
    }
  }, [isOpen, initialTab, runId, reset])

  // ── Auto-navigate when the flow completes ─────────────────────────────────

  useEffect(() => {
    if (phase.type === 'done') {
      const timer = setTimeout(() => {
        onClose()
        navigate(`/projects/${projectId}/functional-testing/live`)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [phase.type, projectId, navigate, onClose])

  // ── Fetch run data ────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false
    if (!isOpen || runId == null) {
      setRun(null)
      return
    }
    setLoading(true)
    setRun(null)
    ;(async () => {
      try {
        const res = await testRecommendationsApi.getRun(runId, projectId)
        if (!cancelled) setRun(res.data)
      } catch (err) {
        if (!cancelled) {
          console.error(err)
          toast.error(formatDetail(err))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, runId, projectId])

  // ── PDF loading ───────────────────────────────────────────────────────────

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    if (!isOpen || !run || tab !== 'pdf' || !run.pdf_path) {
      setPdfUrl((u) => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
      setPdfError(null)
      setPdfLoading(false)
      return
    }

    setPdfLoading(true)
    setPdfError(null)
    setPdfUrl(null)
    ;(async () => {
      try {
        const response = await testRecommendationsApi.getPdf(run.id, projectId, false)
        if (cancelled) return
        objectUrl = URL.createObjectURL(response.data)
        if (cancelled) {
          URL.revokeObjectURL(objectUrl)
          return
        }
        setPdfUrl(objectUrl)
      } catch (e) {
        if (!cancelled) {
          console.error(e)
          setPdfError('Could not load the PDF.')
          toast.error('Could not load test recommendations PDF')
        }
      } finally {
        if (!cancelled) setPdfLoading(false)
      }
    })()

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [isOpen, run, tab, projectId])

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleClose = () => {
    setPdfUrl((u) => {
      if (u) URL.revokeObjectURL(u)
      return null
    })
    reset()
    onClose()
  }

  const handleDownloadPdf = async () => {
    if (!run) return
    try {
      const response = await testRecommendationsApi.getPdf(run.id, projectId, true)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `test-recommendations-${run.id}.pdf`
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      toast.success('Download started')
    } catch (e) {
      console.error(e)
      toast.error('Download failed')
    }
  }

  const toggleKey = useCallback((key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const handleViewComingSoon = (feature: string) => {
    navigate(
      `/projects/${projectId}/coming-soon?feature=${encodeURIComponent(feature)}`
    )
    onClose()
  }

  const handleGoToLive = () => {
    onClose()
    navigate(`/projects/${projectId}/functional-testing/live`)
  }

  // ── Derive selected items list from keys ──────────────────────────────────

  const result = run?.result_json
  const standard = result?.standard_tests ?? []
  const recommended = result?.recommended_tests ?? []
  const snap = result?.input_snapshot

  const selectedItems: SelectedItem[] = Array.from(selectedKeys).map((key) => {
    const [section, idxStr] = key.split('-')
    const idx = Number(idxStr)
    const item = section === 'standard' ? standard[idx] : recommended[idx]
    return { key, category: item?.category, name: item?.name }
  })

  const hasFunctionalSelected = selectedItems.some(
    (i) => resolveItemAction(i.category) === 'functional'
  )

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/40" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-200"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-[min(calc(100vw-2rem),66rem)] max-h-[92vh] overflow-hidden rounded-lg bg-white shadow-xl flex flex-col">

              {/* ── Header ─────────────────────────────────────────────── */}
              <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-4 py-3 flex-shrink-0">
                <div className="flex items-center gap-2 min-w-0">
                  <LightBulbIcon className="w-6 h-6 text-amber-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <Dialog.Title className="text-lg font-semibold text-gray-900 truncate">
                      Testing Recommendations
                    </Dialog.Title>
                    <p className="text-xs text-gray-500 truncate">
                      Select test types below — check the ones you want, then accept to run them.
                    </p>
                    <p className="text-xs text-gray-400 truncate">
                      {run?.requirement_title || run?.requirement_file_name || 'Run detail'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {run?.status === 'completed' && !isFlowActive && (
                    <Button
                      variant="outline"
                      size="sm"
                      type="button"
                      onClick={() => setEmailDialogOpen(true)}
                      title="Email PDF report"
                    >
                      <EnvelopeIcon className="w-4 h-4 mr-1" />
                      Email
                    </Button>
                  )}
                  {tab === 'pdf' && run?.pdf_path && !isFlowActive && (
                    <Button variant="outline" size="sm" type="button" onClick={handleDownloadPdf}>
                      <ArrowDownTrayIcon className="w-4 h-4 mr-1" />
                      PDF
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={handleClose} aria-label="Close">
                    <XMarkIcon className="w-5 h-5" />
                  </Button>
                </div>
              </div>

              {/* ── Tab strip (only in summary view, not during flow) ───── */}
              {!loading && !isFlowActive && run?.status === 'completed' && result && (
                <div className="px-4 pt-3 pb-0 border-b border-gray-100 flex gap-1 flex-wrap flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => setTab('summary')}
                    className={`px-3 py-1.5 text-sm rounded-md ${
                      tab === 'summary'
                        ? 'bg-amber-100 text-amber-900 font-medium'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    Summary
                  </button>
                  <button
                    type="button"
                    onClick={() => setTab('pdf')}
                    disabled={!run.pdf_path}
                    title={run.pdf_path ? 'View PDF report' : 'PDF not available'}
                    className={`px-3 py-1.5 text-sm rounded-md ${
                      tab === 'pdf'
                        ? 'bg-amber-100 text-amber-900 font-medium'
                        : 'text-gray-600 hover:bg-gray-100'
                    } ${!run.pdf_path ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    Report PDF
                  </button>
                </div>
              )}

              {/* ── Scrollable body ─────────────────────────────────────── */}
              <div className="overflow-y-auto p-4 space-y-4 flex-1">
                {/* Loading */}
                {loading && (
                  <div className="flex justify-center py-12">
                    <Loader />
                  </div>
                )}

                {/* Run failed */}
                {!loading && run?.status === 'failed' && (
                  <div className="rounded-md bg-red-50 p-3 text-sm text-red-800 flex gap-2">
                    <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0" />
                    <span>{run.error_message || 'Run failed.'}</span>
                  </div>
                )}

                {/* Flow progress panel (replaces summary while flow is active) */}
                {isFlowActive && (
                  <FlowProgressPanel
                    phase={phase}
                    onRetry={reset}
                    onGoToLive={handleGoToLive}
                  />
                )}

                {/* Summary tab */}
                {!loading && !isFlowActive && run?.status === 'completed' && result && tab === 'summary' && (
                  <>
                    <div className="flex flex-wrap gap-2 justify-end">
                      <Button
                        variant="outline"
                        size="sm"
                        type="button"
                        onClick={() => setEmailDialogOpen(true)}
                      >
                        <EnvelopeIcon className="w-4 h-4 mr-1" />
                        Email report
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        type="button"
                        onClick={() => {
                          downloadRunJson(run)
                          toast.success('Download started')
                        }}
                      >
                        <ArrowDownTrayIcon className="w-4 h-4 mr-1" />
                        Download JSON
                      </Button>
                    </div>

                    <div className="space-y-6">
                      <div className="space-y-1">
                        <h3 className="text-2xl font-bold text-gray-900 tracking-tight">
                          Test Strategy Recommendations
                        </h3>
                        <p className="text-sm text-gray-500">
                          Select the test types you want to run using the checkboxes — then click
                          <strong className="text-gray-700"> Accept &amp; Run</strong> at the bottom.
                          Functional tests run immediately; other types will be available soon.
                        </p>
                      </div>

                      {result.detailed_report?.summary_paragraph ? (
                        <div className="bg-slate-50 border-l-4 border-amber-500 p-5 rounded-r-lg shadow-sm">
                          <h4 className="text-sm font-bold text-amber-900 uppercase tracking-wider mb-2">
                            Executive Summary
                          </h4>
                          <p className="text-gray-800 leading-relaxed text-lg italic">
                            &ldquo;{result.detailed_report.summary_paragraph}&rdquo;
                          </p>
                        </div>
                      ) : null}

                      <HighPriorityCallout standard={standard} recommended={recommended} />

                      <div className="space-y-8 pt-4">
                        <SelectableStrategyTable
                          title="Primary Test Focus Areas"
                          items={standard}
                          section="standard"
                          selectedKeys={selectedKeys}
                          onToggle={toggleKey}
                        />
                        <SelectableStrategyTable
                          title="Additional Recommended Coverage"
                          items={recommended}
                          section="recommended"
                          selectedKeys={selectedKeys}
                          onToggle={toggleKey}
                        />
                      </div>

                      {selectedKeys.size > 0 && (
                        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded px-3 py-2">
                          {selectedKeys.size} test type{selectedKeys.size !== 1 ? 's' : ''}{' '}
                          selected.{' '}
                          {hasFunctionalSelected
                            ? 'Functional tests will be generated and run immediately.'
                            : 'The selected types are not yet available — click to view their roadmap.'}
                        </p>
                      )}
                    </div>

                    {(result.warnings?.length ?? 0) > 0 && (
                      <div className="rounded-md bg-amber-50 border border-amber-100 p-3 text-sm text-amber-900 space-y-1">
                        {result.warnings!.map((w, i) => (
                          <p key={i}>{w}</p>
                        ))}
                      </div>
                    )}

                    {/* Supporting details (collapsible) */}
                    <details className="group text-sm rounded-lg border border-gray-200 bg-gray-50/80">
                      <summary className="cursor-pointer font-semibold text-gray-800 px-4 py-3 list-none flex items-center gap-2 [&::-webkit-details-marker]:hidden">
                        <span className="text-amber-700 group-open:rotate-90 transition-transform inline-block">
                          ▸
                        </span>
                        Supporting details — domain detection, gap analysis, methodology
                      </summary>
                      <div className="px-4 pb-4 pt-2 space-y-4 border-t border-gray-200">
                        {snap?.user_stories_included && snap.user_stories_included.length > 0 && (
                          <details className="text-sm rounded border border-gray-200 p-3 bg-white">
                            <summary className="cursor-pointer font-medium text-gray-800">
                              User stories included in this run ({snap.user_stories_included.length}
                              {typeof snap.user_stories_total_in_project === 'number'
                                ? ` of ${snap.user_stories_total_in_project} in project`
                                : ''}
                              )
                            </summary>
                            <ul className="mt-2 space-y-1 text-gray-600 list-disc pl-5 max-h-40 overflow-y-auto">
                              {snap.user_stories_included.map((s, i) => (
                                <li key={s.id ?? i}>
                                  <span className="font-mono text-xs">
                                    {s.external_key || `#${s.id}`}
                                  </span>
                                  {s.title ? ` — ${s.title}` : ''}
                                </li>
                              ))}
                            </ul>
                          </details>
                        )}

                        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm text-gray-600">Detected domain</span>
                            <span className="font-semibold text-gray-900">
                              {result.domain_label || result.domain_id || '—'}
                            </span>
                            <span className="text-xs px-2 py-0.5 rounded bg-gray-50 text-gray-600 border border-gray-200">
                              {result.domain_id}
                            </span>
                          </div>
                          <div className="text-sm text-gray-600">
                            Confidence:{' '}
                            <span className="font-medium text-gray-900">
                              {typeof result.confidence === 'number'
                                ? `${(result.confidence * 100).toFixed(0)}%`
                                : '—'}
                            </span>
                            {' · '}
                            Source:{' '}
                            <span className="font-medium text-gray-900">
                              {result.source || '—'}
                            </span>
                          </div>
                          {(result.intent_summary || result.llm_fallback?.intent_summary) && (
                            <div className="rounded border border-blue-100 bg-blue-50/80 p-3 text-sm text-gray-800">
                              <span className="font-medium text-gray-900">Product intent</span>
                              <p className="mt-1 text-gray-700">
                                {result.intent_summary || result.llm_fallback?.intent_summary}
                              </p>
                            </div>
                          )}
                          {result.report_summary && (
                            <p className="text-xs text-gray-600">{result.report_summary}</p>
                          )}
                          {result.llm_fallback?.rationale && (
                            <p className="text-xs text-gray-600">
                              Domain rationale: {result.llm_fallback.rationale}
                            </p>
                          )}
                          {result.llm_fallback?.error && (
                            <p className="text-xs text-amber-800">
                              {result.source === 'keyword_fallback'
                                ? 'LLM classification failed (keyword matching used): '
                                : 'LLM note failed: '}
                              {result.llm_fallback.error}
                            </p>
                          )}
                        </div>

                        {result.local_classification?.evidence &&
                          Object.keys(result.local_classification.evidence).length > 0 && (
                            <details className="text-sm rounded border border-gray-200 p-3 bg-white">
                              <summary className="cursor-pointer font-medium text-gray-800">
                                Keyword evidence
                              </summary>
                              <ul className="mt-2 space-y-1 text-gray-600 list-disc pl-5">
                                {Object.entries(result.local_classification.evidence).map(
                                  ([dom, terms]) => (
                                    <li key={dom}>
                                      <span className="font-medium text-gray-800">{dom}</span>
                                      {': '}
                                      {terms && terms.length ? terms.join(', ') : '—'}
                                    </li>
                                  )
                                )}
                              </ul>
                            </details>
                          )}

                        {result.playbook_merge_note && (
                          <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-800">
                            <h4 className="font-semibold text-gray-900 mb-1">
                              How this playbook is built
                            </h4>
                            <p className="text-gray-700 leading-relaxed">
                              {result.playbook_merge_note.replace(/\*\*/g, '')}
                            </p>
                          </div>
                        )}

                        {result.gap_analysis_snapshot && (
                          <div className="rounded-lg border border-gray-200 p-4 text-sm space-y-2 bg-white">
                            <h4 className="font-semibold text-gray-900">{GAP_ANALYSIS_LABEL} Context</h4>
                            <p className="text-xs text-gray-500">
                              Run #{result.gap_analysis_snapshot.gap_analysis_run_id ?? '—'} ·
                              Coverage:{' '}
                              {result.gap_analysis_snapshot.coverage_estimate_percent != null
                                ? `${result.gap_analysis_snapshot.coverage_estimate_percent}%`
                                : '—'}{' '}
                              · Gaps: {result.gap_analysis_snapshot.gaps_count ?? '—'} · Suggested
                              stories:{' '}
                              {result.gap_analysis_snapshot.suggested_stories_count ?? '—'}
                            </p>
                            {result.gap_analysis_snapshot.summary && (
                              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                                {result.gap_analysis_snapshot.summary}
                              </p>
                            )}
                            {result.gap_analysis_snapshot.suggested_user_stories_preview &&
                              result.gap_analysis_snapshot.suggested_user_stories_preview.length >
                                0 && (
                                <details className="text-xs text-gray-600">
                                  <summary className="cursor-pointer font-medium text-gray-800">
                                    Suggested stories (
                                    {
                                      result.gap_analysis_snapshot.suggested_user_stories_preview
                                        .length
                                    }
                                    )
                                  </summary>
                                  <ul className="mt-2 space-y-2 list-disc pl-5">
                                    {result.gap_analysis_snapshot.suggested_user_stories_preview.map(
                                      (s, i) => (
                                        <li key={i}>
                                          <span className="font-medium text-gray-800">
                                            {s.title}
                                          </span>
                                          {s.rationale ? (
                                            <p className="text-gray-600 mt-0.5">{s.rationale}</p>
                                          ) : null}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                </details>
                              )}
                            {result.gap_analysis_snapshot.notes_excerpt ? (
                              <p className="text-xs text-gray-500 border-t border-gray-100 pt-2">
                                Notes: {result.gap_analysis_snapshot.notes_excerpt}
                              </p>
                            ) : null}
                          </div>
                        )}

                        {result.detailed_report?.summary_paragraph && (
                          <div className="rounded-lg border border-blue-100 bg-blue-50/40 p-4 text-sm">
                            <h4 className="font-semibold text-gray-900 mb-2">
                              Recommendation Summary
                            </h4>
                            <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                              {result.detailed_report.summary_paragraph}
                            </p>
                          </div>
                        )}

                        {result.detail_llm_error && (
                          <p className="text-xs text-amber-800 bg-amber-50/80 border border-amber-100 rounded p-2">
                            Detailed narrative could not be fully generated: {result.detail_llm_error}
                          </p>
                        )}
                      </div>
                    </details>
                  </>
                )}

                {/* PDF tab */}
                {!loading && !isFlowActive && run?.status === 'completed' && tab === 'pdf' && (
                  <div className="space-y-2">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        type="button"
                        onClick={() => setEmailDialogOpen(true)}
                      >
                        <EnvelopeIcon className="w-4 h-4 mr-1" />
                        Email report
                      </Button>
                      {run?.pdf_path && (
                        <Button variant="outline" size="sm" type="button" onClick={handleDownloadPdf}>
                          <ArrowDownTrayIcon className="w-4 h-4 mr-1" />
                          Download PDF
                        </Button>
                      )}
                    </div>
                    <div className="min-h-[480px] border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
                      {pdfLoading && (
                        <div className="flex justify-center py-16">
                          <Loader />
                        </div>
                      )}
                      {pdfError && <p className="p-4 text-sm text-red-600">{pdfError}</p>}
                      {!run.pdf_path && !pdfLoading && (
                        <p className="p-4 text-sm text-gray-600">
                          No PDF was generated for this run.
                        </p>
                      )}
                      {pdfUrl && !pdfLoading && (
                        <iframe
                          title="Test recommendations PDF"
                          src={pdfUrl}
                          className="w-full h-[70vh] bg-white"
                        />
                      )}
                    </div>
                  </div>
                )}

                {!loading && !run && runId != null && (
                  <p className="text-sm text-gray-500 text-center py-8">Could not load run.</p>
                )}
              </div>

              {/* ── Sticky action bar (summary tab, items selected, no active flow) ── */}
              {!loading &&
                !isFlowActive &&
                run?.status === 'completed' &&
                tab === 'summary' &&
                selectedKeys.size > 0 && (
                  <AcceptLaunchBar
                    selectedItems={selectedItems}
                    onAcceptFunctional={accept}
                    onViewComingSoon={handleViewComingSoon}
                    isDisabled={contextRunning}
                  />
                )}
            </Dialog.Panel>
          </Transition.Child>
        </div>

        <EmailReportDialog
          isOpen={emailDialogOpen}
          onClose={() => setEmailDialogOpen(false)}
          projectId={projectId}
          runId={runId}
          kind="testRec"
          reportLabel="testing recommendations report"
        />
      </Dialog>
    </Transition>
  )
}
