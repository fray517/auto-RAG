import { type FormEvent, useId, useState } from 'react'
import { getApiBaseUrl } from '../config'

type ChatMode = 'strict' | 'explain'

type ChatSource = {
  chunk_id: number
  knowledge_block_id: number
  video_job_id: number
  video_title: string
  block_type: string
  section: string | null
  score: number
  excerpt: string
}

type ChatResponse = {
  answer: string
  mode: ChatMode
  sources: ChatSource[]
  sections: string[]
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

export function ChatPage() {
  const id = useId()
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<ChatMode>('strict')
  const [topK, setTopK] = useState(5)
  const [answer, setAnswer] = useState<ChatResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ask(e: FormEvent) {
    e.preventDefault()
    const cleanQuestion = question.trim()
    if (!cleanQuestion) {
      setError('Введите вопрос.')
      return
    }

    setLoading(true)
    setError(null)
    setAnswer(null)
    try {
      const res = await fetch(`${getApiBaseUrl()}/chat/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
        },
        body: JSON.stringify({
          question: cleanQuestion,
          mode,
          top_k: topK,
        }),
      })
      const data: unknown = await res.json()
      if (!res.ok) {
        throw new Error(getApiError(data, `HTTP ${res.status}`))
      }
      setAnswer(data as ChatResponse)
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="chat" aria-labelledby={`${id}-h`}>
      <h2 className="chat__title" id={`${id}-h`}>
        Chat
      </h2>
      <p className="chat__intro">
        Задайте вопрос по базе знаний. Ответ строится через retrieval и LLM.
      </p>

      <form className="chat__form" onSubmit={ask}>
        <label className="chat__label" htmlFor={`${id}-question`}>
          Вопрос
        </label>
        <textarea
          className="chat__question"
          id={`${id}-question`}
          rows={4}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Например: какие механики входа обсуждаются?"
          disabled={loading}
        />

        <div className="chat__controls">
          <fieldset className="chat__fieldset">
            <legend className="chat__legend">Режим</legend>
            <label className="chat__radio">
              <input
                type="radio"
                name={`${id}-mode`}
                value="strict"
                checked={mode === 'strict'}
                onChange={() => setMode('strict')}
                disabled={loading}
              />
              Строго по документу
            </label>
            <label className="chat__radio">
              <input
                type="radio"
                name={`${id}-mode`}
                value="explain"
                checked={mode === 'explain'}
                onChange={() => setMode('explain')}
                disabled={loading}
              />
              С пояснениями ИИ
            </label>
          </fieldset>

          <label className="chat__topk" htmlFor={`${id}-topk`}>
            Источников
            <input
              id={`${id}-topk`}
              type="number"
              min={1}
              max={10}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={loading}
            />
          </label>

          <button
            className="chat__btn chat__btn--primary"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Ответ формируется…' : 'Спросить'}
          </button>
        </div>
      </form>

      {error ? (
        <p className="chat__err" role="alert">
          {error}
        </p>
      ) : null}

      {answer ? (
        <article className="chat__result">
          <div className="chat__answer">
            <h3 className="chat__subtitle">Ответ</h3>
            <p className="chat__mode">
              Режим: {answer.mode === 'strict' ? 'strict' : 'explain'}
            </p>
            <div className="chat__answer-text">{answer.answer}</div>
          </div>

          <section className="chat__sources">
            <h3 className="chat__subtitle">Источники</h3>
            {answer.sources.length === 0 ? (
              <p className="chat__muted">Источники не найдены.</p>
            ) : (
              <ol className="chat__source-list">
                {answer.sources.map((source) => (
                  <li className="chat__source" key={source.chunk_id}>
                    <p className="chat__source-title">
                      {source.video_title} / {source.block_type}
                      {source.section ? ` / ${source.section}` : ''}
                    </p>
                    <p className="chat__score">
                      score: {source.score.toFixed(4)}, chunk:{' '}
                      {source.chunk_id}
                    </p>
                    <p className="chat__excerpt">{source.excerpt}</p>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="chat__sections">
            <h3 className="chat__subtitle">Разделы</h3>
            {answer.sections.length === 0 ? (
              <p className="chat__muted">Разделы не найдены.</p>
            ) : (
              <ul className="chat__section-list">
                {answer.sections.map((section) => (
                  <li key={section}>{section}</li>
                ))}
              </ul>
            )}
          </section>
        </article>
      ) : null}
    </section>
  )
}
