import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@common/components/ui/Button'
import { signupApi } from '@common/api/signup'
import toast from 'react-hot-toast'

const AVAILABLE_QUESTIONS = [
  'What was the name of your first pet?',
  'What city were you born in?',
  "What was your mother's maiden name?",
  'What was the name of your elementary school?',
  'What is your favorite color?',
]

interface FormErrors {
  question1?: string
  answer1?: string
  question2?: string
  answer2?: string
  form?: string
}

export default function SecurityQuestions() {
  const navigate = useNavigate()
  const location = useLocation()
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<FormErrors>({})
  const [question1, setQuestion1] = useState('')
  const [answer1, setAnswer1] = useState('')
  const [question2, setQuestion2] = useState('')
  const [answer2, setAnswer2] = useState('')

  const userData = (location.state as any)?.userData

  useEffect(() => {
    if (!userData) {
      navigate('/signup')
    }
  }, [userData, navigate])

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}
    if (!question1) newErrors.question1 = 'Please select a security question'
    if (!answer1.trim()) newErrors.answer1 = 'Answer is required'
    if (!question2) newErrors.question2 = 'Please select a security question'
    if (!answer2.trim()) newErrors.answer2 = 'Answer is required'
    if (question1 && question2 && question1 === question2) {
      newErrors.question2 = 'Please select a different question'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    setIsLoading(true)
    try {
      const signupData = {
        ...userData,
        security_questions: [
          { question: question1, answer: answer1 },
          { question: question2, answer: answer2 },
        ],
      }

      const result = await signupApi.signup(signupData)
      toast.success(result.message)
      navigate('/verify-email', { state: { email: userData.email } })
    } catch (error: any) {
      const response = error?.response
      // Handle lockout — redirect to OTP page
      const lockoutHeader = response?.headers?.['x-lockout-seconds']
      if (response?.status === 403 && lockoutHeader) {
        navigate('/verify-email', { state: { email: userData.email } })
        return
      }
      // Extract validation error messages (422) or generic detail
      let detail = response?.data?.detail || 'Failed to complete signup'
      if (response?.status === 422 && response?.data?.details?.errors) {
        const fieldErrors = response.data.details.errors
          .map((e: any) => e.msg)
          .join('; ')
        detail = fieldErrors || response?.data?.message || detail
      }
      toast.error(detail)
      setErrors({ form: detail })
    } finally {
      setIsLoading(false)
    }
  }

  if (!userData) return null

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 py-8">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-primary-600">QAstra</h1>
            <h2 className="text-xl font-semibold text-gray-900 mt-4">Security Questions</h2>
            <p className="text-gray-600 text-sm mt-2">
              These will be used to verify your identity if you need to reset your password.
            </p>
          </div>

          {errors.form && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
              {errors.form}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Question 1 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Question 1 <span className="text-red-500">*</span>
              </label>
              <select
                value={question1}
                onChange={(e) => {
                  setQuestion1(e.target.value)
                  if (errors.question1) setErrors((p) => ({ ...p, question1: undefined }))
                }}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value="">Select a question...</option>
                {AVAILABLE_QUESTIONS.map((q) => (
                  <option key={q} value={q} disabled={q === question2}>
                    {q}
                  </option>
                ))}
              </select>
              {errors.question1 && <p className="mt-1 text-sm text-red-600">{errors.question1}</p>}
            </div>

            <div>
              <label htmlFor="answer1" className="block text-sm font-medium text-gray-700 mb-1">
                Answer 1 <span className="text-red-500">*</span>
              </label>
              <input
                id="answer1"
                type="text"
                value={answer1}
                onChange={(e) => {
                  setAnswer1(e.target.value)
                  if (errors.answer1) setErrors((p) => ({ ...p, answer1: undefined }))
                }}
                placeholder="Your answer"
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
              {errors.answer1 && <p className="mt-1 text-sm text-red-600">{errors.answer1}</p>}
            </div>

            {/* Question 2 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Question 2 <span className="text-red-500">*</span>
              </label>
              <select
                value={question2}
                onChange={(e) => {
                  setQuestion2(e.target.value)
                  if (errors.question2) setErrors((p) => ({ ...p, question2: undefined }))
                }}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value="">Select a question...</option>
                {AVAILABLE_QUESTIONS.map((q) => (
                  <option key={q} value={q} disabled={q === question1}>
                    {q}
                  </option>
                ))}
              </select>
              {errors.question2 && <p className="mt-1 text-sm text-red-600">{errors.question2}</p>}
            </div>

            <div>
              <label htmlFor="answer2" className="block text-sm font-medium text-gray-700 mb-1">
                Answer 2 <span className="text-red-500">*</span>
              </label>
              <input
                id="answer2"
                type="text"
                value={answer2}
                onChange={(e) => {
                  setAnswer2(e.target.value)
                  if (errors.answer2) setErrors((p) => ({ ...p, answer2: undefined }))
                }}
                placeholder="Your answer"
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
              {errors.answer2 && <p className="mt-1 text-sm text-red-600">{errors.answer2}</p>}
            </div>

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Submit & Verify Email
            </Button>
          </form>

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
