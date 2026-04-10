/** Persist which gap-analysis suggestion indices were accepted (per run), so UI survives navigation. */

const STORAGE_KEY = 'qastra_gap_analysis_accepted'

type AcceptedMap = Record<string, number[]>

function readMap(): AcceptedMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    return parsed as AcceptedMap
  } catch {
    return {}
  }
}

function writeMap(map: AcceptedMap) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
  } catch {
    /* quota / private mode */
  }
}

export function getAcceptedIndicesForRun(runId: number): Set<number> {
  const map = readMap()
  const arr = map[String(runId)]
  return new Set(Array.isArray(arr) ? arr : [])
}

export function recordAcceptedSuggestion(runId: number, index: number) {
  const map = readMap()
  const key = String(runId)
  const next = new Set(map[key] ?? [])
  next.add(index)
  map[key] = [...next].sort((a, b) => a - b)
  writeMap(map)
}
