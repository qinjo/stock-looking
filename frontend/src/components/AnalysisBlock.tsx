import type { Analysis, Quote } from '../types'

export function directionMeta(d: string | undefined): { cls: string; text: string } {
  switch (d) {
    case 'up':
      return { cls: 'b-up', text: '看涨' }
    case 'down':
      return { cls: 'b-down', text: '看跌' }
    default:
      return { cls: 'b-flat', text: d ? String(d) : '未知' }
  }
}

export const fmt = (v: number | null | undefined, d = 2): string =>
  v === null || v === undefined || Number.isNaN(v) ? '--' : Number(v).toFixed(d)

export const pct = (v: number | null | undefined): string =>
  v === null || v === undefined || Number.isNaN(v) ? '--' : (Number(v) * 100).toFixed(1) + '%'

export function quoteTime(q: Quote | null): string {
  if (!q?.time) return ''
  const t = new Date(q.time)
  return Number.isNaN(t.getTime()) ? '' : t.toLocaleString('zh-CN')
}

export function upDownClass(v: number | null | undefined): string {
  if (v === null || v === undefined) return ''
  return v < 0 ? 'down' : 'up'
}

export function ul(items: string[] | undefined, fallback = '（无）') {
  if (!items || items.length === 0) return <p className="empty">{fallback}</p>
  return (
    <ul>
      {items.map((x, i) => (
        <li key={i}>{x}</li>
      ))}
    </ul>
  )
}

export function AnalysisBlock({ a }: { a: Analysis | null }) {
  if (!a) return null
  const { cls, text } = directionMeta(a.direction)
  return (
    <>
      <div className="head verdict">
        <span className={`badge ${cls}`}>{text}</span>
        <span className="conf">
          置信度{' '}
          <meter
            min={0}
            max={1}
            low={0.45}
            high={0.65}
            optimum={0.8}
            value={a.confidence ?? 0}
          />
          {' '}
          {fmt(a.confidence)}
        </span>
      </div>
      <div className="cols">
        <div className="case bull">
          <h4>▲ 看涨证据</h4>
          {ul(a.bull_cases)}
        </div>
        <div className="case bear">
          <h4>▼ 看跌证据</h4>
          {ul(a.bear_cases)}
        </div>
      </div>
      {a.reasons && a.reasons.length > 0 && (
        <div className="section">
          <h4>综合判断理由</h4>
          {ul(a.reasons)}
        </div>
      )}
      {a.risks && a.risks.length > 0 && (
        <div className="section risks">
          <h4>⚠ 风险</h4>
          {ul(a.risks)}
        </div>
      )}
      {a.summary && <div className="summary">💬 {a.summary}</div>}
    </>
  )
}