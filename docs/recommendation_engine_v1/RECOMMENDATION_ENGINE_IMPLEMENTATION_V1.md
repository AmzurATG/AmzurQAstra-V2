# Recommendation Engine — End-to-End Implementation

## File Structure

```
AmzurQAstra/
│
├── RECOMMENDATION_ENGINE_REVIEW.md
│
├── backend/
│   ├── main.py                                       # Route registration (prefix /api)
│   │
│   ├── config/
│   │   └── domain_mapping.json                       # 7 domain configs (keywords, business_context, tests)
│   │
│   ├── services/
│   │   ├── recommendation_engine.py                  # Multi-layer semantic engine (~1,800 lines)
│   │   │                                             #   └─ Phase 1: LLM-based out-of-scope filtering
│   │   │                                             #   └─ Phase 2: 3-layer scoring (keyword + semantic + stories)
│   │   │                                             #   └─ Phase 3: Weighted fusion
│   │   │                                             #   └─ Phase 4: Post-processing & evidence validation
│   │   ├── strategy_recommender.py                   # Strategy-level recommendation logic
│   │   ├── domain_classifier.py                      # Fast domain classifier (keyword 50% + embeddings 50%)
│   │   ├── llm_domain_classifier.py                  # LLM fallback classifier (GPT-4/Gemini)
│   │   ├── domain_test_orchestrator.py               # Orchestrates domain pipeline
│   │   ├── litellm_client.py                         # LiteLLM proxy/direct API wrapper
│   │   ├── llm_client.py                             # OpenAI/Fireworks API client
│   │   └── llm_helper.py                             # LLM helper utilities
│   │
│   ├── routes/
│   │   └── test_recommendations_routes.py            # API endpoints
│   │       ├── POST /generate-test-recommendations   #   → Multi-layer semantic engine
│   │       └── POST /domain-based-recommendations    #   → Domain-based engine
│   │
│   ├── test_api_endpoint.py                          # Tests: domain recommendations endpoint
│   ├── test_domain_classification.py                 # Tests: domain classifier
│   └── test_brd_validation.py                        # Tests: BRD validation
│
└── frontend/
    └── src/
        ├── App.js                                    # Route mapping → TestRecommendationsDisplay
        │
        ├── components/
        │   ├── TestRecommendationsDisplay.js         # Main recommendations UI (renders results)
        │   ├── AITestUserStories.js                  # User stories input + triggers recommendations
        │   ├── AITestSidebar.js                      # Sidebar navigation for AI test features
        │   └── BICOutputScreen.js                    # Build integrity check output
        │
        └── utils/
            └── routes/
                └── routes.js                         # Route: /test-recommendations
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                                │
│                                                                         │
│  AITestUserStories.js ─── (BRD + user stories)  ───┐                    │
│                                                    │                    │
│  BICOutputScreen.js ──── (BRD content) ──────────┐ │                    │
│                                                  │ │                    │
└──────────────────────────────────────────────────┼─┼────────────────────┘
                                                   │ │
                               ┌───────────────────┘ │
                               ▼                     ▼
              POST /api/domain-based       POST /api/generate-test
              -recommendations             -recommendations
                               │                     │
┌──────────────────────────────┼─────────────────────┼────────────────────┐
│ BACKEND                      │                     │                    │
│                              ▼                     ▼                    │
│           domain_test_orchestrator.py    recommendation_engine.py       │
│                    │                        │                           │
│         ┌──────────┴──────────┐       ┌─────┴──────────┐                │
│         ▼                     ▼       ▼                ▼                │
│  domain_classifier.py   llm_domain    LLM (filter    3-Layer            │
│  (keyword + semantic)   _classifier   out-of-scope)  Scoring            │
│         │                  .py             │            │               │
│         │                   │              │     ┌──────┼──────┐        │
│         ▼                   ▼              │     ▼      ▼      ▼        │
│  domain_mapping.json   litellm_client      │  L1:KW  L2:Sem  L3:US      │
│                              │             │     │      │      │        │
│                              ▼             │     └──────┴──────┘        │
│                         GPT-4/Gemini       │           │                │
│                                            │     Weighted Fusion        │
│                                            │           │                │
│                                            └─────┬─────┘                │
│                                                  ▼                      │
│                                         Standard + Recommended          │
│                                              Tests                      │
└─────────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                             │
│  TestRecommendationsDisplay.js                                       │
│  └─ Renders: standard tests (sorted HIGH→LOW) + recommended tests    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Engine 1: Multi-Layer Semantic Engine

**File:** `backend/services/recommendation_engine.py`

### Scoring Formula

```
confidence = (0.30 × L_keyword) + (0.35 × L_semantic) + (0.35 × L_stories)
```

### Adjustments

| Condition | Modifier |
|-----------|----------|
| User story matches test type | × 1.30 (+30% bonus) |
| Semantic-only match (no keywords or stories) | × 0.85 (-15% penalty) |
| Weak inference | × 0.70 (-30% penalty) |
| Domain context match | × 1.10 to 1.15 (+10-15% boost) |
| Payment test without explicit keywords | Suppressed |

### Thresholds

| Parameter | Value |
|-----------|-------|
| Semantic similarity floor (L2) | 0.28 |
| User story similarity floor (L3) | 0.25 |
| Recommendation output threshold | 0.08 |
| Keyword minimum (standard tests) | 1+ |
| Keyword minimum (recommended tests) | 2+ |

### 24 Testing Types Taxonomy

**Standard/Critical (11):**
Smoke, Functional, Role-Based Access, API Functional, UI Regression, Payment Workflow, Session Management, Connectivity, Browser Compatibility, Error Handling, Mobile Responsiveness

**Recommended/Post-MVP (13):**
Chaos, Interoperability, Usability, API Contract, AI Visual Regression, Payment Security, Concurrency, Real-time Events, Accessibility Compliance, Localization, PWA, Predictive Analytics, Data Migration

---

## Engine 2: Domain-Based System

**Files:** `domain_classifier.py` → `llm_domain_classifier.py` → `domain_test_orchestrator.py`

### 3-Stage Pipeline

| Stage | File | Logic |
|-------|------|-------|
| 1. Fast Classify | `domain_classifier.py` | Keyword match (50%) + sentence-transformer embeddings (50%) |
| 2. LLM Fallback | `llm_domain_classifier.py` | Triggered if confidence < 0.60; uses GPT-4/Gemini |
| 3. Recommend | `domain_test_orchestrator.py` | Maps domain → 5 standard + 5 recommended tests |

### 7 Supported Domains

| Domain | Example Keywords |
|--------|-----------------|
| Healthcare | patient, ehr, hipaa, clinical |
| Retail/eCommerce | cart, checkout, product, inventory |
| CRM | customer, lead, opportunity, sales |
| Logistics/Supply Chain | shipment, tracking, warehouse, route |
| Banking/Financial | transaction, payment, compliance |
| SaaS/B2B | collaboration, workflow, integration |
| IoT/Hardware | device, sensor, firmware, connectivity |

---

## LLM Prompts

### Prompt 1: Out-of-Scope Content Filtering

**Used in:** `recommendation_engine.py` (Phase 1 — Preprocessing)  
**Purpose:** Removes deferred/excluded BRD sections before scoring  
**Temperature:** 0.1  
**Expected Response:** JSON

```text
You are a Business Analyst expert. Your task is to clean a Business Requirements Document (BRD)
by removing ONLY out-of-scope content while preserving all in-scope content.

