import { XCircleIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { Card } from '@common/components/ui/Card'
import type { RunStatusResponse } from '../types'
import { IntegrityCheckScreenshotGallery } from '../components/IntegrityCheckScreenshotGallery'

interface Props {
  result: RunStatusResponse
}

function fmt(ms?: number) {
  if (!ms) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export default function IntegrityCheckResults({ result }: Props) {
  const passed = result.overall_status === 'passed'
  const hasError = result.overall_status === 'error' || result.status === 'error'

  return (
    <Card>
      <div className="flex items-start gap-4">
        <div
          className={`p-3 rounded-full shrink-0 ${passed ? 'bg-green-100' : hasError ? 'bg-yellow-100' : 'bg-red-100'}`}
        >
          {passed ? (
            <ShieldCheckIcon className="w-8 h-8 text-green-600" />
          ) : (
            <XCircleIcon className={`w-8 h-8 ${hasError ? 'text-yellow-600' : 'text-red-600'}`} />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-4">
          <div>
            <h3 className="text-xl font-bold text-gray-900">
              {passed ? 'All Checks Passed' : hasError ? 'Check Encountered an Error' : 'Some Checks Failed'}
            </h3>
            <p className="text-gray-500 text-sm mt-0.5">Completed in {fmt(result.duration_ms)}</p>
          </div>

          {result.summary && (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">Summary</p>
              <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">{result.summary}</p>
            </div>
          )}

          {result.error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-xs font-semibold text-red-700 mb-1">What went wrong</p>
              <p className="text-sm text-red-800">{result.error}</p>
            </div>
          )}

          {result.screenshots.length > 0 && (
            <IntegrityCheckScreenshotGallery
              screenshots={result.screenshots}
              heading={`Screens from this run (${result.screenshots.length})`}
              hint="Click a thumbnail for the gallery. Use ← → or the side arrows; Esc to close."
              variant="comfortable"
            />
          )}

          {result.screenshots.length === 0 && !result.error && (
            <p className="text-sm text-gray-500">No screen captures were saved for this run.</p>
          )}
        </div>
      </div>
    </Card>
  )
}
