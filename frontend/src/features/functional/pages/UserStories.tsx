import {
  useState,
  useEffect,
  useLayoutEffect,
  useCallback,
  useRef,
  useMemo,
} from 'react'
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
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { SyncFromIntegrationModal } from '../components'
import { UserStoryCreateModal } from '../components/userStories/UserStoryCreateModal'
import { UserStoryListRow } from '../components/userStories/UserStoryListRow'
import { TestGenerationInfoDialog } from '../components/userStories/TestGenerationInfoDialog'
import { useUserStoryTestGeneration } from '../hooks/useUserStoryTestGeneration'
import { usePmQuickSync } from '../hooks/usePmQuickSync'
import { userStoriesApi } from '../api'
import type { UserStory, UserStoryStats } from '../types'
import {
  USER_STORIES_PAGE_SIZE,
  STATUS_OPTIONS,
  statusConfig,
} from '../constants/userStoryUi'
import {
  getPmSyncPreferences,
  hasValidSyncScopeForQuickSync,
  hydratePmSyncPreferencesFromIntegrations,
  isJiraScopedWithoutSprintSelection,
  sprintIdsQueryFromPrefs,
} from '../utils/pmSyncPreferences'
import toast from 'react-hot-toast'

const userStorySelectionKey = (projectId: string) => `qastra:user-story-selection:${projectId}`

function loadUserStorySelection(projectId: string | undefined): Set<number> {
  if (!projectId || typeof window === 'undefined') return new Set()
  try {
    const raw = sessionStorage.getItem(userStorySelectionKey(projectId))
    if (!raw) return new Set()
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return new Set()
    return new Set(
      parsed.filter((n): n is number => typeof n === 'number' && Number.isFinite(n))
    )
  } catch {
    return new Set()
  }
}

