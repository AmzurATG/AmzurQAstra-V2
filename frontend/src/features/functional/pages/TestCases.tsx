import React, { useState, useCallback } from 'react'
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

export default function TestCases() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject } = useProjectStore()
  const pid = Number(projectId)

  // Hooks
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
    loadTestCases
  } = useTestCaseFilters(projectId)

  const exec = useTestRunExecution()

  // Local State
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [loadingSteps, setLoadingSteps] = useState<Set<number>>(new Set())
  const [stepsCache, setStepsCache] = useState<Record<number, TestStep[]>>({})
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingTestCase, setEditingTestCase] = useState<TestCase | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  
  const [showCreds, setShowCreds] = useState(false)
  const [overrideUser, setOverrideUser] = useState('')
  const [overridePass, setOverridePass] = useState('')

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

  // Execution Handlers
  const buildRequest = (tcIds?: number[]): TestRunCreateRequest => ({
    project_id: pid,
    app_url: currentProject?.app_url || undefined,
    test_case_ids: tcIds,
    credentials: (overrideUser || overridePass)
      ? { username: overrideUser || undefined, password: overridePass || undefined }
      : undefined,
  })

  const runSingle = async (tcId: number) => {
    if (!currentProject?.app_url) { toast.error('Set App URL first'); return }
    toast.promise(exec.startRun(buildRequest([tcId])), {
      loading: 'Initializing browser...',
      success: 'Execution started',
      error: (err) => `Failed: ${err.message || err}`
    })
  }

  const runSelected = async () => {
    if (!currentProject?.app_url) { toast.error('Set App URL first'); return }
    if (selectedIds.size === 0) { toast.error('Select cases first'); return }
    toast.promise(exec.startRun(buildRequest(Array.from(selectedIds))), {
      loading: `Starting ${selectedIds.size} tests...`,
      success: 'Execution started',
      error: (err) => `Failed: ${err.message || err}`
    })
  }

  const runAll = async () => {
    if (!currentProject?.app_url) { toast.error('Set App URL first'); return }
    toast.promise(exec.startRun(buildRequest()), {
      loading: 'Preparing full test run...',
      success: 'Execution started',
      error: (err) => `Failed: ${err.message || err}`
    })
  }

  const saveCredentialsToProject = async () => {
    if (!pid || !overrideUser || !overridePass) return
    try {
      await projectsApi.update(pid, {
        app_credentials: {
          username: overrideUser,
          password: overridePass
        }
      })
      toast.success('Credentials saved to project settings')
      // Refresh project to update header
      const { fetchProject } = useProjectStore.getState()
      await fetchProject(projectId!)
      setShowCreds(false)
    } catch (err) {
      toast.error('Failed to save credentials')
    }
  }

  const isRunning = exec.progress && !['completed', 'passed', 'failed', 'error', 'cancelled'].includes(exec.progress.status)
  const isDone = exec.progress && !isRunning

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
            type="text" placeholder="Search..." value={searchQuery}
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
            onToggleAll={() => setSelectedIds(prev => prev.size === testCases.length ? new Set() : new Set(testCases.map(t => t.id)))}
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
