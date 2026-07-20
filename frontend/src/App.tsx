import { Navigate, Route, Routes } from 'react-router-dom'
import { useState } from 'react'

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
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([])
  const [refreshKey, setRefreshKey] = useState(0)
  const [isDarkMode, setIsDarkMode] = useState(true)

  const refreshDashboard = () => setRefreshKey((current) => current + 1)

  return (
    <div
      className={`${isDarkMode ? 'dark theme-dark' : 'theme-light'} app-shell text-sm antialiased`}
    >
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
          <div className="header-actions">
            <button
              type="button"
              className="mode-toggle dark:border-amber-500/40 dark:text-amber-200"
              onClick={() => setIsDarkMode((current) => !current)}
            >
              {isDarkMode ? 'Light' : 'Dark'}
            </button>
            <ProcessingStatus refreshKey={refreshKey} />
          </div>
        </header>

        <div className="dashboard-grid">
          <UploadPanel onDocumentsChanged={refreshDashboard} />
          <ChatWindow selectedDocumentIds={selectedDocumentIds} onActivity={refreshDashboard} />
          <DocumentLibrary
            refreshKey={refreshKey}
            selectedDocumentIds={selectedDocumentIds}
            onSelectionChange={setSelectedDocumentIds}
            onDocumentsChanged={refreshDashboard}
          />
          <StatsPanel refreshKey={refreshKey} />
        </div>
      </main>
    </div>
  )
}

export default App
