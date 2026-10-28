# GitSummarize — Build Progress

## Current Status: All Bugs Fixed — Frontend Built, API Rebuilding

**Images built:**
- `gitsummarize-frontend` — built successfully (nginx + React SPA)
- `gitsummarize-api` — rebuilding with fixes (weasyprint deps, HF_HOME, correct poetry.lock)

### Phase 1–7 Complete (Design → Tests)
All production code has been written and is structurally validated:
- **Architecture**: LangGraph 9-node sequential pipeline
- **Database**: PostgreSQL (async SQLAlchemy 2.0) + Neo4j + Qdrant
- **Agents**: All 9 agents implemented with LangChain fallback chain
- **API**: FastAPI with 3 route groups (repositories, analysis, chat)
- **Frontend**: React 18 + Vite + TailwindCSS + ReactFlow + Mermaid
- **Tests**: pytest with conftest fixtures
- **Docker**: Multi-stage Dockerfile + docker-compose.yml (7 services)
- **CI/CD**: GitHub Actions workflow

---

## Bugs Found and Fixed

### TypeScript Errors (Frontend)
| File | Error | Fix |
|------|-------|-----|
| `src/types/index.ts` | `RepositoryListResponse` missing from types | Added interface |
| `src/api/client.ts` | Duplicate `RepositoryListResponse` definition | Removed local, re-exported from types |
| `src/pages/HomePage.tsx` | `repo` param implicitly `any` | Fixed by resolving type conflict upstream |

**Result**: `tsc --noEmit` → 0 errors. `npm run build` → built in 51s.

### Dockerfile Bugs
| Bug | Fix |
|-----|-----|
| `poetry install --no-dev` removed in Poetry 1.5+ | Changed to `--without dev` / `--with dev` |
| HuggingFace model downloads to `/root/.cache/` but app runs as `appuser` | Set `ENV HF_HOME=/app/.cache` before model download |
| WeasyPrint 62.x needs libpango, libcairo2, libgdk-pixbuf | Added system packages to apt-get |

### LangGraph State Reducer Bug
- All 9 agents used `{**state, ...}` which returned the full state including `errors`
- `AnalysisState.errors: Annotated[list[str], add]` applies the `add` reducer
- LangGraph does `old_errors + returned_errors` — returning full state causes duplicate accumulation
- Fix: Each agent now returns only the keys it actually modified (no `{**state, ...}`)
- `_make_safe_node` now returns `{"errors": [new_error]}` on exception only

### Celery + asyncpg Event Loop Bug
- `asyncio.run()` creates a new event loop per Celery task
- Module-level `_engine` (asyncpg pool) is bound to the FIRST event loop
- Second task would fail: "Future attached to a different loop"
- Fix: `await close_engine()` at the start of each `_run_async()` call

### Missing Alembic Migration
- `alembic/versions/` was empty — no tables would ever be created
- Fix: Created `0001_initial.py` with both `repositories` and `analyses` tables

### Docker Compose: Tables Never Created
- API service started uvicorn directly without running migrations
- Fix: Command changed to `sh -c "alembic upgrade head && uvicorn backend.main:app ..."`

---

## Services Architecture

```
localhost:3000   -> Frontend (React/Vite -> Nginx)
localhost:8000   -> FastAPI API
localhost:5555   -> Celery Flower (task monitoring)
localhost:5432   -> PostgreSQL
localhost:7474   -> Neo4j Browser
localhost:7687   -> Neo4j Bolt
localhost:6333   -> Qdrant REST
localhost:6379   -> Redis
```

## To Run

```bash
# Build and start all services
docker-compose up --build

# First startup: migrations run automatically in the api service
# Access app at http://localhost:3000
```

## Known Limitations (Not Bugs)
- `embed_texts()` blocks the event loop (sync SentenceTransformer in async context) — acceptable for v1
- Large chunk size warnings in Vite build — Mermaid.js bundle is large but functional
- npm audit: 2 vulnerabilities — indirect deps, not blocking
