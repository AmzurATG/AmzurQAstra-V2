# Test Recommendation Engine

## Overview

The Test Recommendation Engine is a domain-based testing strategy suggestion system that analyzes a project's Business Requirements Document (BRD) and user stories, classifies the business domain (e.g., healthcare, retail, finance), and recommends curated standard and additional test cases. It uses **keyword-based classification with optional LLM fallback** for domain detection and provides test playbooks loaded from a YAML configuration file.

---

## File Structure

```
backend/
├── alembic/
│   └── versions/
│       ├── 20260427_0001_add_test_recommendation_runs.py   # Migration: create test_recommendation_runs table
│       └── 20260428_0001_test_recommendation_pdf_path.py    # Migration: add pdf_path column
├── api/
│   └── v1/
│       └── functional/
│           ├── router.py                                    # Registers recommendation routes
│           └── test_recommendations.py                      # API endpoints (CRUD, PDF, email)
├── features/
│   └── functional/
│       ├── config/
│       │   └── domain_test_mapping.yaml                     # Domain definitions, keywords, test playbooks
│       ├── core/
│       │   └── llm_prompts/
│       │       └── test_recommendation_domain.py            # LLM system prompt for domain classification
│       ├── db/
│       │   └── models/
│       │       └── test_recommendation_run.py               # SQLAlchemy model for recommendation runs
│       ├── schemas/
│       │   └── test_recommendation.py                       # Pydantic request/response schemas
│       └── services/
│           ├── recommendation/
│           │   ├── __init__.py
│           │   ├── domain_classifier.py                     # Keyword scoring algorithm + strategy resolver
│           │   └── domain_config.py                         # YAML loader + domain record dataclasses
│           ├── test_recommendation_pdf.py                   # PDF report builder (FPDF)
│           └── test_recommendation_service.py               # Main orchestrator service
├── tests/
│   └── test_recommendation_domain_classifier.py             # Unit tests for keyword classifier
│
frontend/
└── src/
    └── features/
        └── functional/
            ├── api/
            │   └── index.ts                                 # API client functions for recommendation endpoints
            ├── components/
            │   ├── EmailReportDialog.tsx                     # Dialog to email recommendation PDF
            │   ├── TestRecommendationRunModal.tsx            # Modal to trigger & view recommendation runs
            │   └── index.ts                                 # Component barrel export
            ├── pages/
            │   └── Requirements.tsx                         # Requirements page (integrates recommendation UI)
            └── types/
                └── index.ts                                 # TypeScript types for recommendation data
│
storage/
└── TestRecommendations/
    └── {project_id}/
        └── {run_id}.pdf                                     # Generated PDF reports
```

---

## API Endpoints

All endpoints are under `/api/v1/functional/test-recommendations` and require authentication + `project_id` query parameter.

| Method   | Route                              | Description                        |
| -------- | ---------------------------------- | ---------------------------------- |
| `POST`   | `/runs`                            | Create & execute a recommendation run |
| `GET`    | `/runs`                            | List all runs for a project (paginated) |
| `GET`    | `/runs/{run_id}`                   | Get a single run's details         |
| `GET`    | `/runs/{run_id}/pdf`               | Download the PDF report            |
| `POST`   | `/runs/{run_id}/email`             | Email the PDF report to a recipient |
| `DELETE` | `/runs/{run_id}`                   | Delete a run and its PDF           |

---

## Database Schema

### Table: `test_recommendation_runs`

| Column          | Type          | Description                                        |
| --------------- | ------------- | -------------------------------------------------- |
| `id`            | Integer (PK)  | Auto-increment primary key                         |
| `project_id`    | Integer (FK)  | References `projects.id`                           |
| `requirement_id`| Integer (FK)  | References `requirements.id`                       |
| `created_by`    | Integer (FK)  | References `users.id` (nullable)                   |
| `status`        | String        | `pending`, `completed`, or `failed`                |
| `result_json`   | JSONB         | Full playbook output (domain, tests, evidence)     |
| `error_message` | Text          | Failure reason (if `status=failed`)                |
| `pdf_path`      | String        | Relative path to the stored PDF report             |
| `created_at`    | DateTime      | Auto-set on creation                               |
| `updated_at`    | DateTime      | Auto-updated on modification                       |

