import React, { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  ArrowDownTrayIcon,
  DocumentArrowUpIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import axios from 'axios'

import { Button } from '@common/components/ui/Button'
import { testCasesApi } from '../api'
import type { TestCaseCsvImportResponse } from '../types'

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
  const [file, setFile] = useState<File | null>(null)
  /** Default off so imports persist to the database; use the checkbox for validate-only runs. */
  const [dryRun, setDryRun] = useState(false)
  const [importMode, setImportMode] = useState<'strict' | 'permissive'>('strict')
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState<TestCaseCsvImportResponse | null>(null)
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setFile(null)
      setLast(null)
      setBusy(false)
      setDragActive(false)
    }
  }, [isOpen])

  const resetForClose = useCallback(() => {
    setFile(null)
    setLast(null)
  }, [])

  const handleClose = () => {
    resetForClose()
    onClose()
  }

  const pickFile = (f: File | null) => {
    if (!f) {
      setFile(null)
      return
    }
    const name = f.name.toLowerCase()
    if (!name.endsWith('.csv') && f.type && !f.type.includes('csv') && !f.type.includes('text')) {
      toast.error('Please choose a .csv file (UTF-8).')
      return
    }
    setFile(f)
    setLast(null)
  }

  const downloadTemplate = async () => {
    try {
      const text = await testCasesApi.getCsvTemplate()
      const blob = new Blob([text], { type: 'text/csv;charset=utf-8' })
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
    if (!file) {
      toast.error('Choose a CSV file or drop it in the area above')
      return
    }
    setBusy(true)
    setLast(null)
    try {
      const fd = new FormData()
      fd.append('project_id', String(projectId))
      fd.append('dry_run', dryRun ? 'true' : 'false')
      fd.append('import_mode', importMode)
      fd.append('file', file)
      const res = await testCasesApi.importCsv(fd)
      const data = res.data
      setLast(data)

      if (!data.dry_run) {
        await onImported({ wroteCases: data.created_cases > 0 })
      }

      if (data.dry_run) {
        if (data.errors.length && importMode === 'strict') {
          toast.error(data.message || 'Validation failed — fix CSV and try again.')
        } else if (data.errors.length) {
          toast('Dry run finished with row notes — see below.', { icon: '⚠️' })
        } else {
          toast.success(data.message || 'Dry run OK — turn off “Validate only” to write to the database.')
        }
      } else if (data.created_cases > 0) {
        toast.success(
          data.message ||
            'Import completed — list moved to the last page (new cases have the highest case numbers).'
        )
      } else if (data.errors.length && importMode === 'strict') {
        toast.error(data.message || 'Import failed')
      } else {
        toast(data.message || 'No cases imported', { icon: 'ℹ️' })
      }
    } catch (err: unknown) {
      toast.error(importCsvErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

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
              <Dialog.Panel className="w-full max-w-lg transform rounded-xl bg-white p-6 shadow-xl transition-all">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <DocumentArrowUpIcon className="w-5 h-5 text-primary-600" />
                      Import test cases (CSV)
                    </Dialog.Title>
                    <p className="text-sm text-gray-500 mt-1">
                      One UTF-8 file: case metadata plus optional steps. Same{' '}
                      <code className="text-xs bg-gray-100 px-1 rounded">case_key</code> merges
                      rows. Empty step columns = no steps for that case. Imports are stored as{' '}
                      <strong className="font-medium text-gray-700">CSV</strong> source in the
                      list (distinct from Manual and AI).
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                    onClick={handleClose}
                    aria-label="Close"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  <Button variant="outline" type="button" className="w-full" onClick={downloadTemplate}>
                    <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
                    Download template + format notes
                  </Button>

                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">CSV file</p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,text/csv,text/plain"
                      className="sr-only"
                      onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
                    />
                    <button
                      type="button"
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
                        const dropped = e.dataTransfer.files?.[0]
                        pickFile(dropped ?? null)
                      }}
                      className={`w-full rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors ${
                        dragActive
                          ? 'border-primary-500 bg-primary-50/80'
                          : 'border-gray-300 bg-gray-50/50 hover:border-primary-300 hover:bg-primary-50/40'
                      }`}
                    >
                      <DocumentArrowUpIcon className="w-10 h-10 mx-auto text-gray-400 mb-2" />
                      {file ? (
                        <div className="space-y-1">
                          <p className="text-sm font-medium text-gray-900 break-all">{file.name}</p>
                          <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                          <p className="text-xs text-primary-600 font-medium pt-1">
                            Click or drop to replace
                          </p>
                        </div>
                      ) : (
                        <div className="text-sm text-gray-600">
                          <span className="font-medium text-primary-600">Drop a file here</span>
                          {' · '}
                          <span>or click to browse</span>
                        </div>
                      )}
                    </button>
                    {file && (
                      <div className="mt-2 flex justify-end">
                        <button
                          type="button"
                          className="text-xs text-gray-500 hover:text-red-600"
                          onClick={() => {
                            setFile(null)
                            if (fileInputRef.current) fileInputRef.current.value = ''
                          }}
                        >
                          Clear file
                        </button>
                      </div>
                    )}
                  </div>

                  {dryRun && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      <strong>Validate only</strong> is on — nothing will be saved. Uncheck it to
                      write cases to the database and refresh the list below.
                    </div>
                  )}

                  <label className="flex items-start gap-3 text-sm text-gray-700 cursor-pointer rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                      className="mt-0.5 rounded border-gray-300"
                    />
                    <span>
                      <span className="font-medium text-gray-900">Validate only (dry run)</span>
                      <span className="block text-gray-500 text-xs mt-0.5">
                        Check the CSV without inserting rows. Turn off to import into the project.
                      </span>
                    </span>
                  </label>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Import mode</label>
                    <select
                      value={importMode}
                      onChange={(e) =>
                        setImportMode(e.target.value === 'permissive' ? 'permissive' : 'strict')
                      }
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                    >
                      <option value="strict">
                        Strict — abort entire import if anything is invalid
                      </option>
                      <option value="permissive">
                        Permissive — skip invalid cases; import the rest
                      </option>
                    </select>
                  </div>

                  <div className="flex gap-2 justify-end pt-2">
                    <Button variant="outline" type="button" onClick={handleClose} disabled={busy}>
                      Close
                    </Button>
                    <Button type="button" onClick={runImport} disabled={busy || !file}>
                      {busy ? 'Working…' : dryRun ? 'Run validation' : 'Import to database'}
                    </Button>
                  </div>

                  {last && (
                    <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm space-y-2 max-h-56 overflow-y-auto">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-gray-900 flex-1">{last.message}</p>
                        {last.dry_run && (
                          <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                            Dry run
                          </span>
                        )}
                      </div>
                      <p className="text-gray-600">
                        Cases: {last.created_cases} · Steps: {last.created_steps}
                        {last.skipped_case_groups
                          ? ` · Skipped groups: ${last.skipped_case_groups}`
                          : ''}
                      </p>
                      {!last.dry_run && last.created_cases > 0 && (
                        <p className="text-xs text-teal-800">
                          Saved with source “CSV”. The table should open on the <strong>last page</strong>
                          — new rows sort last by case #. If filters hide them, set Status to “All
                          statuses” (many template rows are draft).
                        </p>
                      )}
                      {last.warnings.length > 0 && (
                        <div>
                          <p className="text-amber-800 font-medium text-xs uppercase tracking-wide">
                            Warnings
                          </p>
                          <ul className="list-disc pl-4 text-xs text-amber-900 space-y-1">
                            {last.warnings.slice(0, 30).map((w, i) => (
                              <li key={`w-${i}`}>
                                Row {w.row}
                                {w.column ? ` (${w.column})` : ''}: {w.message}
                              </li>
                            ))}
                            {last.warnings.length > 30 ? (
                              <li>… and {last.warnings.length - 30} more</li>
                            ) : null}
                          </ul>
                        </div>
                      )}
                      {last.errors.length > 0 && (
                        <div>
                          <p className="text-red-800 font-medium text-xs uppercase tracking-wide">
                            Row notes / errors
                          </p>
                          <ul className="list-disc pl-4 text-xs text-red-900 space-y-1">
                            {last.errors.slice(0, 40).map((w, i) => (
                              <li key={`e-${i}`}>
                                Row {w.row}
                                {w.column ? ` (${w.column})` : ''}: {w.message}
                              </li>
                            ))}
                            {last.errors.length > 40 ? (
                              <li>… and {last.errors.length - 40} more</li>
                            ) : null}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
