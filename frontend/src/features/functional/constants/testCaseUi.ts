import type { TestCaseCategory, TestCasePriority, TestCaseStatus } from '../types'
import { formatDisplayLabel } from '@common/utils/formatDisplayLabel'

export const testCasePriorityLabels: Record<TestCasePriority, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

export const testCaseCategoryLabels: Record<TestCaseCategory, string> = {
  smoke: 'Smoke',
  regression: 'Regression',
  e2e: 'E2E',
  integration: 'Integration',
  sanity: 'Sanity',
}

export const testCaseStatusLabels: Record<TestCaseStatus, string> = {
  draft: 'Draft',
  ready: 'Ready',
  deprecated: 'Deprecated',
}

export function testCasePriorityLabel(priority: string): string {
  return testCasePriorityLabels[priority as TestCasePriority] ?? formatDisplayLabel(priority)
}

export function testCaseCategoryLabel(category: string): string {
  return testCaseCategoryLabels[category as TestCaseCategory] ?? formatDisplayLabel(category)
}

export function testCaseStatusLabel(status: string): string {
  return testCaseStatusLabels[status as TestCaseStatus] ?? formatDisplayLabel(status)
}
