import { KeyIcon, CheckBadgeIcon, TrashIcon, LockClosedIcon, NoSymbolIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import type { AuthMethod, AuthSession } from '../types'

interface Props {
  authMethod: AuthMethod
  onAuthMethodChange: (m: AuthMethod) => void
  username: string
  onUsernameChange: (v: string) => void
  password: string
  onPasswordChange: (v: string) => void
  loginUrl?: string
  onLoginUrlChange?: (v: string) => void
  savedSession: AuthSession | null
  isSaving: boolean
  appUrl: string
  onSave: () => void
  onClear: () => void
}

const METHOD_PILLS: {
  id: AuthMethod
  label: string
  short: string
  Icon: typeof KeyIcon
}[] = [
  { id: 'none', label: 'No login', short: 'Skip', Icon: NoSymbolIcon },
  { id: 'credentials', label: 'Manual credentials', short: 'Manual', Icon: KeyIcon },
]

function AuthMethodPills({
  authMethod,
  onAuthMethodChange,
}: {
  authMethod: AuthMethod
  onAuthMethodChange: (m: AuthMethod) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {METHOD_PILLS.map(({ id, label, short, Icon }) => {
        const selected = authMethod === id
        return (
          <button
            key={id}
            type="button"
            onClick={() => onAuthMethodChange(id)}
            title={label}
            className={`inline-flex items-center gap-2 rounded-xl border-2 px-3.5 py-2 text-sm font-medium shadow-sm transition-all ${
              selected
                ? 'border-primary-500 bg-primary-50 text-primary-800 ring-1 ring-primary-200'
                : 'border-gray-200 bg-white text-gray-700 hover:border-primary-300 hover:bg-gray-50'
            }`}
          >
            <Icon className={`h-4 w-4 ${selected ? 'text-primary-600' : 'text-gray-500'}`} />
            <span>{short}</span>
          </button>
        )
      })}
    </div>
  )
}

export function AuthSessionPanel({
  authMethod,
  onAuthMethodChange,
  username,
  onUsernameChange,
  password,
  onPasswordChange,
  loginUrl = '',
  onLoginUrlChange,
  savedSession,
  isSaving,
  appUrl: _appUrl,
  onSave,
  onClear,
}: Props) {
  void _appUrl
  const legacyGoogle = savedSession?.auth_type === 'google_oauth'

  return (
    <div className="space-y-4">
      {legacyGoogle && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-amber-900">Legacy Google OAuth session stored</p>
            <p className="mt-1 text-xs text-amber-800/90">
              Integrity check now uses email and password only. Clear this session, then enter credentials below (or save them for future runs).
            </p>
            <button
              type="button"
              onClick={onClear}
              className="mt-2 text-xs font-semibold text-amber-900 underline hover:no-underline"
            >
              Clear saved session
            </button>
          </div>
        </div>
      )}

      {savedSession && !legacyGoogle && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <CheckBadgeIcon className="h-4 w-4 text-emerald-600" />
            <span className="text-sm font-medium text-emerald-800">Saved credentials active</span>
          </div>
          <button
            type="button"
            onClick={onClear}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
          >
            <TrashIcon className="h-3.5 w-3.5" />
            Clear
          </button>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-white to-gray-50/80 p-4 shadow-sm">
        <p className="mb-1 text-sm font-semibold text-gray-800">Account credentials</p>
        <p className="mb-3 text-xs text-gray-500">
          Use your app login email and password, or the Google account email and password when you choose Google sign-in on the app (see Login type above).
        </p>
        <AuthMethodPills authMethod={authMethod} onAuthMethodChange={onAuthMethodChange} />
      </div>

      {authMethod === 'credentials' && (
        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <KeyIcon className="h-4 w-4" />
            Email &amp; password
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input
              label="Username / Email"
              value={username}
              onChange={(e) => onUsernameChange(e.target.value)}
              placeholder="user@example.com"
              autoComplete="username"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>
          <div className="space-y-3">
            {onLoginUrlChange && (
              <Input
                label="Login page URL (optional)"
                value={loginUrl}
                onChange={(e) => onLoginUrlChange(e.target.value)}
                placeholder="Leave empty to use Application URL"
              />
            )}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex items-center gap-1 text-xs text-gray-500">
                <LockClosedIcon className="h-3 w-3 shrink-0" />
                Credentials are encrypted at rest using AES-256
              </p>
              <Button
                size="sm"
                variant="secondary"
                onClick={onSave}
                isLoading={isSaving}
                disabled={!username || !password}
                className="shrink-0"
              >
                Save for future runs
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
