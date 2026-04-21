import { formatDistanceToNow } from 'date-fns'
import { Link } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { PageLoader } from '@common/components/ui/Loader'
import { Button } from '@common/components/ui/Button'
import { DashboardActivityChart } from '@common/components/dashboard/DashboardActivityChart'
import { useDashboardOverview } from '@common/hooks/useDashboardOverview'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentListIcon,
  ClockIcon,
  FolderIcon,
  PlayIcon,
  StopCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'

function RunStatusIcon({ status }: { status: string }) {
  const s = status.toLowerCase()
  if (s === 'passed') return <CheckCircleIcon className="h-5 w-5 shrink-0 text-green-500" />
  if (s === 'failed' || s === 'error')
    return <XCircleIcon className="h-5 w-5 shrink-0 text-red-500" />
  if (s === 'running') return <ArrowPathIcon className="h-5 w-5 shrink-0 text-blue-500" />
  if (s === 'pending') return <ClockIcon className="h-5 w-5 shrink-0 text-amber-500" />
  if (s === 'cancelled') return <StopCircleIcon className="h-5 w-5 shrink-0 text-gray-400" />
  return <PlayIcon className="h-5 w-5 shrink-0 text-gray-400" />
}

function formatProjectSubtitle(description: string | null | undefined) {
  if (!description || !description.trim()) return null
  return description.trim()
}

export default function Dashboard() {
  const { data, loading, error, reload } = useDashboardOverview()

  if (loading) return <PageLoader />

  if (error || !data) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Card className="p-6">
          <p className="text-red-600">{error ?? 'Unable to load dashboard.'}</p>
          <Button className="mt-4" onClick={() => reload()}>
            Retry
          </Button>
        </Card>
      </div>
    )
  }

  const stats = [
    {
      name: 'Projects',
      value: data.project_count,
      sub: 'Active projects you can access',
      icon: FolderIcon,
      href: '/projects',
    },
    {
      name: 'Test cases',
      value: data.test_cases_total,
      sub: 'Across all projects',
      icon: ClipboardDocumentListIcon,
      href: '/projects',
    },
    {
      name: 'Test runs',
      value: data.runs_total,
      sub:
        data.runs_total > 0
          ? `${data.runs_passed} passed · ${data.runs_failed} failed`
          : 'No runs yet',
      icon: PlayIcon,
      href: '/projects',
    },
    {
      name: 'Pass rate',
      value: `${data.avg_pass_rate}%`,
      sub: 'Finished runs that passed (all time)',
      icon: CheckCircleIcon,
      href: '/projects',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Overview of your QA automation · data from all your projects</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => reload()}>
          <ArrowPathIcon className="mr-1.5 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.name} to={stat.href} className="block min-h-[108px]">
            <Card className="h-full transition-shadow hover:shadow-md">
              <div className="flex items-start gap-4">
                <div className="shrink-0 rounded-lg bg-primary-100 p-3">
                  <stat.icon className="h-6 w-6 text-primary-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold tabular-nums text-gray-900">{stat.value}</p>
                  <p className="mt-1 line-clamp-2 text-xs text-gray-500">{stat.sub}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <div className="mb-2 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
          <CardTitle className="mb-0">Run activity (last 7 days)</CardTitle>
          <span className="text-xs text-gray-500">UTC · stacked by outcome when each run was created</span>
        </div>
        <DashboardActivityChart days={data.activity_by_day} />
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="mb-2 flex items-center justify-between gap-2">
            <CardTitle className="mb-0">Recent test runs</CardTitle>
            <Link
              to="/projects"
              className="shrink-0 text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              Projects
            </Link>
          </div>
          <div className="mt-4 space-y-1">
            {data.recent_runs.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500">No test runs yet.</p>
            ) : (
              data.recent_runs.map((run) => (
                <Link
                  key={run.id}
                  to={`/projects/${run.project_id}/functional-testing/history/${run.id}`}
                  className="flex items-center justify-between gap-3 rounded-md py-2.5 pl-1 pr-2 transition-colors hover:bg-gray-50"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <RunStatusIcon status={run.status} />
                    <div className="min-w-0">
                      <p className="truncate font-medium text-gray-900">
                        {run.name?.trim() || `Run #${run.id}`}
                      </p>
                      <p className="truncate text-sm text-gray-500">
                        {run.description?.trim() || run.project_name}
                      </p>
                    </div>
                  </div>
                  <span className="shrink-0 text-xs text-gray-500">
                    {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                  </span>
                </Link>
              ))
            )}
          </div>
        </Card>

        <Card>
          <div className="mb-2 flex items-center justify-between gap-2">
            <CardTitle className="mb-0">Recent projects</CardTitle>
            <Link
              to="/projects"
              className="shrink-0 text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              View all
            </Link>
          </div>
          <div className="mt-4 space-y-1">
            {data.recent_projects.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500">No projects yet.</p>
            ) : (
              data.recent_projects.map((project) => {
                const sub = formatProjectSubtitle(project.description)
                return (
                  <Link
                    key={project.id}
                    to={`/projects/${project.id}`}
                    className="flex items-start gap-3 rounded-md py-2.5 pl-1 pr-2 transition-colors hover:bg-gray-50"
                  >
                    <FolderIcon className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900">{project.name}</p>
                      {sub ? (
                        <p className="break-words text-sm text-gray-500 line-clamp-2" title={sub}>
                          {sub}
                        </p>
                      ) : (
                        <p className="text-sm italic text-gray-400">No description</p>
                      )}
                    </div>
                  </Link>
                )
              })
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
