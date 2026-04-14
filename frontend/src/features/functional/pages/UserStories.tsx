import { useState, useEffect, useLayoutEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { PaginationBar } from '@common/components/ui/PaginationBar'
import {
  PlusIcon,
  ArrowPathIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  LinkIcon,
} from '@heroicons/react/24/outline'
import { SyncFromIntegrationModal } from '../components'
import { UserStoryCreateModal } from '../components/userStories/UserStoryCreateModal'
import { UserStoryListRow } from '../components/userStories/UserStoryListRow'
import { userStoriesApi } from '../api'
import type { UserStory, UserStoryStats } from '../types'
import { DEFAULT_SYNC_ISSUE_TYPES, USER_STORIES_PAGE_SIZE } from '../constants/userStoryUi'
import toast from 'react-hot-toast'

export default function UserStories() {
  const { projectId } = useParams<{ projectId: string }>()
  const [stories, setStories] = useState<UserStory[]>([])
  const [stats, setStats] = useState<UserStoryStats>({
    total: 0,
    open: 0,
    in_progress: 0,
    done: 0,
    blocked: 0,
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false)
  const [isQuickSyncing, setIsQuickSyncing] = useState(false)
  const [generatingStoryId, setGeneratingStoryId] = useState<number | null>(null)
  const [deletingStoryId, setDeletingStoryId] = useState<number | null>(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const loadStats = useCallback(async () => {
    if (!projectId) return
    try {
      const response = await userStoriesApi.getStats(Number(projectId))
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }, [projectId])

  const loadStories = useCallback(async () => {
    if (!projectId) return
    setIsLoading(true)
    try {
      const params: {
        page: number
        page_size: number
        status?: string
        search?: string
      } = {
        page,
        page_size: USER_STORIES_PAGE_SIZE,
      }
      if (statusFilter !== 'all') params.status = statusFilter
      const q = debouncedSearch.trim()
      if (q) params.search = q

      const response = await userStoriesApi.list(Number(projectId), params)
      const data = response.data
      setStories(data.items || [])
      setPagination({
        total: data.total ?? 0,
        total_pages: data.total_pages || 1,
        has_next: data.has_next,
        has_prev: data.has_prev,
      })
    } catch (error) {
      console.error('Failed to load stories:', error)
    } finally {
      setIsLoading(false)
    }
  }, [projectId, page, statusFilter, debouncedSearch])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim()), 400)
    return () => clearTimeout(t)
  }, [searchQuery])

  useLayoutEffect(() => {
    setPage(1)
  }, [projectId, statusFilter, debouncedSearch])

  useEffect(() => {
    if (projectId) loadStats()
  }, [projectId, loadStats])

  useEffect(() => {
    if (projectId) loadStories()
  }, [projectId, loadStories])

  const handleSearch = () => setDebouncedSearch(searchQuery.trim())

  const hasListFilters = statusFilter !== 'all' || debouncedSearch.length > 0

  const handleSyncComplete = () => {
    loadStories()
    loadStats()
  }

  const handleSyncNow = async () => {
    if (!projectId) return
    setIsQuickSyncing(true)
    try {
      const integrationsRes = await userStoriesApi.getIntegrations(Number(projectId))
      const pmIntegrations = integrationsRes.data.filter(
        (i) => i.is_enabled && ['jira', 'redmine', 'azure_devops'].includes(i.integration_type)
      )
      if (pmIntegrations.length === 0) {
        toast.error('No project management integration connected. Add one under Integrations.')
        return
      }
      const integration = pmIntegrations[0]
      const syncResponse = await userStoriesApi.sync(Number(projectId), {
        integration_type: integration.integration_type,
        issue_types: [...DEFAULT_SYNC_ISSUE_TYPES],
        force_full_sync: false,
      })
      if (syncResponse.data.status === 'success') {
        const n = syncResponse.data.items_synced
        if (n === 0) {
          toast.success('Already up to date — no new or changed issues.')
        } else {
          toast.success(`Synced ${n} item${n === 1 ? '' : 's'}.`)
        }
        handleSyncComplete()
      } else {
        toast.error(syncResponse.data.message || 'Sync completed with errors')
      }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to sync')
    } finally {
      setIsQuickSyncing(false)
    }
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
        loadStories()
      } else {
        toast.error(response.data.error || 'Failed to generate tests')
      }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to generate tests')
    } finally {
      setGeneratingStoryId(null)
    }
  }

  const handleDeleteStory = async (storyId: number, storyKey: string | null) => {
    const confirmMessage = `Are you sure you want to delete ${storyKey || `Story #${storyId}`}? This will also delete all related test cases and test steps.`
    if (!window.confirm(confirmMessage)) return

    setDeletingStoryId(storyId)
    try {
      const response = await userStoriesApi.delete(Number(projectId), storyId)
      toast.success(response.data.message || 'User story deleted successfully')
      loadStories()
      loadStats()
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to delete user story')
    } finally {
      setDeletingStoryId(null)
    }
  }

  const rangeStart =
    pagination.total === 0 ? 0 : (page - 1) * USER_STORIES_PAGE_SIZE + 1
  const rangeEnd = Math.min(page * USER_STORIES_PAGE_SIZE, pagination.total)

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-gray-900">User Stories</h1>
          <p className="text-gray-600">Browse stories (read-only). Open a story to edit fields.</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-3">
          <Button
            variant="primary"
            onClick={handleSyncNow}
            isLoading={isQuickSyncing}
            disabled={isQuickSyncing}
          >
            <ArrowPathIcon className="mr-2 h-4 w-4" />
            Sync now
          </Button>
          <Button
            variant="outline"
            onClick={() => setIsSyncModalOpen(true)}
            disabled={isQuickSyncing}
          >
            <ArrowPathIcon className="mr-2 h-4 w-4" />
            Sync from Integration
          </Button>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <PlusIcon className="mr-2 h-4 w-4" />
            Add Manual Story
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
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

      <Card>
        <div className="flex flex-col gap-4 md:flex-row">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search user stories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500"
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

      {!isLoading && pagination.total === 0 && !hasListFilters && (
        <Card className="py-12 text-center">
          <LinkIcon className="mx-auto mb-4 h-12 w-12 text-gray-300" />
          <h3 className="mb-2 text-lg font-medium text-gray-900">No User Stories Yet</h3>
          <p className="mb-4 text-gray-500">
            Connect to Jira or Redmine to import user stories, or add them manually.
          </p>
          <div className="flex justify-center gap-3">
            <Link to={`/projects/${projectId}/integrations`}>
              <Button variant="outline">
                <LinkIcon className="mr-2 h-4 w-4" />
                Configure Integrations
              </Button>
            </Link>
            <Button onClick={handleSyncNow} isLoading={isQuickSyncing} disabled={isQuickSyncing}>
              <ArrowPathIcon className="mr-2 h-4 w-4" />
              Sync now
            </Button>
          </div>
        </Card>
      )}

      {isLoading && (
        <Card className="py-12 text-center">
          <ArrowPathIcon className="mx-auto mb-4 h-8 w-8 animate-spin text-primary-500" />
          <p className="text-gray-500">Loading user stories...</p>
        </Card>
      )}

      {!isLoading && stories.length > 0 && (
        <Card className="min-w-0">
          <div>
            <CardTitle>Stories</CardTitle>
            <p className="mt-1 text-sm text-gray-500">
              {pagination.total} total
              {pagination.total > 0 ? ` · rows ${rangeStart}–${rangeEnd}` : null}
            </p>
          </div>
          <div className="mt-4 divide-y divide-gray-100">
            {stories.map((story, index) => (
              <UserStoryListRow
                key={story.id}
                story={story}
                projectId={projectId!}
                serial={(page - 1) * USER_STORIES_PAGE_SIZE + index + 1}
                generatingStoryId={generatingStoryId}
                deletingStoryId={deletingStoryId}
                onGenerateTests={handleGenerateTests}
                onDelete={handleDeleteStory}
              />
            ))}
          </div>
          <PaginationBar
            page={page}
            totalPages={pagination.total_pages}
            hasPrev={pagination.has_prev}
            hasNext={pagination.has_next}
            onPageChange={setPage}
            totalItems={pagination.total}
            pageSize={USER_STORIES_PAGE_SIZE}
            itemLabel="stories"
          />
        </Card>
      )}

      {!isLoading && pagination.total === 0 && hasListFilters && (
        <Card className="py-8 text-center">
          <p className="text-gray-500">No stories match your filters</p>
        </Card>
      )}

      <SyncFromIntegrationModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        projectId={Number(projectId)}
        onSyncComplete={handleSyncComplete}
      />

      <UserStoryCreateModal
        projectId={Number(projectId)}
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={() => {
          loadStories()
          loadStats()
        }}
      />
    </div>
  )
}
