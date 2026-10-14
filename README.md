# StudyQuiz AI

A RAG-based study platform: students upload study material (PDF / PPTX), get
auto-generated quizzes, and receive AI-evaluated answers with detailed
feedback.

---

## Features

- **Upload & ingest** PDF/PPTX (including PPTX speaker notes); text is parsed,
  chunked, embedded, and stored in a persistent ChromaDB vector store. Every
  chunk keeps its file name + page/slide number as metadata.
- **Quiz generation** from a chosen document:
  - Question types: MCQ, short answer, long answer (pick one or mix)
  - Difficulty: easy / medium / hard (recall → understanding → analysis)
  - 1–20 questions, optional topic/keyword focus
  - Questions are grounded in retrieved source chunks — never invented facts
- **Taking a quiz** with per-question input (MCQ options or free text).
- **AI evaluation** (the differentiator):
  - MCQ: deterministic check against the correct option + LLM-written explanation
  - Short/long answer: LLM-as-judge with rubric (reference answer + key points
    stored at generation time) and source chunks → score 0–10, covered/missed
    points, specific improvement suggestions, and the model answer
- **Two LLM modes**, switchable from the UI (default via `DEFAULT_LLM_MODE`):
  - `local` — Ollama (default generation model `qwen2.5:7b-instruct`)
  - `gemini` — Google Gemini API (model from `GEMINI_MODEL`)
  - Embedding provider is independent from generation mode (Ollama
    `nomic-embed-text`) so switching never requires re-indexing.
- **Results & history**: per-question feedback cards, total score, attempt
  history, source page/slide references.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend  React + Vite + TypeScript + Tailwind + TanStack Query          │
│  Pages: Upload/Documents · Create Quiz · Take Quiz · Results · History   │
│  Header: Local/Gemini mode toggle + health indicator                     │
└───────────────▲───────────────────────────────────────┬──────────────────┘
                │ HTTP (JSON)                            │
┌───────────────┴───────────────────────────────────────▼──────────────────┐
│ Backend  FastAPI (Python 3.11+)                        Pydantic v2         │
│                                                                           │
│  api/      documents · quizzes · attempts · health                        │
│  services/ quiz_generator · evaluator · health_service                    │
│  rag/      parsers · chunking · embeddings · vectorstore · retriever      │
│  llm/      base (LLMProvider) · ollama_provider · gemini_provider ·       │
│            factory (mode switch)                                          │
│  prompts/  quiz generation & evaluation templates (files, not inline)    │
│  models/   SQLAlchemy ORM · schemas/ Pydantic DTOs                        │
│                                                                           │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐               │
│  │ SQLite        │   │ ChromaDB      │   │ Ollama        │               │
│  │ (documents,   │   │ (persistent   │   │ nomic-embed   │               │
│  │  quizzes,     │   │  vector store)│   │ + qwen2.5     │               │
│  │  attempts)    │   │               │   │ and/or Gemini │               │
│  └───────────────┘   └───────────────┘   └───────────────┘               │
└──────────────────────────────────────────────────────────────────────────┘
```

No LangChain — the RAG pipeline is a small, readable, plain-Python stack:
parsers → chunkers → embedder (Ollama HTTP API) → ChromaDB → retriever →
LLM services with Pydantic-validated structured output.

---

## Repository layout

```
StudyQuiz-AI/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + CORS + routers
│   │   ├── config.py          # pydantic-settings (reads backend/.env)
│   │   ├── db.py              # SQLAlchemy engine/session
│   │   ├── api/               # documents, quizzes, attempts, health
│   │   ├── llm/               # provider abstraction (local + gemini)
│   │   ├── rag/               # parsers, chunking, embeddings, vectorstore, retriever
│   │   ├── services/          # quiz_generator, evaluator, health_service
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── prompts/           # prompt templates as separate files/constants
│   ├── tests/                 # pytest suite
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/                  # React + Vite + TS app
│   ├── src/
│   │   ├── api/               # typed fetch client + shared types
│   │   ├── components/        # Layout, ModeToggle, HealthIndicator, badges
│   │   ├── hooks/             # useHealth polling
│   │   ├── pages/             # Documents, CreateQuiz, TakeQuiz, Results, History
│   │   ├── state/             # ModeContext (localStorage LLM mode)
│   │   └── utils/             # formatting helpers
│   ├── vite.config.ts         # dev server + /api proxy to the backend
│   └── package.json
└── README.md
```

---

## Prerequisites

- Python 3.11+ (tested on 3.12)
- Node.js 18+ (tested on 22)
- [Ollama](https://ollama.com/) running locally (`ollama serve`)

---

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements-dev.txt

# Pull the models Ollama needs (defaults):
ollama pull qwen2.5:7b-instruct   # generation (local mode)
ollama pull nomic-embed-text      # embeddings

# Optional — use Gemini (cloud) mode:
cp .env.example .env
# then edit backend/.env and set GEMINI_API_KEY=...
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

The dev server proxies `/api` to `http://127.0.0.1:8000` (override with the
`VITE_API_PROXY` env var). For a production build, `npm run build` emits
`frontend/dist`; point `VITE_API_BASE_URL` at the backend if it is served from a
different origin than the static files.

