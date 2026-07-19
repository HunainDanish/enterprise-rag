export function UploadPanel() {
  return (
    <section id="upload" className="dashboard-panel upload-panel">
      <div className="panel-kicker">Ingestion</div>
      <div className="panel-heading">
        <h2>Upload</h2>
        <span className="panel-code">PDF / DOCX / MD / TXT</span>
      </div>
      <div className="drop-zone">
        <div>
          <p className="drop-title">Document intake queue</p>
          <p className="panel-muted">Upload controls will land here.</p>
        </div>
        <button type="button" className="panel-button">
          Select files
        </button>
      </div>
    </section>
  )
}
