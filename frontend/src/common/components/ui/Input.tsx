import { clsx } from 'clsx'
import { InputHTMLAttributes, forwardRef, useMemo, useState } from 'react'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  /** Red asterisk on label without setting native `required` (e.g. conditional validation). */
  requiredMark?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, required, requiredMark, ...props }, ref) => {
    const showStar = Boolean(required || requiredMark)
    const [showPassword, setShowPassword] = useState(false)
    const isPasswordField = props.type === 'password'
    const resolvedType = useMemo(() => {
      if (!isPasswordField) return props.type
      return showPassword ? 'text' : 'password'
    }, [isPasswordField, props.type, showPassword])
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
            {showStar ? (
              <span className="text-red-500 ml-0.5" aria-hidden="true">
                *
              </span>
            ) : null}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={id}
            required={required}
            className={clsx(
              'block w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
              isPasswordField ? 'pr-10' : null,
              error ? 'border-red-300' : 'border-gray-300',
              className
            )}
            {...props}
            type={resolvedType}
          />
          {isPasswordField && (
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              title={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
            </button>
          )}
        </div>
        {error && (
          <p className="mt-1 text-sm text-red-600">{error}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
