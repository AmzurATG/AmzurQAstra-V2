/**
 * Backend hosts static files (e.g. /screenshots) at the app root, not under /api/v1.
 */
export function getBackendOrigin(): string {
  const base = import.meta.env.VITE_API_URL || '/api/v1'
  const trimmed = base.replace(/\/?api\/v1\/?$/, '')
  return trimmed || ''
}

/** Build absolute URL for a stored path like /screenshots/foo.png (unauthenticated static mount). */
export function getBackendAssetUrl(storedPath: string): string {
  if (!storedPath) return ''
  if (storedPath.startsWith('http')) return storedPath
  const origin = getBackendOrigin()
  return `${origin}${storedPath.startsWith('/') ? '' : '/'}${storedPath}`
}
