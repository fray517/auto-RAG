import { useEffect, useState } from 'react'
import './App.css'

type HealthState = 'loading' | 'ok' | 'error'

const NAV_STUBS = [
  'Dashboard',
  'Upload',
  'Processing',
  'Transcript',
  'Materials',
  'Chat',
  'Visualization',
  'Settings',
] as const

function getApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base === 'string' && base.trim() !== '') {
    return base.replace(/\/$/, '')
  }
  return 'http://localhost:8000'
}

function App() {
  const [health, setHealth] = useState<HealthState>('loading')

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
        <h1 className="app__title">auto-RAG</h1>
        <p
          className={`app__status app__status--${health}`}
          role="status"
          aria-live="polite"
        >
          {statusLabel}
        </p>
      </header>

      <nav className="app__nav" aria-label="Разделы (заглушки)">
        <ul className="app__nav-list">
          {NAV_STUBS.map((name) => (
            <li key={name}>
              <button type="button" className="app__nav-btn" disabled>
                {name}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}

export default App
