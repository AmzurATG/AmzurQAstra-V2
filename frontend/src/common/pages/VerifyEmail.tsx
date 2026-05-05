import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@common/components/ui/Button'
import { signupApi } from '@common/api/signup'
import toast from 'react-hot-toast'

const OTP_LENGTH = 6
const RESEND_COOLDOWN = 30 // seconds

export default function VerifyEmail() {
  const navigate = useNavigate()
  const location = useLocation()
  const email = (location.state as any)?.email || ''

  const [otp, setOtp] = useState<string[]>(Array(OTP_LENGTH).fill(''))
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [resendLoading, setResendLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [isLockedOut, setIsLockedOut] = useState(false)
  const [lockoutCountdown, setLockoutCountdown] = useState(0)

  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  // Redirect if no email
  useEffect(() => {
    if (!email) navigate('/signup')
  }, [email, navigate])

  // Resend cooldown timer
  useEffect(() => {
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  // Lockout countdown timer
  useEffect(() => {
    if (lockoutCountdown <= 0) {
      if (isLockedOut) {
        setIsLockedOut(false)
        setError('')
        localStorage.removeItem(`lockoutEnd_${email}`)
      }
      return
    }
    const timer = setTimeout(() => setLockoutCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [lockoutCountdown, isLockedOut, email])

  // Restore lockout state from localStorage
  useEffect(() => {
    if (!email) return
    const stored = localStorage.getItem(`lockoutEnd_${email}`)
    if (stored) {
      const remaining = Math.floor((parseInt(stored) - Date.now()) / 1000)
      if (remaining > 0) {
        setIsLockedOut(true)
        setLockoutCountdown(remaining)
      } else {
        localStorage.removeItem(`lockoutEnd_${email}`)
      }
    }
  }, [email])

  // Persist lockout state
  useEffect(() => {
    if (isLockedOut && lockoutCountdown > 0) {
      localStorage.setItem(`lockoutEnd_${email}`, (Date.now() + lockoutCountdown * 1000).toString())
    }
  }, [isLockedOut, lockoutCountdown, email])

  const handleChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return
    const newOtp = [...otp]
    newOtp[index] = value.slice(-1)
    setOtp(newOtp)
    if (error) setError('')

    // Auto-focus next
    if (value && index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus()
    }

    // Auto-submit when all digits entered
    if (value && index === OTP_LENGTH - 1) {
      const code = newOtp.join('')
      if (code.length === OTP_LENGTH) {
        handleVerify(code)
      }
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
    if (e.key === 'ArrowRight' && index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus()
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      const code = otp.join('')
      if (code.length === OTP_LENGTH) handleVerify(code)
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH)
    if (!pasted) return
    const newOtp = pasted.split('').concat(Array(OTP_LENGTH).fill('')).slice(0, OTP_LENGTH)
    setOtp(newOtp)
    const nextIndex = Math.min(pasted.length, OTP_LENGTH - 1)
    inputRefs.current[nextIndex]?.focus()
    // Auto-submit if full paste
    if (pasted.length === OTP_LENGTH) {
      handleVerify(pasted)
    }
  }

  const handleVerify = useCallback(
    async (code?: string) => {
      const verificationCode = code || otp.join('')
      if (verificationCode.length !== OTP_LENGTH) {
        setError('Please enter all 6 digits')
        return
      }
      if (isLockedOut) return

      setIsLoading(true)
      setError('')
      try {
        const result = await signupApi.verifyOtp(email, verificationCode)
        if (result.success) {
          toast.success('Email verified! You can now sign in.')
          localStorage.removeItem(`lockoutEnd_${email}`)
          navigate('/login')
        }
      } catch (err: any) {
        const response = err?.response
        const detail = response?.data?.detail || 'Verification failed'

        // Handle lockout
        const lockoutSeconds = response?.headers?.['x-lockout-seconds']
        if (response?.status === 403 && lockoutSeconds) {
          const seconds = parseInt(lockoutSeconds)
          setIsLockedOut(true)
          setLockoutCountdown(seconds)
          setOtp(Array(OTP_LENGTH).fill(''))
          setError(detail)
        } else {
          setError(detail)
        }
      } finally {
        setIsLoading(false)
      }
    },
    [otp, email, isLockedOut, navigate]
  )

  const handleResend = async () => {
    if (countdown > 0 || resendLoading || isLockedOut) return
    setResendLoading(true)
    try {
      await signupApi.resendOtp(email)
      toast.success('New verification code sent!')
      setCountdown(RESEND_COOLDOWN)
      setOtp(Array(OTP_LENGTH).fill(''))
      setError('')
      inputRefs.current[0]?.focus()
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Failed to resend code'
      toast.error(detail)
    } finally {
      setResendLoading(false)
    }
  }

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}s`
  }

  if (!email) return null

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-primary-600">QAstra</h1>
            <h2 className="text-xl font-semibold text-gray-900 mt-4">Verify Your Email</h2>
            <p className="text-gray-600 text-sm mt-2">
              We've sent a 6-digit code to <strong>{email}</strong>
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
              {error}
            </div>
          )}

          {isLockedOut && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded-lg mb-4 text-sm text-center">
              Too many attempts. Try again in <strong>{formatTime(lockoutCountdown)}</strong>
            </div>
          )}

          {/* OTP Inputs */}
          <div className="flex justify-center gap-3 mb-6">
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={(el) => { inputRefs.current[index] = el }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={index === 0 ? handlePaste : undefined}
                disabled={isLockedOut}
                className="w-12 h-14 text-center text-2xl font-semibold border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 disabled:bg-gray-100"
                autoFocus={index === 0}
              />
            ))}
          </div>

          {/* Verify Button */}
          <Button
            onClick={() => handleVerify()}
            className="w-full"
            isLoading={isLoading}
            disabled={otp.join('').length !== OTP_LENGTH || isLockedOut}
          >
            Verify
          </Button>

          {/* Resend */}
          <div className="text-center mt-4">
            <p className="text-sm text-gray-600">
              Didn't receive the code?{' '}
              {countdown > 0 ? (
                <span className="text-gray-400">Resend in {countdown}s</span>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendLoading || isLockedOut}
                  className="text-primary-600 hover:text-primary-700 font-medium disabled:opacity-50"
                >
                  {resendLoading ? 'Sending...' : 'Resend code'}
                </button>
              )}
            </p>
          </div>

          <p className="text-center text-sm text-gray-600 mt-6">
            <button
              type="button"
              onClick={() => navigate('/signup')}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              &larr; Back to signup
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
