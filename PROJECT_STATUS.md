# Enterprise Document Intelligence Platform - Project Status

Last updated: July 19, 2026

## Project Overview

This project is an Enterprise Document Intelligence Platform built as a full-stack RAG application. The goal is to let users upload business documents, extract and clean their text, index the content into a vector database, and later ask questions over those documents using Gemini through LangChain.

The project currently has a working FastAPI backend foundation, Gemini API wiring, SQLite-backed document tracking, multi-format upload support, document text extraction for PDF, TXT, Markdown, and DOCX files, configurable retrieval chunking, local sentence-transformer embedding generation, persistent ChromaDB vector storage, a semantic search retrieval endpoint, a grounded Gemini RAG answer chain, a source citation layer with SQLite chat logging, and session-scoped conversational memory.

The system is being built module by module so each layer is tested before more RAG logic is added.

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic Settings
- SQLAlchemy
- SQLite
- LangChain
- LangChain Google GenAI
- Gemini API
- ChromaDB
- FAISS
- sentence-transformers
- pypdf
- python-multipart

### Frontend

- Vite
- React
- TypeScript
- ESLint
- Axios
- React Router DOM
- Tailwind CSS

### Storage

- Uploaded source files are stored on disk.
- Document metadata is stored in SQLite.
- Extracted text, retrieval chunks, and local embeddings are currently stored as JSON sidecar files beside uploaded documents.
- Vector storage is persisted under `backend/app/vectordb/`.

## Repository Structure

```text
enterprise-rag/
  backend/
    app/
      api/
        chat.py
        documents.py
        search.py
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
    public/
    package.json
  .gitignore
  PROJECT_STATUS.md
```

## Implemented Modules

## Module 0: Initial Project Setup

The base repository setup is complete.

Implemented:

- Created the `enterprise-rag/` project root.
- Initialized Git and pushed the project to GitHub.
- Created `backend/`.
- Created a Python virtual environment inside `backend/venv`.
- Installed and froze backend dependencies into `backend/requirements.txt`.
- Created the backend app folder structure:
  - `api`
  - `core`
  - `services`
  - `rag`
  - `models`
  - `utils`
  - `uploads`
  - `vectordb`
- Created `frontend/` using Vite, React, and TypeScript.
- Installed frontend packages including Axios, React Router DOM, and Tailwind.
- Added `.gitignore` rules for virtual environments, node modules, environment files, uploads, vector DB files, SQLite DB files, and logs.

Verified:

- Backend imports worked for core dependencies.
- Frontend Vite dev server opened successfully with the default React page.

## Module 1: Backend Skeleton and Health Check

The FastAPI backend skeleton is implemented.

Implemented files:

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/api/documents.py`
- `backend/app/api/chat.py`
- `backend/app/api/search.py`

Implemented behavior:

- Created the main FastAPI app.
- Enabled CORS for the Vite dev origin:

```text
http://localhost:5173
```

- Added placeholder routers for future features:
  - `/api/documents`
  - `/api/chat`
  - `/api/search`
- Added a health endpoint:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

- Added FastAPI lifespan startup logic to initialize the SQLite database tables.
- Added a custom OpenAPI schema normalizer so Swagger UI correctly renders multipart file uploads as file pickers.

Important note:

The OpenAPI fix exists because the installed FastAPI/Pydantic combination emitted upload fields using `contentMediaType`, which Swagger UI showed as `array<string>`. The project now rewrites those fields to `format: binary`, which Swagger UI understands as file upload input.

Verified:

- `/docs` loads.
- `/health` returns `{"status": "ok"}`.

## Module 2: Configuration and Gemini API Key Wiring

Gemini API configuration is implemented and tested.

Implemented files:

- `backend/app/core/config.py`
- `backend/app/core/llm.py`
- `backend/scripts/test_llm.py`

Configuration currently loaded through Pydantic Settings:

- `GOOGLE_API_KEY`
- `ALLOWED_ORIGINS`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `EMBEDDING_MODEL`
- `DATABASE_URL`
- `UPLOAD_DIR`

The settings class loads values from:

```text
backend/.env
```

The shared Gemini LLM instance is created in:

```text
backend/app/core/llm.py
```

Current LLM configuration:

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.2,
)
```

