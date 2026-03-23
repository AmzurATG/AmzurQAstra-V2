# QAstra Architecture

This document describes the technical architecture of QAstra, including all components, services, and their interactions.

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                  USER                                           │
│                          (QA Team / Tester)                                     │
└───────────────────────────────────┬────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                                      │
│         Dashboard • Test Cases • Test Runs • Integrations                       │
└───────────────────────────────────┬────────────────────────────────────────────┘
                                    │ REST API
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                     │
└───────────────────────────────────┬────────────────────────────────────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
         ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
         │   MCP       │    │  Playwright │    │   Target    │
         │   Server    │    │   Worker    │    │   App       │
         └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Component Details

### 1. Frontend (React)

**Technology Stack:**
- React 18 with TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Zustand (state management)
- React Query (data fetching)
- React Router (navigation)

**Port:** `5173` (development)

**Key Pages:**

| Page | Path | Description |
|------|------|-------------|
| Login | `/login` | User authentication |
| Dashboard | `/` | Overview and statistics |
| Projects | `/projects` | Project management |
| Functional Dashboard | `/functional` | Functional testing home |
| Requirements | `/functional/requirements` | Upload/manage requirements |
| Test Cases | `/functional/test-cases` | View/edit test cases |
| Test Runs | `/functional/test-runs` | Execute and monitor tests |
| Integrity Check | `/functional/integrity-check` | Build verification |
| Settings | `/settings` | User preferences |
| Integrations | `/integrations` | Jira/Azure/Slack setup |

**Directory Structure:**
```
frontend/
├── src/
│   ├── common/              # Shared across all features
│   │   ├── api/             # API clients (axios)
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Common pages (Login, Dashboard)
│   │   ├── store/           # Zustand stores
│   │   └── types/           # TypeScript interfaces
│   └── features/
│       └── functional/      # Functional testing feature
│           ├── api/         # Feature-specific API
│           ├── pages/       # Feature pages
│           └── types/       # Feature types
```

---

### 2. Backend (FastAPI)

**Technology Stack:**
- Python 3.11+
- FastAPI (web framework)
- SQLAlchemy (ORM)
- Pydantic (validation)
- PostgreSQL (database)
- Alembic (migrations)

**Port:** `8000`

**Architecture:**

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                    │
│                                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │   Auth      │  │  Projects   │  │ Test Cases  │  │  Test Execution      │   │
│  │   Service   │  │  Service    │  │  Service    │  │  Service             │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┬───────────┘   │
│                                                                 │              │
│  ┌─────────────────────────────────────────────────────────────┼─────────────┐ │
│  │                         LLM ENGINE                           │            │ │
│  │  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐│             │ │
│  │  │ OpenAI/Claude │    │ Test Case Gen │    │ Test Step Gen ││             │ │
│  │  │ Client        │    │ Prompts       │    │ Prompts       ││             │ │
│  │  └───────────────┘    └───────────────┘    └───────────────┘│             │ │
│  └─────────────────────────────────────────────────────────────┴─────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Services:**

| Service | Responsibility |
|---------|----------------|
| **AuthService** | User authentication, JWT tokens, password hashing |
| **ProjectService** | Project CRUD, user permissions |
| **RequirementService** | Document upload, parsing, storage |
| **TestCaseService** | Test case CRUD, filtering |
| **TestGenerationService** | LLM-based test case generation |
| **TestExecutionService** | Orchestrate test runs via MCP |
| **IntegrityCheckService** | Build verification workflows |
| **FileService** | File upload, storage, retrieval |
| **NotificationService** | Slack/email notifications |

**LLM Engine:**

| Component | Purpose |
|-----------|---------|
| **OpenAI Client** | GPT-4/GPT-3.5 API integration |
| **Anthropic Client** | Claude API integration |
| **Test Case Prompts** | Generate test cases from requirements |
| **Test Step Prompts** | Generate executable steps from test cases |

**API Endpoints:**

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Login, register, refresh token |
| Users | `/api/v1/users` | User management |
| Projects | `/api/v1/projects` | Project CRUD |
| Integrations | `/api/v1/integrations` | Jira, Azure, Slack |
| Requirements | `/api/v1/functional/requirements` | Requirement docs |
| Test Cases | `/api/v1/functional/test-cases` | Test case management |
| Test Runs | `/api/v1/functional/test-runs` | Test execution |
| Integrity | `/api/v1/functional/integrity-check` | Build checks |

**Directory Structure:**
```
backend/
├── config.py                # Settings from environment
├── main.py                  # FastAPI application
├── common/
│   ├── db/models/           # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── llm/                 # LLM clients & prompts
│   ├── integrations/        # Jira, Azure, Slack
│   └── utils/               # Security, logging, exceptions
├── api/v1/
│   ├── common/              # Auth, users, projects routes
│   └── functional/          # Feature-specific routes
└── features/functional/
    ├── db/models/           # Requirement, TestCase, TestRun
    ├── schemas/             # Feature Pydantic schemas
    ├── services/            # Feature business logic
    └── core/                # Document parsers, MCP client
```

