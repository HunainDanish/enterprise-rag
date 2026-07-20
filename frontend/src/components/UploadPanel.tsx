import { useEffect, useMemo, useRef, useState } from 'react'

import { listDocuments, uploadDocument, type DocumentRecord } from '../api/client'

type UploadPanelProps = {
  onDocumentsChanged: () => void
}

type UploadItem = {
  key: string
  filename: string
  progress: number
  status: string
  documentId?: string
  error?: string
}

const ACTIVE_STATUSES = new Set(['pending', 'processing', 'embedding'])
const POLL_INTERVAL_MS = 2500

export function UploadPanel({ onDocumentsChanged }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [items, setItems] = useState<UploadItem[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const activeDocumentIds = useMemo(
    () =>
      items
        .filter((item) => item.documentId && ACTIVE_STATUSES.has(item.status))
        .map((item) => item.documentId as string),
    [items],
  )

  useEffect(() => {
    if (activeDocumentIds.length === 0) {
      return
    }

    const poll = async () => {
      const documents = await listDocuments()
      setItems((current) => mergePolledStatuses(current, documents))
      onDocumentsChanged()
    }

    const timerId = window.setInterval(() => {
      void poll()
    }, POLL_INTERVAL_MS)

    return () => window.clearInterval(timerId)
  }, [activeDocumentIds, onDocumentsChanged])

  const handleFiles = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList)
    const queuedItems = files.map((file) => ({
      key: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
      filename: file.name,
      progress: 0,
      status: 'queued',
    }))
    setItems((current) => [...queuedItems, ...current])

    await Promise.all(
      files.map(async (file, index) => {
        const key = queuedItems[index].key
        try {
          setItem(key, { status: 'uploading' })
          const document = await uploadDocument(file, (progress) => {
            setItem(key, { progress })
          })
          setItem(key, {
            documentId: document.id,
            progress: 100,
            status: document.status,
          })
          onDocumentsChanged()
        } catch {
          setItem(key, {
            error: 'Upload failed',
            status: 'failed',
          })
        }
      }),
    )
  }

  const setItem = (key: string, patch: Partial<UploadItem>) => {
    setItems((current) =>
      current.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    )
  }

  return (
    <section id="upload" className="dashboard-panel upload-panel">
      <div className="panel-kicker">Ingestion</div>
      <div className="panel-heading">
        <h2>Upload</h2>
        <span className="panel-code">PDF / DOCX / MD / TXT</span>
      </div>
      <div
        className={isDragging ? 'drop-zone is-dragging' : 'drop-zone'}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          void handleFiles(event.dataTransfer.files)
        }}
      >
        <div>
          <p className="drop-title">Document intake queue</p>
          <p className="panel-muted">Drop files here or select PDF, DOCX, Markdown, and TXT files.</p>
        </div>
        <input
          ref={inputRef}
          className="visually-hidden"
          type="file"
          multiple
          accept=".pdf,.docx,.md,.txt"
          onChange={(event) => {
            if (event.target.files) {
              void handleFiles(event.target.files)
              event.target.value = ''
            }
          }}
        />
        <button type="button" className="panel-button" onClick={() => inputRef.current?.click()}>
          Select files
        </button>
      </div>
      <div className="upload-list">
        {items.map((item) => (
          <div className="upload-row" key={item.key}>
            <div>
              <p>{item.filename}</p>
              <span>{item.error ?? statusLabel(item.status)}</span>
            </div>
            <div className="progress-track" aria-label={`${item.filename} upload progress`}>
              <span style={{ width: `${item.progress}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function mergePolledStatuses(items: UploadItem[], documents: DocumentRecord[]) {
  const documentsById = new Map(documents.map((document) => [document.id, document]))
  return items.map((item) => {
    if (!item.documentId) {
      return item
    }

    const document = documentsById.get(item.documentId)
    if (!document) {
      return item
    }

    return { ...item, status: document.status }
  })
}

function statusLabel(status: string) {
  if (status === 'embedding') {
    return 'Embedding chunks'
  }

  if (status === 'processing') {
    return 'Extracting text'
  }

  if (status === 'ready') {
    return 'Ready'
  }

  return status
}
