import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  XMarkIcon,
  SparklesIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import type { SuggestedStory } from '../types'

interface BrdStoryPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  stories: SuggestedStory[]
  modulesIdentified: number
  isAccepting: boolean
  onAccept: (selectedIndices?: number[]) => void
}

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-gray-100 text-gray-600',
}

export function BrdStoryPreviewModal({
  isOpen,
  onClose,
  stories,
  modulesIdentified,
  isAccepting,
  onAccept,
}: BrdStoryPreviewModalProps) {
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(stories.map((_, i) => i)),
  )

  const toggleAll = () => {
    if (selected.size === stories.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(stories.map((_, i) => i)))
    }
  }

  const toggle = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const handleAccept = () => {
    const indices = Array.from(selected).sort((a, b) => a - b)
    onAccept(indices.length === stories.length ? undefined : indices)
  }

  const allSelected = selected.size === stories.length
  const noneSelected = selected.size === 0

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
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-start justify-center p-4 pt-16">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl rounded-2xl bg-white shadow-2xl">
                {/* Header */}
                <div className="flex items-start justify-between border-b px-6 py-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <SparklesIcon className="h-5 w-5 text-indigo-500" />
                      <Dialog.Title className="text-lg font-semibold text-gray-900">
                        AI-Generated User Stories
                      </Dialog.Title>
                    </div>
                    <p className="mt-0.5 text-sm text-gray-500">
                      {stories.length} stories across {modulesIdentified} modules — select which to add.
                    </p>
                  </div>
                  <button onClick={onClose} className="rounded-lg p-1 hover:bg-gray-100">
                    <XMarkIcon className="h-5 w-5 text-gray-400" />
                  </button>
                </div>

                {/* Toolbar */}
                <div className="flex items-center justify-between border-b bg-gray-50 px-6 py-2">
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={toggleAll}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600"
                    />
                    Select all ({stories.length})
                  </label>
                  <span className="text-sm text-gray-500">{selected.size} selected</span>
                </div>

                {/* Story list */}
                <div className="max-h-[56vh] divide-y overflow-y-auto">
                  {stories.map((story, idx) => (
                    <label
                      key={idx}
                      className={`flex cursor-pointer gap-4 px-6 py-4 transition-colors hover:bg-gray-50 ${
                        selected.has(idx) ? 'bg-indigo-50/40' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(idx)}
                        onChange={() => toggle(idx)}
                        className="mt-1 h-4 w-4 flex-shrink-0 rounded border-gray-300 text-indigo-600"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-gray-900">{story.title}</span>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                              PRIORITY_BADGE[story.priority] ?? PRIORITY_BADGE.medium
                            }`}
                          >
                            {story.priority}
                          </span>
                          {story.module && (
                            <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                              {story.module}
                            </span>
                          )}
                        </div>
                        {story.acceptance_criteria && (
                          <p className="mt-1 line-clamp-2 text-xs text-gray-500">
                            {story.acceptance_criteria}
                          </p>
                        )}
                        {story.rationale && (
                          <p className="mt-0.5 text-xs italic text-gray-400">{story.rationale}</p>
                        )}
                      </div>
                    </label>
                  ))}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between border-t bg-gray-50 px-6 py-4">
                  <Button variant="ghost" onClick={onClose} disabled={isAccepting}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleAccept}
                    disabled={noneSelected || isAccepting}
                    isLoading={isAccepting}
                    leftIcon={<CheckCircleIcon className="h-4 w-4" />}
                  >
                    Add {selected.size} {selected.size === 1 ? 'Story' : 'Stories'} to Project
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
