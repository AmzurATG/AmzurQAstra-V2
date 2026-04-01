import { useState, useEffect, Fragment } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Dialog, Transition, Switch } from '@headlessui/react'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { 
  SparklesIcon, 
  PlayIcon, 
  PlusIcon, 
  ArrowLeftIcon,
  ArrowPathIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { testCasesApi, testStepsApi } from '../api'
import type { TestCase, TestStep, TestStepAction } from '../types'
import toast from 'react-hot-toast'

const ACTION_OPTIONS: TestStepAction[] = [
  'navigate', 'click', 'fill', 'type', 'select', 'check', 'uncheck',
  'hover', 'wait', 'screenshot', 'assert_visible', 'assert_text', 
  'assert_url', 'assert_title', 'custom'
]

export default function TestCaseDetail() {
  const { projectId, testCaseId } = useParams<{ projectId: string; testCaseId: string }>()
  const [testCase, setTestCase] = useState<TestCase | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Edit modal state
  const [editingStep, setEditingStep] = useState<TestStep | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  
  // Delete state
  const [deletingStepId, setDeletingStepId] = useState<number | null>(null)

  // Regenerate steps state
  const [isRegenerating, setIsRegenerating] = useState(false)

  useEffect(() => {
    if (testCaseId) {
      loadTestCase()
    }
  }, [testCaseId])

  const loadTestCase = async () => {
    if (!testCaseId) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await testCasesApi.getWithSteps(Number(testCaseId))
      setTestCase(response.data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to load test case'
      setError(message)
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleEditStep = (step: TestStep) => {
    setEditingStep({ ...step })
    setIsEditModalOpen(true)
  }

  const handleSaveStep = async () => {
    if (!editingStep) return
    
    setIsSaving(true)
    try {
      await testStepsApi.update(editingStep.id, {
        action: editingStep.action,
        target: editingStep.target,
        value: editingStep.value,
        description: editingStep.description,
        expected_result: editingStep.expected_result,
      })
      toast.success('Step updated successfully')
      setIsEditModalOpen(false)
      setEditingStep(null)
      loadTestCase()
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to update step'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteStep = async (stepId: number, stepNumber: number) => {
    if (!window.confirm(`Are you sure you want to delete Step ${stepNumber}?`)) {
      return
    }
    
    setDeletingStepId(stepId)
    try {
      await testStepsApi.delete(stepId)
      toast.success('Step deleted successfully')
      loadTestCase()
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to delete step'
      toast.error(message)
    } finally {
      setDeletingStepId(null)
    }
  }

  const handleRegenerateSteps = async () => {
    if (!testCaseId) return
    if (!window.confirm('This will delete existing steps and generate new ones. Continue?')) {
      return
    }
    
    setIsRegenerating(true)
    try {
      const response = await testCasesApi.regenerateSteps(Number(testCaseId))
      if (response.data.success) {
        toast.success(`${response.data.steps_created} steps regenerated successfully`)
        loadTestCase()
      } else {
        toast.error(response.data.error || 'Failed to regenerate steps')
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to regenerate steps'
      toast.error(message)
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleToggleIntegrityCheck = async () => {
    if (!testCase || !testCaseId) return
    
    const newValue = !testCase.integrity_check
    try {
      await testCasesApi.update(Number(testCaseId), { integrity_check: newValue })
      setTestCase({ ...testCase, integrity_check: newValue })
      toast.success(newValue ? 'Added to integrity check' : 'Removed from integrity check')
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to update'
      toast.error(message)
    }
  }

  const actionColors: Record<string, string> = {
    navigate: 'bg-blue-100 text-blue-700',
    click: 'bg-green-100 text-green-700',
    fill: 'bg-purple-100 text-purple-700',
    type: 'bg-purple-100 text-purple-700',
    select: 'bg-indigo-100 text-indigo-700',
    check: 'bg-teal-100 text-teal-700',
    uncheck: 'bg-teal-100 text-teal-700',
    hover: 'bg-cyan-100 text-cyan-700',
    wait: 'bg-yellow-100 text-yellow-700',
    screenshot: 'bg-pink-100 text-pink-700',
    assert_visible: 'bg-orange-100 text-orange-700',
    assert_text: 'bg-orange-100 text-orange-700',
    assert_url: 'bg-orange-100 text-orange-700',
    assert_title: 'bg-orange-100 text-orange-700',
    custom: 'bg-gray-100 text-gray-700',
  }

  const priorityColors: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-gray-100 text-gray-600',
  }

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-600',
    ready: 'bg-green-100 text-green-700',
    deprecated: 'bg-red-100 text-red-600',
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <ArrowPathIcon className="w-8 h-8 animate-spin text-primary-500" />
        <span className="ml-2 text-gray-600">Loading test case...</span>
      </div>
    )
  }

  if (error || !testCase) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error || 'Test case not found'}</p>
        <Link to={`/projects/${projectId}/test-cases`}>
          <Button variant="outline">
            <ArrowLeftIcon className="w-4 h-4 mr-2" />
            Back to Test Cases
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Link 
        to={`/projects/${projectId}/test-cases`}
        className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeftIcon className="w-4 h-4 mr-1" />
        Back to Test Cases
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{testCase.title}</h1>
            {testCase.is_generated && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
                <SparklesIcon className="w-3 h-3" />
                AI Generated
              </span>
            )}
          </div>
          <p className="text-gray-600">{testCase.description || 'No description'}</p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={handleRegenerateSteps}
            disabled={isRegenerating}
          >
            {isRegenerating ? (
              <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <SparklesIcon className="w-4 h-4 mr-2" />
            )}
            {isRegenerating ? 'Regenerating...' : 'Regenerate Steps'}
          </Button>
          <Button>
            <PlayIcon className="w-4 h-4 mr-2" />
            Run Test
          </Button>
        </div>
      </div>

      {/* Test Case Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardTitle>Details</CardTitle>
          <dl className="mt-4 space-y-3">
            <div>
              <dt className="text-sm text-gray-500">Priority</dt>
              <dd>
                <span className={`px-2 py-0.5 text-xs rounded font-medium ${priorityColors[testCase.priority] || 'bg-gray-100'}`}>
                  {testCase.priority}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Category</dt>
              <dd className="font-medium capitalize">{testCase.category}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Status</dt>
              <dd>
                <span className={`px-2 py-0.5 text-xs rounded font-medium ${statusColors[testCase.status] || 'bg-gray-100'}`}>
                  {testCase.status}
                </span>
              </dd>
            </div>
            {testCase.user_story && (
              <div>
                <dt className="text-sm text-gray-500">User Story</dt>
                <dd>
                  <Link 
                    to={`/projects/${projectId}/user-stories`}
                    className="text-primary-600 hover:underline font-mono text-sm"
                  >
                    {testCase.user_story.external_key || `US-${testCase.user_story.id}`}
                  </Link>
                </dd>
              </div>
            )}
            {testCase.jira_key && (
              <div>
                <dt className="text-sm text-gray-500">Jira Key</dt>
                <dd className="font-mono text-sm">{testCase.jira_key}</dd>
              </div>
            )}
            <div className="pt-3 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheckIcon className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-700">Integrity Check</span>
                </div>
                <Switch
                  checked={testCase.integrity_check}
                  onChange={handleToggleIntegrityCheck}
                  className={`${testCase.integrity_check ? 'bg-green-600' : 'bg-gray-200'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2`}
                >
                  <span className={`${testCase.integrity_check ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                </Switch>
              </div>
              <p className="mt-1 text-xs text-gray-500">Include in build integrity check</p>
            </div>
          </dl>
        </Card>

        <Card className="md:col-span-2">
          <CardTitle>Preconditions</CardTitle>
          <p className="mt-4 text-gray-600">
            {testCase.preconditions || 'No preconditions specified'}
          </p>
        </Card>
      </div>

      {/* Test Steps */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <CardTitle>Test Steps ({testCase.steps?.length || 0})</CardTitle>
          <Button variant="outline" size="sm">
            <PlusIcon className="w-4 h-4 mr-2" />
            Add Step
          </Button>
        </div>

        {testCase.steps && testCase.steps.length > 0 ? (
          <div className="space-y-3">
            {testCase.steps.map((step, index) => (
              <div key={step.id} className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center font-bold shrink-0">
                  {step.step_number || index + 1}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs rounded font-medium ${actionColors[step.action] || 'bg-gray-100 text-gray-700'}`}>
                      {step.action}
                    </span>
                    <span className="text-gray-700">{step.description || 'No description'}</span>
                  </div>
                  <div className="text-sm text-gray-600 space-x-2">
                    {step.target && (
                      <span className="bg-gray-200 px-1.5 py-0.5 rounded text-xs">{step.target}</span>
                    )}
                    {step.value && (
                      <span>→ <span className="font-mono bg-blue-50 px-1.5 py-0.5 rounded text-xs">"{step.value}"</span></span>
                    )}
                  </div>
                  {step.expected_result && (
                    <div className="mt-2 text-sm text-green-600">
                      Expected: {step.expected_result}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => handleEditStep(step)}
                  >
                    <PencilIcon className="w-4 h-4 mr-1" />
                    Edit
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-red-600 hover:text-red-700"
                    onClick={() => handleDeleteStep(step.id, step.step_number || index + 1)}
                    disabled={deletingStepId === step.id}
                  >
                    {deletingStepId === step.id ? (
                      <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    ) : (
                      <TrashIcon className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>No test steps defined yet.</p>
            <Button variant="outline" className="mt-4">
              <PlusIcon className="w-4 h-4 mr-2" />
              Add First Step
            </Button>
          </div>
        )}
      </Card>

      {/* Edit Step Modal */}
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
                      Edit Step {editingStep?.step_number}
                    </Dialog.Title>
                    <button
                      onClick={() => setIsEditModalOpen(false)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Body */}
                  {editingStep && (
                    <div className="px-6 py-4 space-y-4">
                      {/* Action */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Action
                        </label>
                        <select
                          value={editingStep.action}
                          onChange={(e) => setEditingStep({ ...editingStep, action: e.target.value as TestStepAction })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                        >
                          {ACTION_OPTIONS.map((action) => (
                            <option key={action} value={action}>{action}</option>
                          ))}
                        </select>
                      </div>

                      {/* Description */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <input
                          type="text"
                          value={editingStep.description || ''}
                          onChange={(e) => setEditingStep({ ...editingStep, description: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Step description"
                        />
                      </div>

                      {/* Target */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Target (Element / URL)
                        </label>
                        <input
                          type="text"
                          value={editingStep.target || ''}
                          onChange={(e) => setEditingStep({ ...editingStep, target: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="e.g. the Login button, the Email input field"
                        />
                      </div>

                      {/* Value */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Value (Input)
                        </label>
                        <input
                          type="text"
                          value={editingStep.value || ''}
                          onChange={(e) => setEditingStep({ ...editingStep, value: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Value to fill or type"
                        />
                      </div>

                      {/* Expected Result */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Expected Result
                        </label>
                        <input
                          type="text"
                          value={editingStep.expected_result || ''}
                          onChange={(e) => setEditingStep({ ...editingStep, expected_result: e.target.value })}
                          className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Expected outcome"
                        />
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
                      onClick={handleSaveStep}
                      disabled={isSaving}
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
