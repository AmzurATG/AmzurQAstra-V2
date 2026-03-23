import { Card, CardTitle } from '@common/components/ui/Card'

export default function Integrations() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-gray-600">Connect external tools and services</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardTitle>Jira</CardTitle>
          <p className="mt-2 text-gray-500">Sync test cases with Jira issues</p>
          <div className="mt-4">
            <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">Not Connected</span>
          </div>
        </Card>

        <Card>
          <CardTitle>Azure DevOps</CardTitle>
          <p className="mt-2 text-gray-500">Import work items and sync test cases</p>
          <div className="mt-4">
            <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">Not Connected</span>
          </div>
        </Card>

        <Card>
          <CardTitle>Slack</CardTitle>
          <p className="mt-2 text-gray-500">Get notifications for test run results</p>
          <div className="mt-4">
            <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">Not Connected</span>
          </div>
        </Card>
      </div>
    </div>
  )
}
