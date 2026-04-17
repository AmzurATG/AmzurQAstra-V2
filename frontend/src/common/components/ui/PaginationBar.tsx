import React from 'react'
import { Button } from './Button'

export type PaginationBarProps = {
  page: number
  totalPages: number
  hasPrev: boolean
  hasNext: boolean
  onPageChange: (page: number) => void
  totalItems?: number
  pageSize?: number
  itemLabel?: string
  className?: string
  /** When set with pageSize & itemLabel, shows “Showing a–b of c …” for the current page. */
  totalItems?: number
  pageSize?: number
  itemLabel?: string
}

export const PaginationBar: React.FC<PaginationBarProps> = ({
  page,
  totalPages,
  hasPrev,
  hasNext,
  onPageChange,
  className = '',
  totalItems,
  pageSize,
  itemLabel = 'items',
}) => {
  if (totalPages <= 1) return null

  const rangeText =
    totalItems != null &&
    pageSize != null &&
    totalItems > 0 &&
    page >= 1
      ? (() => {
          const start = (page - 1) * pageSize + 1
          const end = Math.min(page * pageSize, totalItems)
          return `Showing ${start}–${end} of ${totalItems} ${itemLabel}`
        })()
      : null

  return (
    <div
      className={`flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4 py-3 px-2 border-t border-gray-100 ${className}`}
    >
      <div className="flex flex-col gap-0.5 text-sm text-gray-500 min-w-0">
        {rangeText ? <span className="text-gray-700">{rangeText}</span> : null}
        <span>
          Page {page} of {totalPages}
        </span>
      </div>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!hasPrev}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!hasNext}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

