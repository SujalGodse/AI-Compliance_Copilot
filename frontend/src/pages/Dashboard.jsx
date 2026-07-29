import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import StatCard from '../components/StatCard'
import DriftChart from '../components/DriftChart'

const API = 'https://15.207.88.50.nip.io/api'

function Dashboard() {
  const [stats,   setStats]   = useState(null)
  const [scores,  setScores]  = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    Promise.all([
      axios.get(API + '/stats'),
      axios.get(API + '/drift-scores'),
      axios.get(API + '/dashboard-summary'),
    ])
      .then(([s, d, sum]) => {
        setStats(s.data)
        setScores(d.data.scores || [])
        setSummary(sum.data)
        setLoading(false)
      })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  if (loading) return <p style={{ padding: 24, color: 'var(--color-text-muted)' }}>Loading dashboard...</p>
  if (error)   return <p style={{ padding: 24, color: 'var(--color-high)' }}>Error: {error}</p>

  const t   = stats.tickets
  const c   = stats.circulars
  const p   = stats.policies
  const dom = summary.by_domain        || []
  const rec = summary.recent_tickets   || []
  const maxDom = Math.max(...dom.map(d => d.count), 1)

  return (
    <div>
      <h2 className="page-title">Dashboard</h2>
      <p className="page-sub">SEBI · RBI · IRDAI · PFRDA Compliance Monitoring</p>

      {/* ── Stat Cards ── */}
      <div className="flex-gap" style={{ marginBottom: 20 }}>
        <StatCard label="Total Tickets"      value={t.total}     />
        <StatCard label="High Priority"      value={t.high}      accent="var(--color-high)" />
        <StatCard label="Medium Priority"    value={t.medium}    accent="var(--color-medium)" />
        <StatCard label="Low Priority"       value={t.low}       accent="var(--color-low)" />
        <StatCard label="Archived"           value={t.archived}  accent="var(--color-archived)" />
        <StatCard label="Circulars Processed" value={c.processed} accent="var(--color-accent)" />
        <StatCard label="Policies Loaded"    value={p.total}     accent="#7b1fa2" />
      </div>

      {/* ── Domain Bars + Recent Tickets ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>

        {/* Tickets by Domain */}
        <div className="card">
          <div className="section-title">Tickets by Domain</div>
          {dom.length === 0 && <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>No data yet.</p>}
          {dom.map(d => (
            <div key={d.domain} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                <span>{d.domain}</span>
                <span style={{ fontWeight: 600, color: 'var(--color-text-muted)' }}>{d.count}</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: ((d.count / maxDom) * 100) + '%' }} />
              </div>
            </div>
          ))}
        </div>

        {/* Recent Tickets */}
        <div className="card">
          <div className="section-title">Recent Tickets</div>
          {rec.length === 0 && <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>No tickets yet.</p>}
          {rec.map(t => (
            <Link
              key={t.ticket_id}
              to={'/tickets/' + t.ticket_id}
              style={{ display: 'block', textDecoration: 'none', color: 'inherit',
                       padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2,
                            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {t.title?.length > 65 ? t.title.slice(0, 65) + '…' : t.title}
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                {t.regulator} · {t.domain} · {new Date(t.created_at).toLocaleDateString()}
              </div>
            </Link>
          ))}
        </div>

      </div>

      {/* ── Drift Chart ── */}
      <div className="card">
        <div className="section-title">Policy Drift Scores by Ticket</div>
        <DriftChart data={scores} />
      </div>
    </div>
  )
}

export default Dashboard