**CRITICAL RULES:**

1. **PRESERVE "In Scope" sections** - NEVER remove content under "In Scope" headers
   - If you see "In Scope" or "In-Scope", keep ALL content under it
   - Only remove content explicitly under "Out of Scope" headers

2. **REMOVE "Out of Scope" sections ONLY** - Be thorough and catch ANY indication that
   something is NOT included in current scope:

   **Explicit Markers:**
   - "Out of Scope", "Out-of-Scope", "Not in Scope"
   - "Deferred", "Future", "Later Phase", "Phase 2+", "V2", "Version 2"
   - "Excluded", "Not Required", "Not Needed"
   - "[OUT OF SCOPE]", "[DEFERRED]", "(Phase 2)", "(Future Release)"
   
   **Informal Phrases:**
   - "not focusing on", "will come later", "future consideration"
   - "nice to have", "lower priority", "if time permits", "if we have time"
   - "next iteration", "post-launch", "post-MVP", "after go-live"
   - "we're skipping", "let's table this", "parking lot item"
   - "optional feature", "stretch goal", "backlog item"
   
   **Temporal Indicators:**
   - "in a future release", "in the next version", "down the road"
   - "eventually", "someday", "at a later date"

3. **Removal boundaries:**
   - Start removing FROM the "Out of Scope" header or exclusion phrase
   - Stop removing BEFORE the next major section (like "4. Requirements" or "In Scope")
   - If a "Scope" section has BOTH "In Scope" and "Out of Scope", remove ONLY
     the "Out of Scope" part

