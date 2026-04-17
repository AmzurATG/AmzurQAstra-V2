import React from 'react'
import { 
  ChevronDownIcon, 
  ChevronRightIcon, 
  PlayIcon, 
  PencilIcon, 
  TrashIcon, 
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { Link } from 'react-router-dom'
import type { TestCase, TestStep, LiveProgressResponse } from '../types'

interface TestCaseTableProps {
  projectId: string | undefined
  testCases: TestCase[]
  expandedRows: Set<number>
  toggleRowExpansion: (id: number) => void
  loadingSteps: Set<number>
  stepsCache: Record<number, TestStep[]>
  onEdit: (tc: TestCase) => void
  onDelete: (testCaseId: number, title: string) => void
  onRunSingle: (tcId: number) => void
  selectedIds: Set<number>
  onToggleSelect: (id: number) => void
  onToggleAll: () => void
  isRunning?: boolean
  progress?: LiveProgressResponse | null
}

const statusIcons = {
  ready: <CheckCircleIcon className="w-5 h-5 text-green-500" />,
  draft: <ClockIcon className="w-5 h-5 text-yellow-500" />,
  deprecated: <XCircleIcon className="w-5 h-5 text-red-500" />,
}

const priorityColors = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-gray-100 text-gray-700',
}

const categoryColors = {
  smoke: 'bg-purple-100 text-purple-700',
  regression: 'bg-blue-100 text-blue-700',
  e2e: 'bg-green-100 text-green-700',
  integration: 'bg-cyan-100 text-cyan-700',
  sanity: 'bg-gray-100 text-gray-700',
}

const itemTypeColors = {
  epic: 'bg-purple-100 text-purple-700',
  story: 'bg-blue-100 text-blue-700',
  bug: 'bg-red-100 text-red-700',
  task: 'bg-gray-100 text-gray-700',
}

const actionIcons: Record<string, string> = {
  navigate: '🌐',
  click: '👆',
  fill: '✏️',
  type: '⌨️',
  select: '📋',
  check: '☑️',
  uncheck: '☐',
  hover: '👁️',
  wait: '⏳',
  screenshot: '📸',
  assert_visible: '👀',
  assert_text: '📝',
  assert_url: '🔗',
  assert_title: '📰',
  custom: '⚙️',
}

