import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export type DocumentRecord = {
  id: string
  filename: string
  filetype: string
  upload_time: string
  num_pages: number
  num_chunks: number
  chunk_count: number
  status: string
}

export type ChatSource = {
  filename: string | null
  page_number: number | null
  chunk_text: string
  score: number
}

export type ChatResponse = {
  session_id: string
  answer: string
  sources: ChatSource[]
}

export type ChatHistoryTurn = {
  id: number
  query: string
  answer: string
  sources: ChatSource[]
  created_at: string
}

export type ChatHistoryResponse = {
  session_id: string
  history: ChatHistoryTurn[]
}

export type RetrievedChunk = {
  document_id: string
  source_filename: string | null
  page_number: number | null
  chunk_index: number
  chunk_text: string
  similarity_score: number
  distance: number
}

export type SearchResponse = {
  query: string
  top_k: number
  document_ids: string[] | null
  results: RetrievedChunk[]
}

export type DashboardStats = {
  total_documents: number
  total_chunks: number
  total_questions: number
}

export async function listDocuments() {
  const response = await apiClient.get<DocumentRecord[]>('/api/documents')
  return response.data
}

export async function uploadDocument(file: File, onProgress: (progress: number) => void) {
  const formData = new FormData()
  formData.append('files', file)

  const response = await apiClient.post<DocumentRecord[]>('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (!event.total) {
        return
      }
      onProgress(Math.round((event.loaded / event.total) * 100))
    },
  })

  return response.data[0]
}

export async function deleteDocument(documentId: string) {
  await apiClient.delete(`/api/documents/${documentId}`)
}

export async function refreshDocument(documentId: string) {
  const response = await apiClient.post<DocumentRecord>(`/api/documents/${documentId}/refresh`)
  return response.data
}

export async function sendChatMessage(payload: {
  session_id: string | null
  query: string
  document_ids: string[] | null
}) {
  const response = await apiClient.post<ChatResponse>('/api/chat', payload)
  return response.data
}

export async function getChatHistory(sessionId: string) {
  const response = await apiClient.get<ChatHistoryResponse>(`/api/chat/${sessionId}/history`)
  return response.data
}

export async function searchRetrievedChunks(query: string, documentIds: string[] | null) {
  const response = await apiClient.get<SearchResponse>('/api/search', {
    params: {
      q: query,
      top_k: 5,
      document_ids: documentIds,
    },
    paramsSerializer: {
      indexes: null,
    },
  })
  return response.data
}

export async function getDashboardStats() {
  const response = await apiClient.get<DashboardStats>('/api/stats')
  return response.data
}
