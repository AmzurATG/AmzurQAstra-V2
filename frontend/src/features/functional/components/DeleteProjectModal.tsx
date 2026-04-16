import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'

interface DeleteProjectModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: number
  projectName: string
  onConfirm: () => Promise<void>
}

export default function DeleteProjectModal({
  isOpen,
  onClose,
  projectId,
  projectName,
  onConfirm,
}: DeleteProjectModalProps) {
  const [confirmText, setConfirmText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)

  const trimmed = projectName.trim()
  const useName = trimmed.length > 0
  const expectedLabel = useName ? trimmed : String(projectId)
  const matches = useName
    ? confirmText.trim() === trimmed
    : confirmText.trim() === String(projectId)

  useEffect(() => {
    if (!isOpen) {
      setConfirmText('')
      setIsDeleting(false)
    }
  }, [isOpen])

  const handleConfirm = async () => {
    if (!matches || isDeleting) return
    setIsDeleting(true)
    try {
      await onConfirm()
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => !isDeleting && onClose()}>
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
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-xl bg-white p-6 shadow-2xl transition-all">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100">
                      <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
                    </div>
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-gray-900">
                        Delete project
                      </Dialog.Title>
                      <p className="mt-2 text-sm text-gray-600">
                        This removes the project from your workspace. Test data stays in the system but
                        this project will no longer appear in your list. This cannot be undone from
                        the UI.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                    onClick={onClose}
                    disabled={isDeleting}
                    aria-label="Close"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                <p className="mt-4 text-sm font-medium text-gray-900">
                  Type{' '}
                  <span className="font-mono text-primary-700">{expectedLabel}</span> to confirm:
                </p>
                <input
                  type="text"
                  className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Project name"
                  disabled={isDeleting}
                  autoComplete="off"
                />

                <div className="mt-6 flex justify-end gap-2">
                  <Button variant="outline" onClick={onClose} disabled={isDeleting}>
                    Cancel
                  </Button>
                  <Button
                    variant="danger"
                    onClick={handleConfirm}
                    disabled={!matches || isDeleting}
                    isLoading={isDeleting}
                  >
                    Delete project
                  </Button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
