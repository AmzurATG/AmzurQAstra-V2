import { Line, LineChart, ResponsiveContainer } from 'recharts'

import { ANALYTICS_COLORS } from './analyticsTokens'

function statusToY(s: string): number {
  if (s === 'passed') return 3
  if (s === 'skipped') return 1
  if (s === 'failed' || s === 'error') return 0
  return 1.5
}

type Props = {
  statuses: string[]
}

export function Sparkline({ statuses }: Props) {
  const data = statuses.map((s, i) => ({ i, v: statusToY(s) }))
  if (!data.length) {
    return <div className="h-8 w-16 rounded border border-dashed border-gray-200 bg-gray-50" />
  }
  return (
    <div className="h-8 w-16 shrink-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={ANALYTICS_COLORS.passed}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