This gives the project one reusable Gemini client instead of creating a new client for every request.

Test script:

```text
backend/scripts/test_llm.py
```

The script calls:

```python
llm.invoke("Say hello in 5 words")
```

Verified:

- The Google API key is loaded from `.env`.
- Gemini API authentication works.
- Gemini returned a valid response.

## Module 3: Multi-Format Document Upload API

The document upload API is implemented with persistent SQLite tracking.

Implemented files:

- `backend/app/api/documents.py`
- `backend/app/models/document.py`
- `backend/app/core/database.py`

Supported upload formats:

- `.pdf`
- `.txt`
- `.md`
- `.docx`

Implemented endpoints:

```http
POST /api/documents/upload
```

Accepts one or more uploaded files using FastAPI `UploadFile` and `File`.

The endpoint uses:

```python
files: Annotated[list[UploadFile], File(description="One or more documents to upload")]
```

This is the modern FastAPI style for multipart file uploads.

Upload behavior:

1. Validate that every uploaded file has a filename.
2. Sanitize the filename to avoid unsafe path traversal.
3. Validate the extension.
4. Generate a unique document ID with UUID.
5. Save the original file to:

```text
backend/app/uploads/{document_id}/original_filename
```

6. Insert a document row into SQLite.
7. Return uploaded document metadata as JSON.
8. Start background text extraction and chunking.

Implemented list endpoint:

```http
GET /api/documents
```

Returns all documents ordered by upload time, newest first.

Document database model:

```text
id
filename
filetype
upload_time
num_pages
num_chunks
status
```

Chat log database model:

```text
id
session_id
query
sources_json
answer
created_at
```

Chat session database model:

```text
id
created_at
updated_at
```

Current status values used:

- `pending`
- `processing`
- `embedding`
- `ready`
- `failed`

Current default values:

- `num_pages = 0`
- `num_chunks = 0`
- `status = "pending"` at initial insert

After upload, the route marks the document as `processing` and schedules background parsing.

Verified:

- Valid files upload successfully.
- Invalid file extensions return HTTP 400.
- Files are saved under the correct UUID folder.
- SQLite records are created.
- `GET /api/documents` returns uploaded document metadata.
- Swagger UI now shows the file picker instead of a plain text field.

## Module 4: Document Parsing and Text Extraction

Document parsing and cleaning are implemented.

Implemented files:

- `backend/app/rag/loaders.py`
- `backend/app/rag/cleaning.py`
- `backend/app/rag/processing.py`

### Loader Interface

Every loader returns the same shape:

```python
[
    {
        "page_number": int | None,
        "text": str
    }
]
```

This uniform return shape is important because later RAG modules will be able to chunk, embed, search, and cite documents without caring whether the source file was a PDF, TXT file, Markdown file, or DOCX file.

### PDF Loader

Function:

```python
load_pdf(path: Path) -> list[PageText]
```

Implementation:

- Uses `pypdf.PdfReader`.
- Extracts text page by page.
- Preserves page numbers starting at `1`.

Example return shape:

```json
[
  {
    "page_number": 1,
    "text": "Extracted page text..."
  }
]
```

This is ready for future citation support.

### TXT Loader

Function:

```python
load_txt(path: Path) -> list[PageText]
```

Implementation:

- Reads the file as UTF-8.
- Ignores invalid encoding characters.
- Returns one text record with `page_number = None`.

### Markdown Loader

Function:

```python
load_markdown(path: Path) -> list[PageText]
```

Implementation:

