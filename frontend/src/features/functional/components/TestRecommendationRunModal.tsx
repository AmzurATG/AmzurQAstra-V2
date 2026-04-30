import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  XMarkIcon,
  LightBulbIcon,
  ExclamationTriangleIcon,
  ArrowDownTrayIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { Loader } from '@common/components/ui/Loader'
import { testRecommendationsApi } from '../api'
import type { TestRecommendationRun, TestRecommendationStrategyItem } from '../types'
import EmailReportDialog from './EmailReportDialog'
import toast from 'react-hot-toast'

type Tab = 'summary' | 'pdf'

interface TestRecommendationRunModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  runId: number | null
  initialTab?: Tab
}

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
  return name
    .replace(/\.[^/.]+$/, '')
    .replace(/[^a-zA-Z0-9-_]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'requirement'
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
  const text = JSON.stringify(payload, null, 2)
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const base = slugifyFilenamePart(run.requirement_title || run.requirement_file_name)
  a.href = url
  a.download = `test-recommendations-run-${run.id}-${base}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function StrategyTable({
  title,
  items,
}: {
  title: string
  items: TestRecommendationStrategyItem[]
}) {
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
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Test focus</th>
              <th className="px-3 py-2">Priority</th>
              <th className="px-3 py-2">Why</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((row, idx) => (
              <tr key={idx} className="bg-white">
                <td className="px-3 py-2 text-gray-700">{row.category ?? '—'}</td>
                <td className="px-3 py-2 font-medium text-gray-900">{row.name ?? '—'}</td>
                <td className="px-3 py-2 text-gray-600 capitalize">{row.priority ?? '—'}</td>
                <td className="px-3 py-2 text-gray-600">{row.reason ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function TestRecommendationRunModal({
  isOpen,
  onClose,
  projectId,
  runId,
  initialTab = 'summary',
}: TestRecommendationRunModalProps) {
  const [tab, setTab] = useState<Tab>(initialTab)
  const [run, setRun] = useState<TestRecommendationRun | null>(null)
  const [loading, setLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)

  useEffect(() => {
    if (isOpen) setTab(initialTab)
  }, [isOpen, initialTab, runId])

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

  const handleClose = () => {
    setPdfUrl((u) => {
      if (u) URL.revokeObjectURL(u)
      return null
    })
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

  const result = run?.result_json
  const standard = result?.standard_tests ?? []
  const recommended = result?.recommended_tests ?? []
  const snap = result?.input_snapshot

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
            <Dialog.Panel className="w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg bg-white shadow-xl flex flex-col">
              <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                  <LightBulbIcon className="w-6 h-6 text-amber-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <Dialog.Title className="text-lg font-semibold text-gray-900 truncate">
                      Testing recommendations
                    </Dialog.Title>
                    <p className="text-xs text-gray-500 truncate">
                      Domain playbook — same PDF report style family as gap analysis
                    </p>
                    <p className="text-xs text-gray-400 truncate">
                      {run?.requirement_title || run?.requirement_file_name || 'Run detail'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {run?.status === 'completed' && (
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
                  {tab === 'pdf' && run?.pdf_path && (
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

              {!loading && run?.status === 'completed' && result && (
                <div className="px-4 pt-3 border-b border-gray-100 flex gap-1 flex-wrap">
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

              <div className="overflow-y-auto p-4 space-y-4 flex-1">
                {loading && (
                  <div className="flex justify-center py-12">
                    <Loader />
                  </div>
                )}

                {!loading && run?.status === 'failed' && (
                  <div className="rounded-md bg-red-50 p-3 text-sm text-red-800 flex gap-2">
                    <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0" />
                    <span>{run.error_message || 'Run failed.'}</span>
                  </div>
                )}

                {!loading && run?.status === 'completed' && result && tab === 'summary' && (
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

                    {snap?.user_stories_included && snap.user_stories_included.length > 0 && (
                      <details className="text-sm rounded border border-gray-200 p-3">
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
                              <span className="font-mono text-xs">{s.external_key || `#${s.id}`}</span>
                              {s.title ? ` — ${s.title}` : ''}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}

                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm text-gray-600">Detected domain</span>
                        <span className="font-semibold text-gray-900">
                          {result.domain_label || result.domain_id || '—'}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-white text-gray-600 border border-gray-200">
                          {result.domain_id}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        Confidence:{' '}
                        <span className="font-medium text-gray-900">
                          {typeof result.confidence === 'number' ? `${(result.confidence * 100).toFixed(0)}%` : '—'}
                        </span>
                        {' · '}
                        Source: <span className="font-medium text-gray-900">{result.source || '—'}</span>
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
                        <p className="text-xs text-gray-600">Domain rationale: {result.llm_fallback.rationale}</p>
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
                        <details className="text-sm rounded border border-gray-200 p-3">
                          <summary className="cursor-pointer font-medium text-gray-800">Keyword evidence</summary>
                          <ul className="mt-2 space-y-1 text-gray-600 list-disc pl-5">
                            {Object.entries(result.local_classification.evidence).map(([dom, terms]) => (
                              <li key={dom}>
                                <span className="font-medium text-gray-800">{dom}</span>
                                {': '}
                                {terms && terms.length ? terms.join(', ') : '—'}
                              </li>
                            ))}
                          </ul>
                        </details>
                      )}

                    {(result.warnings?.length ?? 0) > 0 && (
                      <div className="rounded-md bg-amber-50 border border-amber-100 p-3 text-sm text-amber-900 space-y-1">
                        {result.warnings!.map((w, i) => (
                          <p key={i}>{w}</p>
                        ))}
                      </div>
                    )}

                    <StrategyTable title="Standard tests" items={standard} />
                    <StrategyTable title="Additional recommendations" items={recommended} />
                  </>
                )}

                {!loading && run?.status === 'completed' && tab === 'pdf' && (
                  <div className="space-y-2">
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" type="button" onClick={() => setEmailDialogOpen(true)}>
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
                      <p className="p-4 text-sm text-gray-600">No PDF was generated for this run.</p>
                    )}
                    {pdfUrl && !pdfLoading && (
                      <iframe title="Test recommendations PDF" src={pdfUrl} className="w-full h-[70vh] bg-white" />
                    )}
                  </div>
                  </div>
                )}

                {!loading && !run && runId != null && (
                  <p className="text-sm text-gray-500 text-center py-8">Could not load run.</p>
                )}
              </div>
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
