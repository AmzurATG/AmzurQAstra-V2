import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { useProjectStore } from '@common/store/projectStore'
import { useProjectOverviewStats } from '../hooks/useProjectOverviewStats'
import {
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  PlayIcon,
  ShieldCheckIcon,
  SparklesIcon,
  Cog6ToothIcon,
  BookOpenIcon,
  LinkIcon,
} from '@heroicons/react/24/outline'

export default function ProjectOverview() {
  const { projectId } = useParams<{ projectId: string }>()
  const { currentProject } = useProjectStore()
  const { labels, loading } = useProjectOverviewStats(projectId)

  const features = useMemo(
    () => [
      {
        name: 'User Stories',
        description: 'Import and manage user stories from Jira or Redmine',
        icon: BookOpenIcon,
        href: `/projects/${projectId}/user-stories`,
        statKey: 'userStories' as const,
      },
      {
        name: 'Requirements',
        description: 'Upload requirement documents to generate test cases',
        icon: DocumentTextIcon,
        href: `/projects/${projectId}/requirements`,
        statKey: 'requirements' as const,
      },
      {
        name: 'Test Cases',
        description: 'AI-generated and manual test cases',
        icon: ClipboardDocumentListIcon,
        href: `/projects/${projectId}/test-cases`,
        statKey: 'testCases' as const,
      },
      {
        name: 'Test Runs',
        description: 'Execute tests via Playwright MCP',
        icon: PlayIcon,
        href: `/projects/${projectId}/test-runs`,
        statKey: 'testRuns' as const,
      },
      {
        name: 'Integrity Check',
        description: 'Verify your app is ready for testing',
        icon: ShieldCheckIcon,
        href: `/projects/${projectId}/integrity-check`,
        statKey: 'integrity' as const,
      },
      {
        name: 'Integrations',
        description: 'Connect to Jira, Azure DevOps, and more',
        icon: LinkIcon,
        href: `/projects/${projectId}/integrations`,
        statKey: 'integrations' as const,
      },
    ],
    [projectId]
  )

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-gray-900">
            {currentProject?.name || 'Project Overview'}
          </h1>
          <p className="break-words text-gray-600">
            {currentProject?.description || 'AI-powered test generation and automation'}
          </p>
        </div>
        <Link
          to={`/projects/${projectId}/settings`}
          className="flex shrink-0 items-center gap-2 self-start rounded-lg px-4 py-2 text-gray-600 hover:bg-gray-100"
        >
          <Cog6ToothIcon className="h-5 w-5 shrink-0" />
          Settings
        </Link>
      </div>

      {currentProject?.app_url && (
        <Card className="min-w-0 bg-gradient-to-r from-primary-50 to-primary-100">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-primary-600">Target Application</p>
              <a
                href={currentProject.app_url}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all text-lg font-semibold text-primary-700 hover:underline"
                title={currentProject.app_url}
              >
                {currentProject.app_url}
              </a>
            </div>
            <Link
              to={`/projects/${projectId}/integrity-check`}
              className="shrink-0 rounded-lg bg-primary-600 px-4 py-2 text-center text-white hover:bg-primary-700"
            >
              Run Integrity Check
            </Link>
          </div>
        </Card>
      )}

      <Card className="min-w-0 bg-gradient-to-r from-primary-500 to-primary-600 text-white">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <SparklesIcon className="h-12 w-12 shrink-0" />
          <div className="min-w-0">
            <h2 className="text-xl font-bold">Get Started with AI Testing</h2>
            <p className="mt-1 opacity-90">
              Upload a requirement document or connect to Jira to auto-generate test cases
            </p>
          </div>
        </div>
      </Card>

      <div className="grid min-w-0 grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => {
          const statText =
            loading || !labels
              ? '…'
              : labels[feature.statKey] ?? '—'

          return (
            <Link key={feature.name} to={feature.href} className="min-w-0">
              <Card className="h-full min-w-0 transition-shadow hover:shadow-md">
                <div className="flex items-start gap-4">
                  <div className="shrink-0 rounded-lg bg-primary-100 p-3">
                    <feature.icon className="h-6 w-6 text-primary-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-gray-900">{feature.name}</h3>
                      <span
                        className={`shrink-0 text-right text-sm text-primary-600 ${
                          loading ? 'animate-pulse text-primary-300' : ''
                        }`}
                      >
                        {statText}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">{feature.description}</p>
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>

      <Card className="min-w-0">
        <CardTitle>How It Works</CardTitle>
        <div className="mt-4 grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { step: 1, title: 'Upload Requirements', desc: 'PDF, Word, or from Jira' },
            { step: 2, title: 'Generate Tests', desc: 'AI creates test cases' },
            { step: 3, title: 'Review & Edit', desc: 'Refine test steps' },
            { step: 4, title: 'Execute', desc: 'Run via Playwright' },
          ].map((item) => (
            <div key={item.step} className="min-w-0 text-center">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 font-bold text-primary-600">
                {item.step}
              </div>
              <h4 className="mt-2 font-medium">{item.title}</h4>
              <p className="text-sm text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
