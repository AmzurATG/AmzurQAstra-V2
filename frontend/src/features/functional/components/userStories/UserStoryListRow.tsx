import { useNavigate } from 'react-router-dom'
import { SparklesIcon, TrashIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import type { UserStory } from '../../types'
import {
  aiGeneratedTestsExistCopy,
  itemTypeConfig,
  priorityConfig,
  sourceConfig,
  statusConfig,
} from '../../constants/userStoryUi'

type Props = {
  story: UserStory
  projectId: string
  serial: number
  generatingStoryId: number | null
  deletingStoryId: number | null
  onGenerateTests: (storyId: number, key: string | null) => void
  onDelete: (storyId: number, key: string | null) => void
}

export function UserStoryListRow({
  story,
  projectId,
  serial,
  generatingStoryId,
  deletingStoryId,
  onGenerateTests,
  onDelete,
}: Props) {
  const navigate = useNavigate()
  const detailPath = `/projects/${projectId}/user-stories/${story.id}`
  const generatedCount = story.generated_test_cases ?? 0
  const hasGeneratedTests = generatedCount > 0

  const statusCfg = statusConfig[story.status] || statusConfig.open
  const StatusIcon = statusCfg.icon
  const priorityCfg = priorityConfig[story.priority] || priorityConfig.medium
  const sourceCfg = sourceConfig[story.source] || sourceConfig.manual
  const itemTypeCfg = itemTypeConfig[story.item_type] || itemTypeConfig.story

  const openDetail = () => navigate(detailPath)

  return (
    <div className="rounded-lg px-2 py-4 -mx-2 transition-colors hover:bg-gray-50">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 flex-1 gap-3">
          <span
            className="w-9 shrink-0 pt-0.5 text-right text-sm tabular-nums text-gray-400"
            aria-hidden
          >
            {serial}.
          </span>
          <button
            type="button"
            onClick={openDetail}
            className="min-w-0 flex-1 rounded-md text-left outline-none ring-primary-500 focus-visible:ring-2"
          >
            <div className="flex flex-wrap items-center gap-2 mb-1">
              {story.external_key && (
                <span className="font-mono text-sm text-primary-600">{story.external_key}</span>
              )}
              <span className="text-xs" title={sourceCfg.label}>
                {sourceCfg.icon}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${itemTypeCfg.color}`}>
                {itemTypeCfg.label}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg.color}`}
              >
                <StatusIcon className="h-3 w-3" />
                {statusCfg.label}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityCfg.color}`}
              >
                {priorityCfg.label}
              </span>
              {story.integrity_check && (
                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                  <ShieldCheckIcon className="h-3 w-3" />
                  Integrity
                </span>
              )}
            </div>
            <h3 className="font-medium text-gray-900">{story.title}</h3>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500">
              {story.assignee && <span>Assignee: {story.assignee}</span>}
              {story.story_points != null && <span>{story.story_points} pts</span>}
              {story.parent_key && <span className="text-purple-600">Parent: {story.parent_key}</span>}
              <span>{story.linked_requirements} requirements</span>
              <span>{story.linked_test_cases} test cases</span>
            </div>
          </button>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5 sm:max-w-[min(100%,28rem)]">
          <div className="flex flex-wrap items-center justify-end gap-2">
          <Button variant="outline" size="sm" type="button" onClick={(e) => { e.stopPropagation(); openDetail() }}>
            View
          </Button>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onGenerateTests(story.id, story.external_key ?? null)
            }}
            disabled={hasGeneratedTests || generatingStoryId === story.id}
            isLoading={generatingStoryId === story.id}
            title={
              hasGeneratedTests
                ? 'Test cases already generated for this story'
                : 'Create AI test cases from this story'
            }
          >
            {generatingStoryId !== story.id && <SparklesIcon className="mr-1 h-4 w-4" />}
            Generate tests
          </Button>
          <Button
            variant="danger"
            size="sm"
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(story.id, story.external_key ?? null)
            }}
            disabled={deletingStoryId === story.id}
            isLoading={deletingStoryId === story.id}
          >
            {deletingStoryId !== story.id && <TrashIcon className="mr-1 h-4 w-4" />}
            Delete
          </Button>
          </div>
          {hasGeneratedTests && (
            <p
              className="text-xs text-gray-500 text-right max-w-[18rem] leading-snug"
              role="status"
            >
              {aiGeneratedTestsExistCopy(generatedCount)}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
