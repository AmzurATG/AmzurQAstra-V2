import type { AgentLogEntry } from '../types'

export interface AgentStepGroup {
  /** 1-based test/merged step number when parseable from the ▶ header; else null */
  stepNumber: number | null
  header: string
  actions: AgentLogEntry[]
  screenshot_path?: string | null
  adaptation?: string | null
}

const HEADER_RE = /^▶\s*Step\s+(\d+)\b/i

/**
 * Group segmented-run agent_logs into per-step buckets.
 * Headers look like: "▶ Step 3/6 [PASSED]: …"
 * Action lines look like: "   • Clicked 'Leagues'"
 */
export function groupAgentLogsByStep(logs: AgentLogEntry[] | null | undefined): AgentStepGroup[] {
  if (!logs?.length) return []

  const groups: AgentStepGroup[] = []
  let current: AgentStepGroup | null = null

  for (const entry of logs) {
    const desc = (entry.description || '').trim()
    const headerMatch = HEADER_RE.exec(desc)
    if (headerMatch || desc.startsWith('▶')) {
      current = {
        stepNumber: headerMatch ? Number(headerMatch[1]) : null,
        header: desc,
        actions: [],
        screenshot_path: entry.screenshot_path,
        adaptation: entry.adaptation,
      }
      groups.push(current)
      continue
    }
    if (!current) {
      current = {
        stepNumber: null,
        header: 'Browser actions',
        actions: [],
      }
      groups.push(current)
    }
    current.actions.push(entry)
    if (entry.screenshot_path && !current.screenshot_path) {
      current.screenshot_path = entry.screenshot_path
    }
  }

  return groups
}

/** Actions recorded under a specific step number (from ▶ Step N headers). */
export function actionsForStep(
  groups: AgentStepGroup[],
  stepNumber: number
): AgentLogEntry[] {
  const g = groups.find((x) => x.stepNumber === stepNumber)
  return g?.actions ?? []
}

export function formatActionDescription(desc: string): string {
  const t = (desc || '').trim()
  if (t.startsWith('•')) return t.replace(/^•\s*/, '')
  // "   • foo" style
  const bullet = t.indexOf('•')
  if (bullet >= 0 && bullet < 4) return t.slice(bullet + 1).trim()
  return t
}
