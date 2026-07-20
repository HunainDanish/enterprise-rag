# Enterprise Document Intelligence Platform

A full-stack Retrieval-Augmented Generation (RAG) application that lets users upload business documents, automatically extracts and indexes their content, and answers natural-language questions grounded in that content — with source citations, conversational memory, and a real dashboard.

Built module by module, with each layer (parsing → chunking → embeddings → vector storage → retrieval → prompting → chat memory → dashboard) tested before the next was added.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Data Flow](#data-flow)
- [Document Status Lifecycle](#document-status-lifecycle)
- [Storage Model](#storage-model)
- [Project Status](#project-status)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Overview

This project is an Enterprise Document Intelligence Platform — a knowledge assistant that resembles a real enterprise RAG product rather than a tutorial demo. Users upload PDF, TXT, Markdown, or DOCX files; the backend parses, cleans, chunks, and embeds them locally; a persistent vector store indexes the content; and a Gemini-powered chat interface answers questions with citations back to the exact document, page, and chunk that supports each claim.

The system is designed around one core principle: **the LLM should never answer from memory** — every response is grounded in retrieved chunks that pass a similarity threshold, and the system explicitly says "I don't know" when nothing relevant is found.

## Key Features

- **Multi-format document upload** — PDF, TXT, Markdown, and DOCX, with drag-and-drop and file-picker support and per-file upload progress.
- **Automatic document processing** — text extraction, conservative cleaning (whitespace collapse, repeated header/footer removal), and configurable chunking with citation metadata.
- **Local embedding generation** — chunks and queries are encoded with `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), so ingestion never touches LLM quota.
- **Persistent vector storage** — ChromaDB collection with metadata-based document separation, add/delete/query helpers, and dimension-safety checks.
- **Semantic search** — a standalone `/api/search` endpoint exposes ranked, retrieved chunks (with similarity score and distance) for transparency and grading.
- **Grounded RAG chat** — a versioned, strictly-grounded prompt template with a similarity-threshold cutoff and an explicit "I don't know" fallback.
- **Source citations** — every answer returns de-duplicated sources with filename, page number, exact chunk text, and score.
- **Conversational memory** — session-scoped chat history, follow-up question rewriting into standalone retrieval queries, and session-aware answer caching.
- **Document management** — list, delete (with vector + file cleanup), and refresh/re-embed any document from the UI.
- **Professional dashboard** — Upload, Chat, Document Library, and Stats panels; dark mode; live processing-status polling; chat export to Markdown/JSON.
- **Resilience** — Gemini quota/rate-limit retry with exponential backoff, in-memory answer caching, and background-task failure isolation (a failed document is marked `failed` without crashing the server).

## Architecture

```
User
  │
  ▼
Frontend (React + TypeScript)
  │  REST calls via shared Axios client
  ▼
Backend (FastAPI)
  │  validates request, saves file, schedules background task
  ▼
Document Processing (Loaders + Cleaning)
  │  PDF / TXT / MD / DOCX → uniform {page_number, text} records
  ▼
Chunking (RecursiveCharacterTextSplitter)
  │  overlapping chunks + citation metadata
  ▼
Embedding Generation (sentence-transformers, local)
  │  384-dim vectors
  ▼
Vector Database (ChromaDB, persistent)
  │  stores vectors + metadata, supports filtered nearest-neighbor search
  ▼
Retriever
  │  query embedding → similarity search → threshold filter → top-k chunks
  ▼
LLM (Gemini via LangChain)
  │  grounded prompt, low temperature, quota-aware retry
  ▼
Response
  cited, grounded answer + sources, returned to the user
```

Ingestion (upload → processing → indexing) and querying (question → retrieval → answer) are two independent pipelines that share the same vector store, so uploads never block on chat and vice versa.

## Tech Stack

**Backend**
- Python, FastAPI, Uvicorn
- Pydantic Settings for configuration
- SQLAlchemy + SQLite for document, chat log, and session persistence
- LangChain + LangChain Google GenAI
- Gemini API (`gemini-2.5-flash`)
- ChromaDB (persistent vector store) / FAISS (referenced for lightweight similarity search)
- `sentence-transformers` for local embeddings
- `pypdf` for PDF parsing
- `python-multipart` for file uploads
- `tenacity` for retry/backoff around Gemini calls

**Frontend**
- Vite, React, TypeScript
- Axios, React Router DOM
- Tailwind CSS
- ESLint

**Storage**
- Uploaded source files on disk
- Document metadata in SQLite
- Extracted text, chunks, and local embeddings as JSON sidecar files beside each upload (development-stage; see [Known Limitations](#known-limitations))
- Vectors persisted under `backend/app/vectordb/`

## Repository Structure

```
enterprise-rag/
  backend/
    app/
      api/
        chat.py
        documents.py
        search.py
        stats.py
      core/
        config.py
        database.py
        llm.py
      models/
        chat_log.py
        document.py
      rag/
        cleaning.py
        chunking.py
        embeddings.py
        chain.py
        loaders.py
        processing.py
        prompts.py
        retriever.py
        vectorstore.py
      uploads/
      vectordb/
      main.py
    scripts/
      test_llm.py
    requirements.txt
    .env
  frontend/
    src/
      api/client.ts
      components/
        UploadPanel.tsx
        ChatWindow.tsx
        DocumentLibrary.tsx
        StatsPanel.tsx
        ProcessingStatus.tsx
      App.tsx
      App.css
      index.css
      main.tsx
    public/
    package.json
    vite.config.ts
  .gitignore
  PROJECT_STATUS.md
```

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

Create `backend/.env` (see [Environment Variables](#environment-variables)), then run:

```bash
uvicorn app.main:app --reload
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`

**Verify the Gemini connection:**

```bash
.\venv\Scripts\python.exe scripts\test_llm.py
```

This confirms the API key and quota are working by calling `llm.invoke("Say hello in 5 words")`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

- Dev server: `http://localhost:5173`
- Dashboard routes: `http://localhost:5173/` and `http://localhost:5173/dashboard`

Optional API override:

```bash
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev
```

**Verification:**

```bash
npm run lint
npm run build
```

### Environment Variables

Loaded from `backend/.env` via Pydantic Settings:

| Variable | Purpose | Default |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini API authentication | — (required) |
| `ALLOWED_ORIGINS` | CORS allow-list | `["http://localhost:5173"]` |
| `CHUNK_SIZE` | Characters per chunk | `500` |
| `CHUNK_OVERLAP` | Overlap between chunks | `50` |
| `EMBEDDING_MODEL` | sentence-transformers model name | `all-MiniLM-L6-v2` |
| `DATABASE_URL` | SQLite connection string | `sqlite:///backend/app/documents.db` |
| `UPLOAD_DIR` | On-disk upload folder | `backend/app/uploads` |
| `VITE_API_URL` | Frontend → backend base URL | `http://127.0.0.1:8000` |

## API Reference

### Health Check
```
GET /health
```
```json
{ "status": "ok" }
```

### Upload Documents
```
POST /api/documents/upload
Content-Type: multipart/form-data
Field: files (one or more)
Allowed: .pdf .txt .md .docx
```
```json
[
  {
    "id": "5935cdd8-6924-4354-b945-f16aa1dff01a",
    "filename": "notes.md",
    "filetype": "md",
    "upload_time": "2026-07-18T19:42:20.265688",
    "num_pages": 0,
    "num_chunks": 0,
    "chunk_count": 0,
    "status": "processing"
  }
]
```

### List Documents
```
GET /api/documents
```
Returns all documents, newest first, including `status` and `chunk_count`.

### Delete Document
```
DELETE /api/documents/{document_id}
```
Removes ChromaDB vectors, the uploaded file folder, and the SQLite row. Returns `204 No Content`.

### Refresh Document Embeddings
```
POST /api/documents/{document_id}/refresh
```
Re-runs parsing → cleaning → chunking → embedding → indexing for one document. Returns `409` if already processing.

### Search Retrieved Chunks
```
GET /api/search?q=your+question&top_k=3&document_ids=doc-1&document_ids=doc-2
```
Returns ranked chunks with `similarity_score`, `distance`, source filename, page number, and chunk index.

### Chat / RAG Answer
```
POST /api/chat
```
```json
{
  "session_id": "optional-session-id",
  "query": "your question",
  "chat_history": [],
  "document_ids": null
}
```
```json
{
  "session_id": "session-id",
  "answer": "Grounded answer with citations...",
  "sources": [
    {
      "filename": "policy.pdf",
      "page_number": 2,
      "chunk_text": "Exact retrieved chunk text...",
      "score": 0.72
    }
  ]
}
```
> Backward-compatible: the backend also accepts the earlier `question` field.

### Chat History
```
GET /api/chat/{session_id}/history
```
Returns all stored turns for that session, oldest first.

### Clear Chat Session
```
DELETE /api/chat/{session_id}
```
Deletes all stored turns and the session row.

### Dashboard Stats
```
GET /api/stats
```
```json
{ "total_documents": 3, "total_chunks": 42, "total_questions": 7 }
```

## Data Flow

**Upload → Index**
```
Upload → extension validated → UUID assigned → file saved → SQLite row inserted (status: processing)
  → background task: extract text → clean → write extracted_pages.json
  → chunk (with citation metadata) → write chunks.json → status: embedding
  → encode chunks locally → write embeddings.json
  → store chunks + embeddings + metadata in ChromaDB
  → update num_pages / num_chunks → status: ready (or failed)
```

**Ask a Question**
```
Question → session reused/created → recent turns loaded from SQLite
  → follow-up rewritten into a standalone query (if history exists)
  → answer cache checked (session-aware)
  → query embedded → ChromaDB nearest-neighbor search
  → low-similarity chunks dropped (threshold: 0.25)
  → grounded prompt built (history for reference resolution + retrieved context as evidence)
  → Gemini called with retry/backoff on 429 / RESOURCE_EXHAUSTED
  → sources de-duplicated by (filename, page_number)
  → turn logged to SQLite → session ID, answer, and citations returned
```

## Document Status Lifecycle

```
pending → processing → embedding → ready
                                  ↘ failed
```

- `pending` — row inserted, not yet picked up.
- `processing` — text extraction and cleaning in progress.
- `embedding` — chunking done; local embeddings being generated and indexed.
- `ready` — chunks and vectors are fully indexed and searchable.
- `failed` — an unexpected error occurred; the SQLAlchemy session rolls back and the server keeps running.

## Storage Model

| Data | Location |
|---|---|
| Original uploaded files | `backend/app/uploads/{document_id}/` |
| Document metadata | SQLite (`documents` table) |
| Extracted text | `backend/app/uploads/{document_id}/extracted_pages.json` |
| Chunks | `backend/app/uploads/{document_id}/chunks.json` |
| Local embeddings | `backend/app/uploads/{document_id}/embeddings.json` |
| Vectors + metadata | `backend/app/vectordb/` (ChromaDB, collection: `documents`) |
| Chat logs & sessions | SQLite (`chat_logs` table) |

**Ignored by Git:** `backend/.env`, `backend/venv/`, `backend/app/uploads/`, `backend/app/vectordb/`, `backend/app/*.db`, `frontend/node_modules/`, `frontend/dist/`, `*.log`.

## Project Status

All 14 core modules are implemented and verified:

| Module | Description |
|---|---|
| 0 | Project setup (repo, venv, Vite frontend, dependency install) |
| 1 | Backend skeleton, CORS, health check, OpenAPI file-picker fix |
| 2 | Gemini API configuration and shared LLM client |
| 3 | Multi-format upload API with SQLite document tracking |
| 4 | Document parsing (PDF/TXT/MD/DOCX) and text cleaning |
| 5 | Configurable chunking with citation metadata |
| 6 | Local embedding generation (sentence-transformers) |
| 7 | Persistent ChromaDB vector storage |
| 8 | Semantic search / retrieval endpoint |
| 9 | Grounded prompt construction and Gemini RAG chain |
| 10 | Source citation layer + chat logging |
| 11 | Session-scoped conversational memory + follow-up rewriting |
| 12 | Document management (delete, refresh) |
| 13 | Frontend dashboard skeleton |
| 14 | Full frontend–backend integration |

See `PROJECT_STATUS.md` for the complete module-by-module implementation log.

## Known Limitations

- Extracted text, chunks, and embeddings are duplicated as JSON sidecar files in addition to ChromaDB/SQLite — convenient for debugging, not the final production design.
- DOCX parsing falls back to reading `word/document.xml` directly from the zip when `python-docx` isn't installed, which is less robust than the other loaders.
- No authentication or per-user access control; document filters are trusted as sent by the client.
- Chunk size and overlap are global settings, not tuned per document type.
- No automated retrieval-quality evaluation (precision/recall) yet — verification has been manual/smoke-test based.

## Roadmap

- Hybrid search (dense vector + keyword/BM25) so exact terms aren't lost to semantic approximation.
- Cross-encoder re-ranking of top-k retrieved chunks before prompting.
- Automatic document summarization and suggested questions on upload.
- Token-usage and cost dashboard.
- Structured evaluation harness for retrieval precision/recall and answer faithfulness.
- Access-controlled retrieval scoped by authenticated user/tenant.
- Basic authentication / simulated user sessions.
