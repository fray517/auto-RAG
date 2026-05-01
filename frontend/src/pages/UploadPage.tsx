import { type FormEvent, useId, useRef, useState } from 'react'
import { getApiBaseUrl } from '../config'

type UploadResponse = {
  job_id: number
  status: string
  filename: string
  stored_path: string
}

type SlideItem = {
  id: number
  sort_order: number
  source_hint: string
  image_url: string
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
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [slides, setSlides] = useState<SlideItem[]>([])
  const [slideSaving, setSlideSaving] = useState(false)
  const [slideError, setSlideError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setSlides([])
    setSlideError(null)
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

  async function captureSlide() {
    if (!result || !videoRef.current) {
      return
    }
    setSlideSaving(true)
    setSlideError(null)
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/videos/${result.job_id}/slides`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: JSON.stringify({
            timestamp_seconds: videoRef.current.currentTime,
          }),
        },
      )
      const data: unknown = await res.json()
      if (!res.ok) {
        setSlideError(formatApiError(data))
        return
      }
      setSlides((items) => [...items, data as SlideItem])
    } catch {
      setSlideError('Не удалось сохранить слайд.')
    } finally {
      setSlideSaving(false)
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
              setSlides([])
              setSlideError(null)
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
      {result ? (
        <div className="upload__video-block">
          <video
            ref={videoRef}
            className="upload__video"
            controls
            src={`${getApiBaseUrl()}/videos/${result.job_id}/file`}
          >
            Ваш браузер не поддерживает просмотр видео.
          </video>
          <button
            className="upload__slide-btn"
            type="button"
            disabled={slideSaving}
            onClick={() => {
              void captureSlide()
            }}
          >
            {slideSaving ? 'Сохраняю слайд…' : 'Сделать слайд'}
          </button>
          {slideError ? (
            <p className="upload__err" role="alert">
              {slideError}
            </p>
          ) : null}
          {slides.length > 0 ? (
            <div className="upload__slides">
              <h3 className="upload__slides-title">Выбранные слайды</h3>
              <ol className="upload__slides-list">
                {slides.map((item) => (
                  <li className="upload__slide" key={item.id}>
                    <img
                      className="upload__slide-img"
                      src={`${getApiBaseUrl()}${item.image_url}`}
                      alt={`Слайд ${item.sort_order + 1}`}
                    />
                    <span className="upload__slide-name">
                      {item.source_hint}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
