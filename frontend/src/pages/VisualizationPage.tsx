import {
  type FormEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react'
import { formatApiErrorMessage } from '../api/apiError'
import { getApiBaseUrl } from '../config'

type VisualizationCard = {
  id: string
  title: string
  body: string
  sort_order: number
}

type KnowledgeMapNode = {
  id: string
  label: string
  level: number
}

type KnowledgeMapEdge = {
  source: string
  target: string
}

type VisualizationResponse = {
  job_id: number
  title: string
  cards: VisualizationCard[]
  map: {
    nodes: KnowledgeMapNode[]
    edges: KnowledgeMapEdge[]
  }
}

type PositionedNode = KnowledgeMapNode & {
  x: number
  y: number
}

type Props = {
  jobId: number | null
  onSetJobId: (id: number | null) => void
}

const SVG_WIDTH = 900
const SVG_HEIGHT = 520

function parseJobIdInput(raw: string): number | null {
  const n = parseInt(raw.trim(), 10)
  if (Number.isNaN(n) || n < 1) {
    return null
  }
  return n
}

  const sorted = [...nodes].sort((a, b) => {
    if (a.level !== b.level) {
      return a.level - b.level
    }
    return a.id.localeCompare(b.id)
  })
  const byLevel = new Map<number, KnowledgeMapNode[]>()
  for (const node of sorted) {
    const group = byLevel.get(node.level) ?? []
    group.push(node)
    byLevel.set(node.level, group)
  }

  const levels = [...byLevel.keys()].sort((a, b) => a - b)
  return sorted.map((node) => {
    const levelIndex = Math.max(levels.indexOf(node.level), 0)
    const levelNodes = byLevel.get(node.level) ?? [node]
    const index = levelNodes.findIndex((item) => item.id === node.id)
    const x = 120 + levelIndex * 220
    const gap = SVG_HEIGHT / (levelNodes.length + 1)
    const y = gap * (index + 1)
    return { ...node, x, y }
  })
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function VisualizationPage({ jobId, onSetJobId }: Props) {
  const id = useId()
  const svgRef = useRef<SVGSVGElement | null>(null)
  const [draftId, setDraftId] = useState('')
  const [data, setData] = useState<VisualizationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const loadVisualization = useCallback(async (targetJobId: number) => {
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/visualization/${targetJobId}`,
      )
      const responseData: unknown = await res.json()
      if (!res.ok) {
        throw new Error(
          formatApiErrorMessage(responseData, `HTTP ${res.status}`),
        )
      }
      setData(responseData as VisualizationResponse)
      setMessage('Визуализация построена.')
    } catch (e) {
      setData(null)
      if (e instanceof Error) {
        setError(e.message)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (jobId == null) {
      return
    }
    setDraftId(String(jobId))
    void loadVisualization(jobId)
  }, [jobId, loadVisualization])

  function submitJobId(e: FormEvent) {
    e.preventDefault()
    const n = parseJobIdInput(draftId)
    if (n == null) {
      setError('Введите положительное целое число.')
      return
    }
    onSetJobId(n)
    void loadVisualization(n)
  }

  async function exportPng() {
    const svg = svgRef.current
    if (svg == null || data == null) {
      return
    }
    setExporting(true)
    setError(null)
    setMessage(null)
    try {
      const serializer = new XMLSerializer()
      const source = serializer.serializeToString(svg)
      const blob = new Blob([source], {
        type: 'image/svg+xml;charset=utf-8',
      })
      const url = URL.createObjectURL(blob)
      const image = new Image()
      const loaded = new Promise<void>((resolve, reject) => {
        image.onload = () => resolve()
        image.onerror = () => reject(new Error('Не удалось собрать PNG.'))
      })
      image.src = url
      await loaded

      const canvas = document.createElement('canvas')
      canvas.width = SVG_WIDTH
      canvas.height = SVG_HEIGHT
      const ctx = canvas.getContext('2d')
      if (ctx == null) {
        throw new Error('Canvas недоступен в браузере.')
      }
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(image, 0, 0)
      URL.revokeObjectURL(url)

      const png = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((result) => {
          if (result == null) {
            reject(new Error('Не удалось сохранить PNG.'))
            return
          }
          resolve(result)
        }, 'image/png')
      })
      downloadBlob(png, `knowledge-map-job-${data.job_id}.png`)
      setMessage('PNG скачан.')
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message)
      }
    } finally {
      setExporting(false)
    }
  }

  const nodes = positionNodes(data?.map.nodes ?? [])
  const nodesById = new Map(nodes.map((node) => [node.id, node]))

  return (
    <section className="visualization" aria-labelledby={`${id}-h`}>
      <h2 className="visualization__title" id={`${id}-h`}>
        Visualization
      </h2>
      <p className="visualization__intro">
        Карточки и карта знаний строятся по разделам методички.
      </p>

      <form className="visualization__form" onSubmit={submitJobId}>
        <label className="visualization__label" htmlFor={`${id}-job`}>
          job_id
        </label>
        <input
          className="visualization__input"
          id={`${id}-job`}
          inputMode="numeric"
          value={draftId}
          onChange={(e) => setDraftId(e.target.value)}
          placeholder={jobId == null ? 'например, 15' : String(jobId)}
        />
        <button
          className="visualization__btn visualization__btn--primary"
          type="submit"
          disabled={loading}
        >
          {loading ? 'Построение…' : 'Построить'}
        </button>
        {jobId != null ? (
          <button
            className="visualization__btn"
            type="button"
            disabled={loading}
            onClick={() => {
              setDraftId(String(jobId))
              void loadVisualization(jobId)
            }}
          >
            Обновить текущую
          </button>
        ) : null}
      </form>

      {data != null ? (
        <div className="visualization__content">
          <div className="visualization__head">
            <div>
              <h3 className="visualization__subtitle">{data.title}</h3>
              <p className="visualization__muted">
                Карточек: {data.cards.length}, узлов: {data.map.nodes.length}
              </p>
            </div>
            <button
              className="visualization__btn"
              type="button"
              disabled={exporting || data.map.nodes.length === 0}
              onClick={() => {
                void exportPng()
              }}
            >
              {exporting ? 'Экспорт…' : 'Скачать PNG'}
            </button>
          </div>

          <section
            className="visualization__map-panel"
            aria-labelledby={`${id}-map`}
          >
            <h3 className="visualization__subtitle" id={`${id}-map`}>
              Карта знаний
            </h3>
            <svg
              className="visualization__map"
              ref={svgRef}
              viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
              role="img"
              aria-label="Карта знаний"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect width="100%" height="100%" fill="#ffffff" />
              {data.map.edges.map((edge) => {
                const source = nodesById.get(edge.source)
                const target = nodesById.get(edge.target)
                if (source == null || target == null) {
                  return null
                }
                return (
                  <line
                    className="visualization__edge"
                    key={`${edge.source}-${edge.target}`}
                    x1={source.x + 82}
                    y1={source.y}
                    x2={target.x - 82}
                    y2={target.y}
                  />
                )
              })}
              {nodes.map((node) => (
                <g key={node.id}>
                  <rect
                    className="visualization__node"
                    x={node.x - 82}
                    y={node.y - 26}
                    width="164"
                    height="52"
                    rx="12"
                  />
                  <text
                    className="visualization__node-text"
                    x={node.x}
                    y={node.y - 4}
                    textAnchor="middle"
                  >
                    {node.label.slice(0, 24)}
                  </text>
                  <text
                    className="visualization__node-level"
                    x={node.x}
                    y={node.y + 15}
                    textAnchor="middle"
                  >
                    уровень {node.level}
                  </text>
                </g>
              ))}
            </svg>
          </section>

          <section aria-labelledby={`${id}-cards`}>
            <h3 className="visualization__subtitle" id={`${id}-cards`}>
              Карточки
            </h3>
            <ol className="visualization__cards">
              {data.cards.map((card) => (
                <li className="visualization__card" key={card.id}>
                  <h4 className="visualization__card-title">
                    {card.title}
                  </h4>
                  <p className="visualization__card-body">
                    {card.body || 'Нет текста раздела.'}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        </div>
      ) : null}

      {error ? (
        <p className="visualization__err" role="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="visualization__ok" role="status">
          {message}
        </p>
      ) : null}
    </section>
  )
}
