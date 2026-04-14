import { useCallback, useState } from 'react'
import toast from 'react-hot-toast'
import { userStoriesApi } from '../api'

type Options = {
  /** Called after successful generation or regeneration */
  onSuccess: () => void | Promise<void>
}

/**
 * Handles LLM test generation for a user story: blocks duplicates unless
 * `forceRegenerate` is true, and surfaces the server "already_exists" message in a dialog.
 */
export function useUserStoryTestGeneration(projectId: number | undefined, { onSuccess }: Options) {
  const [generatingStoryId, setGeneratingStoryId] = useState<number | null>(null)
  const [infoDialogOpen, setInfoDialogOpen] = useState(false)
  const [infoMessage, setInfoMessage] = useState('')

  const runGenerate = useCallback(
    async (storyId: number, forceRegenerate: boolean) => {
      if (!projectId) return
      setGeneratingStoryId(storyId)
      try {
        const res = await userStoriesApi.generateTests(projectId, storyId, {
          include_steps: true,
          force_regenerate: forceRegenerate,
        })
        const data = res.data

        if (!data.success && data.code === 'already_exists') {
          setInfoMessage(
            data.error ||
              'Test cases are already generated for this user story. Use Regenerate to replace them.'
          )
          setInfoDialogOpen(true)
          return
        }

        if (data.success) {
          const n = data.test_cases_created
          if (n === 0 && forceRegenerate) {
            toast.success('Previous test cases were removed; no new cases were generated.')
          } else if (n === 0) {
            toast.success('No new test cases were added.')
          } else {
            toast.success(`Generated ${n} test case${n === 1 ? '' : 's'}.`)
          }
          await onSuccess()
        } else {
          toast.error(data.error || 'Failed to generate tests')
        }
      } catch (error: unknown) {
        const message =
          error && typeof error === 'object' && 'response' in error
            ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined
        toast.error(message || 'Failed to generate tests')
      } finally {
        setGeneratingStoryId(null)
      }
    },
    [projectId, onSuccess]
  )

  return {
    generatingStoryId,
    runGenerate,
    infoDialogOpen,
    infoMessage,
    closeInfoDialog: () => setInfoDialogOpen(false),
  }
}