- Reads Markdown as UTF-8.
- Lightly strips Markdown syntax.
- Keeps headings as meaningful text.
- Converts Markdown links to their visible link text.
- Removes simple bold, italic, strikethrough, inline-code markers, and list markers.
- Returns one text record with `page_number = None`.

The goal is conservative cleanup, not aggressive Markdown rendering.

### DOCX Loader

Function:

```python
load_docx(path: Path) -> list[PageText]
```

Implementation:

- Tries to use `python-docx` if installed.
- If `python-docx` is not installed, falls back to reading `word/document.xml` directly from the DOCX zip file.
- Extracts paragraph text.
- Returns one text record with `page_number = None`.

Current environment note:

- `python-docx` is not installed in the virtual environment.
- The fallback XML-based loader is working and has successfully extracted text from existing uploaded DOCX files.

### Cleaning

Implemented in:

```text
backend/app/rag/cleaning.py
```

Current cleaning behavior:

- Removes non-printable characters.
- Removes zero-width Unicode markers.
- Collapses repeated whitespace.
- Removes empty lines.
- Conservatively detects repeated first/last lines across multi-page documents and removes likely repeated headers/footers.

The cleaning is intentionally conservative so meaningful punctuation and document content are not stripped accidentally.

### Background Processing

Implemented in:

```text
backend/app/rag/processing.py
```

Current background flow:

1. Load the document row by ID.
2. Mark status as `processing`.
3. Choose the correct loader based on file type.
4. Extract raw text.
5. Clean extracted text.
6. Write extracted pages to:

```text
backend/app/uploads/{document_id}/extracted_pages.json
```

7. Pass cleaned pages into chunking.
8. Pass chunks into local embedding generation.
9. Store chunks, embeddings, and metadata in ChromaDB.
10. Update `num_pages` and `num_chunks`.
11. Mark status as `ready`.
12. If anything fails, mark status as `failed`.

Current development behavior:

- `processing.py` prints a short extraction preview to the console.
- This is useful while building, but it can be removed or replaced with structured logging later.

Verified:

- Markdown upload moves through extraction successfully.
- Extracted Markdown text is cleaned.
- `extracted_pages.json` is written successfully.
- Existing uploaded PDF files parse successfully.
- Existing uploaded DOCX files parse successfully through the fallback loader.

## Module 5: Chunking Strategy

Document chunking is implemented and wired into background processing.

Implemented files:

- `backend/app/rag/chunking.py`
- `backend/app/rag/processing.py`
- `backend/app/core/config.py`

Chunking behavior:

- Uses LangChain's `RecursiveCharacterTextSplitter`.
- Reads chunk settings from application configuration:
  - `settings.CHUNK_SIZE`
  - `settings.CHUNK_OVERLAP`
- Current defaults:
  - `CHUNK_SIZE = 500`
  - `CHUNK_OVERLAP = 50`
- Splits cleaned page text after extraction and cleaning.
- Skips empty cleaned pages.
- Preserves metadata on every chunk:
  - `document_id`
  - `filename`
  - `page_number`
  - `chunk_index`

Chunk sidecar output:

```text
backend/app/uploads/{document_id}/chunks.json
```

Each chunk is stored in this shape:

```json
{
  "page_content": "Chunk text...",
  "metadata": {
    "document_id": "document uuid",
    "filename": "source.pdf",
    "page_number": 1,
    "chunk_index": 0
  }
}
```

Background processing now:

1. Extracts raw document text.
2. Cleans extracted page text.
3. Writes `extracted_pages.json`.
4. Chunks cleaned text.
5. Writes `chunks.json`.
6. Sets document status to `embedding` before Module 6 handles vectors.

Verified:

- `backend/app/rag/chunking.py`, `backend/app/rag/processing.py`, and `backend/app/core/config.py` compile successfully.
- The backend virtual environment imports `RecursiveCharacterTextSplitter` and `app.rag.chunking.chunk_pages` successfully.

## Module 6: Embedding Generation

Local embedding generation is implemented and wired into background processing.

