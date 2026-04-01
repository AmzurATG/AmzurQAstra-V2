import { NavLink, useLocation, useParams, useNavigate } from 'react-router-dom'
import { useUIStore } from '@common/store/uiStore'
import { useProjectStore } from '@common/store/projectStore'
import { useEffect } from 'react'
import {
  HomeIcon,
  FolderIcon,
  Cog6ToothIcon,
  LinkIcon,
  BeakerIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  PlayIcon,
  ShieldCheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowLeftIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline'

// Global navigation (when NOT inside a project)
const globalNav = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Projects', href: '/projects', icon: FolderIcon },
]

const globalBottomNav = [
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

// Project-scoped navigation (when INSIDE a project)
const getProjectNav = (projectId: string) => [
  { name: 'Overview', href: `/projects/${projectId}`, icon: BeakerIcon },
  { name: 'User Stories', href: `/projects/${projectId}/user-stories`, icon: BookOpenIcon },
  { name: 'Requirements', href: `/projects/${projectId}/requirements`, icon: DocumentTextIcon },
  { name: 'Test Cases', href: `/projects/${projectId}/test-cases`, icon: ClipboardDocumentListIcon },
  { name: 'Test Runs', href: `/projects/${projectId}/test-runs`, icon: PlayIcon },
  { name: 'Integrity Check', href: `/projects/${projectId}/integrity-check`, icon: ShieldCheckIcon },
  { name: 'Integrations', href: `/projects/${projectId}/integrations`, icon: LinkIcon },
]

const getProjectBottomNav = (projectId: string) => [
  { name: 'Project Settings', href: `/projects/${projectId}/settings`, icon: Cog6ToothIcon },
]

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const { currentProject } = useProjectStore()
  const location = useLocation()
  const navigate = useNavigate()
  const { projectId } = useParams()
  
  // Check if we're inside a project (URL has /projects/:id/...)
  const isInsideProject = location.pathname.match(/^\/projects\/\d+/)
  const currentProjectId = projectId || location.pathname.match(/^\/projects\/(\d+)/)?.[1]

  // Fix for blank pages: if we are at /projects/:id/functional/settings, redirect to /projects/:id/settings
  useEffect(() => {
    if (location.pathname.includes('/functional/settings')) {
      navigate(location.pathname.replace('/functional/settings', '/settings'), { replace: true })
    }
    if (location.pathname.includes('/functional/test-runs')) {
      navigate(location.pathname.replace('/functional/test-runs', '/test-runs'), { replace: true })
    }
  }, [location.pathname, navigate])

  const linkClass = (isActive: boolean) =>
    `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
      isActive
        ? 'bg-primary-100 text-primary-700'
        : 'text-gray-600 hover:bg-gray-100'
    }`

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-gray-200 transition-all duration-300 ${
        sidebarOpen ? 'w-64' : 'w-20'
      }`}
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
        {sidebarOpen && (
          <span className="text-xl font-bold text-primary-600">QAstra</span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100"
        >
          {sidebarOpen ? (
            <ChevronLeftIcon className="w-5 h-5" />
          ) : (
            <ChevronRightIcon className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {isInsideProject && currentProjectId ? (
          <>
            {/* Back to Projects */}
            <NavLink
              to="/projects"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-100 mb-4"
            >
              <ArrowLeftIcon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span>Back to Projects</span>}
            </NavLink>

            {/* Project Name */}
            {sidebarOpen && currentProject && (
              <div className="px-3 py-2 mb-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Project
                </p>
                <p className="text-sm font-medium text-gray-900 truncate">
                  {currentProject.name}
                </p>
              </div>
            )}

            {/* Project Navigation */}
            {sidebarOpen && (
              <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mt-4">
                Functional Testing
              </p>
            )}
            <div className="mt-2 space-y-1">
              {getProjectNav(currentProjectId).map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  end={item.href === `/projects/${currentProjectId}`}
                  className={({ isActive }) => linkClass(isActive)}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  {sidebarOpen && <span>{item.name}</span>}
                </NavLink>
              ))}
            </div>
          </>
        ) : (
          <>
            {/* Global Navigation */}
            {globalNav.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                end={item.href === '/'}
                className={({ isActive }) => linkClass(isActive)}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span>{item.name}</span>}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* Bottom Navigation */}
      <div className="border-t border-gray-200 px-3 py-4 space-y-1">
        {isInsideProject && currentProjectId ? (
          getProjectBottomNav(currentProjectId).map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) => linkClass(isActive)}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.name}</span>}
            </NavLink>
          ))
        ) : (
          globalBottomNav.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) => linkClass(isActive)}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.name}</span>}
            </NavLink>
          ))
        )}
      </div>
    </aside>
  )
}
