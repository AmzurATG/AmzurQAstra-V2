import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useState,
} from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowPathIcon,
  ArrowUturnLeftIcon,
  ArrowUturnRightIcon,
  ArrowUpOnSquareIcon,
  CheckCircleIcon,
  ClockIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { Card, CardTitle } from '@common/components/ui/Card'

import { testCasesApi } from '../../api'
import { TestCaseEditModal } from '../TestCaseEditModal'
import type { TestCase, TestCasePriority } from '../../types'

export interface StoryTestCaseListHandle {
  reload: () => void
}

export interface StoryTestCaseListProps {
  projectId: number
  storyId: number
  /** Fires when promotions/demotions change counts so the parent can refresh. */
  onCountsChange?: (counts: { draft: number; ready: number; total: number }) => void
}

const PRIORITY_PILL: Record<TestCasePriority, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-gray-100 text-gray-700',
}

const PAGE_SIZE = 100

/**
 * Story-scoped test-case list with a promotion gate.
 *
 * Data model note: the server already defaults `TestCase.status` to `draft`
 * on creation, so the promotion flow is a pure UI concern — we flip
 * draft <-> ready via the existing PUT endpoint (bulkUpdateStatus fan-out).
 * No backend changes.
 *
 * UX contract:
 *   - Drafts live in the top section with bulk-select + Move to Functional Testing.
 *   - Readies live in the bottom section with a "Move back to draft" escape hatch
 *     so mis-clicks are always one step away from recovery.
 *   - A 5-second Undo toast covers accidental promotion of the wrong rows.
 */
