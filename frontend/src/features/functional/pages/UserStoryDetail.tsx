import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon, PencilIcon, SparklesIcon, TrashIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { Card, CardTitle } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { PageLoader } from '@common/components/ui/Loader'
import { userStoriesApi } from '../api'
import type { UserStory } from '../types'
import { UserStoryEditModal } from '../components/userStories/UserStoryEditModal'
import { itemTypeConfig, priorityConfig, sourceConfig, statusConfig } from '../constants/userStoryUi'
import toast from 'react-hot-toast'

export default function UserStoryDetail() {
  const { projectId, storyId } = useParams<{ projectId: string; storyId: string }>()
  const navigate = useNavigate()
  const pid = Number(projectId)
  const sid = Number(storyId)

  const [story, setStory] = useState<UserStory | null>(null)
  const [loading, setLoading] = useState(true)
  const [editOpen, setEditOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadStory = useCallback(async () => {
    if (!projectId || !storyId || Number.isNaN(sid)) return
    setLoading(true)
    try {
      const res = await userStoriesApi.get(pid, sid)
      setStory(res.data)
    } catch {
      setStory(null)
      toast.error('Failed to load user story')
    } finally {
      setLoading(false)
    }
  }, [pid, projectId, sid, storyId])

  useEffect(() => {
    loadStory()
  }, [loadStory])

  const handleGenerateTests = async () => {
    if (!story) return
    setGenerating(true)
    try {
      const response = await userStoriesApi.generateTests(pid, story.id, { include_steps: true })
      if (response.data.success) {
        toast.success(`Generated ${response.data.test_cases_created} test case(s)`)
        loadStory()
      } else {
        toast.error(response.data.error || 'Failed to generate tests')
      }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to generate tests')
    } finally {
      setGenerating(false)
    }
  }

  const handleDelete = async () => {
    if (!story) return
    const key = story.external_key
    if (
      !window.confirm(
        `Delete ${key || `story #${story.id}`}? Related test cases and steps will be removed.`
      )
    ) {
      return
    }
    setDeleting(true)
    try {
      await userStoriesApi.delete(pid, story.id)
      toast.success('User story deleted')
      navigate(`/projects/${projectId}/user-stories`)
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(message || 'Failed to delete')
    } finally {
      setDeleting(false)
    }
  }

  if (loading) return <PageLoader />

  if (!story) {
    return (
      <div className="space-y-4">
        <Link
          to={`/projects/${projectId}/user-stories`}
          className="inline-flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to user stories
        </Link>
        <Card>
          <p className="text-gray-600">Story not found or you don&apos;t have access.</p>
        </Card>
      </div>
    )
  }

  const statusCfg = statusConfig[story.status] || statusConfig.open
  const StatusIcon = statusCfg.icon
  const priorityCfg = priorityConfig[story.priority] || priorityConfig.medium
  const sourceCfg = sourceConfig[story.source] || sourceConfig.manual
  const itemTypeCfg = itemTypeConfig[story.item_type] || itemTypeConfig.story

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <Link
          to={`/projects/${projectId}/user-stories`}
          className="inline-flex shrink-0 items-center gap-2 text-sm text-primary-600 hover:text-primary-700"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to list
        </Link>
        <div className="flex flex-wrap gap-2 lg:ml-auto">
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            <PencilIcon className="mr-1.5 h-4 w-4" />
            Edit
          </Button>
          <Button variant="outline" onClick={handleGenerateTests} disabled={generating} isLoading={generating}>
            <SparklesIcon className="mr-1.5 h-4 w-4" />
            Generate tests
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={deleting} isLoading={deleting}>
            <TrashIcon className="mr-1.5 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <Card className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 pb-4">
          {story.external_key && (
            <span className="font-mono text-lg text-primary-600">{story.external_key}</span>
          )}
          <span title={sourceCfg.label}>{sourceCfg.icon}</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${itemTypeCfg.color}`}>
            {itemTypeCfg.label}
          </span>
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg.color}`}
          >
            <StatusIcon className="h-3 w-3" />
            {statusCfg.label}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityCfg.color}`}>
            {priorityCfg.label}
          </span>
          {story.integrity_check && (
            <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
              <ShieldCheckIcon className="h-3 w-3" />
              Integrity check
            </span>
          )}
        </div>
        <h1 className="mt-4 text-2xl font-bold text-gray-900">{story.title}</h1>
        <div className="mt-3 flex flex-wrap gap-4 text-sm text-gray-600">
          {story.assignee && <span>Assignee: {story.assignee}</span>}
          {story.story_points != null && <span>{story.story_points} points</span>}
          {story.parent_key && <span className="text-purple-600">Parent: {story.parent_key}</span>}
          <span>{story.linked_requirements} requirements</span>
          <span>{story.linked_test_cases} test cases</span>
        </div>
      </Card>

      <Card className="min-w-0">
        <CardTitle>Description</CardTitle>
        <p className="mt-2 whitespace-pre-wrap text-gray-700">
          {story.description?.trim() ? story.description : '—'}
        </p>
      </Card>

      <Card className="min-w-0">
        <CardTitle>Acceptance criteria</CardTitle>
        <p className="mt-2 whitespace-pre-wrap text-gray-700">
          {story.acceptance_criteria?.trim() ? story.acceptance_criteria : '—'}
        </p>
      </Card>

      <UserStoryEditModal
        projectId={pid}
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        story={story}
        onSaved={loadStory}
      />
    </div>
  )
}
