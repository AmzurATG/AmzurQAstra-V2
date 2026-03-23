# QAstra End-to-End Flow

This document describes the complete workflow of QAstra, from inputs to test execution and reporting.

---

## Overview

```
INPUTS → BUILD INTEGRITY CHECK → TEST CASE GENERATION → TEST STEP GENERATION → PLAYWRIGHT EXECUTION
```

---

## Inputs

QAstra accepts multiple input sources to generate and execute tests:

| Input Type | Description | Format |
|------------|-------------|--------|
| **Requirement Document** | Product requirements, user stories, or specifications | PDF, Word, Markdown |
| **App URL + Credentials** | Target application URL with login credentials | URL, username/password |
| **Jira/Azure DevOps Board** | Connected task tracker with stories and acceptance criteria | API integration |
| **Existing Test Cases** | Previously created test cases (optional) | Import from CSV/JSON |

```
┌─────────────────┬─────────────────┬─────────────────┬───────────────────────┐
│  Requirement    │  App URL +      │  Jira/Azure     │  Existing Test        │
│  Document       │  Credentials    │  DevOps Board   │  Cases (optional)     │
└────────┬────────┴────────┬────────┴────────┬────────┴───────────┬───────────┘
         │                 │                 │                     │
         ▼                 ▼                 ▼                     ▼
                        [PHASE 1: BUILD INTEGRITY CHECK]
```

---

## Phase 1: Build Integrity Check

**Purpose**: Verify the target application is ready for testing before generating or executing tests.

### Steps Performed

1. **Verify App Reachable**
   - HTTP/HTTPS connectivity check
   - DNS resolution validation
   - SSL certificate verification

2. **Login with Credentials**
   - Navigate to login page
   - Enter provided credentials
   - Verify successful authentication
   - Handle MFA if configured

3. **Check Critical Pages Load**
   - Navigate to key application pages
   - Verify page load completes
   - Check for JavaScript errors
   - Validate essential elements present

4. **Capture Baseline Screenshots**
   - Screenshot of each critical page
   - Store for visual regression comparison
   - Record page load times

### Output

| Result | Action |
|--------|--------|
| ✅ All checks pass | Proceed to Phase 2 |
| ❌ App unreachable | Block testing, notify user |
| ⚠️ Partial failure | Warning, allow user to proceed |

---

## Phase 2: Test Case Generation (LLM)

**Purpose**: Automatically generate test cases from requirements using AI.

### Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: TEST CASE GENERATION (LLM)                     │
│                                                                             │
│  1. Parse requirement document (PDF/Word/Markdown)                          │
│  2. Extract user stories from Jira/Azure DevOps                             │
│  3. Analyze acceptance criteria                                             │
│  4. Generate structured test cases                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Generated Test Case Structure

Each test case includes:

| Field | Description | Example |
|-------|-------------|---------|
| **Test ID** | Unique identifier | TC-LOGIN-001 |
| **Title** | Brief description | Verify login with valid credentials |
| **Description** | Detailed explanation | User should be able to login with registered email and password |
| **Preconditions** | Required state | User account exists, user is logged out |
| **Priority** | Importance level | Critical, High, Medium, Low |
| **Category** | Test type | Smoke, Regression, E2E |
| **Tags** | Labels for filtering | authentication, happy-path |

### LLM Prompts Used

- **System Prompt**: Defines the AI as a QA expert
- **Context**: Includes app description, existing test cases
- **Requirements**: The parsed requirement content
- **Output Format**: JSON schema for structured response

---

## Phase 3: Test Step Generation (LLM)

**Purpose**: Generate detailed, executable test steps for each test case.

### Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 3: TEST STEP GENERATION (LLM)                     │
│                                                                             │
│  For each test case:                                                        │
│  1. Analyze test objective                                                  │
│  2. Determine required actions                                              │
│  3. Identify target elements                                                │
│  4. Define assertions and expected results                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Generated Test Step Structure

Each step includes:

| Field | Description | Example |
|-------|-------------|---------|
| **Step #** | Execution order | 1, 2, 3... |
| **Action** | Playwright action | click, fill, navigate, assert |
| **Target** | Element selector | `#email`, `button[type="submit"]` |
| **Value** | Input data (if applicable) | "test@example.com" |
| **Expected Result** | What should happen | Redirect to /dashboard |

