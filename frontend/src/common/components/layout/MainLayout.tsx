import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import { Breadcrumbs } from './Breadcrumbs'
import { useUIStore } from '@common/store/uiStore'

export default function MainLayout() {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen)
  const isLoading = useUIStore((state) => state.isLoading)

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Global Loading Bar */}
      {isLoading && (
        <div className="fixed top-0 left-0 right-0 h-1 bg-primary-100 z-[60]">
          <div className="h-full bg-primary-600 animate-progress origin-left"></div>
        </div>
      )}
      <Sidebar />
      <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Breadcrumbs />
          <Outlet />
        </main>
      </div>
    </div>
  )
}
