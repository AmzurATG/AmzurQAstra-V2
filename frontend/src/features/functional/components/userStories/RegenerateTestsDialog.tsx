import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'

type Props = {
  isOpen: boolean
  storyLabel: string
  isLoading: boolean
  onClose: () => void
  onConfirm: () => void
}

export function RegenerateTestsDialog({
  isOpen,
  storyLabel,
  isLoading,
  onClose,
  onConfirm,
}: Props) {
  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => !isLoading && onClose()}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" />
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
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-xl bg-white p-6 shadow-xl">
                <div className="flex items-start gap-3">
                  <ExclamationTriangleIcon
                    className="h-6 w-6 shrink-0 text-amber-500"
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Regenerate test cases?
                    </Dialog.Title>
                    <p className="mt-2 text-sm text-gray-600">
                      This removes AI-generated test cases for{' '}
                      <span className="font-medium text-gray-800">{storyLabel}</span> and creates new
                      ones. Manually added test cases are kept. This cannot be undone.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={isLoading}
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-50"
                    aria-label="Close"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>
                <div className="mt-6 flex justify-end gap-3">
                  <Button variant="outline" onClick={onClose} disabled={isLoading}>
                    Cancel
                  </Button>
                  <Button variant="primary" onClick={onConfirm} isLoading={isLoading}>
                    Regenerate
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
