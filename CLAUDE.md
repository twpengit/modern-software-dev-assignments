# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup
```bash
conda activate cs146s
poetry install
```

### Week 2 (root-level Poetry)
```bash
poetry run uvicorn week2.app.main:app --reload   # start server
poetry run pytest week2/tests/ -v                # all tests
poetry run pytest week2/tests/test_extract.py -v # single test file
```

### Weeks 4–7 (Makefile per week)
```bash
cd week{4,5,6,7}
make run     # uvicorn backend.app.main:app --reload
make test    # pytest -q backend/tests
make format  # black + ruff --fix
make lint    # ruff check
```

### Linting (root)
```bash
poetry run black --line-length 100 .
poetry run ruff check .
```

## Architecture

### Repository layout
Each week is a self-contained assignment that progressively adds patterns. Week 2 is the minimal baseline; weeks 4–7 converge on a production-style stack.

### Week 2 — minimal FastAPI + raw SQLite
- `week2/app/db.py` — raw `sqlite3` connection helpers (no ORM)
- `week2/app/routers/` — thin endpoint handlers; HTTP exceptions raised directly
- `week2/app/services/extract.py` — LLM extraction via Anthropic SDK pointed at MiniMax (`base_url="https://api.minimaxi.com/anthropic"`, key `MINIMAX_API_KEY`)
- Frontend is static HTML served by FastAPI (`StaticFiles`)
- Tests mock `week2.app.services.extract._client` to avoid real API calls

### Weeks 4–7 — SQLAlchemy + Pydantic + dependency injection
All later weeks share this pattern:

```python
# db.py
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(bind=engine)

def get_db():
    session = SessionLocal()
    try:
        yield session; session.commit()
    except: session.rollback(); raise
    finally: session.close()

# router
@router.get("/")
def list_items(db: Session = Depends(get_db)):
    return [Schema.model_validate(i) for i in db.execute(select(Model)).scalars()]
```

- Models live in `backend/app/models.py`, Pydantic schemas in `backend/app/schemas.py`
- Week 7 adds `TimestampMixin` (`created_at`/`updated_at`), pagination, and PATCH endpoints
- Tests use `conftest.py` with a temporary in-memory SQLite DB and `app.dependency_overrides` to swap `get_db`

### LLM integration
The Anthropic SDK is used throughout with MiniMax as the backend provider:
```python
_client = anthropic.Anthropic(
    api_key=os.environ["MINIMAX_API_KEY"],
    base_url="https://api.minimaxi.com/anthropic",
)
```
Model: `MiniMax-M2.5`. Responses are expected as raw JSON arrays; the code strips markdown fences before parsing.

### Environment
`.env` at repo root is loaded by `python-dotenv`. Required keys: `MINIMAX_API_KEY`.
