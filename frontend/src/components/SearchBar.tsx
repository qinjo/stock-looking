import { useState } from 'react'

interface Props {
  initial: string
  loading: boolean
  onAnalyze: (raw: string) => void
}

export default function SearchBar({ initial, loading, onAnalyze }: Props) {
  const [value, setValue] = useState(initial)

  function submit() {
    if (!value.trim()) return
    onAnalyze(value)
  }

  return (
    <div className="controls">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
        placeholder="输入股票代码，逗号分隔，如：600519, 300750, 000001"
        aria-label="股票代码"
      />
      <button onClick={submit} disabled={loading}>
        {loading ? '分析中…' : '开始分析'}
      </button>
    </div>
  )
}