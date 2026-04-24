/** Базовый URL API (корневой .env: VITE_API_BASE_URL). */
export function getApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base === 'string' && base.trim() !== '') {
    return base.replace(/\/$/, '')
  }
  return 'http://localhost:8005'
}
