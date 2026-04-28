import { Fragment, useEffect, useState, type FormEvent } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { EnvelopeIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { gapAnalysisApi, testRecommendationsApi } from '../api'
import toast from 'react-hot-toast'

export type ReportEmailKind = 'gap' | 'testRec'

function formatDetail(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown } } }
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(' ')
  }
  return 'Something went wrong'
}

interface EmailReportDialogProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  runId: number | null
  kind: ReportEmailKind
  reportLabel: string
}

export default function EmailReportDialog({
  isOpen,
  onClose,
  projectId,
  runId,
  kind,
  reportLabel,
}: EmailReportDialogProps) {
  const [email, setEmail] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (!isOpen) setEmail('')
  }, [isOpen])

  const handleClose = () => {
    if (!sending) onClose()
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const trimmed = email.trim()
    if (!trimmed) {
      toast.error('Enter a recipient email address')
      return
    }
    if (runId == null) {
      toast.error('No run is selected. Close this dialog and open the report again.')
      return
    }
    setSending(true)
    try {
      if (kind === 'gap') {
        await gapAnalysisApi.emailReport(runId, projectId, trimmed)
      } else {
        await testRecommendationsApi.emailReport(runId, projectId, trimmed)
      }
      toast.success('Report emailed successfully')
      onClose()
    } catch (err) {
      console.error(err)
      toast.error(formatDetail(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-[60]" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md rounded-xl bg-white shadow-xl border border-gray-200">
                <div className="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4">
                  <div className="flex items-center gap-2 min-w-0">
                    <EnvelopeIcon className="w-5 h-5 text-indigo-600 shrink-0" />
                    <Dialog.Title className="text-base font-semibold text-gray-900">
                      Email {reportLabel}
                    </Dialog.Title>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-40"
                    onClick={handleClose}
                    disabled={sending}
                    aria-label="Close"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
                <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
                  <p className="text-sm text-gray-600">
                    The formal report PDF will be sent as an attachment to the address you enter below.
                  </p>
                  <div>
                    <label htmlFor="report-email-to" className="block text-sm font-medium text-gray-700 mb-1">
                      Recipient email
                    </label>
                    <input
                      id="report-email-to"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(ev) => setEmail(ev.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="name@company.com"
                      disabled={sending}
                      required
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-1">
                    <Button type="button" variant="outline" onClick={handleClose} disabled={sending}>
                      Cancel
                    </Button>
                    <Button type="submit" isLoading={sending}>
                      Send
                    </Button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
