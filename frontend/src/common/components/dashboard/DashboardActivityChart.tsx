import { format, parseISO } from 'date-fns'
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
import type { DashboardActivityDay } from '@features/functional/types'

type Row = {
  label: string
  Passed: number
  Failed: number
  Other: number
}

export function DashboardActivityChart({ days }: { days: DashboardActivityDay[] }) {
  const data: Row[] = days.map((d) => ({
    label: format(parseISO(d.date), 'EEE M/d'),
    Passed: d.passed,
    Failed: d.failed,
    Other: d.other,
  }))

  const hasData = data.some((r) => r.Passed + r.Failed + r.Other > 0)

  return (
    <div className="h-[280px] w-full">
      {!hasData ? (
        <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/80 text-sm text-gray-500">
          No test runs in the last 7 days
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} className="text-gray-600" />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={36} />
            <Tooltip
              contentStyle={{
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                fontSize: '12px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="Passed" stackId="runs" fill="#16a34a" radius={[0, 0, 0, 0]} />
            <Bar dataKey="Failed" stackId="runs" fill="#dc2626" />
            <Bar dataKey="Other" stackId="runs" fill="#94a3b8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
