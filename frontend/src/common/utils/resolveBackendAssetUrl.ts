/**
 * Backend serves screenshots at /screenshots/... (FastAPI StaticFiles).
 * The SPA often runs on another origin (e.g. :5173) while API is :8000 — relative /screenshots
 * would hit the dev server and 404. Resolve to the API origin when VITE_API_URL is absolute.
 */
export function resolveBackendAssetUrl(path: string | undefined | null): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const normalized = path.startsWith('/') ? path : `/${path}`

  const apiBase = import.meta.env.VITE_API_URL || '/api/v1'
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    try {
      const origin = new URL(apiBase).origin
      return `${origin}${normalized}`
    } catch {
      /* fall through */
    }
  }

  // Relative API (e.g. /api/v1) — same origin; dev server must proxy /screenshots (see vite.config)
  if (typeof window !== 'undefined') {
    return `${window.location.origin}${normalized}`
  }
  return normalized
}
