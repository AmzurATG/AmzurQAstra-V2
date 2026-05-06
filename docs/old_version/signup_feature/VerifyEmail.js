import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FaShieldAlt } from 'react-icons/fa';
import applogo from '../assets/images/logo.png';
import bgImage from '../assets/images/login-bg.png';
import routes from '../utils/routes/routes';

const VerifyEmail = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [canResend, setCanResend] = useState(true);
  const [countdown, setCountdown] = useState(0);
  const [isLockedOut, setIsLockedOut] = useState(false);
  const [lockoutCountdown, setLockoutCountdown] = useState(0);
  
  const inputRefs = useRef([]);
  const email = location.state?.email || '';

  // Countdown timer for resend button
  useEffect(() => {
    let timer;
    if (countdown > 0) {
      timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    } else {
      setCanResend(true);
    }
    return () => clearTimeout(timer);
  }, [countdown]);

  // Lockout countdown timer
  useEffect(() => {
    let timer;
    if (lockoutCountdown > 0) {
      timer = setTimeout(() => setLockoutCountdown(lockoutCountdown - 1), 1000);
    } else if (isLockedOut && lockoutCountdown === 0) {
      setIsLockedOut(false);
      setError('');
    }
    return () => clearTimeout(timer);
  }, [lockoutCountdown, isLockedOut]);

  useEffect(() => {
  // On mount, check for lockout in localStorage
  const lockoutEnd = localStorage.getItem(`lockoutEnd_${email}`);
  if (lockoutEnd) {
    const now = Date.now();
    const remaining = Math.floor((parseInt(lockoutEnd) - now) / 1000);
    if (remaining > 0) {
      setIsLockedOut(true);
      setLockoutCountdown(remaining);
    } else {
      localStorage.removeItem(`lockoutEnd_${email}`);
    }
  }
}, [email]);

