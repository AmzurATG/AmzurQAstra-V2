import { useState, useEffect, Fragment } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Dialog, Transition, Switch } from '@headlessui/react'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import {
  PlusIcon,
  ArrowPathIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  LinkIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  SparklesIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { SyncFromIntegrationModal } from '../components'
import { userStoriesApi } from '../api'
import type { UserStory, UserStoryStats, UserStoryStatus, UserStoryPriority, UserStoryItemType } from '../types'
import toast from 'react-hot-toast'

const STATUS_OPTIONS: UserStoryStatus[] = ['open', 'in_progress', 'done', 'blocked', 'closed']
const PRIORITY_OPTIONS: UserStoryPriority[] = ['low', 'medium', 'high', 'critical']
const ITEM_TYPE_OPTIONS: UserStoryItemType[] = ['epic', 'story', 'bug', 'task', 'subtask', 'feature', 'requirement']

const statusConfig = {
  open: { label: 'Open', color: 'bg-gray-100 text-gray-700', icon: ClockIcon },
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: ArrowPathIcon },
  done: { label: 'Done', color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
  blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700', icon: ExclamationCircleIcon },
  closed: { label: 'Closed', color: 'bg-gray-100 text-gray-600', icon: CheckCircleIcon },
}

const priorityConfig = {
  low: { label: 'Low', color: 'bg-gray-100 text-gray-600' },
  medium: { label: 'Medium', color: 'bg-yellow-100 text-yellow-700' },
  high: { label: 'High', color: 'bg-orange-100 text-orange-700' },
  critical: { label: 'Critical', color: 'bg-red-100 text-red-700' },
}

const sourceConfig = {
  jira: { label: 'Jira', icon: '🎫' },
  redmine: { label: 'Redmine', icon: '🔴' },
  azure_devops: { label: 'Azure DevOps', icon: '🔷' },
  manual: { label: 'Manual', icon: '✏️' },
}

const itemTypeConfig = {
  epic: { label: 'Epic', color: 'bg-purple-100 text-purple-700' },
  story: { label: 'Story', color: 'bg-blue-100 text-blue-700' },
  bug: { label: 'Bug', color: 'bg-red-100 text-red-700' },
  task: { label: 'Task', color: 'bg-gray-100 text-gray-700' },
  subtask: { label: 'Sub-task', color: 'bg-gray-100 text-gray-600' },
  feature: { label: 'Feature', color: 'bg-green-100 text-green-700' },
  requirement: { label: 'Requirement', color: 'bg-indigo-100 text-indigo-700' },
}

export default function UserStories() {
  const { projectId } = useParams<{ projectId: string }>()
  const [stories, setStories] = useState<UserStory[]>([])
  const [stats, setStats] = useState<UserStoryStats>({ total: 0, open: 0, in_progress: 0, done: 0, blocked: 0 })
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false)
  const [generatingStoryId, setGeneratingStoryId] = useState<number | null>(null)
  const [deletingStoryId, setDeletingStoryId] = useState<number | null>(null)
  
  // Edit modal state
  const [editingStory, setEditingStory] = useState<UserStory | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Create modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [newStory, setNewStory] = useState({
    title: '',
    description: '',
    acceptance_criteria: '',
    status: 'open' as UserStoryStatus,
    priority: 'medium' as UserStoryPriority,
    item_type: 'story' as UserStoryItemType,
    story_points: undefined as number | undefined,
    assignee: '',
    integrity_check: false,
  })

  // Load stories on mount
  useEffect(() => {
    if (projectId) {
      loadStories()
      loadStats()
    }
  }, [projectId])

  const loadStories = async () => {
    if (!projectId) return
    setIsLoading(true)
    try {
      const params: any = {}
      if (statusFilter !== 'all') params.status = statusFilter
      if (searchQuery) params.search = searchQuery
      
      const response = await userStoriesApi.list(Number(projectId), params)
      setStories(response.data.items || [])
    } catch (error) {
      console.error('Failed to load stories:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadStats = async () => {
    if (!projectId) return
    try {
      const response = await userStoriesApi.getStats(Number(projectId))
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  // Reload when filters change
  useEffect(() => {
    if (projectId && !isLoading) {
      loadStories()
    }
  }, [statusFilter])

  const handleSearch = () => {
    loadStories()
  }

  const handleSyncComplete = () => {
    loadStories()
    loadStats()
  }

  const handleGenerateTests = async (storyId: number, storyKey: string | null) => {
    setGeneratingStoryId(storyId)
    try {
      const response = await userStoriesApi.generateTests(Number(projectId), storyId, {
        include_steps: true,
      })
      
      if (response.data.success) {
        toast.success(
          `Generated ${response.data.test_cases_created} test case(s) for ${storyKey || `Story #${storyId}`}`
        )
        // Reload stories to update test case count
        loadStories()
      } else {
        toast.error(response.data.error || 'Failed to generate tests')
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to generate tests'
      toast.error(message)
    } finally {
      setGeneratingStoryId(null)
    }
  }

  const handleDeleteStory = async (storyId: number, storyKey: string | null) => {
    const confirmMessage = `Are you sure you want to delete ${storyKey || `Story #${storyId}`}? This will also delete all related test cases and test steps.`
    if (!window.confirm(confirmMessage)) {
      return
    }
    
    setDeletingStoryId(storyId)
    try {
      const response = await userStoriesApi.delete(Number(projectId), storyId)
      toast.success(response.data.message || 'User story deleted successfully')
      loadStories()
      loadStats()
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to delete user story'
      toast.error(message)
    } finally {
      setDeletingStoryId(null)
    }
  }

  const handleEditStory = (story: UserStory) => {
    setEditingStory({ ...story })
    setIsEditModalOpen(true)
  }

  const handleSaveStory = async () => {
    if (!editingStory || !projectId) return
    
    setIsSaving(true)
    try {
      await userStoriesApi.update(Number(projectId), editingStory.id, {
        title: editingStory.title,
        description: editingStory.description,
        status: editingStory.status,
        priority: editingStory.priority,
        item_type: editingStory.item_type,
        story_points: editingStory.story_points,
        assignee: editingStory.assignee,
        integrity_check: editingStory.integrity_check,
      })
      toast.success('User story updated successfully')
      setIsEditModalOpen(false)
      setEditingStory(null)
      loadStories()
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to update user story'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleOpenCreate = () => {
    setNewStory({
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
    setIsCreateModalOpen(true)
  }

  const handleCreateStory = async () => {
    if (!projectId || !newStory.title.trim()) return

    setIsCreating(true)
    try {
      await userStoriesApi.create(Number(projectId), {
        project_id: Number(projectId),
        title: newStory.title.trim(),
        description: newStory.description || undefined,
        acceptance_criteria: newStory.acceptance_criteria || undefined,
        status: newStory.status,
        priority: newStory.priority,
        item_type: newStory.item_type,
        story_points: newStory.story_points,
        assignee: newStory.assignee || undefined,
        integrity_check: newStory.integrity_check,
      })
      toast.success('User story created successfully')
      setIsCreateModalOpen(false)
      loadStories()
      loadStats()
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to create user story'
      toast.error(message)
    } finally {
      setIsCreating(false)
    }
  }

  const filteredStories = stories.filter((story) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      story.title.toLowerCase().includes(query) ||
      (story.external_key?.toLowerCase().includes(query) ?? false)
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Stories</h1>
          <p className="text-gray-600">Import and manage user stories from Jira or Redmine</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => setIsSyncModalOpen(true)}>
            <ArrowPathIcon className="w-4 h-4 mr-2" />
            Sync from Integration
          </Button>
          <Button onClick={handleOpenCreate}>
            <PlusIcon className="w-4 h-4 mr-2" />
            Add Manual Story
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="text-center">
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
          <div className="text-sm text-gray-500">Total</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-gray-600">{stats.open}</div>
          <div className="text-sm text-gray-500">Open</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-blue-600">{stats.in_progress}</div>
          <div className="text-sm text-gray-500">In Progress</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-green-600">{stats.done}</div>
          <div className="text-sm text-gray-500">Done</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-red-600">{stats.blocked}</div>
          <div className="text-sm text-gray-500">Blocked</div>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search user stories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="done">Done</option>
              <option value="blocked">Blocked</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Integration Notice */}
      {!isLoading && stories.length === 0 && (
        <Card className="text-center py-12">
          <LinkIcon className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No User Stories Yet</h3>
          <p className="text-gray-500 mb-4">
            Connect to Jira or Redmine to import user stories, or add them manually.
          </p>
          <div className="flex justify-center gap-3">
            <Link to={`/projects/${projectId}/integrations`}>
              <Button variant="outline">
                <LinkIcon className="w-4 h-4 mr-2" />
                Configure Integrations
              </Button>
            </Link>
            <Button onClick={() => setIsSyncModalOpen(true)}>
              <ArrowPathIcon className="w-4 h-4 mr-2" />
              Sync Now
            </Button>
          </div>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <Card className="text-center py-12">
          <ArrowPathIcon className="w-8 h-8 mx-auto text-primary-500 animate-spin mb-4" />
          <p className="text-gray-500">Loading user stories...</p>
        </Card>
      )}

      {/* Stories List */}
      {!isLoading && filteredStories.length > 0 && (
        <Card>
          <CardTitle>Stories ({filteredStories.length})</CardTitle>
          <div className="mt-4 divide-y divide-gray-100">
            {filteredStories.map((story) => {
              const statusCfg = statusConfig[story.status] || statusConfig.open
              const StatusIcon = statusCfg.icon
              const priorityCfg = priorityConfig[story.priority] || priorityConfig.medium
              const sourceCfg = sourceConfig[story.source] || sourceConfig.manual
              const itemTypeCfg = itemTypeConfig[story.item_type] || itemTypeConfig.story
              
              return (
                <div
                  key={story.id}
                  className="py-4 hover:bg-gray-50 px-2 -mx-2 rounded-lg cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {story.external_key && (
                          <span className="text-sm font-mono text-primary-600">{story.external_key}</span>
                        )}
                        <span className="text-xs" title={sourceCfg.label}>
                          {sourceCfg.icon}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded-full ${itemTypeCfg.color}`}
                        >
                          {itemTypeCfg.label}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${statusCfg.color}`}
                        >
                          <StatusIcon className="w-3 h-3" />
                          {statusCfg.label}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded-full ${priorityCfg.color}`}
                        >
                          {priorityCfg.label}
                        </span>
                        {story.integrity_check && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">
                            <ShieldCheckIcon className="w-3 h-3" />
                            Integrity Check
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">{story.title}</h3>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                        {story.assignee && <span>Assignee: {story.assignee}</span>}
                        {story.story_points && <span>{story.story_points} pts</span>}
                        {story.parent_key && (
                          <span className="text-purple-600">Parent: {story.parent_key}</span>
                        )}
                        <span>{story.linked_requirements} requirements</span>
                        <span>{story.linked_test_cases} test cases</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleEditStory(story)
                        }}
                      >
                        <PencilIcon className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                      <Button variant="outline" size="sm">
                        Generate Requirements
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleGenerateTests(story.id, story.external_key ?? null)
                        }}
                        disabled={generatingStoryId === story.id}
                        isLoading={generatingStoryId === story.id}
                      >
                        {generatingStoryId !== story.id && (
                          <SparklesIcon className="w-4 h-4 mr-1" />
                        )}
                        Generate Tests
                      </Button>
                      <Button 
                        variant="danger" 
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteStory(story.id, story.external_key ?? null)
                        }}
                        disabled={deletingStoryId === story.id}
                        isLoading={deletingStoryId === story.id}
                      >
                        {deletingStoryId !== story.id && (
                          <TrashIcon className="w-4 h-4 mr-1" />
                        )}
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {!isLoading && filteredStories.length === 0 && stories.length > 0 && (
        <Card className="text-center py-8">
          <p className="text-gray-500">No stories match your filters</p>
        </Card>
      )}

      {/* Sync Modal */}
      <SyncFromIntegrationModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        projectId={Number(projectId)}
        onSyncComplete={handleSyncComplete}
      />

      {/* Edit Story Modal */}
      <Transition appear show={isEditModalOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setIsEditModalOpen(false)}>
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
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Edit User Story
                    </Dialog.Title>
                    <button
                      onClick={() => setIsEditModalOpen(false)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Body */}
                  {editingStory && (
                    <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                      {/* External Key (readonly) */}
                      {editingStory.external_key && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            External Key
                          </label>
                          <div className="px-3 py-2 bg-gray-100 rounded-lg text-sm font-mono text-gray-600">
                            {editingStory.external_key}
                          </div>
                        </div>
                      )}

                      {/* Title */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Title *
                        </label>
                        <input
                          type="text"
                          value={editingStory.title}
                          onChange={(e) => setEditingStory({ ...editingStory, title: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="User story title"
                        />
                      </div>

                      {/* Description */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <textarea
                          value={editingStory.description || ''}
                          onChange={(e) => setEditingStory({ ...editingStory, description: e.target.value })}
                          rows={4}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="User story description"
                        />
                      </div>

                      {/* Status & Priority row */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Status
                          </label>
                          <select
                            value={editingStory.status}
                            onChange={(e) => setEditingStory({ ...editingStory, status: e.target.value as UserStoryStatus })}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          >
                            {STATUS_OPTIONS.map((status) => (
                              <option key={status} value={status}>
                                {statusConfig[status]?.label || status}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Priority
                          </label>
                          <select
                            value={editingStory.priority}
                            onChange={(e) => setEditingStory({ ...editingStory, priority: e.target.value as UserStoryPriority })}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          >
                            {PRIORITY_OPTIONS.map((priority) => (
                              <option key={priority} value={priority}>
                                {priorityConfig[priority]?.label || priority}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {/* Item Type & Story Points row */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Item Type
                          </label>
                          <select
                            value={editingStory.item_type}
                            onChange={(e) => setEditingStory({ ...editingStory, item_type: e.target.value as UserStoryItemType })}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          >
                            {ITEM_TYPE_OPTIONS.map((type) => (
                              <option key={type} value={type}>
                                {itemTypeConfig[type]?.label || type}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Story Points
                          </label>
                          <input
                            type="number"
                            value={editingStory.story_points || ''}
                            onChange={(e) => setEditingStory({ ...editingStory, story_points: e.target.value ? Number(e.target.value) : undefined })}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                            placeholder="0"
                            min="0"
                          />
                        </div>
                      </div>

                      {/* Assignee */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Assignee
                        </label>
                        <input
                          type="text"
                          value={editingStory.assignee || ''}
                          onChange={(e) => setEditingStory({ ...editingStory, assignee: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Assignee name"
                        />
                      </div>

                      {/* Integrity Check Toggle */}
                      <div className="pt-4 border-t border-gray-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <ShieldCheckIcon className="w-5 h-5 text-gray-500" />
                            <div>
                              <span className="text-sm font-medium text-gray-700">Integrity Check</span>
                              <p className="text-xs text-gray-500">Include all test cases in build integrity checks</p>
                            </div>
                          </div>
                          <Switch
                            checked={editingStory.integrity_check || false}
                            onChange={(checked) => setEditingStory({ ...editingStory, integrity_check: checked })}
                            className={`${editingStory.integrity_check ? 'bg-green-600' : 'bg-gray-200'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2`}
                          >
                            <span className={`${editingStory.integrity_check ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                          </Switch>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <Button
                      variant="outline"
                      onClick={() => setIsEditModalOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSaveStory}
                      disabled={isSaving || !editingStory?.title}
                      isLoading={isSaving}
                    >
                      Save Changes
                    </Button>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
      {/* Create Story Modal */}
      <Transition appear show={isCreateModalOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setIsCreateModalOpen(false)}>
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
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      New User Story
                    </Dialog.Title>
                    <button
                      onClick={() => setIsCreateModalOpen(false)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Body */}
                  <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                    {/* Title */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Title <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={newStory.title}
                        onChange={(e) => setNewStory({ ...newStory, title: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        placeholder="User story title"
                        autoFocus
                      />
                    </div>

                    {/* Description */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description
                      </label>
                      <textarea
                        value={newStory.description}
                        onChange={(e) => setNewStory({ ...newStory, description: e.target.value })}
                        rows={3}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        placeholder="As a user, I want to..."
                      />
                    </div>

                    {/* Acceptance Criteria */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Acceptance Criteria
                      </label>
                      <textarea
                        value={newStory.acceptance_criteria}
                        onChange={(e) => setNewStory({ ...newStory, acceptance_criteria: e.target.value })}
                        rows={3}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        placeholder="Given... When... Then..."
                      />
                    </div>

                    {/* Status & Priority row */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Status
                        </label>
                        <select
                          value={newStory.status}
                          onChange={(e) => setNewStory({ ...newStory, status: e.target.value as UserStoryStatus })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{statusConfig[s]?.label || s}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Priority
                        </label>
                        <select
                          value={newStory.priority}
                          onChange={(e) => setNewStory({ ...newStory, priority: e.target.value as UserStoryPriority })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        >
                          {PRIORITY_OPTIONS.map((p) => (
                            <option key={p} value={p}>{priorityConfig[p]?.label || p}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Item Type & Story Points row */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Item Type
                        </label>
                        <select
                          value={newStory.item_type}
                          onChange={(e) => setNewStory({ ...newStory, item_type: e.target.value as UserStoryItemType })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        >
                          {ITEM_TYPE_OPTIONS.map((t) => (
                            <option key={t} value={t}>{itemTypeConfig[t]?.label || t}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Story Points
                        </label>
                        <input
                          type="number"
                          value={newStory.story_points ?? ''}
                          onChange={(e) => setNewStory({ ...newStory, story_points: e.target.value ? Number(e.target.value) : undefined })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="0"
                          min="0"
                        />
                      </div>
                    </div>

                    {/* Assignee */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Assignee
                      </label>
                      <input
                        type="text"
                        value={newStory.assignee}
                        onChange={(e) => setNewStory({ ...newStory, assignee: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        placeholder="Assignee name"
                      />
                    </div>

                    {/* Integrity Check Toggle */}
                    <div className="pt-4 border-t border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <ShieldCheckIcon className="w-5 h-5 text-gray-500" />
                          <div>
                            <span className="text-sm font-medium text-gray-700">Integrity Check</span>
                            <p className="text-xs text-gray-500">Include all test cases in build integrity checks</p>
                          </div>
                        </div>
                        <Switch
                          checked={newStory.integrity_check}
                          onChange={(checked) => setNewStory({ ...newStory, integrity_check: checked })}
                          className={`${newStory.integrity_check ? 'bg-green-600' : 'bg-gray-200'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2`}
                        >
                          <span className={`${newStory.integrity_check ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                        </Switch>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreateStory}
                      disabled={isCreating || !newStory.title.trim()}
                      isLoading={isCreating}
                    >
                      Create Story
                    </Button>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </div>
  )
}
