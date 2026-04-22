import React, { useCallback, useEffect, useState } from 'react'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { IntegrityCheckScreenshot } from './IntegrityCheckScreenshot'
import { resolveBackendAssetUrl } from '@common/utils/resolveBackendAssetUrl'

export type IntegrityScreenshotGalleryVariant = 'compact' | 'comfortable'

interface IntegrityCheckScreenshotGalleryProps {
  screenshots: string[]
  /** Section title (e.g. "Screens so far (3)") */
  heading: string
  /** Optional line under the heading */
  hint?: string
  /** compact = progress-style small thumbs; comfortable = results-style larger grid */
  variant?: IntegrityScreenshotGalleryVariant
}

/**
 * Thumbnail grid + full-screen lightbox with chevrons and ← / → / Esc keyboard navigation
 * (aligned with AgentStepsStrip gallery behavior; uses public screenshot URLs).
 */
export function IntegrityCheckScreenshotGallery({
  screenshots,
  heading,
  hint,
  variant = 'compact',
}: IntegrityCheckScreenshotGalleryProps) {
  const [galleryIndex, setGalleryIndex] = useState<number | null>(null)
  const [lightboxFailed, setLightboxFailed] = useState(false)

  const close = useCallback(() => {
    setGalleryIndex(null)
    setLightboxFailed(false)
  }, [])

  useEffect(() => {
    setLightboxFailed(false)
  }, [galleryIndex])

  useEffect(() => {
    if (galleryIndex === null) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        close()
        return
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setGalleryIndex((i) => (i !== null && i > 0 ? i - 1 : i))
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        setGalleryIndex((i) =>
          i !== null && i < screenshots.length - 1 ? i + 1 : i
        )
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [galleryIndex, screenshots.length, close])

  if (screenshots.length === 0) return null

  const currentSrc = galleryIndex !== null ? screenshots[galleryIndex] : null
  const currentUrl = currentSrc ? resolveBackendAssetUrl(currentSrc) : ''

  const gridClass =
    variant === 'comfortable'
      ? 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3'
      : 'grid grid-cols-3 sm:grid-cols-4 gap-2'

  const thumbButtonClass =
    variant === 'comfortable'
      ? 'group block w-full rounded-lg overflow-hidden border border-gray-200 bg-gray-100 hover:shadow-md transition-shadow text-left'
      : 'block w-full rounded-lg overflow-hidden border border-gray-200 hover:shadow-md transition-shadow text-left'

  const thumbImgClass =
    variant === 'comfortable'
      ? 'w-full h-36 sm:h-40 object-cover object-top group-hover:scale-[1.02] transition-transform duration-300'
      : 'w-full h-20 object-cover object-top'

  const galleryHasPrev = galleryIndex !== null && galleryIndex > 0
  const galleryHasNext =
    galleryIndex !== null && galleryIndex < screenshots.length - 1

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        {heading}
      </h4>
      {hint ? (
        <p className="text-sm text-gray-500 mb-3">{hint}</p>
      ) : null}
      <div className={gridClass}>
        {screenshots.map((src, i) => (
          <button
            key={`${i}-${src}`}
            type="button"
            onClick={() => setGalleryIndex(i)}
            className={thumbButtonClass}
            aria-label={`View screenshot ${i + 1} of ${screenshots.length}`}
          >
            <IntegrityCheckScreenshot
              src={src}
              alt={`Screen ${i + 1}`}
              variant={variant === 'comfortable' ? 'gallery' : 'thumb'}
              className={thumbImgClass}
            />
          </button>
        ))}
      </div>

      {galleryIndex !== null && currentUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal
          aria-labelledby="integrity-gallery-title"
        >
          <button
            type="button"
            className="absolute top-4 right-4 text-white p-2 rounded-full hover:bg-white/10 z-[60]"
            onClick={close}
            aria-label="Close"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
          {galleryHasPrev && (
            <button
              type="button"
              className="absolute left-2 md:left-4 top-1/2 -translate-y-1/2 z-[60] rounded-full bg-white/90 p-2 text-gray-800 shadow-lg hover:bg-white"
              aria-label="Previous screenshot"
              onClick={() =>
                setGalleryIndex((i) => (i !== null && i > 0 ? i - 1 : i))
              }
            >
              <ChevronLeftIcon className="w-8 h-8" />
            </button>
          )}
          {galleryHasNext && (
            <button
              type="button"
              className="absolute right-2 md:right-4 top-1/2 -translate-y-1/2 z-[60] rounded-full bg-white/90 p-2 text-gray-800 shadow-lg hover:bg-white"
              aria-label="Next screenshot"
              onClick={() =>
                setGalleryIndex((i) =>
                  i !== null && i < screenshots.length - 1 ? i + 1 : i
                )
              }
            >
              <ChevronRightIcon className="w-8 h-8" />
            </button>
          )}
          <div className="max-w-4xl max-h-[90vh] w-full flex flex-col gap-2 bg-white rounded-lg overflow-hidden shadow-xl relative">
            {lightboxFailed ? (
              <div className="p-16 text-gray-500 text-sm text-center">
                Could not load image.
              </div>
            ) : (
              <img
                src={currentUrl}
                alt=""
                className="max-h-[70vh] w-full object-contain bg-gray-900"
                onError={() => setLightboxFailed(true)}
              />
            )}
            <div className="p-4 text-sm border-t border-gray-100">
              <p id="integrity-gallery-title" className="font-semibold text-gray-900">
                Screenshot{' '}
                <span className="text-gray-500 font-normal">
                  {galleryIndex + 1} / {screenshots.length}
                </span>
              </p>
              <p className="mt-2">
                <a
                  href={currentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 hover:underline"
                >
                  Open in new tab
                </a>
              </p>
              <p className="text-[10px] text-gray-400 mt-3">
                Use the side arrows or ← → keys for the next or previous
                screenshot. Esc to close.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