Implemented files:

- `backend/app/rag/embeddings.py`
- `backend/app/rag/processing.py`
- `backend/app/core/config.py`

Embedding behavior:

- Uses `sentence-transformers` locally, so embedding does not consume Gemini API quota.
- Loads a single shared `SentenceTransformer` model at module import time.
- Uses the configured model from `settings.EMBEDDING_MODEL`.
- Current default:
  - `EMBEDDING_MODEL = "all-MiniLM-L6-v2"`
- Provides:

```python
encode_texts(texts: list[str]) -> list[list[float]]
```

- Encodes chunks in batches using:
  - `batch_size=32`
  - `show_progress_bar=False`
- Returns plain Python lists so embeddings can be serialized as JSON and inserted into the vector store.
- Returns an empty list immediately when there are no chunks.

Embedding sidecar output:

```text
backend/app/uploads/{document_id}/embeddings.json
```

Embeddings are stored in the same order as `chunks.json`, so later vector-store indexing can pair each vector with the chunk at the same index.

Background processing now:

1. Extracts raw document text.
2. Cleans extracted page text.
3. Writes `extracted_pages.json`.
4. Chunks cleaned text.
5. Writes `chunks.json`.
6. Sets document status to `embedding` while vectors are generated.
7. Encodes all chunk text in one batched call.
8. Writes `embeddings.json`.
9. Passes embeddings to Module 7 for vector storage.

Verified:

- `backend/app/rag/embeddings.py`, `backend/app/rag/processing.py`, `backend/app/rag/chunking.py`, and `backend/app/core/config.py` compile successfully.
- The backend virtual environment loads `all-MiniLM-L6-v2` through `sentence-transformers`.
- A smoke test encoded two texts into two 384-dimensional float vectors.

## Module 7: Vector Database - ChromaDB

Persistent vector storage is implemented with ChromaDB.

Implemented files:

- `backend/app/rag/vectorstore.py`
- `backend/app/rag/processing.py`

Vector store behavior:

- Uses ChromaDB `PersistentClient(path="app/vectordb")`.
- Uses one shared collection for the whole app:
  - `documents`
- Uses embeddings from `settings.EMBEDDING_MODEL`.
- Current embedding model:
  - `all-MiniLM-L6-v2`
- Current expected embedding dimension:
  - `384`
- Stores every chunk in the shared collection and separates documents by `document_id` metadata.
- Uses stable Chroma IDs in this shape:

```text
{document_id}:{chunk_index}
```

- Stores chunk text as Chroma documents.
- Stores precomputed local embeddings from Module 6.
- Stores chunk metadata:
  - `document_id`
  - `filename`
  - `page_number`
  - `chunk_index`

Chroma metadata note:

- ChromaDB rejects `None` metadata values.
- For non-paginated sources such as TXT, Markdown, and DOCX, `page_number=None` is normalized to `page_number=0` inside ChromaDB.
- The original `chunks.json` sidecar still preserves the loader output metadata.

Implemented functions:

```python
add_chunks(document_id, chunks, embeddings)
delete_document(document_id)
query(embedding, top_k, filter=None)
```

Function behavior:

- `add_chunks` validates that chunk and embedding counts match.
- `add_chunks` validates that every embedding length matches the current embedding model dimension before calling ChromaDB.
- `add_chunks` deletes existing vectors for the same `document_id` before inserting, so reprocessing a document does not duplicate chunks.
- `add_chunks` rejects duplicate generated chunk IDs before insertion.
- `delete_document` removes vectors with `where={"document_id": document_id}`.
- `query` performs vector search with optional Chroma metadata filtering.
- `query` requires `top_k >= 1`.
- `query` validates that the query embedding length matches the current embedding model dimension.

Dimension mismatch handling:

