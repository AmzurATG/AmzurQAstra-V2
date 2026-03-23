import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useProjectStore } from '@common/store/projectStore'
import { Card, CardTitle } from '@common/components/ui/Card'
import { PageLoader } from '@common/components/ui/Loader'
import {
  FolderIcon,
  ClipboardDocumentListIcon,
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'

export default function Dashboard() {
  const { projects, isLoading, fetchProjects } = useProjectStore()

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  if (isLoading) return <PageLoader />

  // Mock stats - replace with real data
  const stats = [
    { name: 'Projects', value: projects.length, icon: FolderIcon, href: '/projects' },
    { name: 'Test Cases', value: 156, icon: ClipboardDocumentListIcon, href: '/functional/test-cases' },
    { name: 'Test Runs', value: 24, icon: PlayIcon, href: '/functional/test-runs' },
    { name: 'Pass Rate', value: '94%', icon: CheckCircleIcon, href: '/functional/test-runs' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your QA automation</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <Link key={stat.name} to={stat.href}>
            <Card className="hover:shadow-md transition-shadow">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <stat.icon className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardTitle>Recent Test Runs</CardTitle>
          <div className="mt-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div className="flex items-center gap-3">
                  <CheckCircleIcon className="w-5 h-5 text-green-500" />
                  <div>
                    <p className="font-medium">Test Run #{100 - i}</p>
                    <p className="text-sm text-gray-500">Login Flow Tests</p>
                  </div>
                </div>
                <span className="text-sm text-gray-500">2h ago</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>Recent Projects</CardTitle>
          <div className="mt-4 space-y-3">
            {projects.slice(0, 3).map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0 hover:bg-gray-50 -mx-2 px-2 rounded"
              >
                <FolderIcon className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="font-medium">{project.name}</p>
                  <p className="text-sm text-gray-500">{project.description || 'No description'}</p>
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
