/// <reference types="vite/client" />
/**
 * Resolve the HTTP origin for static assets (e.g. /screenshots) served by the API server.
 * VITE_API_URL is often http://host:port/api/v1 — strip the path to get the origin.
 */
export function getBackendOrigin(): string {
  const explicit = import.meta.env.VITE_BACKEND_ORIGIN as string | undefined
  if (explicit?.trim()) {
    return explicit.replace(/\/$/, '')
  }
  const base = import.meta.env.VITE_API_URL || ''
  if (!base || base.startsWith('/')) {
    return typeof window !== 'undefined' ? window.location.origin : ''
  }
  try {
    const u = new URL(base)
    return `${u.protocol}//${u.host}`
  } catch {
    return typeof window !== 'undefined' ? window.location.origin : ''
  }
}

/**
 * Turn a relative screenshot path (/screenshots/...) into a URL that loads in the browser.
 * When VITE_API_URL is relative (e.g. /api/v1), Vite proxies /screenshots → backend — use same-origin path.
 * When VITE_API_URL is absolute, point at that host.
 */
export function resolveScreenshotUrl(path: string): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  const apiBase = import.meta.env.VITE_API_URL || ''
  if (apiBase.startsWith('/')) {
    return normalized
  }
  const origin = getBackendOrigin()
  if (!origin) return normalized
  return `${origin}${normalized}`
}
