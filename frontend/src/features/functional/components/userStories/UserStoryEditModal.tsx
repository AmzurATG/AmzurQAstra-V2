import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition, Switch } from '@headlessui/react'
import { XMarkIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { userStoriesApi } from '../../api'
import type { UserStory, UserStoryItemType, UserStoryPriority, UserStoryStatus } from '../../types'
import {
  ITEM_TYPE_OPTIONS,
  PRIORITY_OPTIONS,
  STATUS_OPTIONS,
  itemTypeConfig,
  priorityConfig,
  statusConfig,
} from '../../constants/userStoryUi'
import toast from 'react-hot-toast'

type Props = {
  projectId: number
  isOpen: boolean
  onClose: () => void
  story: UserStory | null
  onSaved: () => void
}

export function UserStoryEditModal({ projectId, isOpen, onClose, story, onSaved }: Props) {
  const [draft, setDraft] = useState<UserStory | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (isOpen && story) setDraft({ ...story })
    if (!isOpen) setDraft(null)
  }, [isOpen, story])

  const handleSave = async () => {
    if (!draft?.title?.trim()) {
      toast.error('Title is required')
      return
    }
    setIsSaving(true)
    try {
      await userStoriesApi.update(projectId, draft.id, {
        title: draft.title,
        description: draft.description,
        status: draft.status,
        priority: draft.priority,
        item_type: draft.item_type,
        story_points: draft.story_points,
        assignee: draft.assignee,
        integrity_check: draft.integrity_check,
      })
      toast.success('User story updated successfully')
      onSaved()
      onClose()
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to update user story')
    } finally {
      setIsSaving(false)
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
                  <Dialog.Title className="text-lg font-semibold text-gray-900">Edit user story</Dialog.Title>
                  <button
                    type="button"
                    onClick={onClose}
                    className="text-gray-400 transition-colors hover:text-gray-600"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {draft && (
                  <div className="max-h-[60vh] space-y-4 overflow-y-auto px-6 py-4">
                    {draft.external_key && (
                      <div>
                        <label className="mb-1 block text-sm font-medium text-gray-700">External key</label>
                        <div className="rounded-lg bg-gray-100 px-3 py-2 font-mono text-sm text-gray-600">
                          {draft.external_key}
                        </div>
                      </div>
                    )}

                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Title *</label>
                      <input
                        type="text"
                        value={draft.title}
                        onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                        className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                        placeholder="User story title"
                      />
                    </div>

                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
                      <textarea
                        value={draft.description || ''}
                        onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                        rows={4}
                        className="w-full rounded-lg border border-gray-300 p-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                        placeholder="User story description"
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
                          {STATUS_OPTIONS.map((status) => (
                            <option key={status} value={status}>
                              {statusConfig[status]?.label || status}
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
                          {PRIORITY_OPTIONS.map((priority) => (
                            <option key={priority} value={priority}>
                              {priorityConfig[priority]?.label || priority}
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
                          {ITEM_TYPE_OPTIONS.map((type) => (
                            <option key={type} value={type}>
                              {itemTypeConfig[type]?.label || type}
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
                        value={draft.assignee || ''}
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
                          checked={draft.integrity_check || false}
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
                )}

                <div className="flex justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
                  <Button variant="outline" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button onClick={handleSave} disabled={isSaving || !draft?.title?.trim()} isLoading={isSaving}>
                    Save changes
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
