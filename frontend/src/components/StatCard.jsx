function StatCard({ label, value, accent }) {
  return (
    <div className="card" style={{ textAlign: 'center', minWidth: 130, flex: 1 }}>
      <div className="stat-number" style={accent ? { color: accent } : {}}>
        {value ?? 0}
      </div>
      <div className="stat-label" style={{ marginTop: 6 }}>{label}</div>
    </div>
  )
}

export default StatCard
