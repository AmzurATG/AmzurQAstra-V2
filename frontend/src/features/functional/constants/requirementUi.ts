import type { GapAnalysisRunStatus, Requirement } from '../types'

export const requirementSourceConfig: Record<
  Requirement['source'] | 'confluence',
  { label: string; color: string }
> = {
  upload: { label: 'Upload', color: 'bg-green-100 text-green-700' },
  jira: { label: 'Jira', color: 'bg-blue-100 text-blue-700' },
  azure_devops: { label: 'Azure DevOps', color: 'bg-purple-100 text-purple-700' },
  confluence: { label: 'Confluence', color: 'bg-teal-100 text-teal-700' },
  manual: { label: 'Manual', color: 'bg-gray-100 text-gray-700' },
}

export const requirementStatusConfig: Record<
  Requirement['status'],
  { label: string; color: string }
> = {
  pending: { label: 'Pending', color: 'bg-yellow-100 text-yellow-700' },
  processed: { label: 'Processed', color: 'bg-green-100 text-green-700' },
  error: { label: 'Error', color: 'bg-red-100 text-red-700' },
}

export const analysisRunStatusConfig: Record<
  GapAnalysisRunStatus,
  { label: string; color: string }
> = {
  pending: { label: 'Pending', color: 'bg-yellow-100 text-yellow-800' },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-800' },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-800' },
}

/** Product copy: feature name in Title Case */
export const GAP_ANALYSIS_LABEL = 'Gap Analysis'
