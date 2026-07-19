import { Navigate, Route, Routes } from 'react-router-dom'

import { ChatWindow } from './components/ChatWindow'
import { DocumentLibrary } from './components/DocumentLibrary'
import { ProcessingStatus } from './components/ProcessingStatus'
import { StatsPanel } from './components/StatsPanel'
import { UploadPanel } from './components/UploadPanel'
import './App.css'

const navItems = [
  { href: '#upload', label: 'Upload', code: '01' },
  { href: '#chat', label: 'Chat', code: '02' },
  { href: '#library', label: 'Library', code: '03' },
  { href: '#stats', label: 'Stats', code: '04' },
]

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function Dashboard() {
  return (
    <div className="app-shell text-sm antialiased">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-mark">ER</span>
          <div>
            <p>Enterprise RAG</p>
            <span>Document Intelligence</span>
          </div>
        </div>
        <nav className="side-nav" aria-label="Dashboard panels">
          {navItems.map((item) => (
            <a href={item.href} key={item.href}>
              <span>{item.code}</span>
              {item.label}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span>Verified index</span>
          <strong>Source-aware workspace</strong>
        </div>
      </aside>

      <main className="dashboard-main text-sm">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Document intelligence console</p>
            <h1>Knowledge operations</h1>
          </div>
          <ProcessingStatus />
        </header>

        <div className="dashboard-grid">
          <UploadPanel />
          <ChatWindow />
          <DocumentLibrary />
          <StatsPanel />
        </div>
      </main>
    </div>
  )
}

export default App
