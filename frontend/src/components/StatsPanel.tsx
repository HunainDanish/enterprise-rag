const stats = [
  { label: 'Documents', value: '--' },
  { label: 'Chunks', value: '--' },
  { label: 'Ready', value: '--' },
]

export function StatsPanel() {
  return (
    <section id="stats" className="dashboard-panel stats-panel">
      <div className="panel-kicker">Operations</div>
      <div className="panel-heading">
        <h2>Stats</h2>
        <span className="panel-code">Index health</span>
      </div>
      <div className="stats-grid">
        {stats.map((stat) => (
          <div className="stat-tile" key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}
