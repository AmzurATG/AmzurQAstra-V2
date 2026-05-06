import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { signupApi } from '@common/api/signup'
import toast from 'react-hot-toast'

const FREE_EMAIL_PROVIDERS = [
  'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
  'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
  'zoho.com', 'yandex.com', 'gmx.com', 'live.com'
  //, 'mailinator.com',
]

interface FormData {
  firstName: string
  lastName: string
  companyName: string
  email: string
  countryCode: string
  phoneNumber: string
  password: string
  confirmPassword: string
}

interface FormErrors {
  firstName?: string
  lastName?: string
  companyName?: string
  email?: string
  phoneNumber?: string
  password?: string
  confirmPassword?: string
  form?: string
}

export default function Signup() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState<FormData>({
    firstName: '',
    lastName: '',
    companyName: '',
    email: '',
    countryCode: '+1',
    phoneNumber: '',
    password: '',
    confirmPassword: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})

  const validateName = (name: string, fieldName: string): string | undefined => {
    if (!name.trim()) return `${fieldName} is required`
    if (name.length > 50) return `${fieldName} must not exceed 50 characters`
    if (!/^[a-zA-Z\s-]+$/.test(name)) return `${fieldName} can only contain letters, spaces, and hyphens`
    return undefined
  }

  const validateEmail = (email: string): string | undefined => {
    if (!email.trim()) return 'Business email is required'
    const emailRegex = /^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/
    if (!emailRegex.test(email)) return 'Please enter a valid email address'
    const domain = email.split('@')[1].toLowerCase()
    if (FREE_EMAIL_PROVIDERS.includes(domain)) return 'Please use a business email address (you@company.com)'
    return undefined
  }

  const validatePassword = (password: string): string | undefined => {
    const missing: string[] = []
    if (password.length < 8) missing.push('at least 8 characters')
    if (password.length > 64) missing.push('no more than 64 characters')
    if (!/[A-Z]/.test(password)) missing.push('one uppercase letter')
    if (!/[a-z]/.test(password)) missing.push('one lowercase letter')
    if (!/[0-9]/.test(password)) missing.push('one number')
    if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) missing.push('one special character')
    if (/\s/.test(password)) missing.push('no whitespace')
    if (missing.length > 0) return `Password must contain: ${missing.join(', ')}`
    return undefined
  }

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}
    newErrors.firstName = validateName(formData.firstName, 'First name')
    newErrors.lastName = validateName(formData.lastName, 'Last name')
    if (!formData.companyName.trim()) newErrors.companyName = 'Company name is required'
    else if (formData.companyName.length < 2) newErrors.companyName = 'Company name must be at least 2 characters'
    else if (formData.companyName.length > 100) newErrors.companyName = 'Company name must not exceed 100 characters'
    newErrors.email = validateEmail(formData.email)
    newErrors.password = validatePassword(formData.password)
    if (!formData.confirmPassword) newErrors.confirmPassword = 'Please confirm your password'
    else if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Passwords do not match'

    // Remove undefined entries
    const filtered = Object.fromEntries(Object.entries(newErrors).filter(([, v]) => v !== undefined))
    setErrors(filtered)
    return Object.keys(filtered).length === 0
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    // Clear error on change
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    setIsLoading(true)
    try {
      // Check if email already exists
      const { exists } = await signupApi.checkEmail(formData.email)
      if (exists) {
        setErrors({ email: 'This email is already registered' })
        setIsLoading(false)
        return
      }

      // Navigate to security questions with user data
      navigate('/security-questions', {
        state: {
          userData: {
            first_name: formData.firstName,
            last_name: formData.lastName,
            company_name: formData.companyName,
            email: formData.email,
            country_code: formData.countryCode || undefined,
            phone_number: formData.phoneNumber || undefined,
            password: formData.password,
            confirm_password: formData.confirmPassword,
          },
        },
      })
    } catch (error: any) {
      const response = error?.response
      let detail = response?.data?.detail || 'An error occurred. Please try again.'
      // Extract field-specific validation errors (422)
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 py-8">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-primary-600">QAstra</h1>
            <p className="text-gray-600 mt-2">Create your account</p>
          </div>

          {errors.form && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
              {errors.form}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input
                id="firstName"
                name="firstName"
                label="First Name"
                value={formData.firstName}
                onChange={handleChange}
                placeholder="John"
                error={errors.firstName}
                required
              />
              <Input
                id="lastName"
                name="lastName"
                label="Last Name"
                value={formData.lastName}
                onChange={handleChange}
                placeholder="Doe"
                error={errors.lastName}
                required
              />
            </div>

            <Input
              id="companyName"
              name="companyName"
              label="Company Name"
              value={formData.companyName}
              onChange={handleChange}
              placeholder="Acme Corp"
              error={errors.companyName}
              required
            />

            <Input
              id="email"
              name="email"
              type="email"
              label="Business Email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@company.com"
              error={errors.email}
              required
            />

            <div className="grid grid-cols-3 gap-2">
              <Input
                id="countryCode"
                name="countryCode"
                label="Code"
                value={formData.countryCode}
                onChange={handleChange}
                placeholder="+1"
              />
              <div className="col-span-2">
                <Input
                  id="phoneNumber"
                  name="phoneNumber"
                  label="Phone (optional)"
                  value={formData.phoneNumber}
                  onChange={handleChange}
                  placeholder="5551234567"
                  error={errors.phoneNumber}
                />
              </div>
            </div>

            <Input
              id="password"
              name="password"
              type="password"
              label="Password"
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              error={errors.password}
              required
              autoComplete="new-password"
            />

            <Input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              label="Confirm Password"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="••••••••"
              error={errors.confirmPassword}
              required
              autoComplete="new-password"
            />

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Continue
            </Button>
          </form>

          <p className="text-center text-sm text-gray-600 mt-6">
            Already have an account?{' '}
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
