import { useAuthStore } from '@common/store/authStore'
import { useProjectStore } from '@common/store/projectStore'
import { useUIStore } from '@common/store/uiStore'
import { Menu, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import {
  UserCircleIcon,
  ChevronDownIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'

export default function Header() {
  const { user, logout } = useAuthStore()
  const currentProject = useProjectStore((state) => state.currentProject)
  const isLoading = useUIStore((state) => state.isLoading)

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* Left side - Current project */}
      <div className="flex items-center gap-4">
        {currentProject && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Project:</span>
            <span className="font-medium">{currentProject.name}</span>
          </div>
        )}
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-amber-400 animate-pulse' : 'bg-green-500'}`} />
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            {isLoading ? 'Processing' : 'System Ready'}
          </span>
        </div>
      </div>

      {/* Right side - User menu */}
      <Menu as="div" className="relative">
        <Menu.Button className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100">
          <UserCircleIcon className="w-8 h-8 text-gray-400" />
          <span className="text-sm font-medium">{user?.full_name || user?.email}</span>
          <ChevronDownIcon className="w-4 h-4 text-gray-400" />
        </Menu.Button>

        <Transition
          as={Fragment}
          enter="transition ease-out duration-100"
          enterFrom="transform opacity-0 scale-95"
          enterTo="transform opacity-100 scale-100"
          leave="transition ease-in duration-75"
          leaveFrom="transform opacity-100 scale-100"
          leaveTo="transform opacity-0 scale-95"
        >
          <Menu.Items className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
            <div className="py-1">
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={logout}
                    className={`${
                      active ? 'bg-gray-100' : ''
                    } flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700`}
                  >
                    <ArrowRightOnRectangleIcon className="w-4 h-4" />
                    Sign out
                  </button>
                )}
              </Menu.Item>
            </div>
          </Menu.Items>
        </Transition>
      </Menu>
    </header>
  )
}
