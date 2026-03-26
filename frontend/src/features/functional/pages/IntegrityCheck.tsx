import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { useProjectStore } from '@common/store/projectStore'
import { integrityCheckApi } from '../api'
import { useIntegrityCheck } from '../hooks/useIntegrityCheck'
import { useAuthSession } from '../hooks/useAuthSession'
import { AuthSessionPanel } from '../components/AuthSessionPanel'
import { StepTimeline } from '../components/StepTimeline'
import { ScreenshotFilmstrip } from '../components/ScreenshotFilmstrip'
import type {
  IntegrityLoginMode,
  IntegrityCheckPreview,
  IntegrityCheckResult,
  IntegrityCheckRun,
} from '../types'
import toast from 'react-hot-toast'
import { resolveScreenshotUrl } from '@common/utils/backendOrigin'
import {
  ShieldCheckIcon,
  PlayIcon,
  XCircleIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
  ListBulletIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ArchiveBoxIcon,
  ArrowTopRightOnSquareIcon,
  ArrowPathIcon,
  ClipboardDocumentIcon,
  GlobeAltIcon,
  KeyIcon,
} from '@heroicons/react/24/outline'

type Tab = 'run' | 'history'

function safeExternalHref(url: string): string | null {
  try {
    const u = new URL(url.trim())
    if (u.protocol === 'http:' || u.protocol === 'https:') return u.href
  } catch {
    /* ignore */
  }
  return null
}

function truncateUrl(url: string, max = 48): string {
  if (url.length <= max) return url
  return `${url.slice(0, max)}…`
}

function labelAuthMethod(m: IntegrityCheckRun['auth_method']): string {
  if (m === 'google_sso') return 'Google on app'
  if (m === 'google_oauth') return 'Google (legacy)'
  if (m === 'credentials') return 'App form'
  return 'No login'
}

const LOGIN_MODE_OPTIONS: {
  value: IntegrityLoginMode
  label: string
  hint: string
  Icon: typeof GlobeAltIcon
}[] = [
  {
    value: 'app_form',
    label: 'App login form',
    hint: 'Fill email & password on your application’s own login page',
    Icon: KeyIcon,
  },
  {
    value: 'google_sso',
    label: 'Google on site',
    hint: 'Clicks “Sign in with Google” on your app, then signs in with the Google account below',
    Icon: GlobeAltIcon,
  },
]

