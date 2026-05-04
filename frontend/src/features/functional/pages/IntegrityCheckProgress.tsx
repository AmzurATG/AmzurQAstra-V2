import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import type { RunStatus } from '../types'
import { IntegrityCheckScreenshotGallery } from '../components/IntegrityCheckScreenshotGallery'

interface Props {
  percentage: number
  currentStep: string
  status: RunStatus
  screenshots: string[]
}

/** Circular SVG progress ring */
function ProgressRing({ pct }: { pct: number }) {
  const r = 54
  const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ

  const color =
    pct === 100 ? '#16a34a' : pct >= 50 ? '#2563eb' : '#9333ea'

  return (
    <svg width={128} height={128} viewBox="0 0 128 128">
      <circle cx={64} cy={64} r={r} fill="none" stroke="#e5e7eb" strokeWidth={10} />
      <circle
        cx={64}
        cy={64}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={10}
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        transform="rotate(-90 64 64)"
        style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s ease' }}
      />
      <text
        x={64}
        y={64}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={22}
        fontWeight={700}
        fill={color}
      >
        {pct}%
      </text>
    </svg>
  )
}

export default function IntegrityCheckProgress({
  percentage,
  currentStep,
  status,
  screenshots,
}: Props) {
  const isFinished = status === 'completed' || status === 'error'

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center gap-3 py-4">
        <ProgressRing pct={percentage} />
        <p
          className={`text-sm font-medium text-center max-w-md px-2
          ${status === 'error' ? 'text-red-600' : 'text-gray-600'}`}
        >
          {isFinished
            ? status === 'error'
              ? 'An error occurred'
              : 'Check complete!'
            : currentStep || 'Starting…'}
        </p>
        {!isFinished && (
          <span className="flex flex-col items-center gap-1">
            <span className="flex items-center gap-1.5 text-xs text-blue-600 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
              Browser is running…
            </span>
            <span className="text-[10px] text-gray-400 text-center max-w-sm px-2">
              Progress follows login milestones and up to five saved screenshots; it reaches 99% while wrapping up, then 100% when the run completes.
            </span>
          </span>
        )}
      </div>

      {screenshots.length > 0 && (
        <IntegrityCheckScreenshotGallery
          screenshots={screenshots}
          heading={`Screens so far (${screenshots.length})`}
          hint="Click a thumbnail to view full size. Use arrow keys or on-screen arrows to browse."
          variant="compact"
        />
      )}

      {!isFinished && screenshots.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-4 text-gray-400 text-sm">
          <ExclamationCircleIcon className="w-8 h-8 opacity-30" />
          <p>Waiting for the browser…</p>
        </div>
      )}
    </div>
  )
}
