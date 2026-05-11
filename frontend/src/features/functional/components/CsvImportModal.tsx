import React, { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  ArrowDownTrayIcon,
  DocumentArrowUpIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import axios from 'axios'

import { Button } from '@common/components/ui/Button'
import { testCasesApi } from '../api'
import type { TestCaseCsvImportResponse } from '../types'

const MAX_FILE_BYTES = 5 * 1024 * 1024 // 5 MiB — mirrors backend MAX_CSV_BYTES

function importCsvErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status
    const raw = err.response?.data
    if (raw && typeof raw === 'object' && 'detail' in raw) {
      const d = (raw as { detail: unknown }).detail
      if (typeof d === 'string') return d
      if (Array.isArray(d)) {
        return d
          .map((item) =>
            typeof item === 'object' && item !== null && 'msg' in item
              ? String((item as { msg: unknown }).msg)
              : JSON.stringify(item)
          )
          .join('; ')
      }
    }
    if (!err.response) {
      return err.message || 'Network error — check API URL and that the server is running.'
    }
    if (status === 403) return 'You do not have access to this project.'
    if (status === 413) return 'File too large for the server.'
    return `Request failed (HTTP ${status}).`
  }
  if (err instanceof Error) return err.message
  return 'Import request failed'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface FileEntry {
  file: File
  result: TestCaseCsvImportResponse | null
  error: string | null
  done: boolean
}

interface CsvImportModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: number
  /** Called after a non–dry-run import. Use wroteCases to jump to the page that contains new rows. */
  onImported: (detail: { wroteCases: boolean }) => void | Promise<void>
}

