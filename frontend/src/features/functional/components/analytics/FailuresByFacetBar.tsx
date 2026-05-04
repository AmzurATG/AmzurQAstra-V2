import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { AnalyticsBarPoint } from '../../types'

import { ANALYTICS_COLORS } from './analyticsTokens'

type Props = {
  byCategory: AnalyticsBarPoint[]
  byPriority: AnalyticsBarPoint[]
}

export function FailuresByFacetBar({ byCategory, byPriority }: Props) {
  const [facet, setFacet] = useState<'category' | 'priority'>('category')
  const data =
    facet === 'category'
      ? byCategory.map((r) => ({
          name: r.facet_value,
          Passed: r.passed,
          Failed: r.failed + r.error,
          'Not executed': r.not_executed,
        }))
      : byPriority.map((r) => ({
          name: r.facet_value,
          Passed: r.passed,
          Failed: r.failed + r.error,
          'Not executed': r.not_executed,
        }))

  const hasData = data.some((d) => d.Passed + d.Failed + d['Not executed'] > 0)

  if (!hasData) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/80 text-sm text-gray-500">
        No test results in this window to group by {facet}.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-1">
        <button
          type="button"
          className={`rounded-md px-2 py-1 text-xs font-semibold ${
            facet === 'category' ? 'bg-primary-100 text-primary-800' : 'text-gray-600'
          }`}
          onClick={() => setFacet('category')}
        >
          Category
        </button>
        <button
          type="button"
          className={`rounded-md px-2 py-1 text-xs font-semibold ${
            facet === 'priority' ? 'bg-primary-100 text-primary-800' : 'text-gray-600'
          }`}
          onClick={() => setFacet('priority')}
        >
          Priority
        </button>
      </div>
      <div className="h-[240px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={48} />
            <YAxis allowDecimals={false} tick={{ fontSize: 10 }} width={28} />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: '1px solid #e5e7eb',
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="Passed" stackId="a" fill={ANALYTICS_COLORS.passed} />
            <Bar dataKey="Failed" stackId="a" fill={ANALYTICS_COLORS.failed} />
            <Bar
              dataKey="Not executed"
              stackId="a"
              fill={ANALYTICS_COLORS.notExecuted}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
