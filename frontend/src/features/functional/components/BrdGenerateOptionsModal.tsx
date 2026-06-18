import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'

type Props = {
  isOpen: boolean
  onClose: () => void
  onConfirm: (maxStories: number, includeUiContext: boolean) => void
  hasUiDiscovery: boolean
  uiDiscoveryStale?: boolean
  isLoading?: boolean
}

export default function BrdGenerateOptionsModal({
  isOpen,
  onClose,
  onConfirm,
  hasUiDiscovery,
  uiDiscoveryStale = false,
  isLoading = false,
}: Props) {
  const [maxStories, setMaxStories] = useState(hasUiDiscovery ? 40 : 20)
  const [includeUiContext, setIncludeUiContext] = useState(hasUiDiscovery)

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" />
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
              <Dialog.Panel className="w-full max-w-md transform rounded-xl bg-white p-6 shadow-xl transition-all">
                <div className="flex items-start justify-between mb-4">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    Generate User Stories from BRD
                  </Dialog.Title>
                  <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600">
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-5">
                  <p className="text-sm text-gray-600">
                    Configure story generation. UI context merges discovered pages and labels into
                    modules and acceptance criteria.
                  </p>

                  {!hasUiDiscovery && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      No UI discovery inventory found. Run UI Discovery on Integrity Check first.
                    </div>
                  )}

                  {hasUiDiscovery && uiDiscoveryStale && (
                    <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-900">
                      UI discovery is older than 7 days — consider re-running discovery.
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max stories: {maxStories}
                    </label>
                    <input
                      type="range"
                      min={10}
                      max={60}
                      step={5}
                      value={maxStories}
                      onChange={(e) => setMaxStories(Number(e.target.value))}
                      className="w-full"
                      disabled={isLoading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      10+ stories with Comprehensive bulk gen typically yields 100+ test cases.
                    </p>
                  </div>

                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeUiContext}
                      onChange={(e) => setIncludeUiContext(e.target.checked)}
                      disabled={isLoading || !hasUiDiscovery}
                      className="mt-1"
                    />
                    <span className="text-sm text-gray-700">Include UI context from latest discovery</span>
                  </label>

                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" onClick={onClose} disabled={isLoading}>
                      Cancel
                    </Button>
                    <Button onClick={() => onConfirm(maxStories, includeUiContext)} isLoading={isLoading}>
                      Generate Stories
                    </Button>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
