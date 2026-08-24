import type { AnalyzeResponse } from './types'

export async function analyzeSymbols(symbols: string): Promise<AnalyzeResponse> {
  let resp: Response
  try {
    resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols }),
    })
  } catch (e) {
    if (e instanceof TypeError) {
      throw new Error(
        '无法连接到后端（Failed to fetch）。请确认 Flask 服务已启动：' +
        'python -m stocklook.webapp（或运行 ./dev.sh），且访问地址为 http://localhost:5173',
      )
    }
    throw new Error(`请求异常：${String(e)}`)
  }
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    let msg = `请求失败（HTTP ${resp.status}）`
    try {
      const body = JSON.parse(text)
      msg = body?.error || msg
    } catch {
      if (text) msg += `：${text.slice(0, 200)}`
    }
    throw new Error(msg)
  }
  return resp.json()
}