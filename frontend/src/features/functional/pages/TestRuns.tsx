import { useParams, Link } from 'react-router-dom'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import {
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'

export default function TestRuns() {
  const { projectId } = useParams<{ projectId: string }>()
  
  // Mock data - replace with actual API calls using projectId
  const testRuns = [
    { id: 1, name: 'Smoke Test Run', status: 'passed', passed: 10, failed: 0, total: 10, duration: '2m 34s', createdAt: '2024-01-15 10:30' },
    { id: 2, name: 'Regression Suite', status: 'failed', passed: 45, failed: 3, total: 48, duration: '15m 12s', createdAt: '2024-01-15 09:15' },
    { id: 3, name: 'Login Flow Tests', status: 'running', passed: 3, failed: 0, total: 8, duration: '-', createdAt: '2024-01-15 10:45' },
    { id: 4, name: 'Checkout Tests', status: 'passed', passed: 12, failed: 0, total: 12, duration: '5m 45s', createdAt: '2024-01-14 16:00' },
  ]

  const statusConfig = {
    passed: { icon: CheckCircleIcon, color: 'text-green-500', bg: 'bg-green-100' },
    failed: { icon: XCircleIcon, color: 'text-red-500', bg: 'bg-red-100' },
    running: { icon: ClockIcon, color: 'text-blue-500', bg: 'bg-blue-100' },
    pending: { icon: ClockIcon, color: 'text-gray-500', bg: 'bg-gray-100' },
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Test Runs</h1>
          <p className="text-gray-600">Execute and monitor test runs</p>
        </div>
        <Button>
          <PlayIcon className="w-4 h-4 mr-2" />
          New Test Run
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="text-center">
          <p className="text-sm text-gray-500">Total Runs</p>
          <p className="text-2xl font-bold text-gray-900">24</p>
        </Card>
        <Card className="text-center">
          <p className="text-sm text-gray-500">Passed</p>
          <p className="text-2xl font-bold text-green-600">20</p>
        </Card>
        <Card className="text-center">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600">3</p>
        </Card>
        <Card className="text-center">
          <p className="text-sm text-gray-500">Pass Rate</p>
          <p className="text-2xl font-bold text-primary-600">87%</p>
        </Card>
      </div>

      {/* Test Runs List */}
      <Card padding="none">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Results</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {testRuns.map((run) => {
              const config = statusConfig[run.status as keyof typeof statusConfig]
              const StatusIcon = config.icon
              return (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className={`inline-flex items-center gap-2 px-2 py-1 rounded ${config.bg}`}>
                      <StatusIcon className={`w-4 h-4 ${config.color}`} />
                      <span className={`text-sm font-medium ${config.color}`}>{run.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <Link to={`/projects/${projectId}/test-runs/${run.id}`} className="font-medium text-primary-600 hover:underline">
                      {run.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-green-600">{run.passed} passed</span>
                      <span className="text-gray-400">|</span>
                      <span className="text-red-600">{run.failed} failed</span>
                      <span className="text-gray-400">|</span>
                      <span className="text-gray-600">{run.total} total</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-600">{run.duration}</td>
                  <td className="px-6 py-4 text-gray-600">{run.createdAt}</td>
                  <td className="px-6 py-4">
                    <Link to={`/projects/${projectId}/test-runs/${run.id}`}>
                      <Button variant="ghost" size="sm">View Details</Button>
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
