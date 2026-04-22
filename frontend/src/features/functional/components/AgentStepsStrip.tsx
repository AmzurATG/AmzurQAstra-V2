import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  PhotoIcon,
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import type { AgentLogEntry } from '../types'
import { fetchScreenshotBlobUrl } from '../utils/screenshotFetch'

function screenshotBasename(path: string): string {
  const i = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'))
  return i >= 0 ? path.slice(i + 1) : path
}

/** Stable blob-cache key: unique per saved file; falls back to step+index when path missing. */
function blobCacheKey(entry: AgentLogEntry, listIndex: number): string {
  const raw = entry.screenshot_path
  if (raw) {
    const base = screenshotBasename(raw)
    if (base) return base
  }
  return `pending-${entry.agent_step}-${listIndex}`
}

function LazyAgentThumb({
  runId,
  testResultId,
  entry,
  index,
  cacheKey,
  onLoaded,
  onOpen,
  blobUrl,
  registerThumb,
}: {
  runId: number
  testResultId: number
  entry: AgentLogEntry
  index: number
  cacheKey: string
  onLoaded: (cacheKey: string, url: string) => void
  onOpen: (entry: AgentLogEntry, index: number) => void
  blobUrl: string | undefined
  registerThumb: (index: number, el: HTMLButtonElement | null) => void
}) {
  const ref = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (blobUrl) return
    const el = ref.current
    if (!el) return
    const raw = entry.screenshot_path
    if (!raw) return
    const filename = screenshotBasename(raw)
    if (!filename) return

    let cancelled = false
    const ob = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting || cancelled) return
        ob.disconnect()
        ;(async () => {
          try {
            const u = await fetchScreenshotBlobUrl(runId, testResultId, filename)
            if (cancelled) {
              URL.revokeObjectURL(u)
              return
            }
            onLoaded(cacheKey, u)
          } catch {
            /* ignore */
          }
        })()
      },
      { root: null, rootMargin: '120px', threshold: 0.01 }
    )
    ob.observe(el)
    return () => {
      cancelled = true
      ob.disconnect()
    }
  }, [runId, testResultId, cacheKey, entry.screenshot_path, blobUrl, onLoaded])

  const setButtonRef = useCallback(
    (el: HTMLButtonElement | null) => {
      ref.current = el
      registerThumb(index, el)
    },
    [index, registerThumb]
  )

  return (
    <button
      ref={setButtonRef}
      type="button"
      onClick={() => onOpen(entry, index)}
      className="shrink-0 w-24 rounded-lg border border-gray-200 overflow-hidden bg-gray-50 hover:ring-2 hover:ring-primary-400 transition-shadow text-left"
    >
      <div className="aspect-video bg-gray-200 flex items-center justify-center">
        {blobUrl ? (
          <img src={blobUrl} alt="" className="w-full h-full object-cover object-top" />
        ) : (
          <span className="text-[9px] text-gray-400 px-1">…</span>
        )}
      </div>
      <div
        className="px-1 py-0.5 text-[9px] text-gray-600 truncate"
        title={entry.description}
      >
        #{entry.agent_step}
      </div>
    </button>
  )
}

interface AgentStepsStripProps {
  runId: number
  testResultId: number
  agentLogs?: AgentLogEntry[] | null
  /** First / summary screenshot from test_result.screenshot_path (JWT-backed fetch). */
  primaryScreenshotPath?: string | null
  /** When false, render nothing (row collapsed). */
  enabled?: boolean
}