---

### 3. MCP Server (Playwright)

**Technology Stack:**
- Node.js 18+
- TypeScript
- Express.js (HTTP API)
- Playwright (browser automation)
- Winston (logging)

**Port:** `3001`

**Architecture:**

```
┌─────────────────────────────────────┐
│         MCP SERVER                  │
│      (Playwright MCP)               │
│                                     │
│  ┌───────────────────────────────┐  │
│  │     MCP Protocol Handler      │  │
│  │  (JSON-RPC over stdio/HTTP)   │  │
│  └───────────────────────────────┘  │
│              │                      │
│              ▼                      │
│  ┌───────────────────────────────┐  │
│  │     Playwright Tools          │  │
│  │  • navigate    • click        │  │
│  │  • fill        • screenshot   │  │
│  │  • assert      • evaluate     │  │
│  └───────────────────────────────┘  │
│              │                      │
│              ▼                      │
│  ┌───────────────────────────────┐  │
│  │     Browser Manager           │  │
│  │  (Chromium/Firefox/WebKit)    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/sessions` | GET | List browser sessions |
| `/mcp/sessions` | POST | Create new session |
| `/mcp/sessions/:id` | DELETE | Close session |
| `/mcp/execute` | POST | Execute single action |
| `/mcp/execute-batch` | POST | Execute multiple actions |
| `/mcp/screenshot` | POST | Capture screenshot |
| `/mcp/page-info/:sessionId` | GET | Get page information |

**Supported Actions:**

| Action | Description | Example |
|--------|-------------|---------|
| `navigate` | Go to URL | `{ action: "navigate", target: "https://app.com" }` |
| `click` | Click element | `{ action: "click", target: "#login-btn" }` |
| `fill` | Enter text | `{ action: "fill", target: "#email", value: "test@test.com" }` |
| `select` | Select option | `{ action: "select", target: "#country", value: "US" }` |
| `check` | Check checkbox | `{ action: "check", target: "#remember-me" }` |
| `hover` | Mouse hover | `{ action: "hover", target: ".menu" }` |
| `wait` | Wait time | `{ action: "wait", value: "2000" }` |
| `screenshot` | Capture image | `{ action: "screenshot" }` |
| `assertVisible` | Check visible | `{ action: "assertVisible", target: ".success" }` |
| `assertText` | Check text | `{ action: "assertText", target: "h1", value: "Welcome" }` |
| `assertUrl` | Check URL | `{ action: "assertUrl", target: "/dashboard" }` |

**Directory Structure:**
```
mcp-server/
├── src/
│   ├── index.ts             # Entry point
│   ├── server.ts            # Express setup
│   ├── core/
│   │   ├── browserManager.ts   # Session management
│   │   └── actionExecutor.ts   # Playwright actions
│   ├── routes/
│   │   ├── mcp.ts           # MCP action routes
│   │   └── sessions.ts      # Session routes
│   ├── middleware/
│   │   ├── errorHandler.ts  # Error handling
│   │   └── requestLogger.ts # Request logging
│   └── utils/
│       └── logger.ts        # Winston logger
```

---

### 4. Database (PostgreSQL)

**Core Tables:**

| Table | Description |
|-------|-------------|
| `users` | User accounts |
| `organizations` | Multi-tenant organizations |
| `projects` | Testing projects |
| `audit_logs` | Activity tracking |

**Functional Testing Tables:**

| Table | Description |
|-------|-------------|
| `requirements` | Uploaded requirement documents |
| `test_cases` | Generated/manual test cases |
| `test_steps` | Individual test steps |
| `test_runs` | Test execution records |
| `test_results` | Per-test-case results |

**Entity Relationship:**

```
Organization (1) ──── (N) User
     │
     └── (N) Project
              │
              ├── (N) Requirement ──── (N) TestCase
              │                             │
              │                             └── (N) TestStep
              │
              └── (N) TestRun ──── (N) TestResult
```

---

### 5. External Integrations

**Jira Integration:**

```
Backend ──── Jira REST API
              │
              ├── Import stories as requirements
              ├── Create/update test cases
              └── Log test results
```

**Azure DevOps Integration:**

```
Backend ──── Azure DevOps API
              │
              ├── Import work items
              ├── Sync test cases
              └── Report results
```

**Slack Integration:**

```
Backend ──── Slack Webhooks
              │
              └── Send notifications
                  ├── Test run started
                  ├── Test run completed
                  └── Failure alerts
```

---

## Data Flow

### Test Generation Flow

```
1. User uploads requirement doc
           │
           ▼
2. Backend parses document (PDF/Word/MD)
           │
           ▼
3. LLM Engine generates test cases
           │
           ▼
4. LLM Engine generates test steps
           │
           ▼
5. Store in PostgreSQL
           │
           ▼
6. Display in Frontend
```

### Test Execution Flow

