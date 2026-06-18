import { useCallback, useState } from 'react'
import toast from 'react-hot-toast'
import { brdStoriesApi } from '../api'
import type { SuggestedStory } from '../types'

type Phase = 'idle' | 'generating' | 'preview' | 'accepting'

type State = {
  phase: Phase
  stories: SuggestedStory[]
  modulesIdentified: number
  error: string | null
}

type Options = {
  onAccepted?: (storyIds: number[]) => void | Promise<void>
}

/**
 * Manages the BRD → user story generation + acceptance flow.
 *
 * Usage:
 *   const { phase, stories, generateStories, acceptStories } = useBrdStoryGeneration(options)
 */
export function useBrdStoryGeneration({ onAccepted }: Options = {}) {
  const [state, setState] = useState<State>({
    phase: 'idle',
    stories: [],
    modulesIdentified: 0,
    error: null,
  })

  const generateStories = useCallback(
    async (
      projectId: number,
      requirementId: number,
      maxStories = 20,
      includeUiContext = true,
    ) => {
      setState({ phase: 'generating', stories: [], modulesIdentified: 0, error: null })
      try {
        const res = await brdStoriesApi.generateStories(
          projectId,
          requirementId,
          maxStories,
          includeUiContext,
        )
        const data = res.data
        if (!data.stories || data.stories.length === 0) {
          setState((prev) => ({
            ...prev,
            phase: 'idle',
            error: 'No stories were generated. Try with a more detailed BRD document.',
          }))
          return
        }
        setState({
          phase: 'preview',
          stories: data.stories,
          modulesIdentified: data.modules_identified,
          error: null,
        })
        toast.success(`Generated ${data.total_stories} user stories from ${data.modules_identified} modules.`)
      } catch (err: unknown) {
        const detail =
          err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined
        const msg = detail || 'Failed to generate stories from BRD.'
        setState({ phase: 'idle', stories: [], modulesIdentified: 0, error: msg })
        toast.error(msg)
      }
    },
    [],
  )

  const acceptStories = useCallback(
    async (
      projectId: number,
      requirementId: number,
      selectedIndices?: number[],
    ) => {
      setState((prev) => ({ ...prev, phase: 'accepting' }))
      try {
        const res = await brdStoriesApi.acceptStories(
          projectId,
          requirementId,
          state.stories,
          selectedIndices,
        )
        const data = res.data
        toast.success(`${data.created} user ${data.created === 1 ? 'story' : 'stories'} added to project.`)
        setState({ phase: 'idle', stories: [], modulesIdentified: 0, error: null })
        await onAccepted?.(data.story_ids)
      } catch (err: unknown) {
        const detail =
          err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined
        const msg = detail || 'Failed to accept stories.'
        setState((prev) => ({ ...prev, phase: 'preview', error: msg }))
        toast.error(msg)
      }
    },
    [state.stories, onAccepted],
  )

  const reset = useCallback(() => {
    setState({ phase: 'idle', stories: [], modulesIdentified: 0, error: null })
  }, [])

  return {
    phase: state.phase,
    stories: state.stories,
    modulesIdentified: state.modulesIdentified,
    error: state.error,
    isGenerating: state.phase === 'generating',
    isAccepting: state.phase === 'accepting',
    generateStories,
    acceptStories,
    reset,
  }
}
