import { useParams, Link } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { useProjectStore } from '@common/store/projectStore'
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

  const features = [
    {
      name: 'User Stories',
      description: 'Import and manage user stories from Jira or Redmine',
      icon: BookOpenIcon,
      href: `/projects/${projectId}/user-stories`,
      stats: '5 stories',
    },
    {
      name: 'Requirements',
      description: 'Upload requirement documents to generate test cases',
      icon: DocumentTextIcon,
      href: `/projects/${projectId}/requirements`,
      stats: '12 documents',
    },
    {
      name: 'Test Cases',
      description: 'AI-generated and manual test cases',
      icon: ClipboardDocumentListIcon,
      href: `/projects/${projectId}/test-cases`,
      stats: '156 cases',
    },
    {
      name: 'Test Runs',
      description: 'Execute tests via Playwright MCP',
      icon: PlayIcon,
      href: `/projects/${projectId}/test-runs`,
      stats: '24 runs',
    },
    {
      name: 'Integrity Check',
      description: 'Verify your app is ready for testing',
      icon: ShieldCheckIcon,
      href: `/projects/${projectId}/integrity-check`,
      stats: 'Last: 2h ago',
    },
    {
      name: 'Integrations',
      description: 'Connect to Jira, Azure DevOps, and more',
      icon: LinkIcon,
      href: `/projects/${projectId}/integrations`,
      stats: '2 connected',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {currentProject?.name || 'Project Overview'}
          </h1>
          <p className="text-gray-600">
            {currentProject?.description || 'AI-powered test generation and automation'}
          </p>
        </div>
        <Link
          to={`/projects/${projectId}/settings`}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          <Cog6ToothIcon className="w-5 h-5" />
          Settings
        </Link>
      </div>

      {/* Project Info */}
      {currentProject?.app_url && (
        <Card className="bg-gradient-to-r from-primary-50 to-primary-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-primary-600 font-medium">Target Application</p>
              <a
                href={currentProject.app_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-lg font-semibold text-primary-700 hover:underline"
              >
                {currentProject.app_url}
              </a>
            </div>
            <Link
              to={`/projects/${projectId}/integrity-check`}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Run Integrity Check
            </Link>
          </div>
        </Card>
      )}

      {/* Quick Start */}
      <Card className="bg-gradient-to-r from-primary-500 to-primary-600 text-white">
        <div className="flex items-center gap-4">
          <SparklesIcon className="w-12 h-12" />
          <div>
            <h2 className="text-xl font-bold">Get Started with AI Testing</h2>
            <p className="opacity-90 mt-1">
              Upload a requirement document or connect to Jira to auto-generate test cases
            </p>
          </div>
        </div>
      </Card>

      {/* Feature Cards - 3 columns, 2 rows */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => (
          <Link key={feature.name} to={feature.href}>
            <Card className="hover:shadow-md transition-shadow h-full">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <feature.icon className="w-6 h-6 text-primary-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">{feature.name}</h3>
                    <span className="text-sm text-primary-600">{feature.stats}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{feature.description}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Workflow Overview */}
      <Card>
        <CardTitle>How It Works</CardTitle>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { step: 1, title: 'Upload Requirements', desc: 'PDF, Word, or from Jira' },
            { step: 2, title: 'Generate Tests', desc: 'AI creates test cases' },
            { step: 3, title: 'Review & Edit', desc: 'Refine test steps' },
            { step: 4, title: 'Execute', desc: 'Run via Playwright' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-10 h-10 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center mx-auto font-bold">
                {item.step}
              </div>
              <h4 className="font-medium mt-2">{item.title}</h4>
              <p className="text-sm text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