- ChromaDB locks a collection's embedding dimension after the first insert.
- During development, if the persistent `documents` collection expects a different dimension than the current embedding model, the app recreates only that collection.
- The app does not recreate the collection on every startup.
- Once the collection accepts 384-dimensional `all-MiniLM-L6-v2` embeddings, vectors persist across server restarts.
- For empty collections that may still be locked to an old dimension, startup uses a temporary 384-dimensional probe embedding and recreates only if Chroma rejects it.

Background processing now:

1. Extracts raw document text.
2. Cleans extracted page text.
3. Writes `extracted_pages.json`.
4. Chunks cleaned text.
5. Writes `chunks.json`.
6. Sets document status to `embedding`.
7. Encodes all chunk text locally.
8. Writes `embeddings.json`.
9. Stores chunks, embeddings, and metadata in ChromaDB.
10. Updates `num_pages`.
11. Updates `num_chunks`.
12. Sets document status to `ready`.

Error handling:

- Chroma insertion failures are logged.
- Background processing logs unexpected failures.
- The SQLAlchemy session rolls back on failure.
- The document status is set to `failed`.
- Background task exceptions are not re-raised after the document is marked failed, so the server keeps running.

Verified:

- `add_chunks`, filtered `query`, and `delete_document` were tested through the backend virtual environment against ChromaDB.
- The test inserted two chunks, queried one result by `document_id`, confirmed metadata, deleted the document, and confirmed filtered query returned no IDs.
- A dimension smoke test confirmed that 384-dimensional vectors insert successfully and 3-dimensional vectors are rejected by `add_chunks` before ChromaDB insertion.

## Module 8: Semantic Search / Retrieval Pipeline

Semantic search retrieval is implemented and exposed through its own inspection endpoint.

Implemented files:

- `backend/app/rag/retriever.py`
- `backend/app/api/search.py`

Retrieval behavior:

- Provides:

```python
retrieve(query, top_k=5, document_ids=None)
```

- Embeds user questions with the same `encode_texts` function used for document chunks.
- Calls the shared ChromaDB vector store `query` helper.
- Supports optional filtering by one or more `document_id` values.
- Returns UI-ready retrieved chunk rows with:
  - `document_id`
  - `source_filename`
  - `page_number`
  - `chunk_index`
  - `chunk_text`
  - `similarity_score`
  - `distance`

Score note:

- ChromaDB returns distances, where smaller means closer.
- The retriever exposes `similarity_score = 1 / (1 + distance)`, where larger means more similar, and also keeps the raw `distance` for debugging.

Implemented endpoint:

```http
GET /api/search?q=...
```

Optional query parameters:

- `top_k`
- `document_ids`

Example response shape:

```json
{
  "query": "What does the policy say about approvals?",
  "top_k": 5,
  "document_ids": null,
  "results": [
    {
      "document_id": "5935cdd8-6924-4354-b945-f16aa1dff01a",
      "source_filename": "policy.pdf",
      "page_number": 2,
      "chunk_index": 4,
      "chunk_text": "Relevant chunk text...",
      "similarity_score": 0.72,
      "distance": 0.38
    }
  ]
}
```

Verified:

- `backend/app/rag/retriever.py` and `backend/app/api/search.py` compile successfully.
- A FastAPI `TestClient` smoke test for `GET /api/search?q=test+query&top_k=1` returned HTTP 200 with a retrieved chunk from the existing ChromaDB collection.

## Module 9: Prompt Construction & Gemini RAG Chain

Grounded prompt construction and the Gemini RAG answer chain are implemented.

Implemented files:

- `backend/app/rag/prompts.py`
- `backend/app/rag/chain.py`
- `backend/app/api/chat.py`

Prompt behavior:

- Defines a single versioned prompt:

```python
RAG_PROMPT_VERSION = "rag_prompt_v1"
```

- Defines `RAG_PROMPT` with strict grounding instructions:
  - Answer only from the provided context.
  - Say "I don't know" when the context is insufficient.
  - Cite the source document and page number for each claim.

Chain behavior:

