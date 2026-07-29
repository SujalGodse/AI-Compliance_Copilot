import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell
} from 'recharts'

function priorityColor(priority) {
  if (!priority) return '#0369a1'
  if (priority.startsWith('HIGH'))   return '#c62828'
  if (priority.startsWith('MEDIUM')) return '#b26a00'
  return '#0369a1'
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: '#fff', border: '1px solid #e0e4e8',
      borderRadius: 6, padding: '10px 14px', fontSize: 12,
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
    }}>
      <div style={{ fontWeight: 700, marginBottom: 4, color: '#1a2332' }}>
        Ticket #{d.name}
      </div>
      <div style={{ color: '#6b7684' }}>Drift Score: <strong style={{ color: '#1a2332' }}>{d.drift?.toFixed(3)}</strong></div>
      <div style={{ color: '#6b7684' }}>Priority: <strong>{d.priority}</strong></div>
    </div>
  )
}

function DriftChart({ data }) {
  if (!data || data.length === 0) {
    return <p style={{ fontSize: 13, color: '#6b7684', padding: '20px 0' }}>No drift scores available yet.</p>
  }

  const chartData = data.map(t => ({
    name:     t.ticket_id?.split('-').pop() || t.ticket_id,
    drift:    parseFloat(t.drift_score) || 0,
    priority: t.priority || '',
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e4e8" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: '#6b7684' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          tick={{ fontSize: 11, fill: '#6b7684' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={v => v.toFixed(1)}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0.8} stroke="#c62828" strokeDasharray="4 2"
          label={{ value: 'HIGH', position: 'right', fontSize: 10, fill: '#c62828' }} />
        <ReferenceLine y={0.6} stroke="#b26a00" strokeDasharray="4 2"
          label={{ value: 'MED', position: 'right', fontSize: 10, fill: '#b26a00' }} />
        <Bar dataKey="drift" radius={[4, 4, 0, 0]} maxBarSize={36}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={priorityColor(entry.priority)} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default DriftChart