// ─── Small helpers ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    passed: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
    error: 'bg-red-100 text-red-700',
    running: 'bg-blue-100 text-blue-700',
    pending: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${map[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

function labelForScreenshotPath(path: string): string {
  const file = path.split('/').pop()?.replace(/\.png$/i, '') || path
  const m = file.match(/^step_(\d+)_(.+)$/i)
  if (!m) return file
  const n = m[1]
  const raw = m[2]
  if (n === '000') {
    if (raw === 'navigate') return 'Navigate'
    if (raw === 'post_login') return 'Post-login'
    if (raw.startsWith('login_')) return raw.replace(/^login_/, 'Login: ').replace(/_/g, ' ')
  }
  return `Step ${parseInt(n, 10)} · ${raw.replace(/_/g, ' ')}`
}

function buildScreenshotFilmstripItems(result: IntegrityCheckResult): { url: string; label: string }[] {
  const rows: { url: string; label: string }[] = []
  const seen = new Set<string>()
  for (const p of result.screenshots || []) {
    if (!p || seen.has(p)) continue
    seen.add(p)
    rows.push({ url: resolveScreenshotUrl(p), label: labelForScreenshotPath(p) })
  }
  for (const tc of result.test_case_results) {
    for (const s of tc.step_results) {
      const p = s.screenshot_path
      if (!p || seen.has(p)) continue
      seen.add(p)
      const shortTitle = tc.title.length > 28 ? `${tc.title.slice(0, 28)}…` : tc.title
      rows.push({
        url: resolveScreenshotUrl(p),
        label: `${shortTitle} · #${s.step_number}`,
      })
    }
  }
  return rows
}

function RunSummaryBanner({ result }: { result: NonNullable<ReturnType<typeof useIntegrityCheck>['result']> }) {
  const passed = result.status === 'passed'
  return (
    <div className={`flex flex-col gap-3 rounded-xl border p-4 ${passed ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className={`flex-shrink-0 rounded-full p-2 ${passed ? 'bg-emerald-100' : 'bg-red-100'}`}>
          {passed
            ? <ShieldCheckIcon className="h-7 w-7 text-emerald-600" />
            : <XCircleIcon className="h-7 w-7 text-red-600" />
          }
        </div>
        <div className="min-w-0 flex-1">
          <p className={`font-bold text-lg ${passed ? 'text-emerald-800' : 'text-red-800'}`}>
            {passed ? 'All checks passed' : 'Some checks failed'}
          </p>
          <p className="text-sm text-gray-600">
            {result.test_cases_passed}/{result.test_cases_total} test cases passed
            &nbsp;·&nbsp;
            {result.duration_ms != null ? `${(result.duration_ms / 1000).toFixed(1)}s` : ''}
          </p>
        </div>
        <div className="grid shrink-0 grid-cols-3 gap-3 text-center text-sm sm:min-w-[280px]">
          {[
            { label: 'Reachable', val: result.app_reachable ? 'Yes' : 'No', ok: result.app_reachable },
            { label: 'Login', val: result.login_successful == null ? 'Skipped' : result.login_successful ? 'OK' : 'Failed', ok: result.login_successful !== false },
            { label: 'Failed', val: String(result.test_cases_failed), ok: result.test_cases_failed === 0 },
          ].map(({ label, val, ok }) => (
            <div key={label} className="rounded-lg bg-white/70 px-3 py-1.5 shadow-sm">
              <p className="text-xs text-gray-500">{label}</p>
              <p className={`font-semibold ${ok ? 'text-emerald-700' : 'text-red-600'}`}>{val}</p>
            </div>
          ))}
        </div>
      </div>
      {(result.login_error || result.login_llm_diagnosis) && (
        <div className="rounded-lg border border-amber-200 bg-amber-50/90 p-3 text-sm text-amber-950">
          {result.login_error && <p className="font-medium text-amber-900">{result.login_error}</p>}
          {result.login_llm_diagnosis && (
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap font-sans text-xs text-amber-900/90">
              {result.login_llm_diagnosis}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Preview section (collapsed by default) ───────────────────────────────────

function PreviewSection({ projectId }: { projectId: number }) {
  const [open, setOpen] = useState(false)
  const [preview, setPreview] = useState<IntegrityCheckPreview | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    integrityCheckApi.getPreview(projectId)
      .then(r => setPreview(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [projectId])

  return (
    <Card>
      <button className="flex w-full items-center justify-between" onClick={() => setOpen(v => !v)}>
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="h-4 w-4 text-primary-500" />
          <CardTitle>Execution Preview</CardTitle>
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          {preview && <>
            <span className="flex items-center gap-1"><BookOpenIcon className="h-3.5 w-3.5" />{preview.total_user_stories} stories</span>
            <span className="flex items-center gap-1"><ClipboardDocumentListIcon className="h-3.5 w-3.5" />{preview.total_test_cases} cases</span>
            <span className="flex items-center gap-1"><ListBulletIcon className="h-3.5 w-3.5" />{preview.total_steps} steps</span>
          </>}
          {open ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
        </div>
      </button>

      {open && (
        <div className="mt-4">
          {loading && <p className="text-sm text-gray-500">Loading…</p>}
          {!loading && preview?.total_test_cases === 0 && (
            <div className="flex items-start gap-3 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
              <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />
              <p className="text-sm text-yellow-800">No test cases flagged for integrity check. Enable the toggle on User Stories or Test Cases.</p>
            </div>
          )}
          {!loading && preview && preview.total_test_cases > 0 && (
            <div className="space-y-1 text-sm text-gray-700">
              {preview.user_stories.map(us => (
                <div key={us.id} className="rounded border border-gray-100 px-3 py-2">
                  <p className="font-medium">{us.external_key && <span className="mr-1 font-mono text-primary-600">{us.external_key}</span>}{us.title}</p>
                  <p className="text-xs text-gray-400">{us.test_cases.length} test cases</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

// ─── History tab ──────────────────────────────────────────────────────────────

function historyBorderClass(status: IntegrityCheckRun['status']): string {
  if (status === 'passed') return 'border-l-emerald-500'
  if (status === 'failed' || status === 'error') return 'border-l-red-500'
  if (status === 'running') return 'border-l-blue-500'
  return 'border-l-gray-300'
}

function HistoryTab({
  projectId,
  onReuseUrl,
}: {
  projectId: number
  onReuseUrl: (url: string) => void
}) {
  const { history, isLoadingHistory, loadHistory } = useIntegrityCheck()
  useEffect(() => {
    loadHistory(projectId)
  }, [projectId, loadHistory])

  const copyUrl = async (url: string) => {
    const href = safeExternalHref(url)
    if (!href) {
      toast.error('Invalid URL to copy')
      return
    }
    try {
      await navigator.clipboard.writeText(href)
      toast.success('URL copied')
    } catch {
      toast.error('Could not copy')
    }
  }

  if (isLoadingHistory) {
    return <p className="py-6 text-center text-sm text-gray-500">Loading history…</p>
  }
  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-gray-400">
        <ArchiveBoxIcon className="h-10 w-10" />
        <p className="text-sm">No past runs yet. Run your first check on the New Run tab.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500">
        Open the app that was tested, copy the URL, or load it back into a new run.
      </p>
      {history.map(run => {
        const openHref = safeExternalHref(run.app_url)
        return (
          <div
            key={run.id}
            className={`rounded-xl border border-gray-200 border-l-4 bg-white shadow-sm transition-shadow hover:shadow-md ${historyBorderClass(run.status)}`}
          >
            <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={run.status} />
                  <span className="rounded-md bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-600">
                    Run #{run.id}
                  </span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {run.browser_engine === 'steel' ? 'Steel' : 'Playwright'}
                  </span>
                  <span className="rounded-md bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-800">
                    {labelAuthMethod(run.auth_method)}
                  </span>
                </div>
                <p className="break-all text-sm font-medium text-gray-900" title={run.app_url}>
                  {truncateUrl(run.app_url, 72)}
                </p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                  <span>
                    {run.test_cases_passed}/{run.test_cases_total} cases passed
                  </span>
                  {run.duration_ms != null && <span>{(run.duration_ms / 1000).toFixed(1)}s</span>}
                  {run.created_at && (
                    <span>{new Date(run.created_at).toLocaleString()}</span>
                  )}
                  {run.app_reachable != null && (
                    <span className={run.app_reachable ? 'text-emerald-600' : 'text-red-600'}>
                      Reachable: {run.app_reachable ? 'yes' : 'no'}
                    </span>
                  )}
                  {run.login_successful != null && (
                    <span className={run.login_successful ? 'text-emerald-600' : 'text-amber-700'}>
                      Login: {run.login_successful ? 'ok' : 'failed'}
                    </span>
                  )}
                </div>
                {run.error && (
                  <p className="rounded-lg bg-red-50 px-2 py-1.5 text-xs text-red-800">{run.error}</p>
                )}
              </div>
              <div className="flex flex-shrink-0 flex-wrap gap-2 sm:flex-col sm:items-stretch">
                {openHref ? (
                  <a
                    href={openHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-primary-200 bg-primary-50 px-3 py-2 text-xs font-semibold text-primary-800 transition-colors hover:bg-primary-100"
                  >
                    <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                    Open app
                  </a>
                ) : (
                  <span className="text-xs text-gray-400">Invalid app URL</span>
                )}
                <button
                  type="button"
                  onClick={() => copyUrl(run.app_url)}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  <ClipboardDocumentIcon className="h-4 w-4" />
                  Copy URL
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onReuseUrl(run.app_url)
                    toast.success('URL loaded on New Run')
                  }}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  <ArrowPathIcon className="h-4 w-4" />
                  Use for new run
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function IntegrityCheck() {
  const { projectId } = useParams<{ projectId: string }>()
  const pid = Number(projectId)
  const { currentProject, fetchProject } = useProjectStore()
  const [activeTab, setActiveTab] = useState<Tab>('run')
  const [appUrl, setAppUrl] = useState('')
  const [loginUrl, setLoginUrl] = useState('')
  const [loginMode, setLoginMode] = useState<IntegrityLoginMode>('app_form')
  const [browserEngine, setBrowserEngine] = useState<'playwright' | 'steel'>('steel')
  const urlSeedRef = useRef<number | null>(null)

  const { isRunning, result, error, runCheck } = useIntegrityCheck()
  const auth = useAuthSession(pid)

  useEffect(() => { if (projectId) fetchProject(projectId) }, [projectId])

  useEffect(() => {
    urlSeedRef.current = null
  }, [projectId])

  useEffect(() => {
    if (!projectId || !currentProject) return
    const id = Number(projectId)
    if (currentProject.id !== id) return
    if (urlSeedRef.current === id) return
    urlSeedRef.current = id
    if (currentProject.app_url) setAppUrl(currentProject.app_url)
  }, [projectId, currentProject])

  const handleRun = async () => {
    if (!appUrl) { toast.error('Enter an application URL'); return }
    if (auth.authMethod === 'credentials') {
      if (!auth.username?.trim() || !auth.password) {
        toast.error('Enter email and password, or choose Skip login')
        return
      }
    }
    await runCheck({
      projectId: pid,
      appUrl,
      username: auth.username,
      password: auth.password,
      loginUrl: loginUrl.trim() || undefined,
      loginMode,
      browserEngine,
    })
  }

  const filmstripItems = result ? buildScreenshotFilmstripItems(result) : []

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Build Integrity Check</h1>
        <p className="text-gray-500 text-sm">Verify your application is ready for automated testing</p>
        <p className="mt-2 max-w-3xl text-xs text-gray-500">
          Use the Application URL for each run. With <strong className="font-medium text-gray-700">Steel</strong> and{' '}
          <code className="rounded bg-gray-100 px-1">STEEL_SOLVE_CAPTCHA=true</code>, the backend may continue past
          common CAPTCHA patterns so automated login can proceed (per your Steel plan).
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1 w-fit">
        {(['run', 'history'] as Tab[]).map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-all ${
              activeTab === t ? 'bg-white text-primary-700 shadow-sm' : 'text-gray-600 hover:text-gray-800'
            }`}>
            {t === 'history' ? 'Run History' : 'New Run'}
          </button>
        ))}
      </div>

      {activeTab === 'history' ? (
        <Card>
          <div className="mb-4 flex items-center gap-2">
            <ArchiveBoxIcon className="h-5 w-5 text-primary-600" />
            <CardTitle>Run history</CardTitle>
          </div>
          <HistoryTab
            projectId={pid}
            onReuseUrl={url => {
              setAppUrl(url)
              setActiveTab('run')
            }}
          />
        </Card>
      ) : (
        <>
          {/* Configuration */}
          <Card>
            <CardTitle>Configuration</CardTitle>
            <div className="mt-4 space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="min-w-0 flex-1">
                  <Input label="Application URL" value={appUrl} onChange={e => setAppUrl(e.target.value)} placeholder="https://app.example.com" />
                </div>
                <button
                  type="button"
                  onClick={() => currentProject?.app_url && setAppUrl(currentProject.app_url)}
                  disabled={!currentProject?.app_url}
                  className="mb-0.5 shrink-0 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reset to project URL
                </button>
              </div>

              <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-white to-slate-50/90 p-4 shadow-sm">
                <label className="mb-1 block text-sm font-semibold text-gray-800">Login type</label>
                <p className="mb-3 text-xs text-gray-500">
                  Same email and password in Authentication below — either typed into your app’s form, or into Google’s
                  sign-in after QAstra clicks “Sign in with Google” on your site.
                </p>
                <div className="flex flex-wrap gap-2">
                  {LOGIN_MODE_OPTIONS.map(({ value, label, hint, Icon }) => {
                    const selected = loginMode === value
                    return (
                      <button
                        key={value}
                        type="button"
                        title={hint}
                        onClick={() => setLoginMode(value)}
                        className={`flex min-w-[10rem] flex-1 flex-col items-start gap-1 rounded-xl border-2 px-3 py-2.5 text-left shadow-sm transition-all sm:min-w-0 sm:flex-initial ${
                          selected
                            ? 'border-primary-500 bg-primary-50 text-primary-900 ring-1 ring-primary-200'
                            : 'border-gray-200 bg-white text-gray-800 hover:border-primary-300 hover:bg-gray-50'
                        }`}
                      >
                        <span className="flex items-center gap-2 text-sm font-semibold">
                          <Icon className={`h-4 w-4 ${selected ? 'text-primary-600' : 'text-gray-500'}`} />
                          {label}
                        </span>
                        <span className="text-[11px] leading-snug text-gray-500">{hint}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
                <p className="text-sm font-semibold text-indigo-900">Seeing the browser</p>
                <p className="mt-1 text-xs text-indigo-900/85">
                  The backend runs Playwright with a visible session (<code className="rounded bg-white/80 px-1">headless=false</code>
                  ). <strong className="font-medium">Playwright (local)</strong> shows Chromium on the machine that runs the API.
                  <strong className="font-medium"> Steel</strong> runs Chromium remotely; use your{' '}
                  <a
                    href="https://steel.dev"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium underline decoration-indigo-400 hover:decoration-indigo-600"
                  >
                    Steel dashboard
                  </a>{' '}
                  for live session view when your plan includes it. Screenshots in this UI always reflect the run.
                </p>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">Browser engine</label>
                <p className="mb-2 text-xs text-gray-500">
                  Steel uses Playwright <code className="rounded bg-gray-100 px-1">connect_over_cdp</code> with optional CAPTCHA
                  solving. Playwright (local) uses bundled Chromium on the server. Set{' '}
                  <code className="rounded bg-gray-100 px-1">STEEL_USE_WITH_PLAYWRIGHT=false</code> if you want local Chromium when
                  this option is selected.
                </p>
                <div className="flex flex-wrap gap-2">
                  {(['steel', 'playwright'] as const).map(eng => (
                    <button key={eng} type="button" onClick={() => setBrowserEngine(eng)}
                      className={`flex items-center gap-2 rounded-lg border-2 px-4 py-2 text-sm font-medium transition-all ${
                        browserEngine === eng ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-primary-300'
                      }`}>
                      <span>{eng === 'playwright' ? '🎭' : '⚡'}</span>
                      <span className="capitalize">{eng === 'steel' ? 'Steel (cloud)' : 'Playwright (local)'}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Auth */}
          <Card>
            <CardTitle>Authentication</CardTitle>
            <div className="mt-4">
              <AuthSessionPanel
                authMethod={auth.authMethod}
                onAuthMethodChange={auth.setAuthMethod}
                username={auth.username}
                onUsernameChange={auth.setUsername}
                password={auth.password}
                onPasswordChange={auth.setPassword}
                loginUrl={loginUrl}
                onLoginUrlChange={setLoginUrl}
                savedSession={auth.savedSession}
                isSaving={auth.isSaving}
                appUrl={appUrl}
                onSave={auth.saveSession}
                onClear={auth.clearSession}
              />
            </div>
          </Card>

          {/* Execution Preview */}
          <PreviewSection projectId={pid} />

          {/* Run button */}
          <Button onClick={handleRun} isLoading={isRunning} disabled={!appUrl} className="w-full sm:w-auto">
            <PlayIcon className="mr-2 h-4 w-4" />
            {isRunning ? 'Running Integrity Check…' : 'Run Integrity Check'}
          </Button>

          {/* Live commentary when running */}
          {isRunning && (
            <Card>
              <div className="flex items-center gap-3 mb-4">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
                <CardTitle>Live Execution</CardTitle>
              </div>
              <StepTimeline testCaseResults={[]} isRunning />
            </Card>
          )}

          {/* Error */}
          {error && !isRunning && (
            <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
              <XCircleIcon className="h-5 w-5 flex-shrink-0 text-red-600" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Results */}
          {result && !isRunning && (
            <Card>
              <RunSummaryBanner result={result} />

              {result.test_case_results.length > 0 && (
                <div className="mt-6 space-y-2">
                  <CardTitle>Step-by-step Results</CardTitle>
                  <div className="mt-3">
                    <StepTimeline testCaseResults={result.test_case_results} isRunning={false} />
                  </div>
                </div>
              )}

              {filmstripItems.length > 0 && (
                <div className="mt-6 space-y-2">
                  <CardTitle>Run screenshots</CardTitle>
                  <p className="text-xs text-gray-500">Chronological captures including navigation, login, and each test step.</p>
                  <div className="mt-3">
                    <ScreenshotFilmstrip screenshots={filmstripItems} />
                  </div>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  )
}
