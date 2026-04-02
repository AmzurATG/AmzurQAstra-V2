import { useState, useCallback, useEffect, useRef } from 'react'
import { testCasesApi, type PaginatedResponse } from '../api'
import type { TestCase } from '../types'

const DEFAULT_PAGE_SIZE = 25

export function useTestCaseFilters(projectId: string | undefined) {
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  })

  const filterSig = `${projectId}|${priorityFilter}|${categoryFilter}|${statusFilter}|${searchQuery}`
  const lastFilterSig = useRef<string | null>(null)

  useEffect(() => {
    lastFilterSig.current = null
  }, [projectId])

  const loadTestCases = useCallback(async () => {
    if (!projectId) return
    setIsLoading(true)
    try {
      let pageToUse = page
      if (lastFilterSig.current === null) {
        lastFilterSig.current = filterSig
      } else if (lastFilterSig.current !== filterSig) {
        lastFilterSig.current = filterSig
        pageToUse = 1
        if (page !== 1) setPage(1)
      }

      const params: {
        page: number
        page_size: number
        priority?: string
        category?: string
        status?: string
        search?: string
      } = { page: pageToUse, page_size: DEFAULT_PAGE_SIZE }
      if (priorityFilter !== 'all') params.priority = priorityFilter
      if (categoryFilter !== 'all') params.category = categoryFilter
      if (statusFilter !== 'all') params.status = statusFilter
      if (searchQuery) params.search = searchQuery

      const response = await testCasesApi.list(Number(projectId), params)
      const data = response.data as PaginatedResponse<TestCase>
      setTestCases(data.items || [])
      setPagination({
        total: data.total,
        total_pages: data.total_pages || 1,
        has_next: data.has_next,
        has_prev: data.has_prev,
      })
    } catch (error) {
      console.error('Failed to load test cases:', error)
    } finally {
      setIsLoading(false)
    }
  }, [
    projectId,
    filterSig,
    page,
    priorityFilter,
    categoryFilter,
    statusFilter,
    searchQuery,
  ])

  useEffect(() => {
    loadTestCases()
  }, [loadTestCases])

  return {
    testCases,
    setTestCases,
    isLoading,
    searchQuery,
    setSearchQuery,
    priorityFilter,
    setPriorityFilter,
    categoryFilter,
    setCategoryFilter,
    statusFilter,
    setStatusFilter,
    page,
    setPage,
    pagination,
    loadTestCases,
  }
}