### Supported Actions

| Action | Description | Playwright Method |
|--------|-------------|-------------------|
| `navigate` | Go to URL | `page.goto()` |
| `click` | Click element | `page.click()` |
| `fill` | Enter text | `page.fill()` |
| `select` | Select dropdown | `page.selectOption()` |
| `check` | Check checkbox | `page.check()` |
| `hover` | Mouse hover | `page.hover()` |
| `wait` | Wait duration | `page.waitForTimeout()` |
| `screenshot` | Capture image | `page.screenshot()` |
| `assert_visible` | Check visibility | `page.isVisible()` |
| `assert_text` | Verify text | `page.textContent()` |
| `assert_url` | Check URL | `page.url()` |

---

## Phase 4: Playwright Execution

**Purpose**: Execute generated tests using Playwright and generate reports.

### Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 4: PLAYWRIGHT EXECUTION                           │
│                                                                             │
│  1. Convert test steps → Playwright actions                                 │
│  2. Launch browser session (Chromium/Firefox/WebKit)                        │
│  3. Execute each step sequentially                                          │
│  4. Capture screenshots on each step                                        │
│  5. Record video (optional)                                                 │
│  6. Generate test report                                                    │
│  7. Push results to Jira (if connected)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Execution Flow

```
Test Case
    │
    ├── Step 1: navigate → /login
    │       └── ✅ Success (1.2s)
    │
    ├── Step 2: fill → #email → "test@example.com"
    │       └── ✅ Success (0.3s)
    │
    ├── Step 3: fill → #password → "password123"
    │       └── ✅ Success (0.2s)
    │
    ├── Step 4: click → button[type="submit"]
    │       └── ✅ Success (0.5s)
    │
    └── Step 5: assert_url → /dashboard
            └── ✅ Success (0.1s)

Result: PASSED (2.3s)
```

### Test Run Output

| Output | Description |
|--------|-------------|
| **Test Results** | Pass/Fail status for each test case |
| **Screenshots** | Image capture at each step |
| **Video Recording** | Full test execution video |
| **Error Details** | Stack trace and context for failures |
| **Performance Metrics** | Step durations, total time |

### Jira Integration

When connected, QAstra can:
- Create test execution records
- Update test case status
- Attach screenshots to issues
- Comment with execution summary
- Link test failures to bugs

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUTS                                          │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│  Requirement    │  App URL +      │  Jira/Azure     │  Existing Test        │
│  Document       │  Credentials    │  DevOps Board   │  Cases (optional)     │
└────────┬────────┴────────┬────────┴────────┬────────┴───────────┬───────────┘
         │                 │                 │                     │
         ▼                 ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 1: BUILD INTEGRITY CHECK                          │
│  • Verify app is reachable                                                  │
│  • Login with credentials                                                   │
│  • Check critical pages load                                                │
│  • Capture baseline screenshots                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: TEST CASE GENERATION (LLM)                     │
│  • Parse requirement document                                               │
│  • Analyze Jira stories/acceptance criteria                                 │
│  • Generate test cases with:                                                │
│    - Test ID, Title, Description                                            │
│    - Preconditions                                                          │
│    - Priority & Category                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 3: TEST STEP GENERATION (LLM)                     │
│  • For each test case, generate detailed steps:                             │
│    - Action (click, type, navigate, assert)                                 │
│    - Target element (selector strategy)                                     │
│    - Expected result                                                        │
│    - Test data                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 4: PLAYWRIGHT EXECUTION                           │
│  • Convert test steps → Playwright actions                                  │
│  • Execute with screenshots/video                                           │
│  • Generate reports                                                         │
│  • Push results back to Jira                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

| Phase | Input | Output | Technology |
|-------|-------|--------|------------|
| **Phase 1** | App URL, Credentials | Integrity Report, Screenshots | Playwright MCP |
| **Phase 2** | Requirements, Jira Stories | Test Cases (JSON) | OpenAI/Claude |
| **Phase 3** | Test Cases | Test Steps with selectors | OpenAI/Claude |
| **Phase 4** | Test Steps | Execution Report, Artifacts | Playwright |
