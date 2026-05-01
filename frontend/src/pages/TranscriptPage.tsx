import { type FormEvent, useEffect, useId, useState } from 'react'
import { getApiBaseUrl } from '../config'

type RawTranscriptResponse = {
  job_id: number
  content: string | null
  updated_at: string | null
}

type OcrItem = {
  id: number
  sort_order: number
  source_hint: string | null
  text: string | null
}

type OcrResultsResponse = {
  job_id: number
  items: OcrItem[]
}

type Props = {
  jobId: number | null
  onSetJobId: (id: number | null) => void
}

function parseJobIdInput(raw: string): number | null {
  const n = parseInt(raw.trim(), 10)
  if (Number.isNaN(n) || n < 1) {
    return null
  }
  return n
}

function getApiError(data: unknown, fallback: string): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
  }
  return fallback
}

function formatUpdatedAt(value: string | null): string {
  if (!value) {
    return 'ещё не сохранялось'
  }
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) {
    return value
  }
  return d.toLocaleString('ru-RU')
}

export function TranscriptPage({ jobId, onSetJobId }: Props) {
  const id = useId()
  const [draftId, setDraftId] = useState('')
  const [content, setContent] = useState('')
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [ocrItems, setOcrItems] = useState<OcrItem[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (jobId == null) {
      return
    }

    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      setMessage(null)
      try {
        const base = getApiBaseUrl()
        const [rawRes, ocrRes] = await Promise.all([
          fetch(`${base}/videos/${jobId}/raw-transcript`),
          fetch(`${base}/videos/${jobId}/ocr`),
        ])
        const rawData: unknown = await rawRes.json()
        const ocrData: unknown = await ocrRes.json()
        if (!rawRes.ok) {
          throw new Error(
            getApiError(rawData, `Raw transcript HTTP ${rawRes.status}`),
          )
        }
        if (!ocrRes.ok) {
          throw new Error(getApiError(ocrData, `OCR HTTP ${ocrRes.status}`))
        }
        if (cancelled) {
          return
        }
        const raw = rawData as RawTranscriptResponse
        const ocr = ocrData as OcrResultsResponse
        setContent(raw.content ?? '')
        setUpdatedAt(raw.updated_at)
        setOcrItems(ocr.items)
      } catch (e) {
        if (!cancelled && e instanceof Error) {
          setError(e.message)
          setContent('')
          setUpdatedAt(null)
          setOcrItems([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [jobId])

  async function saveRawTranscript() {
    if (jobId == null) {
      return
    }
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/videos/${jobId}/raw-transcript`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: JSON.stringify({ content }),
        },
      )
      const data: unknown = await res.json()
      if (!res.ok) {
        throw new Error(getApiError(data, `HTTP ${res.status}`))
      }
      const saved = data as RawTranscriptResponse
      setContent(saved.content ?? '')
      setUpdatedAt(saved.updated_at)
      setMessage('Сырая транскрипция сохранена.')
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message)
      }
    } finally {
      setSaving(false)
    }
  }

  function submitJobId(e: FormEvent) {
    e.preventDefault()
    const n = parseJobIdInput(draftId)
    if (n == null) {
      setError('Введите положительное целое число.')
      return
    }
    setError(null)
    onSetJobId(n)
  }

  return (
    <section className="transcript" aria-labelledby={`${id}-h`}>
      <h2 className="transcript__title" id={`${id}-h`}>
        Transcript
      </h2>
      <p className="transcript__intro">
        Просмотр OCR и ручная правка сырой транскрипции.
      </p>

      {jobId == null ? (
        <form className="transcript__job-form" onSubmit={submitJobId}>
          <label className="transcript__label" htmlFor={`${id}-job`}>
            job_id
          </label>
          <input
            className="transcript__job-input"
            id={`${id}-job`}
            inputMode="numeric"
            value={draftId}
            onChange={(e) => setDraftId(e.target.value)}
            placeholder="например, 9"
          />
          <button className="transcript__btn" type="submit">
            Открыть
          </button>
        </form>
      ) : (
        <>
          <div className="transcript__meta">
            <span>
              <strong>job_id:</strong> {jobId}
            </span>
            <span>
              <strong>обновлено:</strong> {formatUpdatedAt(updatedAt)}
            </span>
            <button
              className="transcript__change-id"
              type="button"
              onClick={() => {
                onSetJobId(null)
                setDraftId('')
                setContent('')
                setUpdatedAt(null)
                setOcrItems([])
                setError(null)
                setMessage(null)
              }}
            >
              Сменить job
            </button>
          </div>

          {loading ? (
            <p className="transcript__muted" role="status">
              Загрузка транскрипции…
            </p>
          ) : null}

          <div className="transcript__grid">
            <section
              className="transcript__panel"
              aria-labelledby={`${id}-raw-h`}
            >
              <h3 className="transcript__subtitle" id={`${id}-raw-h`}>
                Сырая транскрипция
              </h3>
              <textarea
                className="transcript__textarea"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Сырой транскрипт появится здесь после STT."
                disabled={loading || saving}
              />
              <button
                className="transcript__btn transcript__btn--primary"
                type="button"
                disabled={loading || saving}
                onClick={() => {
                  void saveRawTranscript()
                }}
              >
                {saving ? 'Сохранение…' : 'Сохранить'}
              </button>
            </section>

            <section
              className="transcript__panel"
              aria-labelledby={`${id}-ocr-h`}
            >
              <h3 className="transcript__subtitle" id={`${id}-ocr-h`}>
                OCR по ключевым кадрам
              </h3>
              {ocrItems.length === 0 ? (
                <p className="transcript__muted">
                  OCR-результатов пока нет.
                </p>
              ) : (
                <ol className="transcript__ocr-list">
                  {ocrItems.map((item) => (
                    <li className="transcript__ocr-item" key={item.id}>
                      <p className="transcript__ocr-source">
                        {item.source_hint ?? `кадр ${item.sort_order + 1}`}
                      </p>
                      <p className="transcript__ocr-text">
                        {item.text || 'Текст не распознан.'}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>

          <section className="transcript__panel transcript__clean">
            <h3 className="transcript__subtitle">
              Очищенная транскрипция
            </h3>
            <p className="transcript__muted">
              Место подготовлено для шага 6.1.
            </p>
          </section>
        </>
      )}

      {error ? (
        <p className="transcript__err" role="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="transcript__ok" role="status">
          {message}
        </p>
      ) : null}
    </section>
  )
}
