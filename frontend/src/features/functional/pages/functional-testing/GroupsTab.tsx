import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Squares2X2Icon, PhotoIcon } from '@heroicons/react/24/outline'

import { Button } from '@common/components/ui/Button'
import { Card } from '@common/components/ui/Card'

import { useRequiredActiveTestRun } from '../../context/ActiveTestRunProvider'
import { fetchScreenshotBlobUrl } from '../../utils/screenshotFetch'
import type { CompletedCaseResult } from '../../types'

function basename(path?: string | null): string {
  if (!path) return ''
  const parts = path.split('/')
  return parts[parts.length - 1] || ''
}

function GroupCaseThumb({
  runId,
  result,
}: {
  runId: number
  result: CompletedCaseResult
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const filename = basename(result.screenshot_path)

  useEffect(() => {
    if (!filename || !runId) return
    let revoked: string | null = null
    let cancelled = false
    fetchScreenshotBlobUrl(runId, result.test_result_id, filename)
      .then((u) => {
        if (cancelled) {
          URL.revokeObjectURL(u)
          return
        }
        revoked = u
        setUrl(u)
      })
      .catch(() => setFailed(true))
    return () => {
      cancelled = true
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [runId, result.test_result_id, filename])

  const ok = result.status === 'passed'

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <div className="aspect-video bg-gray-100 flex items-center justify-center">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={result.title} className="w-full h-full object-cover" />
        ) : failed || !filename ? (
          <PhotoIcon className="w-8 h-8 text-gray-300" />
        ) : (
          <div className="w-full h-full animate-pulse bg-gray-200" />
        )}
      </div>
      <div className="p-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-gray-800 truncate">{result.title}</span>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold shrink-0 ${
              ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}
          >
            {result.status}
          </span>
        </div>
        <p className="text-[10px] text-gray-400 mt-0.5">Case #{result.test_case_id}</p>
      </div>
    </div>
  )
}

export default function GroupsTab() {
  const { projectId } = useParams<{ projectId: string }>()
  const { activeRunId, progress } = useRequiredActiveTestRun()
  const base = `/projects/${projectId}/functional-testing`

  if (!progress || (!progress.groups?.length && !progress.completed_results?.length)) {
    return (
      <Card className="py-12 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
          <Squares2X2Icon className="h-6 w-6 text-gray-400" />
        </div>
        <h3 className="mt-4 text-base font-semibold text-gray-900">No execution groups yet</h3>
        <p className="mt-1 text-sm text-gray-500">
          Select cases in Test Cases and run them. The orchestrator groups shared-login flows,
          and each group&apos;s screenshots appear here.
        </p>
        <div className="mt-6">
          <Link to={`${base}/cases`}>
            <Button>Go to Test Cases</Button>
          </Link>
        </div>
      </Card>
    )
  }

  const groups = progress.groups || []
  const resultsByGroup = new Map<string, CompletedCaseResult[]>()
  const ungrouped: CompletedCaseResult[] = []
  for (const r of progress.completed_results || []) {
    const gid = r.group_id
    if (gid) {
      const arr = resultsByGroup.get(gid) || []
      arr.push(r)
      resultsByGroup.set(gid, arr)
    } else {
      ungrouped.push(r)
    }
  }

  const renderGroup = (
    key: string,
    title: string,
    caseIds: number[] | undefined,
    results: CompletedCaseResult[]
  ) => {
    const passed = results.filter((r) => r.status === 'passed').length
    return (
      <Card key={key} className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
            <p className="text-xs text-gray-500">
              {caseIds?.length ?? results.length} case{(caseIds?.length ?? results.length) === 1 ? '' : 's'}
              {results.length > 0 && ` · ${passed}/${results.length} passed`}
            </p>
          </div>
        </div>
        {results.length === 0 ? (
          <p className="text-xs text-gray-400 py-4">Waiting for cases in this group to finish…</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {results.map((r) => (
              <GroupCaseThumb key={r.test_result_id} runId={activeRunId ?? 0} result={r} />
            ))}
          </div>
        )}
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {groups.map((g) =>
        renderGroup(g.group_id, g.title || g.group_id, g.case_ids, resultsByGroup.get(g.group_id) || [])
      )}
      {ungrouped.length > 0 && renderGroup('__ungrouped', 'Other cases', undefined, ungrouped)}
    </div>
  )
}
