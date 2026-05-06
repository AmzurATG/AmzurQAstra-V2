import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import applogo from '../assets/images/logo.png';
import bgImage from '../assets/images/login-bg.png';
import routes from '../utils/routes/routes';
const SecurityQuestions = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [userData, setUserData] = useState(null);
  const [errors, setErrors] = useState({});
  
  const [securityQuestions, setSecurityQuestions] = useState({
    question1: '',
    answer1: '',
    question2: '',
    answer2: '',
  });
  
  // Check if user data is available from previous step
  useEffect(() => {
    if (location.state && location.state.userData) {
      setUserData(location.state.userData);
    } else {
      // Redirect to signup if no data
      navigate(routes.signup);
    }
  }, [location.state, navigate]);
  
  const availableQuestions = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was your mother's maiden name?",
    "What was the name of your elementary school?",
    "What is your favorite color?"
  ];
  
  // Field validation functions
  const validateField = (name, value, currentErrors = errors) => {
    const newErrors = { ...currentErrors };
    
    switch (name) {
      case 'question1':
        if (!value.trim()) {
          newErrors.question1 = 'Please select a security question';
        } else {
          delete newErrors.question1;
        }
        break;
      case 'answer1':
        if (!value.trim()) {
          newErrors.answer1 = 'Answer is required';
        } else {
          delete newErrors.answer1;
        }
        break;
      case 'question2':
        if (!value.trim()) {
          newErrors.question2 = 'Please select a security question';
        } else {
          delete newErrors.question2;
        }
        break;
      case 'answer2':
        if (!value.trim()) {
          newErrors.answer2 = 'Answer is required';
        } else {
          delete newErrors.answer2;
        }
        break;
      default:
        break;
    }
    
    return newErrors;
  };
  
  const validateAllFields = () => {
    let newErrors = {};
    newErrors = validateField('question1', securityQuestions.question1, newErrors);
    newErrors = validateField('answer1', securityQuestions.answer1, newErrors);
    newErrors = validateField('question2', securityQuestions.question2, newErrors);
    newErrors = validateField('answer2', securityQuestions.answer2, newErrors);
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setSecurityQuestions({
      ...securityQuestions,
      [name]: value
    });
    
    // Clear error for this field when user starts typing/selecting
    if (errors[name]) {
      const newErrors = { ...errors };
      delete newErrors[name];
      setErrors(newErrors);
    }
    
    // Validate field immediately for real-time feedback
    const fieldErrors = validateField(name, value);
    setErrors(fieldErrors);
  };
  
  const handleSubmit = async (e) => {
    // Prevent default form submission
    e.preventDefault();
    
    // Validate all fields at once
    const isValid = validateAllFields();
    
    // Check if all fields are valid
    if (!isValid) {
      return;
    }

    setIsLoading(true);
    setError("");
    
    try {
      const security_questions = [
        { question: securityQuestions.question1, answer: securityQuestions.answer1 },
        { question: securityQuestions.question2, answer: securityQuestions.answer2 }
      ];
      
      // Combine the user data with security questions
      const completeUserData = {
        ...userData,
        security_questions: security_questions
      };
      
      const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${API_BASE_URL}/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(completeUserData)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        // Check if it's a lockout error
        const lockoutHeader = response.headers.get('X-Lockout-Seconds') || response.headers.get('x-lockout-seconds');
        if (response.status === 403 && lockoutHeader) {
          // Navigate directly to OTP page to show lockout
          navigate(routes.verifyEmail, { state: { email: userData.email } });
          return;
        }
        
        // Handle other server error messages
        const errorMessage = data.detail || 'Failed to complete signup';
        throw new Error(errorMessage);
      }
      
      // Navigate to OTP verification page
      navigate(routes.verifyEmail, { state: { email: userData.email } });
    } catch (error) {
      console.error('Security question submission error:', error);
      setError(typeof error.message === 'string' ? error.message : 'An error occurred during signup');
    } finally {
      setIsLoading(false);
    }
  };

  // Return early if no user data
  if (!userData) {
    return <div>Loading...</div>;
  }

    return (
    <div 
      className="min-h-screen bg-cover bg-center bg-no-repeat flex items-center justify-center p-4"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="w-full max-w-md">
        {/* Logo outside and centered above the card */}
        <div className="flex justify-center mb-6">
          <img src={applogo} alt="QAstra" className="h-12 w-auto"/>
        </div>
        
        {/* Card */}
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg p-2">
          <div className="text-center px-6 pt-4 pb-4">
            <div className="text-2xl font-semibold text-gray-900">Security Questions</div>
          </div>
       <div className="px-6 pb-6 pt-0">
          <p className="text-gray-600 text-sm mb-6 text-center">
            Please answer the following security questions. These will be used to verify your identity if you need to reset your password.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-1.5 rounded-md mb-4 text-sm">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1.5">
                Security Question 1 <span style={{ color: 'var(--destructive)' }}>*</span>
              </label>
              <select
                name="question1"
                value={securityQuestions.question1}
                onChange={handleChange}
                className={`w-full px-3 py-2 bg-white border rounded text-sm text-gray-900 focus:outline-none focus:ring-1 focus:border-tileBg appearance-none cursor-pointer bg-[length:1.25em] bg-[right_0.5rem_center] bg-no-repeat transition-all duration-200 ${
                  errors.question1 ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-tileBorder hover:border-tileBorder focus:ring-tileBorder'
                }`}
                      style={{
                        backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                        paddingRight: '2.5rem'
                      }}
              >
                <option value="" disabled>Select a question...</option>
                {availableQuestions
                .filter((question) => question !== securityQuestions.question2)
                .map((question, index) => (
                <option
                  key={index}
                  value={question}
                  style={{
                      backgroundColor: 'white',
                      color: '#111827',
                      padding: '8px 12px'
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.backgroundColor = 'var(--primary)';
                      e.target.style.color = 'white';
                    }}
                    onMouseLeave={(e) => {
                      if (!e.target.selected) {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#111827';
                      }
                    }}
                >
                  {question}
                </option>
              ))}
              </select>
              {errors.question1 && <p className="text-red-600 text-sm mt-1">{errors.question1}</p>}
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-900 mb-1.5">
                  Your answer <span style={{ color: 'var(--destructive)' }}>*</span>
                </label>
                <input
                  type="text"
                  name="answer1"
                  value={securityQuestions.answer1}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:border-tileBg transition-all duration-200 ${
                    errors.answer1 ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-tileBorder hover:border-tileBorder focus:ring-tileBorder'
                  }`}
                  placeholder="Your answer"
                />
                {errors.answer1 && <p className="text-red-600 text-sm mt-1">{errors.answer1}</p>}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1.5">
                Security Question 2 <span style={{ color: 'var(--destructive)' }}>*</span>
              </label>
              <select
                name="question2"
                value={securityQuestions.question2}
                onChange={handleChange}
                className={`w-full px-3 py-2 bg-white border rounded text-sm text-gray-900 focus:outline-none focus:ring-1 focus:border-tileBg appearance-none cursor-pointer bg-[length:1.25em] bg-[right_0.5rem_center] bg-no-repeat transition-all duration-200 ${
                  errors.question2 ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-tileBorder hover:border-tileBorder focus:ring-tileBorder'
                }`}
                      style={{
                        backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                        paddingRight: '2.5rem'
                      }}
              >
              <option value="" disabled>Select a question...</option>
              {availableQuestions
              .filter((question) => question !== securityQuestions.question1)
              .map((question, index) => (
              <option key={index} value={question}>{question}</option>
              ))}
              </select>
              {errors.question2 && <p className="text-red-600 text-sm mt-1">{errors.question2}</p>}
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-900 mb-1.5">
                  Your answer <span style={{ color: 'var(--destructive)' }}>*</span>
                </label>
                <input
                  type="text"
                  name="answer2"
                  value={securityQuestions.answer2}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:border-tileBg transition-all duration-200 ${
                    errors.answer2 ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-tileBorder hover:border-tileBorder focus:ring-tileBorder'
                  }`}
                  placeholder="Enter answer"
                />
                {errors.answer2 && <p className="text-red-600 text-sm mt-1">{errors.answer2}</p>}
              </div>
            </div>

            <div className="flex gap-4 mt-6">
              <button
                type="button"
                onClick={() => window.history.back()}
                className="flex-1 bg-gray-50 text-gray-900 font-medium py-2 px-4 rounded-md border border-tileBorder hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300 text-sm transition-all duration-200"
              >
                Back
              </button>
              
              <button
                type="submit"
                disabled={isLoading}
                className={`flex-1 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 text-sm transition-all duration-200 ${
                  isLoading ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                style={{ backgroundColor: 'var(--primary)' }}
              >
                {isLoading ? 'Processing...' : 'Continue'}
              </button>
            </div>
          </form>
        </div>
      </div>
      </div>
    </div>
  );
};

export default SecurityQuestions;
