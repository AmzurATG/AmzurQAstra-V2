import React from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ChevronRightIcon, HomeIcon } from '@heroicons/react/20/solid'
import { useProjectStore } from '@common/store/projectStore'

export const Breadcrumbs: React.FC = () => {
  const location = useLocation()
  const { projectId } = useParams()
  const { currentProject } = useProjectStore()
  
  const pathnames = location.pathname.split('/').filter((x) => x)
  
  // Don't show on dashboard
  if (pathnames.length === 0) return null

  return (
    <nav className="flex mb-4" aria-label="Breadcrumb">
      <ol className="inline-flex items-center space-x-1 md:space-x-3">
        <li className="inline-flex items-center">
          <Link to="/" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-primary-600">
            <HomeIcon className="w-4 h-4 mr-2" />
            Dashboard
          </Link>
        </li>
        {pathnames.map((value, index) => {
          const last = index === pathnames.length - 1
          const to = `/${pathnames.slice(0, index + 1).join('/')}`
          
          // Replace project ID with project name if available
          let label = value.charAt(0).toUpperCase() + value.slice(1).replace(/-/g, ' ')
          if (value === projectId && currentProject) {
            label = currentProject.name
          }

          return (
            <li key={to}>
              <div className="flex items-center">
                <ChevronRightIcon className="w-5 h-5 text-gray-400" />
                {last ? (
                  <span className="ml-1 text-sm font-medium text-gray-700 md:ml-2">{label}</span>
                ) : (
                  <Link to={to} className="ml-1 text-sm font-medium text-gray-500 hover:text-primary-600 md:ml-2">
                    {label}
                  </Link>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
