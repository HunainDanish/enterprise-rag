import { useCallback, useEffect, useState } from 'react'

import {
  deleteDocument,
  listDocuments,
  refreshDocument,
  type DocumentRecord,
} from '../api/client'

type DocumentLibraryProps = {
  refreshKey: number
  selectedDocumentIds: string[]
  onSelectionChange: (documentIds: string[]) => void
  onDocumentsChanged: () => void
}

export function DocumentLibrary({
  refreshKey,
  selectedDocumentIds,
  onSelectionChange,
  onDocumentsChanged,
}: DocumentLibraryProps) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null)

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoading(true)
      const nextDocuments = await listDocuments()
      setDocuments(nextDocuments)
      setError(null)
      const existingIds = new Set(nextDocuments.map((document) => document.id))
      const nextSelection = selectedDocumentIds.filter((id) => existingIds.has(id))
      if (nextSelection.length !== selectedDocumentIds.length) {
        onSelectionChange(nextSelection)
      }
    } catch {
      setError('Unable to load documents')
    } finally {
      setIsLoading(false)
    }
  }, [onSelectionChange, selectedDocumentIds])

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      void fetchDocuments()
    }, 0)

    return () => window.clearTimeout(timerId)
  }, [fetchDocuments, refreshKey])

  const toggleDocument = (documentId: string) => {
    if (selectedDocumentIds.includes(documentId)) {
      onSelectionChange(selectedDocumentIds.filter((id) => id !== documentId))
      return
    }

    onSelectionChange([...selectedDocumentIds, documentId])
  }

  const handleDelete = async (documentId: string) => {
    setBusyDocumentId(documentId)
    try {
      await deleteDocument(documentId)
      onSelectionChange(selectedDocumentIds.filter((id) => id !== documentId))
      await fetchDocuments()
      onDocumentsChanged()
    } finally {
      setBusyDocumentId(null)
    }
  }

  const handleRefresh = async (documentId: string) => {
    setBusyDocumentId(documentId)
    try {
      await refreshDocument(documentId)
      await fetchDocuments()
      onDocumentsChanged()
    } finally {
      setBusyDocumentId(null)
    }
  }

  return (
    <section id="library" className="dashboard-panel library-panel">
      <div className="panel-kicker">Traceable sources</div>
      <div className="panel-heading">
        <h2>Library</h2>
        <button type="button" className="icon-button" onClick={() => void fetchDocuments()}>
          Refresh
        </button>
      </div>
      <div className="library-list">
        {isLoading && <p className="panel-muted">Loading documents.</p>}
        {error && <p className="panel-error">{error}</p>}
        {!isLoading && !error && documents.length === 0 && (
          <p className="panel-muted">No documents indexed yet.</p>
        )}
        {documents.map((document) => (
          <div className="library-row" key={document.id}>
            <label className="filter-check">
              <input
                type="checkbox"
                checked={selectedDocumentIds.includes(document.id)}
                onChange={() => toggleDocument(document.id)}
              />
              <span>{filetypeLabel(document.filetype)}</span>
            </label>
            <div>
              <p>{document.filename}</p>
              <span>
                {document.chunk_count} chunks · {document.filetype.toUpperCase()}
              </span>
            </div>
            <div className="library-actions">
              <span className={`status-badge status-${document.status}`}>{document.status}</span>
              <button
                type="button"
                className="icon-button"
                disabled={busyDocumentId === document.id}
                onClick={() => void handleRefresh(document.id)}
              >
                Reindex
              </button>
              <button
                type="button"
                className="icon-button is-danger"
                disabled={busyDocumentId === document.id}
                onClick={() => void handleDelete(document.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function filetypeLabel(filetype: string) {
  return filetype.slice(0, 4).toUpperCase()
}
