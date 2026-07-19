export function ChatWindow() {
  return (
    <section id="chat" className="dashboard-panel chat-panel">
      <div className="panel-kicker">Grounded answers</div>
      <div className="panel-heading">
        <h2>Chat</h2>
        <span className="panel-code">RAG session</span>
      </div>
      <div className="answer-shell">
        <div className="answer-line" />
        <div className="answer-copy">
          <p className="answer-title">Ask across the indexed library</p>
          <p className="panel-muted">Chat controls and citations will land here.</p>
        </div>
      </div>
      <div className="citation-chain" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </section>
  )
}
