import React, { useState, useEffect, Fragment } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Dialog, Transition } from '@headlessui/react'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import {
  PlusIcon,
  SparklesIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  LinkIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { testCasesApi } from '../api'
import type { TestCase, TestStep, TestCasePriority, TestCaseCategory, TestCaseStatus } from '../types'
import toast from 'react-hot-toast'

const PRIORITY_OPTIONS = ['critical', 'high', 'medium', 'low'] as const
const CATEGORY_OPTIONS = ['smoke', 'regression', 'e2e', 'integration', 'sanity'] as const
const STATUS_OPTIONS = ['draft', 'ready', 'deprecated'] as const

export default function TestCases() {
  const { projectId } = useParams<{ projectId: string }>()
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [loadingSteps, setLoadingSteps] = useState<Set<number>>(new Set())
  const [stepsCache, setStepsCache] = useState<Record<number, TestStep[]>>({})
  const [deletingTestCaseId, setDeletingTestCaseId] = useState<number | null>(null)
  
  // Edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingTestCase, setEditingTestCase] = useState<TestCase | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadTestCases()
    }
  }, [projectId])

  const loadTestCases = async () => {
    if (!projectId) return
    setIsLoading(true)
    try {
      const params: any = { page_size: 100 }
      if (priorityFilter !== 'all') params.priority = priorityFilter
      if (categoryFilter !== 'all') params.category = categoryFilter
      if (statusFilter !== 'all') params.status = statusFilter
      if (searchQuery) params.search = searchQuery
      
      const response = await testCasesApi.list(Number(projectId), params)
      setTestCases(response.data.items || [])
    } catch (error) {
      console.error('Failed to load test cases:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = () => {
    loadTestCases()
  }

  const handleDeleteTestCase = async (testCaseId: number, title: string) => {
    const confirmMessage = `Are you sure you want to delete "${title}"? This will also delete all test steps.`
    if (!window.confirm(confirmMessage)) {
      return
    }
    
    setDeletingTestCaseId(testCaseId)
    try {
      await testCasesApi.delete(testCaseId)
      toast.success('Test case deleted successfully')
      // Clear from cache if expanded
      setStepsCache(prev => {
        const newCache = { ...prev }
        delete newCache[testCaseId]
        return newCache
      })
      setExpandedRows(prev => {
        const newSet = new Set(prev)
        newSet.delete(testCaseId)
        return newSet
      })
      loadTestCases()
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to delete test case'
      toast.error(message)
    } finally {
      setDeletingTestCaseId(null)
    }
  }

  const handleEditTestCase = (tc: TestCase) => {
    setEditingTestCase({ ...tc })
    setIsEditModalOpen(true)
  }

  const handleSaveTestCase = async () => {
    if (!editingTestCase) return
    
    setIsSaving(true)
    try {
      await testCasesApi.update(editingTestCase.id, {
        title: editingTestCase.title,
        description: editingTestCase.description,
        preconditions: editingTestCase.preconditions,
        priority: editingTestCase.priority,
        category: editingTestCase.category,
        status: editingTestCase.status,
        tags: editingTestCase.tags,
      })
      toast.success('Test case updated successfully')
      setIsEditModalOpen(false)
      setEditingTestCase(null)
      loadTestCases()
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to update test case'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    if (projectId && !isLoading) {
      loadTestCases()
    }
  }, [priorityFilter, categoryFilter, statusFilter])

  const toggleRowExpansion = async (id: number) => {
    const newSet = new Set(expandedRows)
    
    if (newSet.has(id)) {
      newSet.delete(id)
      setExpandedRows(newSet)
    } else {
      newSet.add(id)
      setExpandedRows(newSet)
      
      // Load steps if not cached
      if (!stepsCache[id]) {
        setLoadingSteps(prev => new Set(prev).add(id))
        try {
          const response = await testCasesApi.getWithSteps(id)
          setStepsCache(prev => ({
            ...prev,
            [id]: response.data.steps || []
          }))
        } catch (error) {
          console.error('Failed to load steps:', error)
        } finally {
          setLoadingSteps(prev => {
            const newLoadingSet = new Set(prev)
            newLoadingSet.delete(id)
            return newLoadingSet
          })
        }
      }
    }
  }

  const actionIcons: Record<string, string> = {
    navigate: '🌐',
    click: '👆',
    fill: '✏️',
    type: '⌨️',
    select: '📋',
    check: '☑️',
    uncheck: '☐',
    hover: '👁️',
    wait: '⏳',
    screenshot: '📸',
    assert_visible: '👀',
    assert_text: '📝',
    assert_url: '🔗',
    assert_title: '📰',
    custom: '⚙️',
  }

  const priorityColors = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-gray-100 text-gray-700',
  }

  const categoryColors = {
    smoke: 'bg-purple-100 text-purple-700',
    regression: 'bg-blue-100 text-blue-700',
    e2e: 'bg-green-100 text-green-700',
    integration: 'bg-cyan-100 text-cyan-700',
    sanity: 'bg-gray-100 text-gray-700',
  }

  const itemTypeColors = {
    epic: 'bg-purple-100 text-purple-700',
    story: 'bg-blue-100 text-blue-700',
    bug: 'bg-red-100 text-red-700',
    task: 'bg-gray-100 text-gray-700',
  }

  const statusIcons = {
    ready: <CheckCircleIcon className="w-5 h-5 text-green-500" />,
    draft: <ClockIcon className="w-5 h-5 text-yellow-500" />,
    deprecated: <XCircleIcon className="w-5 h-5 text-red-500" />,
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Test Cases</h1>
          <p className="text-gray-600">
            Manage your functional test cases
            {testCases.length > 0 && (
              <span className="ml-2 text-primary-600 font-medium">({testCases.length} total)</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadTestCases} disabled={isLoading}>
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button>
            <PlusIcon className="w-4 h-4 mr-2" />
            New Test Case
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search test cases..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          
          <select 
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
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
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Categories</option>
            <option value="smoke">Smoke</option>
            <option value="regression">Regression</option>
            <option value="e2e">E2E</option>
            <option value="integration">Integration</option>
            <option value="sanity">Sanity</option>
          </select>
          
          <select 
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Status</option>
            <option value="ready">Ready</option>
            <option value="draft">Draft</option>
            <option value="deprecated">Deprecated</option>
          </select>
        </div>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <Card className="text-center py-12">
          <ArrowPathIcon className="w-8 h-8 mx-auto text-primary-500 animate-spin mb-4" />
          <p className="text-gray-500">Loading test cases...</p>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && testCases.length === 0 && (
        <Card className="text-center py-12">
          <SparklesIcon className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Test Cases Yet</h3>
          <p className="text-gray-500 mb-4">
            Generate test cases from User Stories or create them manually.
          </p>
          <Link to={`/projects/${projectId}/user-stories`}>
            <Button variant="outline">
              <LinkIcon className="w-4 h-4 mr-2" />
              Go to User Stories
            </Button>
          </Link>
        </Card>
      )}

      {/* Test Cases List */}
      {!isLoading && testCases.length > 0 && (
        <Card padding="none">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="w-8 px-4 py-3"></th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User Story</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Steps</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {testCases.map((tc) => (
                <React.Fragment key={tc.id}>
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-4">
                    <button 
                      onClick={() => toggleRowExpansion(tc.id)}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      {expandedRows.has(tc.id) ? (
                        <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronRightIcon className="w-4 h-4 text-gray-500" />
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-4">
                    {statusIcons[tc.status as keyof typeof statusIcons]}
                  </td>
                  <td className="px-4 py-4">
                    <Link 
                      to={`/projects/${projectId}/test-cases/${tc.id}`} 
                      className="font-medium text-primary-600 hover:underline"
                    >
                      {tc.title}
                    </Link>
                  </td>
                  <td className="px-4 py-4">
                    {tc.user_story ? (
                      <Link 
                        to={`/projects/${projectId}/user-stories`}
                        className="inline-flex items-center gap-1 text-sm"
                      >
                        <span className={`px-1.5 py-0.5 text-xs rounded ${itemTypeColors[tc.user_story.item_type as keyof typeof itemTypeColors] || 'bg-gray-100 text-gray-700'}`}>
                          {tc.user_story.item_type}
                        </span>
                        <span className="text-primary-600 hover:underline font-mono text-xs">
                          {tc.user_story.external_key || `US-${tc.user_story.id}`}
                        </span>
                      </Link>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    <span className={`px-2 py-1 text-xs rounded font-medium ${priorityColors[tc.priority as keyof typeof priorityColors]}`}>
                      {tc.priority}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`px-2 py-1 text-xs rounded ${categoryColors[tc.category as keyof typeof categoryColors] || 'bg-gray-100 text-gray-600'}`}>
                      {tc.category}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-sm text-gray-600">{tc.steps_count} steps</span>
                  </td>
                  <td className="px-4 py-4">
                    {tc.is_generated ? (
                      <span className="flex items-center gap-1 text-sm text-purple-600">
                        <SparklesIcon className="w-4 h-4" />
                        AI
                      </span>
                    ) : (
                      <span className="text-sm text-gray-500">Manual</span>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleEditTestCase(tc)}
                      >
                        <PencilIcon className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                      <Button 
                        variant="danger" 
                        size="sm"
                        onClick={() => handleDeleteTestCase(tc.id, tc.title)}
                        disabled={deletingTestCaseId === tc.id}
                        isLoading={deletingTestCaseId === tc.id}
                      >
                        {deletingTestCaseId !== tc.id && (
                          <TrashIcon className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </td>
                </tr>
                
                {/* Expanded Steps Row */}
                {expandedRows.has(tc.id) && (
                  <tr className="bg-gray-50">
                    <td colSpan={9} className="px-4 py-4">
                      {loadingSteps.has(tc.id) ? (
                        <div className="flex items-center justify-center py-4">
                          <ArrowPathIcon className="w-5 h-5 animate-spin text-primary-500 mr-2" />
                          <span className="text-sm text-gray-500">Loading steps...</span>
                        </div>
                      ) : stepsCache[tc.id]?.length > 0 ? (
                        <div className="ml-8 mr-4">
                          <h4 className="text-sm font-medium text-gray-700 mb-3">Test Steps</h4>
                          <div className="space-y-2">
                            {stepsCache[tc.id].map((step) => (
                              <div
                                key={step.id}
                                className="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-200"
                              >
                                <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
                                  {step.step_number}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="text-base">
                                      {actionIcons[step.action] || '⚙️'}
                                    </span>
                                    <span className="text-xs font-medium text-gray-500 uppercase">
                                      {step.action.replace('_', ' ')}
                                    </span>
                                    {step.target && (
                                      <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono text-gray-700 truncate max-w-xs">
                                        {step.target}
                                      </code>
                                    )}
                                  </div>
                                  {step.description && (
                                    <p className="text-sm text-gray-600">{step.description}</p>
                                  )}
                                  {step.expected_result && (
                                    <p className="text-xs text-gray-500 mt-1">
                                      <span className="font-medium">Expected:</span> {step.expected_result}
                                    </p>
                                  )}
                                  {step.playwright_code && (
                                    <div className="mt-2">
                                      <code className="text-xs bg-gray-900 text-green-400 px-2 py-1 rounded block overflow-x-auto">
                                        {step.playwright_code}
                                      </code>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-4 text-sm text-gray-500">
                          No steps generated yet
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Edit Test Case Modal */}
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
                      Edit Test Case
                    </Dialog.Title>
                    <button
                      onClick={() => setIsEditModalOpen(false)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Body */}
                  {editingTestCase && (
                    <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                      {/* Title */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Title *
                        </label>
                        <input
                          type="text"
                          value={editingTestCase.title}
                          onChange={(e) => setEditingTestCase({ ...editingTestCase, title: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Test case title"
                        />
                      </div>

                      {/* Description */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <textarea
                          value={editingTestCase.description || ''}
                          onChange={(e) => setEditingTestCase({ ...editingTestCase, description: e.target.value })}
                          rows={3}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Test case description"
                        />
                      </div>

                      {/* Preconditions */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Preconditions
                        </label>
                        <textarea
                          value={editingTestCase.preconditions || ''}
                          onChange={(e) => setEditingTestCase({ ...editingTestCase, preconditions: e.target.value })}
                          rows={2}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Preconditions required before running this test"
                        />
                      </div>

                      {/* Priority & Category row */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Priority
                          </label>
                          <select
                            value={editingTestCase.priority}
                            onChange={(e) => setEditingTestCase({ ...editingTestCase, priority: e.target.value as TestCasePriority })}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          >
                            {PRIORITY_OPTIONS.map((priority) => (
                              <option key={priority} value={priority}>
                                {priority.charAt(0).toUpperCase() + priority.slice(1)}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Category
                          </label>
                          <select
                            value={editingTestCase.category}
                            onChange={(e) => setEditingTestCase({ ...editingTestCase, category: e.target.value as TestCaseCategory })}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          >
                            {CATEGORY_OPTIONS.map((category) => (
                              <option key={category} value={category}>
                                {category.toUpperCase()}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {/* Status */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Status
                        </label>
                        <select
                          value={editingTestCase.status}
                          onChange={(e) => setEditingTestCase({ ...editingTestCase, status: e.target.value as TestCaseStatus })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        >
                          {STATUS_OPTIONS.map((status) => (
                            <option key={status} value={status}>
                              {status.charAt(0).toUpperCase() + status.slice(1)}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Tags */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Tags
                        </label>
                        <input
                          type="text"
                          value={editingTestCase.tags || ''}
                          onChange={(e) => setEditingTestCase({ 
                            ...editingTestCase, 
                            tags: e.target.value
                          })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Enter tags separated by commas"
                        />
                        <p className="mt-1 text-xs text-gray-500">Separate tags with commas</p>
                      </div>

                      {/* Source info (readonly) */}
                      {editingTestCase.is_generated && (
                        <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-50 px-3 py-2 rounded-lg">
                          <SparklesIcon className="w-4 h-4" />
                          <span>This test case was generated by AI</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <Button
                      variant="outline"
                      onClick={() => setIsEditModalOpen(false)}
                      disabled={isSaving}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSaveTestCase}
                      disabled={isSaving || !editingTestCase?.title}
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
    </div>
  )
}
