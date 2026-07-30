import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

import { API_BASE } from '../config'

function getBadgeClass(priority) {
  if (priority?.includes('HIGH')) return 'badge badge-high'
  if (priority?.includes('MEDIUM')) return 'badge badge-medium'
  if (priority?.includes('LOW')) return 'badge badge-low'
  return 'badge badge-archived'
}

function Tickets() {
  const [tickets, setTickets] = useState(null)
  const [error, setError] = useState(null)
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [regulatorFilter, setRegulatorFilter] = useState('all')
  const [domainFilter, setDomainFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const fetchTickets = () => {
    axios.get(`${API_BASE}/tickets`)
      .then(res => setTickets(res.data.tickets))
      .catch(err => setError(err.message))
  }

  useEffect(() => {
    fetchTickets()
  }, [])

  const handleStatusChange = (ticketId, newStatus, e) => {
    e.preventDefault()
    e.stopPropagation()

    axios.patch(`${API_BASE}/tickets/${ticketId}/status`, { status: newStatus })
      .then(() => fetchTickets())
      .catch(err => alert(`Status update failed: ${err.message}`))
  }

  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>
  if (!tickets) return <p>Loading tickets...</p>

  const priorities = [...new Set(tickets.map(t => t.priority))]
  const regulators = [...new Set(tickets.map(t => t.regulator))]
  const domains = [...new Set(tickets.map(t => t.domain))]
  const statuses = [...new Set(tickets.map(t => t.status || 'open'))]

  const filtered = tickets.filter(t =>
    (priorityFilter === 'all' || t.priority === priorityFilter) &&
    (regulatorFilter === 'all' || t.regulator === regulatorFilter) &&
    (domainFilter === 'all' || t.domain === domainFilter) &&
    (statusFilter === 'all' || (t.status || 'open') === statusFilter)
  )

  const selectStyle = {
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid var(--color-border)',
    fontSize: '12px',
    background: '#fff'
  }

  return (
    <div>
      {/* Printable Report Header (Visible ONLY on PDF / Print Export) */}
      <div className="print-only">
        <h1 style={{ fontSize: '18pt', margin: '0 0 4px', color: '#0f172a' }}>BANK OF INDIA — COMPLIANCE COPILOT</h1>
        <h3 style={{ fontSize: '12pt', margin: '0 0 8px', color: '#334155', fontWeight: 500 }}>Executive Compliance Audit & Ticket Summary Report</h3>
        <div style={{ fontSize: '9pt', color: '#64748b' }}>
          Report Generated: {new Date().toLocaleString()} | Total Tickets Displayed: {filtered.length} | Database: AWS RDS PostgreSQL
        </div>
      </div>

      {/* Main Page Title Header (Hidden on Print) */}
      <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div>
          <h2 className="page-title">Compliance Tickets ({filtered.length} of {tickets.length})</h2>
          <p className="page-sub">Actionable compliance obligations and gap remediation tickets in AWS RDS</p>
        </div>

        {/* Action Export Buttons */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <a
            href={`${API_BASE}/tickets/export/csv`}
            download="compliance_tickets_report.csv"
            style={{
              padding: '8px 14px',
              borderRadius: '6px',
              border: '1px solid #0369a1',
              background: '#0369a1',
              color: '#fff',
              textDecoration: 'none',
              fontSize: '12px',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            📥 Export CSV
          </a>
          <button
            onClick={() => window.print()}
            style={{
              padding: '8px 14px',
              borderRadius: '6px',
              border: '1px solid #64748b',
              background: '#fff',
              color: '#1e293b',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            🖨️ Export PDF / Print
          </button>
        </div>
      </div>

      {/* Filter Bar (Hidden on Print) */}
      <div className="card mb-16 no-print" style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <strong style={{ fontSize: '12px', color: '#64748b' }}>FILTERS:</strong>

          <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} style={selectStyle}>
            <option value="all">All Priorities</option>
            {priorities.map(p => <option key={p} value={p}>{p}</option>)}
          </select>

          <select value={regulatorFilter} onChange={e => setRegulatorFilter(e.target.value)} style={selectStyle}>
            <option value="all">All Regulators</option>
            {regulators.map(r => <option key={r} value={r}>{r}</option>)}
          </select>

          <select value={domainFilter} onChange={e => setDomainFilter(e.target.value)} style={selectStyle}>
            <option value="all">All Domains</option>
            {domains.map(d => <option key={d} value={d}>{d}</option>)}
          </select>

          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={selectStyle}>
            <option value="all">All Statuses</option>
            {statuses.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
          </select>
        </div>
      </div>

      {/* Tickets Data Table */}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticket ID</th>
              <th>Regulator / Domain</th>
              <th>Title</th>
              <th>Drift Score</th>
              <th>Priority</th>
              <th>Status</th>
              <th className="no-print">Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', color: '#94a3b8', padding: '24px' }}>
                  No compliance tickets match the selected filters.
                </td>
              </tr>
            )}

            {filtered.map(t => (
              <tr key={t.ticket_id}>
                <td><strong>{t.ticket_id}</strong></td>
                <td>
                  <span className="badge badge-blue">{t.regulator}</span>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>{t.domain}</div>
                </td>
                <td style={{ maxWidth: '280px', fontWeight: 600 }}>{t.title}</td>
                <td><strong>{t.drift_score}</strong></td>
                <td><span className={getBadgeClass(t.priority)}>{t.priority}</span></td>
                <td>
                  <span className="print-only" style={{ fontWeight: 700, textTransform: 'uppercase' }}>
                    {t.status || 'open'}
                  </span>
                  <select
                    className="no-print"
                    value={t.status || 'open'}
                    onChange={(e) => handleStatusChange(t.ticket_id, e.target.value, e)}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 600,
                      border: '1px solid #cbd5e1',
                      background: t.status === 'resolved' ? '#eaf6ea' : (t.status === 'in_progress' ? '#fff4e0' : '#fff'),
                      color: t.status === 'resolved' ? '#2e7d32' : (t.status === 'in_progress' ? '#b26a00' : '#1e293b')
                    }}
                  >
                    <option value="open">OPEN</option>
                    <option value="in_progress">IN PROGRESS</option>
                    <option value="resolved">RESOLVED</option>
                    <option value="archived">ARCHIVED</option>
                  </select>
                </td>
                <td className="no-print">
                  <Link
                    to={`/tickets/${t.ticket_id}`}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: '1px solid #0369a1',
                      color: '#0369a1',
                      textDecoration: 'none',
                      fontSize: '12px',
                      fontWeight: 600
                    }}
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Tickets
