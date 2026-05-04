import { Link } from 'react-router-dom'
import { ChevronRightIcon } from '@heroicons/react/24/outline'

import type { AnalyticsFailureCluster } from '../../types'

import { ActionCard } from './ActionCard'

type Props = {
  projectId: string
  clusters: AnalyticsFailureCluster[]
}

export function FailureClustersCard({ projectId, clusters }: Props) {
  const base = `/projects/${projectId}`
  if (!clusters.length) {
    return (
      <ActionCard
        title="Failure clusters"
        hint="Grouped error signatures from this window. Jira / Azure DevOps mapping is planned."
      >
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center text-sm text-gray-500">
          No failures in this window.
        </div>
      </ActionCard>
    )
  }

  return (
    <ActionCard
      title="Failure clusters"
      hint="Grouped error signatures from this window. Jira / Azure DevOps mapping is planned."
    >
      <ul className="divide-y divide-gray-100">
        {clusters.slice(0, 8).map((c) => (
          <li key={c.signature} className="py-2">
            <Link
              to={
                c.sample_test_case_id
                  ? `${base}/functional-testing/cases/${c.sample_test_case_id}`
                  : `${base}/functional-testing/history/${c.last_seen_run_id}`
              }
              className="group flex items-start gap-2 rounded-md py-1 hover:bg-gray-50"
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-gray-800 line-clamp-2" title={c.signature}>
                  {c.signature || '(empty message)'}
                </p>
                <p className="text-[10px] text-gray-500 mt-0.5">
                  {c.count} hit(s)
                  {c.sample_test_case_title ? ` · ${c.sample_test_case_title}` : ''}
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
