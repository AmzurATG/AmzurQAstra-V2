import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  XMarkIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { Loader } from '@common/components/ui/Loader'
import { requirementsApi } from '../api'
import type { Requirement } from '../types'
import {
  canBrowserPreviewPdf,
  isPlainTextRequirement,
  isWordRequirement,
} from '../utils/requirementPreview'
import toast from 'react-hot-toast'

interface RequirementPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  requirement: Requirement | null
}

type LoadState = 'idle' | 'loading' | 'ready' | 'error'

export default function RequirementPreviewModal({
  isOpen,
  onClose,
  requirement,
}: RequirementPreviewModalProps) {
  const [pdfState, setPdfState] = useState<LoadState>('idle')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    if (!isOpen || !requirement) {
      setPdfState('idle')
      setLoadError(null)
      setPdfUrl(null)
      return
    }

    if (!requirement.file_path) {
      setPdfState('ready')
      setPdfUrl(null)
      return
    }

    if (!canBrowserPreviewPdf(requirement)) {
      setPdfState('ready')
      setPdfUrl(null)
      return
    }

    setPdfState('loading')
    setLoadError(null)
    setPdfUrl(null)

    ;(async () => {
      try {
        const response = await requirementsApi.getFile(requirement.id)
        if (cancelled) return
        objectUrl = URL.createObjectURL(response.data)
        if (cancelled) {
          URL.revokeObjectURL(objectUrl)
          objectUrl = null
          return
        }
        setPdfUrl(objectUrl)
        setPdfState('ready')
      } catch (e: unknown) {
        if (cancelled) return
        console.error(e)
        setLoadError('Could not load the file for preview.')
        setPdfState('error')
        toast.error('Could not load document preview')
      }
    })()

    return () => {
      cancelled = true
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
      setPdfUrl(null)
    }
  }, [isOpen, requirement])

  const handleClose = () => {
    setPdfState('idle')
    setLoadError(null)
    onClose()
  }

  const handleDownload = async () => {
    if (!requirement?.file_path) {
      toast.error('No file to download')
      return
    }
    try {
      const response = await requirementsApi.getFile(requirement.id)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = requirement.file_name || 'requirement-document'
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      toast.success('Download started')
    } catch {
      toast.error('Download failed')
    }
  }

  const showTextBody =
    requirement &&
    (isWordRequirement(requirement) ||
      isPlainTextRequirement(requirement) ||
      (!canBrowserPreviewPdf(requirement) && requirement.content))

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
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-xl bg-white shadow-xl transition-all flex flex-col max-h-[90vh]">
                <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4 shrink-0">
                  <div className="min-w-0 flex-1">
                    <Dialog.Title className="text-lg font-semibold text-gray-900 truncate">
                      {requirement?.title || 'Document'}
                    </Dialog.Title>
                    {requirement?.file_name && (
                      <p className="text-sm text-gray-500 truncate mt-0.5">{requirement.file_name}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {requirement?.file_path && (
                      <Button variant="outline" size="sm" onClick={handleDownload}>
                        <ArrowDownTrayIcon className="w-4 h-4 mr-1.5" />
                        Download
                      </Button>
                    )}
                    <button
                      type="button"
                      onClick={handleClose}
                      className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      aria-label="Close"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto min-h-0 px-6 py-4">
                  {!requirement ? null : !requirement.file_path && requirement.content ? (
                    <article className="rounded-lg border border-gray-100 bg-gray-50/80 p-4 max-h-[70vh] overflow-y-auto">
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                        Extracted text
                      </p>
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
                        {requirement.content}
                      </pre>
                    </article>
                  ) : canBrowserPreviewPdf(requirement) ? (
                    <div className="rounded-lg border border-gray-200 bg-gray-100 overflow-hidden min-h-[420px]">
                      {pdfState === 'loading' && (
                        <div className="flex flex-col items-center justify-center py-24 gap-3">
                          <Loader size="lg" />
                          <p className="text-sm text-gray-500">Loading PDF preview…</p>
                        </div>
                      )}
                      {pdfState === 'error' && loadError && (
                        <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
                          <ExclamationCircleIcon className="w-12 h-12 text-amber-500 mb-2" />
                          <p className="text-sm text-gray-700">{loadError}</p>
                          {requirement.content && (
                            <div className="mt-6 w-full text-left rounded-lg border border-gray-200 bg-white p-4 max-h-[50vh] overflow-y-auto">
                              <p className="text-xs font-medium text-gray-500 mb-2">Extracted text</p>
                              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                                {requirement.content}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                      {pdfState === 'ready' && pdfUrl && (
                        <iframe
                          title="PDF preview"
                          src={pdfUrl}
                          className="w-full h-[70vh] border-0 bg-white"
                        />
                      )}
                    </div>
                  ) : showTextBody && requirement.content ? (
                    <div className="space-y-3">
                      {isWordRequirement(requirement) && (
                        <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 text-sm text-amber-900">
                          <DocumentTextIcon className="w-5 h-5 shrink-0 mt-0.5" />
                          <p>
                            Word documents are shown as <strong>extracted text</strong> (same text used for
                            test generation). Layout and images are not preserved in the browser.
                          </p>
                        </div>
                      )}
                      <article className="rounded-lg border border-gray-100 bg-gray-50/80 p-4 max-h-[70vh] overflow-y-auto">
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                          {isPlainTextRequirement(requirement) ? 'Document' : 'Extracted text'}
                        </p>
                        <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
                          {requirement.content}
                        </pre>
                      </article>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-gray-500 text-sm">
                      <p>No preview is available for this format.</p>
                      {requirement.file_path && (
                        <Button className="mt-4" variant="outline" onClick={handleDownload}>
                          <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
                          Download file
                        </Button>
                      )}
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
