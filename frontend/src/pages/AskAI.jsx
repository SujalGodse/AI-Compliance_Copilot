import { useState } from 'react'
import axios from 'axios'

import { API_BASE } from '../config'

function AskAI() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('askai_history')
    return saved ? JSON.parse(saved) : []
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAsk = async () => {
    if (!query.trim()) return

    const userMsg = { role: 'user', text: query }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    localStorage.setItem('askai_history', JSON.stringify(updatedMessages))
    setLoading(true)
    setError(null)
    setQuery('')

    try {
      const res = await axios.post(`${API_BASE}/chat`, { query: userMsg.text })
      const aiMsg = { role: 'ai', text: res.data.answer, sources: res.data.sources }
      const newMessages = [...updatedMessages, aiMsg]
      setMessages(newMessages)
      localStorage.setItem('askai_history', JSON.stringify(newMessages))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setMessages([])
    localStorage.removeItem('askai_history')
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleAsk()
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Ask AI</h2>
        {messages.length > 0 && (
          <button
            onClick={handleClear}
            style={{
              padding: '6px 12px',
              fontSize: '11px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              background: '#fff',
              color: '#666',
              cursor: 'pointer'
            }}
          >
            🗑 Clear History
          </button>
        )}
      </div>
      <p style={{ color: '#666' }}>Ask questions about your bank policies and compliance requirements.</p>

      <div style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        minHeight: '300px',
        maxHeight: '500px',
        overflowY: 'auto',
        padding: '1rem',
        marginBottom: '1rem',
        background: '#fafafa'
      }}>
        {messages.length === 0 && <p style={{ color: '#999' }}>Ask a question below to get started.</p>}

        {messages.map((m, i) => (
          <div key={i} style={{
            marginBottom: '1rem',
            textAlign: m.role === 'user' ? 'right' : 'left'
          }}>
            <div style={{
              display: 'inline-block',
              background: m.role === 'user' ? '#1976d2' : '#fff',
              color: m.role === 'user' ? '#fff' : '#333',
              border: m.role === 'ai' ? '1px solid #ddd' : 'none',
              borderRadius: '8px',
              padding: '0.6rem 1rem',
              maxWidth: '80%'
            }}>
              {m.text}
            </div>

            {m.sources && m.sources.length > 0 && (
              <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.3rem' }}>
                Sources: {Array.from(new Set(m.sources.map(s => s.filename).filter(Boolean))).join(', ')}
              </div>
            )}
          </div>
        ))}

        {loading && <p style={{ color: '#999' }}>Thinking...</p>}
      </div>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="e.g. What is the KYC policy for onboarding?"
          style={{ flex: 1, padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
        />
        <button
          onClick={handleAsk}
          disabled={loading}
          style={{ padding: '0.6rem 1.2rem', borderRadius: '6px', border: 'none', background: '#1976d2', color: '#fff', cursor: 'pointer' }}
        >
          Ask
        </button>
      </div>
    </div>
  )
}

export default AskAI