**Indices:** `project_id`, `requirement_id`, `created_by`

---

## End-to-End Flow

```
1. POST /runs  { project_id, requirement_id }
        │
2. _precheck()
   ├── Validate requirement exists & has parsed text content
   └── Verify project has ≥ 1 user story
        │
3. _build_corpus()
   ├── BRD text (truncated to 80K chars)
   └── Up to 100 user stories (ascending by ID)
        │
4. classify_domains_keyword()
   ├── Score each domain via weighted keyword hits from YAML
   ├── confidence = (top1 - top2) / (top1 + ε)
   └── Fallback to "general" if no domain keywords matched
        │
5. [Optional] _llm_classify_domain()
   ├── Triggered only if LLM fallback is enabled AND local confidence < threshold
   ├── Sends corpus + system prompt to LLM (temperature=0.15)
   └── Overrides local choice only if LLM confidence > local confidence
        │
6. strategies_for_domain()
   └── Load standard_tests[] + recommended_tests[] from YAML for chosen domain
        │
7. _gap_alignment_warnings()
   └── Cross-reference latest gap analysis run for this requirement
        │
8. Persist TestRecommendationRun (status=completed, result_json filled)
        │
9. build_test_recommendation_pdf()
   └── Render business-readable PDF via FPDF
        │
10. _write_pdf_to_storage()
    └── Save to storage/TestRecommendations/{project_id}/{run_id}.pdf
        │
11. Return completed run to frontend
```

---

## Domain Classification

### Keyword-Based (Primary)

Configured in `domain_test_mapping.yaml`. Currently defined domains:

| Domain ID    | Label              | Example Keywords                                      |
| ------------ | ------------------ | ----------------------------------------------------- |
| `general`    | General software   | *(fallback — no keywords)*                            |
| `healthcare` | Healthcare         | hipaa, phi, patient, clinical, ehr, emr, hl7, fhir   |
| `retail`     | Retail / e-commerce| checkout, cart, inventory, pos, sku, fulfillment      |
| `finance`    | Finance / banking  | bank, payment, ledger, kyc, aml, pci, settlement     |

**Algorithm:**
1. For each domain (except `general`), count keyword occurrences in the corpus (case-insensitive).
2. Apply keyword weights (e.g., `hipaa: 3×`, `pci: 3×`).
3. Rank by score. Confidence = `(top1_score − top2_score) / (top1_score + ε)`, capped to `[0, 1]`.
4. If only one domain has a non-zero score, confidence is boosted to ≥ 0.75.
5. If no domain-specific keywords match, falls back to `general`.

### LLM Fallback (Optional)

Triggered when `TEST_RECOMMENDATION_LLM_FALLBACK_ENABLED=true` and local confidence is below `TEST_RECOMMENDATION_DOMAIN_CONFIDENCE_THRESHOLD`.

---

## LLM Prompts

### Domain Classification System Prompt

**Source:** `backend/features/functional/core/llm_prompts/test_recommendation_domain.py`

```
You classify the business domain of a software product from a draft requirements
document and user story titles/descriptions.
Pick exactly one domain_id from this list: ["healthcare", "retail", "finance", "general"].

Respond with a single JSON object only (no markdown, no code fences):
{"domain_id": "<one of the allowed ids>", "confidence": <number from 0 to 1>, "rationale": "<short string>"}

Rules:
- Prefer the most specific domain when evidence supports it; use "general" only when none fit well.
- confidence reflects how sure you are (0.9+ when evidence is strong).
```

> The allowed domain IDs list is dynamically built from `domain_test_mapping.yaml` at runtime (all `id` values except `general` are included, plus `general` itself).

### Domain Classification User Prompt

```
Classify this product's domain using the following text:

<corpus text — BRD + user stories, capped to TEST_RECOMMENDATION_LLM_MAX_CORPUS_CHARS>
```

**LLM Settings:**
- Temperature: `0.15` (low, for deterministic output)
- Expected response format: Single JSON object `{"domain_id", "confidence", "rationale"}`

