import type { StockResult } from '../types'
import { AnalysisBlock, fmt, pct, quoteTime, upDownClass } from './AnalysisBlock'

interface Props {
  result: StockResult
  llmEnabled: boolean
}

export default function StockCard({ result, llmEnabled }: Props) {
  const { symbol, metrics, importances, quote, analysis, raw, error } = result

  // 管线整体失败（无回测指标）
  if (error && !metrics) {
    return (
      <div className="card">
        <div className="head">
          <span className="name">{symbol}</span>
        </div>
        <div className="err">分析失败：{error}</div>
      </div>
    )
  }

  const m: Partial<NonNullable<StockResult['metrics']>> = metrics ?? {}
  const imps = importances
    ? Object.entries(importances)
        .slice(0, 6)
        .map(([k, v]) => `${k}: ${v}`)
        .join('　')
    : ''

  return (
    <div className="card">
      <div className="head">
        <span className="name">{quote?.name || symbol}</span>
        <span className="sym">{symbol}</span>
        <span className="time">{quoteTime(quote)}</span>
      </div>

      <div className="quote">
        现价 <b className={upDownClass(quote?.change_pct)}>{fmt(quote?.price)}</b>{' '}
        <span className={upDownClass(quote?.change_pct)}>
          {fmt(quote?.change)} ({fmt(quote?.change_pct)}%)
        </span>
        ｜今开 {fmt(quote?.open)} ｜ 最高 {fmt(quote?.high)} ｜ 最低 {fmt(quote?.low)} ｜换手{' '}
        {fmt(quote?.turnover)}% ｜ 量比 {fmt(quote?.volume_ratio)} ｜ 振幅 {fmt(quote?.amplitude)}%
      </div>

      {!llmEnabled && (
        <div className="err">未配置 DEEPSEEK_API_KEY，仅显示回测指标。</div>
      )}
      {llmEnabled && error && <div className="err">{error}</div>}
      {llmEnabled && !error && <AnalysisBlock a={analysis} />}
      {llmEnabled && !error && !analysis && raw && <pre className="raw">{raw}</pre>}

      <div className="meta">
        <span>回测 n={m.n ?? '--'}</span>
        <span>上涨基线 up_rate={pct(m.up_rate)}</span>
        <span>accuracy={pct(m.accuracy)}</span>
        <span>auc={pct(m.auc)}</span>
        <span>胜率={pct(m.win_rate)}</span>
        <span>
          混淆 {[m.tn, m.fp, m.fn, m.tp].map((x) => x ?? '--').join('/')}
        </span>
        {imps && <div>特征重要性: {imps}</div>}
      </div>
    </div>
  )
}