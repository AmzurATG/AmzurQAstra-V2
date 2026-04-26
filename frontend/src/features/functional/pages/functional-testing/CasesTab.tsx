import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowPathIcon, PlayIcon, PlusIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { Card } from '@common/components/ui/Card'
import { PaginationBar } from '@common/components/ui/PaginationBar'
import { projectsApi } from '@common/api/projects'
import { useProjectStore } from '@common/store/projectStore'

import { testCasesApi, testStepsApi } from '../../api'
import { CredentialsOverride } from '../../components/CredentialsOverride'
import { TestCaseEditModal } from '../../components/TestCaseEditModal'
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
  } = useTestCaseFilters(projectId)

  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [loadingSteps, setLoadingSteps] = useState<Set<number>>(new Set())
  const [stepsCache, setStepsCache] = useState<Record<number, TestStep[]>>({})
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() =>
    loadTestCaseSelection(projectId)
  )

  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingTestCase, setEditingTestCase] = useState<TestCase | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const [showCreds, setShowCreds] = useState(false)
  const [overrideUser, setOverrideUser] = useState('')
  const [overridePass, setOverridePass] = useState('')

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

  const handleSave = async () => {
    if (!editingTestCase) return
    setIsSaving(true)
    try {
      await testCasesApi.update(editingTestCase.id, editingTestCase)
      toast.success('Updated')
      setIsEditModalOpen(false)
      loadTestCases()
    } catch {
      toast.error('Update failed')
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
    dispatchRun(buildRequest([tcId]), 'Initializing browser…')

  const runSelected = () => {
    if (selectedIds.size === 0) {
      toast.error('Select cases first')
      return
    }
    dispatchRun(
      buildRequest(Array.from(selectedIds)),
      `Starting ${selectedIds.size} tests…`
    )
  }

  const runAll = () =>
    dispatchRun(buildRequest(), 'Preparing full test run…')

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

  const handleCreateManualCase = async () => {
    if (!pid) return
    try {
      // Inside Functional Testing, manual cases skip promotion: they're born
      // "ready". Contrast with authoring inside a User Story, which lands as
      // draft. Rationale: users here are already in the execution workspace.
      const res = await testCasesApi.create({
        project_id: pid,
        title: 'Untitled manual case',
        description: '',
        priority: 'medium',
        category: 'regression',
        status: 'ready',
        is_generated: false,
      })
      toast.success('Manual case created')
      setEditingTestCase(res.data)
      setIsEditModalOpen(true)
      loadTestCases()
    } catch {
      toast.error('Failed to create case')
    }
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

  const runAllLabel =
    statusFilter === 'ready' ? 'Run All Ready' : 'Run All (filtered)'
  const runDisabled =
    activeRun.isCreating || activeRun.isRunning || testCases.length === 0

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
          {selectedIds.size > 0 && (
            <Button
              variant="outline"
              onClick={runSelected}
              disabled={activeRun.isCreating || activeRun.isRunning}
            >
              <PlayIcon className="w-4 h-4 mr-1" /> Run ({selectedIds.size})
            </Button>
          )}
          <Button onClick={runAll} disabled={runDisabled}>
            <PlayIcon className="w-4 h-4 mr-2" /> {runAllLabel}
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

      <TestCaseEditModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        testCase={editingTestCase}
        setTestCase={setEditingTestCase}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  )
}
