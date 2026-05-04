import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { AnalyticsTrendPoint } from '../../types'

import { ANALYTICS_COLORS } from './analyticsTokens'

type Props = {
  points: AnalyticsTrendPoint[]
}

export function PassRateTrendLine({ points }: Props) {
  const data = points.map((p) => ({
    label: `#${p.run_number}`,
    rate: p.value,
    runId: p.run_id,
  }))

  if (!data.length) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/80 text-sm text-gray-500">
        Not enough finished runs in this window for a trend line.
      </div>
    )
  }

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={32} />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e5e7eb',
              fontSize: 12,
            }}
            formatter={(v: number) => [`${v}%`, 'Pass rate']}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          <Line
            type="monotone"
            dataKey="rate"
            name="Result pass %"
            stroke={ANALYTICS_COLORS.passed}
            strokeWidth={2}
            dot={{ r: 3, fill: ANALYTICS_COLORS.passed }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