export const CsvImportModal: React.FC<CsvImportModalProps> = ({
  isOpen,
  onClose,
  projectId,
  onImported,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<FileEntry[]>([])
  const [dryRun, setDryRun] = useState(false)
  const [importMode, setImportMode] = useState<'strict' | 'permissive'>('strict')
  const [busy, setBusy] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setFiles([])
      setBusy(false)
      setDragActive(false)
    }
  }, [isOpen])

  const handleClose = () => {
    if (!busy) {
      setFiles([])
      onClose()
    }
  }

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const list = Array.from(incoming)
    const accepted: FileEntry[] = []
    for (const f of list) {
      const name = f.name.toLowerCase()
      if (!name.endsWith('.csv') && f.type && !f.type.includes('csv') && !f.type.includes('text')) {
        toast.error(`${f.name}: not a CSV file — skipped`)
        continue
      }
      if (f.size > MAX_FILE_BYTES) {
        toast.error(`${f.name}: exceeds 5 MB limit — skipped`)
        continue
      }
      accepted.push({ file: f, result: null, error: null, done: false })
    }
    if (accepted.length) {
      setFiles((prev) => {
        // Deduplicate by name+size — avoid adding the same file twice
        const existing = new Set(prev.map((e) => `${e.file.name}|${e.file.size}`))
        return [...prev, ...accepted.filter((e) => !existing.has(`${e.file.name}|${e.file.size}`))]
      })
    }
  }, [])

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const downloadTemplate = async () => {
    try {
      const res = await testCasesApi.getCsvTemplate()
      const blob = new Blob([res.data as unknown as string], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'qastra-test-cases-template.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Could not download template')
    }
  }

  const runImport = async () => {
    const pending = files.filter((e) => !e.done)
    if (pending.length === 0) {
      toast.error('Add at least one CSV file to import')
      return
    }
    setBusy(true)

    let totalCreatedCases = 0
    let anyWroteCases = false

    for (let i = 0; i < files.length; i++) {
      const entry = files[i]
      if (entry.done) continue

      try {
        const fd = new FormData()
        fd.append('project_id', String(projectId))
        fd.append('dry_run', dryRun ? 'true' : 'false')
        fd.append('import_mode', importMode)
        fd.append('file', entry.file)
        const res = await testCasesApi.importCsv(fd)
        const data = res.data

        setFiles((prev) =>
          prev.map((e, idx) => (idx === i ? { ...e, result: data, error: null, done: true } : e))
        )

        if (!data.dry_run && data.created_cases > 0) {
          totalCreatedCases += data.created_cases
          anyWroteCases = true
        }
      } catch (err) {
        const msg = importCsvErrorMessage(err)
        setFiles((prev) =>
          prev.map((e, idx) => (idx === i ? { ...e, result: null, error: msg, done: true } : e))
        )
      }
    }

    setBusy(false)

    if (!dryRun) {
      await onImported({ wroteCases: anyWroteCases })
      if (anyWroteCases) {
        toast.success(
          `Import complete — ${totalCreatedCases} case(s) created across ${
            files.filter((e) => e.done && e.result && e.result.created_cases > 0).length
          } file(s).`
        )
      }
    } else {
      toast('Dry-run finished — review results below.', { icon: '🔍' })
    }
  }

  const allDone = files.length > 0 && files.every((e) => e.done)
  const pendingCount = files.filter((e) => !e.done).length
  const hasFiles = files.length > 0

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-xl transform rounded-xl bg-white p-6 shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <DocumentArrowUpIcon className="w-5 h-5 text-primary-600" />
                      Import test cases (CSV)
                    </Dialog.Title>
                    <p className="text-sm text-gray-500 mt-1">
                      One or more UTF-8 CSVs (max <strong>5 MB</strong> each). Same{' '}
                      <code className="text-xs bg-gray-100 px-1 rounded">case_key</code> on multiple
                      rows = one test case. Imported cases default to{' '}
                      <strong className="text-gray-700">draft</strong> status.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-40"
                    onClick={handleClose}
                    disabled={busy}
                    aria-label="Close"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  {/* Template download */}
                  <Button variant="outline" type="button" className="w-full" onClick={downloadTemplate}>
                    <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
                    Download template + format notes
                  </Button>

                  {/* Drop zone */}
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      CSV files{' '}
                      <span className="text-xs font-normal text-gray-400">(up to 5 MB each)</span>
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,text/csv,text/plain"
                      multiple
                      className="sr-only"
                      onChange={(e) => {
                        if (e.target.files) addFiles(e.target.files)
                        e.target.value = ''
                      }}
                    />
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => fileInputRef.current?.click()}
                      onDragEnter={(e) => {
                        e.preventDefault()
                        setDragActive(true)
                      }}
                      onDragOver={(e) => {
                        e.preventDefault()
                        setDragActive(true)
                      }}
                      onDragLeave={(e) => {
                        e.preventDefault()
                        if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                          setDragActive(false)
                        }
                      }}
                      onDrop={(e) => {
                        e.preventDefault()
                        setDragActive(false)
                        if (e.dataTransfer.files) addFiles(e.dataTransfer.files)
                      }}
                      className={`w-full rounded-xl border-2 border-dashed px-4 py-6 text-center transition-colors disabled:opacity-50 ${
                        dragActive
                          ? 'border-primary-500 bg-primary-50/80'
                          : 'border-gray-300 bg-gray-50/50 hover:border-primary-300 hover:bg-primary-50/40'
                      }`}
                    >
                      <DocumentArrowUpIcon className="w-9 h-9 mx-auto text-gray-400 mb-2" />
                      <div className="text-sm text-gray-600">
                        <span className="font-medium text-primary-600">Drop files here</span>
                        {' · '}
                        <span>or click to browse</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">Multiple files allowed</p>
                    </button>
                  </div>

                  {/* File queue */}
                  {hasFiles && (
                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {files.map((entry, idx) => (
                        <div
                          key={`${entry.file.name}|${entry.file.size}|${idx}`}
                          className={`rounded-lg border px-3 py-2 text-sm ${
                            entry.done && entry.error
                              ? 'border-red-200 bg-red-50'
                              : entry.done && entry.result
                              ? entry.result.errors.length > 0 && importMode === 'strict'
                                ? 'border-red-200 bg-red-50'
                                : 'border-green-200 bg-green-50'
                              : 'border-gray-200 bg-gray-50'
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            {entry.done && entry.error ? (
                              <ExclamationCircleIcon className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                            ) : entry.done ? (
                              <CheckCircleIcon className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                            ) : (
                              <div className="w-4 h-4 rounded-full border-2 border-gray-300 shrink-0 mt-0.5" />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 truncate">{entry.file.name}</p>
                              <p className="text-xs text-gray-500">{formatFileSize(entry.file.size)}</p>

                              {/* Result summary inline */}
                              {entry.done && entry.result && (
                                <div className="mt-1 space-y-1">
                                  <p className="text-xs text-gray-700">{entry.result.message}</p>
                                  <p className="text-xs text-gray-500">
                                    Cases: {entry.result.created_cases} · Steps:{' '}
                                    {entry.result.created_steps}
                                    {entry.result.skipped_case_groups
                                      ? ` · Skipped: ${entry.result.skipped_case_groups}`
                                      : ''}
                                    {entry.result.dry_run && (
                                      <span className="ml-1 px-1 rounded bg-amber-100 text-amber-800">
                                        dry run
                                      </span>
                                    )}
                                  </p>
                                  {entry.result.warnings.length > 0 && (
                                    <details className="text-xs">
                                      <summary className="cursor-pointer text-amber-700 font-medium">
                                        {entry.result.warnings.length} warning(s)
                                      </summary>
                                      <ul className="list-disc pl-4 text-amber-900 space-y-0.5 mt-1">
                                        {entry.result.warnings.slice(0, 10).map((w, i) => (
                                          <li key={i}>
                                            Row {w.row}
                                            {w.column ? ` (${w.column})` : ''}: {w.message}
                                          </li>
                                        ))}
                                        {entry.result.warnings.length > 10 && (
                                          <li>… and {entry.result.warnings.length - 10} more</li>
                                        )}
                                      </ul>
                                    </details>
                                  )}
                                  {entry.result.errors.length > 0 && (
                                    <details className="text-xs" open>
                                      <summary className="cursor-pointer text-red-700 font-medium">
                                        {entry.result.errors.length} error(s)
                                      </summary>
                                      <ul className="list-disc pl-4 text-red-900 space-y-0.5 mt-1">
                                        {entry.result.errors.slice(0, 10).map((e, i) => (
                                          <li key={i}>
                                            Row {e.row}
                                            {e.column ? ` (${e.column})` : ''}: {e.message}
                                          </li>
                                        ))}
                                        {entry.result.errors.length > 10 && (
                                          <li>… and {entry.result.errors.length - 10} more</li>
                                        )}
                                      </ul>
                                    </details>
                                  )}
                                </div>
                              )}

                              {entry.done && entry.error && (
                                <p className="text-xs text-red-700 mt-1">{entry.error}</p>
                              )}
                            </div>

                            {!busy && (
                              <button
                                type="button"
                                onClick={() => removeFile(idx)}
                                className="text-gray-400 hover:text-red-500 shrink-0"
                                aria-label="Remove file"
                              >
                                <TrashIcon className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {dryRun && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      <strong>Validate only</strong> is on — nothing will be saved. Uncheck to write
                      cases to the database.
                    </div>
                  )}

                  <label className="flex items-start gap-3 text-sm text-gray-700 cursor-pointer rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                      className="mt-0.5 rounded border-gray-300"
                      disabled={busy}
                    />
                    <span>
                      <span className="font-medium text-gray-900">Validate only (dry run)</span>
                      <span className="block text-gray-500 text-xs mt-0.5">
                        Check CSV(s) without inserting rows. Turn off to import into the project.
                      </span>
                    </span>
                  </label>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Import mode</label>
                    <select
                      value={importMode}
                      disabled={busy}
                      onChange={(e) =>
                        setImportMode(e.target.value === 'permissive' ? 'permissive' : 'strict')
                      }
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                    >
                      <option value="strict">
                        Strict — abort entire file if anything is invalid
                      </option>
                      <option value="permissive">
                        Permissive — skip invalid cases; import the rest
                      </option>
                    </select>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap gap-2 justify-end pt-2">
                    <Button variant="outline" type="button" onClick={handleClose} disabled={busy}>
                      {allDone ? 'Close' : 'Cancel'}
                    </Button>
                    {allDone && !dryRun && (
                      <Button
                        variant="outline"
                        type="button"
                        onClick={() => setFiles((prev) => prev.map((e) => ({ ...e, done: false, result: null, error: null })))}
                        disabled={busy}
                      >
                        Re-import all
                      </Button>
                    )}
                    <Button
                      type="button"
                      onClick={runImport}
                      disabled={busy || pendingCount === 0}
                      isLoading={busy}
                    >
                      {busy
                        ? 'Working…'
                        : dryRun
                        ? `Validate ${pendingCount} file${pendingCount !== 1 ? 's' : ''}`
                        : `Import ${pendingCount} file${pendingCount !== 1 ? 's' : ''}`}
                    </Button>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