---

## Configuration

| Environment Variable                                | Type    | Default | Description                                        |
| --------------------------------------------------- | ------- | ------- | -------------------------------------------------- |
| `TEST_RECOMMENDATION_LLM_FALLBACK_ENABLED`          | Boolean | `false` | Enable LLM fallback for domain classification      |
| `TEST_RECOMMENDATION_DOMAIN_CONFIDENCE_THRESHOLD`    | Float   | ~0.5    | Local confidence threshold that triggers LLM fallback |
| `TEST_RECOMMENDATION_LLM_MAX_CORPUS_CHARS`           | Integer | ~40000  | Max text length sent to LLM                        |
| `STORAGE_LOCAL_PATH`                                 | String  | —       | Base directory for stored PDFs                     |
| `SMTP_HOST` / `EMAIL_FROM_ADDRESS`                   | String  | —       | SMTP settings for email delivery (optional)        |

---

## Result JSON Structure

The `result_json` stored on each completed run contains:

```json
{
  "domain_id": "healthcare",
  "domain_label": "Healthcare",
  "confidence": 0.92,
  "source": "local",
  "report_summary": "Detected domain \"Healthcare\" (92% confidence; source: local). ...",
  "input_snapshot": {
    "run_kind": "test_recommendations",
    "requirement_id": 1,
    "project_id": 1,
    "user_stories_included": [{"id": 1, "external_key": "US-1", "title": "..."}],
    "user_stories_total_in_project": 50,
    "max_stories_cap": 100,
    "ordering": "user_stories.id ascending"
  },
  "local_classification": {
    "domain_id": "healthcare",
    "confidence": 0.92,
    "label": "Healthcare",
    "per_domain_scores": {"healthcare": 15.0, "retail": 0.0, "finance": 2.0},
    "evidence": {"healthcare": ["hipaa", "phi", "patient"]},
    "score_breakdown": {"healthcare": {"hipaa": 9.0, "phi": 3.0, "patient": 3.0}}
  },
  "llm_fallback": null,
  "standard_tests": [
    {"category": "Compliance", "name": "PHI handling and access control", "priority": "high", "reason": "..."}
  ],
  "recommended_tests": [
    {"category": "Interoperability", "name": "HL7 / FHIR message validation", "priority": "medium", "reason": "..."}
  ],
  "warnings": []
}
```

---

## Design Highlights

- **Two-tier classification** — fast keyword matching first; LLM only when confidence is uncertain.
- **YAML-driven playbooks** — new domains and test strategies can be added without code changes.
- **Graceful degradation** — PDF generation failures don't block run completion; warnings are tracked.
- **On-demand PDF regeneration** — PDFs can be rebuilt from the persisted `result_json`.
- **Secure file handling** — path traversal prevention on PDF read/write/delete operations.
- **Audit trail** — full input snapshot stored (BRD size, stories used, total available).

---

## V1 vs V2 Comparison

> V1 reference code is stored in `docs/recommendation_engine_v1/` for historical reference.

### Architecture Overview

| Aspect | V1 (Previous Project) | V2 (Current) |
| ------ | --------------------- | ------------- |
| **Engines** | Two separate engines (Multi-Layer Semantic + Domain-Based) | Single unified domain-based engine |
| **Orchestrator** | `domain_test_orchestrator.py` coordinates classifier → recommender agents | `test_recommendation_service.py` handles full lifecycle |
| **State** | Stateless API calls (no persistence) | Database-persisted runs with status tracking |
| **Output** | JSON response only | JSON + PDF report + email delivery |
| **Config Format** | `domain_mapping.json` | `domain_test_mapping.yaml` |
| **Codebase Size** | ~1,800 lines in `recommendation_engine.py` alone + 6 service files | ~400 lines in service + modular classifier/config/PDF modules |

### Domain Classification

