import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  XMarkIcon,
  ArrowDownTrayIcon,
  DocumentMagnifyingGlassIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { Loader } from '@common/components/ui/Loader'
import { gapAnalysisApi } from '../api'
import type { GapAnalysisRun } from '../types'
import {
  getAcceptedIndicesForRun,
  recordAcceptedSuggestion,
} from '../utils/gapAnalysisAcceptedStorage'
import toast from 'react-hot-toast'

type Tab = 'summary' | 'pdf'

interface GapAnalysisRunModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  runId: number | null
  initialTab?: Tab
  onAccepted?: () => void
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

export default function GapAnalysisRunModal({
  isOpen,
  onClose,
  projectId,
  runId,
  initialTab = 'summary',
  onAccepted,
}: GapAnalysisRunModalProps) {
  const [tab, setTab] = useState<Tab>(initialTab)
  const [run, setRun] = useState<GapAnalysisRun | null>(null)
  const [loading, setLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [acceptingIndex, setAcceptingIndex] = useState<number | null>(null)
  const [dismissed, setDismissed] = useState<Set<number>>(() => new Set())
  const [acceptedIndices, setAcceptedIndices] = useState<Set<number>>(() => new Set())

  useEffect(() => {
    if (isOpen) setTab(initialTab)
  }, [isOpen, initialTab, runId])

  useEffect(() => {
    let cancelled = false
    if (!isOpen || runId == null) {
      setRun(null)
      setDismissed(new Set())
      setAcceptedIndices(new Set())
      return
    }
    setLoading(true)
    setRun(null)
    ;(async () => {
      try {
        const res = await gapAnalysisApi.getRun(runId, projectId)
        if (!cancelled) {
          setRun(res.data)
          setAcceptedIndices(getAcceptedIndicesForRun(runId))
        }
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
        const response = await gapAnalysisApi.getPdf(run.id, projectId, false)
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
          toast.error('Could not load gap analysis PDF')
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
      const response = await gapAnalysisApi.getPdf(run.id, projectId, true)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `gap-analysis-${run.id}.pdf`
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

  const handleAccept = async (index: number) => {
    if (!run) return
    setAcceptingIndex(index)
    try {
      const res = await gapAnalysisApi.acceptSuggestions(run.id, projectId, [index])
      const { created, errors } = res.data
      if (created > 0) {
        toast.success(created === 1 ? 'User story created' : `${created} user stories created`)
        recordAcceptedSuggestion(run.id, index)
        setAcceptedIndices((prev) => new Set(prev).add(index))
        onAccepted?.()
        const next = await gapAnalysisApi.getRun(run.id, projectId)
        setRun(next.data)
      }
      if (errors?.length) {
        toast.error(errors.join(' '))
      }
    } catch (err) {
      console.error(err)
      toast.error(formatDetail(err))
    } finally {
      setAcceptingIndex(null)
    }
  }

  const suggestions = run?.result_json?.suggested_user_stories ?? []
  const gaps = run?.result_json?.gaps ?? []
  const title =
    run?.requirement_title ||
    run?.requirement_file_name ||
    (run ? `Requirement #${run.requirement_id}` : 'Gap analysis')

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/40" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 sm:p-6">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-xl bg-white shadow-xl transition-all flex flex-col max-h-[90vh]">
                <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4 shrink-0">
                  <div className="min-w-0 flex-1">
                    <Dialog.Title className="text-lg font-semibold text-gray-900 truncate flex items-center gap-2">
                      <DocumentMagnifyingGlassIcon className="w-5 h-5 text-indigo-600 shrink-0" />
                      {title}
                    </Dialog.Title>
                    {run && (
                      <p className="text-sm text-gray-500 mt-0.5">
                        Run #{run.id} ·{' '}
                        {new Date(run.created_at).toLocaleString(undefined, {
                          dateStyle: 'medium',
                          timeStyle: 'short',
                        })}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={handleClose}
                    className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                    aria-label="Close"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {run && (
                  <div className="border-b border-gray-100 px-6 flex gap-1">
                    <button
                      type="button"
                      onClick={() => setTab('summary')}
                      className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
                        tab === 'summary'
                          ? 'border-indigo-600 text-indigo-700'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Summary & suggestions
                    </button>
                    <button
                      type="button"
                      onClick={() => setTab('pdf')}
                      disabled={!run.pdf_path}
                      className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px disabled:opacity-40 disabled:cursor-not-allowed ${
                        tab === 'pdf'
                          ? 'border-indigo-600 text-indigo-700'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      PDF report
                    </button>
                  </div>
                )}

                <div className="flex-1 overflow-y-auto min-h-0 px-6 py-4">
                  {loading && (
                    <div className="flex flex-col items-center justify-center py-16 gap-3">
                      <Loader size="lg" />
                      <p className="text-sm text-gray-500">Loading run…</p>
                    </div>
                  )}

                  {!loading && run && tab === 'summary' && (
                    <div className="space-y-6">
                      {run.status === 'failed' && run.error_message && (
                        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 flex gap-2">
                          <ExclamationCircleIcon className="w-5 h-5 shrink-0" />
                          <span>{run.error_message}</span>
                        </div>
                      )}

                      {run.result_json?._export_warnings?.length ? (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                          {run.result_json._export_warnings.join(' ')}
                        </div>
                      ) : null}

                      {run.result_json?.summary && (
                        <section>
                          <h3 className="text-sm font-semibold text-gray-900 mb-2">Summary</h3>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">
                            {run.result_json.summary}
                          </p>
                          {run.result_json.coverage_estimate_percent != null && (
                            <p className="text-xs text-gray-500 mt-2">
                              Estimated coverage: {run.result_json.coverage_estimate_percent}%
                            </p>
                          )}
                        </section>
                      )}

                      {gaps.length > 0 && (
                        <section>
                          <h3 className="text-sm font-semibold text-gray-900 mb-2">Gaps</h3>
                          <ul className="space-y-2">
                            {gaps.map((g, i) => (
                              <li
                                key={i}
                                className="text-sm border border-gray-100 rounded-lg p-3 bg-gray-50/80"
                              >
                                {g.type && g.type !== 'unknown' && (
                                  <span className="text-xs font-medium text-indigo-600 uppercase">
                                    {g.type}
                                  </span>
                                )}
                                <p className="text-gray-800 mt-1">{g.detail}</p>
                                {g.related_story_key && (
                                  <p className="text-xs text-gray-500 mt-1">
                                    Story: {g.related_story_key}
                                  </p>
                                )}
                              </li>
                            ))}
                          </ul>
                        </section>
                      )}

                      {run.result_json?.notes && (
                        <section>
                          <h3 className="text-sm font-semibold text-gray-900 mb-2">Notes</h3>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">
                            {run.result_json.notes}
                          </p>
                        </section>
                      )}

                      <section>
                        <h3 className="text-sm font-semibold text-gray-900 mb-3">
                          Suggested user stories
                        </h3>
                        {suggestions.length === 0 ? (
                          <p className="text-sm text-gray-500">No suggestions in this run.</p>
                        ) : (
                          <ul className="space-y-3">
                            {suggestions.map((s, index) => {
                              if (dismissed.has(index)) return null
                              const added = acceptedIndices.has(index)
                              return (
                                <li
                                  key={index}
                                  className="border border-gray-200 rounded-lg p-4 space-y-2"
                                >
                                  <p className="font-medium text-gray-900">{s.title}</p>
                                  {s.description && (
                                    <p className="text-sm text-gray-600 whitespace-pre-wrap">
                                      {s.description}
                                    </p>
                                  )}
                                  {s.acceptance_criteria && (
                                    <div>
                                      <p className="text-xs font-medium text-gray-500 uppercase">
                                        Acceptance criteria
                                      </p>
                                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                                        {s.acceptance_criteria}
                                      </p>
                                    </div>
                                  )}
                                  {s.rationale && (
                                    <p className="text-xs text-gray-500 italic">{s.rationale}</p>
                                  )}
                                  <div className="flex gap-2 pt-1">
                                    {added ? (
                                      <Button size="sm" variant="outline" disabled>
                                        Added
                                      </Button>
                                    ) : (
                                      <Button
                                        size="sm"
                                        onClick={() => handleAccept(index)}
                                        isLoading={acceptingIndex === index}
                                        disabled={acceptingIndex !== null}
                                      >
                                        Accept
                                      </Button>
                                    )}
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() =>
                                        setDismissed((prev) => new Set(prev).add(index))
                                      }
                                      disabled={acceptingIndex !== null || added}
                                    >
                                      Dismiss
                                    </Button>
                                  </div>
                                </li>
                              )
                            })}
                          </ul>
                        )}
                      </section>
                    </div>
                  )}

                  {!loading && run && tab === 'pdf' && (
                    <div className="space-y-3">
                      <div className="flex justify-end">
                        <Button variant="outline" size="sm" onClick={handleDownloadPdf}>
                          <ArrowDownTrayIcon className="w-4 h-4 mr-1.5" />
                          Download
                        </Button>
                      </div>
                      <div className="rounded-lg border border-gray-200 bg-gray-100 overflow-hidden min-h-[420px]">
                        {pdfLoading && (
                          <div className="flex flex-col items-center justify-center py-24 gap-3">
                            <Loader size="lg" />
                            <p className="text-sm text-gray-500">Loading PDF…</p>
                          </div>
                        )}
                        {pdfError && (
                          <div className="flex flex-col items-center justify-center py-16 px-4 text-center text-sm text-gray-700">
                            {pdfError}
                          </div>
                        )}
                        {!pdfLoading && !pdfError && pdfUrl && (
                          <iframe
                            title="Gap analysis PDF"
                            src={pdfUrl}
                            className="w-full h-[70vh] border-0 bg-white"
                          />
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
