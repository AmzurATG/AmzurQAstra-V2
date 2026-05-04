import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import type { AnalyticsLatestRunBreakdown } from '../../types'

import { ANALYTICS_COLORS } from './analyticsTokens'

type Props = {
  latest: AnalyticsLatestRunBreakdown | null
}

export function LatestRunDonut({ latest }: Props) {
  if (!latest) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/80 text-sm text-gray-500">
        No finished runs yet — run tests to see this chart.
      </div>
    )
  }

  const failedTotal = latest.failed + latest.error
  const data = [
    { name: 'Passed', value: latest.passed, color: ANALYTICS_COLORS.passed },
    { name: 'Not executed', value: latest.not_executed, color: ANALYTICS_COLORS.notExecuted },
    { name: 'Failed', value: failedTotal, color: ANALYTICS_COLORS.failed },
  ].filter((d) => d.value > 0)

  const total = latest.passed + latest.failed + latest.not_executed + latest.error
  const pct = total > 0 ? Math.round((latest.passed / total) * 100) : 0

  if (!data.length) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/80 text-sm text-gray-500">
        No results in the latest run.
      </div>
    )
  }

  return (
    <div className="h-[280px] w-full relative">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={58}
            outerRadius={88}
            paddingAngle={2}
            isAnimationActive={false}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e5e7eb',
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-2xl font-bold tabular-nums text-gray-900">{pct}%</span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-gray-500">
          Pass rate
        </span>
        <span className="text-[10px] text-gray-400 mt-0.5">Run #{latest.run_number}</span>
      </div>
      {latest.cancelled_runs_in_window > 0 ? (
        <p className="text-[10px] text-center text-gray-500 mt-1">
          {latest.cancelled_runs_in_window} cancelled run(s) in window (not executed / on hold)
        </p>
      ) : null}
    </div>
  )
}