export default function UserStories() {
  const { projectId } = useParams<{ projectId: string }>()
  const [stories, setStories] = useState<UserStory[]>([])
  const [stats, setStats] = useState<UserStoryStats>({
    total: 0,
    open: 0,
    in_progress: 0,
    done: 0,
    blocked: 0,
    closed: 0,
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
  const [deletingStoryId, setDeletingStoryId] = useState<number | null>(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [integrationsReady, setIntegrationsReady] = useState(false)
  const [hasPmIntegration, setHasPmIntegration] = useState(false)
  /** Server has sync_scope with issue types — enables Sync now when localStorage is empty (new device/tab). */
  const [remoteQuickSyncAllowed, setRemoteQuickSyncAllowed] = useState(false)

  const [selectedIds, setSelectedIds] = useState<Set<number>>(() =>
    loadUserStorySelection(projectId)
  )
  /** When set, user used “select all eligible” across all pages — used for checkbox checked/indeterminate. */
  const [selectAllEligibleSnapshot, setSelectAllEligibleSnapshot] = useState<number[] | null>(null)
  const [isSelectingAllEligible, setIsSelectingAllEligible] = useState(false)
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null)

  const reloadStoriesAndStatsRef = useRef<() => void>(() => {})

  const {
    isQuickSyncing,
    syncNow: handleSyncNow,
    hasConfiguredSync,
    refreshPreferences,
    prefsVersion,
  } = usePmQuickSync(
    projectId,
    () => reloadStoriesAndStatsRef.current(),
    remoteQuickSyncAllowed
  )

  const listViewKey = `${page}|${debouncedSearch}|${statusFilter}|${prefsVersion}`
  const prevListViewKeyRef = useRef<string | null>(null)
  const prevPageStoryIdsRef = useRef<Set<number>>(new Set())

  const loadStats = useCallback(async () => {
    if (!projectId) return
    try {
      const prefs = getPmSyncPreferences(Number(projectId))
      if (isJiraScopedWithoutSprintSelection(prefs)) {
        setStats({
          total: 0,
          open: 0,
          in_progress: 0,
          done: 0,
          blocked: 0,
          closed: 0,
        })
        return
      }
      const sprintIds = sprintIdsQueryFromPrefs(prefs)
      const response = await userStoriesApi.getStats(
        Number(projectId),
        sprintIds ? { sprint_ids: sprintIds } : undefined
      )
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }, [projectId, prefsVersion])

  const loadStories = useCallback(async () => {
    if (!projectId) return
    setIsLoading(true)
    try {
      const prefs = getPmSyncPreferences(Number(projectId))
      if (isJiraScopedWithoutSprintSelection(prefs)) {
        setStories([])
        setPagination({
          total: 0,
          total_pages: 1,
          has_next: false,
          has_prev: false,
        })
        return
      }
      const sprintIds = sprintIdsQueryFromPrefs(prefs)
      const params: {
        page: number
        page_size: number
        status?: string
        search?: string
        sprint_ids?: string
      } = {
        page,
        page_size: USER_STORIES_PAGE_SIZE,
      }
      if (statusFilter !== 'all') params.status = statusFilter
      const q = debouncedSearch.trim()
      if (q) params.search = q
      if (sprintIds) params.sprint_ids = sprintIds

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
  }, [projectId, page, statusFilter, debouncedSearch, prefsVersion])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim()), 400)
    return () => clearTimeout(t)
  }, [searchQuery])

  useLayoutEffect(() => {
    setPage(1)
  }, [projectId, statusFilter, debouncedSearch, prefsVersion])

  useEffect(() => {
    if (projectId) loadStats()
  }, [projectId, loadStats])

  useEffect(() => {
    if (projectId) loadStories()
  }, [projectId, loadStories])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    setIntegrationsReady(false)
    setRemoteQuickSyncAllowed(false)
    ;(async () => {
      try {
        const res = await userStoriesApi.getIntegrations(Number(projectId))
        if (cancelled) return
        const pm = res.data.filter(
          (i) =>
            i.is_enabled && ['jira', 'redmine', 'azure_devops'].includes(i.integration_type)
        )
        setHasPmIntegration(pm.length > 0)
        setRemoteQuickSyncAllowed(
          res.data.some(
            (i) =>
              i.is_enabled &&
              ['jira', 'redmine', 'azure_devops'].includes(i.integration_type) &&
              hasValidSyncScopeForQuickSync(i.config as Record<string, unknown> | null)
          )
        )
        const hydrated = hydratePmSyncPreferencesFromIntegrations(Number(projectId), res.data)
        if (hydrated) {
          refreshPreferences()
        }
      } catch {
        if (!cancelled) {
          setHasPmIntegration(false)
          setRemoteQuickSyncAllowed(false)
        }
      } finally {
        if (!cancelled) setIntegrationsReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [projectId, refreshPreferences])

  const onTestGenerationSuccess = useCallback(() => {
    loadStories()
    loadStats()
  }, [loadStories, loadStats])

  const {
    generatingStoryId,
    runGenerate,
    infoDialogOpen,
    infoMessage,
    closeInfoDialog,
  } = useUserStoryTestGeneration(projectId ? Number(projectId) : undefined, {
    onSuccess: onTestGenerationSuccess,
  })

  const handleSearch = () => setDebouncedSearch(searchQuery.trim())

  const hasListFilters = statusFilter !== 'all' || debouncedSearch.length > 0

  const reloadStoriesAndStats = useCallback(() => {
    loadStories()
    loadStats()
  }, [loadStories, loadStats])

  useEffect(() => {
    reloadStoriesAndStatsRef.current = reloadStoriesAndStats
  }, [reloadStoriesAndStats])

  const handleIntegrationSyncComplete = useCallback(() => {
    refreshPreferences()
    reloadStoriesAndStats()
  }, [refreshPreferences, reloadStoriesAndStats])

  const handleGenerateTests = (storyId: number, _displayKey: string) => {
    void runGenerate(storyId, false)
  }

  const handleToggleSelect = useCallback((storyId: number) => {
    setSelectAllEligibleSnapshot(null)
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(storyId)) next.delete(storyId)
      else next.add(storyId)
      return next
    })
  }, [])

  const isGlobalEligibleSelection = useMemo(() => {
    if (
      selectAllEligibleSnapshot === null ||
      selectAllEligibleSnapshot.length === 0 ||
      selectedIds.size === 0
    ) {
      return false
    }
    if (selectAllEligibleSnapshot.length !== selectedIds.size) return false
    return selectAllEligibleSnapshot.every((id) => selectedIds.has(id))
  }, [selectAllEligibleSnapshot, selectedIds])

  const handleSelectAllEligibleAcrossPages = useCallback(async () => {
    if (isGlobalEligibleSelection) {
      setSelectedIds(new Set())
      setSelectAllEligibleSnapshot(null)
      return
    }
    if (!projectId) return
    const pid = Number(projectId)
    const prefs = getPmSyncPreferences(pid)
    if (isJiraScopedWithoutSprintSelection(prefs)) {
      toast.error('Choose a sprint scope in Sync from Integration first.')
      return
    }
    const sprintIds = sprintIdsQueryFromPrefs(prefs)
    const params: {
      page: number
      page_size: number
      status?: string
      search?: string
      sprint_ids?: string
    } = { page: 1, page_size: 100 }
    if (statusFilter !== 'all') params.status = statusFilter
    const q = debouncedSearch.trim()
    if (q) params.search = q
    if (sprintIds) params.sprint_ids = sprintIds

    setIsSelectingAllEligible(true)
    try {
      const eligible: number[] = []
      let pageNum = 1
      let totalPages = 1
      do {
        const res = await userStoriesApi.list(pid, { ...params, page: pageNum })
        const data = res.data
        totalPages = data.total_pages ?? 1
        for (const item of data.items ?? []) {
          if ((item.generated_test_cases ?? 0) === 0) eligible.push(item.id)
        }
        pageNum++
      } while (pageNum <= totalPages)

      setSelectedIds(new Set(eligible))
      setSelectAllEligibleSnapshot(eligible)
      if (eligible.length === 0) {
        toast.success('No stories without generated tests in this list.')
      }
    } catch {
      toast.error('Failed to load stories for selection')
    } finally {
      setIsSelectingAllEligible(false)
    }
  }, [
    projectId,
    statusFilter,
    debouncedSearch,
    isGlobalEligibleSelection,
  ])

  useEffect(() => {
    const el = selectAllCheckboxRef.current
    if (!el) return
    el.indeterminate =
      selectedIds.size > 0 && !isGlobalEligibleSelection
  }, [selectedIds, isGlobalEligibleSelection])

  const [isBulkGenerating, setIsBulkGenerating] = useState(false)

  const handleBulkGenerateTests = useCallback(async () => {
    if (selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    setIsBulkGenerating(true)
    try {
      for (const id of ids) {
        await runGenerate(id, false)
      }
    } finally {
      setIsBulkGenerating(false)
    }
  }, [selectedIds, runGenerate])

  useEffect(() => {
    setSelectedIds(loadUserStorySelection(projectId))
    setSelectAllEligibleSnapshot(null)
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    try {
      sessionStorage.setItem(
        userStorySelectionKey(projectId),
        JSON.stringify([...selectedIds])
      )
    } catch {
      // ignore quota / private mode
    }
  }, [projectId, selectedIds])

  useEffect(() => {
    if (isLoading) return
    const idsNow = new Set(stories.map((s) => s.id))
    const sameView = prevListViewKeyRef.current === listViewKey
    prevListViewKeyRef.current = listViewKey

    if (!sameView) {
      prevPageStoryIdsRef.current = idsNow
      return
    }
    setSelectedIds((prev) => {
      const next = new Set(prev)
      let changed = false
      for (const id of prevPageStoryIdsRef.current) {
        if (!idsNow.has(id) && next.has(id)) {
          next.delete(id)
          changed = true
        }
      }
      prevPageStoryIdsRef.current = idsNow
      return changed ? next : prev
    })
  }, [stories, isLoading, listViewKey])

  useEffect(() => {
    setSelectAllEligibleSnapshot(null)
  }, [listViewKey])

  useEffect(() => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      let changed = false
      for (const s of stories) {
        if ((s.generated_test_cases ?? 0) > 0 && next.has(s.id)) {
          next.delete(s.id)
          changed = true
        }
      }
      return changed ? next : prev
    })
  }, [stories])

  useEffect(() => {
    const snapshotInvalid = stories.some(
      (s) => (s.generated_test_cases ?? 0) > 0 && selectedIds.has(s.id)
    )
    if (snapshotInvalid) setSelectAllEligibleSnapshot(null)
  }, [stories, selectedIds])

  const handleDeleteStory = async (storyId: number, displayKey: string) => {
    const confirmMessage = `Are you sure you want to delete ${displayKey}? This will also delete all related test cases and test steps.`
    if (!window.confirm(confirmMessage)) return

    setDeletingStoryId(storyId)
    try {
      const response = await userStoriesApi.delete(Number(projectId), storyId)
      toast.success(response.data.message || 'User story deleted successfully')
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.delete(storyId)
        return next
      })
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

  const syncFromIntegrationIsPrimary = hasPmIntegration && !hasConfiguredSync
  const syncNowVariant = hasConfiguredSync ? 'primary' : 'outline'
  const syncFromIntegrationVariant = syncFromIntegrationIsPrimary ? 'primary' : 'outline'

  const syncNowTooltip =
    !hasConfiguredSync
      ? 'Use Sync from Integration first to choose integration, item types, and sprint (Jira).'
      : undefined

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-gray-900">User Stories</h1>
          <p className="text-gray-600">Browse stories (read-only). Open a story to edit fields.</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-3">
          <Button
            variant={syncNowVariant}
            onClick={handleSyncNow}
            isLoading={isQuickSyncing}
            disabled={isQuickSyncing || !hasConfiguredSync}
            title={syncNowTooltip}
          >
            <ArrowPathIcon className="mr-2 h-4 w-4" />
            Sync now
          </Button>
          <Button
            variant={syncFromIntegrationVariant}
            onClick={() => setIsSyncModalOpen(true)}
            disabled={isQuickSyncing}
            title={
              syncFromIntegrationIsPrimary
                ? 'Choose integration, item types, and sprint — then you can use Sync now.'
                : undefined
            }
          >
            <ArrowPathIcon className="mr-2 h-4 w-4" />
            Sync from Integration
          </Button>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <PlusIcon className="mr-2 h-4 w-4" />
            Add Manual Story
          </Button>
          {selectedIds.size > 0 && (
            <Button
              variant="outline"
              type="button"
              onClick={() => void handleBulkGenerateTests()}
              disabled={generatingStoryId !== null || isQuickSyncing}
              title="Generate AI test cases for all selected stories (across pages)."
            >
              <SparklesIcon className="mr-2 h-4 w-4" />
              Generate tests ({selectedIds.size})
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
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
        <Card className="text-center">
          <div className="text-2xl font-bold text-gray-600">{stats.closed}</div>
          <div className="text-sm text-gray-500">Closed</div>
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
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {statusConfig[s]?.label ?? s}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {!isLoading && !integrationsReady && pagination.total === 0 && !hasListFilters && (
        <Card className="py-12 text-center">
          <ArrowPathIcon className="mx-auto mb-4 h-8 w-8 animate-spin text-primary-500" />
          <p className="text-gray-500">Loading…</p>
        </Card>
      )}

      {!isLoading && integrationsReady && pagination.total === 0 && !hasListFilters && (
        <Card className="py-12 text-center">
          <LinkIcon className="mx-auto mb-4 h-12 w-12 text-gray-300" />
          <h3 className="mb-2 text-lg font-medium text-gray-900">No User Stories Yet</h3>
          {hasPmIntegration ? (
            <>
              <p className="mb-4 max-w-md mx-auto text-gray-500">
                Your project is connected to a tool, but no work items have been imported yet. Use{' '}
                <span className="font-medium text-gray-700">Sync from Integration</span> to choose
                what to import (and for Jira, which sprint). After that,{' '}
                <span className="font-medium text-gray-700">Sync now</span> repeats the same scope.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Button
                  variant={syncFromIntegrationVariant}
                  onClick={() => setIsSyncModalOpen(true)}
                  disabled={isQuickSyncing}
                >
                  <ArrowPathIcon className="mr-2 h-4 w-4" />
                  Sync from Integration
                </Button>
                <Button
                  variant={syncNowVariant}
                  onClick={handleSyncNow}
                  isLoading={isQuickSyncing}
                  disabled={isQuickSyncing || !hasConfiguredSync}
                  title={syncNowTooltip}
                >
                  <ArrowPathIcon className="mr-2 h-4 w-4" />
                  Sync now
                </Button>
                <Link to={`/projects/${projectId}/integrations`}>
                  <Button variant="outline">
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Manage integrations
                  </Button>
                </Link>
              </div>
            </>
          ) : (
            <>
              <p className="mb-4 max-w-md mx-auto text-gray-500">
                Connect to Jira, Redmine, or Azure DevOps to import user stories, or add them
                manually.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link to={`/projects/${projectId}/integrations`}>
                  <Button variant="primary">
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Configure Integrations
                  </Button>
                </Link>
                <Button
                  variant="outline"
                  onClick={handleSyncNow}
                  isLoading={isQuickSyncing}
                  disabled={isQuickSyncing || !hasConfiguredSync}
                  title={syncNowTooltip}
                >
                  <ArrowPathIcon className="mr-2 h-4 w-4" />
                  Sync now
                </Button>
              </div>
            </>
          )}
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
          <div className="mt-4 flex flex-wrap items-center gap-4 border-b border-gray-100 px-2 pb-3">
            <label className="inline-flex cursor-pointer select-none items-center gap-2 text-sm text-gray-700">
              <input
                ref={selectAllCheckboxRef}
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={isGlobalEligibleSelection}
                onChange={() => void handleSelectAllEligibleAcrossPages()}
                disabled={
                  stories.length === 0 ||
                  isSelectingAllEligible ||
                  generatingStoryId !== null
                }
                aria-label="Select all eligible stories on all pages"
              />
              {isSelectingAllEligible ? (
                <span className="text-gray-500">Selecting…</span>
              ) : (
                <span>
                  Select all eligible{' '}
                  <span className="text-gray-500">(all pages — stories without generated tests)</span>
                </span>
              )}
            </label>
            {selectedIds.size > 0 && (
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() => void handleBulkGenerateTests()}
                disabled={generatingStoryId !== null || isQuickSyncing || isSelectingAllEligible}
                title="Generate tests for every selected story"
              >
                <SparklesIcon className="mr-1.5 h-4 w-4" />
                Generate tests ({selectedIds.size})
              </Button>
            )}
            {selectedIds.size > 0 && (
              <Button
                variant="ghost"
                size="sm"
                type="button"
                className="text-gray-600"
                onClick={() => {
                  setSelectedIds(new Set())
                  setSelectAllEligibleSnapshot(null)
                }}
              >
                Clear selection
              </Button>
            )}
          </div>
          <div className="mt-4 divide-y divide-gray-100">
            {stories.map((story) => (
              <UserStoryListRow
                key={story.id}
                story={story}
                projectId={projectId!}
                selected={selectedIds.has(story.id)}
                onToggleSelect={handleToggleSelect}
                generatingStoryId={generatingStoryId}
                isBulkGenerating={isBulkGenerating}
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
        onSyncComplete={handleIntegrationSyncComplete}
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

      <TestGenerationInfoDialog
        isOpen={infoDialogOpen}
        message={infoMessage}
        onClose={closeInfoDialog}
      />
    </div>
  )
}
