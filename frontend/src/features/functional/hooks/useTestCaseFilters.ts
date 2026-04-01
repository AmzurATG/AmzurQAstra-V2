import { useState, useCallback, useEffect } from 'react'
import { testCasesApi } from '../api'
import type { TestCase } from '../types'

export function useTestCaseFilters(projectId: string | undefined) {
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const loadTestCases = useCallback(async () => {
    if (!projectId) return
    setIsLoading(true)
    try {
      const params: any = { page_size: 100 }
      if (priorityFilter !== 'all') params.priority = priorityFilter
      if (categoryFilter !== 'all') params.category = categoryFilter
      if (statusFilter !== 'all') params.status = statusFilter
      if (searchQuery) params.search = searchQuery
      
      const response = await testCasesApi.list(Number(projectId), params)
      setTestCases(response.data.items || [])
    } catch (error) {
      console.error('Failed to load test cases:', error)
    } finally {
      setIsLoading(false)
    }
  }, [projectId, priorityFilter, categoryFilter, statusFilter, searchQuery])

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
    loadTestCases
  }
}
