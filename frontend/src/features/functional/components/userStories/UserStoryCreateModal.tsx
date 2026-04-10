import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition, Switch } from '@headlessui/react'
import { XMarkIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { userStoriesApi } from '../../api'
import type { UserStoryItemType, UserStoryPriority, UserStoryStatus } from '../../types'
import {
  ITEM_TYPE_OPTIONS,
  PRIORITY_OPTIONS,
  STATUS_OPTIONS,
  itemTypeConfig,
  priorityConfig,
  statusConfig,
} from '../../constants/userStoryUi'
import toast from 'react-hot-toast'

export type NewStoryDraft = {
  title: string
  description: string
  acceptance_criteria: string
  status: UserStoryStatus
  priority: UserStoryPriority
  item_type: UserStoryItemType
  story_points: number | undefined
  assignee: string
  integrity_check: boolean
}

const emptyDraft = (): NewStoryDraft => ({
  title: '',
  description: '',
  acceptance_criteria: '',
  status: 'open',
  priority: 'medium',
  item_type: 'story',
  story_points: undefined,
  assignee: '',
  integrity_check: false,
})

type Props = {
  projectId: number
  isOpen: boolean
  onClose: () => void
  onCreated: () => void
}

export function UserStoryCreateModal({ projectId, isOpen, onClose, onCreated }: Props) {
  const [draft, setDraft] = useState<NewStoryDraft>(emptyDraft)
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    if (isOpen) setDraft(emptyDraft())
  }, [isOpen])

  const handleCreate = async () => {
    if (!draft.title.trim()) return
    setIsCreating(true)
    try {
      await userStoriesApi.create(projectId, {
        project_id: projectId,
        title: draft.title.trim(),
        description: draft.description || undefined,
        acceptance_criteria: draft.acceptance_criteria || undefined,
        status: draft.status,
        priority: draft.priority,
        item_type: draft.item_type,
        story_points: draft.story_points,
        assignee: draft.assignee || undefined,
        integrity_check: draft.integrity_check,
      })
      toast.success('User story created successfully')
      onCreated()
      onClose()
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to create user story')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-lg transform overflow-hidden rounded-xl bg-white shadow-2xl transition-all">
                <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">New user story</Dialog.Title>
                  <button
                    type="button"
                    onClick={onClose}
                    className="text-gray-400 transition-colors hover:text-gray-600"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                <div className="max-h-[60vh] space-y-4 overflow-y-auto px-6 py-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Title <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={draft.title}
                      onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      placeholder="User story title"
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
                    <textarea
                      value={draft.description}
                      onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                      rows={3}
                      className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      placeholder="As a user, I want to..."
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Acceptance criteria</label>
                    <textarea
                      value={draft.acceptance_criteria}
                      onChange={(e) => setDraft({ ...draft, acceptance_criteria: e.target.value })}
                      rows={3}
                      className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      placeholder="Given... When... Then..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Status</label>
                      <select
                        value={draft.status}
                        onChange={(e) =>
                          setDraft({ ...draft, status: e.target.value as UserStoryStatus })
                        }
                        className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>
                            {statusConfig[s]?.label || s}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Priority</label>
                      <select
                        value={draft.priority}
                        onChange={(e) =>
                          setDraft({ ...draft, priority: e.target.value as UserStoryPriority })
                        }
                        className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      >
                        {PRIORITY_OPTIONS.map((p) => (
                          <option key={p} value={p}>
                            {priorityConfig[p]?.label || p}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Item type</label>
                      <select
                        value={draft.item_type}
                        onChange={(e) =>
                          setDraft({ ...draft, item_type: e.target.value as UserStoryItemType })
                        }
                        className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      >
                        {ITEM_TYPE_OPTIONS.map((t) => (
                          <option key={t} value={t}>
                            {itemTypeConfig[t]?.label || t}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Story points</label>
                      <input
                        type="number"
                        value={draft.story_points ?? ''}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            story_points: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                        className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                        placeholder="0"
                        min={0}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Assignee</label>
                    <input
                      type="text"
                      value={draft.assignee}
                      onChange={(e) => setDraft({ ...draft, assignee: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                      placeholder="Assignee name"
                    />
                  </div>

                  <div className="border-t border-gray-200 pt-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldCheckIcon className="h-5 w-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-700">Integrity check</span>
                          <p className="text-xs text-gray-500">
                            Include linked test cases in build integrity checks
                          </p>
                        </div>
                      </div>
                      <Switch
                        checked={draft.integrity_check}
                        onChange={(checked) => setDraft({ ...draft, integrity_check: checked })}
                        className={`${
                          draft.integrity_check ? 'bg-green-600' : 'bg-gray-200'
                        } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2`}
                      >
                        <span
                          className={`${
                            draft.integrity_check ? 'translate-x-6' : 'translate-x-1'
                          } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                        />
                      </Switch>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
                  <Button variant="outline" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={isCreating || !draft.title.trim()}
                    isLoading={isCreating}
                  >
                    Create story
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