export const StoryTestCaseList = forwardRef<StoryTestCaseListHandle, StoryTestCaseListProps>(
  function StoryTestCaseList(
    { projectId, storyId, onCountsChange }: StoryTestCaseListProps,
    ref
  ) {
  const [cases, setCases] = useState<TestCase[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedDrafts, setSelectedDrafts] = useState<Set<number>>(new Set())
  const [promotingIds, setPromotingIds] = useState<Set<number>>(new Set())
  const [isCreating, setIsCreating] = useState(false)
  const [editing, setEditing] = useState<TestCase | null>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isSavingEdit, setIsSavingEdit] = useState(false)

  const loadCases = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await testCasesApi.list(projectId, {
        user_story_id: storyId,
        page: 1,
        page_size: PAGE_SIZE,
      })
      const items = res.data.items || []
      setCases(items)
      setSelectedDrafts((prev) => {
        const validIds = new Set(items.filter((c) => c.status === 'draft').map((c) => c.id))
        const next = new Set<number>()
        prev.forEach((id) => {
          if (validIds.has(id)) next.add(id)
        })
        return next
      })
    } catch {
      toast.error('Failed to load test cases')
    } finally {
      setIsLoading(false)
    }
  }, [projectId, storyId])

  useEffect(() => {
    void loadCases()
  }, [loadCases])

  useImperativeHandle(ref, () => ({ reload: loadCases }), [loadCases])

  const drafts = useMemo(() => cases.filter((c) => c.status === 'draft'), [cases])
  const readies = useMemo(() => cases.filter((c) => c.status === 'ready'), [cases])
  const deprecatedCount = useMemo(
    () => cases.filter((c) => c.status === 'deprecated').length,
    [cases]
  )

  useEffect(() => {
    onCountsChange?.({
      draft: drafts.length,
      ready: readies.length,
      total: cases.length,
    })
  }, [drafts.length, readies.length, cases.length, onCountsChange])

  const toggleDraft = (id: number) => {
    setSelectedDrafts((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAllDrafts = () => {
    if (drafts.length === 0) return
    setSelectedDrafts((prev) => {
      const allSelected = drafts.every((c) => prev.has(c.id))
      if (allSelected) return new Set()
      return new Set(drafts.map((c) => c.id))
    })
  }

  const promoteIds = useCallback(
    async (ids: number[], withUndo = true) => {
      if (ids.length === 0) return
      setPromotingIds(new Set(ids))
      try {
        const { succeeded, failed } = await testCasesApi.bulkUpdateStatus(ids, 'ready')
        if (succeeded.length > 0) {
          if (failed.length === 0) {
            if (withUndo) {
              toast.custom(
                (t) => (
                  <div className="flex items-center gap-3 rounded-lg bg-gray-900 px-4 py-3 text-sm text-white shadow-lg">
                    <CheckCircleIcon className="h-5 w-5 text-green-400" />
                    <span>
                      Moved {succeeded.length} case{succeeded.length === 1 ? '' : 's'} to Functional Testing
                    </span>
                    <button
                      type="button"
                      className="ml-2 rounded px-2 py-1 text-xs font-semibold uppercase tracking-wide text-primary-300 hover:bg-white/10"
                      onClick={() => {
                        toast.dismiss(t.id)
                        void undoPromotion(succeeded)
                      }}
                    >
                      Undo
                    </button>
                  </div>
                ),
                { duration: 5000 }
              )
            } else {
              toast.success(
                `Moved ${succeeded.length} case${succeeded.length === 1 ? '' : 's'} to Functional Testing`
              )
            }
          } else {
            toast.success(
              `Promoted ${succeeded.length} of ${ids.length}; ${failed.length} failed`
            )
          }
        } else if (failed.length > 0) {
          toast.error(failed[0].error)
        }
        setSelectedDrafts((prev) => {
          const next = new Set(prev)
          succeeded.forEach((id) => next.delete(id))
          return next
        })
        await loadCases()
      } finally {
        setPromotingIds(new Set())
      }
    },
    // undoPromotion is defined below but only used inside the toast callback
    // which runs later; referenced via closure below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [loadCases]
  )

  const undoPromotion = useCallback(
    async (ids: number[]) => {
      if (ids.length === 0) return
      const { succeeded, failed } = await testCasesApi.bulkUpdateStatus(ids, 'draft')
      if (succeeded.length > 0) {
        toast.success(
          failed.length === 0
            ? 'Promotion undone'
            : `Reverted ${succeeded.length}; ${failed.length} failed`
        )
      } else if (failed.length > 0) {
        toast.error('Failed to undo promotion')
      }
      await loadCases()
    },
    [loadCases]
  )

  const handlePromoteSelected = () => promoteIds(Array.from(selectedDrafts))
  const handlePromoteOne = (id: number) => promoteIds([id])
  const handleDemoteOne = async (id: number) => {
    setPromotingIds(new Set([id]))
    try {
      const { succeeded, failed } = await testCasesApi.bulkUpdateStatus([id], 'draft')
      if (succeeded.length) toast.success('Moved back to draft')
      else if (failed.length) toast.error(failed[0].error)
      await loadCases()
    } finally {
      setPromotingIds(new Set())
    }
  }

  const handleCreateManual = async () => {
    setIsCreating(true)
    try {
      // Manual cases authored inside a story land as DRAFT so they follow the
      // same promotion flow as LLM-generated cases. The sibling flow on the
      // Cases tab creates them READY directly — see CasesTab.handleCreateManualCase.
      const res = await testCasesApi.create({
        project_id: projectId,
        user_story_id: storyId,
        title: 'Untitled manual case',
        description: '',
        priority: 'medium',
        category: 'regression',
        status: 'draft',
        is_generated: false,
      })
      toast.success('Manual case created (draft)')
      setEditing(res.data)
      setIsEditOpen(true)
      await loadCases()
    } catch {
      toast.error('Failed to create case')
    } finally {
      setIsCreating(false)
    }
  }

  const handleDelete = async (tc: TestCase) => {
    if (!window.confirm(`Delete "${tc.title}"?`)) return
    try {
      await testCasesApi.delete(tc.id)
      toast.success('Deleted')
      await loadCases()
    } catch (err: unknown) {
      const detail =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Delete failed')
    }
  }

  const handleSaveEdit = async () => {
    if (!editing) return
    setIsSavingEdit(true)
    try {
      await testCasesApi.update(editing.id, editing)
      toast.success('Updated')
      setIsEditOpen(false)
      await loadCases()
    } catch {
      toast.error('Update failed')
    } finally {
      setIsSavingEdit(false)
    }
  }

  const promoteSelectedDisabled =
    selectedDrafts.size === 0 || promotingIds.size > 0

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Test cases</CardTitle>
          <p className="text-sm text-gray-500">
            {drafts.length} draft · {readies.length} in Functional Testing
            {deprecatedCount > 0 ? ` · ${deprecatedCount} deprecated` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadCases()}
            disabled={isLoading}
          >
            <ArrowPathIcon
              className={`mr-1 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
          <Button size="sm" onClick={handleCreateManual} disabled={isCreating}>
            <PlusIcon className="mr-1 h-4 w-4" />
            New manual case
          </Button>
        </div>
      </div>

      <Card padding="none">
        <div className="flex flex-col gap-2 border-b border-gray-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <ClockIcon className="h-4 w-4 text-amber-500" />
            Draft ({drafts.length})
            <span className="text-xs font-normal text-gray-500">
              — review, then promote to Functional Testing
            </span>
          </div>
          <Button
            size="sm"
            onClick={handlePromoteSelected}
            disabled={promoteSelectedDisabled}
            isLoading={promotingIds.size > 0 && selectedDrafts.size > 0}
          >
            <ArrowUpOnSquareIcon className="mr-1 h-4 w-4" />
            Move to Functional Testing ({selectedDrafts.size})
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <ArrowPathIcon className="h-6 w-6 animate-spin text-gray-300" />
          </div>
        ) : drafts.length === 0 ? (
          <div className="py-10 text-center text-sm text-gray-500">
            No draft cases. Generate tests from this story or add a manual one.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="w-10 px-3 py-2">
                    <input
                      type="checkbox"
                      className="rounded"
                      checked={
                        drafts.length > 0 &&
                        drafts.every((c) => selectedDrafts.has(c.id))
                      }
                      onChange={toggleAllDrafts}
                    />
                  </th>
                  <th className="w-16 px-3 py-2">Case #</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Priority</th>
                  <th className="px-3 py-2">Steps</th>
                  <th className="w-36 px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {drafts.map((tc) => (
                  <tr key={tc.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        className="rounded"
                        checked={selectedDrafts.has(tc.id)}
                        onChange={() => toggleDraft(tc.id)}
                      />
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-500">
                      #{tc.case_number ?? tc.id}
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/projects/${projectId}/functional-testing/cases/${tc.id}`}
                        className="font-medium text-primary-600 hover:underline"
                      >
                        {tc.title}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_PILL[tc.priority]}`}
                      >
                        {tc.priority}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600">{tc.steps_count}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="xs"
                          variant="outline"
                          onClick={() => handlePromoteOne(tc.id)}
                          disabled={promotingIds.has(tc.id)}
                          title="Move to Functional Testing"
                        >
                          <ArrowUpOnSquareIcon className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => {
                            setEditing(tc)
                            setIsEditOpen(true)
                          }}
                        >
                          <PencilIcon className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="xs"
                          variant="ghost"
                          className="text-red-600 hover:bg-red-50"
                          onClick={() => void handleDelete(tc)}
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card padding="none">
        <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3 text-sm font-medium text-gray-700">
          <CheckCircleIcon className="h-4 w-4 text-green-500" />
          In Functional Testing ({readies.length})
          <span className="text-xs font-normal text-gray-500">
            — ready to execute
          </span>
        </div>
        {readies.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-500">
            Nothing promoted yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="w-16 px-3 py-2">Case #</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Priority</th>
                  <th className="px-3 py-2">Steps</th>
                  <th className="w-36 px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {readies.map((tc) => (
                  <tr key={tc.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-mono text-xs text-gray-500">
                      #{tc.case_number ?? tc.id}
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/projects/${projectId}/functional-testing/cases/${tc.id}`}
                        className="font-medium text-primary-600 hover:underline"
                      >
                        {tc.title}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_PILL[tc.priority]}`}
                      >
                        {tc.priority}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600">{tc.steps_count}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => void handleDemoteOne(tc.id)}
                          disabled={promotingIds.has(tc.id)}
                          title="Move back to draft"
                        >
                          <ArrowUturnLeftIcon className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => {
                            setEditing(tc)
                            setIsEditOpen(true)
                          }}
                        >
                          <PencilIcon className="h-3.5 w-3.5" />
                        </Button>
                        <Link
                          to={`/projects/${projectId}/functional-testing/cases/${tc.id}`}
                          className="inline-flex items-center rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                          title="Open in Functional Testing"
                        >
                          <ArrowUturnRightIcon className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <TestCaseEditModal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        testCase={editing}
        setTestCase={(tc) => setEditing(tc)}
        onSave={handleSaveEdit}
        isSaving={isSavingEdit}
      />
    </div>
  )
})