- Provides:

```python
answer_question(query, chat_history, document_ids=None)
```

- Normalizes the query for cache keys and retrieval.
- Retrieves the top 5 chunks through the Module 8 retriever.
- Drops chunks below the minimum similarity threshold:

```python
MIN_SIMILARITY_SCORE = 0.25
```

- Returns "I don't know" without calling Gemini when no retrieved chunks pass the threshold.
- Builds the grounded prompt with source-labeled context blocks.
- Includes recent chat history only to help resolve references in the current question, not as evidence.
- Calls the shared Gemini `llm` from `backend/app/core/llm.py`.

Retry behavior:

- Wraps Gemini calls with `tenacity`.
- Retries only likely quota/rate-limit failures containing:
  - `429`
  - `RESOURCE_EXHAUSTED`
- Uses exponential backoff with up to 4 attempts.

Cache behavior:

- Uses a simple in-memory LRU-style cache.
- Cache key:

```text
(normalized_query, sorted_document_ids)
```

- Current cache TTL:

```text
10 minutes
```

- Current maximum size:

```text
128 answers
```

Implemented endpoint:

```http
POST /api/chat
```

Request shape:

```json
{
  "question": "What does the policy say about approvals?",
  "chat_history": [],
  "document_ids": null
}
```

Response shape:

