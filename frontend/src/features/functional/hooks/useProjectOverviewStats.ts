import { useCallback, useEffect, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import {
  userStoriesApi,
  requirementsApi,
  testCasesApi,
  testRunsApi,
  integrityCheckApi,
} from '../api'

export type ProjectOverviewStats = {
  userStories: number
  requirements: number
  testCases: number
  testRuns: number
  integrityLabel: string
  integrations: number
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`
}

export function useProjectOverviewStats(projectId: string | undefined) {
  const [stats, setStats] = useState<ProjectOverviewStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!projectId) {
      setStats(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    const pid = Number(projectId)

    try {
      const [
        storiesR,
        reqR,
        tcR,
        runsR,
        integHistR,
        integrationsR,
      ] = await Promise.allSettled([
        userStoriesApi.getStats(pid),
        requirementsApi.list(projectId, { page: 1, page_size: 1 }),
        testCasesApi.list(pid, { page: 1, page_size: 1 }),
        testRunsApi.summary(pid),
        integrityCheckApi.getHistory(projectId, { limit: 5 }),
        userStoriesApi.getIntegrations(pid),
      ])

      let userStories = 0
      if (storiesR.status === 'fulfilled') {
        userStories = storiesR.value.data.total ?? 0
      }

      let requirements = 0
      if (reqR.status === 'fulfilled') {
        requirements = reqR.value.data.total ?? 0
      }

      let testCases = 0
      if (tcR.status === 'fulfilled') {
        testCases = tcR.value.data.total ?? 0
      }

      let testRuns = 0
      if (runsR.status === 'fulfilled') {
        testRuns = runsR.value.data.total ?? 0
      }

      let integrityLabel = 'No runs yet'
      if (integHistR.status === 'fulfilled') {
        const rows = integHistR.value.data || []
        const last = rows[0]?.created_at
        if (last) {
          integrityLabel = `${formatDistanceToNow(new Date(last), { addSuffix: true })}`
        }
      }

      let integrations = 0
      if (integrationsR.status === 'fulfilled') {
        integrations = Array.isArray(integrationsR.value.data)
          ? integrationsR.value.data.length
          : 0
      }

      setStats({
        userStories,
        requirements,
        testCases,
        testRuns,
        integrityLabel,
        integrations,
      })
    } catch {
      setError('Failed to load some statistics')
      setStats({
        userStories: 0,
        requirements: 0,
        testCases: 0,
        testRuns: 0,
        integrityLabel: '—',
        integrations: 0,
      })
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    load()
  }, [load])

  const labels = stats
    ? {
        userStories: plural(stats.userStories, 'story', 'stories'),
        requirements: plural(stats.requirements, 'document', 'documents'),
        testCases: plural(stats.testCases, 'case', 'cases'),
        testRuns: plural(stats.testRuns, 'run', 'runs'),
        integrity: stats.integrityLabel,
        integrations:
          stats.integrations === 0
            ? 'None connected'
            : plural(stats.integrations, 'integration', 'integrations'),
      }
    : null

  return { stats, labels, loading, error, reload: load }
}
