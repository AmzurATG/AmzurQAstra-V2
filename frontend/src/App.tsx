import { useState, useEffect } from 'react'
import { Outlet, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { useAuthStore } from '@common/store/authStore'
import MainLayout from '@common/components/layout/MainLayout'
import ProjectLayout from '@common/components/layout/ProjectLayout'
import { ErrorBoundary } from '@common/components/layout/ErrorBoundary'
import Login from '@common/pages/Login'
import Signup from '@common/pages/Signup'
import SecurityQuestions from '@common/pages/SecurityQuestions'
import VerifyEmail from '@common/pages/VerifyEmail'
import ForgotPassword from '@common/pages/ForgotPassword'
import Dashboard from '@common/pages/Dashboard'
import Projects from '@common/pages/Projects'
import Settings from '@common/pages/Settings'

// Functional Testing Feature (Project-scoped)
import ProjectOverview from '@features/functional/pages/ProjectOverview'
import Requirements from '@features/functional/pages/Requirements'
import TestCaseDetail from '@features/functional/pages/TestCaseDetail'
import TestRunDetail from '@features/functional/pages/TestRunDetail'
import FunctionalTesting from '@features/functional/pages/FunctionalTesting'
import Analytics from '@features/functional/pages/analytics/Analytics'
import CasesTab from '@features/functional/pages/functional-testing/CasesTab'
import LiveTab from '@features/functional/pages/functional-testing/LiveTab'
import HistoryTab from '@features/functional/pages/functional-testing/HistoryTab'
import { ActiveTestRunProvider } from '@features/functional/context/ActiveTestRunProvider'
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
  const fetchUser = useAuthStore((state) => state.fetchUser)
  const [isValidating, setIsValidating] = useState(true)

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser().finally(() => setIsValidating(false))
    } else {
      setIsValidating(false)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (isValidating) return null

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

/**
 * Project-scoped wrapper that binds the single ActiveTestRunProvider lifetime
 * to the project URL segment. Every child route (Functional Testing shell,
 * test case detail, run detail, etc.) can then read live-run state from the
 * same source of truth. Unmounting on project switch tears down the polling
 * subscription — no cross-tenant leakage.
 */
function ProjectScopedRoutes() {
  return (
    <ActiveTestRunProvider>
      <Outlet />
    </ActiveTestRunProvider>
  )
}

/**
 * Legacy redirect shims. Keep forever (not deprecated): saved bookmarks,
 * emailed links, and inbound URLs from integrations still work. Forwarding
 * happens server-path-preserving for detail pages.
 */
function LegacyTestCasesRedirect() {
  const { projectId } = useParams<{ projectId: string }>()
  return <Navigate to={`/projects/${projectId}/functional-testing/cases`} replace />
}
function LegacyTestCaseDetailRedirect() {
  const { projectId, testCaseId } = useParams<{ projectId: string; testCaseId: string }>()
  return (
    <Navigate
      to={`/projects/${projectId}/functional-testing/cases/${testCaseId}`}
      replace
    />
  )
}
function LegacyTestRunsRedirect() {
  const { projectId } = useParams<{ projectId: string }>()
  return <Navigate to={`/projects/${projectId}/functional-testing/history`} replace />
}
function LegacyTestRunDetailRedirect() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  return (
    <Navigate
      to={`/projects/${projectId}/functional-testing/history/${runId}`}
      replace
    />
  )
}

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/security-questions" element={<SecurityQuestions />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        
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
            <Route element={<ProjectScopedRoutes />}>
              <Route index element={<ProjectOverview />} />
              <Route path="user-stories/:storyId" element={<UserStoryDetail />} />
              <Route path="user-stories" element={<UserStories />} />
              <Route path="requirements" element={<Requirements />} />

              {/* Functional Testing workspace */}
              <Route path="functional-testing">
                <Route element={<FunctionalTesting />}>
                  <Route index element={<Navigate to="cases" replace />} />
                  <Route path="cases" element={<CasesTab />} />
                  <Route path="live" element={<LiveTab />} />
                  <Route path="history" element={<HistoryTab />} />
                </Route>
                <Route path="cases/:testCaseId" element={<TestCaseDetail />} />
                <Route path="history/:runId" element={<TestRunDetail />} />
              </Route>

              {/* Legacy URL redirects — kept permanently, not deprecated */}
              <Route path="test-cases" element={<LegacyTestCasesRedirect />} />
              <Route
                path="test-cases/:testCaseId"
                element={<LegacyTestCaseDetailRedirect />}
              />
              <Route path="test-runs" element={<LegacyTestRunsRedirect />} />
              <Route
                path="test-runs/:runId"
                element={<LegacyTestRunDetailRedirect />}
              />

              <Route path="analytics" element={<Analytics />} />
              <Route path="integrity-check" element={<IntegrityCheck />} />
              <Route path="integrations" element={<ProjectIntegrations />} />
              <Route path="integrations/jira" element={<JiraIntegration />} />
              <Route
                path="integrations/azure-devops"
                element={<AzureDevOpsIntegration />}
              />
              <Route path="settings" element={<ProjectSettings />} />
            </Route>
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