useEffect(() => {
  // When lockout starts, save end time to localStorage
  if (isLockedOut && lockoutCountdown > 0) {
    localStorage.setItem(
      `lockoutEnd_${email}`,
      (Date.now() + lockoutCountdown * 1000).toString()
    );
  }
  // When lockout ends, remove from localStorage
  if (!isLockedOut) {
    localStorage.removeItem(`lockoutEnd_${email}`);
  }
}, [isLockedOut, lockoutCountdown, email]);


  const handleChange = (index, value) => {
    // Only allow numbers
    if (!/^\d*$/.test(value)) return;
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    
    // Clear any previous errors when user starts typing
    if (error) {
      setError('');
    }

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };


  const handleKeyDown = (index, e) => {
  // Handle backspace
  if (e.key === 'Backspace' && !otp[index] && index > 0) {
    inputRefs.current[index - 1]?.focus();
  }

  // Handle Enter key to submit form
  if (e.key === 'Enter') {
    e.preventDefault();
    if (otp.join('').length === 6) {
      handleVerify();
    }
  }

  // Handle left arrow
  if (e.key === 'ArrowLeft' && index > 0) {
     const prevInput = inputRefs.current[index - 1];
     prevInput?.focus();
     setTimeout(() => {
        prevInput?.setSelectionRange(1, 1);
    }, 0);
  }

  // Handle right arrow
  if (e.key === 'ArrowRight' && index < 5) {
    const nextInput = inputRefs.current[index + 1];
    nextInput?.focus();
    nextInput?.setSelectionRange(0, 0);
  }
};

  

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').slice(0, 6);
    if (!/^\d+$/.test(pastedData)) return;
    
    const newOtp = pastedData.split('').concat(Array(6).fill('')).slice(0, 6);
    setOtp(newOtp);
    
    // Focus the last filled input or next empty one
    const nextIndex = Math.min(pastedData.length, 5);
    inputRefs.current[nextIndex]?.focus();
  };

  const handleVerify = async () => {
    try {
      setLoading(true);
      setError('');
      
      const verificationCode = otp.join('');
      
      // Validate OTP length
      if (verificationCode.length !== 6) {
        setError('Please enter all 6 digits');
        setLoading(false);
        return;
      }
      
      // Validate all digits are numbers
      if (!/^\d{6}$/.test(verificationCode)) {
        setError('Please enter only numbers');
        setLoading(false);
        return;
      }
      
      const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      
      console.log('Verifying OTP:', verificationCode, 'for email:', email);
      
      const response = await fetch(`${API_BASE_URL}/verify-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          email: email,
          otp: verificationCode
        })
      });
      
      const data = await response.json();
      
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);
      console.log('Response data:', data);
      
      if (!response.ok) {
        // Handle lockout response
        const lockoutHeader = response.headers.get('X-Lockout-Seconds') || response.headers.get('x-lockout-seconds');
        console.log('Lockout header value:', lockoutHeader);
        
        if (response.status === 403 && lockoutHeader) {
          const lockoutSeconds = parseInt(lockoutHeader);
          console.log('Lockout detected, seconds:', lockoutSeconds);
          setIsLockedOut(true);
          setLockoutCountdown(lockoutSeconds);
          setError(data.detail || 'Too many incorrect attempts. Please wait.');
          // Clear OTP inputs during lockout
          setOtp(['', '', '', '', '', '']);
        } else {
          console.log('Non-lockout error:', response.status, data.detail);
          throw new Error(data.detail || 'Verification failed');
        }
        return;
      }
      
      setMessage('OTP Verified');
      setOpenSnackbar(true);
      
      // Redirect after successful verification
      setTimeout(() => {
        navigate(routes.login, { 
          state: { verificationSuccess: true }
        });
      }, 2000);
    } catch (err) {
      console.error('Verification error:', err);
      setError(err.message || 'Invalid verification code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (!canResend) return;
    
    try {
      setResendLoading(true);
      setError('');
      setMessage('');
      
      const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      
      console.log('Resending OTP for email:', email);
      
      const response = await fetch(`${API_BASE_URL}/resend-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email: email })
      });
      
      const data = await response.json();
      
      console.log('Resend response status:', response.status);
      console.log('Resend response data:', data);
      
      if (!response.ok) {
        // Handle lockout response
        const lockoutHeader = response.headers.get('X-Lockout-Seconds') || response.headers.get('x-lockout-seconds');
        console.log('Resend lockout header value:', lockoutHeader);
        
        if (response.status === 403 && lockoutHeader) {
          const lockoutSeconds = parseInt(lockoutHeader);
          console.log('Resend lockout detected, seconds:', lockoutSeconds);
          setIsLockedOut(true);
          setLockoutCountdown(lockoutSeconds);
          setError(data.detail || 'Too many incorrect attempts. Please wait.');
        } else {
          throw new Error(data.detail || 'Failed to resend code');
        }
        return;
      }
      
      setMessage('Verification code sent! Please check your email.');
      setCanResend(false);
      setCountdown(30); // 30 second countdown
      
      // Clear the current OTP input
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
      
    } catch (err) {
      console.error('Resend error:', err);
      setError(err.message || 'Failed to resend verification code. Please try again.');
    } finally {
      setResendLoading(false);
    }
  };

  // If email is not provided, show access denied
  if (!email) {
    return (
      <div className="min-h-screen bg-cover bg-center bg-no-repeat flex items-center justify-center p-4" style={{ backgroundImage: `url(${bgImage})` }}>
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Access Denied</h2>
          <p className="text-gray-600 mb-6">Please sign up first to verify your email.</p>
          <button
            onClick={() => navigate(routes.signup)}
            className="w-full text-white font-medium py-2 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 text-md"
            style={{ backgroundColor: 'var(--primary)' }}
          >
            Go to Sign Up
          </button>
        </div>
      </div>
    );
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
            
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">Verify Your Email</h2>
            <p className="text-gray-600 text-sm">
              We've sent a 6-digit verification code to<br />
              <span className="font-medium" style={{ color: 'var(--primary)' }}>{email}</span>
            </p>
          </div>
       <div className="px-6 pb-6 pt-0">

        {isLockedOut && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-center">
            <div className="flex items-center justify-center mb-2">
              <FaShieldAlt className="text-red-500 text-xl mr-2" />
              <span className="text-red-700 font-semibold text-lg">Account Locked</span>
            </div>
            <p className="text-red-600 text-sm mb-3">
              Too many incorrect attempts. Please wait before trying again.
            </p>
            <div className="bg-white rounded-md p-3 border border-red-200">
              <div className="text-red-800 text-sm font-medium mb-1">Time remaining:</div>
              <div className="text-red-700 text-2xl font-bold font-mono">
                {Math.floor(lockoutCountdown / 60).toString().padStart(2, '0')}:
                {(lockoutCountdown % 60).toString().padStart(2, '0')}
              </div>
            </div>
          </div>
        )}

        {!isLockedOut && error && (
          <div className=" text-red-700 px-3 py-1.5 text-center font-medium mb-4 text-sm">
            {error}
          </div>
        )}

        {!isLockedOut && message && (
          <div className="text-green-700 text-center font-medium mb-4 text-sm">
            {message}
          </div>
        )}

        <form onSubmit={(e) => { e.preventDefault(); handleVerify(); }}>
          <div className="flex justify-center gap-4 pt-3 mb-6">
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={el => inputRefs.current[index] = el}
                type="text"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={handlePaste}
                className={`w-10 h-10 text-center text-lg font-bold bg-white border rounded-md text-gray-900 focus:outline-none focus:ring-1 transition-all duration-200 ${
                  isLockedOut 
                    ? 'border-red-300 bg-red-50 text-red-400 cursor-not-allowed' 
                    : 'border-tileBorder focus:ring-tileBorder focus:border-tileBg hover:border-tileBorder'
                }`}
                disabled={loading || isLockedOut}
                autoComplete="off"
              />
            ))}
          </div>

          <button
            type="submit"
            disabled={loading || otp.join('').length !== 6 || isLockedOut}
            className={`w-full text-white font-medium py-2 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 text-md ${
              loading || otp.join('').length !== 6 || isLockedOut ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            style={{ backgroundColor: isLockedOut ? '#9CA3AF' : 'var(--primary)' }}
          >
            {loading ? 'Verifying...' : isLockedOut ? 'Account Locked' : 'Verify Email'}
          </button>
        </form>

        <div className="flex items-center justify-center gap-2 mt-4">
          <p className="text-gray-600 text-sm">
            Didn't receive the code?
          </p>
          <button
            onClick={handleResendCode}
            disabled={!canResend || resendLoading || isLockedOut}
            className="font-medium text-sm disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
            style={{ color: canResend && !resendLoading && !isLockedOut ? 'var(--primary)' : undefined }}
          >
            {resendLoading ? 'Sending...' : 
             isLockedOut ? 'Account Locked' :
             !canResend ? `Resend in ${countdown}s` : 
             'Resend OTP'}
          </button>
        </div>

        <div className="mt-4 text-center">
          <button
            onClick={() => navigate(routes.signup)}
            disabled={isLockedOut}
            className={`text-sm transition-colors font-medium ${
              isLockedOut ? 'text-gray-400 cursor-not-allowed' : ''
            }`}
            style={{ color: isLockedOut ? undefined : 'var(--primary)' }}
          >
            Back to Sign In
          </button>
        </div>
        </div>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;