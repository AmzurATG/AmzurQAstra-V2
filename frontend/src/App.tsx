import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@common/store/authStore'
import MainLayout from '@common/components/layout/MainLayout'
import ProjectLayout from '@common/components/layout/ProjectLayout'
import { ErrorBoundary } from '@common/components/layout/ErrorBoundary'
import Login from '@common/pages/Login'
import Dashboard from '@common/pages/Dashboard'
import Projects from '@common/pages/Projects'
import Settings from '@common/pages/Settings'

// Functional Testing Feature (Project-scoped)
import ProjectOverview from '@features/functional/pages/ProjectOverview'
import Requirements from '@features/functional/pages/Requirements'
import TestCases from '@features/functional/pages/TestCases'
import TestCaseDetail from '@features/functional/pages/TestCaseDetail'
import TestRuns from '@features/functional/pages/TestRuns'
import TestRunDetail from '@features/functional/pages/TestRunDetail'
import IntegrityCheck from '@features/functional/pages/IntegrityCheck'
import ProjectSettings from '@features/functional/pages/ProjectSettings'
import ProjectIntegrations from '@features/functional/pages/ProjectIntegrations'
import UserStories from '@features/functional/pages/UserStories'
import UserStoryDetail from '@features/functional/pages/UserStoryDetail'
import JiraIntegration from '@features/functional/pages/JiraIntegration'
import AzureDevOpsIntegration from '@features/functional/pages/AzureDevOpsIntegration'
import NotFound from '@common/pages/NotFound'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route
          path="/"
          element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          }
        >
          {/* Global Routes */}
          <Route index element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="settings" element={<Settings />} />
          
          {/* Project-Scoped Routes */}
          <Route path="projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<ProjectOverview />} />
            <Route path="user-stories/:storyId" element={<UserStoryDetail />} />
            <Route path="user-stories" element={<UserStories />} />
            <Route path="requirements" element={<Requirements />} />
            <Route path="test-cases" element={<TestCases />} />
            <Route path="test-cases/:testCaseId" element={<TestCaseDetail />} />
            <Route path="test-runs" element={<TestRuns />} />
            <Route path="test-runs/:runId" element={<TestRunDetail />} />
            <Route path="integrity-check" element={<IntegrityCheck />} />
            <Route path="integrations" element={<ProjectIntegrations />} />
            <Route path="integrations/jira" element={<JiraIntegration />} />
            <Route path="integrations/azure-devops" element={<AzureDevOpsIntegration />} />
            <Route path="settings" element={<ProjectSettings />} />
          </Route>

          {/* Catch-all Route for authenticated area */}
          <Route path="*" element={<NotFound />} />
        </Route>

        {/* Catch-all Route for unauthenticated area */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
