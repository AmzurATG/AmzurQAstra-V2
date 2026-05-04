import { Link } from 'react-router-dom'
import { ChevronRightIcon } from '@heroicons/react/24/outline'

import type { AnalyticsStaleTest } from '../../types'

import { ActionCard } from './ActionCard'

type Props = {
  projectId: string
  stale: AnalyticsStaleTest[]
}

export function StaleTestsCard({ projectId, stale }: Props) {
  const base = `/projects/${projectId}/functional-testing/cases`
  if (!stale.length) {
    return (
      <ActionCard
        title="Stale tests"
        hint="Ready cases with no execution in this window."
      >
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center text-sm text-gray-500">
          All ready cases ran at least once this window.
        </div>
      </ActionCard>
    )
  }

  return (
    <ActionCard title="Stale tests" hint="Ready cases with no execution in this window.">
      <ul className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
        {stale.slice(0, 20).map((s) => (
          <li key={s.test_case_id} className="py-2">
            <Link
              to={`${base}/${s.test_case_id}`}
              className="group flex items-center justify-between gap-2 rounded-md py-1 hover:bg-gray-50"
            >
              <span className="text-sm text-gray-800 truncate">{s.title}</span>
              <ChevronRightIcon className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-primary-500" />
            </Link>
          </li>
        ))}
      </ul>
      {stale.length > 20 ? (
        <p className="text-[10px] text-gray-400 mt-2">+{stale.length - 20} more</p>
      ) : null}
    </ActionCard>
  )
}
