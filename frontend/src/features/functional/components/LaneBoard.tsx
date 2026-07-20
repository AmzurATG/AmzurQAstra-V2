import React, { useEffect, useRef, useState } from 'react'
import type { ActiveLaneInfo, GroupProgressInfo } from '../types'

interface LaneBoardProps {
  lanes: ActiveLaneInfo[]
  groups?: GroupProgressInfo[]
  laneTarget?: number
  /** Completed and total case counts to compute live throughput + ETA. */
  completed?: number
  total?: number
}

function useThroughput(completed: number, total: number) {
  const startRef = useRef<number | null>(null)
  const [, force] = useState(0)
  useEffect(() => {
    if (startRef.current === null && completed > 0) startRef.current = Date.now()
  }, [completed])
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 5000)
    return () => clearInterval(t)
  }, [])
  if (!startRef.current || completed <= 0) return null
  const elapsedHr = (Date.now() - startRef.current) / 3_600_000
  if (elapsedHr <= 0) return null
  const perHr = completed / elapsedHr
  if (perHr <= 0) return null
  const remaining = Math.max(0, total - completed)
  const etaMin = (remaining / perHr) * 60
  return { perHr: Math.round(perHr), etaMin: Math.round(etaMin) }
}

export const LaneBoard: React.FC<LaneBoardProps> = ({
  lanes,
  groups = [],
  laneTarget = 6,
  completed = 0,
  total = 0,
}) => {
  const tput = useThroughput(completed, total)
  const slots = Array.from({ length: laneTarget }, (_, i) => {
    const laneId = i + 1
    return lanes.find((l) => (l.lane_id ?? l.worker_id) === laneId) ?? {
      worker_id: laneId,
      lane_id: laneId,
      title: 'Idle',
      step: 'Waiting for work',
      busy: false,
    }
  })

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">Browser Lanes ({laneTarget})</h3>
          {tput && (
            <span className="text-xs text-gray-500 tabular-nums">
              ~{tput.perHr} cases/hr
              {tput.etaMin > 0 && ` · ETA ${tput.etaMin < 60 ? `${tput.etaMin}m` : `${(tput.etaMin / 60).toFixed(1)}h`}`}
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {slots.map((lane) => (
            <div
              key={lane.worker_id}
              className={`rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                lane.busy !== false && lane.title !== 'Idle'
                  ? 'border-primary-200 bg-primary-50/60'
                  : 'border-gray-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-primary-700">Lane {lane.worker_id}</span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    lane.busy !== false && lane.title !== 'Idle'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {lane.busy !== false && lane.title !== 'Idle' ? 'Busy' : 'Idle'}
                </span>
              </div>
              <p className="mt-1 font-medium text-gray-800 truncate">{lane.title || '—'}</p>
              {lane.step && (
                <p className="text-xs text-gray-500 truncate mt-0.5">{lane.step}</p>
              )}
            </div>
          ))}
        </div>
      </div>
      {groups.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Execution Groups</h3>
          <div className="flex flex-wrap gap-2">
            {groups.map((g) => (
              <div
                key={g.group_id}
                className="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs"
              >
                <span className="font-semibold text-gray-700">{g.title || g.group_id}</span>
                <span className="text-gray-400 mx-1">·</span>
                <span className="text-gray-500">{g.case_ids?.length ?? 0} cases</span>
                {g.status && (
                  <span className="ml-1 text-primary-600">({g.status})</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
