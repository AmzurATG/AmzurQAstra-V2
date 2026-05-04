import type { AnalyticsWindow } from '../../types'

const WINDOWS: { id: AnalyticsWindow; label: string }[] = [
  { id: '7d', label: '7 days' },
  { id: '30d', label: '30 days' },
  { id: '90d', label: '90 days' },
]

type SourceTab = { id: string; label: string; disabled?: boolean; hint?: string }

const SOURCES: SourceTab[] = [
  { id: 'functional', label: 'Functional' },
  { id: 'integrity', label: 'Integrity Check', disabled: true, hint: 'Coming soon' },
  { id: 'performance', label: 'Performance', disabled: true, hint: 'Coming soon' },
  { id: 'security', label: 'Security', disabled: true, hint: 'Coming soon' },
]

type Props = {
  window: AnalyticsWindow
  onWindowChange: (w: AnalyticsWindow) => void
  activeSource: string
}

export function AnalyticsHeader({ window, onWindowChange, activeSource }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Test report analytics</h1>
          <p className="text-sm text-gray-600 max-w-2xl">
            Pass rate, stability, and failure focus for this project. Switch time window to compare
            trends. Other test types will appear here as they are enabled.
          </p>
        </div>
        <div className="flex flex-wrap gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.id}
              type="button"
              onClick={() => onWindowChange(w.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                window === w.id
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
        {SOURCES.map((s) => (
          <div key={s.id} className="relative group">
            <button
              type="button"
              disabled={Boolean(s.disabled)}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                activeSource === s.id && !s.disabled
                  ? 'bg-primary-100 text-primary-800'
                  : s.disabled
                    ? 'cursor-not-allowed text-gray-400 bg-gray-50'
                    : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {s.label}
              {s.disabled && s.hint ? (
                <span className="ml-1.5 text-[10px] font-normal text-gray-400">({s.hint})</span>
              ) : null}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
