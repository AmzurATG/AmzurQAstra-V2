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
}

export const PaginationBar: React.FC<PaginationBarProps> = ({
  page,
  totalPages,
  hasPrev,
  hasNext,
  onPageChange,
  className = '',
}) => {
  if (totalPages <= 1) return null

  return (
    <div
      className={`flex items-center justify-between gap-4 py-3 px-2 border-t border-gray-100 ${className}`}
    >
      <span className="text-sm text-gray-500">
        Page {page} of {totalPages}
      </span>
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
