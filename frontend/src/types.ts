export interface Quote {
  name: string | null
  code: string | null
  price: number | null
  prev_close: number | null
  open: number | null
  high: number | null
  low: number | null
  change: number | null
  change_pct: number | null
  volume: number | null
  amount_wan: number | null
  turnover: number | null
  amplitude: number | null
  volume_ratio: number | null
  time: string | null
}

export interface Metrics {
  n: number
  up_rate: number
  accuracy: number
  auc: number
  win_rate: number
  tn: number
  fp: number
  fn: number
  tp: number
}

export interface Analysis {
  direction: 'up' | 'down' | 'flat' | string
  confidence: number | null
  bull_cases?: string[]
  bear_cases?: string[]
  reasons?: string[]
  risks?: string[]
  summary?: string
}

export interface StockResult {
  symbol: string
  metrics: Metrics | null
  importances: Record<string, number> | null
  quote: Quote | null
  analysis: Analysis | null
  raw: string | null
  error: string | null
}

export interface AnalyzeResponse {
  results: StockResult[]
  llm_enabled: boolean
}