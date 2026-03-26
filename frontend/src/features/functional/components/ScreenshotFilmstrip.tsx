import { useState } from 'react'
import { XMarkIcon, MagnifyingGlassPlusIcon } from '@heroicons/react/24/outline'

interface Screenshot {
  url: string
  label: string
}

interface Props {
  screenshots: Screenshot[]
}

export function ScreenshotFilmstrip({ screenshots }: Props) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)

  if (screenshots.length === 0) return null

  return (
    <>
      {/* Filmstrip */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {screenshots.map((s, i) => (
          <button
            key={i}
            onClick={() => setLightboxUrl(s.url)}
            className="group relative flex-shrink-0 overflow-hidden rounded-lg border border-gray-200 bg-gray-100 transition-all hover:border-primary-400 hover:shadow-md"
            style={{ width: 140, height: 88 }}
            title={s.label}
          >
            <img
              src={s.url}
              alt={s.label}
              className="h-full w-full object-cover"
              onError={(e) => {
                ;(e.target as HTMLImageElement).src =
                  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='88'%3E%3Crect fill='%23f3f4f6' width='140' height='88'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%239ca3af' font-size='11'%3ENo image%3C/text%3E%3C/svg%3E"
              }}
            />
            {/* Step number badge */}
            <span className="absolute left-1 top-1 rounded bg-black/60 px-1 py-0.5 text-xs font-mono text-white">
              {s.label}
            </span>
            {/* Zoom overlay */}
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
              <MagnifyingGlassPlusIcon className="h-6 w-6 text-white" />
            </div>
          </button>
        ))}
      </div>

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setLightboxUrl(null)}
        >
          <div className="relative max-h-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setLightboxUrl(null)}
              className="absolute -right-3 -top-3 z-10 rounded-full bg-white p-1 shadow-lg hover:bg-gray-100"
            >
              <XMarkIcon className="h-5 w-5 text-gray-700" />
            </button>
            <img
              src={lightboxUrl}
              alt="Screenshot"
              className="max-h-[85vh] max-w-full rounded-lg shadow-2xl"
            />
          </div>
        </div>
      )}
    </>
  )
}
