import { useEffect, useState } from 'react'

import { getDashboardStats, type DashboardStats } from '../api/client'

type StatsPanelProps = {
  refreshKey: number
}

const emptyStats: DashboardStats = {
  total_documents: 0,
  total_chunks: 0,
  total_questions: 0,
}

export function StatsPanel({ refreshKey }: StatsPanelProps) {
  const [stats, setStats] = useState<DashboardStats>(emptyStats)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setStats(await getDashboardStats())
        setError(null)
      } catch {
        setError('Stats unavailable')
      }
    }

    void fetchStats()
  }, [refreshKey])

  const tiles = [
    { label: 'Documents', value: stats.total_documents },
    { label: 'Chunks', value: stats.total_chunks },
    { label: 'Questions', value: stats.total_questions },
  ]

  return (
    <section id="stats" className="dashboard-panel stats-panel">
      <div className="panel-kicker">Operations</div>
      <div className="panel-heading">
        <h2>Stats</h2>
        <span className="panel-code">Index health</span>
      </div>
      {error && <p className="panel-error">{error}</p>}
      <div className="stats-grid">
        {tiles.map((stat) => (
          <div className="stat-tile" key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}
