import { useEffect, useState } from 'react'
import { getApiBaseUrl } from './config'
import { ProcessingPage } from './pages/ProcessingPage'
import { TranscriptPage } from './pages/TranscriptPage'
import { UploadPage } from './pages/UploadPage'
import './App.css'

type HealthState = 'loading' | 'ok' | 'error'

type Section = 'home' | 'upload' | 'processing' | 'transcript'

const STUB_BEFORE_UPLOAD = ['Dashboard'] as const
const STUB_AFTER_PROCESSING = [
  'Materials',
  'Chat',
  'Visualization',
  'Settings',
] as const

function App() {
  const [health, setHealth] = useState<HealthState>('loading')
  const [section, setSection] = useState<Section>('home')
  const [processingJobId, setProcessingJobId] = useState<number | null>(
    null,
  )

  useEffect(() => {
    const base = getApiBaseUrl()
    const controller = new AbortController()
    fetch(`${base}/health`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) {
          throw new Error('HTTP error')
        }
        return res.json() as Promise<{ status?: string }>
      })
      .then((data) => {
        if (data?.status === 'ok') {
          setHealth('ok')
        } else {
          setHealth('error')
        }
      })
      .catch(() => {
        if (controller.signal.aborted) {
          return
        }
        setHealth('error')
      })
    return () => controller.abort()
  }, [])

  let statusLabel: string
  if (health === 'loading') {
    statusLabel = 'проверка…'
  } else if (health === 'ok') {
    statusLabel = 'backend доступен'
  } else {
    statusLabel = 'backend недоступен'
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">
          <button
            type="button"
            className="app__brand"
            onClick={() => {
              setSection('home')
            }}
          >
            auto-RAG
          </button>
        </h1>
        <p
          className={`app__status app__status--${health}`}
          role="status"
          aria-live="polite"
        >
          {statusLabel}
        </p>
      </header>

      <nav className="app__nav" aria-label="Разделы">
        <ul className="app__nav-list">
          {STUB_BEFORE_UPLOAD.map((name) => (
            <li key={name}>
              <button type="button" className="app__nav-btn" disabled>
                {name}
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              className={
                section === 'upload'
                  ? 'app__nav-btn app__nav-btn--active'
                  : 'app__nav-btn app__nav-btn--link'
              }
              onClick={() => setSection('upload')}
            >
              Upload
            </button>
          </li>
          <li>
            <button
              type="button"
              className={
                section === 'processing'
                  ? 'app__nav-btn app__nav-btn--active'
                  : 'app__nav-btn app__nav-btn--link'
              }
              onClick={() => setSection('processing')}
            >
              Processing
            </button>
          </li>
          <li>
            <button
              type="button"
              className={
                section === 'transcript'
                  ? 'app__nav-btn app__nav-btn--active'
                  : 'app__nav-btn app__nav-btn--link'
              }
              onClick={() => setSection('transcript')}
            >
              Transcript
            </button>
          </li>
          {STUB_AFTER_PROCESSING.map((name) => (
            <li key={name}>
              <button type="button" className="app__nav-btn" disabled>
                {name}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <main className="app__main">
        {section === 'home' ? (
          <p className="app__hint">
            Выберите раздел: загрузка — «Upload», этапы — «Processing».
          </p>
        ) : null}
        {section === 'upload' ? (
          <UploadPage
            onJobCreated={(jobId) => {
              setProcessingJobId(jobId)
              setSection('processing')
            }}
          />
        ) : null}
        {section === 'processing' ? (
          <ProcessingPage
            key={
              processingJobId === null
                ? 'processing-idle'
                : `processing-${processingJobId}`
            }
            jobId={processingJobId}
            onSetJobId={setProcessingJobId}
          />
        ) : null}
        {section === 'transcript' ? (
          <TranscriptPage
            jobId={processingJobId}
            onSetJobId={setProcessingJobId}
          />
        ) : null}
      </main>
    </div>
  )
}

export default App
