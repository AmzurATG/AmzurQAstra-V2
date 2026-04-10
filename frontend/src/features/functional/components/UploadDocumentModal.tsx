import { useState, useCallback, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  XMarkIcon,
  DocumentArrowUpIcon,
  CheckCircleIcon,
  ServerIcon,
  CloudIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { requirementsApi } from '../api'
import { REQUIREMENT_UPLOAD_MAX_BYTES } from '../constants/requirementUpload'
import toast from 'react-hot-toast'

interface UploadDocumentModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  onUploadComplete: () => void
}

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.md', '.txt']

function formatBytes(n: number): string {
  return n.toLocaleString('en-US')
}

export default function UploadDocumentModal({
  isOpen,
  onClose,
  projectId,
  onUploadComplete,
}: UploadDocumentModalProps) {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resetForm = () => {
    setTitle('')
    setFile(null)
    setError(null)
  }

  const handleClose = () => {
    if (!isUploading) {
      resetForm()
      onClose()
    }
  }

  const validateFile = (f: File): string | null => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`
    }

    if (f.size > REQUIREMENT_UPLOAD_MAX_BYTES) {
      return (
        `File size is ${formatBytes(f.size)} bytes; maximum allowed is ` +
        `${formatBytes(REQUIREMENT_UPLOAD_MAX_BYTES)} bytes (5 MiB).`
      )
    }

    return null
  }

  const handleFileSelect = (selectedFile: File) => {
    const validationError = validateFile(selectedFile)
    if (validationError) {
      setError(validationError)
      return
    }

    setFile(selectedFile)
    setError(null)

    if (!title) {
      const nameWithoutExt = selectedFile.name.replace(/\.[^/.]+$/, '')
      setTitle(nameWithoutExt)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [title])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    if (!title.trim()) {
      setError('Please enter a title')
      return
    }

    setIsUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title.trim())
      formData.append('project_id', projectId)

      await requirementsApi.upload(formData)

      toast.success('Document uploaded successfully!')
      resetForm()
      onUploadComplete()
      onClose()
    } catch (err: any) {
      console.error('Upload failed:', err)
      const raw = err.response?.data?.detail
      const message =
        typeof raw === 'string'
          ? raw
          : Array.isArray(raw)
            ? raw.map((x: { msg?: string }) => x.msg).filter(Boolean).join(' ')
            : 'Failed to upload document'
      setError(message)
      toast.error(message)
    } finally {
      setIsUploading(false)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
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
          <div className="fixed inset-0 bg-black/25" />
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
              <Dialog.Panel className="w-full max-w-lg transform overflow-hidden rounded-xl bg-white p-6 shadow-xl transition-all">
                <div className="flex items-center justify-between mb-6">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    Upload Requirement Document
                  </Dialog.Title>
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={isUploading}
                    className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <p className="block text-sm font-medium text-gray-700 mb-2">Storage destination</p>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                      <div
                        className="rounded-lg border-2 border-primary-500 bg-primary-50 p-3 text-left"
                        role="status"
                        aria-current="true"
                      >
                        <div className="flex items-center gap-2 text-primary-800">
                          <ServerIcon className="h-5 w-5 shrink-0" />
                          <span className="text-sm font-semibold">Local</span>
                        </div>
                        <p className="mt-1 text-xs text-primary-700">Upload from this device</p>
                      </div>
                      <div
                        className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-left opacity-60"
                        aria-disabled="true"
                      >
                        <div className="flex items-center gap-2 text-gray-600">
                          <CloudIcon className="h-5 w-5 shrink-0" />
                          <span className="text-sm font-medium">Amazon S3</span>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">Coming soon</p>
                      </div>
                      <div
                        className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-left opacity-60"
                        aria-disabled="true"
                      >
                        <div className="flex items-center gap-2 text-gray-600">
                          <CloudIcon className="h-5 w-5 shrink-0" />
                          <span className="text-sm font-medium">Supabase</span>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">Coming soon</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Document Title
                    </label>
                    <Input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Enter a descriptive title"
                      disabled={isUploading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Document File
                    </label>
                    <div
                      onDrop={handleDrop}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      className={`
                        relative rounded-lg border-2 border-dashed p-6 text-center transition-colors
                        ${
                          isDragging
                            ? 'border-primary-500 bg-primary-50'
                            : file
                              ? 'border-green-300 bg-green-50'
                              : 'border-gray-300 hover:border-gray-400'
                        }
                        ${isUploading ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                      `}
                    >
                      <input
                        type="file"
                        accept={ALLOWED_EXTENSIONS.join(',')}
                        onChange={handleFileInputChange}
                        disabled={isUploading}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      />

                      {file ? (
                        <div className="flex flex-col items-center">
                          <CheckCircleIcon className="h-10 w-10 text-green-500 mb-2" />
                          <p className="text-sm font-medium text-gray-900">{file.name}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {formatFileSize(file.size)} ({formatBytes(file.size)} bytes)
                          </p>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setFile(null)
                            }}
                            className="mt-2 text-xs text-red-600 hover:text-red-700"
                          >
                            Remove file
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center">
                          <DocumentArrowUpIcon className="h-10 w-10 text-gray-400 mb-2" />
                          <p className="text-sm text-gray-600">
                            <span className="text-primary-600 font-medium">Click to upload</span>{' '}
                            or drag and drop
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            PDF, Word, Markdown, or Text — max {formatBytes(REQUIREMENT_UPLOAD_MAX_BYTES)}{' '}
                            bytes (5 MiB)
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {error && (
                    <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm">{error}</div>
                  )}

                  <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600">
                    <p className="font-medium mb-1">Supported formats:</p>
                    <ul className="list-disc list-inside space-y-0.5">
                      <li>PDF documents (.pdf)</li>
                      <li>Word documents (.docx, .doc)</li>
                      <li>Markdown files (.md)</li>
                      <li>Plain text files (.txt)</li>
                    </ul>
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6">
                  <Button variant="outline" onClick={handleClose} disabled={isUploading}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleUpload}
                    disabled={!file || !title.trim() || isUploading}
                    isLoading={isUploading}
                  >
                    {isUploading ? 'Uploading...' : 'Upload Document'}
                  </Button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