```
1. User initiates test run
           │
           ▼
2. Backend fetches test cases + steps
           │
           ▼
3. Backend calls MCP Server
           │
           ▼
4. MCP Server creates browser session
           │
           ▼
5. MCP Server executes each step
           │
           ├── Capture screenshots
           ├── Record errors
           └── Track timing
           │
           ▼
6. MCP Server returns results
           │
           ▼
7. Backend stores results
           │
           ▼
8. Backend notifies Slack (if configured)
           │
           ▼
9. Backend updates Jira (if configured)
           │
           ▼
10. Frontend displays report
```

---

## Complete Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                  USER                                           │
│                          (QA Team / Tester)                                     │
└───────────────────────────────────┬────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                                      │
│         Dashboard • Test Cases • Test Runs • Integrations                       │
│                                                                                 │
│         Port: 5173 | Tech: React, TypeScript, Tailwind, Zustand                 │
└───────────────────────────────────┬────────────────────────────────────────────┘
                                    │ REST API
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                    │
│                                                                                │
│         Port: 8000 | Tech: Python, FastAPI, SQLAlchemy, Pydantic               │
│                                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │   Auth      │  │  Projects   │  │ Test Cases  │  │  Test Execution      │   │
│  │   Service   │  │  Service    │  │  Service    │  │  Service             │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┬───────────┘   │
│                                                                │               │
│  ┌─────────────────────────────────────────────────────────────┼─────────────┐ │
│  │                         LLM ENGINE                          │             │ │
│  │  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐│             │ │
│  │  │ OpenAI/Claude │    │ Test Case Gen │    │ Test Step Gen ││             │ │
│  │  │ Client        │    │ Prompts       │    │ Prompts       ││             │ │
│  │  └───────────────┘    └───────────────┘    └───────────────┘│             │ │
│  └─────────────────────────────────────────────────────────────┼─────────────┘ │
└────────────────────────────────────────────────────────────────┼───────────────┘
                                                                 │
                         ┌───────────────────────────────────────┤
                         │                                       │
                         ▼                                       ▼
┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐
│         MCP SERVER                  │    │      PLAYWRIGHT WORKER              │
│      (Playwright MCP)               │    │    (Background Execution)           │
│                                     │    │                                     │
│  Port: 3001                         │    │  For batch/parallel execution       │
│  Tech: Node.js, TypeScript,         │    │  Tech: Celery/RQ (future)           │
│        Express, Playwright          │    │                                     │
│                                     │    │  ┌───────────────────────────────┐  │
│  ┌───────────────────────────────┐  │    │  │      Celery/RQ Worker         │  │
│  │     MCP Protocol Handler      │  │    │  │   (Batch test execution)      │  │
│  │  (JSON-RPC over stdio/HTTP)   │  │    │  └───────────────────────────────┘  │
│  └───────────────────────────────┘  │    │              │                      │
│              │                      │    │              ▼                      │
│              ▼                      │    │  ┌───────────────────────────────┐  │
│  ┌───────────────────────────────┐  │    │  │     Playwright Executor       │  │
│  │     Playwright Tools          │  │    │  │   (Run generated tests)       │  │
│  │  • navigate    • click        │  │    │  └───────────────────────────────┘  │
│  │  • fill        • screenshot   │  │    │                                     │
│  │  • assert      • evaluate     │  │    └─────────────────────────────────────┘
│  └───────────────────────────────┘  │
│              │                      │
│              ▼                      │
│  ┌───────────────────────────────┐  │
│  │     Browser Manager           │  │
│  │  (Chromium/Firefox/WebKit)    │  │
│  └───────────────────────────────┘  │
└───────────────┬─────────────────────┘
                │
                ▼
      ┌─────────────────┐        ┌─────────────────┐
      │  TARGET APP     │        │   PostgreSQL    │
      │  (App under     │        │   Database      │
      │   test)         │        │   Port: 5432    │
      └─────────────────┘        └─────────────────┘
```

---

## Technology Summary

| Component | Technology | Port |
|-----------|------------|------|
| Frontend | React, TypeScript, Vite, Tailwind | 5173 |
| Backend | Python, FastAPI, SQLAlchemy | 8000 |
| MCP Server | Node.js, TypeScript, Playwright | 3001 |
| Database | PostgreSQL | 5432 |
| Cache | Redis (optional) | 6379 |
| LLM | OpenAI GPT-4, Anthropic Claude | - |

---

## Security Considerations

| Layer | Security Measure |
|-------|------------------|
| **Authentication** | JWT tokens, bcrypt password hashing |
| **API** | CORS, rate limiting, input validation |
| **Database** | Parameterized queries, connection pooling |
| **Secrets** | Environment variables, no hardcoded keys |
| **MCP Server** | Session isolation, timeout limits |

---

## Scalability Notes

| Area | Approach |
|------|----------|
| **Database** | Connection pooling, read replicas |
| **Backend** | Horizontal scaling with load balancer |
| **MCP Server** | Multiple instances, session affinity |
| **Test Execution** | Celery/RQ workers for parallel runs |
| **File Storage** | S3-compatible storage for artifacts |
