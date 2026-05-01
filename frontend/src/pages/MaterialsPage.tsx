import { type FormEvent, useEffect, useId, useState } from 'react'
import { getApiBaseUrl } from '../config'

type MaterialKind = 'summary' | 'manual-guide' | 'checklist'

type MaterialResponse = {
  job_id: number
  content: string | null
  updated_at: string | null
}

type MaterialState = {
  content: string
  updatedAt: string | null
  saving: boolean
  generating: boolean
}

type MaterialConfig = {
  kind: MaterialKind
  title: string
  description: string
  emptyText: string
  savedText: string
  generatedText: string
  rows: number
}

type Props = {
  jobId: number | null
  onSetJobId: (id: number | null) => void
}

const MATERIALS: MaterialConfig[] = [
  {
    kind: 'summary',
    title: 'Конспект',
    description: 'Краткое структурированное содержание видео.',
    emptyText: 'Конспект ещё не создан.',
    savedText: 'Конспект сохранён.',
    generatedText: 'Конспект сгенерирован.',
    rows: 14,
  },
  {
    kind: 'manual-guide',
    title: 'Методичка',
    description: 'Основной учебный документ с разделами и примерами.',
    emptyText: 'Методичка ещё не создана.',
    savedText: 'Методичка сохранена.',
    generatedText: 'Методичка сгенерирована.',
    rows: 20,
  },
  {
    kind: 'checklist',
    title: 'Чек-лист',
    description: 'Практические проверяемые пункты по материалу.',
    emptyText: 'Чек-лист ещё не создан.',
    savedText: 'Чек-лист сохранён.',
    generatedText: 'Чек-лист сгенерирован.',
    rows: 14,
  },
]

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

function emptyMaterial(): MaterialState {
  return {
    content: '',
    updatedAt: null,
    saving: false,
    generating: false,
  }
}

function makeInitialMaterials(): Record<MaterialKind, MaterialState> {
  return {
    summary: emptyMaterial(),
    'manual-guide': emptyMaterial(),
    checklist: emptyMaterial(),
  }
}

export function MaterialsPage({ jobId, onSetJobId }: Props) {
  const id = useId()
  const [draftId, setDraftId] = useState('')
  const [materials, setMaterials] = useState(makeInitialMaterials)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (jobId == null) {
      return
    }

    let cancelled = false

    async function load() {
      setLoading(true)
      setMessage(null)
      setError(null)
      try {
        const base = getApiBaseUrl()
        const responses = await Promise.all(
          MATERIALS.map(async (item) => {
            const res = await fetch(`${base}/videos/${jobId}/${item.kind}`)
            const data: unknown = await res.json()
            if (!res.ok) {
              throw new Error(getApiError(data, `${item.title}: HTTP ${res.status}`))
            }
            return [item.kind, data as MaterialResponse] as const
          }),
        )
        if (cancelled) {
          return
        }
        const next = makeInitialMaterials()
        for (const [kind, data] of responses) {
          next[kind] = {
            ...next[kind],
            content: data.content ?? '',
            updatedAt: data.updated_at,
          }
        }
        setMaterials(next)
      } catch (e) {
        if (!cancelled && e instanceof Error) {
          setError(e.message)
          setMaterials(makeInitialMaterials())
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

  function updateMaterial(kind: MaterialKind, patch: Partial<MaterialState>) {
    setMaterials((current) => ({
      ...current,
      [kind]: {
        ...current[kind],
        ...patch,
      },
    }))
  }

  async function generateMaterial(config: MaterialConfig) {
    if (jobId == null) {
      return
    }
    updateMaterial(config.kind, { generating: true })
    setMessage(null)
    setError(null)
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/videos/${jobId}/${config.kind}/generate`,
        { method: 'POST' },
      )
      const data: unknown = await res.json()
      if (!res.ok) {
        throw new Error(getApiError(data, `HTTP ${res.status}`))
      }
      const saved = data as MaterialResponse
      updateMaterial(config.kind, {
        content: saved.content ?? '',
        updatedAt: saved.updated_at,
      })
      setMessage(config.generatedText)
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message)
      }
    } finally {
      updateMaterial(config.kind, { generating: false })
    }
  }

  async function saveMaterial(config: MaterialConfig) {
    if (jobId == null) {
      return
    }
    updateMaterial(config.kind, { saving: true })
    setMessage(null)
    setError(null)
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/videos/${jobId}/${config.kind}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: JSON.stringify({
            content: materials[config.kind].content,
          }),
        },
      )
      const data: unknown = await res.json()
      if (!res.ok) {
        throw new Error(getApiError(data, `HTTP ${res.status}`))
      }
      const saved = data as MaterialResponse
      updateMaterial(config.kind, {
        content: saved.content ?? '',
        updatedAt: saved.updated_at,
      })
      setMessage(config.savedText)
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message)
      }
    } finally {
      updateMaterial(config.kind, { saving: false })
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
    <section className="materials" aria-labelledby={`${id}-h`}>
      <h2 className="materials__title" id={`${id}-h`}>
        Materials
      </h2>
      <p className="materials__intro">
        Итоговые материалы: конспект, методичка и чек-лист.
      </p>

      {jobId == null ? (
        <form className="materials__job-form" onSubmit={submitJobId}>
          <label className="materials__label" htmlFor={`${id}-job`}>
            job_id
          </label>
          <input
            className="materials__job-input"
            id={`${id}-job`}
            inputMode="numeric"
            value={draftId}
            onChange={(e) => setDraftId(e.target.value)}
            placeholder="например, 15"
          />
          <button className="materials__btn" type="submit">
            Открыть
          </button>
        </form>
      ) : (
        <>
          <div className="materials__meta">
            <span>
              <strong>job_id:</strong> {jobId}
            </span>
            <button
              className="materials__change-id"
              type="button"
              onClick={() => {
                onSetJobId(null)
                setDraftId('')
                setMaterials(makeInitialMaterials())
                setError(null)
                setMessage(null)
              }}
            >
              Сменить job
            </button>
          </div>

          {loading ? (
            <p className="materials__muted" role="status">
              Загрузка материалов…
            </p>
          ) : null}

          <div className="materials__list">
            {MATERIALS.map((item) => {
              const state = materials[item.kind]
              const busy = loading || state.saving || state.generating
              return (
                <section className="materials__panel" key={item.kind}>
                  <div className="materials__panel-head">
                    <div>
                      <h3 className="materials__subtitle">{item.title}</h3>
                      <p className="materials__muted">{item.description}</p>
                      <p className="materials__updated">
                        Обновлено: {formatUpdatedAt(state.updatedAt)}
                      </p>
                    </div>
                    <button
                      className="materials__btn"
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        void generateMaterial(item)
                      }}
                    >
                      {state.generating ? 'Генерация…' : 'Сгенерировать'}
                    </button>
                  </div>

                  <textarea
                    className="materials__textarea"
                    rows={item.rows}
                    value={state.content}
                    onChange={(e) => {
                      updateMaterial(item.kind, {
                        content: e.target.value,
                      })
                    }}
                    placeholder={item.emptyText}
                    disabled={busy}
                  />
                  <button
                    className="materials__btn materials__btn--primary"
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      void saveMaterial(item)
                    }}
                  >
                    {state.saving ? 'Сохранение…' : 'Сохранить'}
                  </button>
                </section>
              )
            })}
          </div>
        </>
      )}

      {error ? (
        <p className="materials__err" role="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="materials__ok" role="status">
          {message}
        </p>
      ) : null}
    </section>
  )
}
