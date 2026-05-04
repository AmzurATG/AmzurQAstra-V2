import { Link } from 'react-router-dom'
import { ChevronRightIcon } from '@heroicons/react/24/outline'

import type { AnalyticsFlakyTest } from '../../types'

import { ActionCard } from './ActionCard'
import { ANALYTICS_COLORS } from './analyticsTokens'

type Props = {
  projectId: string
  flaky: AnalyticsFlakyTest[]
}

export function FlakyTestsCard({ projectId, flaky }: Props) {
  const base = `/projects/${projectId}/functional-testing/cases`
  if (!flaky.length) {
    return (
      <ActionCard
        title="Flaky tests"
        hint="Cases with 2+ status changes in their last 10 results (this window)."
      >
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center text-sm text-gray-500">
          No flaky patterns detected.
        </div>
      </ActionCard>
    )
  }

  return (
    <ActionCard
      title="Flaky tests"
      hint="Cases with 2+ status changes in their last 10 results (this window)."
    >
      <ul className="divide-y divide-gray-100">
        {flaky.map((f) => (
          <li key={f.test_case_id} className="py-2">
            <Link
              to={`${base}/${f.test_case_id}`}
              className="group flex items-center justify-between gap-2 rounded-md py-1 hover:bg-gray-50"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{f.title}</p>
                <p className="text-[10px] text-gray-500">
                  <span style={{ color: ANALYTICS_COLORS.flaky }} className="font-semibold">
                    {f.flips} flips
                  </span>
                  {' · last: '}
                  <span className="uppercase">{f.last_status}</span>
                </p>
              </div>
              <ChevronRightIcon className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-primary-500" />
            </Link>
          </li>
        ))}
      </ul>
    </ActionCard>
  )
}
