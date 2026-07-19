import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../api/client'

type DocumentStatus = {
  id: string
  filename: string
  status: string
}

const POLL_INTERVAL_MS = 4000

export function ProcessingStatus() {
  const [documents, setDocuments] = useState<DocumentStatus[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await apiClient.get<DocumentStatus[]>('/api/documents')
      setDocuments(response.data)
      setError(null)
    } catch {
      setError('Document status unavailable')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const activeDocuments = documents.filter((document) => document.status !== 'ready')
  const hasActiveDocuments = activeDocuments.length > 0

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      void fetchDocuments()
    }, 0)

    return () => window.clearTimeout(timerId)
  }, [fetchDocuments])

  useEffect(() => {
    if (!hasActiveDocuments) {
      return
    }

    const timerId = window.setInterval(() => {
      void fetchDocuments()
    }, POLL_INTERVAL_MS)

    return () => window.clearInterval(timerId)
  }, [fetchDocuments, hasActiveDocuments])

  return (
    <aside className="processing-status" aria-live="polite">
      <span className={hasActiveDocuments ? 'status-dot is-active' : 'status-dot'} />
      <div>
        <p>{statusLabel(isLoading, error, hasActiveDocuments, activeDocuments.length)}</p>
        <span>{statusDetail(isLoading, error, documents.length)}</span>
      </div>
    </aside>
  )
}

function statusLabel(
  isLoading: boolean,
  error: string | null,
  hasActiveDocuments: boolean,
  activeCount: number,
) {
  if (isLoading) {
    return 'Checking index'
  }

  if (error) {
    return error
  }

  if (hasActiveDocuments) {
    return `${activeCount} processing`
  }

  return 'Index ready'
}

function statusDetail(isLoading: boolean, error: string | null, documentCount: number) {
  if (isLoading) {
    return 'Polling document library'
  }

  if (error) {
    return 'Retry on next refresh'
  }

  return `${documentCount} documents tracked`
}