export const AgentStepsStrip: React.FC<AgentStepsStripProps> = ({
  runId,
  testResultId,
  agentLogs,
  primaryScreenshotPath,
  enabled = true,
}) => {
  const logs = agentLogs ?? []
  const withShots = useMemo(
    () => logs.filter((l) => l.screenshot_path),
    [logs]
  )
  const [blobByKey, setBlobByKey] = useState<Record<string, string>>({})
  const [primaryBlobUrl, setPrimaryBlobUrl] = useState<string | null>(null)
  /** Index into `withShots` when viewing agent step gallery; null = closed */
  const [galleryIndex, setGalleryIndex] = useState<number | null>(null)
  const [primaryLightbox, setPrimaryLightbox] = useState(false)
  const [lightboxLoading, setLightboxLoading] = useState(false)
  const blobsRef = useRef<Record<string, string>>({})
  const stripScrollRef = useRef<HTMLDivElement>(null)
  const thumbRefs = useRef<Map<number, HTMLButtonElement>>(new Map())

  useEffect(() => {
    blobsRef.current = blobByKey
  }, [blobByKey])

  const registerThumb = useCallback((index: number, el: HTMLButtonElement | null) => {
    if (el) thumbRefs.current.set(index, el)
    else thumbRefs.current.delete(index)
  }, [])

  const primaryName = primaryScreenshotPath ? screenshotBasename(primaryScreenshotPath) : ''

  const onThumbLoaded = useCallback((cacheKey: string, url: string) => {
    setBlobByKey((prev) => (prev[cacheKey] ? prev : { ...prev, [cacheKey]: url }))
  }, [])

  const loadBlobForEntry = useCallback(
    async (entry: AgentLogEntry, listIndex: number): Promise<void> => {
      const k = blobCacheKey(entry, listIndex)
      if (blobsRef.current[k]) return
      const fn = entry.screenshot_path ? screenshotBasename(entry.screenshot_path) : ''
      if (!fn) return
      setLightboxLoading(true)
      try {
        const u = await fetchScreenshotBlobUrl(runId, testResultId, fn)
        setBlobByKey((prev) => {
          if (prev[k]) {
            URL.revokeObjectURL(u)
            return prev
          }
          return { ...prev, [k]: u }
        })
      } catch {
        /* ignore */
      } finally {
        setLightboxLoading(false)
      }
    },
    [runId, testResultId]
  )

  const openGalleryAtIndex = useCallback(
    (index: number) => {
      if (index < 0 || index >= withShots.length) return
      setGalleryIndex(index)
    },
    [withShots.length]
  )

  const onThumbOpen = useCallback(
    (_entry: AgentLogEntry, index: number) => {
      openGalleryAtIndex(index)
    },
    [openGalleryAtIndex]
  )

  useEffect(() => {
    if (galleryIndex === null) return
    const entry = withShots[galleryIndex]
    if (!entry) return
    let cancelled = false
    ;(async () => {
      await loadBlobForEntry(entry, galleryIndex)
      if (cancelled) return
      requestAnimationFrame(() => {
        thumbRefs.current.get(galleryIndex)?.scrollIntoView({
          inline: 'nearest',
          behavior: 'smooth',
          block: 'nearest',
        })
      })
    })()
    return () => {
      cancelled = true
    }
  }, [galleryIndex, withShots, loadBlobForEntry])

  useEffect(() => {
    if (galleryIndex === null) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        setGalleryIndex(null)
        return
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setGalleryIndex((i) => (i !== null && i > 0 ? i - 1 : i))
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        setGalleryIndex((i) =>
          i !== null && i < withShots.length - 1 ? i + 1 : i
        )
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [galleryIndex, withShots.length])

  const scrollStrip = (delta: number) => {
    stripScrollRef.current?.scrollBy({ left: delta, behavior: 'smooth' })
  }

  useEffect(() => {
    if (!enabled || !primaryName) {
      setPrimaryBlobUrl(null)
      return
    }
    let cancelled = false
    let url: string | null = null
    ;(async () => {
      try {
        const u = await fetchScreenshotBlobUrl(runId, testResultId, primaryName)
        if (cancelled) {
          URL.revokeObjectURL(u)
          return
        }
        url = u
        setPrimaryBlobUrl(u)
      } catch {
        if (!cancelled) setPrimaryBlobUrl(null)
      }
    })()
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [enabled, runId, testResultId, primaryName])

  if (!enabled) {
    return null
  }

  if (!primaryName && logs.length === 0) {
    return (
      <p className="text-xs text-gray-400 italic py-1">No agent step log for this run.</p>
    )
  }

  const galleryEntry = galleryIndex !== null ? withShots[galleryIndex] : null
  const galleryBlobKey =
    galleryEntry && galleryIndex !== null ? blobCacheKey(galleryEntry, galleryIndex) : ''
  const galleryHasPrev = galleryIndex !== null && galleryIndex > 0
  const galleryHasNext = galleryIndex !== null && galleryIndex < withShots.length - 1

  return (
    <div className="mt-3 border-t border-gray-100 pt-3 space-y-3 w-full min-w-0 max-w-full">
      {primaryName && (
        <div className="min-w-0">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <PhotoIcon className="w-3.5 h-3.5" /> Run snapshot
          </p>
          <button
            type="button"
            onClick={() => setPrimaryLightbox(true)}
            className="max-w-md rounded-lg border border-gray-200 overflow-hidden bg-gray-50 hover:ring-2 hover:ring-primary-400 transition-shadow text-left"
          >
            <div className="aspect-video bg-gray-200 flex items-center justify-center min-h-[120px]">
              {primaryBlobUrl ? (
                <img src={primaryBlobUrl} alt="" className="w-full h-full object-cover object-top" />
              ) : (
                <span className="text-[10px] text-gray-400 px-2">Loading snapshot…</span>
              )}
            </div>
          </button>
        </div>
      )}

      {logs.length > 0 && withShots.length === 0 && (
        <p className="text-xs text-gray-400 italic py-1">
          {logs.length} agent step(s); no screenshots captured.
        </p>
      )}

      {withShots.length > 0 && (
        <div className="min-w-0 max-w-full">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <PhotoIcon className="w-3.5 h-3.5" /> Agent steps (screenshots load as you scroll)
          </p>
          <div className="flex items-center gap-1 min-w-0 max-w-full">
            <button
              type="button"
              className="shrink-0 rounded-lg border border-gray-200 bg-white p-1.5 text-gray-600 shadow-sm hover:bg-gray-50 disabled:opacity-40"
              aria-label="Scroll screenshots left"
              onClick={() => scrollStrip(-280)}
            >
              <ChevronLeftIcon className="w-5 h-5" />
            </button>
            <div
              ref={stripScrollRef}
              className="min-w-0 flex-1 overflow-x-auto overflow-y-hidden overscroll-x-contain pb-1 [scrollbar-width:thin]"
            >
              <div className="flex w-max min-w-0 gap-2 pr-1">
                {withShots.map((entry, index) => {
                  const ck = blobCacheKey(entry, index)
                  return (
                    <LazyAgentThumb
                      key={ck}
                      runId={runId}
                      testResultId={testResultId}
                      entry={entry}
                      index={index}
                      cacheKey={ck}
                      blobUrl={blobByKey[ck]}
                      onLoaded={onThumbLoaded}
                      onOpen={onThumbOpen}
                      registerThumb={registerThumb}
                    />
                  )
                })}
              </div>
            </div>
            <button
              type="button"
              className="shrink-0 rounded-lg border border-gray-200 bg-white p-1.5 text-gray-600 shadow-sm hover:bg-gray-50 disabled:opacity-40"
              aria-label="Scroll screenshots right"
              onClick={() => scrollStrip(280)}
            >
              <ChevronRightIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {primaryLightbox && primaryBlobUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal
        >
          <button
            type="button"
            className="absolute top-4 right-4 text-white p-2 rounded-full hover:bg-white/10"
            onClick={() => setPrimaryLightbox(false)}
            aria-label="Close"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
          <div className="max-w-4xl max-h-[90vh] flex flex-col gap-2 bg-white rounded-lg overflow-hidden shadow-xl">
            <img
              src={primaryBlobUrl}
              alt=""
              className="max-h-[70vh] w-full object-contain bg-gray-900"
            />
            <div className="p-4 text-sm">
              <p className="font-semibold text-gray-900">Run snapshot</p>
              <p className="text-gray-600 mt-1 text-xs">Primary screenshot for this test result.</p>
            </div>
          </div>
        </div>
      )}

      {galleryEntry && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal
          aria-labelledby="agent-gallery-title"
        >
          <button
            type="button"
            className="absolute top-4 right-4 text-white p-2 rounded-full hover:bg-white/10 z-[60]"
            onClick={() => setGalleryIndex(null)}
            aria-label="Close"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
          {galleryHasPrev && (
            <button
              type="button"
              className="absolute left-2 md:left-4 top-1/2 -translate-y-1/2 z-[60] rounded-full bg-white/90 p-2 text-gray-800 shadow-lg hover:bg-white"
              aria-label="Previous screenshot"
              onClick={() => setGalleryIndex((i) => (i !== null && i > 0 ? i - 1 : i))}
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
                  i !== null && i < withShots.length - 1 ? i + 1 : i
                )
              }
            >
              <ChevronRightIcon className="w-8 h-8" />
            </button>
          )}
          <div className="max-w-4xl max-h-[90vh] w-full flex flex-col gap-2 bg-white rounded-lg overflow-hidden shadow-xl relative">
            {lightboxLoading && galleryEntry && !blobByKey[galleryBlobKey] ? (
              <div className="p-16 text-gray-500 text-sm">Loading image…</div>
            ) : galleryEntry && blobByKey[galleryBlobKey] ? (
              <img
                src={blobByKey[galleryBlobKey]}
                alt=""
                className="max-h-[70vh] w-full object-contain bg-gray-900"
              />
            ) : (
              <div className="p-16 text-gray-500 text-sm">Could not load image.</div>
            )}
            <div className="p-4 text-sm border-t border-gray-100">
              <p id="agent-gallery-title" className="font-semibold text-gray-900">
                Agent step {galleryEntry.agent_step}
                <span className="text-gray-500 font-normal text-xs ml-2">
                  {galleryIndex !== null ? `${galleryIndex + 1} / ${withShots.length}` : ''}
                </span>
              </p>
              <p className="text-gray-600 mt-1">{galleryEntry.description}</p>
              {galleryEntry.adaptation && (
                <p className="text-xs text-purple-700 mt-2">{galleryEntry.adaptation}</p>
              )}
              <p className="text-[10px] text-gray-400 mt-3">
                Use the side arrows or ← → keys for the next or previous screenshot. Esc to close.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
