import { useEffect, useState } from 'react'
import axios from 'axios'

const API_BASE = 'https://15.207.88.50.nip.io/api'

function AuditTrail() {
  const [audit, setAudit] = useState(null)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    axios.get(`${API_BASE}/audit`)
      .then(res => setAudit(res.data.audit))
      .catch(err => setError(err.message))
  }, [])

  if (error) return <p style={{color: 'red'}}>Error: {error}</p>
  if (!audit) return <p>Loading...</p>

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', textAlign: 'left' }}>
      <h2>Audit Trail ({audit.length})</h2>
      <p style={{ color: '#666' }}>Full processing log — every circular's journey through the 3-agent pipeline.</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {audit.map(a => (
          <div key={a.id} style={{
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '1rem',
            background: '#fff'
          }}>
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
              onClick={() => setExpanded(expanded === a.id ? null : a.id)}
            >
              <div>
                <strong>{a.ticket_id}</strong>
                <span style={{ color: '#666', marginLeft: '0.8rem' }}>
                  Circular #{a.circular_id} · {a.regulator} · {a.domain}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{
                  padding: '0.2rem 0.6rem',
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  background: a.route === 'archive' ? '#eee' : '#e8f5e9',
                  color: a.route === 'archive' ? '#666' : '#2e7d32'
                }}>
                  {a.route}
                </span>
                <span>{expanded === a.id ? '▲' : '▼'}</span>
              </div>
            </div>

            <div style={{ marginTop: '0.4rem', color: '#333' }}>{a.title}</div>

            {expanded === a.id && (
              <div style={{ marginTop: '1rem', borderTop: '1px solid #eee', paddingTop: '1rem', fontSize: '0.9rem' }}>
                <div style={{ marginBottom: '0.6rem' }}>
                  <strong>Agent 1 — Classifier:</strong>{' '}
                  regulator={a.agent1_out?.regulator || a.regulator || 'N/A'}, domain={a.agent1_out?.domain || a.domain || 'N/A'}, doc_type={a.agent1_out?.doc_type || 'Circular'}
                </div>
                <div style={{ marginBottom: '0.6rem' }}>
                  <strong>Agent 2 — Policy Mapper:</strong>{' '}
                  drift_score={a.agent2_out?.drift_score ?? a.drift_score}, priority={a.agent2_out?.priority || a.priority}<br />
                  affected_policies: {a.agent2_out?.affected_policies?.join(', ') || 'none'}
                </div>
                <div>
                  <strong>Agent 3 — Advisor:</strong>{' '}
                  ticket_id={a.agent3_out?.ticket_id || a.ticket_id}, summary_len={a.agent3_out?.summary_len || 0} chars, change_len={a.agent3_out?.change_len || 0} chars
                </div>
                <div style={{ marginTop: '0.6rem', color: '#999' }}>
                  Processed at: {new Date(a.created_at).toLocaleString()}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default AuditTrail
