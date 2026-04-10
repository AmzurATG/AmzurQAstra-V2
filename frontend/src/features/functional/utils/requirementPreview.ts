import type { Requirement } from '../types'

export function isPdfRequirement(r: Pick<Requirement, 'file_type' | 'file_name'>): boolean {
  const t = (r.file_type || '').toLowerCase()
  if (t.includes('pdf')) return true
  return (r.file_name || '').toLowerCase().endsWith('.pdf')
}

export function isWordRequirement(r: Pick<Requirement, 'file_type' | 'file_name'>): boolean {
  const t = (r.file_type || '').toLowerCase()
  if (t.includes('word') || t.includes('msword') || t.includes('wordprocessingml')) return true
  const n = (r.file_name || '').toLowerCase()
  return n.endsWith('.docx') || n.endsWith('.doc')
}

export function isPlainTextRequirement(r: Pick<Requirement, 'file_type' | 'file_name'>): boolean {
  const t = (r.file_type || '').toLowerCase()
  if (t.includes('text/plain') || t.includes('text/markdown')) return true
  const n = (r.file_name || '').toLowerCase()
  return n.endsWith('.txt') || n.endsWith('.md') || n.endsWith('.markdown')
}

export function canBrowserPreviewPdf(r: Pick<Requirement, 'file_type' | 'file_name' | 'file_path'>): boolean {
  return !!r.file_path && isPdfRequirement(r)
}
