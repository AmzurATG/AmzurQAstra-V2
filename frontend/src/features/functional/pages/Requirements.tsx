import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Loader } from '@common/components/ui/Loader'
import {
  DocumentTextIcon,
  ArrowUpTrayIcon,
  TrashIcon,
  DocumentMagnifyingGlassIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline'
import { requirementsApi, gapAnalysisApi, userStoriesApi, testRecommendationsApi } from '../api'
import {
  UploadDocumentModal,
  RequirementPreviewModal,
  GapAnalysisRunModal,
  TestRecommendationRunModal,
} from '../components'
import type { Requirement, GapAnalysisRun, TestRecommendationRun } from '../types'
import toast from 'react-hot-toast'

function formatApiError(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown } } }
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(' ')
  }
  return 'Request failed'
}

export default function Requirements() {
  const { projectId } = useParams<{ projectId: string }>()

  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [gapAnalyzingId, setGapAnalyzingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [previewRequirement, setPreviewRequirement] = useState<Requirement | null>(null)
  const [userStoryTotal, setUserStoryTotal] = useState<number | null>(null)
  const [gapRuns, setGapRuns] = useState<GapAnalysisRun[]>([])
  const [gapRunsLoading, setGapRunsLoading] = useState(false)
  const [testRecRuns, setTestRecRuns] = useState<TestRecommendationRun[]>([])
  const [testRecRunsLoading, setTestRecRunsLoading] = useState(false)
  const [testRecRunningId, setTestRecRunningId] = useState<string | null>(null)
  const [gapModal, setGapModal] = useState<{
    runId: number
    tab: 'summary' | 'pdf'
  } | null>(null)
  const [testRecModal, setTestRecModal] = useState<{
    runId: number
    tab: 'summary' | 'pdf'
  } | null>(null)
  const [deletingGapRunId, setDeletingGapRunId] = useState<number | null>(null)
  const [deletingTestRecRunId, setDeletingTestRecRunId] = useState<number | null>(null)

  const fetchRequirements = async () => {
    if (!projectId) return

    setIsLoading(true)
    setError(null)
    try {
      const response = await requirementsApi.list(projectId)
      setRequirements(response.data.items || [])
    } catch (err: unknown) {
      console.error('Failed to fetch requirements:', err)
      setError(formatApiError(err) || 'Failed to load requirements')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchGapRuns = useCallback(async () => {
    if (!projectId) return
    setGapRunsLoading(true)
    try {
      const res = await gapAnalysisApi.listRuns(projectId, { page: 1, page_size: 50 })
      setGapRuns(res.data.items || [])
    } catch (err) {
      console.error('Failed to fetch gap analysis runs:', err)
    } finally {
      setGapRunsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchRequirements()
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    ;(async () => {
      try {
        const stats = await userStoriesApi.getStats(Number(projectId))
        if (!cancelled) setUserStoryTotal(stats.data.total)
      } catch {
        if (!cancelled) setUserStoryTotal(0)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [projectId])

  const fetchTestRecRuns = useCallback(async () => {
    if (!projectId) return
    setTestRecRunsLoading(true)
    try {
      const res = await testRecommendationsApi.listRuns(projectId, { page: 1, page_size: 50 })
      setTestRecRuns(res.data.items || [])
    } catch (err) {
      console.error('Failed to fetch test recommendation runs:', err)
    } finally {
      setTestRecRunsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchGapRuns()
  }, [fetchGapRuns])

  useEffect(() => {
    fetchTestRecRuns()
  }, [fetchTestRecRuns])

  const handleGapAnalysis = async (requirement: Requirement) => {
    if (!projectId) return
    setGapAnalyzingId(requirement.id)
    try {
      const res = await gapAnalysisApi.createRun(Number(projectId), Number(requirement.id))
      if (res.data.status === 'failed') {
        toast.error(res.data.error_message || 'Gap analysis failed')
      } else {
        toast.success('Gap analysis completed')
      }
      await fetchGapRuns()
      setGapModal({ runId: res.data.id, tab: 'summary' })
    } catch (err: unknown) {
      console.error('Gap analysis failed:', err)
      toast.error(formatApiError(err) || 'Gap analysis failed')
    } finally {
      setGapAnalyzingId(null)
    }
  }

  const handleTestRecommendations = async (requirement: Requirement) => {
    if (!projectId) return
    setTestRecRunningId(requirement.id)
    try {
      const res = await testRecommendationsApi.createRun(Number(projectId), Number(requirement.id))
      if (res.data.status === 'failed') {
        toast.error(res.data.error_message || 'Test recommendations failed')
      } else {
        toast.success('Test recommendations completed')
      }
      await fetchTestRecRuns()
      setTestRecModal({ runId: res.data.id, tab: 'summary' })
    } catch (err: unknown) {
      console.error('Test recommendations failed:', err)
      toast.error(formatApiError(err) || 'Test recommendations failed')
    } finally {
      setTestRecRunningId(null)
    }
  }

  const handleDownloadGapPdf = async (run: GapAnalysisRun) => {
    if (!projectId) return
    try {
      const response = await gapAnalysisApi.getPdf(run.id, projectId, true)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `gap-analysis-${run.id}.pdf`
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      toast.success('Download started')
    } catch (e) {
      console.error(e)
      toast.error(formatApiError(e) || 'Download failed')
    }
  }

  const handleDownloadTestRecPdf = async (run: TestRecommendationRun) => {
    if (!projectId) return
    try {
      const response = await testRecommendationsApi.getPdf(run.id, projectId, true)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `test-recommendations-${run.id}.pdf`
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      toast.success('Download started')
    } catch (e) {
      console.error(e)
      toast.error(formatApiError(e) || 'Download failed')
    }
  }

  const handleDeleteGapRun = async (run: GapAnalysisRun) => {
    if (!projectId) return
    if (
      !confirm(
        `Delete gap analysis run #${run.id}? The stored PDF will be removed. This cannot be undone.`
      )
    ) {
      return
    }
    setDeletingGapRunId(run.id)
    try {
      await gapAnalysisApi.deleteRun(run.id, projectId)
      toast.success('Run deleted')
      if (gapModal?.runId === run.id) setGapModal(null)
      await fetchGapRuns()
    } catch (err) {
      console.error(err)
      toast.error(formatApiError(err) || 'Delete failed')
    } finally {
      setDeletingGapRunId(null)
    }
  }

  const handleDeleteTestRecRun = async (run: TestRecommendationRun) => {
    if (!projectId) return
    if (
      !confirm(
        `Delete test recommendation run #${run.id}? The stored PDF will be removed. This cannot be undone.`
      )
    ) {
      return
    }
    setDeletingTestRecRunId(run.id)
    try {
      await testRecommendationsApi.deleteRun(run.id, projectId)
      toast.success('Run deleted')
      if (testRecModal?.runId === run.id) setTestRecModal(null)
      await fetchTestRecRuns()
    } catch (err) {
      console.error(err)
      toast.error(formatApiError(err) || 'Delete failed')
    } finally {
      setDeletingTestRecRunId(null)
    }
  }

  const handleDelete = async (requirement: Requirement) => {
    if (!confirm(`Are you sure you want to delete "${requirement.title}"?`)) {
      return
    }

    setDeletingId(requirement.id)
    try {
      await requirementsApi.delete(requirement.id)
      toast.success('Requirement deleted')
      fetchRequirements()
    } catch (err: unknown) {
      console.error('Failed to delete requirement:', err)
      toast.error(formatApiError(err) || 'Failed to delete requirement')
    } finally {
      setDeletingId(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  }

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'jira':
        return 'bg-blue-100 text-blue-700'
      case 'azure_devops':
        return 'bg-purple-100 text-purple-700'
      case 'upload':
        return 'bg-green-100 text-green-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const rowActionBusy = gapAnalyzingId !== null || deletingId !== null || testRecRunningId !== null

  const requirementHasParsedContent = (req: Requirement) =>
    !!(req.content && req.content.trim().length > 0)

  const gapAnalysisDisabledFor = (req: Requirement) => {
    if (!requirementHasParsedContent(req)) return true
    if (userStoryTotal === null) return true
    if (userStoryTotal === 0) return true
    return false
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Requirements</h1>
          <p className="text-gray-600">Manage requirement documents for test generation</p>
        </div>
        <Button onClick={() => setIsUploadModalOpen(true)}>
          <ArrowUpTrayIcon className="w-4 h-4 mr-2" />
          Upload Document
        </Button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Loader size="lg" />
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <Card className="text-center py-8">
          <ExclamationTriangleIcon className="w-12 h-12 mx-auto text-red-400 mb-3" />
          <p className="text-red-600 mb-4">{error}</p>
          <Button variant="outline" onClick={fetchRequirements}>
            Try Again
          </Button>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !error && requirements.length === 0 && (
        <Card className="text-center py-12">
          <DocumentTextIcon className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <h3 className="text-lg font-medium text-gray-900 mb-1">No requirements yet</h3>
          <p className="text-gray-500 mb-4">
            Upload a requirement document to get started with gap analysis and test generation.
          </p>
          <Button onClick={() => setIsUploadModalOpen(true)}>
            <ArrowUpTrayIcon className="w-4 h-4 mr-2" />
            Upload Your First Document
          </Button>
        </Card>
      )}

      {/* Requirements List */}
      {!isLoading && !error && requirements.length > 0 && (
        <Card padding="none">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Test Cases</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {requirements.map((req) => (
                <tr key={req.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <DocumentTextIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                      <div>
                        <span className="font-medium text-gray-900">{req.title}</span>
                        {req.file_path && (
                          <p className="text-xs text-gray-500 truncate max-w-xs">
                            {req.file_path.split('/').pop()}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded ${getSourceBadgeColor(req.source)}`}>
                      {req.source}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-600">{req.test_cases_count} cases</td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        req.status === 'processed'
                          ? 'bg-green-100 text-green-700'
                          : req.status === 'error'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {req.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-600 text-sm">{formatDate(req.created_at)}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setPreviewRequirement(req)}
                        disabled={rowActionBusy}
                        title="Preview document"
                      >
                        <EyeIcon className="w-4 h-4 mr-1" />
                        Preview
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleGapAnalysis(req)}
                        isLoading={gapAnalyzingId === req.id}
                        disabled={rowActionBusy || gapAnalysisDisabledFor(req)}
                        title={
                          !requirementHasParsedContent(req)
                            ? 'Upload and process a document first'
                            : userStoryTotal === 0
                              ? 'Import or create user stories before running gap analysis'
                              : 'Run gap analysis (BRD vs user stories)'
                        }
                      >
                        <DocumentMagnifyingGlassIcon className="w-4 h-4 mr-1" />
                        Gap analysis
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleTestRecommendations(req)}
                        isLoading={testRecRunningId === req.id}
                        disabled={rowActionBusy || gapAnalysisDisabledFor(req)}
                        title={
                          !requirementHasParsedContent(req)
                            ? 'Upload and process a document first'
                            : userStoryTotal === 0
                              ? 'Import or create user stories first'
                              : 'Run test recommendations (domain playbook)'
                        }
                      >
                        <LightBulbIcon className="w-4 h-4 mr-1" />
                        Recommendations
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(req)}
                        isLoading={deletingId === req.id}
                        disabled={rowActionBusy}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Gap analysis history */}
      {!isLoading && !error && projectId && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Gap analysis reports</h2>
              <p className="text-sm text-gray-500">
                Compare requirement documents with user stories. Preview the PDF or accept suggested
                stories into User Stories.
              </p>
            </div>
          </div>
          {gapRunsLoading ? (
            <div className="flex justify-center py-8">
              <Loader />
            </div>
          ) : gapRuns.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">
              No gap analysis runs yet. Use <strong>Gap analysis</strong> on a requirement row above.
            </p>
          ) : (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full min-w-[640px]">
                <thead className="bg-gray-50 border-y border-gray-200">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-12">
                      S.No.
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      BRD / document
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Run date
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {gapRuns.map((run, idx) => (
                    <tr key={run.id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-3 text-sm text-gray-600">{idx + 1}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className="font-medium text-gray-900">
                          {run.requirement_title || run.requirement_file_name || `Requirement #${run.requirement_id}`}
                        </span>
                        {run.requirement_file_name && run.requirement_title && (
                          <p className="text-xs text-gray-500 truncate max-w-xs mt-0.5">
                            {run.requirement_file_name}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                        {formatDateTime(run.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 text-xs rounded ${
                            run.status === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : run.status === 'failed'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1 flex-wrap">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setGapModal({ runId: run.id, tab: 'summary' })}
                          >
                            Details
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={!run.pdf_path}
                            onClick={() => setGapModal({ runId: run.id, tab: 'pdf' })}
                            title={run.pdf_path ? 'Preview PDF' : 'PDF not available'}
                          >
                            Preview PDF
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={!run.pdf_path}
                            onClick={() => handleDownloadGapPdf(run)}
                          >
                            <ArrowDownTrayIcon className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={deletingGapRunId === run.id}
                            onClick={() => handleDeleteGapRun(run)}
                            title="Delete run"
                            className="text-red-600 hover:text-red-700"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Test recommendation runs */}
      {!isLoading && !error && projectId && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Test recommendation runs</h2>
              <p className="text-sm text-gray-500">
                Domain-based standard and recommended test focus areas from the BRD and user stories.
              </p>
            </div>
          </div>
          {testRecRunsLoading ? (
            <div className="flex justify-center py-8">
              <Loader />
            </div>
          ) : testRecRuns.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">
              No runs yet. Use <strong>Recommendations</strong> on a requirement row above.
            </p>
          ) : (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full min-w-[640px]">
                <thead className="bg-gray-50 border-y border-gray-200">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-12">
                      S.No.
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      BRD / document
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Run date
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {testRecRuns.map((run, idx) => (
                    <tr key={run.id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-3 text-sm text-gray-600">{idx + 1}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className="font-medium text-gray-900">
                          {run.requirement_title ||
                            run.requirement_file_name ||
                            `Requirement #${run.requirement_id}`}
                        </span>
                        {run.requirement_file_name && run.requirement_title && (
                          <p className="text-xs text-gray-500 truncate max-w-xs mt-0.5">
                            {run.requirement_file_name}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                        {formatDateTime(run.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 text-xs rounded ${
                            run.status === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : run.status === 'failed'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1 flex-wrap">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setTestRecModal({ runId: run.id, tab: 'summary' })}
                          >
                            Details
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={!run.pdf_path}
                            onClick={() => setTestRecModal({ runId: run.id, tab: 'pdf' })}
                            title={run.pdf_path ? 'Preview PDF' : 'PDF not available'}
                          >
                            Preview PDF
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={!run.pdf_path}
                            onClick={() => handleDownloadTestRecPdf(run)}
                          >
                            <ArrowDownTrayIcon className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={deletingTestRecRunId === run.id}
                            onClick={() => handleDeleteTestRecRun(run)}
                            title="Delete run"
                            className="text-red-600 hover:text-red-700"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Upload Modal */}
      <UploadDocumentModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        projectId={projectId || ''}
        onUploadComplete={() => {
          fetchRequirements()
          fetchGapRuns()
          fetchTestRecRuns()
        }}
      />

      <RequirementPreviewModal
        isOpen={previewRequirement !== null}
        onClose={() => setPreviewRequirement(null)}
        requirement={previewRequirement}
      />

      <GapAnalysisRunModal
        isOpen={gapModal !== null}
        onClose={() => setGapModal(null)}
        projectId={projectId || ''}
        runId={gapModal?.runId ?? null}
        initialTab={gapModal?.tab ?? 'summary'}
        onAccepted={async () => {
          await fetchGapRuns()
          if (!projectId) return
          try {
            const stats = await userStoriesApi.getStats(Number(projectId))
            setUserStoryTotal(stats.data.total)
          } catch {
            /* ignore */
          }
        }}
      />

      <TestRecommendationRunModal
        isOpen={testRecModal !== null}
        onClose={() => setTestRecModal(null)}
        projectId={projectId || ''}
        runId={testRecModal?.runId ?? null}
        initialTab={testRecModal?.tab ?? 'summary'}
      />
    </div>
  )
}