export const TestCaseTable: React.FC<TestCaseTableProps> = ({
  projectId,
  testCases,
  expandedRows,
  toggleRowExpansion,
  loadingSteps,
  stepsCache,
  onEdit,
  onDelete,
  onRunSingle,
  selectedIds,
  onToggleSelect,
  onToggleAll,
  isRunning,
  progress
}) => {
  const allCurrentPageSelected =
    testCases.length > 0 && testCases.every((tc) => selectedIds.has(tc.id))

  return (
    <table className="w-full">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="w-8 px-4 py-3">
            <input 
              type="checkbox" 
              className="rounded" 
              checked={allCurrentPageSelected}
              onChange={onToggleAll} 
            />
          </th>
          <th className="w-8 px-4 py-3"></th>
          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap w-24">
            Case #
          </th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User Story</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Steps</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200">
        {testCases.map((tc) => {
          const isCurrentlyRunning = progress?.status === 'running' && 
            (progress.current_test_case_title === tc.title || 
             progress.completed_results.some(r => r.test_case_id === tc.id && r.status === 'running'));
          
          const completedResult = progress?.completed_results.find(r => r.test_case_id === tc.id);

          return (
            <React.Fragment key={tc.id}>
              <tr className={`transition-colors ${isCurrentlyRunning ? 'bg-primary-50/50' : 'hover:bg-gray-50'}`}>
                <td className="px-4 py-4">
                  <input 
                    type="checkbox" 
                    className="rounded" 
                    checked={selectedIds.has(tc.id)} 
                    onChange={() => onToggleSelect(tc.id)} 
                  />
                </td>
                <td className="px-4 py-4">
                  <button 
                    onClick={() => toggleRowExpansion(tc.id)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    {expandedRows.has(tc.id) ? (
                      <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRightIcon className="w-4 h-4 text-gray-500" />
                    )}
                  </button>
                </td>
                <td className="px-3 py-4">
                  <span className="inline-flex items-center justify-center min-w-[2.25rem] px-2 py-1 rounded-md bg-gray-100 text-sm font-bold text-gray-900 tabular-nums">
                    #{tc.case_number ?? tc.id}
                  </span>
                </td>
                <td className="px-4 py-4">
                  {isCurrentlyRunning ? (
                    <div className="flex items-center justify-center w-5 h-5">
                      <ArrowPathIcon className="w-4 h-4 text-primary-500 animate-spin" />
                    </div>
                  ) : completedResult ? (
                    completedResult.status === 'passed' 
                      ? <CheckCircleIcon className="w-5 h-5 text-green-500" />
                      : <XCircleIcon className="w-5 h-5 text-red-500" />
                  ) : (
                    statusIcons[tc.status as keyof typeof statusIcons]
                  )}
                </td>
                <td className="px-4 py-4">
                  <Link 
                    to={`/projects/${projectId}/test-cases/${tc.id}`} 
                    className={`font-medium hover:underline ${isCurrentlyRunning ? 'text-primary-700' : 'text-primary-600'}`}
                  >
                    {tc.title}
                  </Link>
                  {isCurrentlyRunning && (
                    <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary-100 text-primary-800 animate-pulse">
                      RUNNING
                    </span>
                  )}
                </td>
              <td className="px-4 py-4">
                {tc.user_story ? (
                  <div className="inline-flex items-center gap-1 text-sm">
                    <span className={`px-1.5 py-0.5 text-xs rounded ${itemTypeColors[tc.user_story.item_type as keyof typeof itemTypeColors] || 'bg-gray-100 text-gray-700'}`}>
                      {tc.user_story.item_type}
                    </span>
                    <span className="text-gray-600 font-mono text-xs">
                      {tc.user_story.external_key || `US-${tc.user_story.id}`}
                    </span>
                  </div>
                ) : (
                  <span className="text-gray-400 text-sm">—</span>
                )}
              </td>
              <td className="px-4 py-4">
                <span className={`px-2 py-1 text-xs rounded font-medium ${priorityColors[tc.priority as keyof typeof priorityColors]}`}>
                  {tc.priority}
                </span>
              </td>
              <td className="px-4 py-4">
                <span className={`px-2 py-1 text-xs rounded ${categoryColors[tc.category as keyof typeof categoryColors] || 'bg-gray-100 text-gray-600'}`}>
                  {tc.category}
                </span>
              </td>
              <td className="px-4 py-4">
                <span className="text-sm text-gray-600">{tc.steps_count} steps</span>
              </td>
              <td className="px-4 py-4">
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRunSingle(tc.id)}
                    disabled={isRunning}
                    title="Run this test case"
                  >
                    <PlayIcon className="w-4 h-4 text-green-600" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => onEdit(tc)}
                  >
                    <PencilIcon className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    onClick={() => onDelete(tc.id, tc.title)}
                  >
                    <TrashIcon className="w-4 h-4" />
                  </Button>
                </div>
              </td>
            </tr>
            
            {expandedRows.has(tc.id) && (
              <tr className="bg-gray-50">
                <td colSpan={10} className="px-4 py-4">
                  {loadingSteps.has(tc.id) ? (
                    <div className="flex items-center justify-center py-4">
                      <ArrowPathIcon className="w-5 h-5 animate-spin text-primary-500 mr-2" />
                      <span className="text-sm text-gray-500">Loading steps...</span>
                    </div>
                  ) : stepsCache[tc.id]?.length > 0 ? (
                    <div className="ml-8 mr-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Test Steps</h4>
                      <div className="space-y-2">
                        {stepsCache[tc.id].map((step) => (
                          <div
                            key={step.id}
                            className="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-200"
                          >
                            <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
                              {step.step_number}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-base">
                                  {actionIcons[step.action] || '⚙️'}
                                </span>
                                <span className="text-xs font-medium text-gray-500 uppercase">
                                  {step.action.replace('_', ' ')}
                                </span>
                                {step.target && (
                                  <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-700 truncate max-w-xs">
                                    {step.target}
                                  </span>
                                )}
                              </div>
                              {step.description && (
                                <p className="text-sm text-gray-600">{step.description}</p>
                              )}
                              {step.expected_result && (
                                <p className="text-xs text-gray-500 mt-1">
                                  <span className="font-medium">Expected:</span> {step.expected_result}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4 text-sm text-gray-500">
                      No steps generated yet
                    </div>
                  )}
                </td>
              </tr>
            )}
          </React.Fragment>
        )})}
      </tbody>
    </table>
  )
}
