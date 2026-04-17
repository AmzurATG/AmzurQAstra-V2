import { useState, useEffect, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, ArrowPathIcon, CheckIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { userStoriesApi } from '../api'
import type { ProjectIntegrationInfo, SyncRequest, Sprint } from '../types'
import { DEFAULT_SYNC_ISSUE_TYPES } from '../constants/userStoryUi'
import {
  getPmSyncPreferences,
  jiraSprintStateFromPrefs,
  setPmSyncPreferences,
} from '../utils/pmSyncPreferences'
import toast from 'react-hot-toast'

interface SyncFromIntegrationModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: number
  onSyncComplete: () => void
}

const ITEM_TYPES = [
  { id: 'Epic', label: 'Epics', description: 'Groups stories together' },
  { id: 'Story', label: 'Stories', description: 'User stories / requirements' },
  { id: 'Bug', label: 'Bugs', description: 'Bug reports' },
  { id: 'Task', label: 'Tasks', description: 'Development tasks' },
  { id: 'Sub-task', label: 'Sub-tasks', description: 'Subtasks of stories' },
]

const DEFAULT_SELECTED_TYPES: string[] = [...DEFAULT_SYNC_ISSUE_TYPES]

export default function SyncFromIntegrationModal({
  isOpen,
  onClose,
  projectId,
  onSyncComplete,
}: SyncFromIntegrationModalProps) {
  const [integrations, setIntegrations] = useState<ProjectIntegrationInfo[]>([])
  const [selectedIntegration, setSelectedIntegration] = useState<ProjectIntegrationInfo | null>(null)
  const [selectedTypes, setSelectedTypes] = useState<string[]>(DEFAULT_SELECTED_TYPES)
  const [sprints, setSprints] = useState<Sprint[]>([])
  /** Jira: user must opt in to All sprints or pick specific sprints */
  const [jiraAllSprints, setJiraAllSprints] = useState(false)
  const [jiraSelectedSprintIds, setJiraSelectedSprintIds] = useState<number[]>([])
  const [isLoadingSprints, setIsLoadingSprints] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load integrations when modal opens
  useEffect(() => {
    if (isOpen) {
      loadIntegrations()
    }
  }, [isOpen, projectId])

  // Load sprints when integration is selected or modal reopens (refresh list)
  useEffect(() => {
    if (!isOpen || !selectedIntegration || selectedIntegration.integration_type !== 'jira') {
      if (selectedIntegration && selectedIntegration.integration_type !== 'jira') {
        setSprints([])
        setJiraAllSprints(false)
        setJiraSelectedSprintIds([])
      }
      return
    }
    loadSprints()
  }, [selectedIntegration, isOpen])

  // Drop sprint ids that no longer exist on the board (never promote to "All sprints" — that hid user scope)
  useEffect(() => {
    if (selectedIntegration?.integration_type !== 'jira' || !sprints.length || jiraAllSprints) return
    if (isLoadingSprints) return
    const valid = jiraSelectedSprintIds.filter((id) =>
      sprints.some((s) => Number(s.id) === Number(id))
    )
    if (valid.length === jiraSelectedSprintIds.length) return
    if (valid.length === 0) {
      setJiraAllSprints(false)
      setJiraSelectedSprintIds([])
    } else {
      setJiraSelectedSprintIds(valid)
    }
  }, [
    sprints,
    selectedIntegration?.integration_type,
    jiraAllSprints,
    jiraSelectedSprintIds,
    isLoadingSprints,
  ])

  const loadSprints = async () => {
    if (!selectedIntegration) return
    setIsLoadingSprints(true)
    try {
      const response = await userStoriesApi.getSprints(projectId, selectedIntegration.integration_type)
      setSprints(response.data)
    } catch (err) {
      console.error('Failed to load sprints:', err)
      setSprints([])
    } finally {
      setIsLoadingSprints(false)
    }
  }

  const loadIntegrations = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await userStoriesApi.getIntegrations(projectId)
      // Filter only PM integrations that are enabled
      const pmIntegrations = response.data.filter(
        (i) => i.is_enabled && ['jira', 'redmine', 'azure_devops'].includes(i.integration_type)
      )
      setIntegrations(pmIntegrations)

      if (pmIntegrations.length > 0) {
        const prefs = getPmSyncPreferences(projectId)
        const match =
          prefs && pmIntegrations.find((i) => i.integration_type === prefs.integration_type)
        if (match && prefs) {
          setSelectedIntegration(match)
          if (prefs.issue_types?.length) {
            setSelectedTypes([...prefs.issue_types])
          }
          if (match.integration_type === 'jira') {
            const st = jiraSprintStateFromPrefs(prefs)
            setJiraAllSprints(st.allSprints)
            setJiraSelectedSprintIds(st.selectedIds.map((id) => Number(id)))
          } else {
            setJiraAllSprints(true)
            setJiraSelectedSprintIds([])
          }
        } else {
          setSelectedIntegration(pmIntegrations[0])
          setSelectedTypes(DEFAULT_SELECTED_TYPES)
          setJiraAllSprints(false)
          setJiraSelectedSprintIds([])
        }
      }
    } catch (err: any) {
      setError('Failed to load integrations')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleTypeToggle = (typeId: string) => {
    setSelectedTypes((prev) =>
      prev.includes(typeId)
        ? prev.filter((t) => t !== typeId)
        : [...prev, typeId]
    )
  }

  const toggleJiraSprint = (sprintId: number) => {
    if (jiraAllSprints) {
      // Leave "all" mode: keep every loaded sprint except the one toggled off
      const allIds = sprints.map((s) => Number(s.id))
      setJiraAllSprints(false)
      setJiraSelectedSprintIds(allIds.filter((id) => id !== sprintId))
      return
    }
    setJiraSelectedSprintIds((prev) =>
      prev.includes(sprintId) ? prev.filter((id) => id !== sprintId) : [...prev, sprintId]
    )
  }

  const handleSync = async () => {
    if (!selectedIntegration || selectedTypes.length === 0) {
      toast.error('Please select at least one item type')
      return
    }

    if (
      selectedIntegration.integration_type === 'jira' &&
      !jiraAllSprints &&
      jiraSelectedSprintIds.length === 0
    ) {
      toast.error('Select at least one sprint, or choose All sprints.')
      return
    }

    setIsSyncing(true)
    try {
      const syncRequest: SyncRequest = {
        integration_type: selectedIntegration.integration_type,
        issue_types: selectedTypes,
        force_full_sync: true,
      }
      if (selectedIntegration.integration_type === 'jira' && !jiraAllSprints) {
        syncRequest.sprint_ids = [...jiraSelectedSprintIds]
      }

      const response = await userStoriesApi.sync(projectId, syncRequest)

      if (response.data.status === 'success') {
        const n = response.data.items_synced
        if (n === 0) {
          toast.success('Already up to date — no new or changed issues.')
        } else {
          toast.success(`Synced ${n} item${n === 1 ? '' : 's'} successfully.`)
        }
        if (selectedIntegration.integration_type === 'jira') {
          setPmSyncPreferences(projectId, {
            integration_type: selectedIntegration.integration_type,
            issue_types: [...selectedTypes],
            force_full_sync: true,
            all_sprints: jiraAllSprints,
            ...(jiraAllSprints ? {} : { sprint_ids: [...jiraSelectedSprintIds] }),
          })
        } else {
          setPmSyncPreferences(projectId, {
            integration_type: selectedIntegration.integration_type,
            issue_types: [...selectedTypes],
            force_full_sync: true,
          })
        }
        onSyncComplete()
        onClose()
      } else {
        toast.error(response.data.message || 'Sync completed with errors')
        if (response.data.errors.length > 0) {
          console.error('Sync errors:', response.data.errors)
        }
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to sync'
      toast.error(message)
    } finally {
      setIsSyncing(false)
    }
  }

  const getIntegrationIcon = (type: string) => {
    switch (type) {
      case 'jira': return '🎫'
      case 'redmine': return '🔴'
      case 'azure_devops': return '🔷'
      default: return '🔗'
    }
  }

  const getIntegrationName = (type: string) => {
    switch (type) {
      case 'jira': return 'Jira'
      case 'redmine': return 'Redmine'
      case 'azure_devops': return 'Azure DevOps'
      default: return type
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
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
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                  <Dialog.Title className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <ArrowPathIcon className="w-5 h-5 text-primary-600" />
                    Sync from Integration
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                {/* Body */}
                <div className="px-6 py-4 space-y-5">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <ArrowPathIcon className="w-6 h-6 animate-spin text-primary-600" />
                      <span className="ml-2 text-gray-600">Loading integrations...</span>
                    </div>
                  ) : error ? (
                    <div className="text-center py-8">
                      <p className="text-red-600">{error}</p>
                      <Button variant="outline" onClick={loadIntegrations} className="mt-4">
                        Retry
                      </Button>
                    </div>
                  ) : integrations.length === 0 ? (
                    <div className="text-center py-8">
                      <p className="text-gray-600">No integrations configured.</p>
                      <p className="text-sm text-gray-500 mt-1">
                        Go to Integrations to set up Jira, Redmine, or Azure DevOps.
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Integration Selection */}
                      {integrations.length > 1 && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select Integration
                          </label>
                          <div className="space-y-2">
                            {integrations.map((integration) => (
                              <button
                                key={integration.id}
                                onClick={() => setSelectedIntegration(integration)}
                                className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-colors ${
                                  selectedIntegration?.id === integration.id
                                    ? 'border-primary-500 bg-primary-50'
                                    : 'border-gray-200 hover:border-gray-300'
                                }`}
                              >
                                <span className="text-xl">
                                  {getIntegrationIcon(integration.integration_type)}
                                </span>
                                <div className="text-left">
                                  <div className="font-medium text-gray-900">
                                    {getIntegrationName(integration.integration_type)}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {integration.config?.project_name || integration.config?.project_key || 'Configured'}
                                  </div>
                                </div>
                                {selectedIntegration?.id === integration.id && (
                                  <CheckIcon className="w-5 h-5 text-primary-600 ml-auto" />
                                )}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Single integration info */}
                      {integrations.length === 1 && selectedIntegration && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <span className="text-2xl">
                            {getIntegrationIcon(selectedIntegration.integration_type)}
                          </span>
                          <div>
                            <div className="font-medium text-gray-900">
                              {getIntegrationName(selectedIntegration.integration_type)}
                            </div>
                            <div className="text-sm text-gray-500">
                              {selectedIntegration.config?.project_name || selectedIntegration.config?.project_key || 'Connected'}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Item Types */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Item Types to Import
                        </label>
                        <div className="space-y-2">
                          {ITEM_TYPES.map((type) => (
                            <label
                              key={type.id}
                              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                            >
                              <input
                                type="checkbox"
                                checked={selectedTypes.includes(type.id)}
                                onChange={() => handleTypeToggle(type.id)}
                                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                              />
                              <div className="flex-1">
                                <span className="text-sm font-medium text-gray-900">
                                  {type.label}
                                </span>
                                <span className="text-xs text-gray-500 ml-2">
                                  ({type.description})
                                </span>
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Sprint Selection (Jira only) */}
                      {selectedIntegration?.integration_type === 'jira' && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Sprints
                          </label>
                          {isLoadingSprints ? (
                            <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                              <ArrowPathIcon className="w-4 h-4 animate-spin text-primary-600" />
                              <span className="text-sm text-gray-500">Loading sprints...</span>
                            </div>
                          ) : (
                            <div className="rounded-lg border border-gray-200 bg-white max-h-52 overflow-y-auto">
                              <label className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 cursor-pointer border-b border-gray-200">
                                <input
                                  type="checkbox"
                                  checked={jiraAllSprints}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setJiraAllSprints(true)
                                      setJiraSelectedSprintIds([])
                                    } else {
                                      setJiraAllSprints(false)
                                    }
                                  }}
                                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                />
                                <span className="text-sm font-medium text-gray-900">All sprints</span>
                              </label>
                              {['active', 'future', 'closed'].map((state) => {
                                const group = sprints.filter((s) => s.state === state)
                                if (group.length === 0) return null
                                return (
                                  <div key={state}>
                                    <div className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 bg-gray-50 sticky top-0 border-b border-gray-100">
                                      {state}
                                    </div>
                                    {group.map((sprint) => (
                                      <label
                                        key={sprint.id}
                                        className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                                      >
                                        <input
                                          type="checkbox"
                                          checked={
                                            jiraAllSprints ||
                                            jiraSelectedSprintIds.some(
                                              (id) => Number(id) === Number(sprint.id)
                                            )
                                          }
                                          onChange={() => toggleJiraSprint(sprint.id)}
                                          className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                        />
                                        <span className="text-sm text-gray-900 flex-1 min-w-0 truncate">
                                          {sprint.name}
                                        </span>
                                      </label>
                                    ))}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          <p className="mt-1 text-xs text-gray-500">
                            With <span className="font-medium">All sprints</span>, every sprint below is included
                            (all boxes checked). Uncheck a sprint to limit scope, or pick only the sprints you
                            need.
                          </p>
                        </div>
                      )}

                      <p className="text-xs text-gray-500 leading-relaxed">
                        Fetches all matching work items from the tool for your selections. Last successful
                        sync:{' '}
                        {selectedIntegration?.last_sync_at
                          ? formatDate(selectedIntegration.last_sync_at)
                          : 'never'}
                        .
                      </p>
                    </>
                  )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                  <Button variant="outline" onClick={onClose} disabled={isSyncing}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSync}
                    isLoading={isSyncing}
                    disabled={
                      !selectedIntegration ||
                      selectedTypes.length === 0 ||
                      isLoading ||
                      (selectedIntegration?.integration_type === 'jira' &&
                        !jiraAllSprints &&
                        jiraSelectedSprintIds.length === 0)
                    }
                  >
                    <ArrowPathIcon className="w-4 h-4 mr-2" />
                    Start Sync
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
