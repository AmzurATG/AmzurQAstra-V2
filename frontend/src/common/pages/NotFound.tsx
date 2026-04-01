import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@common/components/ui/Button'

export default function NotFound() {
  return (
    <div className="min-h-[400px] flex flex-col items-center justify-center p-6 text-center">
      <div className="w-20 h-20 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mb-6">
        <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 9.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h1 className="text-4xl font-extrabold text-gray-900 mb-2">404</h1>
      <h2 className="text-xl font-bold text-gray-700 mb-4">Page Not Found</h2>
      <p className="text-gray-500 mb-8 max-w-md">
        The page you are looking for doesn't exist or has been moved.
      </p>
      <Link to="/">
        <Button size="lg">
          Back to Dashboard
        </Button>
      </Link>
    </div>
  )
}
