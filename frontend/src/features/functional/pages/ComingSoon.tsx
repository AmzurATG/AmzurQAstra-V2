import { useNavigate, useSearchParams, useParams } from 'react-router-dom'
import { ArrowLeftIcon, BeakerIcon, LockClosedIcon, BoltIcon, GlobeAltIcon, ShieldCheckIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'

// ---------------------------------------------------------------------------
// Feature registry — each "coming soon" test type has a description + icon
// ---------------------------------------------------------------------------

interface FeatureMeta {
  icon: React.ComponentType<{ className?: string }>
  description: string
  bulletPoints: string[]
  eta?: string
}

const FEATURE_REGISTRY: Record<string, FeatureMeta> = {
  'API Testing': {
    icon: BoltIcon,
    description:
      'Automated validation of your REST, GraphQL, and gRPC endpoints — from contract checks to load simulation.',
    bulletPoints: [
      'Auto-generate API test cases from OpenAPI / Swagger specs',
      'Schema validation, status-code assertions, and response-body checks',
      'Chain requests to test multi-step API workflows',
      'Run in CI/CD pipelines with zero browser overhead',
    ],
    eta: 'Q3 2026',
  },
  'API & Integration Testing': {
    icon: BoltIcon,
    description:
      'End-to-end integration tests that verify communication between your services, databases, and third-party APIs.',
    bulletPoints: [
      'Cross-service contract testing (e.g. consumer-driven contracts)',
      'Database state assertions before and after API calls',
      'Mock external dependencies with built-in stubs',
      'Track integration coverage against your requirement docs',
    ],
    eta: 'Q3 2026',
  },
  'Security Testing': {
    icon: LockClosedIcon,
    description:
      'Automated security scanning that surfaces OWASP Top 10 vulnerabilities and policy violations in your application.',
    bulletPoints: [
      'SQL injection, XSS, and CSRF detection',
      'Authentication and authorisation boundary checks',
      'Sensitive data exposure scans across HTTP responses',
      'OWASP-aligned severity scoring with remediation guidance',
    ],
    eta: 'Q4 2026',
  },
  'Performance Testing': {
    icon: ChartBarIcon,
    description:
      "Load, stress, and spike testing to validate your app's behaviour under real-world traffic conditions.",
    bulletPoints: [
      'Define concurrent-user scenarios from existing functional test cases',
      'P95 / P99 response-time thresholds with automatic pass/fail',
      'Identify bottlenecks across frontend, API, and database layers',
      'Generate performance regression reports per release',
    ],
    eta: 'Q4 2026',
  },
  'Compliance Testing': {
    icon: ShieldCheckIcon,
    description:
      'Verify that your application meets regulatory and industry-standard compliance requirements automatically.',
    bulletPoints: [
      'HIPAA, GDPR, SOC 2, and PCI-DSS compliance checks',
      'Audit-trail generation linked to specific test runs',
      'Policy-as-code rules you can extend for your domain',
      'Executive-ready compliance reports mapped to gap analysis',
    ],
    eta: 'Q1 2027',
  },
  'Usability Testing': {
    icon: GlobeAltIcon,
    description:
      'Automated heuristic checks and accessibility audits to surface UX issues before they reach your users.',
    bulletPoints: [
      'WCAG 2.2 AA / AAA accessibility scanning',
      'Core Web Vitals monitoring on key user journeys',
      'Broken-flow detection using AI-powered navigation heuristics',
      'Annotated screenshots highlighting usability findings',
    ],
    eta: 'Q1 2027',
  },
  'Compatibility Testing': {
    icon: BeakerIcon,
    description:
      'Cross-browser, cross-device, and cross-OS validation to ensure a consistent experience everywhere.',
    bulletPoints: [
      'Parallel test execution across Chrome, Firefox, Safari, and Edge',
      'Mobile viewport emulation and real-device cloud integration',
      'Visual regression diffing for pixel-level change detection',
      'Automatic retry on flaky cross-browser steps',
    ],
    eta: 'Q2 2027',
  },
}

const DEFAULT_FEATURE: FeatureMeta = {
  icon: BeakerIcon,
  description:
    'This testing capability is on our roadmap and will be available in a future release of QAstra.',
  bulletPoints: [
    'AI-assisted test generation tailored to your requirements',
    'Seamless integration with your existing workflows',
    'Detailed reporting and gap analysis support',
  ],
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ComingSoon() {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()

  const featureName = searchParams.get('feature') || 'This Testing Type'
  const meta = FEATURE_REGISTRY[featureName] ?? DEFAULT_FEATURE
  const Icon = meta.icon

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate(`/projects/${projectId}/requirements`)
    }
  }

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-lg text-center space-y-8">

        {/* Illustration */}
        <div className="flex justify-center">
          <div className="relative">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-amber-100 to-amber-200 flex items-center justify-center shadow-inner">
              <Icon className="w-12 h-12 text-amber-600" />
            </div>
            <span className="absolute -top-2 -right-2 bg-amber-500 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow">
              Soon
            </span>
          </div>
        </div>

        {/* Headline */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-gray-900">{featureName}</h1>
          <p className="text-gray-500 leading-relaxed">{meta.description}</p>
        </div>

        {/* What's coming */}
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 text-left space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            What&apos;s included
          </p>
          <ul className="space-y-2">
            {meta.bulletPoints.map((point, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-gray-700">
                <span className="mt-1 w-4 h-4 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center flex-shrink-0 text-xs font-bold">
                  {i + 1}
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>

        {/* ETA badge */}
        {meta.eta && (
          <p className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-50 border border-amber-200 text-sm font-medium text-amber-800">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            Expected: {meta.eta}
          </p>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button variant="outline" onClick={handleBack}>
            <ArrowLeftIcon className="w-4 h-4 mr-2" />
            Go back
          </Button>
          <Button
            onClick={() => navigate(`/projects/${projectId}/functional-testing/cases`)}
          >
            Run Functional Tests now
          </Button>
        </div>

        <p className="text-xs text-gray-400">
          Want to prioritise this feature? Reach out to the QAstra team and let us know.
        </p>
      </div>
    </div>
  )
}
