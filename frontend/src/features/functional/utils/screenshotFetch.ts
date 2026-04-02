import { apiClient } from '@common/api/client'

/**
 * Load a run screenshot with Bearer auth (for use in <img> via object URL).
 * Caller should URL.revokeObjectURL when done.
 */
export async function fetchScreenshotBlobUrl(
  runId: number,
  resultId: number,
  filename: string
): Promise<string> {
  const safe = encodeURIComponent(filename)
  const res = await apiClient.get(
    `/functional/test-runs/${runId}/results/${resultId}/screenshots/${safe}`,
    { responseType: 'blob' }
  )
  return URL.createObjectURL(res.data as Blob)
}
