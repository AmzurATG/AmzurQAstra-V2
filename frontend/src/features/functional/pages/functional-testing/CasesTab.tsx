import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowPathIcon, PlayIcon, PlusIcon, DocumentArrowUpIcon, CheckBadgeIcon, Squares2X2Icon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { Card } from '@common/components/ui/Card'
import { PaginationBar } from '@common/components/ui/PaginationBar'
import { projectsApi } from '@common/api/projects'
import { useProjectStore } from '@common/store/projectStore'

import { testCasesApi, testStepsApi } from '../../api'
import { CredentialsOverride } from '../../components/CredentialsOverride'
import { TestCaseEditModal } from '../../components/TestCaseEditModal'
import { CsvImportModal } from '../../components/CsvImportModal'
import { ExcelImportModal } from '../../components/ExcelImportModal'
import { TestCaseTable } from '../../components/TestCaseTable'
import { useRequiredActiveTestRun } from '../../context/ActiveTestRunProvider'
import { useTestCaseFilters } from '../../hooks/useTestCaseFilters'
import type { TestCase, TestRunCreateRequest, TestStep } from '../../types'

const testCaseSelectionKey = (projectId: string) =>
  `qastra:test-case-selection:${projectId}`

function loadTestCaseSelection(projectId: string | undefined): Set<number> {
  if (!projectId || typeof window === 'undefined') return new Set()
  try {
    const raw = sessionStorage.getItem(testCaseSelectionKey(projectId))
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

/**
 * Functional Testing → Cases tab.
 *
 * Owns: the "ready" pool of test cases, bulk selection, run dispatch.
 *
 * Does NOT own (moved up to the shell + provider):
 *   - Execution progress UI (pinned ExecutionPanel)
 *   - Live polling (ActiveTestRunProvider)
 *   - App URL gate (lifted into provider.ensureProjectHasAppUrl)
 */
export default function CasesTab() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, revalidateProject } = useProjectStore()
  const pid = Number(projectId)

  const activeRun = useRequiredActiveTestRun()

  const {
    testCases,
    isLoading,
    searchQuery,
    setSearchQuery,
    priorityFilter,
    setPriorityFilter,
    categoryFilter,
    setCategoryFilter,
    statusFilter,
    setStatusFilter,
    page,
    setPage,
    pagination,
    loadTestCases,
    loadTestCasesAfterImport,
  } = useTestCaseFilters(projectId)

  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [loadingSteps, setLoadingSteps] = useState<Set<number>>(new Set())
  const [stepsCache, setStepsCache] = useState<Record<number, TestStep[]>>({})
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() =>
    loadTestCaseSelection(projectId)
  )

  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [isExcelImportModalOpen, setIsExcelImportModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingTestCase, setEditingTestCase] = useState<TestCase | null>(null)
  const [isCreatingNew, setIsCreatingNew] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [showCreds, setShowCreds] = useState(false)
  const [overrideUser, setOverrideUser] = useState('')
  const [overridePass, setOverridePass] = useState('')
  const [isRunningAll, setIsRunningAll] = useState(false)
  const [isSelectingAll, setIsSelectingAll] = useState(false)
  const [executionStrategy, setExecutionStrategy] = useState<'sequential' | 'grouped_parallel' | 'playwright'>('grouped_parallel')

  // Pre-populate credentials from project settings
  useEffect(() => {
    if (currentProject?.has_credentials) {
      setOverrideUser((prev) => prev || currentProject.app_username || '')
      setOverridePass((prev) => prev || currentProject.app_password || '')
    }
  }, [currentProject])

  const listViewKey = `${page}|${searchQuery}|${priorityFilter}|${categoryFilter}|${statusFilter}`
  const prevListViewKeyRef = useRef<string | null>(null)
  const prevPageCaseIdsRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    if (projectId) void revalidateProject(projectId)
  }, [projectId, revalidateProject])

  useEffect(() => {
    setSelectedIds(loadTestCaseSelection(projectId))
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    try {
      sessionStorage.setItem(
        testCaseSelectionKey(projectId),
        JSON.stringify([...selectedIds])
      )
    } catch {
      // ignore quota / private mode
    }
  }, [projectId, selectedIds])

  // Drop selections for rows that disappeared within the same list view.
  useEffect(() => {
    if (isLoading) return
    const idsNow = new Set(testCases.map((t) => t.id))
    const sameView = prevListViewKeyRef.current === listViewKey
    prevListViewKeyRef.current = listViewKey

    if (!sameView) {
      prevPageCaseIdsRef.current = idsNow
      return
    }

    setSelectedIds((prev) => {
      const next = new Set(prev)
      let changed = false
      for (const id of prevPageCaseIdsRef.current) {
        if (!idsNow.has(id) && next.has(id)) {
          next.delete(id)
          changed = true
        }
      }
      prevPageCaseIdsRef.current = idsNow
      return changed ? next : prev
    })
  }, [testCases, isLoading, listViewKey])

  const toggleRowExpansion = useCallback(
    async (id: number) => {
      setExpandedRows((prev) => {
        const next = new Set(prev)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        return next
      })

      if (!stepsCache[id]) {
        setLoadingSteps((prev) => new Set(prev).add(id))
        try {
          const res = await testCasesApi.getWithSteps(id)
          setStepsCache((prev) => ({ ...prev, [id]: res.data.steps || [] }))
        } catch {
          toast.error('Failed to load steps')
        } finally {
          setLoadingSteps((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
        }
      }
    },
    [stepsCache]
  )

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Delete "${title}"?`)) return
    try {
      await testCasesApi.delete(id)
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      toast.success('Deleted')
      loadTestCases()
    } catch (err: unknown) {
      const detail =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Delete failed')
    }
  }

  const closeEditModal = () => {
    setIsEditModalOpen(false)
    setIsCreatingNew(false)
    setEditingTestCase(null)
  }

  const handleSave = async () => {
    if (!editingTestCase) return
    setIsSaving(true)
    try {
      if (isCreatingNew) {
        await testCasesApi.create({
          project_id: editingTestCase.project_id,
          title: editingTestCase.title,
          description: editingTestCase.description,
          priority: editingTestCase.priority,
          category: editingTestCase.category,
          status: editingTestCase.status,
          is_generated: false,
        })
        toast.success('Manual case created')
      } else {
        await testCasesApi.update(editingTestCase.id, editingTestCase)
        toast.success('Updated')
      }
      closeEditModal()
      loadTestCases()
    } catch {
      toast.error(isCreatingNew ? 'Failed to create case' : 'Update failed')
    } finally {
      setIsSaving(false)
    }
  }

  const buildRequest = (tcIds?: number[]): TestRunCreateRequest => {
    // Always read the latest project so newly-saved app_url takes effect.
    const cp = useProjectStore.getState().currentProject
    return {
      project_id: pid,
      app_url: cp?.app_url || undefined,
      test_case_ids: tcIds,
      execution_strategy: executionStrategy,
      credentials:
        overrideUser || overridePass
          ? {
              username: overrideUser || undefined,
              password: overridePass || undefined,
            }
          : undefined,
    }
  }

  const dispatchRun = async (
    request: TestRunCreateRequest,
    loadingMsg: string
  ) => {
    if (activeRun.isCreating || activeRun.isRunning) return
    if (!(await activeRun.ensureProjectHasAppUrl())) {
      toast.error('Set App URL first')
      return
    }
    const runPromise = activeRun.startRun(request).then((runId) => {
      if (runId) {
        navigate(`/projects/${projectId}/functional-testing/live`)
      }
      return runId
    })
    toast.promise(runPromise, {
      loading: loadingMsg,
      success: (id) => (id ? 'Execution started' : 'Could not start run'),
      error: (err) => `Failed: ${(err as Error).message || err}`,
    })
  }

  const runSingle = (tcId: number) =>
    dispatchRun(buildRequest([tcId]), 'Starting test…')

  /** Resolve every selected row (fetch if not on current page) and ensure all are `ready`. */
  const resolveRunnableSelectedIds = async (): Promise<number[] | null> => {
    const ids = Array.from(selectedIds)
    const byId = new Map(testCases.map((tc) => [tc.id, tc]))
    const missing = ids.filter((id) => !byId.has(id))
    try {
      const fetched = await Promise.all(
        missing.map((id) => testCasesApi.get(id).then((r) => r.data))
      )
      for (const tc of fetched) {
        if (tc.project_id !== pid) {
          toast.error('Selected test case does not belong to this project')
          return null
        }
        byId.set(tc.id, tc)
      }
    } catch {
      toast.error('Could not verify status for some selected test cases')
      return null
    }
    const blocked: TestCase[] = []
    for (const id of ids) {
      const tc = byId.get(id)
      if (!tc) {
        toast.error('Some selected test cases were not found')
        return null
      }
      if (tc.status !== 'ready') blocked.push(tc)
    }
    if (blocked.length > 0) {
      const statuses = [...new Set(blocked.map((t) => t.status))].join(', ')
      toast.error(
        `Only Ready cases can run. ${blocked.length} selected case(s) are not runnable (status: ${statuses}). Mark them Ready or deselect.`
      )
      return null
    }
    return ids
  }

  const runSelected = async () => {
    if (selectedIds.size === 0) {
      toast.error('Select cases first')
      return
    }
    const runnableIds = await resolveRunnableSelectedIds()
    if (!runnableIds) return
    dispatchRun(buildRequest(runnableIds), `Starting ${runnableIds.length} selected test${runnableIds.length !== 1 ? 's' : ''}…`)
  }

  /**
   * Promote every draft case to ready first, then kick off a run over all ready cases.
   * Deprecated cases are skipped by the backend automatically.
   */
  const runAll = async () => {
    if (activeRun.isCreating || activeRun.isRunning || isRunningAll) return
    if (!(await activeRun.ensureProjectHasAppUrl())) {
      toast.error('Set App URL first')
      return
    }
    setIsRunningAll(true)
    try {
      const promoteRes = await testCasesApi.promoteAllDraft(pid)
      const promoted = promoteRes.data.promoted
      if (promoted > 0) {
        toast.success(`${promoted} draft case${promoted !== 1 ? 's' : ''} promoted to Ready`)
        // Refresh the list so the UI reflects the new statuses
        loadTestCases()
      }

      const runPromise = activeRun.startRun(buildRequest(undefined)).then((runId) => {
        if (runId) navigate(`/projects/${projectId}/functional-testing/live`)
        return runId
      })
      toast.promise(runPromise, {
        loading: 'Starting test run…',
        success: (id) => (id ? 'Execution started' : 'Could not start run'),
        error: (err) => `Failed: ${(err as Error).message || err}`,
      })
    } catch (err) {
      toast.error(`Failed to start run: ${(err as Error).message || err}`)
    } finally {
      setIsRunningAll(false)
    }
  }

  /**
   * Fetch every non-deprecated test case ID across all pages and add to selection.
   * Uses a large page_size so a single request covers even big projects.
   */
  const handleSelectAll = async () => {
    if (isSelectingAll) return
    setIsSelectingAll(true)
    try {
      const res = await testCasesApi.list(pid, { page_size: 2000, page: 1 })
      const allIds = res.data.items
        .filter((tc) => tc.status !== 'deprecated')
        .map((tc) => tc.id)
      if (allIds.length === 0) {
        toast('No selectable test cases found')
        return
      }
      setSelectedIds(new Set(allIds))
      toast.success(`${allIds.length} case${allIds.length !== 1 ? 's' : ''} selected`)
    } catch {
      toast.error('Could not fetch all test cases')
    } finally {
      setIsSelectingAll(false)
    }
  }

  /** True when any selected row visible on this page is not `ready` (instant toolbar feedback). */
  const selectionIncludesNonReadyOnPage = useMemo(() => {
    const idSet = new Set(selectedIds)
    for (const tc of testCases) {
      if (idSet.has(tc.id) && tc.status !== 'ready') return true
    }
    return false
  }, [selectedIds, testCases])

  const handleBulkStatus = async (newStatus: 'ready' | 'draft' | 'deprecated') => {
    if (!projectId || selectedIds.size === 0) {
      toast.error('Select cases first')
      return
    }
    const ids = Array.from(selectedIds)
    const label = newStatus === 'ready' ? 'Ready' : newStatus === 'draft' ? 'Draft' : 'Deprecated'
    try {
      const res = await testCasesApi.bulkUpdateStatus(pid, ids, newStatus as import('../../types').TestCaseStatus)
      const updated = res.data.updated
      toast.success(`${updated} case${updated !== 1 ? 's' : ''} marked as ${label}`)
      setSelectedIds(new Set())
      loadTestCases()
    } catch {
      toast.error(`Failed to update status to ${label}`)
    }
  }

  const saveCredentialsToProject = async () => {
    if (!pid || !overrideUser || !overridePass) return
    try {
      const updated = await projectsApi.update(pid, {
        app_credentials: {
          username: overrideUser,
          password: overridePass,
        },
      })
      useProjectStore.getState().setCurrentProject(updated)
      toast.success('Credentials saved to project settings')
      setShowCreds(false)
    } catch {
      toast.error('Failed to save credentials')
    }
  }

  const handleCreateManualCase = () => {
    if (!pid) return
    // Open the form first; persist only when the user clicks Save Changes.
    // Manual cases in Functional Testing default to "ready" (execution workspace).
    setEditingTestCase({
      id: 0,
      case_number: 0,
      project_id: pid,
      title: '',
      description: '',
      priority: 'medium',
      category: 'regression',
      status: 'ready',
      is_generated: false,
      is_automated: false,
      integrity_check: false,
      steps_count: 0,
      created_at: '',
      updated_at: '',
    })
    setIsCreatingNew(true)
    setIsEditModalOpen(true)
  }

  const handleToggleAll = useCallback(() => {
    const pageIds = testCases.map((t) => t.id)
    if (pageIds.length === 0) return
    setSelectedIds((prev) => {
      const allOnPage = pageIds.every((id) => prev.has(id))
      const next = new Set(prev)
      if (allOnPage) {
        pageIds.forEach((id) => next.delete(id))
      } else {
        pageIds.forEach((id) => next.add(id))
      }
      return next
    })
  }, [testCases])

  const handleStepUpdate = useCallback(
    async (stepId: number, data: Partial<TestStep>) => {
      await testStepsApi.update(stepId, data)
      // Refresh the cached steps for the test case that owns this step
      for (const [tcId, steps] of Object.entries(stepsCache)) {
        const idx = steps.findIndex((s) => s.id === stepId)
        if (idx !== -1) {
          const res = await testCasesApi.getWithSteps(Number(tcId))
          setStepsCache((prev) => ({ ...prev, [Number(tcId)]: res.data.steps || [] }))
          break
        }
      }
    },
    [stepsCache]
  )

  const runAllDisabled =
    activeRun.isCreating || activeRun.isRunning || isRunningAll

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Test Cases</h2>
          <p className="text-sm text-gray-500">
            Cases promoted from a user story, or created directly here. Select
            one or more to run them.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={loadTestCases} disabled={isLoading}>
            <ArrowPathIcon
              className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
            />{' '}
            Refresh
          </Button>

          {/* Select All — picks every non-deprecated case across all pages */}
          <Button
            variant="outline"
            onClick={() => void handleSelectAll()}
            disabled={isSelectingAll}
            title="Select every non-deprecated test case across all pages"
          >
            {isSelectingAll
              ? <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
              : <Squares2X2Icon className="w-4 h-4 mr-2" />
            }
            Select All
          </Button>

          {selectedIds.size > 0 && (
            <>
              <Button
                onClick={() => void runSelected()}
                disabled={
                  activeRun.isCreating ||
                  activeRun.isRunning ||
                  selectionIncludesNonReadyOnPage
                }
                title={
                  selectionIncludesNonReadyOnPage
                    ? 'Some selected cases are not Ready — mark them Ready or deselect first'
                    : 'Run selected test cases one by one'
                }
              >
                <PlayIcon className="w-4 h-4 mr-1" /> Run Selected ({selectedIds.size})
              </Button>
              <Button
                variant="outline"
                onClick={() => handleBulkStatus('ready')}
                title="Mark selected cases as Ready"
              >
                <CheckBadgeIcon className="w-4 h-4 mr-1 text-green-600" />
                Mark Ready ({selectedIds.size})
              </Button>
              <Button
                variant="outline"
                onClick={() => handleBulkStatus('draft')}
                title="Mark selected cases as Draft"
              >
                Mark Draft ({selectedIds.size})
              </Button>
            </>
          )}

          {/* Run All — auto-promotes drafts to ready, then runs everything */}
          <Button
            onClick={() => void runAll()}
            disabled={runAllDisabled}
            title="Promote any draft cases to Ready, then run all test cases"
          >
            {isRunningAll
              ? <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
              : <PlayIcon className="w-4 h-4 mr-2" />
            }
            Run All
          </Button>

          <select
            value={executionStrategy}
            onChange={(e) => setExecutionStrategy(e.target.value as 'sequential' | 'grouped_parallel' | 'playwright')}
            className="px-3 py-2 border rounded-lg text-sm bg-white"
            title="Choose how test cases are executed"
          >
            <option value="sequential">Sequential (AI)</option>
            <option value="playwright">⚡ Playwright Fast (no AI)</option>
            <option value="grouped_parallel">Grouped Parallel (AI lanes)</option>
          </select>

          <Button variant="outline" onClick={() => setIsImportModalOpen(true)}>
            <DocumentArrowUpIcon className="w-4 h-4 mr-2" /> Import CSV
          </Button>
          <Button variant="outline" onClick={() => setIsExcelImportModalOpen(true)}>
            <DocumentArrowUpIcon className="w-4 h-4 mr-2" /> Import Excel
          </Button>
          <Button onClick={handleCreateManualCase}>
            <PlusIcon className="w-4 h-4 mr-2" /> New Case
          </Button>
        </div>
      </div>

      <CredentialsOverride
        projectId={projectId}
        showCreds={showCreds}
        setShowCreds={setShowCreds}
        overrideUser={overrideUser}
        setOverrideUser={setOverrideUser}
        overridePass={overridePass}
        setOverridePass={setOverridePass}
        onSaveToProject={saveCredentialsToProject}
      />

      {/* Inline hint when viewing draft cases */}
      {statusFilter === 'draft' && testCases.length > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
          <PlayIcon className="w-4 h-4 text-amber-500 shrink-0" />
          <span>
            {testCases.length} draft case{testCases.length !== 1 ? 's' : ''} visible — click <strong>Run All</strong> to auto-promote them to Ready and run everything.
          </span>
        </div>
      )}

      <Card>
        <div className="flex flex-col md:flex-row gap-4 mb-4">
          <input
            type="text"
            placeholder="Search title, Jira key, US-#, or story id…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
            title="Status lens"
          >
            <option value="all">All statuses</option>
            <option value="ready">Ready (for execution)</option>
            <option value="draft">Draft (needs promotion)</option>
            <option value="deprecated">Deprecated</option>
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            <option value="all">All Categories</option>
            <option value="smoke">Smoke</option>
            <option value="regression">Regression</option>
            <option value="e2e">E2E</option>
            <option value="integration">Integration</option>
            <option value="sanity">Sanity</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <ArrowPathIcon className="w-8 h-8 mx-auto animate-spin text-primary-500" />
          </div>
        ) : testCases.length === 0 ? (
          <div className="text-center py-12 text-sm text-gray-500">
            {statusFilter === 'ready'
              ? 'No ready cases yet. Promote cases from a user story or create a new manual case here.'
              : 'No cases match the current filter.'}
          </div>
        ) : (
          <TestCaseTable
            projectId={projectId}
            testCases={testCases}
            expandedRows={expandedRows}
            toggleRowExpansion={toggleRowExpansion}
            loadingSteps={loadingSteps}
            stepsCache={stepsCache}
            onEdit={(tc) => {
              setEditingTestCase(tc)
              setIsCreatingNew(false)
              setIsEditModalOpen(true)
            }}
            onDelete={handleDelete}
            onRunSingle={runSingle}
            selectedIds={selectedIds}
            onToggleSelect={(id) =>
              setSelectedIds((prev) => {
                const next = new Set(prev)
                if (next.has(id)) next.delete(id)
                else next.add(id)
                return next
              })
            }
            onToggleAll={handleToggleAll}
            isRunning={activeRun.isRunning}
            isCreating={activeRun.isCreating}
            progress={activeRun.progress}
            onStepUpdate={handleStepUpdate}
          />
        )}
        <PaginationBar
          page={page}
          totalPages={pagination.total_pages}
          hasPrev={pagination.has_prev}
          hasNext={pagination.has_next}
          onPageChange={setPage}
        />
      </Card>

      <CsvImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        projectId={pid}
        onImported={({ wroteCases }) => {
          if (wroteCases) void loadTestCasesAfterImport()
          else void loadTestCases()
        }}
      />

      <ExcelImportModal
        isOpen={isExcelImportModalOpen}
        onClose={() => setIsExcelImportModalOpen(false)}
        projectId={pid}
        onImported={({ wroteCases }) => {
          if (wroteCases) void loadTestCasesAfterImport()
          else void loadTestCases()
        }}
      />

      <TestCaseEditModal
        isOpen={isEditModalOpen}
        onClose={closeEditModal}
        testCase={editingTestCase}
        setTestCase={setEditingTestCase}
        onSave={handleSave}
        isSaving={isSaving}
        title={isCreatingNew ? 'New Manual Test Case' : 'Edit Test Case'}
      />
    </div>
  )
}