```json
{
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

Verified:

- `backend/app/rag/prompts.py`, `backend/app/rag/chain.py`, and `backend/app/api/chat.py` compile successfully.
- Module 9 imports load successfully.
- OpenAPI generation includes the `POST /api/chat` request schema.
- A FastAPI `TestClient` smoke test confirmed the RAG chain could be reached through `POST /api/chat` while using a mocked LLM to avoid spending Gemini quota.

## Module 10: Source Citation Layer

Source citations and backend chat logging are implemented.

Implemented files:

- `backend/app/models/chat_log.py`
- `backend/app/core/database.py`
- `backend/app/rag/chain.py`
- `backend/app/api/chat.py`

Citation behavior:

- Chat responses expose the frontend-ready citation shape, with `session_id` added by Module 11 for conversational memory:

```json
{
  "session_id": "session-123",
  "answer": "Grounded answer...",
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

- Sources are generated from the chunks that passed the similarity threshold and were used in the prompt.
- Sources are de-duplicated by `(filename, page_number)` so one page is not repeated when multiple chunks from that page are retrieved.
- When duplicate chunks from the same page exist, the highest-scoring chunk is kept as the visible exact chunk citation.

Chat logging behavior:

- Added a SQLite-backed `chat_logs` table.
- Every chat request logs:
  - `query`
  - `sources_json`
  - `answer`
  - `created_at`
- This table is ready to double as chat history storage in a later module.
- `init_db()` imports the chat log model so the table is created during FastAPI startup.

Verified:

- `backend/app/models/chat_log.py`, `backend/app/core/database.py`, `backend/app/rag/chain.py`, and `backend/app/api/chat.py` compile successfully.
- Module 10 imports load successfully and `init_db()` creates the `chat_logs` table.
- A mocked FastAPI `TestClient` smoke test for `POST /api/chat` returned `answer`, `sources`, and the session ID used for conversational memory.
- The mocked smoke test confirmed a new `chat_logs` row was inserted.

## Module 11: Conversational Memory

Session-scoped conversational memory is implemented.

Implemented files:

- `backend/app/models/chat_log.py`
- `backend/app/core/database.py`
- `backend/app/rag/chain.py`
- `backend/app/api/chat.py`

Memory behavior:

- Chat requests now accept an optional `session_id`.
- If no `session_id` is provided, the backend creates a UUID session and returns it in the response.
- Each chat turn is stored under its session in SQLite.
- The chain loads the last 6 turns for the session before answering.
- Recent session history is prepended to the prompt before the retrieved document context.
- History is used only to resolve references; answers are still grounded only in retrieved document chunks.

Follow-up rewrite behavior:

- Before embedding/retrieval, contextual follow-up questions are rewritten into standalone search queries using Gemini.
- The rewrite prompt uses recent session history and asks Gemini to return only the standalone retrieval query.
- If no session history exists, the original question is embedded directly.
- Answer cache keys now include session and history context so follow-up answers are not reused across unrelated conversations.

Implemented endpoints:

```http
GET /api/chat/{session_id}/history
DELETE /api/chat/{session_id}
```

History response shape:

```json
{
  "session_id": "session-123",
  "history": [
    {
      "id": 1,
      "query": "What are the required features?",
      "answer": "Grounded answer...",
      "sources": [],
      "created_at": "2026-07-19T12:00:00Z"
    }
  ]
}
```

Clear response shape:

```json
{
  "session_id": "session-123",
  "deleted_turns": 2
}
```

Schema migration note:

- `init_db()` includes a lightweight SQLite guard that adds `chat_logs.session_id` to existing development databases if the table was created before Module 11.

Verified:

- Module 11 files compile successfully.
- `init_db()` applies the chat log session schema guard successfully.
- A mocked FastAPI `TestClient` smoke test created two turns in one session, retrieved both through `GET /api/chat/{session_id}/history`, and cleared them through `DELETE /api/chat/{session_id}`.

## Current API Surface

### Health Check

```http
GET /health
```

Returns:

```json
{
  "status": "ok"
}
```

### Upload Documents

```http
POST /api/documents/upload
```

Request type:

```text
multipart/form-data
```

Field:

```text
files
```

Type:

```text
one or more uploaded files
```

Allowed extensions:

- `.pdf`
- `.txt`
- `.md`
- `.docx`

Example response:

```json
[
  {
    "id": "5935cdd8-6924-4354-b945-f16aa1dff01a",
    "filename": "notes.md",
    "filetype": "md",
    "upload_time": "2026-07-18T19:42:20.265688",
    "num_pages": 0,
    "num_chunks": 0,
    "status": "processing"
  }
]
```

### List Documents

```http
GET /api/documents
```

Example response:

```json
[
  {
    "id": "5935cdd8-6924-4354-b945-f16aa1dff01a",
    "filename": "notes.md",
    "filetype": "md",
    "upload_time": "2026-07-18T19:42:20.265688",
    "num_pages": 1,
    "num_chunks": 3,
    "status": "ready"
  }
]
```

### Search Retrieved Chunks

```http
GET /api/search?q=your+question
```

Optional filters:

```http
GET /api/search?q=your+question&top_k=3&document_ids=doc-id-1&document_ids=doc-id-2
```

Returns ranked retrieved chunks with similarity score, source filename, page number, chunk index, and chunk text.

### Chat / RAG Answer

```http
POST /api/chat
```

Request:

```json
{
  "session_id": "optional-session-id",
  "question": "your question",
  "chat_history": [],
  "document_ids": null
}
```

Response:

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

Returns a grounded Gemini answer plus de-duplicated source citations containing filename, page number, exact chunk text, and score.

### Chat History

```http
GET /api/chat/{session_id}/history
```

Returns all stored turns for that chat session ordered oldest first.

### Clear Chat Session

```http
DELETE /api/chat/{session_id}
```

Deletes all stored turns for the session and removes the session row.

## Data Flow Implemented So Far

```text
User uploads file
  -> FastAPI validates extension
  -> UUID document ID is generated
  -> Original file is saved on disk
  -> Document row is inserted into SQLite
  -> Document status becomes processing
  -> Background task extracts text
  -> Text is cleaned
  -> Extracted pages are saved as JSON
  -> Cleaned text is split into overlapping chunks
  -> Chunks are saved as JSON with citation metadata
  -> Document status becomes embedding
  -> Chunk text is encoded locally with sentence-transformers
  -> Embeddings are saved as JSON
  -> Chunks, embeddings, and metadata are stored in ChromaDB
  -> Document row is updated with page and chunk counts
  -> Document status becomes ready
User searches by question
  -> Query text is encoded with the same local embedding model
  -> ChromaDB retrieves the nearest stored chunks
  -> API returns ranked chunks with source metadata for UI inspection
User asks a chat question
  -> Session ID is reused or created
  -> Recent turns for that session are loaded from SQLite
  -> Follow-up question is rewritten into a standalone retrieval query when history exists
  -> Rewritten query is checked against the session-aware answer cache
  -> Relevant chunks are retrieved from ChromaDB using the standalone query
  -> Low-similarity chunks are removed
  -> A versioned grounded prompt is built with conversation history before retrieved context
  -> Gemini is called with quota-aware retry/backoff
  -> Sources are de-duplicated by filename and page number
  -> Session ID, query, sources, and answer are logged to SQLite
  -> Session ID, answer, and source citations are returned
User views or clears chat history
  -> History is read from or deleted from SQLite by session ID
```

## Runtime Files

The following are runtime/generated files and are intentionally ignored by Git:

- `backend/.env`
- `backend/venv/`
- `backend/app/uploads/`
- `backend/app/vectordb/`
- `backend/app/*.db`
- `frontend/node_modules/`
- `frontend/dist/`
- `*.log`

## Current Configuration

Loaded from:

```text
backend/.env
```

Important settings:

```text
GOOGLE_API_KEY
ALLOWED_ORIGINS
CHUNK_SIZE
CHUNK_OVERLAP
EMBEDDING_MODEL
DATABASE_URL
UPLOAD_DIR
```

Current defaults in code:

```text
ALLOWED_ORIGINS = ["http://localhost:5173"]
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DATABASE_URL = sqlite:///backend/app/documents.db
UPLOAD_DIR = backend/app/uploads
```

## How to Run

### Backend

From `backend/`:

```powershell
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Gemini Smoke Test

From `backend/`:

```powershell
.\venv\Scripts\python.exe scripts\test_llm.py
```

This confirms the Gemini API key and quota are working.

### Frontend

From `frontend/`:

```powershell
npm run dev
```

Default Vite dev server:

```text
http://localhost:5173
```



## Current Completion Summary

Completed:

- Project setup
- Backend skeleton
- Health endpoint
- CORS
- Pydantic settings
- Gemini API wiring
- Shared Gemini LLM instance
- Gemini smoke test
- SQLite database setup
- Document model
- Multi-file upload endpoint
- Extension validation
- Safe disk storage
- Document listing endpoint
- Swagger file-picker fix
- PDF text extraction
- TXT text extraction
- Markdown text extraction
- DOCX text extraction
- Conservative text cleaning
- RecursiveCharacterTextSplitter chunking
- Configurable chunk size and overlap
- Chunk metadata for document ID, filename, page number, and chunk index
- Local sentence-transformer embedding generation
- Batched chunk embedding with `batch_size=32`
- Persistent ChromaDB vector storage
- Shared ChromaDB collection using `document_id` metadata separation
- Vector add, delete-by-document, and filtered query helpers
- Semantic retrieval pipeline using the shared embedding model
- `/api/search` endpoint for retrieved chunk inspection
- Versioned RAG prompt template
- Grounded Gemini RAG answer chain
- Similarity threshold filtering before LLM calls
- Gemini quota retry/backoff for 429 and `RESOURCE_EXHAUSTED`
- In-memory answer cache for repeated demo questions
- `/api/chat` endpoint for RAG answers
- Source citation response shape for chat answers
- De-duplicated source list with exact chunk text and score
- SQLite `chat_logs` table for query/source/answer history
- Session-scoped chat memory
- Follow-up query rewriting before retrieval
- Chat history and clear-session endpoints
- Background parsing task
- Document status updates
- Extracted text sidecar JSON output
- Chunk sidecar JSON output
- Embedding sidecar JSON output
