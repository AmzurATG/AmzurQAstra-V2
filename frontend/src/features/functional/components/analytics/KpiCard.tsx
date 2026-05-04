import {
  ArrowRightIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline'

import type { AnalyticsKpiPoint } from '../../types'

type Props = {
  kpi: AnalyticsKpiPoint
}

function trendVisual(kpi: AnalyticsKpiPoint): { Icon: typeof ArrowTrendingUpIcon; className: string } {
  if (kpi.trend === 'flat') {
    return { Icon: ArrowRightIcon, className: 'text-gray-400' }
  }
  const good =
    (kpi.trend === 'up' && kpi.higher_is_better) ||
    (kpi.trend === 'down' && !kpi.higher_is_better)
  if (kpi.trend === 'up') {
    return {
      Icon: ArrowTrendingUpIcon,
      className: good ? 'text-green-600' : 'text-red-600',
    }
  }
  return {
    Icon: ArrowTrendingDownIcon,
    className: good ? 'text-green-600' : 'text-red-600',
  }
}

export function KpiCard({ kpi }: Props) {
  const { Icon, className } = trendVisual(kpi)
  return (
    <div
      className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
      title={kpi.help}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{kpi.label}</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-2xl font-bold tabular-nums text-gray-900">{kpi.value}</span>
        {kpi.delta ? (
          <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${className}`}>
            <Icon className="h-4 w-4" />
            {kpi.delta}
          </span>
        ) : kpi.trend !== 'flat' ? (
          <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${className}`}>
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
    </div>
  )
}
