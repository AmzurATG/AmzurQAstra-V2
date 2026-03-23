# AmzurQAstra-V2

AI-Powered QA Automation Platform that leverages Playwright MCP (Model Context Protocol) to generate, manage, and execute functional tests using AI.

## Features

- **AI Test Generation**: Automatically generate test cases from requirement documents (PDF, Word, Markdown)
- **Playwright Integration**: Execute tests using Playwright through MCP server
- **Multi-Browser Support**: Test on Chromium, Firefox, and WebKit
- **Build Integrity Check**: Verify application readiness before testing
- **Flexible Document Storage**: Local filesystem, AWS S3, or Supabase storage
- **Integrations**: Jira, Azure DevOps, Redmine for requirements import
- **LLM Support**: OpenAI, Anthropic Claude, and LiteLLM proxy

## Architecture

```
AmzurQAstra-V2/
├── backend/          # FastAPI backend (Python)
├── frontend/         # React frontend (TypeScript)
├── mcp-server/       # Playwright MCP server (Node.js)
├── storage/          # Document storage (outside backend)
├── logs/             # Application logs
└── docker-compose.yml
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)

### Local Development Setup

You'll need **3 terminal windows** to run all services:

#### Terminal 1: Backend (Port 8000)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2: MCP Server (Port 3001)

```powershell
cd mcp-server
npm install
npx playwright install
npm run dev
```

#### Terminal 3: Frontend (Port 5173)

```powershell
cd frontend
npm install
npm run dev
```

### Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| MCP Server | http://localhost:3001 |

### Environment Setup

1. Copy environment file:
   ```powershell
   copy backend\.env.example backend\.env
   ```

2. Edit `backend/.env` with your configuration:
   - Database connection
   - LLM API keys (OpenAI/Anthropic/LiteLLM)
   - Storage configuration
   - Integration credentials (optional)

### Database Setup

```powershell
# Create database
psql -U postgres -c "CREATE DATABASE qastra;"

# Run migrations (from backend folder)
cd backend
alembic upgrade head
```

## Document Storage

QAstra supports flexible document storage backends:

| Type | Description | Config |
|------|-------------|--------|
| `local` | Local filesystem (default) | `STORAGE_LOCAL_PATH=../storage` |
| `s3` | AWS S3 or S3-compatible | `STORAGE_S3_BUCKET`, `STORAGE_S3_REGION` |
| `supabase` | Supabase Storage | `STORAGE_SUPABASE_URL`, `STORAGE_SUPABASE_BUCKET` |

Set `STORAGE_TYPE` in your `.env` file to switch between backends.

## Workflow

1. **Upload Requirements**: Upload PDF/Word documents or import from Jira/Azure DevOps
2. **Generate Test Cases**: AI analyzes requirements and generates test cases
3. **Review & Edit**: Refine test steps and add assertions
4. **Run Integrity Check**: Verify the target application is testable
5. **Execute Tests**: Run tests via Playwright MCP and view results

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL |
| Frontend | React, TypeScript, Tailwind CSS, Zustand |
| MCP Server | Node.js, TypeScript, Playwright |
| AI | OpenAI GPT-4, Anthropic Claude, LiteLLM |

## Default Credentials

```
Email: admin@qastra.dev
Password: admin123
```

## License

MIT License - see LICENSE file for details.
