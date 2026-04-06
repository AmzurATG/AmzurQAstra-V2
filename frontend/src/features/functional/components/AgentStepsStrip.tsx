import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { PhotoIcon, XMarkIcon } from '@heroicons/react/24/outline'
import type { AgentLogEntry } from '../types'
import { fetchScreenshotBlobUrl } from '../utils/screenshotFetch'

function screenshotBasename(path: string): string {
  const i = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'))
  return i >= 0 ? path.slice(i + 1) : path
}

function LazyAgentThumb({
  runId,
  testResultId,
  entry,
  onLoaded,
  onOpen,
  blobUrl,
}: {
  runId: number
  testResultId: number
  entry: AgentLogEntry
  onLoaded: (step: number, url: string) => void
  onOpen: (entry: AgentLogEntry) => void
  blobUrl: string | undefined
}) {
  const ref = useRef<HTMLButtonElement>(null)

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
            created = u
            onLoaded(entry.agent_step, u)
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
  }, [runId, testResultId, entry.agent_step, entry.screenshot_path, blobUrl, onLoaded])

  return (
    <button
      ref={ref}
      type="button"
      onClick={() => onOpen(entry)}
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
  const [blobByStep, setBlobByStep] = useState<Record<number, string>>({})
  const [primaryBlobUrl, setPrimaryBlobUrl] = useState<string | null>(null)
  const [lightbox, setLightbox] = useState<AgentLogEntry | null>(null)
  const [primaryLightbox, setPrimaryLightbox] = useState(false)
  const [lightboxLoading, setLightboxLoading] = useState(false)
  const blobsRef = useRef<Record<number, string>>({})
  useEffect(() => {
    blobsRef.current = blobByStep
  }, [blobByStep])

  const primaryName = primaryScreenshotPath ? screenshotBasename(primaryScreenshotPath) : ''

  const onThumbLoaded = useCallback((step: number, url: string) => {
    setBlobByStep((prev) => (prev[step] ? prev : { ...prev, [step]: url }))
  }, [])

  const openAgentLightbox = useCallback(
    async (entry: AgentLogEntry) => {
      setLightbox(entry)
      const step = entry.agent_step
      if (blobsRef.current[step]) return
      const fn = entry.screenshot_path ? screenshotBasename(entry.screenshot_path) : ''
      if (!fn) return
      setLightboxLoading(true)
      try {
        const u = await fetchScreenshotBlobUrl(runId, testResultId, fn)
        setBlobByStep((prev) => {
          if (prev[entry.agent_step]) {
            URL.revokeObjectURL(u)
            return prev
          }
          return { ...prev, [entry.agent_step]: u }
        })
      } catch {
        /* ignore */
      } finally {
        setLightboxLoading(false)
      }
    },
    [runId, testResultId]
  )

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

  return (
    <div className="mt-3 border-t border-gray-100 pt-3 space-y-3">
      {primaryName && (
        <div>
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
        <div>
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <PhotoIcon className="w-3.5 h-3.5" /> Agent steps (screenshots load as you scroll)
          </p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {withShots.map((entry) => (
              <LazyAgentThumb
                key={`${entry.agent_step}-${entry.timestamp}`}
                runId={runId}
                testResultId={testResultId}
                entry={entry}
                blobUrl={blobByStep[entry.agent_step]}
                onLoaded={onThumbLoaded}
                onOpen={openAgentLightbox}
              />
            ))}
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

      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal
        >
          <button
            type="button"
            className="absolute top-4 right-4 text-white p-2 rounded-full hover:bg-white/10"
            onClick={() => setLightbox(null)}
            aria-label="Close"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
          <div className="max-w-4xl max-h-[90vh] flex flex-col gap-2 bg-white rounded-lg overflow-hidden shadow-xl">
            {lightboxLoading && !blobByStep[lightbox.agent_step] ? (
              <div className="p-16 text-gray-500 text-sm">Loading image…</div>
            ) : blobByStep[lightbox.agent_step] ? (
              <img
                src={blobByStep[lightbox.agent_step]}
                alt=""
                className="max-h-[70vh] w-full object-contain bg-gray-900"
              />
            ) : (
              <div className="p-16 text-gray-500 text-sm">Could not load image.</div>
            )}
            <div className="p-4 text-sm">
              <p className="font-semibold text-gray-900">Agent step {lightbox.agent_step}</p>
              <p className="text-gray-600 mt-1">{lightbox.description}</p>
              {lightbox.adaptation && (
                <p className="text-xs text-purple-700 mt-2">{lightbox.adaptation}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
