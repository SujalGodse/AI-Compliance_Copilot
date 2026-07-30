import { useState } from 'react'
import axios from 'axios'

import { API_BASE } from '../config'

function Pipeline() {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [startedAt, setStartedAt] = useState(null)

  const handleRun = async () => {
    setRunning(true)
    setResult(null)
    setError(null)
    setStartedAt(new Date())

    try {
      const res = await axios.post(`${API_BASE}/pipeline/run`, {}, {
        timeout: 30000 // 30 second client timeout
      })
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <h2 className="page-title">Pipeline Execution</h2>
      <p className="page-sub">Manually trigger compliance ingestion, PaddleOCR, Milvus vector indexing, and Multi-Agent audit</p>

      <div className="card" style={{ textAlign: 'center', padding: '32px 24px', maxWidth: '720px' }}>
        <div className="section-title">Manual Pipeline Trigger</div>
        <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginBottom: '24px' }}>
          Executes the complete pipeline: fetches live SEBI/RBI circulars, processes scanned PDFs with PaddleOCR, generates 1024-d embeddings in Milvus, and executes the Multi-Agent audit engine.
        </p>

        <button
          onClick={handleRun}
          disabled={running}
          style={{
            padding: '12px 28px',
            borderRadius: '6px',
            border: 'none',
            background: running ? '#94a3b8' : '#0369a1',
            color: '#fff',
            fontSize: '14px',
            fontWeight: 600,
            cursor: running ? 'not-allowed' : 'pointer',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          {running ? 'Starting Pipeline...' : '▶ Run Full Pipeline'}
        </button>

        {running && (
          <div style={{ marginTop: '20px', fontSize: '13px', color: '#64748b' }}>
            <p>Initiating pipeline request...</p>
            <p style={{ fontSize: '12px' }}>Started at: {startedAt?.toLocaleTimeString()}</p>
          </div>
        )}

        {result && (
          <div style={{ marginTop: '24px', padding: '16px', borderRadius: '6px', background: '#eaf6ea', border: '1px solid #a3e635', textAlign: 'left' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: '#2e7d32', marginBottom: '4px' }}>
              ✅ {result.message}
            </div>
            <p style={{ fontSize: '13px', color: '#1b5e20', margin: 0 }}>
              Total compliance tickets in AWS RDS PostgreSQL: <strong>{result.total_tickets}</strong>
            </p>
          </div>
        )}

        {error && (
          <div style={{ marginTop: '24px', padding: '16px', borderRadius: '6px', background: '#fdecea', border: '1px solid #fca5a5', textAlign: 'left' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: '#c62828', marginBottom: '4px' }}>
              ❌ Pipeline Execution Notice
            </div>
            <p style={{ fontSize: '13px', color: '#b71c1c', margin: 0 }}>{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Pipeline
