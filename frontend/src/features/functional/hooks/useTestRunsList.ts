import { useState, useEffect, useCallback } from 'react'
import { testRunsApi, type PaginatedResponse } from '../api'
import type { TestRun, TestRunSummary } from '../types'

const DEFAULT_PAGE_SIZE = 20

export function useTestRunsList(
  projectId: string | undefined,
  statusFilter: string,
  pageSize: number = DEFAULT_PAGE_SIZE
) {
  const [runs, setRuns] = useState<TestRun[]>([])
  const [summary, setSummary] = useState<TestRunSummary | null>(null)
  const [page, setPage] = useState(1)
  const [meta, setMeta] = useState({
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  })
  const [loading, setLoading] = useState(true)

  const loadSummary = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await testRunsApi.summary(Number(projectId))
      setSummary(res.data)
    } catch {
      setSummary(null)
    }
  }, [projectId])

  const loadRuns = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const params: {
        page: number
        page_size: number
        status_filter?: string
      } = { page, page_size: pageSize }
      if (statusFilter !== 'all') {
        params.status_filter = statusFilter
      }
      const res = await testRunsApi.list(Number(projectId), params)
      const data = res.data as PaginatedResponse<TestRun>
      setRuns(data.items || [])
      setMeta({
        total: data.total,
        total_pages: data.total_pages || 1,
        has_next: data.has_next,
        has_prev: data.has_prev,
      })
    } catch {
      setRuns([])
    } finally {
      setLoading(false)
    }
  }, [projectId, page, pageSize, statusFilter])

  useEffect(() => {
    loadSummary()
  }, [loadSummary])

  useEffect(() => {
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    setPage(1)
  }, [statusFilter, projectId])

  return {
    runs,
    summary,
    loading,
    page,
    setPage,
    meta,
    pageSize,
    reload: () => {
      loadSummary()
      loadRuns()
    },
  }
}
