import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'

export default function TestRunDetail() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()

  // Mock data - replace with actual API calls using projectId and runId
  const testRun = {
    id: runId,
    name: 'Regression Suite',
    status: 'failed',
    passed: 45,
    failed: 3,
    total: 48,
    duration: '15m 12s',
    browser: 'chromium',
    startedAt: '2024-01-15 09:15:00',
    completedAt: '2024-01-15 09:30:12',
  }

  const results = [
    { id: 1, title: 'Verify login with valid credentials', status: 'passed', duration: '2.3s' },
    { id: 2, title: 'Verify login fails with invalid password', status: 'passed', duration: '1.8s' },
    { id: 3, title: 'Add item to cart', status: 'failed', duration: '5.2s', error: 'Element not found: .add-to-cart-btn' },
    { id: 4, title: 'Complete checkout', status: 'passed', duration: '8.1s' },
    { id: 5, title: 'Verify order confirmation', status: 'passed', duration: '3.4s' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{testRun.name}</h1>
        <p className="text-gray-600">Run #{testRun.id} • {testRun.startedAt}</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="text-center">
          <p className="text-sm text-gray-500">Status</p>
          <p className={`text-xl font-bold ${testRun.status === 'passed' ? 'text-green-600' : 'text-red-600'}`}>
            {testRun.status.toUpperCase()}
          </p>
        </Card>
        <Card className="text-center">
          <p className="text-sm text-gray-500">Pass Rate</p>
          <p className="text-xl font-bold text-gray-900">
            {Math.round((testRun.passed / testRun.total) * 100)}%
          </p>
        </Card>
        <Card className="text-center">
          <p className="text-sm text-gray-500">Duration</p>
          <p className="text-xl font-bold text-gray-900">{testRun.duration}</p>
        </Card>
        <Card className="text-center">
          <p className="text-sm text-gray-500">Browser</p>
          <p className="text-xl font-bold text-gray-900">{testRun.browser}</p>
        </Card>
      </div>

      {/* Results */}
      <Card>
        <CardTitle>Test Results</CardTitle>
        <div className="mt-4 space-y-2">
          {results.map((result) => (
            <div
              key={result.id}
              className={`flex items-center justify-between p-4 rounded-lg ${
                result.status === 'passed' ? 'bg-green-50' : 'bg-red-50'
              }`}
            >
              <div className="flex items-center gap-3">
                {result.status === 'passed' ? (
                  <CheckCircleIcon className="w-5 h-5 text-green-500" />
                ) : (
                  <XCircleIcon className="w-5 h-5 text-red-500" />
                )}
                <div>
                  <p className="font-medium">{result.title}</p>
                  {result.error && (
                    <p className="text-sm text-red-600 mt-1">{result.error}</p>
                  )}
                </div>
              </div>
              <span className="text-sm text-gray-500">{result.duration}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
