# AmzurQAstra-V2

AI-powered QA automation platform: generate and manage functional tests from requirements, run test workflows, and verify target apps with a **Build Integrity Check** powered by **browser-use**, **Playwright**, and **Google Gemini**.

## Features

- **AI test generation**: Create test cases from requirement documents (PDF, Word, Markdown)
- **Build Integrity Check**: Async browser run (headed Chrome) against your app URL — optional email/password or **Google Sign-In** mode, live progress, screenshots, and persisted results (Gemini-driven agent)
- **Flexible document storage**: Local filesystem, AWS S3, or Supabase
- **Integrations**: Jira, Azure DevOps, Redmine (where configured)
- **LLM support**: OpenAI, Anthropic, LiteLLM proxy, and **Gemini** for the integrity agent

## Architecture

```
AmzurQAstra-V2/
├── backend/          # FastAPI (Python), Alembic, integrity agent (browser-use)
├── frontend/         # React + Vite + TypeScript
├── storage/          # Document storage (outside backend; optional)
└── logs/             # Application logs (outside backend)
```

## Quick start

### Prerequisites

- **Node.js** 18+
- **Python** 3.11+ (3.12 recommended)
- **PostgreSQL** 15+
- **Redis** (optional; used if configured)

### Local development (two terminals)

Use a virtual environment and install Python dependencies from `backend/requirements.txt` (e.g. `uv pip install -r requirements.txt` with your tool of choice).

#### Terminal 1 — Backend (port 8000)

```powershell
cd backend
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1    # PowerShell
# or: venv\Scripts\activate.bat   # CMD

uv pip install -r requirements.txt
uv run playwright install chromium
alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 — Frontend (port 5173)

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` and `/screenshots` to the backend so API calls and integrity-check screenshots load correctly.

### URLs

| Service | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

### Environment

1. Copy the example env file if present:

   ```powershell
   copy backend\.env.example backend\.env
   ```

2. Edit `backend/.env` at minimum:

   | Variable | Purpose |
   |----------|---------|
   | `DATABASE_URL` | PostgreSQL connection string |
   | `GEMINI_API_KEY` | **Required for Build Integrity Check** (Gemini via browser-use) |
   | `SECRET_KEY` / JWT | Auth |
   | OpenAI / Anthropic / LiteLLM | Other AI features, as needed |
   | `BROWSER_USE_DEFAULT_EXTENSIONS` | Optional (`true`/`false`); default extensions download to the user profile — disable on low disk space |

3. Frontend (optional): set `VITE_API_URL` in `frontend/.env` (e.g. `http://localhost:8000/api/v1`) so screenshot URLs resolve to the API origin in production-like setups.

### Database

```powershell
# First-time DB creation (if you use the repo script)
cd database
python database_setup_local.py

cd ..\backend
alembic upgrade head
```

Integrity Check results are stored after migration **`0002`** (table `integrity_check_results`).

### Build Integrity Check — notes

- **Manual login**: Email/password are passed to the agent via browser-use **`sensitive_data`** placeholders; do not commit real secrets in code.
- **Google Sign-In**: Use the UI toggle; the agent follows OAuth in the opened browser (MFA may require a human).
- **Windows**: The backend runs the agent on a dedicated asyncio loop so Chrome can launch (`asyncio` subprocess support).
- **Screenshots** are written under the configured screenshots directory and served at `/screenshots/...`. Do not commit generated PNGs (keep `backend/screenshots/` out of version control).

## Document storage

| Type | Config |
|------|--------|
| `local` (default) | `STORAGE_LOCAL_PATH` |
| `s3` | `STORAGE_S3_*` |
| `supabase` | `STORAGE_SUPABASE_*` |

Set `STORAGE_TYPE` in `backend/.env`.

## Workflow

1. Upload requirements or import from integrations  
2. Generate and refine test cases  
3. **Build Integrity Check**: open *Functional Testing → Integrity Check*, set URL and credentials or Google Sign-In, run and poll until complete  
4. Execute functional test runs as configured in the product  

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Backend | Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Integrity agent | browser-use, Playwright (Chromium), Google Gemini |
| Other AI | OpenAI, Anthropic, LiteLLM (features as configured) |

## License

MIT License — see LICENSE if present.
