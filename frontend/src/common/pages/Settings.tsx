import { Card, CardTitle } from '@common/components/ui/Card'

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600">Manage your account and preferences</p>
      </div>

      <Card>
        <CardTitle>Profile Settings</CardTitle>
        <p className="mt-4 text-gray-500">Settings page coming soon...</p>
      </Card>
    </div>
  )
}