---

## Running

**Backend**

```bash
cd backend
.venv\Scripts\activate          # or: source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger UI): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/health>

**Frontend**

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>.

---

## Testing

```bash
cd backend
.venv\Scripts\activate
pytest
```

The suite covers: chunking, parsers, the Chroma vector store, structured-JSON
retry with a fake provider, deterministic MCQ grading, quiz generation,
LLM-as-judge evaluation, API smoke tests (documents, quizzes, attempts, health),
and DB schema sync. All LLM calls in tests use fake providers — no Ollama or
network access is required to run `pytest`.

**Frontend checks**

```bash
cd frontend
npm run typecheck   # tsc --noEmit
npm run build       # typecheck + production bundle
```

---

## API overview

| Method | Endpoint                          | Description                                   |
| ------ | --------------------------------- | --------------------------------------------- |
| POST   | `/api/documents`                  | Upload PDF/PPTX (background ingestion)        |
| GET    | `/api/documents`                  | List documents + processing status            |
| GET    | `/api/documents/{id}`             | Document detail                               |
| DELETE | `/api/documents/{id}`             | Remove a document (+ its chunks)              |
| POST   | `/api/quizzes/generate`           | Generate a quiz from a document               |
| GET    | `/api/quizzes/{id}`               | Fetch a quiz with its questions               |
| POST   | `/api/attempts`                   | Submit answers → per-question evaluation      |
| GET    | `/api/attempts?quiz_id=...`       | Attempt history for a quiz                    |
| GET    | `/api/attempts/{id}`              | Full attempt result                           |
| GET    | `/api/health`                     | DB + Ollama + Gemini availability             |

---

## Configuration (`backend/.env`)

| Variable              | Default               | Description                              |
| --------------------- | --------------------- | ---------------------------------------- |
| `DEFAULT_LLM_MODE`    | `local`               | `local` or `gemini`                      |
| `OLLAMA_BASE_URL`     | `http://localhost:11434` | Ollama server                            |
| `OLLAMA_MODEL`        | `qwen2.5:7b-instruct` | Local generation model                   |
| `OLLAMA_EMBED_MODEL`  | `nomic-embed-text`    | Embedding model                          |
| `GEMINI_API_KEY`      | *(empty)*             | Google API key (leave empty to disable)  |
| `GEMINI_MODEL`        | `gemini-2.0-flash`    | Gemini generation model                  |
| `CHROMA_DIR`          | `./data/chroma`       | Persistent vector store path             |
| `DATABASE_URL`        | `sqlite:///./data/studyquiz.db` | SQL database (Postgres-compatible) |
| `MAX_UPLOAD_MB`       | `50`                  | Upload size limit                        |
| `LLM_TIMEOUT_SECONDS` | `180`                 | Per-call LLM timeout (raise on slow CPUs) |
| `LLM_MAX_JSON_ATTEMPTS` | `3`                 | Structured-JSON retry budget             |
| `CORS_ORIGINS`        | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `API_PREFIX`          | `/api`                | Route prefix for all API endpoints       |

---

## Project status

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 | Backend skeleton, config, DB models, health endpoint, LLM provider abstraction + tests | ✅ Done |
| 2 | Document ingestion: parsing, chunking, embeddings, Chroma storage, upload endpoints | ✅ Done |
| 3 | Quiz generation service + endpoints | ✅ Done |
| 4 | Evaluation service + attempts endpoints | ✅ Done |
| 5 | React frontend, all pages, mode toggle | ✅ Done |
| 6 | Polish: error handling, README, tests, end-to-end check | ✅ Done |

