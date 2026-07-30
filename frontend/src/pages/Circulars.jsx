import { useEffect, useState } from 'react'
import axios from 'axios'

import { API_BASE } from '../config'

const statusColor = {
  processed: { bg: 'var(--color-low-bg)', text: 'var(--color-low)' },
  pending: { bg: 'var(--color-medium-bg)', text: 'var(--color-medium)' },
  failed: { bg: 'var(--color-high-bg)', text: 'var(--color-high)' },
  skipped: { bg: 'var(--color-archived-bg)', text: 'var(--color-archived)' },
}

const outcomeColor = {
  process: { bg: 'var(--color-low-bg)', text: 'var(--color-low)', label: 'Ticketed' },
  archive: { bg: 'var(--color-archived-bg)', text: 'var(--color-archived)', label: 'Archived' },
}

function Circulars() {
  const [circulars, setCirculars] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    axios.get(API_BASE + '/circulars')
      .then(function(res) { setCirculars(res.data.circulars) })
      .catch(function(err) { setError(err.message) })
  }, [])

  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>
  if (!circulars) return <p>Loading...</p>

  return (
    <div>
      <h2>Circulars ({circulars.length})</h2>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: '20px' }}>
        All circulars fetched from regulatory sources.
      </p>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <thead>
          <tr>
            <th style={thStyle}>#</th>
            <th style={thStyle}>Title</th>
            <th style={thStyle}>Source</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>Outcome</th>
            <th style={thStyle}>Drift Score</th>
            <th style={thStyle}>Fetched</th>
            <th style={thStyle}>PDF</th>
          </tr>
        </thead>
        <tbody>
          {circulars.map(function(c) {
            var sc = statusColor[c.status] || statusColor.pending
            var oc = c.outcome ? outcomeColor[c.outcome] : null
            var pdfUrl = API_BASE + '/circulars/' + c.id + '/file'

            return (
              <tr key={c.id} style={rowStyle}>
                <td style={tdStyle}>{c.id}</td>
                <td style={tdStyle}>{c.title}</td>
                <td style={tdStyle}>{c.source}</td>
                <td style={tdStyle}>
                  <span style={{ background: sc.bg, color: sc.text, padding: '2px 8px', borderRadius: '4px' }}>{c.status}</span>
                </td>
                <td style={tdStyle}>
                  {oc && <span style={{ background: oc.bg, color: oc.text, padding: '2px 8px', borderRadius: '4px' }}>{oc.label}</span>}
                </td>
                <td style={tdStyle}>{c.drift_score}</td>
                <td style={tdStyle}>{c.fetched_at}</td>
                <td style={tdStyle}>
                  <a href={pdfUrl} target="_blank" rel="noreferrer" className="pdf-view-link">View</a>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

var thStyle = { textAlign: 'left', padding: '10px', fontSize: '11px', color: '#888' }
var tdStyle = { padding: '10px' }
var rowStyle = { borderBottom: '1px solid #eee' }

export default Circulars
