import { useEffect, useId, useState } from 'react'
import { getApiBaseUrl } from '../config'
import {
  STAGE_LABELS_RU,
  STAGE_ORDER,
  indexOfStage,
} from '../domain/pipelineStages'

const POLL_MS = 2500

type JobStatusResponse = {
  job_id: number
  status: string
  stage: string
  progress_percent: number | null
  error: string | null
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

export function ProcessingPage({ jobId, onSetJobId }: Props) {
  const id = useId()
  const [draftId, setDraftId] = useState('')
  const [loading, setLoading] = useState(false)
  const [inputError, setInputError] = useState<string | null>(null)
  const [pollError, setPollError] = useState<string | null>(null)
  const [status, setStatus] = useState<JobStatusResponse | null>(null)

  useEffect(() => {
    if (jobId == null) {
      return
    }

    let cancelled = false

    async function load(isFirst: boolean) {
      if (isFirst) {
        setLoading(true)
      }
      try {
        const res = await fetch(
          `${getApiBaseUrl()}/videos/${jobId}/status`,
        )
        if (!res.ok) {
          const errData: unknown = await res.json()
          const detail =
            errData &&
            typeof errData === 'object' &&
            'detail' in errData &&
            typeof (errData as { detail: unknown }).detail === 'string'
              ? (errData as { detail: string }).detail
              : `HTTP ${res.status}`
          throw new Error(detail)
        }
        const data = (await res.json()) as JobStatusResponse
        if (!cancelled) {
          setStatus(data)
          setPollError(null)
        }
      } catch (e) {
        if (!cancelled && e instanceof Error) {
          setPollError(e.message)
          setStatus(null)
        }
      } finally {
        if (isFirst && !cancelled) {
          setLoading(false)
        }
      }
    }

    void load(true)
    const t = window.setInterval(() => {
      void load(false)
    }, POLL_MS)

    return () => {
      cancelled = true
      window.clearInterval(t)
    }
  }, [jobId])

  const currentIndex = status
    ? indexOfStage(status.stage)
    : 0

  return (
    <section className="processing" aria-labelledby={`${id}-h`}>
      <h2 className="processing__title" id={`${id}-h`}>
        Обработка
      </h2>
      {jobId == null ? (
        <div className="processing__form-block">
          <p className="processing__intro">
            Укажите идентификатор задачи (job_id), чтобы видеть этапы.
            Он выдаётся после загрузки на странице «Upload».
          </p>
          <div className="processing__form">
            <label className="processing__label" htmlFor={`${id}-job`}>
              job_id
            </label>
            <input
              className="processing__input"
              id={`${id}-job`}
              inputMode="numeric"
              value={draftId}
              onChange={(e) => setDraftId(e.target.value)}
              placeholder="например, 1"
            />
            <button
              type="button"
              className="processing__go"
              onClick={() => {
                const n = parseJobIdInput(draftId)
                if (n == null) {
                  setInputError('Введите положительное целое число.')
                  return
                }
                setInputError(null)
                onSetJobId(n)
              }}
            >
              Показать
            </button>
          </div>
          {inputError ? (
            <p className="processing__err" role="alert">
              {inputError}
            </p>
          ) : null}
        </div>
      ) : (
        <>
          <p className="processing__meta">
            <span className="processing__meta-item">
              <strong>job_id:</strong> {jobId}
            </span>
            {status ? (
              <>
                <span className="processing__meta-item">
                  <strong>статус:</strong> {status.status}
                </span>
                {status.progress_percent != null ? (
                  <span className="processing__meta-item">
                    <strong>прогресс:</strong> {status.progress_percent}%
                  </span>
                ) : null}
              </>
            ) : null}
            <button
              type="button"
              className="processing__change-id"
              onClick={() => {
                onSetJobId(null)
                setDraftId('')
                setStatus(null)
                setPollError(null)
              }}
            >
              Сменить job
            </button>
          </p>
          {loading && !status ? (
            <p className="processing__loading" role="status">
              Загрузка…
            </p>
          ) : null}
          {pollError ? (
            <p className="processing__err" role="alert">
              {pollError}
            </p>
          ) : null}
          {status?.error ? (
            <p className="processing__err" role="alert">
              Ошибка пайплайна: {status.error}
            </p>
          ) : null}
          <ol className="processing__steps" aria-label="Этапы обработки">
            {STAGE_ORDER.map((stageId, i) => {
              let mod = 'pending'
              if (i < currentIndex) {
                mod = 'done'
              } else if (i === currentIndex) {
                mod = 'active'
              }
              return (
                <li
                  key={stageId}
                  className={`processing__step processing__step--${mod}`}
                  aria-current={mod === 'active' ? 'step' : undefined}
                >
                  <span className="processing__step-num">{i + 1}.</span>
                  {STAGE_LABELS_RU[stageId]}
                </li>
              )
            })}
          </ol>
        </>
      )}
    </section>
  )
}
