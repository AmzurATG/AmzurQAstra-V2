import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import axios from 'axios';
import './App.css';
import SignupForm from './components/SignupForm';
import LoginForm from './components/LoginForm';
import VerifyEmail from './components/VerifyEmail';
import SecurityQuestions from './components/SecurityQuestions';
import ForgotPassword from './components/ForgotPassword';
import LandingPage from './components/LandingPage';
import SubscriptionSuccess from './components/SubscriptionSuccess';
import SubscriptionCancel from './components/SubscriptionCancel';
import SocialAuthCallback from './components/SocialAuthCallback';
import routes from './utils/routes/routes';
import SubscriptionPlans from './components/SubscriptionPlans';
import SuccessPage from './pages/SuccessPage';
import CancelPage from './pages/CancelPage';
import PaymentPage from './pages/PaymentPage';

import RoleDashboard from './components/RoleDashboard';
import AITestCasesPage from './components/AITestCasesPage'; // Import the AITestCasesPage component
import BuildIntegrityCheckPage from './components/BuildIntegrityCheckPage'; // Import the BuildIntegrityCheckPage component
import { TestAutomationProvider } from './contexts/TestAutomationContext';
import TestCasesManager from './components/TestCasesManager'; // Import for Test Cases Manager
import BICOutputScreen from './components/BICOutputScreen'; // Import for BIC Output Screen
import TestResultsDetailPage from './components/TestResultsDetailPage'; // Import for detailed test results
import TestRecommendationsDisplay from './components/TestRecommendationsDisplay'; // Import for test recommendations
import BRDSetupPage from './components/BRDSetupPage'; // Import for BRD Setup page
import GapAnalysisResultsPage from './components/GapAnalysisResultsPage'; // Import for Gap Analysis Results page
import ExecutionReportPage from './components/ExecutionReportPage'; // Import for Execution Report page


// Set up global axios interceptor to include Authorization header for all requests
axios.interceptors.request.use(
  (config) => {
    // Try to get token from localStorage - prioritize user.token (most recent login)
    let token = null;
    
    // First check user object for token (most recent login)
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        token = user.token;
      } catch (e) {
        console.error('Error parsing user from localStorage:', e);
      }
    }
    
    // If not found, try standalone token as fallback
    if (!token) {
      token = localStorage.getItem('token');
    }
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('🔐 Adding Authorization header to request:', config.url);
    } else {
      console.warn('⚠️ No token found in localStorage for request:', config.url);
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const userData = localStorage.getItem('user');
  
  if (!userData) {
    // Save the intended destination (including hash and query params)
    const currentPath = window.location.hash.substring(1); // Remove the leading #
    if (currentPath && currentPath !== routes.login) {
      localStorage.setItem('redirectAfterLogin', currentPath);
    }
    return <Navigate to={routes.login} replace />;
  }
  
  return children;
};

// Main App component with routes
function App() {
  return (
    <Router>
      
        <TestAutomationProvider>
          <div className="App">
            <ToastContainer position="top-right" autoClose={5000} />
            <Routes>
              <Route path={routes.home} element={<LandingPage />} />
              <Route path={routes.signup} element={<SignupForm />} />
              <Route path={routes.login} element={<LoginForm />} />
              <Route path={routes.verifyEmail} element={<VerifyEmail />} />
              <Route path={routes.securityQuestions} element={<SecurityQuestions />} />
              <Route path={routes.forgotPassword} element={<ForgotPassword />} />
              <Route path={routes.payment} element={<PaymentPage />} />
              <Route path={routes.pricing} element={<SubscriptionPlans />} />
              {/* Social auth callback route */}
              <Route path={routes.authCallback} element={<SocialAuthCallback />} />
              
              <Route 
                path={routes.subscriptionSuccess} 
                element={
                  <ProtectedRoute>
                    <SubscriptionSuccess />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path={routes.subscriptionCancel} 
                element={
                  <SubscriptionCancel />
                } 
              />
              <Route path={routes.paymentSuccess} element={<SuccessPage />} />
              <Route path={routes.paymentCancel} element={<CancelPage />} />
              <Route path={routes.testResults} element={<TestResultsDetailPage />} />
              <Route 
                path={routes.executionReport} 
                element={
                  <ProtectedRoute>
                    <ExecutionReportPage />
                  </ProtectedRoute>
                }
              />

              <Route 
                path={routes.gapAnalysisResults} 
                element={
                  <ProtectedRoute>
                    <GapAnalysisResultsPage />
                  </ProtectedRoute>
                }
              />
              
              
              <Route 
                path={routes.aiTestCases} 
                element={
                  <ProtectedRoute>
                    <AITestCasesPage />
                  </ProtectedRoute>
                }
              />
              <Route 
                path={routes.buildIntegrityCheck} 
                element={
                  <ProtectedRoute>
                    <BuildIntegrityCheckPage />
                  </ProtectedRoute>
                }
              />
              <Route path={routes.roleDashboard} element={<RoleDashboard />} />
              <Route path={routes.dashboard} element={<Navigate to={routes.brdSetup} replace />} />
              <Route path={routes.qaDashboard} element={<RoleDashboard />} />
              <Route path={routes.devDashboard} element={<RoleDashboard />} />
              <Route path={routes.managerDashboard} element={<RoleDashboard />} />
              <Route path={routes.clientDashboard} element={<RoleDashboard />} />

              {/* TestMasterDashboard route - no layout wrapper */}
              <Route path={routes.testCasesManager} element={<TestCasesManager />} />
              <Route 
                path={routes.bicOutput} 
                element={
                  <ProtectedRoute>
                    <BICOutputScreen />
                  </ProtectedRoute>
                } 
              />
              <Route path={routes.testResultsDetail} element={<TestResultsDetailPage />} />

              {/* BRD Analysis Dashboard route */}
              <Route 
                path={routes.testRecommendations} 
                element={
                  <ProtectedRoute>
                    <TestRecommendationsDisplay />
                  </ProtectedRoute>
                } 
              />

              {/* BRD Setup Page - Step 1 */}
              <Route 
                path={routes.brdSetup} 
                element={
                  <ProtectedRoute>
                    <BRDSetupPage />
                  </ProtectedRoute>
                } 
              />

              {/* Gap Analysis Results Page - Step 2 */}
              <Route 
                path={routes.gapAnalysisResults} 
                element={
                  <ProtectedRoute>
                    <GapAnalysisResultsPage />
                  </ProtectedRoute>
                } 
              />

              {/* Test Recommendations route - also accessible directly */}
              <Route 
                path={routes.testRecommendations} 
                element={
                  <ProtectedRoute>
                    <TestRecommendationsDisplay />
                  </ProtectedRoute>
                } 
              />

              {/* Redirect unknown routes to home */}
              <Route path="*" element={<Navigate to={routes.home} />} />
            </Routes>
          </div>
        </TestAutomationProvider>
      
    </Router>
  );
}

export default App;