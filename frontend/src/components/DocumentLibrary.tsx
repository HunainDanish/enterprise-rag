const libraryRows = ['Board policy handbook', 'Procurement controls', 'Security appendix']

export function DocumentLibrary() {
  return (
    <section id="library" className="dashboard-panel library-panel">
      <div className="panel-kicker">Traceable sources</div>
      <div className="panel-heading">
        <h2>Library</h2>
        <span className="panel-code">Documents</span>
      </div>
      <div className="library-list">
        {libraryRows.map((row, index) => (
          <div className="library-row" key={row}>
            <span className="source-mark" />
            <div>
              <p>{row}</p>
              <span>Source shell {index + 1}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