| Aspect | V1 | V2 |
| ------ | -- | -- |
| **Primary Method** | Keyword match (50%) + sentence-transformer embeddings (50%) | Weighted keyword match only |
| **Embedding Model** | `all-mpnet-base-v2` (~420 MB) | None (removed) |
| **LLM Fallback Trigger** | Confidence < 0.60 | Confidence < configurable threshold (~0.5) |
| **LLM Providers** | GPT-4 / Gemini via LiteLLM proxy with multi-provider fallback | Project's configured LLM client (provider-agnostic) |
| **LLM Temperature** | 0.1 | 0.15 |
| **Confidence Formula** | `(keyword × 0.5) + (embedding × 0.5)` | `(top1_score − top2_score) / (top1_score + ε)` |
| **Minimum Confidence** | 0.35 (below → LOW_CONFIDENCE response) | Falls back to `general` domain (always returns results) |

### Supported Domains

| V1 (7 domains) | V2 (4 domains) |
| --------------- | --------------- |
| Healthcare | Healthcare |
| Retail / eCommerce | Retail / e-commerce |
| Banking / Financial | Finance / banking |
| CRM | *(not included)* |
| Logistics / Supply Chain | *(not included)* |
| Aeronautical / Aviation | *(not included)* |
| Salesforce (CRM Platform) | *(not included)* |
| *(no fallback domain)* | General software (fallback) |

### Multi-Layer Semantic Engine (V1 Only — Removed in V2)

V1 had a second engine (`recommendation_engine.py`) that scored BRD content against a **fixed 24 testing-type taxonomy** using 3-layer fusion:

| Layer | Weight | Method |
| ----- | ------ | ------ |
| L1: Keyword | 30% | Deterministic keyword trigger matching |
| L2: Semantic | 35% | Section-level paragraph embeddings vs test-type descriptions |
| L3: User Stories | 35% | Per-story embedding comparison against test types |

**Scoring adjustments:**
- User story matches test type → ×1.30 bonus
- Semantic-only match (no keyword/story support) → ×0.85 penalty
- Weak inference → ×0.70 penalty
- Domain context match → ×1.10–1.15 boost
- Payment test without explicit keywords → suppressed

**Thresholds:** Semantic floor 0.28, story floor 0.25, output threshold 0.08.

**24 Testing Types Taxonomy:**
- *Standard (11):* Smoke, Functional, Role-Based Access, API Functional, UI Regression, Payment Workflow, Session Management, Connectivity, Browser Compatibility, Error Handling, Mobile Responsiveness
- *Recommended (13):* Chaos, Interoperability, Usability, API Contract, AI Visual Regression, Payment Security, Concurrency, Real-time Events, Accessibility Compliance, Localization, PWA, Predictive Analytics, Data Migration

This entire engine was **removed in V2** in favor of the domain-based playbook approach.

### LLM Prompts

| Prompt | V1 | V2 |
| ------ | -- | -- |
| **Out-of-Scope Filtering** | Full BRD preprocessing prompt to remove deferred/excluded sections via LLM (temp 0.1). Returns `{cleaned_text, removed_sections}` | Not used (no BRD preprocessing) |
| **Domain Classification** | Detailed prompt with 7 domains, evidence phrases, top-3 candidates, reasoning. Returns `{domain, confidence_score, evidence, reasoning, top_candidates}` | Minimal prompt with dynamic domain list. Returns `{domain_id, confidence, rationale}` |
| **Semantic Scoring** | Sentence-transformer local embeddings (not an LLM call) | Not used |

#### V1 Domain Classification Prompt (LLM Fallback)

```
System: You are an expert software QA analyst specializing in domain classification.

User: You are an expert software QA analyst specializing in domain classification
for test strategy planning.

Task: Analyze the BRD and user stories below to identify the PRIMARY application domain.

Available Domains:
1. Healthcare - ...
2. Retail / eCommerce - ...
[... 7 domains with descriptions ...]

BRD Content: <truncated to 3,000 chars>
User Stories: <truncated to 1,500 chars>

Instructions:
1. Identify the PRIMARY domain from the list above
2. Provide confidence score (0.0 to 1.0)
3. List 3-5 key evidence phrases
4. Provide brief reasoning (2-3 sentences)
5. If confidence < 0.7, provide top 3 candidate domains with scores

Response Format (JSON only):
{
  "domain": "Exact domain name",
  "confidence_score": 0.85,
  "evidence": ["phrase1", "phrase2", "phrase3"],
  "reasoning": "...",
  "top_candidates": [{"domain": "...", "confidence": 0.85}, ...]
}
```

