import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useProjectStore } from '@common/store/projectStore'
import { Card, CardTitle } from '@common/components/ui/Card'
import { PageLoader } from '@common/components/ui/Loader'
import {
  DocumentTextIcon,
  PlayIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const { currentProject, isLoading, selectProject, clearCurrentProject } = useProjectStore()

  useEffect(() => {
    if (projectId) {
      selectProject(parseInt(projectId))
    }
    return () => clearCurrentProject()
  }, [projectId, selectProject, clearCurrentProject])

  if (isLoading || !currentProject) return <PageLoader />

  const quickActions = [
    { name: 'Requirements', description: 'Upload and manage requirements', icon: DocumentTextIcon, href: `/projects/${projectId}/requirements` },
    { name: 'Functional Testing', description: 'Promote cases, execute runs, and review history', icon: PlayIcon, href: `/projects/${projectId}/functional-testing` },
    { name: 'Integrity Check', description: 'Verify app is ready for testing', icon: ShieldCheckIcon, href: `/projects/${projectId}/integrity-check` },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{currentProject.name}</h1>
        <p className="text-gray-600">{currentProject.description || 'No description'}</p>
      </div>

      {/* Project Info */}
      <Card>
        <CardTitle>Project Details</CardTitle>
        <dl className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-gray-500">Application URL</dt>
            <dd className="font-medium">{currentProject.app_url || 'Not configured'}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Jira Project</dt>
            <dd className="font-medium">{currentProject.jira_project_key || 'Not connected'}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Azure DevOps</dt>
            <dd className="font-medium">{currentProject.azure_devops_project || 'Not connected'}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Created</dt>
            <dd className="font-medium">{new Date(currentProject.created_at).toLocaleDateString()}</dd>
          </div>
        </dl>
      </Card>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action) => (
            <Link key={action.name} to={action.href}>
              <Card className="hover:shadow-md transition-shadow h-full">
                <div className="flex flex-col items-center text-center">
                  <div className="p-3 bg-primary-100 rounded-lg mb-3">
                    <action.icon className="w-6 h-6 text-primary-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">{action.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{action.description}</p>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
