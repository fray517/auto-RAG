import { useEffect, useId, useState } from 'react'
import { formatApiErrorMessage } from '../api/apiError'
import { getApiBaseUrl } from '../config'
import {
  STAGE_LABELS_RU,
  STAGE_ORDER,
  indexOfStage,
  labelForStage,
} from '../domain/pipelineStages'

const POLL_MS = 2500

type JobStatusResponse = {
  job_id: number
  status: string
  stage: string
  progress_percent: number | null
  error: string | null
}

type DeleteJobResponse = {
  job_id: number
  deleted_records: Record<string, number>
  deleted_files: string[]
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
  const [deleting, setDeleting] = useState(false)
  const [inputError, setInputError] = useState<string | null>(null)
  const [pollError, setPollError] = useState<string | null>(null)
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null)
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
        const data: unknown = await res.json()
        if (!res.ok) {
          throw new Error(
            formatApiErrorMessage(data, `HTTP ${res.status}`),
          )
        }
        const payload = data as JobStatusResponse
        if (!cancelled) {
          setStatus(payload)
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

  async function deleteCurrentJob() {
    if (jobId == null || deleting) {
      return
    }
    const ok = window.confirm(
      `Удалить job ${jobId} и все связанные данные?`,
    )
    if (!ok) {
      return
    }

    setDeleting(true)
    setPollError(null)
    setDeleteMessage(null)
    try {
      const res = await fetch(`${getApiBaseUrl()}/videos/${jobId}`, {
        method: 'DELETE',
      })
      const data: unknown = await res.json()
      if (!res.ok) {
        throw new Error(
          formatApiErrorMessage(data, `HTTP ${res.status}`),
        )
      }
      const deleted = data as DeleteJobResponse
      const recordsCount = Object.values(deleted.deleted_records).reduce(
        (sum, value) => sum + value,
        0,
      )
      setDeleteMessage(
        `Job ${deleted.job_id} удалена. Записей: ${recordsCount}, ` +
          `путей: ${deleted.deleted_files.length}.`,
      )
      setStatus(null)
      setDraftId('')
      onSetJobId(null)
    } catch (e) {
      if (e instanceof Error) {
        setPollError(e.message)
      }
    } finally {
      setDeleting(false)
    }
  }

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
          {deleteMessage ? (
            <p className="processing__ok" role="status">
              {deleteMessage}
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
              disabled={deleting}
              onClick={() => {
                onSetJobId(null)
                setDraftId('')
                setStatus(null)
                setPollError(null)
              }}
            >
              Сменить job
            </button>
            <button
              type="button"
              className="processing__delete-id"
              disabled={deleting}
              onClick={() => {
                void deleteCurrentJob()
              }}
            >
              {deleting ? 'Удаление…' : 'Удалить job'}
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
            <div className="processing__err-block" role="alert">
              <p className="processing__err-title">Сбой обработки</p>
              <p className="processing__err-stage">
                Этап:{' '}
                <strong>{labelForStage(status.stage)}</strong>
                <span className="processing__err-stage-id">
                  {' '}
                  ({status.stage})
                </span>
              </p>
              <p className="processing__err-text">{status.error}</p>
            </div>
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