#### V1 Out-of-Scope Filtering Prompt

```
You are a Business Analyst expert. Your task is to clean a Business Requirements
Document (BRD) by removing ONLY out-of-scope content while preserving all in-scope content.

CRITICAL RULES:
1. PRESERVE "In Scope" sections — NEVER remove content under "In Scope" headers
2. REMOVE "Out of Scope" sections ONLY — catch explicit markers (Out of Scope,
   Deferred, Future, Phase 2+, Excluded), informal phrases (not focusing on,
   will come later, nice to have, post-MVP), and temporal indicators (in a future
   release, eventually, at a later date)
3. Removal boundaries: start FROM the exclusion header, stop BEFORE the next major section

ORIGINAL BRD: {text}

RESPOND WITH JSON ONLY:
{"cleaned_text": "<full cleaned BRD>", "removed_sections": ["Feature C", "Feature D"]}
```

### Test Recommendation Output

| Aspect | V1 | V2 |
| ------ | -- | -- |
| **Standard tests** | 5 per domain (from JSON) or up to 11 (from 24-type taxonomy) | Variable per domain (from YAML), each with category/name/priority/reason |
| **Recommended tests** | 5 per domain (from JSON) or up to 13 (from taxonomy) | Variable per domain (from YAML) |
| **Avoid list** | Yes — each domain lists tests to avoid | Not included |
| **Evidence** | Matched keywords + semantic similarity scores + evidence phrases | Matched keywords + weighted score breakdown per domain |
| **Confidence levels** | HIGH (≥0.7), MEDIUM (≥0.4), LOW (<0.4) | Raw float (0–1) with source indicator (local/llm) |

### Infrastructure & Dependencies

| Aspect | V1 | V2 |
| ------ | -- | -- |
| **ML Model** | `sentence-transformers/all-mpnet-base-v2` (~420 MB) | None |
| **Python Deps** | `sentence-transformers`, `numpy`, `scikit-learn`, `torch` | `fpdf` (for PDF generation only) |
| **LLM Client** | Custom `LiteLLMClient` + `LLMClient` (OpenAI/Fireworks/Gemini) with multi-provider cascading fallback | Project's shared `get_llm_client()` (provider-agnostic) |
| **Database** | None (stateless) | `test_recommendation_runs` table with migrations |
| **Storage** | None | PDF files in `storage/TestRecommendations/{project_id}/` |
| **PDF Reports** | Not available | FPDF-rendered business reports |
| **Email Delivery** | Not available | SMTP-based PDF attachment |
| **Gap Analysis Integration** | Not available | Cross-references latest gap analysis for alignment warnings |

### What Was Removed in V2

1. **Multi-Layer Semantic Engine** — entire 24-type taxonomy and 3-layer scoring
2. **Sentence-transformer embeddings** — no local ML model dependency
3. **Out-of-scope BRD filtering** — LLM-based preprocessing step
4. **3 additional domains** — CRM, Logistics, Aviation/Aeronautical, Salesforce
5. **Avoid-tests list** — per-domain list of tests to skip
6. **Multi-provider LLM cascading** — LiteLLM proxy → OpenAI → Fireworks → Gemini fallback chain

### What Was Added in V2

1. **Database persistence** — runs tracked with status, results, timestamps
2. **PDF report generation** — business-readable FPDF output
3. **Email delivery** — send PDF reports via SMTP
4. **Gap analysis warnings** — cross-reference BRD/backlog alignment issues
5. **General fallback domain** — always returns results (no LOW_CONFIDENCE dead end)
6. **YAML-driven config** — easier to edit than JSON; includes keyword weights
7. **Keyword weighting** — domain-specific multipliers (e.g., `hipaa: 3×`)
8. **On-demand PDF regeneration** — rebuild from stored `result_json`
9. **Run deletion with cleanup** — removes DB record + stored PDF file
