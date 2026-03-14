# Week 2 – Action Item Extractor

A minimal FastAPI + SQLite application that converts free-form notes into enumerated action items using LLM-powered extraction via the MiniMax API.

## Overview

Paste notes into the web UI and extract actionable tasks with one click. Items can be saved to a SQLite database, marked as done, and reviewed later. Two extraction endpoints are available: a standard one and an LLM-powered alternative.

## Setup

**Prerequisites:** Python 3.10+, Conda environment `cs146s`, a `.env` file at the repo root.

```bash
# .env (repo root)
MINIMAX_API_KEY=your_key_here
```

```bash
conda activate cs146s
poetry install
```

## Running

```bash
# From the repo root
poetry run uvicorn week2.app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## API Endpoints

### Notes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/notes` | List all saved notes |
| `POST` | `/notes` | Create a note |
| `GET` | `/notes/{note_id}` | Get a single note |

**POST `/notes`** request body:
```json
{ "content": "Meeting notes about Q1 planning" }
```

Response `201`:
```json
{ "id": 1, "content": "Meeting notes about Q1 planning", "created_at": "2025-01-15 10:30:00" }
```

---

### Action Items

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/action-items/extract` | Extract action items via LLM |
| `POST` | `/action-items/extract-llm` | Extract action items via LLM (named alternative) |
| `GET` | `/action-items` | List all action items (filter by `?note_id=`) |
| `POST` | `/action-items/{id}/done` | Mark an item done or undone |

**POST `/action-items/extract`** (and `/extract-llm`) request body:
```json
{ "text": "- Fix login bug\n- Write tests", "save_note": true }
```

Response `200`:
```json
{
  "note_id": 1,
  "items": [
    { "id": 1, "text": "Fix login bug" },
    { "id": 2, "text": "Write tests" }
  ]
}
```

**POST `/action-items/{id}/done`** request body:
```json
{ "done": true }
```

Returns `404` if the item does not exist.

## Frontend

The UI at `/` provides:
- **Extract** — calls `/action-items/extract`
- **Extract LLM** — calls `/action-items/extract-llm`
- **List Notes** — fetches and displays all saved notes
- **Save as note** checkbox — persists the input text alongside extracted items
- Interactive checkboxes to mark items done

## Running Tests

```bash
poetry run pytest week2/tests/ -v        # all tests
poetry run pytest week2/tests/test_extract.py -v  # single file
```

All 8 tests mock the LLM client (`week2.app.services.extract._client`) to avoid real API calls. Test cases cover bullet lists, keyword-prefixed lines, numbered lists, empty input, plain narrative, markdown fence stripping, wrapper-object responses, and mixed formats.

## Project Structure

```
week2/
├── app/
│   ├── main.py              # FastAPI app, lifespan (init_db), routers, static files
│   ├── db.py                # Raw sqlite3 helpers — init, insert, list, update
│   ├── schemas.py           # Pydantic request/response models
│   ├── routers/
│   │   ├── notes.py         # /notes endpoints
│   │   └── action_items.py  # /action-items endpoints
│   └── services/
│       └── extract.py       # LLM extraction via Anthropic SDK (MiniMax backend)
├── frontend/
│   └── index.html           # Vanilla HTML/JS UI
├── tests/
│   └── test_extract.py      # Unit tests with mocked LLM
└── data/
    └── app.db               # SQLite database (auto-created on startup)
```

## Key Design Decisions

- **Raw SQLite3 (no ORM):** Keeps the baseline minimal; later weeks introduce SQLAlchemy.
- **Pydantic schemas:** All request/response bodies are typed models; validation (e.g. blank text rejection) lives in `schemas.py`.
- **Lifespan for startup:** `init_db()` runs inside a FastAPI `asynccontextmanager` lifespan rather than at module import time.
- **LLM JSON robustness:** The extraction layer handles plain arrays, markdown-fenced responses, and wrapper objects like `{"items": [...]}`.
- **No frontend build step:** Static HTML served directly by FastAPI; no framework or bundler required.
