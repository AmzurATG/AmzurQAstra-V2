import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { useProjectStore } from '@common/store/projectStore'
import { integrityCheckApi } from '../api'
import type { IntegrityCheckResult, IntegrityCheckPreview } from '../types'
import toast from 'react-hot-toast'
import {
  ShieldCheckIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlayIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
  ListBulletIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'

export default function IntegrityCheck() {
  const { projectId } = useParams<{ projectId: string }>()
  const { currentProject, fetchProject } = useProjectStore()
  const [appUrl, setAppUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<IntegrityCheckResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<IntegrityCheckPreview | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [expandedStories, setExpandedStories] = useState<Set<number>>(new Set())
  const [expandedTestCases, setExpandedTestCases] = useState<Set<number>>(new Set())

  // Fetch project details on mount
  useEffect(() => {
    if (projectId) {
      fetchProject(projectId)
    }
  }, [projectId, fetchProject])

  // Pre-fill form from project settings
  useEffect(() => {
    if (currentProject) {
      if (currentProject.app_url) {
        setAppUrl(currentProject.app_url)
      }
      if (currentProject.app_username) {
        setUsername(currentProject.app_username)
      }
    }
  }, [currentProject])

  // Load preview on mount
  useEffect(() => {
    if (projectId) {
      loadPreview()
    }
  }, [projectId])

  const loadPreview = async () => {
    if (!projectId) return
    setIsLoadingPreview(true)
    try {
      const response = await integrityCheckApi.getPreview(Number(projectId))
      setPreview(response.data)
    } catch (err) {
      console.error('Failed to load integrity check preview:', err)
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const toggleStory = (id: number) => {
    setExpandedStories((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleTestCase = (id: number) => {
    setExpandedTestCases((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleRunCheck = async () => {
    if (!appUrl) {
      toast.error('Please enter an application URL')
      return
    }
    if (!projectId) {
      toast.error('Project ID is required')
      return
    }

    setIsRunning(true)
    setError(null)
    setResult(null)

    try {
      const response = await integrityCheckApi.run({
        project_id: parseInt(projectId),
        app_url: appUrl,
        credentials: username || password ? { username, password } : undefined,
      })
      setResult(response.data)
      toast.success('Integrity check completed')
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to run integrity check'
      setError(message)
      toast.error(message)
    } finally {
      setIsRunning(false)
    }
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Build Integrity Check</h1>
        <p className="text-gray-600">Verify your application is ready for testing</p>
      </div>

      {/* Configuration */}
      <Card>
        <CardTitle>Configuration</CardTitle>
        <div className="mt-4 space-y-4">
          <Input
            label="Application URL"
            value={appUrl}
            onChange={(e) => setAppUrl(e.target.value)}
            placeholder="https://app.example.com"
          />
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Username (optional)"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="test@example.com"
            />
            <Input
              label="Password (optional)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <Button onClick={handleRunCheck} isLoading={isRunning} disabled={!appUrl}>
            <PlayIcon className="w-4 h-4 mr-2" />
            {isRunning ? 'Running Check...' : 'Run Integrity Check'}
          </Button>
        </div>
      </Card>

      {/* Execution Preview */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheckIcon className="w-5 h-5 text-green-600" />
            <CardTitle>Execution Preview</CardTitle>
          </div>
          {preview && (
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <BookOpenIcon className="w-4 h-4" />
                {preview.total_user_stories} user {preview.total_user_stories === 1 ? 'story' : 'stories'}
              </span>
              <span className="flex items-center gap-1">
                <ClipboardDocumentListIcon className="w-4 h-4" />
                {preview.total_test_cases} test {preview.total_test_cases === 1 ? 'case' : 'cases'}
              </span>
              <span className="flex items-center gap-1">
                <ListBulletIcon className="w-4 h-4" />
                {preview.total_steps} {preview.total_steps === 1 ? 'step' : 'steps'}
              </span>
            </div>
          )}
        </div>

        {isLoadingPreview && (
          <p className="text-sm text-gray-500 py-4">Loading preview...</p>
        )}

        {!isLoadingPreview && preview && preview.total_test_cases === 0 && (
          <div className="flex items-center gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600 flex-shrink-0" />
            <p className="text-sm text-yellow-800">
              No user stories or test cases are flagged for integrity check. Go to User Stories or Test Case Detail and enable the Integrity Check toggle.
            </p>
          </div>
        )}

        {!isLoadingPreview && preview && preview.total_test_cases > 0 && (
          <div className="space-y-2">
            {/* User Stories with their test cases */}
            {preview.user_stories.map((us) => (
              <div key={`us-${us.id}`} className="border border-gray-200 rounded-lg">
                <button
                  onClick={() => toggleStory(us.id)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 text-left"
                >
                  <div className="flex items-center gap-2">
                    {expandedStories.has(us.id) ? (
                      <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRightIcon className="w-4 h-4 text-gray-500" />
                    )}
                    <BookOpenIcon className="w-4 h-4 text-blue-500" />
                    {us.external_key && (
                      <span className="text-sm font-mono text-primary-600">{us.external_key}</span>
                    )}
                    <span className="font-medium text-gray-900 text-sm">{us.title}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {us.test_cases.length} test {us.test_cases.length === 1 ? 'case' : 'cases'}
                  </span>
                </button>

                {expandedStories.has(us.id) && (
                  <div className="border-t border-gray-100 px-4 pb-3">
                    {us.test_cases.map((tc) => (
                      <div key={`tc-${tc.id}`} className="ml-6 mt-2">
                        <button
                          onClick={() => toggleTestCase(tc.id)}
                          className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 text-left"
                        >
                          <div className="flex items-center gap-2">
                            {expandedTestCases.has(tc.id) ? (
                              <ChevronDownIcon className="w-3.5 h-3.5 text-gray-400" />
                            ) : (
                              <ChevronRightIcon className="w-3.5 h-3.5 text-gray-400" />
                            )}
                            <ClipboardDocumentListIcon className="w-4 h-4 text-indigo-500" />
                            <span className="text-sm text-gray-800">{tc.title}</span>
                          </div>
                          <span className="text-xs text-gray-400">
                            {tc.steps.length} {tc.steps.length === 1 ? 'step' : 'steps'}
                          </span>
                        </button>

                        {expandedTestCases.has(tc.id) && tc.steps.length > 0 && (
                          <div className="ml-8 mt-1 space-y-1">
                            {tc.steps.map((step) => (
                              <div
                                key={step.step_number}
                                className="flex items-center gap-2 text-xs text-gray-600 py-1 px-2 bg-gray-50 rounded"
                              >
                                <span className="text-gray-400 w-5 text-right">#{step.step_number}</span>
                                <span className="px-1.5 py-0.5 rounded bg-white border border-gray-200 font-mono">
                                  {step.action}
                                </span>
                                {step.target && (
                                  <span className="text-gray-500 truncate max-w-xs" title={step.target}>
                                    {step.target}
                                  </span>
                                )}
                                {step.description && (
                                  <span className="text-gray-400 truncate">{step.description}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {us.test_cases.length === 0 && (
                      <p className="ml-6 mt-2 text-xs text-gray-400 italic">No test cases linked</p>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Standalone test cases (flagged directly, not via user story) */}
            {preview.standalone_test_cases.length > 0 && (
              <div className="border border-gray-200 rounded-lg">
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                  <span className="text-sm font-medium text-gray-700">
                    Standalone Test Cases (flagged directly)
                  </span>
                </div>
                <div className="px-4 pb-3">
                  {preview.standalone_test_cases.map((tc) => (
                    <div key={`stc-${tc.id}`} className="mt-2">
                      <button
                        onClick={() => toggleTestCase(tc.id)}
                        className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 text-left"
                      >
                        <div className="flex items-center gap-2">
                          {expandedTestCases.has(tc.id) ? (
                            <ChevronDownIcon className="w-3.5 h-3.5 text-gray-400" />
                          ) : (
                            <ChevronRightIcon className="w-3.5 h-3.5 text-gray-400" />
                          )}
                          <ClipboardDocumentListIcon className="w-4 h-4 text-indigo-500" />
                          <span className="text-sm text-gray-800">{tc.title}</span>
                        </div>
                        <span className="text-xs text-gray-400">
                          {tc.steps.length} {tc.steps.length === 1 ? 'step' : 'steps'}
                        </span>
                      </button>

                      {expandedTestCases.has(tc.id) && tc.steps.length > 0 && (
                        <div className="ml-8 mt-1 space-y-1">
                          {tc.steps.map((step) => (
                            <div
                              key={step.step_number}
                              className="flex items-center gap-2 text-xs text-gray-600 py-1 px-2 bg-gray-50 rounded"
                            >
                              <span className="text-gray-400 w-5 text-right">#{step.step_number}</span>
                              <span className="px-1.5 py-0.5 rounded bg-white border border-gray-200 font-mono">
                                {step.action}
                              </span>
                              {step.target && (
                                <span className="text-gray-500 truncate max-w-xs" title={step.target}>
                                  {step.target}
                                </span>
                              )}
                              {step.description && (
                                <span className="text-gray-400 truncate">{step.description}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Error */}
      {error && (
        <Card>
          <div className="flex items-center gap-4 p-4 bg-red-50 rounded-lg">
            <XCircleIcon className="w-8 h-8 text-red-600" />
            <div>
              <h3 className="font-bold text-red-900">Check Failed</h3>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Results */}
      {result && (
        <Card>
          <div className="flex items-center gap-4 mb-6">
            <div className={`p-3 rounded-full ${result.status === 'passed' ? 'bg-green-100' : 'bg-red-100'}`}>
              {result.status === 'passed' ? (
                <ShieldCheckIcon className="w-8 h-8 text-green-600" />
              ) : (
                <XCircleIcon className="w-8 h-8 text-red-600" />
              )}
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">
                {result.status === 'passed' ? 'All Checks Passed' : 'Some Checks Failed'}
              </h3>
              <p className="text-gray-600">
                Completed in {formatDuration(result.duration_ms)} • {result.test_cases_total} test cases executed
              </p>
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">App Reachable</p>
              <div className="flex items-center gap-2 mt-1">
                {result.app_reachable ? (
                  <CheckCircleIcon className="w-5 h-5 text-green-500" />
                ) : (
                  <XCircleIcon className="w-5 h-5 text-red-500" />
                )}
                <span className="font-medium">{result.app_reachable ? 'Yes' : 'No'}</span>
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Test Cases Passed</p>
              <p className="font-medium text-lg">{result.test_cases_passed} / {result.test_cases_total}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Test Cases Failed</p>
              <p className={`font-medium text-lg ${result.test_cases_failed > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {result.test_cases_failed}
              </p>
            </div>
          </div>

          {/* Error message */}
          {result.error && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-yellow-800">{result.error}</p>
            </div>
          )}

          {/* Test Case Results */}
          {result.test_case_results && result.test_case_results.length > 0 && (
            <>
              <CardTitle>Test Case Results</CardTitle>
              <div className="mt-4 space-y-4">
                {result.test_case_results.map((tc) => (
                  <div
                    key={tc.test_case_id}
                    className={`p-4 rounded-lg border ${
                      tc.status === 'passed' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {tc.status === 'passed' ? (
                          <CheckCircleIcon className="w-5 h-5 text-green-500" />
                        ) : (
                          <XCircleIcon className="w-5 h-5 text-red-500" />
                        )}
                        <span className="font-medium">{tc.title}</span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {tc.steps_passed}/{tc.steps_total} steps • {formatDuration(tc.duration_ms)}
                      </span>
                    </div>
                    
                    {/* Step Results */}
                    <div className="ml-8 space-y-1">
                      {tc.step_results.map((step) => (
                        <div 
                          key={step.step_number}
                          className={`flex items-center justify-between text-sm p-2 rounded ${
                            step.status === 'passed' ? 'bg-green-100/50' : 'bg-red-100/50'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500">#{step.step_number}</span>
                            <span className="px-1.5 py-0.5 text-xs rounded bg-white">
                              {step.action}
                            </span>
                            <span className="text-gray-600">{step.description || ''}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {step.error && (
                              <span className="text-xs text-red-600">{step.error}</span>
                            )}
                            <span className="text-gray-400">{formatDuration(step.duration_ms)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Screenshots */}
          {result.screenshots && result.screenshots.length > 0 && (
            <div className="mt-6">
              <CardTitle>Screenshots</CardTitle>
              <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
                {result.screenshots.map((screenshot, index) => (
                  <a
                    key={index}
                    href={screenshot}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block border rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                  >
                    <img
                      src={screenshot}
                      alt={`Screenshot ${index + 1}`}
                      className="w-full h-32 object-cover"
                    />
                  </a>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
