import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'

const API_BASE = 'https://15.207.88.50.nip.io/api'

const priorityColor = {
  'HIGH — P1': '#d32f2f',
  'MEDIUM — P2': '#f57c00',
  'LOW — P3': '#388e3c'
}

function TicketDetail() {
  const { ticketId } = useParams()
  const [ticket, setTicket] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    axios.get(`${API_BASE}/tickets/${ticketId}`)
      .then(res => setTicket(res.data))
      .catch(err => setError(err.message))
  }, [ticketId])

  if (error) return <p style={{color: 'red'}}>Error: {error}</p>
  if (!ticket) return <p>Loading...</p>

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
      <Link to="/tickets">← Back to Tickets</Link>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
        <h2>{ticket.ticket_id}</h2>
        <span style={{
          color: priorityColor[ticket.priority] || '#333',
          fontWeight: 'bold',
          fontSize: '1.1rem'
        }}>
          {ticket.priority}
        </span>
      </div>

      <h3>{ticket.title}</h3>

      <p style={{ color: '#666' }}>
        {ticket.regulator} · {ticket.domain} · {ticket.doc_type}
      </p>

      <div style={{ display: 'flex', gap: '2rem', margin: '1rem 0', fontSize: '0.9rem' }}>
        <div>Drift Score: <strong>{ticket.drift_score}</strong></div>
        <div>Semantic: <strong>{ticket.semantic_score}</strong></div>
        <div>Policy Match: <strong>{ticket.policy_score}</strong></div>
        <div>Entity Match: <strong>{ticket.entity_score}</strong></div>
      </div>

      <h4>Summary</h4>
      <p>{ticket.summary}</p>

      <h4>Change List</h4>
      <pre style={{ whiteSpace: 'pre-wrap', background: '#f4f4f4', padding: '1rem', borderRadius: '6px' }}>
        {ticket.change_list}
      </pre>

      <h4>Affected Policies</h4>
      <ul>
        {ticket.affected_policies.map((p, i) => <li key={i}>{p}</li>)}
      </ul>
    </div>
  )
}

export default TicketDetail
