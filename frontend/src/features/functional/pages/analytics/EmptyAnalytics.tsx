import { Link } from 'react-router-dom'

import { Card, CardTitle } from '@common/components/ui/Card'

type Props = {
  projectId: string
}

export function EmptyAnalytics({ projectId }: Props) {
  const cases = `/projects/${projectId}/functional-testing/cases`
  return (
    <Card className="p-10 text-center max-w-lg mx-auto">
      <CardTitle className="text-lg">No run data in this window yet</CardTitle>
      <p className="text-sm text-gray-600 mt-2">
        Run functional tests to populate charts and failure insights. Try widening the time window (top
        right) if you expected history here.
      </p>
      <Link
        to={cases}
        className="mt-6 inline-flex rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
      >
        Run tests
      </Link>
    </Card>
  )
}
