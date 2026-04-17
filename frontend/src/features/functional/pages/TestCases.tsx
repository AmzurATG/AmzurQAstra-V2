import { useState, useCallback, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { PaginationBar } from '@common/components/ui/PaginationBar'
import { useProjectStore } from '@common/store/projectStore'
import { PlusIcon, PlayIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { testCasesApi } from '../api'
import { projectsApi } from '@common/api/projects'
import { useTestCaseFilters } from '../hooks/useTestCaseFilters'
import { useTestRunExecution } from '../hooks/useTestRunExecution'
import { TestCaseTable } from '../components/TestCaseTable'
import { ExecutionPanel } from '../components/ExecutionPanel'
import { CredentialsOverride } from '../components/CredentialsOverride'
import { TestCaseEditModal } from '../components/TestCaseEditModal'
import type { TestCase, TestStep, TestRunCreateRequest } from '../types'

const testCaseSelectionKey = (projectId: string) => `qastra:test-case-selection:${projectId}`

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

/** If store has no app URL, one silent GET may recover after Settings save or another tab. */
async function ensureProjectHasAppUrl(projectId: string | undefined): Promise<boolean> {
  if (!projectId) return false
  const store = useProjectStore.getState()
  if (store.currentProject?.app_url) return true
  await store.revalidateProject(projectId)
  return !!(useProjectStore.getState().currentProject?.app_url)
}

export default function TestCases() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { revalidateProject } = useProjectStore()
  const pid = Number(projectId)

  const {
    testCases,
    isLoading,
    searchQuery,
    setSearchQuery,
    priorityFilter,
    setPriorityFilter,
    categoryFilter,
    setCategoryFilter,
    statusFilter: _statusFilter,
    setStatusFilter: _setStatusFilter,
    page,
    setPage,
    pagination,
    loadTestCases
  } = useTestCaseFilters(projectId)

  const exec = useTestRunExecution()

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

  const listViewKey = `${page}|${searchQuery}|${priorityFilter}|${categoryFilter}|${_statusFilter}`
  const prevListViewKeyRef = useRef<string | null>(null)
  const prevPageCaseIdsRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    if (projectId) {
      void revalidateProject(projectId)
    }
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

  // After refresh on the same list view, drop selections for rows that disappeared (e.g. delete).
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

  // Handlers
  const toggleRowExpansion = useCallback(async (id: number) => {
    setExpandedRows(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
    
    if (!stepsCache[id]) {
      setLoadingSteps(prev => new Set(prev).add(id))
      try {
        const res = await testCasesApi.getWithSteps(id)
        setStepsCache(prev => ({ ...prev, [id]: res.data.steps || [] }))
      } catch (err) {
        toast.error('Failed to load steps')
      } finally {
        setLoadingSteps(prev => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
      }
    }
  }, [stepsCache])

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
    } catch (err) {
      toast.error('Delete failed')
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
    } catch (err) {
      toast.error('Update failed')
    } finally {
      setIsSaving(false)
    }
  }

  // Execution Handlers (read latest project from store so runs use URL after revalidate)
  const buildRequest = (tcIds?: number[]): TestRunCreateRequest => {
    const cp = useProjectStore.getState().currentProject
    return {
      project_id: pid,
      app_url: cp?.app_url || undefined,
      test_case_ids: tcIds,
      credentials: (overrideUser || overridePass)
        ? { username: overrideUser || undefined, password: overridePass || undefined }
        : undefined,
    }
  }

  const runSingle = async (tcId: number) => {
    if (!(await ensureProjectHasAppUrl(projectId))) {
      toast.error('Set App URL first')
      return
    }
    toast.promise(exec.startRun(buildRequest([tcId])), {
      loading: 'Initializing browser...',
      success: 'Execution started',
      error: (err) => `Failed: ${err.message || err}`
    })
  }

  const runSelected = async () => {
    if (!(await ensureProjectHasAppUrl(projectId))) {
      toast.error('Set App URL first')
      return
    }
    if (selectedIds.size === 0) { toast.error('Select cases first'); return }
    toast.promise(exec.startRun(buildRequest(Array.from(selectedIds))), {
      loading: `Starting ${selectedIds.size} tests...`,
      success: 'Execution started',
      error: (err) => `Failed: ${err.message || err}`
    })
  }

  const runAll = async () => {
    if (!(await ensureProjectHasAppUrl(projectId))) {
      toast.error('Set App URL first')
      return
    }
    toast.promise(exec.startRun(buildRequest()), {
      loading: 'Preparing full test run...',
      success: 'Execution started',
      error: (err) => `Failed: ${err.message || err}`
    })
  }

  const saveCredentialsToProject = async () => {
    if (!pid || !overrideUser || !overridePass) return
    try {
      const updated = await projectsApi.update(pid, {
        app_credentials: {
          username: overrideUser,
          password: overridePass
        }
      })
      useProjectStore.getState().setCurrentProject(updated)
      toast.success('Credentials saved to project settings')
      setShowCreds(false)
    } catch (err) {
      toast.error('Failed to save credentials')
    }
  }

  const isRunning = exec.progress && !['completed', 'passed', 'failed', 'error', 'cancelled'].includes(exec.progress.status)
  const isDone = exec.progress && !isRunning

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Test Cases</h1>
          <p className="text-gray-600">Manage and execute functional tests</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadTestCases} disabled={isLoading}>
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          {selectedIds.size > 0 && (
            <Button variant="outline" onClick={runSelected} disabled={!!isRunning}>
              <PlayIcon className="w-4 h-4 mr-1" /> Run ({selectedIds.size})
            </Button>
          )}
          <Button onClick={runAll} disabled={!!isRunning || testCases.length === 0}>
            <PlayIcon className="w-4 h-4 mr-2" /> Run All
          </Button>
          <Button>
            <PlusIcon className="w-4 h-4 mr-2" /> New Case
          </Button>
        </div>
      </div>

      <CredentialsOverride 
        projectId={projectId}
        showCreds={showCreds} setShowCreds={setShowCreds}
        overrideUser={overrideUser} setOverrideUser={setOverrideUser}
        overridePass={overridePass} setOverridePass={setOverridePass}
        onSaveToProject={saveCredentialsToProject}
      />

      <ExecutionPanel 
        progress={exec.progress} 
        isRunning={!!isRunning} 
        isCreating={exec.isCreating}
        error={exec.error}
        isDone={!!isDone} 
        onCancel={exec.cancelRun}
        onViewDetails={() => navigate(`/projects/${projectId}/test-runs/${exec.runId}`)}
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
          <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
          </select>
          <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
            <option value="all">All Categories</option>
            <option value="smoke">Smoke</option><option value="regression">Regression</option><option value="e2e">E2E</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-12"><ArrowPathIcon className="w-8 h-8 mx-auto animate-spin text-primary-500" /></div>
        ) : (
          <TestCaseTable 
            projectId={projectId} testCases={testCases}
            expandedRows={expandedRows} toggleRowExpansion={toggleRowExpansion}
            loadingSteps={loadingSteps} stepsCache={stepsCache}
            onEdit={(tc) => { setEditingTestCase(tc); setIsEditModalOpen(true) }}
            onDelete={handleDelete} onRunSingle={runSingle}
            selectedIds={selectedIds} 
            onToggleSelect={(id) => setSelectedIds(prev => {
              const next = new Set(prev)
              if (next.has(id)) next.delete(id); else next.add(id)
              return next
            })}
            onToggleAll={handleToggleAll}
            isRunning={!!isRunning}
            progress={exec.progress}
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
        isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)}
        testCase={editingTestCase} setTestCase={setEditingTestCase}
        onSave={handleSave} isSaving={isSaving}
      />
    </div>
  )
}