---

## Phase notes

### Phase 1 — skeleton, LLM abstraction, health

What is implemented and verified:

- `backend/app/config.py` — typed settings via pydantic-settings; reads `backend/.env`
  (falls back to repo-root `.env`); nothing hard-coded.
- `backend/app/models/entities.py` — SQLAlchemy 2.0 tables for `documents`,
  `quizzes`, `questions`, `attempts`, `attempt_answers` (created on startup).
- `backend/app/llm/` — provider abstraction:
  - `LLMProvider` base class with `generate()` and retrying
    `generate_json(schema)` (up to 3 attempts, feeds validation errors back,
    raises `LLMStructuredOutputError` on failure).
  - `ollama_provider.py` — Ollama `/api/chat` with the `format` JSON-schema
    parameter for structured output.
  - `gemini_provider.py` — google-genai SDK with JSON-schema response mode and
    graceful fallback to constrained JSON when a schema cannot be converted.
  - `factory.py` — `get_provider(mode)` with `local`/`gemini` validation and
    provider caching; unknown modes raise a clear configuration error.
  - Typed error hierarchy (`LLMConnectionError`, `LLMTimeoutError`,
    `LLMAuthError`, `LLMRateLimitError`, `LLMModelNotFoundError`, ...) where
    every error carries a `user_message` for the UI.
- `GET /api/health` — reports DB, Ollama, Gemini, and embedding availability
  (models list + whether the configured default model is pulled). Never 500s.
- `backend/app/services/mcq.py` — deterministic MCQ grading (used by the
  evaluator in Phase 4).

**Run it**

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000/api/health and http://127.0.0.1:8000/docs
```

**Test it**

```bash
cd backend
.venv\Scripts\activate
pytest            # full suite; see the Testing section above
```

Example health output:

```json
{
  "status": "ok",
  "database": { "ok": true },
  "llm": {
    "local":  { "available": true, "default_model_available": false,
                "error": "Model 'qwen2.5:7b-instruct' is not pulled..." },
    "gemini": { "available": false, "error": "GEMINI_API_KEY is not set..." }
  },
  "embeddings": { "mode": "ollama-embed", "available": true, ... }
}
```

### Phase 2 — document ingestion

- `backend/app/rag/parsers.py` — PyMuPDF for PDFs (per-page text) and
  python-pptx for slides, **including speaker notes**; each page/slide keeps its
  1-based number.
- `backend/app/rag/chunking.py` — overlapping word-window chunking with
  page-aware metadata and stable `chunk_id`s.
- `backend/app/rag/embeddings.py` — Ollama `/api/embeddings` client
  (`nomic-embed-text` by default) with batch embedding and clear errors.
- `backend/app/rag/vectorstore.py` — persistent ChromaDB wrapper: upsert,
  query, list, count, and delete-collection (idempotent — tolerates a missing
  collection).
- `backend/app/services/document_processor.py` — background pipeline:
  parse → chunk → embed → store, updating `documents.status`
  (`processing` → `ready`/`failed`) and `num_chunks`.
- `backend/app/api/documents.py` — upload (validated extension + size),
  list/detail, and delete (removes chunks and the stored file).
- Ingestion runs as a FastAPI `BackgroundTask`; the client polls document
  status.

### Phase 3 — quiz generation

- `backend/app/prompts/quiz_generation.py` — system prompt + JSON-schema-shaped
  user prompt; prompts live in files/constants, never inline in services.
- `backend/app/services/quiz_generator.py` — embeds the topic, retrieves the
  most relevant chunks, and asks the provider for structured questions
  (`generate_json`). Questions are grounded in the retrieved context only, and
  the source `chunk_id`s + page numbers are stored with each question.
- Question types: `mcq` (4 options + correct index + explanation),
  `short_answer` / `long_answer` (reference answer + key points).
- `backend/app/api/quizzes.py` — `POST /api/quizzes/generate` returns `202`
  immediately and generates in the background; `GET /api/quizzes/{id}` and
  `GET /api/quizzes` expose questions **without** the answers.
- Regeneration/retry safety: generation retries JSON via the provider
  abstraction and records `failed` + `error_message` on hard errors.

### Phase 4 — evaluation

- `backend/app/prompts/evaluation.py` — LLM-as-judge prompt with an explicit
  rubric (reference answer, key points, source chunks) and a prompt-injection
  guard that fences the untrusted student answer between
  `<<<STUDENT_ANSWER>>>` / `<<<END_STUDENT_ANSWER>>>` markers.
- MCQ answers are graded **deterministically** (`app/services/mcq.py`) reusing
  the stored explanation as feedback — no LLM call.
- Short/long answers are judged by the LLM → score 0–10, covered/missed points,
  feedback, and the model answer. Blank answers score 0 without an LLM call.
- Verdicts: `correct` (≥ 8), `partial` (≥ 5), `incorrect` (< 5), `blank`.
  Each question is worth up to 10 points (attempt max = 10 × questions).
- `backend/app/api/attempts.py` — `POST /api/attempts` grades synchronously and
  returns full per-question feedback; `GET /api/attempts` (history) and
  `GET /api/attempts/{id}` expose results. Correct answers are revealed only
  through attempt feedback, never in the quiz itself.

### Schema upgrades without Alembic

This project intentionally ships without a migration tool. On startup
`init_db()` creates missing tables and then runs an **add-only** column sync for
SQLite (`app/db.py`), so a database created by an earlier phase keeps working
after new nullable columns are introduced. Data is never dropped or rewritten.

**Verify Phases 2–4 end to end** (needs Ollama + the models):

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --port 8000
# in another shell, upload a PDF, generate a quiz, submit an attempt via /docs
```

