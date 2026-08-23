import type { AnalyzeResponse } from './types'

export async function analyzeSymbols(symbols: string): Promise<AnalyzeResponse> {
  const resp = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbols }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.error || `请求失败（${resp.status}）`)
  }
  return resp.json()
}