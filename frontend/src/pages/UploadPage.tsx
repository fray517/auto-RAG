import { type FormEvent, useId, useState } from 'react'
import { getApiBaseUrl } from '../config'

type UploadResponse = {
  job_id: number
  status: string
  filename: string
  stored_path: string
}

function formatApiError(data: unknown): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: unknown }).msg)
          }
          return null
        })
        .filter(Boolean)
      if (parts.length > 0) {
        return parts.join(' ')
      }
    }
  }
  return 'Ошибка запроса'
}

type UploadPageProps = {
  /** Автоматический переход к обработке с этим job_id. */
  onJobCreated?: (jobId: number) => void
}

export function UploadPage({ onJobCreated }: UploadPageProps) {
  const id = useId()
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    if (!file) {
      setError('Выберите видеофайл.')
      return
    }
    setLoading(true)
    try {
      const body = new FormData()
      body.append('file', file)
      const res = await fetch(`${getApiBaseUrl()}/videos/upload`, {
        method: 'POST',
        body,
      })
      const data: unknown = await res.json()
      if (!res.ok) {
        setError(formatApiError(data))
        return
      }
      const u = data as UploadResponse
      setResult(u)
      onJobCreated?.(u.job_id)
    } catch {
      setError('Не удалось связаться с сервером. Проверьте сеть и API.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="upload" aria-labelledby={`${id}-h`}>
      <h2 className="upload__title" id={`${id}-h`}>
        Загрузка видео
      </h2>
      <p className="upload__hint">
        Форматы: mp4, mov, avi, mkv, webm.
      </p>
      <form className="upload__form" onSubmit={onSubmit}>
        <div className="upload__field">
          <label className="upload__label" htmlFor={`${id}-file`}>
            Файл
          </label>
          <input
            className="upload__input"
            id={`${id}-file`}
            name="file"
            type="file"
            accept=".mp4,.mov,.avi,.mkv,.webm,video/*"
            disabled={loading}
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null
              setFile(f)
              setError(null)
              setResult(null)
            }}
          />
        </div>
        <button
          className="upload__submit"
          type="submit"
          disabled={loading || !file}
        >
          {loading ? 'Загрузка…' : 'Загрузить'}
        </button>
      </form>
      {error ? (
        <p className="upload__err" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="upload__ok" role="status">
          <p className="upload__ok-line">
            <strong>job_id:</strong> {result.job_id}
          </p>
          <p className="upload__ok-line">
            <strong>статус:</strong> {result.status}
          </p>
          <p className="upload__ok-line">
            <strong>файл:</strong> {result.filename}
          </p>
        </div>
      ) : null}
    </section>
  )
}
