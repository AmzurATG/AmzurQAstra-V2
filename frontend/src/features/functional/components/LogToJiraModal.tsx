import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Link } from 'react-router-dom'
import { XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { Button } from '@common/components/ui/Button'
import { testRunsApi, userStoriesApi } from '../api'
import type { CompletedCaseResult, ProjectIntegrationInfo, Sprint } from '../types'

interface LogToJiraModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: number
  runId: number
  runNumber?: number | null
  result: CompletedCaseResult
  onLogged: (payload: { key: string; url?: string | null }) => void
}

export function LogToJiraModal({
  isOpen,
  onClose,
  projectId,
  runId,
  runNumber,
  result,
  onLogged,
}: LogToJiraModalProps) {
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [integration, setIntegration] = useState<ProjectIntegrationInfo | null>(null)
  const [sprints, setSprints] = useState<Sprint[]>([])
  const [sprintId, setSprintId] = useState<string>('') // '' = backlog
  const [summary, setSummary] = useState('')
  const [priority, setPriority] = useState('Medium')
  const [attachScreenshots, setAttachScreenshots] = useState(true)
  const [previewOpen, setPreviewOpen] = useState(false)

  const projectKey = integration?.config?.project_key || integration?.config?.project_name
  const projectLabel =
    integration?.config?.project_name && integration?.config?.project_key
      ? `${integration.config.project_name} (${integration.config.project_key})`
      : projectKey || '—'

  const defaultSummary = useMemo(
    () => `[QAstra] ${result.title || 'Test case'} failed`,
    [result.title]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const integRes = await userStoriesApi.getIntegrations(projectId)
      const jira = (integRes.data || []).find(
        (i) => i.integration_type === 'jira' && i.is_enabled
      )
      setIntegration(jira || null)
      if (!jira) {
        setSprints([])
        return
      }
      try {
        const sprintRes = await userStoriesApi.getSprints(projectId, 'jira')
        const list = (sprintRes.data || []).filter((s) =>
          ['active', 'future'].includes(String(s.state || '').toLowerCase())
        )
        setSprints(list.length ? list : sprintRes.data || [])
      } catch {
        setSprints([])
      }
    } catch {
      setError('Could not load Jira integration.')
      setIntegration(null)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (!isOpen) return
    setSummary(defaultSummary)
    setPriority('Medium')
    setSprintId('')
    setAttachScreenshots(true)
    setPreviewOpen(false)
    setSubmitting(false)
    void load()
  }, [isOpen, defaultSummary, load])

  const handleSubmit = async () => {
    if (!integration) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await testRunsApi.logResultToJira(runId, result.test_result_id, {
        sprint_id: sprintId ? Number(sprintId) : null,
        summary: summary.trim() || defaultSummary,
        priority,
        attach_screenshots: attachScreenshots,
      })
      toast.success(`Logged to Jira as ${res.data.key}`)
      onLogged({ key: res.data.key, url: res.data.url })
      onClose()
    } catch (e: unknown) {
      const detail =
        e && typeof e === 'object' && 'response' in e
          ? (e as { response?: { data?: { detail?: unknown }; status?: number } }).response
          : undefined
      const d = detail?.data?.detail
      if (detail?.status === 409 && d && typeof d === 'object' && d !== null && 'key' in d) {
        const payload = d as { key: string; url?: string; message?: string }
        toast.error(payload.message || 'Already logged to Jira')
        onLogged({ key: payload.key, url: payload.url })
        onClose()
        return
      }
      const msg =
        typeof d === 'string'
          ? d
          : d && typeof d === 'object' && d !== null && 'message' in d
            ? String((d as { message: string }).message)
            : 'Failed to create Jira bug'
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const failedStep = (result.step_results || []).find((s) => s.status === 'failed')
  const already = result.jira_bug_key

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-lg transform overflow-hidden rounded-xl bg-white p-6 shadow-xl transition-all">
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Log to Jira
                    </Dialog.Title>
                    <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                      {result.title}
                      <span className="text-gray-400">
                        {' '}
                        · Run #{runNumber ?? runId}
                      </span>
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-md p-1 text-gray-400 hover:text-gray-600"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {loading ? (
                  <div className="flex items-center gap-2 py-8 text-sm text-gray-500 justify-center">
                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                    Loading Jira…
                  </div>
                ) : already ? (
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700">
                      This failure was already filed as{' '}
                      {result.jira_bug_url ? (
                        <a
                          href={result.jira_bug_url}
                          target="_blank"
                          rel="noreferrer"
                          className="font-semibold text-primary-600 hover:underline"
                        >
                          {already}
                        </a>
                      ) : (
                        <span className="font-semibold">{already}</span>
                      )}
                      .
                    </p>
                    <div className="flex justify-end">
                      <Button variant="outline" onClick={onClose}>
                        Close
                      </Button>
                    </div>
                  </div>
                ) : !integration ? (
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700">
                      Jira is not connected for this project. Connect it under Integrations, then try
                      again.
                    </p>
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" onClick={onClose}>
                        Cancel
                      </Button>
                      <Link to={`/projects/${projectId}/integrations`}>
                        <Button>Open Integrations</Button>
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Jira project
                      </label>
                      <p className="text-sm font-medium text-gray-900">{projectLabel}</p>
                    </div>

                    <div>
                      <label
                        htmlFor="log-jira-sprint"
                        className="block text-xs font-medium text-gray-500 mb-1"
                      >
                        Sprint
                      </label>
                      <select
                        id="log-jira-sprint"
                        value={sprintId}
                        onChange={(e) => setSprintId(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      >
                        <option value="">Backlog (no sprint)</option>
                        {sprints.map((s) => (
                          <option key={s.id} value={String(s.id)}>
                            {s.name}
                            {s.state ? ` · ${s.state}` : ''}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 text-[11px] text-gray-500">
                        Leave as Backlog to create the bug without assigning a sprint.
                      </p>
                    </div>

                    <div>
                      <label
                        htmlFor="log-jira-summary"
                        className="block text-xs font-medium text-gray-500 mb-1"
                      >
                        Summary
                      </label>
                      <input
                        id="log-jira-summary"
                        value={summary}
                        onChange={(e) => setSummary(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="log-jira-priority"
                        className="block text-xs font-medium text-gray-500 mb-1"
                      >
                        Priority
                      </label>
                      <select
                        id="log-jira-priority"
                        value={priority}
                        onChange={(e) => setPriority(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      >
                        {['Highest', 'High', 'Medium', 'Low', 'Lowest'].map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </select>
                    </div>

                    <label className="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={attachScreenshots}
                        onChange={(e) => setAttachScreenshots(e.target.checked)}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      Attach evidence screenshots
                    </label>

                    <div>
                      <button
                        type="button"
                        onClick={() => setPreviewOpen((v) => !v)}
                        className="text-xs font-medium text-primary-600 hover:underline"
                      >
                        {previewOpen ? 'Hide preview' : 'Show repro preview'}
                      </button>
                      {previewOpen && (
                        <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700 space-y-2 max-h-40 overflow-y-auto">
                          <p>
                            <span className="font-semibold">Failed step: </span>
                            {failedStep
                              ? `${failedStep.step_number}. ${failedStep.description || '—'}`
                              : '—'}
                          </p>
                          {(result.user_message || result.error_message) && (
                            <p>
                              <span className="font-semibold">Error: </span>
                              {result.user_message || result.error_message}
                            </p>
                          )}
                          <p className="text-gray-500">
                            Full steps, expected/actual, and environment are included in the Jira
                            description.
                          </p>
                        </div>
                      )}
                    </div>

                    {error && (
                      <p className="text-sm text-red-600 rounded-md border border-red-100 bg-red-50 px-3 py-2">
                        {error}
                      </p>
                    )}

                    <div className="flex justify-end gap-2 pt-1">
                      <Button variant="outline" onClick={onClose} disabled={submitting}>
                        Cancel
                      </Button>
                      <Button onClick={handleSubmit} isLoading={submitting}>
                        Create bug
                      </Button>
                    </div>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