Expected flow: document goes `processing` → `ready`; the quiz goes
`generating` → `ready`; `POST /api/attempts` returns a score plus per-question
feedback (MCQ verdicts are exact; short/long include covered/missed points and a
model answer).

### Phase 5 — React frontend

Vite + React 18 + TypeScript (strict), React Router, plain CSS, no UI kit. The
dev server proxies `/api` so the browser sees a single origin.

- **Documents** (`/`) — upload PDF/PPTX, live status polling while ingesting,
  delete, and a shortcut to create a quiz from a ready document.
- **Create Quiz** (`/create`) — pick a processed document, 1–20 questions,
  question types, difficulty, optional topic focus; `?document_id=` preselects;
  shows existing quizzes for the document.
- **Take Quiz** (`/quizzes/:id`) — polls while the quiz is `generating`, then
  renders MCQ radios / free-text areas; submitting evaluates and routes to the
  result.
- **Results** — score hero + progress bar, per-question cards with verdict
  colours, the correct MCQ option highlighted, covered/missed points, feedback,
  a collapsible model answer, and source page tags.
- **History** — all attempts with score/percentage and links to full results.
- **Mode toggle** — Local ↔ Gemini in the top bar, persisted in
  `localStorage` (`studyquiz.llmMode`) and sent with generation/submission
  requests. Gemini shows a warning marker when `GEMINI_API_KEY` is unset.
- **Health indicator** — polls `/api/health` and surfaces database, Ollama,
  Gemini, and embedding availability.

`src/api/client.ts` is a small typed `fetch` wrapper (`ApiError` carries the
backend's `detail` message, so failures render as readable banners).

### Phase 6 — polish & end-to-end verification

- Backend and frontend error states are user-facing (no raw stack traces in the
  UI); background jobs report `failed` + `error_message` and the UI shows it.
- Two real bugs found and fixed during end-to-end testing:
  - Ollama health reported `nomic-embed-text` as missing because Ollama lists it
    as `nomic-embed-text:latest`; model matching now normalizes the implicit
    `:latest` tag.
  - A database created before Phase 4 lacked the new
    `attempt_answers.selected_option` column; `init_db()` now performs an
    add-only SQLite column sync (see "Schema upgrades without Alembic").
- **End-to-end check (real Ollama, CPU-only):** uploaded a PDF → `ready` (2
  chunks) → generated a 3-question mixed quiz → `ready` → submitted an attempt →
  received per-question verdicts, covered/missed points, feedback, and a model
  answer, all persisted and visible in History and the Results page.
- Automated tests: `pytest` (backend, fake LLMs only) plus
  `npm run typecheck` and `npm run build` (frontend).