import { Card, CardTitle } from '@common/components/ui/Card'
import {
  ShieldCheckIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
  ListBulletIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import type { IntegrityCheckPreview } from '../types'

type Props = {
  preview: IntegrityCheckPreview | null
  expandedStories: Set<number>
  expandedTcs: Set<number>
  onToggleStory: (id: number) => void
  onToggleTc: (id: number) => void
}

export default function IntegrityCheckExecutionPreview({
  preview,
  expandedStories,
  expandedTcs,
  onToggleStory,
  onToggleTc,
}: Props) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="w-5 h-5 text-green-600" />
          <CardTitle>Execution Preview</CardTitle>
        </div>
        {preview && (
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <BookOpenIcon className="w-4 h-4" />
              {preview.total_user_stories} stories
            </span>
            <span className="flex items-center gap-1">
              <ClipboardDocumentListIcon className="w-4 h-4" />
              {preview.total_test_cases} cases
            </span>
            <span className="flex items-center gap-1">
              <ListBulletIcon className="w-4 h-4" />
              {preview.total_steps} steps
            </span>
          </div>
        )}
      </div>

      {!preview || preview.total_test_cases === 0 ? null : (
        <div className="space-y-2">
          {preview.user_stories.map(us => (
            <div key={us.id} className="border border-gray-200 rounded-lg">
              <button
                type="button"
                onClick={() => onToggleStory(us.id)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 text-left"
              >
                <div className="flex items-center gap-2">
                  {expandedStories.has(us.id) ? (
                    <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                  ) : (
                    <ChevronRightIcon className="w-4 h-4 text-gray-500" />
                  )}
                  <BookOpenIcon className="w-4 h-4 text-blue-500" />
                  {us.external_key && (
                    <span className="text-sm font-mono text-primary-600">{us.external_key}</span>
                  )}
                  <span className="font-medium text-gray-900 text-sm">{us.title}</span>
                </div>
                <span className="text-xs text-gray-500">{us.test_cases.length} test cases</span>
              </button>
              {expandedStories.has(us.id) && (
                <div className="border-t border-gray-100 px-4 pb-3">
                  {us.test_cases.map(tc => (
                    <div key={tc.id} className="ml-6 mt-2">
                      <button
                        type="button"
                        onClick={() => onToggleTc(tc.id)}
                        className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 text-left"
                      >
                        <div className="flex items-center gap-2">
                          {expandedTcs.has(tc.id) ? (
                            <ChevronDownIcon className="w-3.5 h-3.5 text-gray-400" />
                          ) : (
                            <ChevronRightIcon className="w-3.5 h-3.5 text-gray-400" />
                          )}
                          <ClipboardDocumentListIcon className="w-4 h-4 text-indigo-500" />
                          <span className="text-sm text-gray-800">{tc.title}</span>
                        </div>
                        <span className="text-xs text-gray-400">{tc.steps.length} steps</span>
                      </button>
                      {expandedTcs.has(tc.id) && tc.steps.length > 0 && (
                        <div className="ml-8 mt-1 space-y-1">
                          {tc.steps.map(s => (
                            <div
                              key={s.step_number}
                              className="flex items-center gap-2 text-xs text-gray-600 py-1 px-2 bg-gray-50 rounded"
                            >
                              <span className="text-gray-400 w-5 text-right">#{s.step_number}</span>
                              <span className="px-1.5 py-0.5 rounded bg-white border border-gray-200 font-mono">
                                {s.action}
                              </span>
                              {s.target && (
                                <span className="text-gray-500 truncate max-w-xs">{s.target}</span>
                              )}
                              {s.description && (
                                <span className="text-gray-400 truncate">{s.description}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {preview.standalone_test_cases.length > 0 && (
            <div className="border border-gray-200 rounded-lg">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <span className="text-sm font-medium text-gray-700">Standalone Test Cases</span>
              </div>
              <div className="px-4 pb-3">
                {preview.standalone_test_cases.map(tc => (
                  <div key={tc.id} className="mt-2">
                    <button
                      type="button"
                      onClick={() => onToggleTc(tc.id)}
                      className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 text-left"
                    >
                      <div className="flex items-center gap-2">
                        {expandedTcs.has(tc.id) ? (
                          <ChevronDownIcon className="w-3.5 h-3.5 text-gray-400" />
                        ) : (
                          <ChevronRightIcon className="w-3.5 h-3.5 text-gray-400" />
                        )}
                        <ClipboardDocumentListIcon className="w-4 h-4 text-indigo-500" />
                        <span className="text-sm text-gray-800">{tc.title}</span>
                      </div>
                      <span className="text-xs text-gray-400">{tc.steps.length} steps</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
