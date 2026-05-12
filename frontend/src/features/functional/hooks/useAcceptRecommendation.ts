import { useCallback, useState } from 'react'
import { useProjectStore } from '@common/store/projectStore'
import { userStoriesApi, testCasesApi } from '../api'
import { useActiveTestRun } from '../context/ActiveTestRunProvider'
import type { UserStory } from '../types'

// ---------------------------------------------------------------------------
// Phase state machine
// ---------------------------------------------------------------------------

export type AcceptPhase =
  | { type: 'idle' }
  | { type: 'checking_url' }
  | { type: 'fetching_stories' }
  | { type: 'generating'; total: number; done: number; currentTitle: string }
  | { type: 'promoting'; count: number }
  | { type: 'launching' }
  | { type: 'done'; runId: number }
  | { type: 'error'; message: string }

export type AcceptPhaseType = AcceptPhase['type']

// ---------------------------------------------------------------------------
// Category → action resolution
// ---------------------------------------------------------------------------

/**
 * Categories that map to the in-product Functional Testing workspace.
 * Everything else is "coming soon" (API, Security, Performance, etc.)
 */
const FUNCTIONAL_CATEGORIES = new Set(['functional', 'regression', 'smoke', 'e2e', 'sanity'])

export function resolveItemAction(category: string | undefined): 'functional' | 'coming-soon' {
  const c = (category ?? '').toLowerCase().trim()
  return FUNCTIONAL_CATEGORIES.has(c) ? 'functional' : 'coming-soon'
}

const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  api: 'API Testing',
  integration: 'API & Integration Testing',
  security: 'Security Testing',
  performance: 'Performance Testing',
  compliance: 'Compliance Testing',
  usability: 'Usability Testing',
  compatibility: 'Compatibility Testing',
}

export function getComingSoonFeatureName(category: string | undefined): string {
  const c = (category ?? '').toLowerCase().trim()
  return CATEGORY_DISPLAY_NAMES[c] ?? `${category ?? 'This'} Testing`
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseAcceptRecommendationReturn {
  phase: AcceptPhase
  /** Kick off the full generate-promote-run flow for the Functional category. */
  accept: () => Promise<void>
  reset: () => void
  /** Mirrors the run context's isRunning so callers can disable "Run" buttons */
  contextRunning: boolean
}

/**
 * Orchestrates the one-click "Accept & Run" flow from a test recommendation:
 *
 *  1. Verify the project has an App URL configured.
 *  2. Fetch all user stories for the project.
 *  3. Generate AI test cases for every story that has none yet.
 *  4. Bulk-promote all newly generated cases to "ready" so the runner picks them up.
 *  5. Start a test run (all ready cases) via the ActiveTestRun context.
 *
 * Designed to be used inside a component that lives within <ActiveTestRunProvider>.
 */
export function useAcceptRecommendation(
  projectId: string | undefined
): UseAcceptRecommendationReturn {
  const [phase, setPhase] = useState<AcceptPhase>({ type: 'idle' })
  const activeRun = useActiveTestRun()

  const accept = useCallback(async () => {
    if (!projectId) {
      setPhase({ type: 'error', message: 'Project ID is missing.' })
      return
    }

    if (!activeRun) {
      setPhase({
        type: 'error',
        message: 'Run context is unavailable. Make sure you are inside a project workspace.',
      })
      return
    }

    const pid = Number(projectId)

    // ── Step 1: Ensure App URL ───────────────────────────────────────────────
    setPhase({ type: 'checking_url' })
    const hasUrl = await activeRun.ensureProjectHasAppUrl()
    if (!hasUrl) {
      setPhase({
        type: 'error',
        message:
          'App URL is not configured. Open Project Settings and add the URL of your application before running tests.',
      })
      return
    }

    // ── Step 2: Fetch user stories (paginate through all pages) ─────────────
    setPhase({ type: 'fetching_stories' })
    let stories: UserStory[] = []
    try {
      const PAGE_SIZE = 50
      let page = 1
      let hasMore = true
      while (hasMore) {
        const res = await userStoriesApi.list(pid, { page, page_size: PAGE_SIZE })
        const data = res.data
        stories = [...stories, ...(data.items ?? [])]
        hasMore = data.has_next ?? false
        page += 1
      }
    } catch (err) {
      const detail =
        err &&
        typeof err === 'object' &&
        'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      setPhase({
        type: 'error',
        message: detail
          ? `Failed to fetch user stories: ${detail}`
          : 'Failed to fetch user stories. Please try again.',
      })
      return
    }

    if (stories.length === 0) {
      setPhase({
        type: 'error',
        message:
          'No user stories found in this project. Add or import user stories before running functional tests.',
      })
      return
    }

    // ── Step 3: Generate test cases for stories that have none yet ───────────
    const needGeneration = stories.filter((s) => (s.generated_test_cases ?? 0) === 0)
    const generatedCaseIds: number[] = []

    if (needGeneration.length > 0) {
      for (let i = 0; i < needGeneration.length; i++) {
        const story = needGeneration[i]
        setPhase({
          type: 'generating',
          total: needGeneration.length,
          done: i,
          currentTitle: story.title,
        })
        try {
          const res = await userStoriesApi.generateTests(pid, story.id, { include_steps: true })
          if (res.data.success && res.data.test_cases.length > 0) {
            generatedCaseIds.push(...res.data.test_cases.map((tc) => tc.id))
          }
        } catch {
          // Non-fatal: a single story failure should not abort the entire flow.
        }
      }
    }

    // ── Step 4: Promote newly generated cases to "ready" ────────────────────
    if (generatedCaseIds.length > 0) {
      setPhase({ type: 'promoting', count: generatedCaseIds.length })
      try {
        await testCasesApi.bulkUpdateStatus(pid, generatedCaseIds, 'ready')
      } catch {
        // Non-fatal: proceed to launch — existing ready cases will still run.
      }
    }

    // ── Step 5: Start a full run (all ready cases) ───────────────────────────
    setPhase({ type: 'launching' })
    const cp = useProjectStore.getState().currentProject
    const runId = await activeRun.startRun({
      project_id: pid,
      app_url: cp?.app_url || undefined,
    })

    if (runId) {
      setPhase({ type: 'done', runId })
    } else {
      setPhase({
        type: 'error',
        message:
          activeRun.error ??
          'Failed to start the test run. Verify your App URL is reachable and try again.',
      })
    }
  }, [projectId, activeRun])

  const reset = useCallback(() => setPhase({ type: 'idle' }), [])

  return {
    phase,
    accept,
    reset,
    contextRunning: activeRun?.isRunning ?? false,
  }
}
