import { useEffect } from 'react'
import { Outlet, useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '@common/store/projectStore'
import { Loader } from '@common/components/ui/Loader'

/**
 * ProjectLayout - Wrapper for project-scoped routes
 * Loads the current project and provides it via store to child routes
 */
export default function ProjectLayout() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, fetchProject, isLoading, error } = useProjectStore()

  useEffect(() => {
    if (projectId) {
      fetchProject(projectId)
    }
  }, [projectId, fetchProject])

  // Handle loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" />
      </div>
    )
  }

  // Handle error or not found
  if (error || (!isLoading && !currentProject)) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <h2 className="text-xl font-semibold text-gray-900">Project Not Found</h2>
        <p className="text-gray-500 mt-2">The project you're looking for doesn't exist.</p>
        <button
          onClick={() => navigate('/projects')}
          className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Back to Projects
        </button>
      </div>
    )
  }

  // Render child routes
  return <Outlet />
}
