import React, { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, SparklesIcon, DocumentArrowUpIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import type { TestCase, TestCasePriority, TestCaseCategory, TestCaseStatus } from '../types'

interface TestCaseEditModalProps {
  isOpen: boolean
  onClose: () => void
  testCase: TestCase | null
  setTestCase: (tc: TestCase) => void
  onSave: () => void
  isSaving: boolean
  title?: string
  saveLabel?: string
}

const PRIORITY_OPTIONS = ['critical', 'high', 'medium', 'low'] as const
const CATEGORY_OPTIONS = ['smoke', 'regression', 'e2e', 'integration', 'sanity'] as const
const STATUS_OPTIONS = ['draft', 'ready', 'deprecated'] as const

export const TestCaseEditModal: React.FC<TestCaseEditModalProps> = ({
  isOpen,
  onClose,
  testCase,
  setTestCase,
  onSave,
  isSaving,
  title = 'Edit Test Case',
  saveLabel = 'Save Changes',
}) => {
  if (!testCase) return null

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
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
              <Dialog.Panel className="w-full max-w-lg transform overflow-hidden rounded-xl bg-white shadow-2xl transition-all">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    {title}
                  </Dialog.Title>
                  <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                    <input
                      type="text"
                      value={testCase.title}
                      onChange={(e) => setTestCase({ ...testCase, title: e.target.value })}
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <textarea
                      value={testCase.description || ''}
                      onChange={(e) => setTestCase({ ...testCase, description: e.target.value })}
                      rows={3}
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                      <select
                        value={testCase.priority}
                        onChange={(e) => setTestCase({ ...testCase, priority: e.target.value as TestCasePriority })}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 outline-none"
                      >
                        {PRIORITY_OPTIONS.map((p) => (
                          <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                      <select
                        value={testCase.category}
                        onChange={(e) => setTestCase({ ...testCase, category: e.target.value as TestCaseCategory })}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 outline-none"
                      >
                        {CATEGORY_OPTIONS.map((c) => (
                          <option key={c} value={c}>{c.toUpperCase()}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                    <select
                      value={testCase.status}
                      onChange={(e) => setTestCase({ ...testCase, status: e.target.value as TestCaseStatus })}
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 outline-none"
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                      ))}
                    </select>
                  </div>

                  {((testCase.source ?? (testCase.is_generated ? 'ai' : 'manual')) === 'ai') && (
                    <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-50 px-3 py-2 rounded-lg">
                      <SparklesIcon className="w-4 h-4" />
                      <span>This test case was generated by AI</span>
                    </div>
                  )}
                  {testCase.source === 'csv' && (
                    <div className="flex items-center gap-2 text-sm text-teal-800 bg-teal-50 px-3 py-2 rounded-lg">
                      <DocumentArrowUpIcon className="w-4 h-4" />
                      <span>This test case was imported from CSV</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                  <Button variant="outline" onClick={onClose} disabled={isSaving}>Cancel</Button>
                  <Button onClick={onSave} disabled={isSaving || !testCase.title} isLoading={isSaving}>{saveLabel}</Button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