4. **Extract** titles of removed out-of-scope features/items for logging

**EXAMPLE:**
BEFORE:
  3. Scope
    In Scope
      - Feature A
      - Feature B
    Out of Scope
      - Feature C
      - Feature D

AFTER (keep "In Scope", remove "Out of Scope"):
  3. Scope
    In Scope
      - Feature A
      - Feature B

**ORIGINAL BRD:**
{text}

**RESPOND WITH JSON ONLY:**
{
  "cleaned_text": "<full cleaned BRD with In Scope preserved, Out of Scope removed>",
  "removed_sections": ["Feature C", "Feature D"]
}

**IMPORTANT:**
- Return the FULL cleaned text (not a summary)
- NEVER remove "In Scope" content
- ONLY remove "Out of Scope" content
- Be conservative - if unsure whether something is in or out of scope, KEEP it
- Respond ONLY with valid JSON, no extra text
```

---

### Prompt 2: LLM Domain Classification

**Used in:** `llm_domain_classifier.py` (Fallback when fast classifier confidence < 0.60)  
**Purpose:** Classifies application domain with higher accuracy  
**Temperature:** 0.1  
**Expected Response:** JSON

**System Message:**
```text
You are an expert software QA analyst specializing in domain classification.
```

**User Message:**
```text
You are an expert software QA analyst specializing in domain classification for test
strategy planning.

**Task**: Analyze the BRD and user stories below to identify the PRIMARY application domain.

**Available Domains**:
{domains_text}

**BRD Content**:
{brd_content}

**User Stories**:
{stories_content}

**Instructions**:
1. Identify the PRIMARY domain from the list above
2. Provide confidence score (0.0 to 1.0) - be realistic, not overly confident
3. List 3-5 key evidence phrases from the BRD that support your classification
4. Provide brief reasoning (2-3 sentences)
5. If confidence < 0.7, provide top 3 candidate domains with scores

**Response Format** (JSON only, no markdown):
{
  "domain": "Exact domain name from list above",
  "confidence_score": 0.85,
  "evidence": ["specific phrase from BRD", "another phrase", "third phrase"],
  "reasoning": "Brief explanation of why this domain was selected",
  "top_candidates": [
    {"domain": "Domain Name", "confidence": 0.85},
    {"domain": "Another Domain", "confidence": 0.45},
    {"domain": "Third Domain", "confidence": 0.30}
  ]
}

Respond with ONLY the JSON object, no additional text.
```

---

## API Endpoints

### POST `/api/generate-test-recommendations`

**Input:**
```json
{
  "brd_content": "string (required)",
  "user_stories": [
    {
      "id": "US-001",
      "title": "string",
      "description": "string",
      "acceptance_criteria": "string or list"
    }
  ],
  "confidence_threshold": 0.08
}
```

**Output:**
```json
{
  "standard_tests": [
    {
      "test_type": "Functional Testing",
      "confidence": 0.82,
      "confidence_level": "HIGH",
      "layer_scores": { "keyword": 0.7, "semantic": 0.85, "stories": 0.9 },
      "evidence": ["matched keywords", "semantic sections"]
    }
  ],
  "recommended_tests": [...],
  "filtered_content": {
    "removed_sections": ["Feature X (deferred)"],
    "original_length": 5000,
    "cleaned_length": 4200
  },
  "metadata": {
    "model": "all-mpnet-base-v2",
    "timestamp": "2026-04-29T...",
    "threshold": 0.08
  }
}
```

### POST `/api/domain-based-recommendations`

**Input:**
```json
{
  "brd_content": "string (required)",
  "user_stories": [...]
}
```

**Output:**
```json
{
  "domain_classification": {
    "domain": "Healthcare",
    "confidence_score": 0.78,
    "confidence_level": "HIGH",
    "keyword_score": 0.65,
    "context_score": 0.91,
    "evidence": ["patient", "ehr", "hipaa"]
  },
  "recommendations": {
    "standard_tests": ["HIPAA Compliance", "Patient Data Validation", ...],
    "recommended_tests": ["Interoperability Testing", ...]
  },
  "processing_time_seconds": 2.3
}
```

---

## ML Model & Dependencies

| Component | Value |
|-----------|-------|
| Embedding Model | `sentence-transformers/all-mpnet-base-v2` |
| Model Size | ~420 MB |
| Distance Metric | Cosine similarity |
| LLM Providers | OpenAI (GPT-4), Google (Gemini) via LiteLLM |
| LLM Temperature | 0.1 (deterministic) |
| Response Format | JSON |
