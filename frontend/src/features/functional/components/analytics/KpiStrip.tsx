import type { AnalyticsKpiPoint } from '../../types'

import { KpiCard } from './KpiCard'

type Props = {
  kpis: AnalyticsKpiPoint[]
}

export function KpiStrip({ kpis }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((k) => (
        <KpiCard key={k.key} kpi={k} />
      ))}
    </div>
  )
}
