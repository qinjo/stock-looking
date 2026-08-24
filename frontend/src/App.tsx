import { useState } from 'react'
import { analyzeSymbols } from './api'
import SearchBar from './components/SearchBar'
import StockCard from './components/StockCard'
import type { AnalyzeResponse, StockResult } from './types'

export default function App() {
  const [symbols, setSymbols] = useState('600519, 300750')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [progress, setProgress] = useState(0)

  function run(raw: string) {
    setSymbols(raw)
    void start(raw)
  }

  async function start(raw: string) {
    setLoading(true)
    setError(null)
    setData(null)
    setProgress(30)
    try {
      const resp = await analyzeSymbols(raw)
      setProgress(100)
      setData(resp)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="wrap">
      <h1>📈 A股次日方向 · 参考信号</h1>
      <p className="sub">
        实时行情快照 + LightGBM 回测 + DeepSeek 大模型分析（仅作研究参考，不构成投资建议）<br />
        ⏱ 一次分析约需 15~30 秒（含实时行情与 LLM 调用），请耐心等待
      </p>

      <SearchBar initial={symbols} loading={loading} onAnalyze={run} />

      {loading && (
        <div className="bar">
          <i style={{ width: `${progress}%` }} />
        </div>
      )}

      {error && <div className="card err">{error}</div>}

      {data && (
        <div className="results">
          {data.results.map((r: StockResult) => (
            <StockCard key={r.symbol} result={r} llmEnabled={data.llm_enabled} />
          ))}
        </div>
      )}

      {!data && !loading && !error && (
        <div className="hint">输入股票代码（逗号分隔）后点击「开始分析」</div>
      )}
    </div>
  )
}