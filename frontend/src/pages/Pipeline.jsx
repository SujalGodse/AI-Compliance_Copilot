import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { API_BASE } from '../config'

// Stage metadata
const STAGES = {
  idle:      { label: 'Idle',                    color: '#64748b', pct: 0   },
  ingestion: { label: 'Stage 1/4 — Ingestion',   color: '#0ea5e9', pct: 15  },
  ocr:       { label: 'Stage 2/4 — PaddleOCR',   color: '#8b5cf6', pct: 35  },
  embedding: { label: 'Stage 3/4 — Milvus Index',color: '#f59e0b', pct: 60  },
  agents:    { label: 'Stage 4/4 — Multi-Agent', color: '#10b981', pct: 80  },
  done:      { label: 'Pipeline Complete ✅',     color: '#16a34a', pct: 100 },
  error:     { label: 'Pipeline Error ❌',        color: '#dc2626', pct: 100 },
}

function Pipeline() {
  const [status,   setStatus]   = useState(null)   // /api/pipeline/status response
  const [starting, setStarting] = useState(false)   // spinner while POST is in-flight
  const [error,    setError]    = useState(null)
  const logRef    = useRef(null)
  const pollRef   = useRef(null)

  // Fetch current status once on mount
  useEffect(() => {
    fetchStatus()
  }, [])

  // Auto-scroll log box to bottom whenever logs change
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [status?.logs])

  // Stop polling when pipeline finishes
  useEffect(() => {
    if (status?.running) {
      startPolling()
    } else {
      stopPolling()
    }
    return () => stopPolling()
  }, [status?.running])

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/pipeline/status`)
      setStatus(res.data)
    } catch (e) {
      setError('Cannot reach server: ' + e.message)
    }
  }

  const startPolling = () => {
    if (pollRef.current) return
    pollRef.current = setInterval(fetchStatus, 3000)  // poll every 3s while running
  }

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const handleRun = async () => {
    setStarting(true)
    setError(null)
    try {
      const res = await axios.post(`${API_BASE}/pipeline/run`, {})
      if (res.data.status === 'already_running') {
        setError('Pipeline is already running! Watch the log below.')
      } else {
        // Start polling immediately after launch
        setTimeout(fetchStatus, 800)
        startPolling()
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setStarting(false)
    }
  }

  const stage     = status?.stage || 'idle'
  const stageInfo = STAGES[stage] || STAGES.idle
  const isRunning = status?.running || false

  if (status === null && error === null) {
    return <p style={{ padding: 24, color: 'var(--color-text-muted)' }}>Loading pipeline status...</p>
  }

  return (
    <div>
      <h2 className="page-title">Pipeline Execution</h2>
      <p className="page-sub">Manually trigger compliance ingestion, PaddleOCR, Milvus vector indexing, and Multi-Agent audit</p>

      {/* ── How It Works ── */}
      <div className="card" style={{ marginBottom: 20, fontSize: 13, color: 'var(--color-text-muted)' }}>
        <div className="section-title">Pipeline Stages</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginTop: 8 }}>
          {[
            { n: 1, name: 'Ingestion', desc: 'Fetches live SEBI/RBI circulars via RSS & S3', time: '~30s' },
            { n: 2, name: 'PaddleOCR', desc: 'Extracts text from scanned PDFs with PaddleOCR', time: '~2–5 min' },
            { n: 3, name: 'Milvus Index', desc: 'Generates 1024-d BAAI/bge-m3 embeddings', time: '~1–3 min' },
            { n: 4, name: 'Multi-Agent', desc: '3 Groq LLM agents per new circular (classify → drift → ticket)', time: '~30–60s each' },
          ].map(s => (
            <div key={s.n} style={{
              padding: '12px 14px',
              borderRadius: 8,
              background: 'var(--color-surface)',
              border: `2px solid ${stage === ['','ingestion','ocr','embedding','agents'][s.n] && isRunning ? stageInfo.color : 'var(--color-border)'}`,
              transition: 'border-color 0.3s'
            }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Stage {s.n}: {s.name}</div>
              <div style={{ fontSize: 11, marginBottom: 4 }}>{s.desc}</div>
              <div style={{ fontSize: 11, color: '#f59e0b', fontWeight: 600 }}>⏱ {s.time}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: 12, color: '#f59e0b', fontWeight: 600 }}>
          ⚠️ Total pipeline time: 5–15 minutes depending on number of new circulars and Groq API response speed.
        </div>
      </div>

      {/* ── Control Card ── */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div className="section-title" style={{ marginBottom: 4 }}>Pipeline Control</div>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              Only processes <strong>new circulars</strong> that don't have tickets yet. Existing tickets are not re-created.
            </div>
          </div>
          <button
            onClick={handleRun}
            disabled={isRunning || starting}
            style={{
              padding: '10px 24px',
              borderRadius: 6,
              border: 'none',
              background: isRunning ? '#94a3b8' : '#0369a1',
              color: '#fff',
              fontSize: 14,
              fontWeight: 600,
              cursor: (isRunning || starting) ? 'not-allowed' : 'pointer',
              boxShadow: 'var(--shadow-sm)',
              flexShrink: 0,
            }}
          >
            {starting ? 'Starting...' : isRunning ? '⏳ Pipeline Running...' : '▶ Run Pipeline'}
          </button>
        </div>

        {/* Progress Bar */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
            <span style={{ fontWeight: 600, color: stageInfo.color }}>{stageInfo.label}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>{stageInfo.pct}%</span>
          </div>
          <div style={{ height: 8, background: 'var(--color-border)', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: stageInfo.pct + '%',
              background: stageInfo.color,
              borderRadius: 4,
              transition: 'width 0.8s ease, background 0.5s ease',
            }} />
          </div>
        </div>

        {/* Current item */}
        {isRunning && status?.current_circular && (
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8 }}>
            🔄 Now processing: <strong>{status.current_circular}</strong>
          </div>
        )}

        {/* Stats row */}
        {status && (stage === 'done' || stage === 'agents' || status.total_processed > 0) && (
          <div style={{ display: 'flex', gap: 16, fontSize: 12, marginTop: 8, flexWrap: 'wrap' }}>
            <span>🟢 Tickets created: <strong>{status.total_processed}</strong></span>
            <span>📁 Archived: <strong>{status.total_archived}</strong></span>
            {status.total_failed > 0 && <span style={{ color: '#dc2626' }}>❌ Errors: <strong>{status.total_failed}</strong></span>}
            <span style={{ color: 'var(--color-text-muted)' }}>DB Tickets: <strong>{status.db_tickets}</strong></span>
            <span style={{ color: 'var(--color-text-muted)' }}>Circulars Done: <strong>{status.db_circulars_done}</strong></span>
          </div>
        )}

        {/* Timestamps */}
        {status?.started_at && (
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--color-text-muted)' }}>
            Started: {new Date(status.started_at + 'Z').toLocaleTimeString()}
            {status.finished_at && (
              <span> · Finished: {new Date(status.finished_at + 'Z').toLocaleTimeString()}
              · Duration: {Math.round((new Date(status.finished_at) - new Date(status.started_at)) / 1000)}s
              </span>
            )}
          </div>
        )}

        {/* Error message */}
        {error && (
          <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 6, background: '#fdecea', border: '1px solid #fca5a5', fontSize: 13, color: '#c62828' }}>
            {error}
          </div>
        )}
        {status?.error && (
          <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 6, background: '#fdecea', border: '1px solid #fca5a5', fontSize: 13, color: '#c62828' }}>
            ❌ Pipeline error: {status.error}
          </div>
        )}
      </div>

      {/* ── Live Log Viewer ── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div className="section-title">Live Execution Log</div>
          {isRunning && (
            <span style={{ fontSize: 11, color: '#0ea5e9', fontWeight: 600, animation: 'pulse 1.5s infinite' }}>
              ● Polling every 3s
            </span>
          )}
        </div>

        <div
          ref={logRef}
          style={{
            background: '#0f172a',
            borderRadius: 8,
            padding: '14px 16px',
            height: 320,
            overflowY: 'auto',
            fontFamily: 'monospace',
            fontSize: 12,
            lineHeight: 1.7,
          }}
        >
          {(!status?.logs || status.logs.length === 0) ? (
            <span style={{ color: '#475569' }}>No pipeline run yet. Click "Run Pipeline" to start.</span>
          ) : (
            status.logs.map((line, i) => {
              let color = '#94a3b8'
              if (line.includes('✅') || line.includes('complete') || line.includes('Ticket created'))  color = '#4ade80'
              else if (line.includes('❌') || line.includes('Error') || line.includes('error'))          color = '#f87171'
              else if (line.includes('warning') || line.includes('warning'))                             color = '#fbbf24'
              else if (line.includes('Stage') || line.includes('['))                                      color = '#38bdf8'
              else if (line.includes('→') || line.includes('processing'))                                color = '#c084fc'
              return (
                <div key={i} style={{ color, marginBottom: 1 }}>{line}</div>
              )
            })
          )}
          {isRunning && (
            <div style={{ color: '#38bdf8', marginTop: 4 }}>▌</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Pipeline
