import { Link } from 'react-router-dom'
import { ChevronRightIcon } from '@heroicons/react/24/outline'

import type { AnalyticsTopFailingTest } from '../../types'

import { ActionCard } from './ActionCard'
import { Sparkline } from './Sparkline'

type Props = {
  projectId: string
  top: AnalyticsTopFailingTest[]
}

export function TopFailingTestsCard({ projectId, top }: Props) {
  const base = `/projects/${projectId}`
  if (!top.length) {
    return (
      <ActionCard title="Top failing tests" hint="Most failures in this window.">
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center text-sm text-gray-500">
          No failing tests in this window.
        </div>
      </ActionCard>
    )
  }

  return (
    <ActionCard title="Top failing tests" hint="Most failures in this window.">
      <ul className="divide-y divide-gray-100">
        {top.map((t) => (
          <li key={t.test_case_id} className="py-2">
            <div className="flex items-center gap-3">
              <Sparkline statuses={t.recent_statuses} />
              <Link
                to={
                  t.latest_run_id
                    ? `${base}/functional-testing/history/${t.latest_run_id}`
                    : `${base}/functional-testing/cases/${t.test_case_id}`
                }
                className="group flex flex-1 min-w-0 items-center justify-between gap-2 rounded-md py-1 hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{t.title}</p>
                  <p className="text-[10px] text-gray-500">{t.fail_count} failure(s)</p>
                </div>
                <ChevronRightIcon className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-primary-500" />
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </ActionCard>
  )
}
