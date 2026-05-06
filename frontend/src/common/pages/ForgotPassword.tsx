import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { passwordResetApi, SecurityQuestion } from '@common/api/passwordReset'
import toast from 'react-hot-toast'

type Step = 'email' | 'security' | 'reset'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('email')
  const [loading, setLoading] = useState(false)

  // Step 1 state
  const [email, setEmail] = useState('')

  // Step 2 state
  const [questions, setQuestions] = useState<SecurityQuestion[]>([])
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  // Step 3 state
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // --- Step 1: Submit email ---
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) {
      toast.error('Please enter your email address')
      return
    }

    setLoading(true)
    try {
      const res = await passwordResetApi.initiate(email.trim())
      setQuestions(res.security_questions)
      // Pre-populate answers object
      const initialAnswers: Record<number, string> = {}
      res.security_questions.forEach((q) => {
        initialAnswers[q.id] = ''
      })
      setAnswers(initialAnswers)
      setStep('security')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') {
        toast.error(detail)
      } else {
        toast.error('No account found with that email address.')
      }
    } finally {
      setLoading(false)
    }
  }

  // --- Step 2: Submit security answers ---
  const handleSecuritySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFieldErrors({})

    // Validate all answers filled
    const empty = questions.filter((q) => !answers[q.id]?.trim())
    if (empty.length > 0) {
      toast.error('Please answer all security questions')
      return
    }

    setLoading(true)
    try {
      const answerPayload = questions.map((q) => ({
        id: q.id,
        answer: answers[q.id].trim(),
      }))
      const res = await passwordResetApi.verifySecurity(email, answerPayload)
      console.log('Security verification response:', res)
      toast.success('Security answers verified! Check your email for the reset token.')
      setStep('reset')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail && typeof detail === 'object' && detail.field_errors) {
        setFieldErrors(detail.field_errors)
        toast.error(detail.message || 'Some answers are incorrect')
      } else if (typeof detail === 'string') {
        toast.error(detail)
      } else {
        toast.error('Failed to verify security answers')
      }
    } finally {
      setLoading(false)
    }
  }

  // --- Step 3: Submit new password ---
  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!resetToken.trim()) {
      toast.error('Please enter the reset token from your email')
      return
    }
    if (!newPassword) {
      toast.error('Please enter a new password')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await passwordResetApi.resetPassword(email, resetToken.trim(), newPassword, confirmPassword)
      toast.success('Password reset successfully! You can now login.')
      navigate('/login')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 422) {
        const errors = err?.response?.data?.details?.errors
        if (Array.isArray(errors) && errors.length > 0) {
          toast.error(errors[0].msg || 'Validation error')
        } else {
          toast.error('Validation error')
        }
      } else if (typeof detail === 'string') {
        toast.error(detail)
      } else {
        toast.error('Failed to reset password')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900">
            {step === 'email' && 'Forgot Password'}
            {step === 'security' && 'Security Verification'}
            {step === 'reset' && 'Reset Password'}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {step === 'email' && 'Enter your email to begin the password reset process'}
            {step === 'security' && 'Answer your security questions to verify your identity'}
            {step === 'reset' && 'Enter the reset token and your new password'}
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center space-x-2">
          {(['email', 'security', 'reset'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === s
                    ? 'bg-blue-600 text-white'
                    : (['email', 'security', 'reset'].indexOf(step) > i
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-600')
                }`}
              >
                {i + 1}
              </div>
              {i < 2 && <div className="w-8 h-0.5 bg-gray-300 mx-1" />}
            </div>
          ))}
        </div>

        {/* Step 1: Email */}
        {step === 'email' && (
          <form onSubmit={handleEmailSubmit} className="mt-8 space-y-6">
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Checking...' : 'Continue'}
            </Button>
            <div className="text-center">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                Back to Login
              </button>
            </div>
          </form>
        )}

        {/* Step 2: Security Questions */}
        {step === 'security' && (
          <form onSubmit={handleSecuritySubmit} className="mt-8 space-y-6">
            {questions.map((q) => (
              <div key={q.id}>
                <Input
                  label={q.question}
                  type="text"
                  value={answers[q.id] || ''}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  placeholder="Your answer"
                  required
                />
                {fieldErrors[String(q.id)] && (
                  <p className="mt-1 text-sm text-red-600">{fieldErrors[String(q.id)]}</p>
                )}
              </div>
            ))}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify Answers'}
            </Button>
            <div className="text-center">
              <button
                type="button"
                onClick={() => setStep('email')}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                Back
              </button>
            </div>
          </form>
        )}

        {/* Step 3: Reset Token + New Password */}
        {step === 'reset' && (
          <form onSubmit={handleResetSubmit} className="mt-8 space-y-6">
            <Input
              label="Reset Token"
              type="text"
              value={resetToken}
              onChange={(e) => setResetToken(e.target.value.toUpperCase())}
              placeholder="Enter 6-character token from email"
              maxLength={6}
              autoComplete="off"
              required
            />
            <Input
              label="New Password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter new password"
              autoComplete="new-password"
              required
            />
            <Input
              label="Confirm Password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm new password"
              autoComplete="new-password"
              required
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Resetting...' : 'Reset Password'}
            </Button>
            <div className="text-center">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                Back to Login
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
