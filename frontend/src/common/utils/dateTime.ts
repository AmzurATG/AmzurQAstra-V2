/**
 * Format an ISO timestamp for display in India Standard Time (Asia/Kolkata),
 * 24-hour clock (no AM/PM).
 */
export function formatDateTimeIST(iso: string | null | undefined): string {
  if (!iso) return '—'
  const opts: Intl.DateTimeFormatOptions = {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }
  try {
    return new Intl.DateTimeFormat('en-IN', opts).format(new Date(iso))
  } catch {
    return new Date(iso).toLocaleString('en-IN', opts)
  }
}
