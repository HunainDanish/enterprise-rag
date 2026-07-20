import { useEffect, useState } from 'react'

import {
  getChatHistory,
  searchRetrievedChunks,
  sendChatMessage,
  type ChatHistoryTurn,
  type ChatSource,
  type RetrievedChunk,
} from '../api/client'

type ChatWindowProps = {
  selectedDocumentIds: string[]
  onActivity: () => void
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  retrievedChunks?: RetrievedChunk[]
  createdAt?: string
}

const SESSION_STORAGE_KEY = 'enterprise-rag-session-id'

export function ChatWindow({ selectedDocumentIds, onActivity }: ChatWindowProps) {
  const [sessionId, setSessionId] = useState<string | null>(() =>
    window.localStorage.getItem(SESSION_STORAGE_KEY),
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [query, setQuery] = useState('')
  const [showRetrievedChunks, setShowRetrievedChunks] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (sessionId) {
      window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
    }
  }, [sessionId])

  const loadHistory = async () => {
    if (!sessionId || isLoadingHistory) {
      return
    }

    setIsLoadingHistory(true)
    setError(null)
    try {
      const response = await getChatHistory(sessionId)
      setMessages(historyTurnsToMessages(response.history))
    } catch {
      setError('Chat history unavailable')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const startNewSession = () => {
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
    setSessionId(null)
    setMessages([])
    setError(null)
  }

  const handleSend = async () => {
    const trimmedQuery = query.trim()
    if (!trimmedQuery || isSending) {
      return
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmedQuery,
      createdAt: new Date().toISOString(),
    }
    setMessages((current) => [...current, userMessage])
    setQuery('')
    setIsSending(true)
    setError(null)

    try {
      const documentIds = selectedDocumentIds.length > 0 ? selectedDocumentIds : null
      const [chatResponse, searchResponse] = await Promise.all([
        sendChatMessage({
          session_id: sessionId,
          query: trimmedQuery,
          document_ids: documentIds,
        }),
        showRetrievedChunks
          ? searchRetrievedChunks(trimmedQuery, documentIds)
          : Promise.resolve(null),
      ])

      setSessionId(chatResponse.session_id)
      window.localStorage.setItem(SESSION_STORAGE_KEY, chatResponse.session_id)
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: chatResponse.answer,
          sources: chatResponse.sources,
          retrievedChunks: searchResponse?.results,
          createdAt: new Date().toISOString(),
        },
      ])
      onActivity()
    } catch {
      setError('Chat request failed')
    } finally {
      setIsSending(false)
    }
  }

  const exportSession = (format: 'markdown' | 'json') => {
    const payload =
      format === 'json'
        ? JSON.stringify({ session_id: sessionId, messages }, null, 2)
        : toMarkdown(sessionId, messages)
    const blob = new Blob([payload], {
      type: format === 'json' ? 'application/json' : 'text/markdown',
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `rag-session-${sessionId ?? 'draft'}.${format === 'json' ? 'json' : 'md'}`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section id="chat" className="dashboard-panel chat-panel">
      <div className="panel-kicker">Grounded answers</div>
      <div className="panel-heading">
        <h2>Chat</h2>
        <div className="panel-heading-actions">
          <span className="panel-code">{selectedDocumentIds.length || 'All'} docs</span>
          <span className="panel-code">{sessionId ? `Session ${sessionId.slice(0, 8)}` : 'New session'}</span>
        </div>
      </div>

      <div className="chat-toolbar">
        <label className="toggle-control">
          <input
            type="checkbox"
            checked={showRetrievedChunks}
            onChange={(event) => setShowRetrievedChunks(event.target.checked)}
          />
          <span>Show retrieved chunks</span>
        </label>
        <div className="export-actions">
          <button
            type="button"
            className="icon-button"
            disabled={!sessionId || isLoadingHistory}
            onClick={() => void loadHistory()}
          >
            {isLoadingHistory ? 'Loading' : 'History'}
          </button>
          <button type="button" className="icon-button" onClick={startNewSession}>
            New
          </button>
          <button
            type="button"
            className="icon-button"
            disabled={messages.length === 0}
            onClick={() => exportSession('markdown')}
          >
            MD
          </button>
          <button
            type="button"
            className="icon-button"
            disabled={messages.length === 0}
            onClick={() => exportSession('json')}
          >
            JSON
          </button>
        </div>
      </div>

      <div className="chat-history" aria-live="polite">
        {messages.length === 0 && (
          <div className="answer-shell">
            <div className="answer-line" />
            <div className="answer-copy">
              <p className="answer-title">Ask across the indexed library</p>
              <p className="panel-muted">
                Answers include source citations. Use History to reload the saved session.
              </p>
            </div>
          </div>
        )}
        {messages.map((message) => (
          <article className={`chat-bubble is-${message.role}`} key={message.id}>
            <span className="chat-meta">
              {message.role === 'user' ? 'You' : 'Assistant'}
              {message.createdAt ? ` - ${formatTime(message.createdAt)}` : ''}
            </span>
            <p>{message.content}</p>
            {message.sources && message.sources.length > 0 && (
              <details className="source-details">
                <summary>Sources</summary>
                <div className="source-list">
                  {message.sources.map((source, index) => (
                    <div className="source-card" key={`${source.filename}-${source.page_number}-${index}`}>
                      <strong>{source.filename ?? 'Unknown source'}</strong>
                      <span>Page {source.page_number || 'n/a'} - Score {source.score.toFixed(2)}</span>
                      <p>{source.chunk_text}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
            {showRetrievedChunks && message.retrievedChunks && (
              <details className="source-details" open>
                <summary>Retrieved chunks</summary>
                <div className="source-list">
                  {message.retrievedChunks.map((chunk) => (
                    <div className="source-card" key={`${chunk.document_id}-${chunk.chunk_index}`}>
                      <strong>{chunk.source_filename ?? chunk.document_id}</strong>
                      <span>
                        Page {chunk.page_number || 'n/a'} - Chunk {chunk.chunk_index} - Score{' '}
                        {chunk.similarity_score.toFixed(2)}
                      </span>
                      <p>{chunk.chunk_text}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </article>
        ))}
      </div>

      {error && <p className="panel-error">{error}</p>}
      <form
        className="chat-input-row"
        onSubmit={(event) => {
          event.preventDefault()
          void handleSend()
        }}
      >
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask a grounded question..."
        />
        <button type="submit" className="panel-button" disabled={isSending || !query.trim()}>
          {isSending ? 'Sending' : 'Send'}
        </button>
      </form>
    </section>
  )
}

function historyTurnsToMessages(history: ChatHistoryTurn[]) {
  return history.flatMap((turn) => [
    {
      id: `history-${turn.id}-user`,
      role: 'user' as const,
      content: turn.query,
      createdAt: turn.created_at,
    },
    {
      id: `history-${turn.id}-assistant`,
      role: 'assistant' as const,
      content: turn.answer,
      sources: turn.sources,
      createdAt: turn.created_at,
    },
  ])
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function toMarkdown(sessionId: string | null, messages: ChatMessage[]) {
  const lines = [`# RAG Session ${sessionId ?? 'draft'}`, '']
  for (const message of messages) {
    lines.push(`## ${message.role === 'user' ? 'User' : 'Assistant'}`, '', message.content, '')
    if (message.sources?.length) {
      lines.push('### Sources', '')
      for (const source of message.sources) {
        lines.push(
          `- ${source.filename ?? 'Unknown source'}${source.page_number ? `, page ${source.page_number}` : ''}`,
        )
      }
      lines.push('')
    }
  }
  return lines.join('\n')
}
