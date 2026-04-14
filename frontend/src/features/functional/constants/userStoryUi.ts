import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import type { UserStoryItemType, UserStoryPriority, UserStoryStatus } from '../types'

export const USER_STORIES_PAGE_SIZE = 20

/** Jira/PM issue type names for default quick sync and modal initial selection */
export const DEFAULT_SYNC_ISSUE_TYPES = ['Epic', 'Story', 'Bug'] as const

export const STATUS_OPTIONS: UserStoryStatus[] = [
  'open',
  'in_progress',
  'done',
  'blocked',
  'closed',
]

export const PRIORITY_OPTIONS: UserStoryPriority[] = ['low', 'medium', 'high', 'critical']

export const ITEM_TYPE_OPTIONS: UserStoryItemType[] = [
  'epic',
  'story',
  'bug',
  'task',
  'subtask',
  'feature',
  'requirement',
]

export const statusConfig = {
  open: { label: 'Open', color: 'bg-gray-100 text-gray-700', icon: ClockIcon },
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: ArrowPathIcon },
  done: { label: 'Done', color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
  blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700', icon: ExclamationCircleIcon },
  closed: { label: 'Closed', color: 'bg-gray-100 text-gray-600', icon: CheckCircleIcon },
}

export const priorityConfig = {
  low: { label: 'Low', color: 'bg-gray-100 text-gray-600' },
  medium: { label: 'Medium', color: 'bg-yellow-100 text-yellow-700' },
  high: { label: 'High', color: 'bg-orange-100 text-orange-700' },
  critical: { label: 'Critical', color: 'bg-red-100 text-red-700' },
}

export const sourceConfig = {
  jira: { label: 'Jira', icon: '🎫' },
  redmine: { label: 'Redmine', icon: '🔴' },
  azure_devops: { label: 'Azure DevOps', icon: '🔷' },
  manual: { label: 'Manual', icon: '✏️' },
}

export const itemTypeConfig = {
  epic: { label: 'Epic', color: 'bg-purple-100 text-purple-700' },
  story: { label: 'Story', color: 'bg-blue-100 text-blue-700' },
  bug: { label: 'Bug', color: 'bg-red-100 text-red-700' },
  task: { label: 'Task', color: 'bg-gray-100 text-gray-700' },
  subtask: { label: 'Sub-task', color: 'bg-gray-100 text-gray-600' },
  feature: { label: 'Feature', color: 'bg-green-100 text-green-700' },
  requirement: { label: 'Requirement', color: 'bg-indigo-100 text-indigo-700' },
}
