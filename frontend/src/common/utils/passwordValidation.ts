/** Client-side password rules (aligned with backend signup / password reset schemas). */

export function validatePassword(password: string): string | undefined {
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

type ApiValidationError = { loc?: (string | number)[]; msg?: string }

const API_FIELD_TO_FORM: Record<string, string> = {
  new_password: 'newPassword',
  confirm_password: 'confirmPassword',
  password: 'password',
}

function sanitizeValidationMessage(msg: string): string {
  return msg.replace(/^Value error,\s*/i, '')
}

/** Map 422 validation errors from the API into form field keys and a combined message. */
export function parseApiValidationErrors(
  errors: ApiValidationError[],
  fieldMap: Record<string, string> = API_FIELD_TO_FORM
): { fieldErrors: Record<string, string>; message: string } {
  const fieldErrors: Record<string, string> = {}
  const messages: string[] = []

  for (const err of errors) {
    const rawMsg = err.msg ? sanitizeValidationMessage(err.msg) : 'Validation error'
    const loc = err.loc ?? []
    const fieldKey = [...loc].reverse().find((part) => typeof part === 'string' && fieldMap[part])
    if (typeof fieldKey === 'string') {
      const formKey = fieldMap[fieldKey]
      if (!fieldErrors[formKey]) fieldErrors[formKey] = rawMsg
    }
    if (!messages.includes(rawMsg)) messages.push(rawMsg)
  }

  return {
    fieldErrors,
    message: messages.join('; ') || 'Validation error',
  }
}
