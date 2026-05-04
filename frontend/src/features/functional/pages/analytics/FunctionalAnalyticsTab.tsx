import { format, parseISO } from 'date-fns'
import { Link } from 'react-router-dom'

import { Card, CardTitle } from '@common/components/ui/Card'

import type { AnalyticsWindow, ProjectAnalytics } from '../../types'
import { AnalyticsHeader } from '../../components/analytics/AnalyticsHeader'
import { FailuresByFacetBar } from '../../components/analytics/FailuresByFacetBar'
import { FailureClustersCard } from '../../components/analytics/FailureClustersCard'
import { FlakyTestsCard } from '../../components/analytics/FlakyTestsCard'
import { KpiStrip } from '../../components/analytics/KpiStrip'
import { LatestRunDonut } from '../../components/analytics/LatestRunDonut'
import { PassRateTrendLine } from '../../components/analytics/PassRateTrendLine'
import { SlowestTestsCard } from '../../components/analytics/SlowestTestsCard'
import { StaleTestsCard } from '../../components/analytics/StaleTestsCard'
import { TopFailingTestsCard } from '../../components/analytics/TopFailingTestsCard'

import { EmptyAnalytics } from './EmptyAnalytics'

type Props = {
  projectId: string
  window: AnalyticsWindow
  onWindowChange: (w: AnalyticsWindow) => void
  data: ProjectAnalytics
}

function isAnalyticsEmpty(data: ProjectAnalytics): boolean {
  const noLatest = data.latest_run === null
  const noTrend = data.pass_rate_trend.length === 0
  const noBars = data.failures_by_category.length === 0
  return noLatest && noTrend && noBars
}

export function FunctionalAnalyticsTab({ projectId, window, onWindowChange, data }: Props) {
  const empty = isAnalyticsEmpty(data)

  return (
    <div className="space-y-8">
      <AnalyticsHeader window={window} onWindowChange={onWindowChange} activeSource="functional" />

      {empty ? (
        <EmptyAnalytics projectId={projectId} />
      ) : (
        <>
          <KpiStrip kpis={data.kpis} />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card>
              <CardTitle className="mb-1 text-base">Latest run breakdown</CardTitle>
              <p className="text-xs text-gray-500 mb-2">Passed vs not executed vs failed (latest finished run).</p>
              <LatestRunDonut latest={data.latest_run} />
            </Card>
            <Card>
              <CardTitle className="mb-1 text-base">Pass rate by run</CardTitle>
              <p className="text-xs text-gray-500 mb-2">Result-level pass % — up to last 30 runs in this window.</p>
              <PassRateTrendLine points={data.pass_rate_trend} />
            </Card>
          </div>

          <Card>
            <CardTitle className="mb-1 text-base">Results by test case facet</CardTitle>
            <p className="text-xs text-gray-500 mb-2">Stacked counts for all results in the window.</p>
            <FailuresByFacetBar
              byCategory={data.failures_by_category}
              byPriority={data.failures_by_priority}
            />
          </Card>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <TopFailingTestsCard projectId={projectId} top={data.top_failing} />
            <FailureClustersCard projectId={projectId} clusters={data.failure_clusters} />
            <FlakyTestsCard projectId={projectId} flaky={data.flaky} />
            <SlowestTestsCard projectId={projectId} slow={data.slowest} />
            <StaleTestsCard projectId={projectId} stale={data.stale} />
          </div>

          <div className="flex flex-wrap justify-center gap-4 text-sm">
            <Link
              to={`/projects/${projectId}/functional-testing/history?status_filter=failed`}
              className="font-medium text-primary-600 hover:text-primary-700"
            >
              View failed runs in history
            </Link>
            <Link
              to={`/projects/${projectId}/functional-testing/cases`}
              className="font-medium text-primary-600 hover:text-primary-700"
            >
              Open test cases
            </Link>
          </div>
        </>
      )}

      <p className="text-[10px] text-gray-400 text-center">
        Generated {format(parseISO(data.generated_at), 'MMM d, yyyy HH:mm')} UTC · Scope: functional runs
        only
      </p>
    </div>
  )
}
