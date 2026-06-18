/** Normalize and validate a local phone number (digits only, 7–15 chars). */
export function normalizePhoneDigits(phone: string, countryCode?: string): string {
  let digits = phone.replace(/\D/g, '')
  const cc = (countryCode || '').replace(/\D/g, '')
  if (cc && digits.startsWith(cc)) {
    digits = digits.slice(cc.length)
  }
  return digits
}

export function validatePhoneNumber(
  phone: string,
  countryCode?: string
): string | undefined {
  if (!phone.trim()) {
    return 'Phone number is required'
  }
  const local = normalizePhoneDigits(phone, countryCode)
  if (local.length < 7 || local.length > 15) {
    return 'Phone number must be 7–15 digits'
  }
  return undefined
}
