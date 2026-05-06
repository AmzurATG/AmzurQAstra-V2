/**
 * Centralized Route Configuration
 *
 * This file contains all route paths used throughout the application.
 * To add a new route, simply add it here and import it where needed.
 *
 * Usage:
 *   import routes from '../../utils/routes/routes';
 *   navigate(routes.dashboard);
 *   <Link to={routes.profile}>Profile</Link>
 *
 * For dynamic routes:
 *   navigate(routes.projectDetails('123'));
 *   <Link to={routes.userProfile(userId)}>View Profile</Link>
 */

const routes = {
  // ==================== Public Routes ====================
  home: '/',
  login: '/login',
  signup: '/signup',
  verifyEmail: '/verify-email',
  securityQuestions: '/security-questions',
  forgotPassword: '/forgot-password',

  // ==================== Auth Callback ====================
  authCallback: '/auth/callback',

  // ==================== Payment & Subscription ====================
  payment: '/payment',
  pricing: '/pricing',
  subscriptionSuccess: '/subscription/success',
  subscriptionCancel: '/subscription/cancel',
  paymentSuccess: '/success',
  paymentCancel: '/cancel',

  // ==================== Dashboard Routes ====================
  dashboard: '/dashboard',
  roleDashboard: '/role-dashboard',
  qaDashboard: '/qa-dashboard',
  devDashboard: '/dev-dashboard',
  managerDashboard: '/manager-dashboard',
  clientDashboard: '/client-dashboard',

  // ==================== BRD & Analysis Routes ====================
  brdSetup: '/brd-setup',
  gapAnalysisResults: '/gap-analysis-results',

  // ==================== Test Management Routes ====================
  aiTestCases: '/ai-test-cases',
  aiTestUserStories: '/ai-test-user-stories',
  aiTestAutomation: '/ai-test-automation',
  testCasesManager: '/test-cases-manager',
  testRecommendations: '/test-recommendations',
  testResults: '/test-results',
  testResultsDetail: '/test-results-detail',
  testScripts: '/test-scripts',
  executionReport: '/execution-report',

  // ==================== Build Integrity Routes ====================
  buildIntegrityCheck: '/build-integrity-check',
  bicOutput: '/bic-output',

  // ==================== Profile Routes ====================
  updateProfile: '/update-profile',

  // ==================== Support & Help Routes ====================
  support: '/support',
  contactSupport: '/contact-support',

  // ==================== Dynamic Routes ====================
  // Usage: routes.projectDetails('123') => '/projects/123'
  projectDetails: (id) => `/projects/${id}`,

  // Usage: routes.userProfile('456') => '/users/456'
  userProfile: (userId) => `/users/${userId}`,

  // Usage: routes.testCaseDetails('tc-001') => '/test-cases/tc-001'
  testCaseDetails: (testCaseId) => `/test-cases/${testCaseId}`,

  // Usage: routes.defectDetails('def-001') => '/defects/def-001'
  defectDetails: (defectId) => `/defects/${defectId}`,
};

export default routes;