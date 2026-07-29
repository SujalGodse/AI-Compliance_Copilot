import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'

const API_BASE = 'https://15.207.88.50.nip.io/api'

function PolicyDetail() {
  const { filename } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [view, setView] = useState('text') // 'text' or 'pdf'

  useEffect(() => {
    axios.get(`${API_BASE}/policies/${filename}/chunks`)
      .then(res => setData(res.data))
      .catch(err => setError(err.message))
  }, [filename])

  if (error) return <p style={{ color: 'var(--color-high)' }}>Error: {error}</p>
  if (!data) return <p>Loading...</p>

  const tabStyle = (active) => ({
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    border: '1px solid var(--color-border)',
    borderBottom: active ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
    background: active ? 'var(--color-surface)' : 'transparent',
    color: active ? 'var(--color-accent)' : 'var(--color-text-muted)',
    cursor: 'pointer',
    borderRadius: '6px 6px 0 0'
  })

  return (
    <div style={{ maxWidth: '900px' }}>
      <Link to="/policies" style={{ fontSize: '13px' }}>← Back to Policies</Link>

      <h2 style={{ marginTop: '12px' }}>{data.filename}</h2>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: '16px' }}>
        {data.chunks.length} chunks extracted
      </p>

      <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
        <button style={tabStyle(view === 'text')} onClick={() => setView('text')}>
          Extracted Text
        </button>
        <button style={tabStyle(view === 'pdf')} onClick={() => setView('pdf')}>
          Original PDF
        </button>
      </div>

      {view === 'text' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {data.chunks.map(c => (
            <div key={c.chunk_index} style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              padding: '14px 16px'
            }}>
              <div style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--color-text-muted)',
                marginBottom: '6px',
                textTransform: 'uppercase',
                letterSpacing: '0.03em'
              }}>
                Chunk {c.chunk_index + 1} · {c.word_count} words
              </div>
              <div style={{ fontSize: '13px', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {c.chunk_text}
              </div>
            </div>
          ))}
        </div>
      )}

      {view === 'pdf' && (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <p style={{ marginBottom: '16px', color: 'var(--color-text-muted)' }}>
            Click below to open the original PDF in a new tab.
          </p>
          
            <a href={API_BASE + '/policies/' + filename + '/file'} target="_blank" rel="noreferrer" className="pdf-view-link">Open PDF in New Tab</a>
        </div>
      )}
    </div>
  )
}

export default PolicyDetail
