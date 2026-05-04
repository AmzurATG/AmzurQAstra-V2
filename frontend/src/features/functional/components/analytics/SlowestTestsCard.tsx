import { Link } from 'react-router-dom'
import { ChevronRightIcon } from '@heroicons/react/24/outline'

import type { AnalyticsSlowTest } from '../../types'

import { ActionCard } from './ActionCard'

type Props = {
  projectId: string
  slow: AnalyticsSlowTest[]
}

function fmtMs(ms: number): string {
  if (ms >= 60000) return `${(ms / 60000).toFixed(1)} min`
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)} s`
  return `${ms} ms`
}

export function SlowestTestsCard({ projectId, slow }: Props) {
  const base = `/projects/${projectId}/functional-testing/cases`
  if (!slow.length) {
    return (
      <ActionCard title="Slowest tests (p95)" hint="Per-case duration in this window.">
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center text-sm text-gray-500">
          No duration data yet.
        </div>
      </ActionCard>
    )
  }

  const max = Math.max(...slow.map((s) => s.p95_ms), 1)

  return (
    <ActionCard title="Slowest tests (p95)" hint="Per-case duration in this window.">
      <ul className="space-y-2">
        {slow.map((s) => (
          <li key={s.test_case_id}>
            <Link
              to={`${base}/${s.test_case_id}`}
              className="group flex items-center gap-2 rounded-md py-1 hover:bg-gray-50"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-gray-900 truncate">{s.title}</p>
                  <span className="text-xs tabular-nums text-gray-600 shrink-0">
                    {fmtMs(s.p95_ms)}
                  </span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary-500"
                    style={{ width: `${Math.min(100, (s.p95_ms / max) * 100)}%` }}
                  />
                </div>
                <p className="text-[10px] text-gray-400 mt-0.5">{s.runs_used} runs with timings</p>
              </div>
              <ChevronRightIcon className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-primary-500" />
            </Link>
          </li>
        ))}
      </ul>
    </ActionCard>
  )
}
