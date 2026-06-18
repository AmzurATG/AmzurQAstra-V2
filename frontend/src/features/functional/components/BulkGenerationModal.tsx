import { Fragment, useCallback, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  XMarkIcon,
  SparklesIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { Button } from '@common/components/ui/Button'
import { userStoriesApi } from '../api'
import { useBulkGenerationJob } from '../hooks/useBulkGenerationJob'
import type { GenerationProfile, GenerationJobStatusResponse, StoryCoverageItem } from '../types'

interface BulkGenerationModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: number
  selectedStoryIds: number[]
  onComplete: () => void
  initialProfile?: GenerationProfile
}

const PROFILES: { id: GenerationProfile; label: string; description: string }[] = [
  { id: 'light', label: 'Light', description: '~5 cases/story — quick coverage' },
  { id: 'standard', label: 'Standard', description: '~10 cases/story — recommended' },
  { id: 'comprehensive', label: 'Comprehensive', description: '~20 cases/story — full AC matrix' },
  {
    id: 'production_web',
    label: 'Production Web',
    description: '~25 cases/story — comprehensive + UI inventory rows',
  },
]

const SCENARIO_COLORS: Record<string, string> = {
  positive: 'bg-green-100 text-green-700',
  negative: 'bg-red-100 text-red-700',
  boundary: 'bg-yellow-100 text-yellow-700',
  edge: 'bg-purple-100 text-purple-700',
  ui_smoke: 'bg-blue-100 text-blue-700',
}

function CoverageRow({ item }: { item: StoryCoverageItem }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-white px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-800 line-clamp-1">{item.story_title}</p>
        <div className="flex flex-shrink-0 items-center gap-2 text-xs">
          <span className="font-semibold text-indigo-600">{item.cases_created} cases</span>
          <span className={item.has_gaps ? 'text-amber-600' : 'text-green-600'}>
            {item.coverage_percent}%
          </span>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.entries(item.scenario_counts ?? {}).map(([type, count]) => (
          <span
            key={type}
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
              SCENARIO_COLORS[type] ?? 'bg-gray-100 text-gray-600'
            }`}
          >
            {count} {type}
          </span>
        ))}
      </div>
    </div>
  )
}

export function BulkGenerationModal({
  isOpen,
  onClose,
  projectId,
  selectedStoryIds,
  onComplete,
  initialProfile = 'standard',
}: BulkGenerationModalProps) {
  const [profile, setProfile] = useState<GenerationProfile>(initialProfile)
  const [isStarting, setIsStarting] = useState(false)
  const [completed, setCompleted] = useState<GenerationJobStatusResponse | null>(null)

  useEffect(() => {
    if (isOpen) {
      setProfile(initialProfile)
      setCompleted(null)
    }
  }, [isOpen, initialProfile])

  const handleComplete = useCallback(
    (report: GenerationJobStatusResponse) => {
      setCompleted(report)
      toast.success('Bulk generation complete!')
      onComplete()
    },
    [onComplete],
  )

  const { job, isPolling, startPolling } = useBulkGenerationJob(projectId, {
    onComplete: handleComplete,
    onError: (msg) => toast.error(msg),
  })

  const handleStart = async () => {
    if (selectedStoryIds.length === 0) {
      toast.error('No user stories selected. Select stories on the list or accept BRD stories first.')
      return
    }
    setIsStarting(true)
    setCompleted(null)
    try {
      const res = await userStoriesApi.bulkGenerateTests(
        projectId,
        selectedStoryIds,
        profile,
        true,
      )
      startPolling(res.data.job_id)
    } catch (err: unknown) {
      const detail =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      toast.error(
        typeof detail === 'string'
          ? detail
          : 'Failed to start bulk generation.',
      )
    } finally {
      setIsStarting(false)
    }
  }

  const handleClose = () => {
    if (!isPolling) onClose()
  }

  const isRunning = isPolling || isStarting
  const progressPct = job?.progress_percent ?? 0

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-200"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
              {/* Header */}
              <div className="flex items-center justify-between border-b px-6 py-4">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="h-5 w-5 text-indigo-500" />
                  <Dialog.Title className="text-base font-semibold text-gray-900">
                    Bulk Test Generation
                  </Dialog.Title>
                </div>
                <button
                  onClick={handleClose}
                  disabled={isPolling}
                  className="rounded-lg p-1 hover:bg-gray-100 disabled:opacity-40"
                >
                  <XMarkIcon className="h-5 w-5 text-gray-400" />
                </button>
              </div>

              <div className="px-6 py-5 space-y-5">
                {/* Story count */}
                <p className="text-sm text-gray-600">
                  Generating test cases for{' '}
                  <span className="font-semibold text-gray-900">{selectedStoryIds.length}</span> user{' '}
                  {selectedStoryIds.length === 1 ? 'story' : 'stories'}.
                </p>
                {selectedStoryIds.length === 0 && (
                  <p className="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
                    No stories selected. Close this dialog and select user stories from the list, or
                    accept generated stories from Requirements first.
                  </p>
                )}

                {/* Profile selector */}
                {!isRunning && !completed && (
                  <div>
                    <p className="mb-2 text-sm font-medium text-gray-700">Generation profile</p>
                    <div className="space-y-2">
                      {PROFILES.map((p) => (
                        <label
                          key={p.id}
                          className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                            profile === p.id
                              ? 'border-indigo-500 bg-indigo-50'
                              : 'border-gray-200 hover:bg-gray-50'
                          }`}
                        >
                          <input
                            type="radio"
                            value={p.id}
                            checked={profile === p.id}
                            onChange={() => setProfile(p.id)}
                            className="mt-0.5 text-indigo-600"
                          />
                          <div>
                            <p className="text-sm font-medium text-gray-800">{p.label}</p>
                            <p className="text-xs text-gray-500">{p.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Progress */}
                {isRunning && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">
                        {job?.current_story_title
                          ? `Generating: ${job.current_story_title}`
                          : 'Starting…'}
                      </span>
                      <span className="font-medium text-indigo-600">{progressPct}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-2 rounded-full bg-indigo-500 transition-all duration-500"
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      {job?.completed_stories ?? 0} / {job?.total_stories ?? selectedStoryIds.length} stories done
                    </p>
                  </div>
                )}

                {/* Coverage report */}
                {completed?.coverage_report && completed.coverage_report.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5">
                      <CheckCircleIcon className="h-4 w-4 text-green-500" />
                      <p className="text-sm font-medium text-gray-700">Coverage Report</p>
                    </div>
                    <div className="max-h-64 space-y-2 overflow-y-auto">
                      {(completed.coverage_report as StoryCoverageItem[]).map((item) => (
                        <CoverageRow key={item.story_id} item={item} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Error state */}
                {job?.status === 'failed' && (
                  <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                    <ExclamationCircleIcon className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>{job.error_message || 'Generation failed.'}</span>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex justify-between border-t bg-gray-50 px-6 py-4">
                <Button variant="ghost" onClick={handleClose} disabled={isPolling}>
                  {completed ? 'Close' : 'Cancel'}
                </Button>
                {!isRunning && !completed && (
                  <Button
                    onClick={handleStart}
                    isLoading={isStarting}
                    disabled={selectedStoryIds.length === 0}
                  >
                    Generate Tests
                  </Button>
                )}
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}
