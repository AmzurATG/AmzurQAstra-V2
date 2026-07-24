/** Format millisecond durations for live tables and reports. */
export function formatDurationMs(ms?: number | null): string {
  if (ms == null || Number.isNaN(ms)) return '—'
  const n = Math.max(0, Math.round(ms))
  if (n < 1000) return `${n}ms`
  const secs = n / 1000
  if (secs < 60) {
    if (Math.abs(secs - Math.round(secs)) < 0.05) return `${Math.round(secs)}s`
    return `${secs.toFixed(1)}s`
  }
  const totalS = Math.round(secs)
  const hours = Math.floor(totalS / 3600)
  const minutes = Math.floor((totalS % 3600) / 60)
  const seconds = totalS % 60
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m`
  if (seconds === 0) return `${minutes}m`
  return `${minutes}m ${String(seconds).padStart(2, '0')}s`
}
