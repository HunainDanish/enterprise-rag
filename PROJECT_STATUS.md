# Enterprise Document Intelligence Platform - Project Status

Last updated: July 19, 2026

## Project Overview

This project is an Enterprise Document Intelligence Platform built as a full-stack RAG application. The goal is to let users upload business documents, extract and clean their text, index the content into a vector database, and later ask questions over those documents using Gemini through LangChain.

The project currently has a working FastAPI backend foundation, Gemini API wiring, SQLite-backed document tracking, multi-format upload support, document text extraction for PDF, TXT, Markdown, and DOCX files, and configurable retrieval chunking.

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
- Extracted text and retrieval chunks are currently stored as JSON sidecar files beside uploaded documents.
- Vector storage is planned under `backend/app/vectordb/`.

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
        document.py
      rag/
        cleaning.py
        chunking.py
        loaders.py
        processing.py
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

Current status values used:

- `pending`
- `processing`
- `embedding`
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
8. Update `num_pages` and `num_chunks`.
9. Mark status as `embedding`.
10. If anything fails, mark status as `failed`.

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
6. Updates `num_pages`.
7. Updates `num_chunks`.
8. Sets document status to `embedding`.

Verified:

- `backend/app/rag/chunking.py`, `backend/app/rag/processing.py`, and `backend/app/core/config.py` compile successfully.
- The backend virtual environment imports `RecursiveCharacterTextSplitter` and `app.rag.chunking.chunk_pages` successfully.

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
    "status": "embedding"
  }
]
```

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
  -> Document row is updated with page and chunk counts
  -> Document status becomes embedding
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
- Background parsing task
- Document status updates
- Extracted text sidecar JSON output
- Chunk sidecar JSON output
