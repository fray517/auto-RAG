/** Читаемое сообщение об ошибке из ответа FastAPI. */

function formatValidationItems(items: unknown): string | null {
  if (!Array.isArray(items)) {
    return null
  }
  const parts = items
    .map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) {
        return String((item as { msg: unknown }).msg)
      }
      return null
    })
    .filter(Boolean) as string[]
  if (parts.length > 0) {
    return parts.join(' ')
  }
  return null
}

export function formatApiErrorMessage(
  data: unknown,
  fallback: string,
): string {
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>
    if (typeof obj.detail === 'string') {
      return obj.detail
    }
    if (Array.isArray(obj.detail)) {
      const fromDetail = formatValidationItems(obj.detail)
      if (fromDetail) {
        return fromDetail
      }
    }
    const fromErrors = formatValidationItems(obj.errors)
    if (fromErrors) {
      return fromErrors
    }
  }
  return fallback
}
