import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Loader } from '@common/components/ui/Loader'
import { 
  DocumentTextIcon, 
  ArrowUpTrayIcon, 
  TrashIcon,
  SparklesIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline'
import { requirementsApi } from '../api'
import { UploadDocumentModal } from '../components'
import type { Requirement } from '../types'
import toast from 'react-hot-toast'

export default function Requirements() {
  const { projectId } = useParams<{ projectId: string }>()
  
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [generatingId, setGeneratingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const fetchRequirements = async () => {
    if (!projectId) return

    setIsLoading(true)
    setError(null)
    try {
      const response = await requirementsApi.list(projectId)
      setRequirements(response.data.items || [])
    } catch (err: any) {
      console.error('Failed to fetch requirements:', err)
      setError('Failed to load requirements')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchRequirements()
  }, [projectId])

  const handleGenerateTests = async (requirement: Requirement) => {
    setGeneratingId(requirement.id)
    try {
      const response = await requirementsApi.generateTestCases(requirement.id)
      toast.success(`Generated ${response.data.test_cases_created} test cases!`)
      fetchRequirements()
    } catch (err: any) {
      console.error('Failed to generate tests:', err)
      toast.error(err.response?.data?.detail || 'Failed to generate test cases')
    } finally {
      setGeneratingId(null)
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
    } catch (err: any) {
      console.error('Failed to delete requirement:', err)
      toast.error(err.response?.data?.detail || 'Failed to delete requirement')
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
            Upload a requirement document to get started with AI-powered test generation.
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
                  <td className="px-6 py-4 text-gray-600">
                    {req.test_cases_count} cases
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded ${
                      req.status === 'processed' 
                        ? 'bg-green-100 text-green-700'
                        : req.status === 'error'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {req.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-600 text-sm">
                    {formatDate(req.created_at)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleGenerateTests(req)}
                        isLoading={generatingId === req.id}
                        disabled={generatingId !== null || deletingId !== null}
                      >
                        <SparklesIcon className="w-4 h-4 mr-1" />
                        Generate
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(req)}
                        isLoading={deletingId === req.id}
                        disabled={generatingId !== null || deletingId !== null}
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

      {/* Upload Modal */}
      <UploadDocumentModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        projectId={projectId || ''}
        onUploadComplete={fetchRequirements}
      />
    </div>
  )
}
