import { useParams } from 'react-router-dom'

import { Button } from '@common/components/ui/Button'
import { PageLoader } from '@common/components/ui/Loader'

import { useAnalyticsWindow } from '../../hooks/useAnalyticsWindow'
import { useProjectAnalytics } from '../../hooks/useProjectAnalytics'
import { FunctionalAnalyticsTab } from './FunctionalAnalyticsTab'

export default function Analytics() {
  const { projectId } = useParams<{ projectId: string }>()
  const { window, setWindow } = useAnalyticsWindow()
  const { data, loading, error, reload } = useProjectAnalytics(projectId, window)

  if (!projectId) return null
  if (loading && !data) return <PageLoader />
  if (error || !data) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">Test report analytics</h1>
        <p className="text-red-600">{error ?? 'Could not load analytics.'}</p>
        <Button variant="outline" size="sm" onClick={() => void reload()}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <FunctionalAnalyticsTab
      projectId={projectId}
      window={window}
      onWindowChange={setWindow}
      data={data}
    />
  )
}
