const MAX_DEPTH = 6
const MAX_LIST = 40
const MAX_DICT_ITEMS = 50

function flattenNested(value: unknown, depth: number): string {
  if (depth > MAX_DEPTH) return '…'
  if (value == null) return ''
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    const parts = value.slice(0, MAX_LIST).map((x) => flattenNested(x, depth + 1))
    if (value.length > MAX_LIST) parts.push('…')
    return parts.join('; ')
  }
  if (typeof value === 'object') {
    const o = value as Record<string, unknown>
    const parts: string[] = []
    let i = 0
    for (const [k, v] of Object.entries(o)) {
      if (i >= MAX_DICT_ITEMS) {
        parts.push('…')
        break
      }
      parts.push(`${k}: ${flattenNested(v, depth + 1)}`)
      i += 1
    }
    return parts.join('; ')
  }
  return String(value)
}

/**
 * Renders step fields when the API may return legacy JSON strings or nested objects.
 */
export function formatStepDisplayValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') {
    const s = value.trim()
    if (s.length >= 2 && '{['.includes(s[0]!) && '}]'.includes(s[s.length - 1]!)) {
      try {
        const parsed: unknown = JSON.parse(s)
        return formatStepDisplayValue(parsed)
      } catch {
        // keep original string
      }
    }
    return value.trim() || ''
  }
  return flattenNested(value, 0)
}
