
# F2MX Test Case Comparison Report: Manual (Sprint 1 & 2) vs AI-Generated (QAstra)


**Generated:** 2026-06-11 19:48  
**Project:** f2mx-2 (ID 18) — https://atg-f2mx.amzur.com/  
**Manual sources:** `F2MX  Sprint 1 Test cases.xlsx`, `F2MX-Sprint 2 Test Cases.xlsx`  
**AI source:** PostgreSQL `test_cases` table — bulk generation job (standard profile) from BRD-derived user stories


## Executive Summary


This report compares **2,836 manually authored test cases** across Sprint 1 and Sprint 2 with **155 AI-generated test cases** produced by QAstra from the F2MX BRD.

| Metric | Manual | AI-Generated |
|--------|-------:|-------------:|
| Total test cases | **2,836** | **155** |
| Sprint 1 cases | 789 | — |
| Sprint 2 cases | 2,047 | — |
| User stories / feature sheets | 49 sheets | 20 user stories |
| Positive scenarios | 2,194 | 135 |
| Negative scenarios | 605 | 12 |
| Mobile-focused (detected) | 1,164 | N/A (platform-agnostic) |
| Web/Admin-focused (detected) | 1,177 | N/A |
| Estimated manual→AI topic overlap (≥12% similarity) | 2,834 / 2,836 (99.9%) | 84 / 155 AI cases have manual analogs |


**Key finding:** The manual test suite is **~18× larger** than the AI suite and goes **much deeper** on UI/UX validation, role-based permission matrices, league lifecycle edge cases, wallet/economy flows, and sprint-specific scope notes. The AI suite provides **broad BRD-level functional coverage** mapped to acceptance criteria but **misses the majority of granular manual scenarios** — especially Sprint 2 league dashboard, public league browsing, private league creation, and wallet/admin economy modules.


## Table of Contents

1. [Methodology](#methodology)
2. [Data Sources & Counts](#data-sources--counts)
3. [Feature Area Mapping](#feature-area-mapping)
4. [Similarities — Where AI Aligns With Manual Testing](#similarities--where-ai-aligns-with-manual-testing)
5. [Coverage by Topic](#coverage-by-topic)
6. [Gap Analysis — What AI Is Missing](#gap-analysis--what-ai-is-missing)
7. [Sprint 1 Detailed Comparison](#sprint-1-detailed-comparison)
8. [Sprint 2 Detailed Comparison](#sprint-2-detailed-comparison)
9. [AI-Only Coverage (Not in Manual Sprints)](#ai-only-coverage-not-in-manual-sprints)
10. [Manual-Only Coverage (Missing from AI)](#manual-only-coverage-missing-from-ai)
11. [Scenario Type & Priority Analysis](#scenario-type--priority-analysis)
12. [Per User Story AI Inventory](#per-user-story-ai-inventory)
13. [Recommendations](#recommendations)
14. [Appendix A — Manual Sheet Inventory](#appendix-a--manual-sheet-inventory)
15. [Appendix B — Full AI Test Case Catalog](#appendix-b--full-ai-test-case-catalog)
16. [Appendix C — Sample Manual→AI Match Pairs](#appendix-c--sample-manualai-match-pairs)

## Methodology


1. **Manual extraction:** All Excel sheets except `Summary` were parsed. Column headers were normalized across varying formats (`Test Objective` vs `Objective`, `Test Executions Steps` vs `Steps to Execute`).
2. **AI extraction:** All 155 test cases, steps, and linked user stories were pulled from project `f2mx-2` (ID 18).
3. **Feature mapping:** Manual sheets were grouped into 7 feature areas and mapped to AI `user_story_id` ranges.
4. **Similarity scoring:** Jaccard token overlap on objective/steps/expected text + topic keyword buckets + area bonus.
5. **Gap identification:** Topics/sheets where manual count >> AI count; AI cases with no manual match; manual cases below similarity threshold.


## Data Sources & Counts


### Manual Test Case Distribution

| Sprint | Test Cases |
| --- | --- |
| Sprint 2 | 2047 |
| Sprint 1 | 789 |

### Manual Platform Detection

| Platform | Count | % of Manual |
| --- | --- | --- |
| web | 1177 | 41.5% |
| mobile | 1164 | 41.0% |
| unknown | 495 | 17.5% |

### AI Generation Metadata


- **Generation job ID:** 1
- **Profile:** standard
- **Status:** completed
- **Stories processed:** 20/20
- **Created:** 2026-06-02 11:57:04.396016+05:30
- **Updated:** 2026-06-02 12:22:48.472890+05:30


## Feature Area Mapping

| Feature Area | Manual TCs | AI TCs | AI/Manual Ratio | Description |
| --- | --- | --- | --- | --- |
| Sprint 2 — Leagues (Mobile) | 991 | 22 | 2.2% | League module access, my leagues, dashboard/matchup/history/standings, public le… |
| Sprint 2 — Leagues (Web Admin) | 541 | 27 | 5.0% | Web admin league management, members, trading activity, settings, buy-in, catego… |
| Sprint 2 — Wallet & Economy | 454 | 25 | 5.5% | User wallet, transactions, league wallet, packages, promotions, buy-in, reconcil… |
| Sprint 1 — Mobile User Auth & Profile | 306 | 53 | 17.3% | Mobile registration, login, 2FA, password recovery, profile, account deletion, l… |
| Sprint 1 — Web Admin User Management | 292 | 27 | 9.2% | Admin console user listing, unlock, suspend, ban, force reset, soft delete, over… |
| Sprint 1 — Web Admin Staff & Settings | 191 | 11 | 5.8% | Internal admin user CRUD, role changes, staff login routing, admin forgot passwo… |
| Cross-cutting — Notifications & Compliance | 0 | 26 | N/A | Legal compliance, app store config, user notifications, admin broadcasts (AI-onl… |

## Similarities — Where AI Aligns With Manual Testing


Despite the volume difference, the AI test cases **correctly capture the high-level functional intent** of many manual scenarios at the **user story / acceptance criteria level**. The following areas show conceptual alignment:


### Registration & Age Verification


**Mapping:** Manual Sprint 1 sheet `User story -1.1 User Registration` (60 TCs) ↔ AI stories 326, 328 (21 TCs)

**Shared intent:** Both cover DOB validation, under-18 blocking, unique email/username, ToS/Privacy consent, default wallet/XP/tier on signup


### Login & 2FA


**Mapping:** Manual `User story -1.2 User Login` (32 TCs) + `Account Security` (31 TCs) ↔ AI story 329 (10 TCs)

**Shared intent:** Active-user login, 2FA OTP prompt, account lock after failed OTP, force password reset redirect, login audit (IP/timestamp)


### Forgot / Reset Password


**Mapping:** Manual mobile + web forgot password sheets (64 TCs combined) ↔ AI story 330 (11 TCs)

**Shared intent:** OTP to email, validation, reset screen, password complexity, expired/invalid OTP errors


### Profile & Avatar


**Mapping:** Manual `My Profile` (52 TCs) ↔ AI story 331 (11 TCs)

**Shared intent:** Avatar upload JPG/PNG, profile field edit, read-only fields (email, DOB, XP, tier), cross-league avatar sync


### Admin User Management


**Mapping:** Manual Users/Unlock/Suspend/Ban/Force Reset sheets ↔ AI stories 334–336 (27 TCs)

**Shared intent:** User listing/search/filter, unlock/suspend/ban, force reset, soft delete, audit logging, mandatory reason codes


### Admin Staff Accounts


**Mapping:** Manual Internal Admin + Modify Role sheets ↔ AI stories 332–333 (11 TCs)

**Shared intent:** Create staff, activation link, PENDING_ACTIVATION status, role assignment, admin console login with 2FA


### Leagues Module Entry


**Mapping:** Manual Post Login + My Leagues ↔ AI story 337 (8 TCs)

**Shared intent:** Redirect to leagues after login, active/upcoming/completed counts, league cards, empty state


### League Dashboard


**Mapping:** Manual League Dashboard (453 TCs) ↔ AI story 338 (9 TCs)

**Shared intent:** Matchup view, history, standings — AI covers headlines only


### Public Leagues


**Mapping:** Manual Public Leagues (1082 TCs) ↔ AI story 339 (5 TCs)

**Shared intent:** Browse/join public leagues — AI has minimal smoke-level coverage


### Player Market / Trading


**Mapping:** Manual Trading Activity sheets ↔ AI story 340 (7 TCs)

**Shared intent:** Real-time ticker, buy/sell shares, no-slippage execution


### Market Admin Config


**Mapping:** Manual League Settings / Buy-In ↔ AI story 341 (5 TCs)

**Shared intent:** Pricing weights, bid/ask spread, market open dates, audit log


### XP & Tiers


**Mapping:** Manual scoring references ↔ AI stories 342–343 (13 TCs)

**Shared intent:** XP awards, tier assignment, Half-PPR scoring, rank configuration


### Notifications


**Mapping:** Scattered manual email/notification checks ↔ AI stories 344–345 (11 TCs)

**Shared intent:** Password change email, account status notifications, admin broadcasts


## Coverage by Topic


Topic keyword buckets detected across manual vs AI corpora:

| Topic | Manual Hits | AI Hits | AI/Manual Ratio | Status |
| --- | --- | --- | --- | --- |
| Login 2Fa | 2657 | 45 | 1.7% | ❌ Missing |
| Ui Ux Validation | 2224 | 155 | 7.0% | ⚠️ Thin |
| Leagues Access | 1226 | 25 | 2.0% | ❌ Missing |
| Registration Signup | 983 | 149 | 15.2% | ✅ Adequate |
| Private Leagues Invites | 651 | 1 | 0.2% | ❌ Missing |
| Wallet Transactions | 649 | 4 | 0.6% | ❌ Missing |
| League Dashboard | 504 | 41 | 8.1% | ⚠️ Thin |
| Trading Market | 462 | 54 | 11.7% | ⚠️ Thin |
| Admin User List | 382 | 27 | 7.1% | ⚠️ Thin |
| Profile Avatar | 358 | 65 | 18.2% | ✅ Adequate |
| Admin Staff Mgmt | 236 | 16 | 6.8% | ⚠️ Thin |
| Xp Scoring | 212 | 53 | 25.0% | ✅ Adequate |
| Change Password | 118 | 28 | 23.7% | ✅ Adequate |
| Public Leagues | 110 | 5 | 4.5% | ❌ Missing |
| Forgot Password | 105 | 8 | 7.6% | ⚠️ Thin |
| Admin Unlock Suspend Ban | 90 | 20 | 22.2% | ✅ Adequate |
| Account Deletion Logout | 86 | 6 | 7.0% | ⚠️ Thin |
| Admin Force Reset | 84 | 9 | 10.7% | ⚠️ Thin |
| Audit Logging | 78 | 14 | 17.9% | ✅ Adequate |
| Admin Override Merge | 55 | 0 | 0.0% | ❌ Missing |
| Notifications | 32 | 18 | 56.2% | ✅ Adequate |
| Legal Appstore | 3 | 7 | 233.3% | ✅ Adequate |

## Gap Analysis — What AI Is Missing


### Critical Gaps (High Manual Volume, Minimal AI Coverage)


#### League Dashboard deep testing


- **Manual:** 453 manual TCs in Sprint 2 `Leagues Dashboard` sheet
- **AI:** 9 AI TCs (story 338)
- **Missing detail:** Matchup week navigation, roster views, trade history within league, scoring breakdowns, commissioner tools, tab switching, edge cases for bye weeks, tie-breakers at UI level


#### Public Leagues browsing & joining


- **Manual:** 1,082 manual TCs in `Public Leagues` sheet
- **AI:** 5 AI TCs (story 339)
- **Missing detail:** Filter/sort public leagues, league detail pages, join flows, full league error states, capacity limits, commissioner vs participant views


#### Private League Creation & Invitations


- **Manual:** 128 + 91 + 43 + 77 = 339 manual TCs across Create Private, Invites, Three Invitation Methods, Create League flows
- **AI:** 0 dedicated AI stories
- **Missing detail:** QR code invites, direct links, in-app invites, commissioner success screens, invite code entry, join private league


#### Wallet & Transactions


- **Manual:** Multiple Sprint 2 wallet sheets (User Wallet, League Wallet, Transactions, Buy-In, Reconciliation)
- **AI:** Indirect coverage via stories 340–343 only
- **Missing detail:** Wallet balance display, transaction history, buy-in payments, end-of-season payouts, admin balance adjustments, promotions, package configuration


#### UI/UX & Element-Level Validation


- **Manual:** 2,224 manual topic hits
- **AI:** 155 AI topic hits
- **Missing detail:** Placeholder text, logo placement, hyperlink labels, popup field layouts, hover states, pagination UI, empty states, tab highlights


#### Role-Based Permission Matrix


- **Manual:** Manual tests per role: Support Agent, Ops Admin, Super Admin, Commissioner, User
- **AI:** AI mentions roles but rarely tests permission denial per role
- **Missing detail:** Support vs Ops vs Super Admin visibility rules, negative tests for unauthorized actions


#### Override Verification & Merge Duplicate Accounts


- **Manual:** 54 manual TCs (27 each)
- **AI:** 0 AI TCs
- **Missing detail:** Entire features not represented in AI generation


#### Mobile Account Deletion (User-Initiated)


- **Manual:** 60 manual TCs in Account Deletion sheet
- **AI:** 0 AI TCs for mobile self-delete
- **Missing detail:** AI covers admin soft-delete only (story 336), not end-user delete account flow


#### Change Password (In-App Security Settings)


- **Manual:** 27 manual TCs
- **AI:** Partial via login/reset flows
- **Missing detail:** Dedicated change-password screen, current password validation, security settings navigation


#### User Logout


- **Manual:** 8 manual TCs
- **AI:** 0 explicit AI TCs
- **Missing detail:** Sign out option visibility, session termination, redirect to login


#### Admin Forgot Password (Web)


- **Manual:** 22 manual TCs (separate from mobile)
- **AI:** Covered only via generic story 330
- **Missing detail:** Web-specific admin recovery UI elements


#### League Admin Web Module


- **Manual:** Web league management sheets in Sprint 2
- **AI:** Minimal
- **Missing detail:** Members/teams tab, trading activity admin view, league settings, categories, buy-in transactions at admin level


### Moderate Gaps


- Negative test depth — Manual: 605 negative cases vs AI: 12 negative


- Boundary/edge cases — Manual includes explicit boundary TCs; AI has 6 boundary + 2 edge


- Dev/QA status tracking — Manual sheets include DevAssignee, DevStatus, QA Comments; AI cases lack execution history linkage


- Preconditions — Manual often specifies device/browser/admin role preconditions; AI preconditions are generic


- Step granularity — Manual avg ~5-8 detailed UI steps; AI avg 7 steps but more abstract (agent-interpretable)


- Sprint scope annotations — Manual marks out-of-scope items; AI generates all BRD stories uniformly


## Sprint 1 Detailed Comparison

| Manual Sheet | TCs | Mapped Area | AI TCs in Area |
| --- | --- | --- | --- |
| User story -1.3 Force Password  | 79 | Sprint 1 — Web Admin User Management | 27 |
| User story-1.1 User Account Adm | 77 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.8 Internal Admin  | 74 | Sprint 1 — Web Admin Staff & Settings | 11 |
| User story -1.1 User Registrati | 60 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User story -1.6 Account Deletio | 59 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User story -1.5 My Profile (Uni | 51 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User story -1.3 Forgot Password | 41 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User story -1.11 Modify Admin R | 38 | Sprint 1 — Web Admin Staff & Settings | 11 |
| User story -1.10 Deactivate Adm | 34 | Sprint 1 — Web Admin Staff & Settings | 11 |
| User story -1.2 User Login | 32 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User Story -1.8 Account Securit | 30 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User story -1.4 Change Password | 26 | Sprint 1 — Mobile User Auth & Profile | 53 |
| User story -1.6 Override Verifi | 26 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.7 Merge Duplicate | 26 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.12  Admin & Staff | 24 | Sprint 1 — Web Admin Staff & Settings | 11 |
| User story -1.4 Suspend User (A | 23 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.5 BAN User | 23 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.2  Unlock Account | 22 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.13 Forgot Passwor | 21 | Sprint 1 — Web Admin Staff & Settings | 11 |
| User story -1.9 Admin Soft Dele | 16 | Sprint 1 — Web Admin User Management | 27 |
| User story -1.7 User Logout | 7 | Sprint 1 — Mobile User Auth & Profile | 53 |

### Sprint 1 — Sheet-by-Sheet Notes


#### User story -1.1 User Registrati (60 manual TCs)


AI stories 326+328 cover AC-level registration but miss 80%+ of UI cases (logo, hyperlink, field placeholders, keyboard type, screen transitions).


#### User story -1.2 User Login (32 manual TCs)


Strong overlap on happy path; manual adds invalid credential matrix, UI layout, inactive/suspended user blocking.


#### User story -1.3 Forgot Password (41 manual TCs)


AI story 330 aligns well on core flow; manual adds device-specific UI validation.


#### User story -1.4 Change Password (26 manual TCs)


Largely missing from AI as dedicated flow.


#### User story -1.5 My Profile (Uni (51 manual TCs)


Good conceptual overlap with AI 331; manual deeply tests every profile screen element.


#### User story -1.6 Account Deletio (59 manual TCs)


Not covered by AI for mobile user-initiated deletion.


#### User story -1.7 User Logout (7 manual TCs)


Not covered by AI.


#### User Story -1.8 Account Securit (30 manual TCs)


Partial overlap with AI 329 (2FA); manual adds suspended user negative paths.


#### User story-1.1 User Account Adm (77 manual TCs)


Overlaps AI 334; manual has 78 TCs on filters, columns, pagination vs AI 7.


#### User story -1.2  Unlock Account (22 manual TCs)


Overlaps AI 335; many manual TCs marked out-of-scope.


#### User story -1.3 Force Password  (79 manual TCs)


Overlaps AI 336; manual more granular on popup UX.


#### User story -1.4 Suspend User (A (23 manual TCs)


Overlaps AI 335 suspend cases.


#### User story -1.5 BAN User (23 manual TCs)


Overlaps AI 335 ban cases.


#### User story -1.6 Override Verifi (26 manual TCs)


NOT in AI.


#### User story -1.7 Merge Duplicate (26 manual TCs)


NOT in AI.


#### User story -1.8 Internal Admin  (74 manual TCs)


Overlaps AI 332.


#### User story -1.9 Admin Soft Dele (16 manual TCs)


Overlaps AI 336.


#### User story -1.10 Deactivate Adm (34 manual TCs)


Overlaps AI 332.


#### User story -1.11 Modify Admin R (38 manual TCs)


Overlaps AI 332.


#### User story -1.12  Admin & Staff (24 manual TCs)


Overlaps AI 333.


#### User story -1.13 Forgot Passwor (21 manual TCs)


Web admin variant; partial AI overlap via 330.


## Sprint 2 Detailed Comparison

| Manual Sheet | TCs | Area | AI TCs | Gap |
| --- | --- | --- | --- | --- |
| User story -1.3 Leagues Dashboa | 452 | Sprint 2 — Leagues (Mobile) | 22 | 430 |
| Web-User Story -1.1 Public Leag | 127 | Sprint 2 — Leagues (Web Admin) | 27 | 100 |
| User story -1.6 Create Private  | 126 | Sprint 2 — Leagues (Mobile) | 22 | 104 |
| User story -1.5 League Settings | 108 | Sprint 2 — Leagues (Web Admin) | 27 | 81 |
| User story -2.1 Packages (Confi | 108 | Sprint 2 — Wallet & Economy | 25 | 83 |
| User Story -1.2 Leagues Module  | 98 | Sprint 2 — Leagues (Web Admin) | 27 | 71 |
| User story - 1.4 Leagues - “Pub | 97 | Sprint 2 — Leagues (Mobile) | 22 | 75 |
| User story -1.3 Members Teams T | 94 | Sprint 2 — Leagues (Web Admin) | 27 | 67 |
| User story -1.5 Leagues - “Invi | 90 | Sprint 2 — Leagues (Mobile) | 22 | 68 |
| User story - 1.9 “Private Leagu | 78 | Sprint 2 — Leagues (Mobile) | 22 | 56 |
| User story -1.4 Trading Activit | 78 | Sprint 2 — Leagues (Web Admin) | 27 | 51 |
| User story -1.8  Leagues - “Cre | 76 | Sprint 2 — Leagues (Mobile) | 22 | 54 |
| User Story -2.9 Admin View of E | 62 | Sprint 2 — Wallet & Economy | 25 | 37 |
| User story -1.2  Leagues - “My  | 61 | Unmapped | 0 | 61 |
| User story -2.2  Managing Start | 56 | Sprint 2 — Wallet & Economy | 25 | 31 |
| User story -1.7 The Three Invit | 42 | Sprint 2 — Leagues (Mobile) | 22 | 20 |
| User story -1.6 Categories Unde | 36 | Sprint 2 — Leagues (Web Admin) | 27 | 9 |
| User story -2.5  End-of-Season  | 35 | Sprint 2 — Wallet & Economy | 25 | 10 |
| User story -2.8 End-of-Season S | 34 | Sprint 2 — Wallet & Economy | 25 | 9 |
| User story -2.4 View Transactio | 33 | Sprint 2 — Wallet & Economy | 25 | 8 |
| User story -2.3 Edit Buy-In con | 33 | Sprint 2 — Wallet & Economy | 25 | 8 |
| User Story -1.1 Post Login Leag | 30 | Sprint 2 — Leagues (Mobile) | 22 | 8 |
| User story -2.3 League Wallet ( | 29 | Sprint 2 — Wallet & Economy | 25 | 4 |
| User story -2.1 User Wallet (Ma | 21 | Sprint 2 — Wallet & Economy | 25 | -4 |
| User story -2.7 Set League Buy- | 21 | Sprint 2 — Wallet & Economy | 25 | -4 |
| User story -2.6 Reconciliation  | 13 | Sprint 2 — Wallet & Economy | 25 | -12 |
| User story -2.5 Adjust User Bal | 8 | Sprint 2 — Wallet & Economy | 25 | -17 |
| User story -2.2  View All Trans | 1 | Sprint 2 — Wallet & Economy | 25 | -24 |

**Sprint 2 dominates manual volume:** 2,047 of 2,836 total manual cases (72.2%). The AI suite allocates only **47 cases** to league/economy stories — a **44× gap** in volume.


## AI-Only Coverage (Not in Manual Sprints)


### Story 326: As a Super Admin, I can configure legal compliance settings so that F2MX operates within US regulati


**AI test cases:** 9 | **Priority:** critical | **Source:** brd_generated

| TC# | Title | Type | AC Ref |
| --- | --- | --- | --- |
| 1 | Verify registration prevented for users under 18 | positive | AC-1 |
| 2 | Verify registration rejected with future Date of Birth | negative | AC-1 |
| 3 | Verify registration rejected with malformed Date of Birth | negative | AC-1 |
| 4 | Verify explicit consent for Terms of Service allows registration progr | positive | AC-2 |
| 5 | Verify timestamp logging for Privacy Policy consent | positive | AC-3 |
| 6 | Verify timestamp logging for all legal consent actions | positive | AC-4 |
| 7 | Verify IP address logging for all legal consent actions | positive | AC-5 |
| 8 | Verify publicly accessible URL for Terms of Service document | positive | AC-6 |
| 9 | Verify publicly accessible URL for Privacy Policy document | positive | AC-7 |

### Story 327: As a Super Admin, I can manage app store configurations so that F2MX is available and monetizable on


**AI test cases:** 6 | **Priority:** critical | **Source:** brd_generated

| TC# | Title | Type | AC Ref |
| --- | --- | --- | --- |
| 10 | Verify Super Admin can successfully configure organization accounts fo | positive | AC-1 |
| 11 | Verify Super Admin can successfully define a new In-App Purchase (IAP) | positive | AC-2 |
| 12 | Verify Super Admin can successfully manage (edit) an existing In-App P | positive | AC-3 |
| 13 | Verify Super Admin can successfully link to an App Store developer acc | positive | AC-4 |
| 14 | Verify Super Admin can successfully link to a Google Play developer ac | positive | AC-5 |
| 15 | Verify Super Admin can successfully manage app metadata and submission | positive | AC-6 |

### Story 344: As a User, I can receive important account and league notifications so that I stay informed about my


**AI test cases:** 5 | **Priority:** high | **Source:** brd_generated

| TC# | Title | Type | AC Ref |
| --- | --- | --- | --- |
| 145 | Verify email confirmation sent on successful password change | positive | AC-1 |
| 146 | Verify notification sent on account status change to suspended | positive | AC-2 |
| 147 | Verify push notification sent for league matchup update | positive | AC-3 |
| 148 | Verify in-app message displayed for critical system alert | positive | AC-4 |
| 149 | Verify user can toggle push notification preference | positive | AC-5 |

### Story 345: As an Ops Admin, I can send targeted messages and emergency broadcasts so that I can communicate cri


**AI test cases:** 6 | **Priority:** high | **Source:** brd_generated

| TC# | Title | Type | AC Ref |
| --- | --- | --- | --- |
| 150 | Verify Ops Admin can send targeted message to a specific user | positive | AC-1 |
| 151 | Verify Ops Admin can send emergency broadcast to all users | positive | AC-2 |
| 152 | Verify targeted message requires a valid reason code | positive | AC-3 |
| 153 | Verify emergency broadcast requires a valid reason code | positive | AC-4 |
| 154 | Verify system logs all sent communications | positive | AC-5 |
| 155 | Verify Ops Admin can enable/disable reminder timing offsets | positive | AC-6 |

## Manual-Only Coverage (Missing from AI)


### Features With Zero AI Representation


- ❌ **Override Verification (Support/Ops/Super Admin)**


- ❌ **Merge Duplicate Accounts**


- ❌ **Mobile User Logout**


- ❌ **Mobile User Account Deletion (self-service)**


- ❌ **Private League Creation wizard**


- ❌ **League Invitation methods (Link/QR/In-App)**


- ❌ **Three Invitation Methods & user Joining**


- ❌ **User Wallet (Mobile) — view balance, transactions**


- ❌ **League Wallet**


- ❌ **View All Transactions**


- ❌ **End-of-Season settlement flows**


- ❌ **Packages configuration**


- ❌ **Issue Promotions**


- ❌ **Adjust User Balance (admin)**


- ❌ **Reconciliation**


- ❌ **Set League Buy-In (admin)**


- ❌ **Admin View of End-of-Season**


### Top 25 Manual Sheets by Volume — AI Coverage Gap

| Sheet | Manual | AI (area) | Gap | Area |
| --- | --- | --- | --- | --- |
| User story -1.3 Leagues Dashboa | 452 | 22 | 430 | Sprint 2 — Leagues (Mobile) |
| Web-User Story -1.1 Public Leag | 127 | 27 | 100 | Sprint 2 — Leagues (Web Admin) |
| User story -1.6 Create Private  | 126 | 22 | 104 | Sprint 2 — Leagues (Mobile) |
| User story -1.5 League Settings | 108 | 27 | 81 | Sprint 2 — Leagues (Web Admin) |
| User story -2.1 Packages (Confi | 108 | 25 | 83 | Sprint 2 — Wallet & Economy |
| User Story -1.2 Leagues Module  | 98 | 27 | 71 | Sprint 2 — Leagues (Web Admin) |
| User story - 1.4 Leagues - “Pub | 97 | 22 | 75 | Sprint 2 — Leagues (Mobile) |
| User story -1.3 Members Teams T | 94 | 27 | 67 | Sprint 2 — Leagues (Web Admin) |
| User story -1.5 Leagues - “Invi | 90 | 22 | 68 | Sprint 2 — Leagues (Mobile) |
| User story -1.3 Force Password  | 79 | 27 | 52 | Sprint 1 — Web Admin User Mana |
| User story - 1.9 “Private Leagu | 78 | 22 | 56 | Sprint 2 — Leagues (Mobile) |
| User story -1.4 Trading Activit | 78 | 27 | 51 | Sprint 2 — Leagues (Web Admin) |
| User story-1.1 User Account Adm | 77 | 27 | 50 | Sprint 1 — Web Admin User Mana |
| User story -1.8  Leagues - “Cre | 76 | 22 | 54 | Sprint 2 — Leagues (Mobile) |
| User story -1.8 Internal Admin  | 74 | 11 | 63 | Sprint 1 — Web Admin Staff & S |
| User Story -2.9 Admin View of E | 62 | 25 | 37 | Sprint 2 — Wallet & Economy |
| User story -1.2  Leagues - “My  | 61 | 0 | 61 | Unmapped |
| User story -1.1 User Registrati | 60 | 53 | 7 | Sprint 1 — Mobile User Auth &  |
| User story -1.6 Account Deletio | 59 | 53 | 6 | Sprint 1 — Mobile User Auth &  |
| User story -2.2  Managing Start | 56 | 25 | 31 | Sprint 2 — Wallet & Economy |
| User story -1.5 My Profile (Uni | 51 | 53 | -2 | Sprint 1 — Mobile User Auth &  |
| User story -1.7 The Three Invit | 42 | 22 | 20 | Sprint 2 — Leagues (Mobile) |
| User story -1.3 Forgot Password | 41 | 53 | -12 | Sprint 1 — Mobile User Auth &  |
| User story -1.11 Modify Admin R | 38 | 11 | 27 | Sprint 1 — Web Admin Staff & S |
| User story -1.6 Categories Unde | 36 | 27 | 9 | Sprint 2 — Leagues (Web Admin) |

## Scenario Type & Priority Analysis


### Manual Test Case Types

| Type | Count |
| --- | --- |
| positive | 2194 |
| negative | 605 |
| league transations | 13 |
| date range | 11 |
| filter | 9 |

### AI Scenario Types

| Scenario Type | Count |
| --- | --- |
| positive | 135 |
| negative | 12 |
| boundary | 6 |
| edge | 2 |

### AI Priority Distribution

| Priority | Count |
| --- | --- |
| high | 94 |
| critical | 55 |
| medium | 6 |

### AI Category Distribution

| Category | Count |
| --- | --- |
| regression | 137 |
| e2e | 17 |
| smoke | 1 |

## Per User Story AI Inventory


### US-326: As a Super Admin, I can configure legal compliance settings so that F2MX operates within U


**Priority:** critical | **Status:** open | **AI cases:** 9


**Acceptance Criteria (preview):** 1. The system prevents registration for users under 18 based on DOB input, displaying a specific error message. 2. The system requires explicit user consent for Terms of Service and Privacy Policy before registration. 3. The system logs timestamps and IP addresses for all legal consent actions. 4. The system provides publicly accessible URLs for Terms of Service and Privacy Policy documents.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 1 | Verify registration prevented for users under 18 | positive | critical | AC-1 | 8 |
| 2 | Verify registration rejected with future Date of Birth | negative | high | AC-1 | 10 |
| 3 | Verify registration rejected with malformed Date of Birth | negative | high | AC-1 | 10 |
| 4 | Verify explicit consent for Terms of Service allows registration  | positive | critical | AC-2 | 7 |
| 5 | Verify timestamp logging for Privacy Policy consent | positive | high | AC-3 | 9 |
| 6 | Verify timestamp logging for all legal consent actions | positive | high | AC-4 | 9 |
| 7 | Verify IP address logging for all legal consent actions | positive | high | AC-5 | 9 |
| 8 | Verify publicly accessible URL for Terms of Service document | positive | high | AC-6 | 4 |
| 9 | Verify publicly accessible URL for Privacy Policy document | positive | high | AC-7 | 4 |

### US-327: As a Super Admin, I can manage app store configurations so that F2MX is available and mone


**Priority:** critical | **Status:** open | **AI cases:** 6


**Acceptance Criteria (preview):** 1. The system supports configuration of organization accounts (e.g., D-U-N-S) for app store submission. 2. The system allows definition and management of In-App Purchase (IAP) products. 3. The system enables linking to App Store and Google Play developer accounts. 4. The system provides tools to manage app metadata and submission details.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 10 | Verify Super Admin can successfully configure organization accoun | positive | critical | AC-1 | 6 |
| 11 | Verify Super Admin can successfully define a new In-App Purchase  | positive | critical | AC-2 | 10 |
| 12 | Verify Super Admin can successfully manage (edit) an existing In- | positive | critical | AC-3 | 8 |
| 13 | Verify Super Admin can successfully link to an App Store develope | positive | critical | AC-4 | 5 |
| 14 | Verify Super Admin can successfully link to a Google Play develop | positive | critical | AC-5 | 5 |
| 15 | Verify Super Admin can successfully manage app metadata and submi | positive | critical | AC-6 | 12 |

### US-328: As a New User, I can create an account and verify my age so that I can access the F2MX pla


**Priority:** critical | **Status:** open | **AI cases:** 12


**Acceptance Criteria (preview):** 1. The system collects Date of Birth (DOB) and blocks registration if the user is under 18 with a specific error message. 2. The system ensures the entered Email and Username are unique before allowing registration. 3. The system validates the Username adheres to specified constraints (max 20 chars, allowed chars, no spaces). 4. The system requires explicit acceptance of Terms of Service and Privacy Policy to proceed with registration. 5. The system assigns a default Global Wallet with 0 balance…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 16 | Verify system collects Date of Birth during registration | positive | critical | AC-1 | 7 |
| 17 | Verify registration proceeds for user aged 18 or older | positive | critical | AC-2 | 10 |
| 18 | Verify registration is blocked for user aged 17 years | negative | critical | AC-2 | 10 |
| 19 | Verify registration is blocked for user aged 1 day old | negative | critical | AC-2 | 8 |
| 20 | Verify system ensures entered Email is unique during registration | positive | critical | AC-3 | 6 |
| 21 | Verify system ensures entered Username is unique during registrat | positive | critical | AC-4 | 8 |
| 22 | Verify Username adheres to specified constraints (valid chars, no | positive | critical | AC-5 | 7 |
| 23 | Verify Username adheres to maximum length constraint (20 characte | boundary | critical | AC-5 | 7 |
| 24 | Verify explicit acceptance of Terms of Service is required for re | positive | critical | AC-6 | 10 |
| 25 | Verify explicit acceptance of Privacy Policy is required for regi | positive | critical | AC-7 | 9 |
| 26 | Verify system assigns default Global Wallet with 0 balance and 0  | positive | critical | AC-8 | 4 |
| 27 | Verify system assigns 'Rookie' Tier status upon successful regist | positive | critical | AC-9 | 3 |

### US-329: As a User, I can securely log in with two-factor authentication so that my account is prot


**Priority:** critical | **Status:** open | **AI cases:** 10


**Acceptance Criteria (preview):** 1. The system only allows registered users with "Active" status to log in. 2. The system prompts for 2FA verification (SMS or Email) after successful username/password validation. 3. The system locks the account for 30 minutes after 3 failed OTP attempts. 4. The system redirects users to a mandatory password change screen if the "Force Password Reset" flag is set. 5. The system logs the Last_Login_Timestamp and IP Address upon successful login.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 28 | Verify successful login for a registered, active user | positive | critical | AC-1 | 6 |
| 29 | Verify system prompts for 2FA after successful username/password  | positive | critical | AC-2 | 6 |
| 30 | Verify account locks for 30 minutes after 3 failed OTP attempts | positive | critical | AC-3 | 10 |
| 31 | Verify account locks after exactly 3 failed OTP attempts | boundary | critical | AC-3 | 9 |
| 32 | Verify redirection to mandatory password change screen when 'Forc | positive | critical | AC-4 | 8 |
| 33 | Verify no redirection to password change when 'Force Password Res | negative | critical | AC-4 | 7 |
| 34 | Verify no redirection to password change if 'Force Password Reset | negative | critical | AC-4 | 7 |
| 35 | Verify Last_Login_Timestamp is logged upon successful login | positive | critical | AC-5 | 8 |
| 36 | Verify IP Address is logged upon successful login | positive | critical | AC-5 | 8 |
| 37 | Successful Login with 2FA and Dashboard Redirection | positive | medium | AC-6 | 9 |

### US-330: As a User, I can recover my password via email so that I can regain access to my account i


**Priority:** high | **Status:** open | **AI cases:** 11


**Acceptance Criteria (preview):** 1. The system sends a secure, time-bound OTP to the registered email address upon request. 2. The system validates the entered OTP and redirects to the Reset Password screen upon success. 3. The system requires the new password to meet complexity requirements (Min 8, Max 15 chars, alphanumeric) and not be identical to the current password. 4. The system displays an error message if the OTP is expired or invalid. 5. The system updates the user's password and redirects to the login screen upon suc…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 38 | Verify system sends OTP to registered email | positive | critical | AC-1 | 4 |
| 39 | Verify system validates correct OTP successfully | positive | high | AC-2 | 5 |
| 40 | Verify redirection to Reset Password screen after successful OTP  | positive | high | AC-3 | 6 |
| 41 | Verify new password meets complexity requirements (8-15 chars, al | positive | high | AC-4 | 12 |
| 42 | Verify new password meets complexity at minimum and maximum chara | boundary | medium | AC-4 | 9 |
| 43 | Verify new password is not identical to current password | positive | high | AC-5 | 5 |
| 44 | Verify system displays error message for expired OTP | positive | high | AC-6 | 4 |
| 45 | Verify system displays error message for invalid OTP | negative | high | AC-6 | 5 |
| 46 | Verify system displays error message for OTP with incorrect forma | negative | medium | AC-6 | 3 |
| 47 | Verify user's password is updated successfully | positive | critical | AC-7 | 3 |
| 48 | Verify redirection to login screen upon successful password reset | positive | high | AC-8 | 6 |

### US-331: As a Logged-In User, I can set up my profile and avatar so that I have a consistent identi


**Priority:** high | **Status:** open | **AI cases:** 11


**Acceptance Criteria (preview):** 1. The system allows users to upload a JPG/PNG avatar (max 5MB) or select from default F2MX avatars. 2. The system immediately updates the user's avatar across all historical and active leagues upon change. 3. The system allows editing of First Name, Last Name, Username, and Bio, with Username requiring uniqueness validation. 4. The system displays read-only fields for Email, Phone, DOB, XP Points, and Tier Badge. 5. The system prevents updating the profile if mandatory fields are empty or valid…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 49 | Verify user can upload a valid JPG avatar within size limit | positive | high | AC-1 | 5 |
| 50 | Verify avatar upload succeeds with a 5MB JPG file | boundary | high | AC-1 | 9 |
| 51 | Verify avatar updates immediately across historical leagues | positive | high | AC-2 | 7 |
| 52 | Verify avatar updates immediately across active leagues | positive | high | AC-3 | 7 |
| 53 | Verify user can edit First Name, Last Name, and Username | positive | high | AC-4 | 8 |
| 54 | Verify user can edit Bio and update Username with unique value | positive | high | AC-5 | 6 |
| 55 | Verify Email, Phone, DOB, XP, and Tier Badge fields are read-only | positive | high | AC-6 | 6 |
| 56 | Verify profile updates successfully when all mandatory fields are | positive | high | AC-7 | 8 |
| 57 | Verify profile update fails when a mandatory field (First Name) i | negative | high | AC-7 | 4 |
| 58 | Verify profile update fails when Username is not unique | negative | high | AC-7 | 6 |
| 59 | Verify system handles null input for a mandatory field (Username) | edge | high | AC-7 | 5 |

### US-332: As a Super Admin, I can create and manage internal staff accounts and their roles so that 


**Priority:** critical | **Status:** open | **AI cases:** 6


**Acceptance Criteria (preview):** 1. The system allows Super Admins to create new staff accounts by providing email, name, phone number, and assigning a role. 2. The system sends a time-bound, single-use activation link to the new staff member's email for password setup. 3. The system sets the new staff account status to "PENDING_ACTIVATION" until the password is set. 4. The system allows Super Admins to toggle an admin account's status between "Active" and "Inactive", immediately revoking access if set to Inactive. 5. The syste…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 60 | Verify Super Admin can create new staff account with valid detail | positive | high | AC-1 | 9 |
| 61 | Verify activation link is sent to new staff member's email | positive | high | AC-2 | 10 |
| 62 | Verify new staff account status is PENDING_ACTIVATION | positive | high | AC-3 | 7 |
| 63 | Verify Super Admin can set staff account status to Active | positive | high | AC-4 | 5 |
| 64 | Verify Super Admin can set staff account status to Inactive and r | positive | critical | AC-5 | 9 |
| 65 | Verify Super Admin can modify an existing staff member's role | positive | high | AC-6 | 6 |

### US-333: As an F2MX Staff Member, I can securely log in to the Admin Console so that I can perform 


**Priority:** critical | **Status:** open | **AI cases:** 5


**Acceptance Criteria (preview):** 1. The system requires staff members to enter registered email/username and password for login. 2. The system enforces 2FA verification (Email or Phone) for all staff logins. 3. The system automatically routes the staff member to the F2MX Admin Console upon successful authentication. 4. The system blocks login attempts for staff accounts with "Inactive" or "Deactivated" status. 5. The system provides a logout option that redirects the staff member to the login screen.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 66 | Verify successful login with valid registered email and password | positive | critical | AC-1 | 6 |
| 67 | Verify 2FA enforcement after successful credential entry | positive | critical | AC-2 | 8 |
| 68 | Verify automatic routing to Admin Console upon full successful au | positive | critical | AC-3 | 8 |
| 69 | Verify login attempt is blocked for an inactive staff account | positive | critical | AC-4 | 6 |
| 70 | Verify logout option redirects to the login screen | positive | critical | AC-5 | 8 |

### US-334: As an F2MX Admin, I can view and filter user accounts so that I can efficiently manage pla


**Priority:** high | **Status:** open | **AI cases:** 7


**Acceptance Criteria (preview):** 1. The system displays all registered user accounts in a searchable and filterable list within the Admin Console. 2. The system allows searching by Username, Email, or Phone Number with partial, exact, and case-insensitive matching. 3. The system provides filters for Account Status (Active, Banned, Suspended, Locked, Deleted), Verification Status, Tier, and Joined Date range. 4. The system displays key user details including User_ID, Username, Email, Status, Verification, Tier, XP Points, Wallet…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 71 | Verify all registered user accounts are displayed in a searchable | positive | critical | AC-1 | 4 |
| 72 | Verify user accounts list is filterable within the Admin Console | positive | critical | AC-2 | 7 |
| 73 | Verify search by Username, Email, or Phone Number with partial an | positive | high | AC-3 | 12 |
| 74 | Verify search by Username, Email, or Phone Number supports case-i | positive | high | AC-4 | 12 |
| 75 | Verify filters for Account Status, Verification Status, Tier, and | positive | high | AC-5 | 12 |
| 76 | Verify all required key user details are displayed for each accou | positive | critical | AC-6 | 9 |
| 77 | Verify pagination controls function correctly for large user list | positive | high | AC-7 | 6 |

### US-335: As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so that I can 


**Priority:** critical | **Status:** open | **AI cases:** 10


**Acceptance Criteria (preview):** 1. The system allows Support, Ops, and Super Admins to unlock accounts that were automatically locked due to failed login attempts. 2. The system allows Ops and Super Admins to suspend a user account for a defined duration (e.g., 24 hours, 7 days, custom). 3. The system allows Ops and Super Admins to permanently ban a user account. 4. The system immediately logs out the user and blocks login access upon suspension or ban. 5. Every status change action requires a reason and is recorded in the aud…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 78 | Verify Support Admin can unlock a locked user account | positive | high | AC-1 | 5 |
| 79 | Verify Super Admin can unlock a locked user account | positive | high | AC-2 | 6 |
| 80 | Verify Ops Admin can suspend a user account for a defined duratio | positive | high | AC-3 | 8 |
| 81 | Verify Super Admin can suspend a user account for a custom durati | positive | high | AC-4 | 9 |
| 82 | Verify Super Admin can suspend a user account for minimum allowed | boundary | high | AC-4 | 9 |
| 83 | Verify Super Admin can permanently ban a user account | positive | high | AC-5 | 8 |
| 84 | Verify active user is immediately logged out upon account suspens | positive | high | AC-6 | 9 |
| 85 | Verify suspended user is blocked from logging in | positive | high | AC-7 | 6 |
| 86 | Verify account status change requires a reason | positive | high | AC-8 | 9 |
| 87 | Verify audit log records all required details for account status  | positive | high | AC-9 | 9 |

### US-336: As an F2MX Admin, I can force password resets and soft delete user accounts so that I can 


**Priority:** high | **Status:** open | **AI cases:** 10


**Acceptance Criteria (preview):** 1. The system allows Support, Ops, and Super Admins to force a password reset on a user account. 2. The system redirects the user to a mandatory password change screen on their next login attempt after a force reset. 3. The system allows Support, Ops, and Super Admins to initiate a soft delete of a user account. 4. The system marks the deleted user record as "Deleted" and anonymizes PII (Email, Name) while preserving historical data integrity. 5. All force password reset and soft delete actions …

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 88 | Verify Support Admin can force password reset for a user | positive | high | AC-1 | 7 |
| 89 | Verify Super Admin can force password reset for a user | positive | high | AC-2 | 6 |
| 90 | Verify user is redirected to mandatory password change after forc | positive | high | AC-3 | 9 |
| 91 | Verify user cannot bypass mandatory password change after force r | negative | high | AC-3 | 5 |
| 92 | Verify mandatory password change rejects invalid new password | negative | high | AC-3 | 6 |
| 93 | Verify Super Admin can initiate soft delete of a user account | positive | high | AC-4 | 7 |
| 94 | Verify soft deleted user record is marked as 'Deleted' | positive | high | AC-5 | 3 |
| 95 | Verify PII anonymization and historical data integrity after soft | positive | high | AC-6 | 11 |
| 96 | Verify force password reset actions require a reason and are audi | positive | high | AC-7 | 11 |
| 97 | Verify soft delete actions require a reason and are audit logged | positive | high | AC-8 | 9 |

### US-337: As a User, I can view and manage my active, upcoming, and completed leagues so that I can 


**Priority:** critical | **Status:** open | **AI cases:** 8


**Acceptance Criteria (preview):** 1. The system redirects the user to the Mobile Leagues module upon successful login. 2. The system displays counts for "Total Active Leagues," "Total Upcoming Leagues," and "Total Completed Leagues." 3. The system allows users to filter their "My Leagues" list by selecting Active, Upcoming, or Completed leagues from the overview section. 4. The system displays each league as a card with its status, name, type, and other relevant information. 5. The system displays an empty state message with act…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 98 | Verify user is redirected to Mobile Leagues module after successf | positive | critical | AC-1 | 6 |
| 99 | Verify display of Total Active and Upcoming Leagues counts | positive | high | AC-2 | 4 |
| 100 | Verify display of Total Completed Leagues count | positive | high | AC-3 | 2 |
| 101 | Verify filtering 'My Leagues' list by Active status | positive | high | AC-4 | 6 |
| 102 | Verify league card displays status, name, and type | positive | medium | AC-5 | 5 |
| 103 | Verify league card displays other relevant information | positive | medium | AC-6 | 5 |
| 104 | Verify empty state message and action buttons for user with no le | positive | high | AC-7 | 5 |
| 105 | Verify empty state message when user's league data is null or emp | edge | high | AC-7 | 4 |

### US-338: As a User, I can access a detailed League Dashboard so that I can view matchups, history, 


**Priority:** high | **Status:** open | **AI cases:** 9


**Acceptance Criteria (preview):** 1. The system navigates to the League Dashboard (Matchup view) when a user taps a League Card. 2. The system displays the current week's head-to-head matchup, including user and opponent avatars, team names, live scores, and projected finals. 3. The system allows navigation between past, current, and future weeks within the Matchup view, dynamically loading relevant data. 4. The system provides a "History" module displaying finalized weekly matchups, results (WIN/LOSS/TIE), and player trade hist…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 106 | Verify navigation to League Dashboard from League Card | positive | critical | AC-1 | 5 |
| 107 | Verify current week's matchup displays user's team details | positive | high | AC-2 | 5 |
| 108 | Verify current week's matchup displays opponent details | positive | high | AC-3 | 4 |
| 109 | Verify navigation to past and current weeks in Matchup view | positive | high | AC-4 | 8 |
| 110 | Verify navigation to future weeks in Matchup view | positive | high | AC-5 | 8 |
| 111 | Verify History module displays finalized weekly matchups and resu | positive | high | AC-6 | 4 |
| 112 | Verify History module displays player trade history with P&L | positive | high | AC-7 | 4 |
| 113 | Verify Standings module displays ranked teams by W-L-T records | positive | high | AC-8 | 10 |
| 114 | Verify Standings module applies tie-breakers and highlights curre | positive | high | AC-9 | 5 |

### US-339: As a User, I can browse and join public leagues so that I can easily find new competitions


**Priority:** medium | **Status:** open | **AI cases:** 5


**Acceptance Criteria (preview):** 1. The system displays a "Public Leagues" category on the Leagues module. 2. The system lists available public leagues with relevant details (e.g., league name, size, status). 3. The system allows a user to join an open public league. 4. The system updates the user's "My Leagues" list upon successfully joining a public league. 5. The system prevents a user from joining a public league that is full or has already started.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 115 | Verify 'Public Leagues' category is displayed on Leagues module | positive | high | AC-1 | 2 |
| 116 | Verify available public leagues are listed with correct details | positive | high | AC-2 | 5 |
| 117 | Verify user can successfully join an open public league | positive | critical | AC-3 | 5 |
| 118 | Verify 'My Leagues' list updates after joining a public league | positive | high | AC-4 | 2 |
| 119 | Verify system prevents joining a full or started public league | positive | high | AC-5 | 5 |

### US-340: As a User, I can view real-time player market prices and trade player shares so that I can


**Priority:** critical | **Status:** open | **AI cases:** 7


**Acceptance Criteria (preview):** 1. The system displays a continuously scrolling ticker showcasing real-time player name and current value changes (green for positive, red for negative). 2. The system updates player values in the ticker at defined intervals (e.g., 45 seconds). 3. The system allows users to buy shares of available players. 4. The system allows users to sell shares of players they own. 5. The system prevents "slippage trades" by ensuring trades execute at the displayed global price.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 120 | Verify continuously scrolling ticker displays real-time player na | positive | high | AC-1 | 4 |
| 121 | Verify player value changes are correctly color-coded in the tick | positive | high | AC-2 | 5 |
| 122 | Verify player values in the ticker update at the defined interval | positive | high | AC-3 | 7 |
| 123 | Verify ticker updates precisely at the 45-second interval boundar | boundary | high | AC-3 | 5 |
| 124 | Verify user can successfully buy shares of an available player | positive | critical | AC-4 | 5 |
| 125 | Verify user can successfully sell shares of a player they own | positive | critical | AC-5 | 9 |
| 126 | Verify trades execute at the exact displayed global price, preven | positive | critical | AC-6 | 10 |

### US-341: As an Ops Admin, I can configure market pricing parameters so that I can manage the platfo


**Priority:** high | **Status:** open | **AI cases:** 5


**Acceptance Criteria (preview):** 1. The system allows Ops Admins to adjust pricing weights for player valuations. 2. The system allows Ops Admins to configure the bid/ask spread for player shares. 3. The system allows Ops Admins to set platform market opening dates. 4. The system applies configured market parameters globally and in real-time. 5. All changes to market parameters are recorded in the audit log with Admin_ID, Action_Type, Timestamp, and Reason.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 127 | Verify Ops Admin can adjust player valuation pricing weights | positive | high | AC-1 | 8 |
| 128 | Verify Ops Admin can configure bid/ask spread for player shares | positive | high | AC-2 | 6 |
| 129 | Verify Ops Admin can set platform market opening dates | positive | high | AC-3 | 5 |
| 130 | Verify configured market parameters apply globally and in real-ti | positive | critical | AC-4 | 10 |
| 131 | Verify market parameter changes are recorded in audit log | positive | high | AC-5 | 6 |

### US-342: As a User, I can earn XP and progress through tiers so that I am rewarded for my platform 


**Priority:** high | **Status:** open | **AI cases:** 7


**Acceptance Criteria (preview):** 1. The system awards XP points to users based on their performance in leagues. 2. The system tracks a user's total XP and assigns them to a corresponding tier (e.g., Rookie, Amateur, Pro). 3. The system displays the user's current XP points and tier status on their profile. 4. The system automatically updates the user's tier when they accumulate enough XP for the next level. 5. The system uses XP gating to control access to certain leagues or features.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 132 | Verify XP points are awarded for league performance | positive | high | AC-1 | 6 |
| 133 | Verify system accurately tracks user's total XP | positive | high | AC-2 | 8 |
| 134 | Verify user is assigned to the correct tier based on XP | positive | high | AC-3 | 3 |
| 135 | Verify user's current XP points are displayed on profile | positive | high | AC-4 | 3 |
| 136 | Verify user's current tier status is displayed on profile | positive | high | AC-5 | 3 |
| 137 | Verify automatic tier update upon reaching next XP threshold | positive | critical | AC-6 | 7 |
| 138 | Verify XP gating grants access to a restricted league/feature | positive | high | AC-7 | 6 |

### US-343: As an Ops Admin, I can configure XP award parameters and ensure consistent Half-PPR scorin


**Priority:** high | **Status:** open | **AI cases:** 6


**Acceptance Criteria (preview):** 1. The system allows Ops Admins to configure the parameter ranges for XP awards. 2. The system allows Ops Admins to configure XP rank levels and tier definitions. 3. The system automatically applies fixed Half-PPR scoring rules for all player performances in leagues. 4. The system ensures that all scoring calculations are consistent and accurate across all leagues. 5. All changes to XP configuration parameters are recorded in the audit log.…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 139 | Verify Ops Admin can configure XP award parameter ranges | positive | high | AC-1 | 4 |
| 140 | Verify Ops Admin can configure XP rank levels and tier definition | positive | high | AC-2 | 11 |
| 141 | Verify system automatically applies Half-PPR scoring rules | positive | critical | AC-3 | 8 |
| 142 | Verify scoring calculations are consistent across leagues | positive | critical | AC-4 | 12 |
| 143 | Verify scoring calculations are accurate across all leagues | positive | critical | AC-5 | 10 |
| 144 | Verify XP configuration changes are recorded in the audit log | positive | high | AC-6 | 5 |

### US-344: As a User, I can receive important account and league notifications so that I stay informe


**Priority:** high | **Status:** open | **AI cases:** 5


**Acceptance Criteria (preview):** 1. The system sends an email confirmation to the user upon successful password change. 2. The system sends notifications to the user if their account status changes (e.g., suspended, banned, deleted). 3. The system sends push notifications for relevant league activities (e.g., matchup updates, trade confirmations). 4. The system displays in-app messages for critical alerts or information. 5. The system provides a mechanism for users to manage their notification preferences (e.g., toggle push not…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 145 | Verify email confirmation sent on successful password change | positive | critical | AC-1 | 9 |
| 146 | Verify notification sent on account status change to suspended | positive | critical | AC-2 | 9 |
| 147 | Verify push notification sent for league matchup update | positive | high | AC-3 | 5 |
| 148 | Verify in-app message displayed for critical system alert | positive | critical | AC-4 | 5 |
| 149 | Verify user can toggle push notification preference | positive | high | AC-5 | 9 |

### US-345: As an Ops Admin, I can send targeted messages and emergency broadcasts so that I can commu


**Priority:** high | **Status:** open | **AI cases:** 6


**Acceptance Criteria (preview):** 1. The system allows Ops Admins to send targeted messages to specific users or league-level groups. 2. The system allows Ops Admins to send emergency broadcast messages (in-app banner + push notifications) to all users. 3. The system requires a reason code for all targeted and emergency communications. 4. The system logs all sent communications, including Admin_ID, message content, target audience, and timestamp. 5. The system allows Ops Admins to enable/disable reminder timing offsets for commu…

| TC# | Title | Scenario | Priority | AC | Steps |
| --- | --- | --- | --- | --- | --- |
| 150 | Verify Ops Admin can send targeted message to a specific user | positive | high | AC-1 | 8 |
| 151 | Verify Ops Admin can send emergency broadcast to all users | positive | critical | AC-2 | 7 |
| 152 | Verify targeted message requires a valid reason code | positive | high | AC-3 | 8 |
| 153 | Verify emergency broadcast requires a valid reason code | positive | high | AC-4 | 9 |
| 154 | Verify system logs all sent communications | positive | high | AC-5 | 7 |
| 155 | Verify Ops Admin can enable/disable reminder timing offsets | positive | medium | AC-6 | 16 |

## Recommendations


### 1. Expand Sprint 2 AI generation


Run bulk generation on league/wallet user stories with `comprehensive` profile; add dedicated stories for private leagues, invitations, wallet.


### 2. Add missing user stories to BRD pipeline


Override Verification, Merge Duplicate Accounts, Mobile Delete Account, User Logout, Wallet modules.


### 3. Import manual TCs as baseline


CSV import high-priority manual cases (smoke/regression) to supplement AI gaps.


### 4. UI-level test tier


Keep AI for AC/functional coverage; use manual suite for UI/UX and permission matrix.


### 5. Map external keys


Link manual sheets to `user_stories.external_key` for traceability.


### 6. Coverage gates


Require ≥80% manual smoke subset covered before marking AI generation complete.


### 7. Platform tags


Add `platform: mobile|web|both` to AI test cases — manual suite clearly separates these.


### 8. Re-generate with gap-fill


Use coverage validator against manual topic buckets, not just AC matrix.


## Appendix A — Manual Sheet Inventory

| Sprint | Sheet | TCs | Area |
| --- | --- | --- | --- |
| S2 | User story -1.3 Leagues Dashboa | 452 | Sprint 2 — Leagues (Mobile) |
| S2 | Web-User Story -1.1 Public Leag | 127 | Sprint 2 — Leagues (Web Admin) |
| S2 | User story -1.6 Create Private  | 126 | Sprint 2 — Leagues (Mobile) |
| S2 | User story -1.5 League Settings | 108 | Sprint 2 — Leagues (Web Admin) |
| S2 | User story -2.1 Packages (Confi | 108 | Sprint 2 — Wallet & Economy |
| S2 | User Story -1.2 Leagues Module  | 98 | Sprint 2 — Leagues (Web Admin) |
| S2 | User story - 1.4 Leagues - “Pub | 97 | Sprint 2 — Leagues (Mobile) |
| S2 | User story -1.3 Members Teams T | 94 | Sprint 2 — Leagues (Web Admin) |
| S2 | User story -1.5 Leagues - “Invi | 90 | Sprint 2 — Leagues (Mobile) |
| S1 | User story -1.3 Force Password  | 79 | Sprint 1 — Web Admin User Management |
| S2 | User story - 1.9 “Private Leagu | 78 | Sprint 2 — Leagues (Mobile) |
| S2 | User story -1.4 Trading Activit | 78 | Sprint 2 — Leagues (Web Admin) |
| S1 | User story-1.1 User Account Adm | 77 | Sprint 1 — Web Admin User Management |
| S2 | User story -1.8  Leagues - “Cre | 76 | Sprint 2 — Leagues (Mobile) |
| S1 | User story -1.8 Internal Admin  | 74 | Sprint 1 — Web Admin Staff & Settings |
| S2 | User Story -2.9 Admin View of E | 62 | Sprint 2 — Wallet & Economy |
| S2 | User story -1.2  Leagues - “My  | 61 | Unmapped |
| S1 | User story -1.1 User Registrati | 60 | Sprint 1 — Mobile User Auth & Profile |
| S1 | User story -1.6 Account Deletio | 59 | Sprint 1 — Mobile User Auth & Profile |
| S2 | User story -2.2  Managing Start | 56 | Sprint 2 — Wallet & Economy |
| S1 | User story -1.5 My Profile (Uni | 51 | Sprint 1 — Mobile User Auth & Profile |
| S2 | User story -1.7 The Three Invit | 42 | Sprint 2 — Leagues (Mobile) |
| S1 | User story -1.3 Forgot Password | 41 | Sprint 1 — Mobile User Auth & Profile |
| S1 | User story -1.11 Modify Admin R | 38 | Sprint 1 — Web Admin Staff & Settings |
| S2 | User story -1.6 Categories Unde | 36 | Sprint 2 — Leagues (Web Admin) |
| S2 | User story -2.5  End-of-Season  | 35 | Sprint 2 — Wallet & Economy |
| S1 | User story -1.10 Deactivate Adm | 34 | Sprint 1 — Web Admin Staff & Settings |
| S2 | User story -2.8 End-of-Season S | 34 | Sprint 2 — Wallet & Economy |
| S2 | User story -2.4 View Transactio | 33 | Sprint 2 — Wallet & Economy |
| S2 | User story -2.3 Edit Buy-In con | 33 | Sprint 2 — Wallet & Economy |
| S1 | User story -1.2 User Login | 32 | Sprint 1 — Mobile User Auth & Profile |
| S1 | User Story -1.8 Account Securit | 30 | Sprint 1 — Mobile User Auth & Profile |
| S2 | User Story -1.1 Post Login Leag | 30 | Sprint 2 — Leagues (Mobile) |
| S2 | User story -2.3 League Wallet ( | 29 | Sprint 2 — Wallet & Economy |
| S1 | User story -1.4 Change Password | 26 | Sprint 1 — Mobile User Auth & Profile |
| S1 | User story -1.6 Override Verifi | 26 | Sprint 1 — Web Admin User Management |
| S1 | User story -1.7 Merge Duplicate | 26 | Sprint 1 — Web Admin User Management |
| S1 | User story -1.12  Admin & Staff | 24 | Sprint 1 — Web Admin Staff & Settings |
| S1 | User story -1.4 Suspend User (A | 23 | Sprint 1 — Web Admin User Management |
| S1 | User story -1.5 BAN User | 23 | Sprint 1 — Web Admin User Management |
| S1 | User story -1.2  Unlock Account | 22 | Sprint 1 — Web Admin User Management |
| S1 | User story -1.13 Forgot Passwor | 21 | Sprint 1 — Web Admin Staff & Settings |
| S2 | User story -2.1 User Wallet (Ma | 21 | Sprint 2 — Wallet & Economy |
| S2 | User story -2.7 Set League Buy- | 21 | Sprint 2 — Wallet & Economy |
| S1 | User story -1.9 Admin Soft Dele | 16 | Sprint 1 — Web Admin User Management |
| S2 | User story -2.6 Reconciliation  | 13 | Sprint 2 — Wallet & Economy |
| S2 | User story -2.5 Adjust User Bal | 8 | Sprint 2 — Wallet & Economy |
| S1 | User story -1.7 User Logout | 7 | Sprint 1 — Mobile User Auth & Profile |
| S2 | User story -2.2  View All Trans | 1 | Sprint 2 — Wallet & Economy |

## Appendix B — Full AI Test Case Catalog


#### TC-1 (ID 558): Verify registration prevented for users under 18


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 8
- **Description:** This test verifies that the system correctly identifies users under 18 based on their Date of Birth (DOB) and prevents their registration, displaying the specified error message as per AC-1. This ensures compliance with age restrictions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration form is displayed with fields for email, pa |
| 2 | fill | Enter a unique email address for registration | The email field displays 'underage@example.com'. |
| 3 | fill | Enter a strong password | The password field displays masked characters. |
| 4 | fill | Re-enter the same password to confirm | The confirm password field displays masked characters. |
| 5 | fill | Enter a date of birth that makes the user under 18 years old | The Date of Birth field displays '01/01/2010'. |
| 6 | click | Click the Register button to submit the form | The system attempts to process the registration. |
| 7 | assert_text | Verify that an error message indicating age restriction is d | The error message 'You must be at least 18 years old to regi |
| 8 | assert_url | Verify that the user remains on the registration page | The browser URL is still '/register', indicating registratio |

#### TC-2 (ID 559): Verify registration rejected with future Date of Birth


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-1
- **Steps:** 10
- **Description:** This test verifies that the system rejects registration attempts when an invalid Date of Birth (DOB) in the future is provided, ensuring data integrity and preventing illogical age calculations.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user registration page | The registration form is displayed with all required fields |
| 2 | fill | Enter a valid first name | The first name field shows 'Test' |
| 3 | fill | Enter a valid last name | The last name field shows 'User' |
| 4 | fill | Enter a unique and valid email address | The email field shows 'test.user@example.com' |
| 5 | fill | Enter a strong password | The password field shows masked characters |
| 6 | fill | Re-enter the same strong password | The confirm password field shows masked characters |
| 7 | fill | Enter a date in the future for the Date of Birth | The Date of Birth field shows '12/31/2050' |
| 8 | click | Click the Register button to submit the form | The system processes the registration request |
| 9 | assert_text | Verify that an error message indicating an invalid future da | An error message 'Date of Birth cannot be in the future' (or |
| 10 | assert_url | Verify that the user remains on the registration page | The browser URL is still the registration page URL, indicati |

#### TC-3 (ID 560): Verify registration rejected with malformed Date of Birth


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-1
- **Steps:** 10
- **Description:** This test verifies that the system rejects registration attempts when a malformed or non-date string is provided for the Date of Birth (DOB), ensuring proper input validation.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration form is displayed with fields for personal  |
| 2 | fill | Enter a valid first name | The First Name field shows 'John' |
| 3 | fill | Enter a valid last name | The Last Name field shows 'Doe' |
| 4 | fill | Enter a valid email address | The Email field shows 'john.doe@example.com' |
| 5 | fill | Enter a strong password | The Password field shows masked characters |
| 6 | fill | Re-enter the same strong password | The Confirm Password field shows masked characters |
| 7 | fill | Enter a malformed string into the Date of Birth field | The Date of Birth field shows 'not a date' |
| 8 | click | Click the Register button to submit the form | The system attempts to process the registration |
| 9 | assert_text | Verify that an error message indicating invalid date format  | An error message like 'Please enter a valid date' or similar |
| 10 | assert_url | Verify that the user remains on the registration page | The browser URL is still '/register', indicating registratio |

#### TC-4 (ID 561): Verify explicit consent for Terms of Service allows registration progression


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 7
- **Description:** This test verifies that when a user explicitly agrees to the Terms of Service during registration, the system correctly recognizes this consent and allows the user to proceed with the registration process, fulfilling AC-2.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a valid email address into the email field. | The email field displays 'testuser@example.com'. |
| 2 | fill | Enter a strong password into the password field. | The password field displays masked characters. |
| 3 | fill | Re-enter the same password to confirm. | The confirm password field displays masked characters. |
| 4 | check | Explicitly check the checkbox to agree to the Terms of Servi | The 'I agree to the Terms of Service' checkbox is selected. |
| 5 | click | Click the Register button to submit the registration form. | The system attempts to process the registration. |
| 6 | assert_url | Verify that the user is redirected to a registration success | The browser URL indicates a successful registration (e.g., ' |
| 7 | assert_visible | Confirm that a success message or the post-registration page | A message like 'Registration successful!' or the main dashbo |

#### TC-5 (ID 562): Verify timestamp logging for Privacy Policy consent


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 9
- **Description:** This test verifies that when a user provides explicit consent for the Privacy Policy during registration, the system correctly logs a timestamp for this legal action, as required by compliance regulations (AC-3).

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration form is displayed with fields for user deta |
| 2 | fill | Enter a unique email address for the new user | The email input field displays the entered email address |
| 3 | fill | Enter a strong password for the new user | The password input field displays masked characters |
| 4 | fill | Re-enter the same password to confirm | The confirm password input field displays masked characters |
| 5 | check | Check the checkbox to provide explicit consent for the Priva | The 'I agree to the Privacy Policy' checkbox is visibly chec |
| 6 | click | Click the Register button to submit the registration form | The user is successfully registered and redirected to the da |
| 7 | assert_url | Verify that the user is redirected to the expected post-regi | The browser URL ends with '/dashboard' (or similar success U |
| 8 | click | Navigate to the user's profile or settings page to view cons | The user's profile or settings page is displayed |
| 9 | assert_visible | Verify that a timestamp for Privacy Policy consent is displa | A timestamp (e.g., 'Privacy Policy accepted on: YYYY-MM-DD H |

#### TC-6 (ID 563): Verify timestamp logging for all legal consent actions


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 9
- **Description:** This test verifies that the system accurately logs timestamps for all explicit legal consent actions (Terms of Service and Privacy Policy) during user registration, ensuring compliance with auditing requirements (AC-4).

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user registration page | The registration page is displayed with fields for user deta |
| 2 | fill | Enter a unique email address for registration | The email field displays the entered value |
| 3 | fill | Enter a strong password | The password field displays masked characters |
| 4 | fill | Re-enter the same password to confirm | The confirm password field displays masked characters |
| 5 | check | Explicitly agree to the Terms of Service | The 'I agree to the Terms of Service' checkbox is checked |
| 6 | check | Explicitly agree to the Privacy Policy | The 'I agree to the Privacy Policy' checkbox is checked |
| 7 | click | Click the Register button to complete the registration proce | The system processes the registration and redirects the user |
| 8 | assert_url | Verify the user is redirected to the dashboard or a success  | The browser URL indicates the user is on the dashboard or a  |
| 9 | assert_visible | Confirm successful registration and implied consent logging | A 'Welcome' message, user's email, or other dashboard elemen |

#### TC-7 (ID 564): Verify IP address logging for all legal consent actions


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 9
- **Description:** This test verifies that the system accurately logs the user's IP address for all explicit legal consent actions (Terms of Service and Privacy Policy) during user registration, ensuring compliance with auditing requirements (AC-5).

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration page is displayed with fields for user deta |
| 2 | fill | Enter a unique email address for registration | The email field displays the entered address |
| 3 | fill | Enter a strong password | The password field displays masked characters |
| 4 | fill | Re-enter the same password to confirm | The confirm password field displays masked characters |
| 5 | check | Explicitly agree to the Terms of Service | The Terms of Service checkbox is checked, and the system sho |
| 6 | check | Explicitly agree to the Privacy Policy | The Privacy Policy checkbox is checked, and the system shoul |
| 7 | click | Click the Register button to complete the registration proce | The user is redirected to a success page or dashboard, and t |
| 8 | assert_url | Verify the user is redirected to the expected post-registrat | The browser URL matches the dashboard or registration succes |
| 9 | assert_visible | Confirm successful registration and page load | A confirmation message or user-specific content is visible o |

#### TC-8 (ID 565): Verify publicly accessible URL for Terms of Service document


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 4
- **Description:** This test verifies that the system provides a publicly accessible URL for the Terms of Service document, ensuring transparency and compliance with legal requirements (AC-6).

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the Terms of Service URL directly in the browser | The browser navigates to the specified URL and the page star |
| 2 | assert_url | Verify that the browser's current URL matches the expected T | The URL in the address bar is exactly 'https://example.com/t |
| 3 | assert_text | Verify that the page title or a prominent heading indicates  | The text 'Terms of Service' is clearly visible on the page,  |
| 4 | assert_visible | Verify that the actual content of the Terms of Service docum | The full text or a significant portion of the Terms of Servi |

#### TC-9 (ID 566): Verify publicly accessible URL for Privacy Policy document


- **Story:** US-326 — As a Super Admin, I can configure legal compliance settings so that F2MX operate
- **Status:** ready | **Priority:** high | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 4
- **Description:** This test verifies that the system provides a publicly accessible URL for the Privacy Policy document, ensuring transparency and compliance with legal requirements (AC-7).

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the Privacy Policy document URL directly in the browser | The browser navigates to the Privacy Policy page |
| 2 | assert_url | Verify that the URL in the browser matches the expected Priv | The browser URL is 'https://example.com/privacy-policy' |
| 3 | assert_text | Verify that the page title or a prominent heading 'Privacy P | The text 'Privacy Policy' is displayed on the page |
| 4 | assert_text | Verify that the document content includes an 'effective date | Text related to an 'effective date' or policy content is vis |

#### TC-10 (ID 567): Verify Super Admin can successfully configure organization accounts for app store submission


- **Story:** US-327 — As a Super Admin, I can manage app store configurations so that F2MX is availabl
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 6
- **Description:** This test verifies that a Super Admin can input and save valid organizational account details, such as a D-U-N-S number, required for app store submissions. This ensures the foundational setup for publishing apps is functional.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a valid D-U-N-S number into the designated field | The D-U-N-S Number field displays '123456789' |
| 2 | fill | Enter the organization's name into the Organization Name fie | The Organization Name field displays 'Example Corp' |
| 3 | click | Click the Save button to submit the entered account details | The system processes the submission |
| 4 | assert_text | Verify that a success message is displayed confirming the sa | A success message 'Organization account details saved succes |
| 5 | assert_text | Verify that the D-U-N-S Number field retains the saved value | The D-U-N-S Number field still displays '123456789' |
| 6 | assert_text | Verify that the Organization Name field retains the saved va | The Organization Name field still displays 'Example Corp' |

#### TC-11 (ID 568): Verify Super Admin can successfully define a new In-App Purchase (IAP) product


- **Story:** US-327 — As a Super Admin, I can manage app store configurations so that F2MX is availabl
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 10
- **Description:** This test verifies that a Super Admin can create and define a new IAP product with all necessary details, such as product ID, type, and pricing. This ensures new monetizable items can be added to the app.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Initiate the process to create a new In-App Purchase (IAP) p | A form or modal for defining a new IAP product is displayed |
| 2 | fill | Enter a unique identifier for the new product | The 'Product ID' field displays the entered value |
| 3 | select | Choose 'Consumable' as the type of IAP product | The 'Product Type' dropdown shows 'Consumable' as selected |
| 4 | fill | Enter a user-facing name for the product | The 'Product Name' field displays 'Gold Coin Pack (1000)' |
| 5 | fill | Provide a detailed description of the product | The 'Product Description' text area displays the entered tex |
| 6 | fill | Set the price for the IAP product | The 'Price' field displays '9.99' |
| 7 | select | Select the currency for the product price | The 'Currency' dropdown shows 'USD' as selected |
| 8 | click | Submit the new IAP product definition | The product definition form closes, and a success message or |
| 9 | assert_text | Verify that a success message is displayed | A message confirming successful product creation is visible  |
| 10 | assert_text | Verify the newly created product appears in the product list | The 'Gold Coin Pack (1000)' product is visible in the list o |

#### TC-12 (ID 569): Verify Super Admin can successfully manage (edit) an existing In-App Purchase (IAP) product


- **Story:** US-327 — As a Super Admin, I can manage app store configurations so that F2MX is availabl
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 8
- **Description:** This test verifies that a Super Admin can modify details of an already defined IAP product, such as its price or description. This ensures flexibility in updating monetizable items.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify that the 'Premium Feature Pack' product is visible in | The 'Premium Feature Pack' product is displayed in the list. |
| 2 | click | Click the edit action to open the product's details for modi | The 'Edit In-App Purchase Product' form is displayed, pre-fi |
| 3 | fill | Change the product's price to a new value. | The 'Price' input field displays '12.99'. |
| 4 | fill | Update the product's description. | The 'Description' text area displays the new description. |
| 5 | click | Submit the changes made to the product. | The changes are saved, and a success message is displayed, o |
| 6 | assert_text | Verify that a success message confirms the product update. | A message like 'Product updated successfully' is visible on  |
| 7 | assert_text | Verify that the updated price is displayed for the 'Premium  | The 'Premium Feature Pack' entry shows '12.99' as its price. |
| 8 | assert_text | Verify that the updated description is displayed for the 'Pr | The 'Premium Feature Pack' entry shows the new description. |

#### TC-13 (ID 570): Verify Super Admin can successfully link to an App Store developer account


- **Story:** US-327 — As a Super Admin, I can manage app store configurations so that F2MX is availabl
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 5
- **Description:** This test verifies that a Super Admin can provide and save the necessary credentials or tokens to establish a link with an Apple App Store developer account. This is crucial for app submission and management on iOS.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter the valid App Store Connect Issuer ID into the designa | The Issuer ID field displays the entered value |
| 2 | fill | Enter the valid App Store Connect Key ID into the designated | The Key ID field displays the entered value |
| 3 | fill | Upload the App Store Connect API Private Key file (.p8) | The file name of the uploaded private key is displayed next  |
| 4 | click | Click the Save button to submit the App Store Connect API de | The page attempts to process the provided credentials |
| 5 | assert_text | Verify that a success message confirms the App Store account | A message indicating 'App Store account linked successfully' |

#### TC-14 (ID 571): Verify Super Admin can successfully link to a Google Play developer account


- **Story:** US-327 — As a Super Admin, I can manage app store configurations so that F2MX is availabl
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 5
- **Description:** This test verifies that a Super Admin can provide and save the necessary credentials or JSON key file to establish a link with a Google Play developer account. This is crucial for app submission and management on Android.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Initiate the file upload process for the Google Play Service | A file selection dialog appears or the input field is ready  |
| 2 | fill | Select and upload the valid Google Play Service Account JSON | The selected file name 'google-play-service-account.json' is |
| 3 | click | Click the button to submit the JSON key and link the account | A loading indicator may appear, followed by a success messag |
| 4 | assert_text | Verify that a success message confirms the account linking. | The text 'Google Play account linked successfully' is visibl |
| 5 | assert_text | Verify that the status of the Google Play account connection | The status indicator clearly shows 'Linked' for the Google P |

#### TC-15 (ID 572): Verify Super Admin can successfully manage app metadata and submission details


- **Story:** US-327 — As a Super Admin, I can manage app store configurations so that F2MX is availabl
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 12
- **Description:** This test verifies that a Super Admin can input, edit, and save various app metadata fields (e.g., app name, description, categories) and submission-related details. This ensures the app can be properly prepared for store submission.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a name for the application | The App Name field displays 'My Awesome App' |
| 2 | fill | Enter a detailed description for the application | The App Description text area displays the entered text |
| 3 | select | Select a primary category for the app | The Primary Category dropdown shows 'Productivity' as select |
| 4 | click | Click the Save button to store the entered metadata | A success message is displayed, indicating the metadata was  |
| 5 | assert_text | Verify that the initial app name persists after saving | The App Name input field still displays 'My Awesome App' |
| 6 | fill | Edit the app name to a new value | The App Name field displays 'My Super Awesome App' |
| 7 | click | Click the Save button to store the updated metadata | A success message is displayed, indicating the metadata was  |
| 8 | assert_text | Verify that the updated app name persists after saving | The App Name input field still displays 'My Super Awesome Ap |
| 9 | fill | Enter the current version number for the app submission | The App Version field displays '1.0.0' |
| 10 | fill | Enter release notes for the current version | The Release Notes text area displays the entered text |

*… and 2 more steps*


#### TC-16 (ID 573): Verify system collects Date of Birth during registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 7
- **Description:** This test verifies that the registration process successfully collects and processes the user's Date of Birth (DOB) as part of the required personal details for account creation.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a valid email address for registration | The email input field displays 'testuser@example.com' |
| 2 | fill | Enter a strong password | The password input field displays masked characters |
| 3 | fill | Re-enter the same password to confirm | The confirm password input field displays masked characters |
| 4 | fill | Enter a valid date of birth (e.g., January 15, 1990) | The Date of Birth field displays '01/15/1990' |
| 5 | click | Click the Register button to submit the registration form | The system processes the registration request |
| 6 | assert_url | Verify that the user is redirected to a registration success | The browser URL ends with '/registration-success' or similar |
| 7 | assert_text | Verify a success message is displayed on the page | A 'Registration Successful' or similar confirmation message  |

#### TC-17 (ID 574): Verify registration proceeds for user aged 18 or older


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 10
- **Description:** This test ensures that a user who meets the minimum age requirement (18 years or older) is allowed to proceed with registration, confirming the age verification logic correctly identifies eligible users.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application registration page | The registration page is displayed with input fields for use |
| 2 | fill | Enter a valid email address for registration | The email field shows the entered address |
| 3 | fill | Enter a strong password | The password field shows masked characters |
| 4 | fill | Re-enter the same password for confirmation | The confirm password field shows masked characters |
| 5 | select | Select a day for the user's birth date | Day '15' is selected in the dropdown |
| 6 | select | Select a month for the user's birth date | Month 'January' is selected in the dropdown |
| 7 | select | Select a year that makes the user 18 years or older | Year '2000' is selected in the dropdown |
| 8 | click | Click the Register button to submit the registration form | The application processes the registration |
| 9 | assert_url | Verify the user is redirected to a success page or dashboard | The browser URL indicates successful registration (e.g., '/r |
| 10 | assert_text | Verify a success message is displayed on the page | A 'Registration Successful' message or similar confirmation  |

#### TC-18 (ID 575): Verify registration is blocked for user aged 17 years


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-2
- **Steps:** 10
- **Description:** This test verifies that the system correctly identifies and blocks registration for users who are exactly 17 years old, displaying the specific error message for age restriction.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application registration page | The registration page is displayed with input fields for use |
| 2 | fill | Enter a first name for the user | The first name field shows 'Test' |
| 3 | fill | Enter a last name for the user | The last name field shows 'User' |
| 4 | fill | Enter a unique email address | The email field shows 'testuser17@example.com' |
| 5 | fill | Enter a strong password | The password field shows masked characters |
| 6 | fill | Re-enter the same password to confirm | The confirm password field shows masked characters |
| 7 | fill | Enter a date of birth that makes the user exactly 17 years o | The date of birth field shows the entered date |
| 8 | click | Click the Register button to submit the form | The system attempts to process the registration |
| 9 | assert_text | Verify that the age restriction error message is displayed | The specific error message 'You must be at least 18 years ol |
| 10 | assert_url | Verify the user remains on the registration page | The browser URL is still the registration page URL |

#### TC-19 (ID 576): Verify registration is blocked for user aged 1 day old


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-2
- **Steps:** 8
- **Description:** This test ensures the system robustly blocks registration for users significantly under the age of 18, specifically a user who is only 1 day old, and presents the correct age restriction error.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a name for the new user | The full name field displays 'Baby One Day Old' |
| 2 | fill | Enter a unique email address for registration | The email field displays 'baby.onedayold@example.com' |
| 3 | fill | Enter a strong password | The password field displays masked characters |
| 4 | fill | Re-enter the same password for confirmation | The confirm password field displays masked characters |
| 5 | fill | Enter a date of birth that makes the user 1 day old (adjust  | The date of birth field displays '01/01/2024' (or current da |
| 6 | click | Click the Register button to submit the form | The system attempts to process the registration |
| 7 | assert_text | Verify that an age restriction error message is displayed | The specific age restriction error message 'You must be at l |
| 8 | assert_url | Verify that the user remains on the registration page | The browser URL is still the registration page URL, indicati |

#### TC-20 (ID 577): Verify system ensures entered Email is unique during registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 6
- **Description:** This test confirms that the system successfully validates the uniqueness of the provided email address, allowing registration to proceed only with an email not already in use.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a unique email address into the Email field | The Email field displays 'newuser@example.com' |
| 2 | fill | Enter a password into the Password field | The Password field displays masked characters |
| 3 | fill | Re-enter the same password into the Confirm Password field | The Confirm Password field displays masked characters |
| 4 | click | Click the Register button to submit the registration form | The system attempts to process the registration |
| 5 | assert_url | Verify the user is redirected to a registration success page | The browser URL indicates a successful registration (e.g., ' |
| 6 | assert_text | Verify a success message is displayed on the page | A message confirming 'Registration successful!' or similar i |

#### TC-21 (ID 578): Verify system ensures entered Username is unique during registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 8
- **Description:** This test confirms that the system successfully validates the uniqueness of the provided username, allowing registration to proceed only with a username not already in use.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration form is displayed with fields for username, |
| 2 | fill | Enter a unique username that is not already registered | The username field displays 'uniqueuser' |
| 3 | fill | Enter a valid email address | The email field displays 'uniqueuser@example.com' |
| 4 | fill | Enter a strong password | The password field displays masked characters |
| 5 | fill | Re-enter the same password for confirmation | The confirm password field displays masked characters |
| 6 | click | Click the Register button to submit the form | The system processes the registration request |
| 7 | assert_url | Verify the user is redirected to the registration success pa | The browser URL ends with '/registration-success' or similar |
| 8 | assert_text | Verify a success message is displayed on the page | The text 'Registration Successful' or similar confirmation i |

#### TC-22 (ID 579): Verify Username adheres to specified constraints (valid chars, no spaces, within max length)


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 7
- **Description:** This test ensures that a username containing only allowed characters, no spaces, and within the maximum length (e.g., 10 characters) is successfully accepted by the system.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a username that contains only allowed characters, no s | The Username field displays 'ValidUser123' |
| 2 | fill | Enter a valid email address. | The Email field displays 'testuser@example.com' |
| 3 | fill | Enter a valid password. | The Password field displays masked characters |
| 4 | fill | Re-enter the same password to confirm. | The Confirm Password field displays masked characters |
| 5 | click | Click the Register button to submit the form. | The system attempts to process the registration |
| 6 | assert_url | Verify that the user is redirected to the dashboard or a suc | The browser URL ends with '/dashboard' or a similar success  |
| 7 | assert_text | Verify a welcome message or the newly registered username is | A welcome message including 'ValidUser123' is visible on the |

#### TC-23 (ID 580): Verify Username adheres to maximum length constraint (20 characters)


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** boundary | **AC Ref:** AC-5
- **Steps:** 7
- **Description:** This test verifies that the system correctly accepts a username that is exactly 20 characters long, confirming the boundary condition for the maximum length constraint.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a username that is exactly 20 characters long | The Username input field displays 'UserWith20CharsABC' |
| 2 | fill | Enter a valid email address for registration | The Email input field displays 'test.user.20@example.com' |
| 3 | fill | Enter a valid password | The Password input field displays masked characters |
| 4 | fill | Re-enter the same password for confirmation | The Confirm Password input field displays masked characters |
| 5 | click | Click the Register button to submit the form | The system attempts to process the registration |
| 6 | assert_url | Verify the user is redirected to a registration success page | The browser URL ends with '/registration-success' or a simil |
| 7 | assert_text | Verify a success message is displayed, confirming the 20-cha | A message like 'Registration successful!' or 'Welcome!' is v |

#### TC-24 (ID 581): Verify explicit acceptance of Terms of Service is required for registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 10
- **Description:** This test ensures that the user must explicitly accept the Terms of Service to successfully complete the registration process, enforcing legal compliance.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration page is displayed with fields for user deta |
| 2 | fill | Enter a name for registration | The name field shows 'Test User' |
| 3 | fill | Enter a unique email address for registration | The email field shows 'testuser@example.com' |
| 4 | fill | Enter a strong password | The password field shows masked characters |
| 5 | fill | Re-enter the same password for confirmation | The confirm password field shows masked characters |
| 6 | click | Attempt to register without accepting the Terms of Service | An error message is displayed, and the user remains on the r |
| 7 | assert_text | Verify that an error message explicitly states the Terms of  | The error message 'You must accept the Terms of Service' (or |
| 8 | check | Explicitly accept the Terms of Service | The 'I accept the Terms of Service' checkbox is now checked |
| 9 | click | Attempt to register again after accepting the Terms of Servi | The user is successfully registered and redirected to the da |
| 10 | assert_url | Verify the user is redirected to the dashboard or a success  | The browser URL indicates successful registration (e.g., end |

#### TC-25 (ID 582): Verify explicit acceptance of Privacy Policy is required for registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 9
- **Description:** This test ensures that the user must explicitly accept the Privacy Policy to successfully complete the registration process, enforcing legal compliance.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the user registration page | The registration form is displayed with fields for user deta |
| 2 | fill | Enter a valid email address into the email field | The email field shows the entered address. |
| 3 | fill | Enter a strong password into the password field | The password field shows masked characters. |
| 4 | fill | Re-enter the same password for confirmation | The confirm password field shows masked characters. |
| 5 | click | Attempt to register without checking the 'I accept the Priva | The registration form remains on the page, and an error mess |
| 6 | assert_text | Verify that an error message explicitly states that the Priv | An error message like 'You must accept the Privacy Policy' i |
| 7 | check | Tick the checkbox to accept the Privacy Policy | The 'I accept the Privacy Policy' checkbox is now checked. |
| 8 | click | Click the Register button again after accepting the Privacy  | The user is redirected to a registration success page or the |
| 9 | assert_url | Verify that the URL indicates successful registration or nav | The browser URL matches a success page or dashboard pattern  |

#### TC-26 (ID 583): Verify system assigns default Global Wallet with 0 balance and 0 XP upon registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-8
- **Steps:** 4
- **Description:** This test confirms that upon successful registration, the system automatically provisions a new user with a Global Wallet initialized with a 0 balance and 0 XP, as per default settings.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user's wallet details page after successful  | The wallet or account details page is displayed |
| 2 | assert_visible | Verify that the Global Wallet section is present on the page | The Global Wallet section is clearly visible |
| 3 | assert_text | Confirm the Global Wallet balance is initialized to 0 | The displayed balance for the Global Wallet is '0' |
| 4 | assert_text | Confirm the Global Wallet XP is initialized to 0 | The displayed XP for the Global Wallet is '0' |

#### TC-27 (ID 584): Verify system assigns 'Rookie' Tier status upon successful registration


- **Story:** US-328 — As a New User, I can create an account and verify my age so that I can access th
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-9
- **Steps:** 3
- **Description:** This test ensures that a newly registered user is correctly assigned the default 'Rookie' Tier status immediately after successful account creation.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Assume the user has successfully registered and is redirecte | The user is on the application dashboard or welcome page. |
| 2 | click | Navigate to the user's profile or account settings page. | The user's profile or account settings page is displayed. |
| 3 | assert_text | Verify that the displayed tier status for the newly register | The text 'Rookie' is visible as the user's assigned tier sta |

#### TC-28 (ID 585): Verify successful login for a registered, active user


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 6
- **Description:** This test ensures that a user with valid credentials and an 'Active' account status can successfully initiate the login process. It confirms adherence to the primary access control rule.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page | The login page is displayed, showing input fields for email  |
| 2 | fill | Enter the email address of a registered, active user | The Email input field displays 'active.user@example.com'. |
| 3 | fill | Enter the correct password for the active user | The Password input field displays masked characters. |
| 4 | click | Click the Login button to submit the credentials | The application attempts to log in the user, and a loading i |
| 5 | assert_url | Verify that the browser navigates to the dashboard or home p | The URL in the browser address bar ends with '/dashboard' (o |
| 6 | assert_visible | Confirm that key elements of the post-login page are visible | The dashboard (or home page) is fully loaded and displays el |

#### TC-29 (ID 586): Verify system prompts for 2FA after successful username/password validation


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 6
- **Description:** This test confirms that after a user successfully enters their username and password, the system correctly transitions to the two-factor authentication prompt. This is a critical security step.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_url | Verify the URL has changed to the 2FA challenge page | The browser URL indicates the 2FA challenge page (e.g., '/2f |
| 2 | assert_visible | Confirm that the 2FA challenge form is displayed | The 2FA challenge form, typically with an input field for a  |
| 3 | assert_text | Verify the page title or heading indicates 2FA | The text 'Two-Factor Authentication' or similar is prominent |
| 4 | assert_text | Verify instructions for entering the 2FA code are present | Instructions like 'Enter the code from your authenticator ap |
| 5 | assert_visible | Confirm the input field for the 2FA code is present | An input field, typically labeled 'Verification Code' or '2F |
| 6 | assert_visible | Confirm the button to submit the 2FA code is present | A button labeled 'Verify', 'Submit', or similar is visible t |

#### TC-30 (ID 587): Verify account locks for 30 minutes after 3 failed OTP attempts


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 10
- **Description:** This test ensures that the account locking mechanism is triggered correctly after three consecutive failed OTP attempts, enhancing security against brute-force attacks. It verifies the system's response to repeated incorrect 2FA inputs.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter an incorrect OTP for the first attempt | The OTP input field displays the entered value |
| 2 | click | Click the Verify OTP button to submit the incorrect OTP | An error message indicating an incorrect OTP is displayed |
| 3 | assert_text | Verify the error message for the first failed attempt | The text 'Incorrect OTP. Please try again.' is visible on th |
| 4 | fill | Enter another incorrect OTP for the second attempt | The OTP input field displays the new entered value |
| 5 | click | Click the Verify OTP button for the second failed attempt | An error message indicating an incorrect OTP is displayed |
| 6 | assert_text | Verify the error message for the second failed attempt | The text 'Incorrect OTP. Please try again.' is visible on th |
| 7 | fill | Enter a third incorrect OTP for the final attempt | The OTP input field displays the new entered value |
| 8 | click | Click the Verify OTP button for the third failed attempt | The page updates to show an account locked message |
| 9 | assert_text | Verify the account locked message is displayed | The specific account locked message is visible on the page |
| 10 | assert_visible | Verify the OTP input field is no longer visible or editable | The OTP input field is not visible or is disabled, preventin |

#### TC-31 (ID 588): Verify account locks after exactly 3 failed OTP attempts


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** boundary | **AC Ref:** AC-3
- **Steps:** 9
- **Description:** This test specifically checks the boundary condition for account locking, ensuring that the system locks the account precisely after the 3rd failed OTP attempt, not before or after. It confirms the accuracy of the counter.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter an incorrect OTP for the first attempt | The OTP input field displays the entered value |
| 2 | click | Submit the first incorrect OTP | An error message indicating an incorrect OTP is displayed |
| 3 | assert_text | Verify the error message for the first failed attempt | The specific 'Incorrect OTP' error message is visible |
| 4 | fill | Enter another incorrect OTP for the second attempt | The OTP input field displays the new entered value |
| 5 | click | Submit the second incorrect OTP | An error message indicating an incorrect OTP is displayed |
| 6 | assert_text | Verify the error message for the second failed attempt | The specific 'Incorrect OTP' error message is visible |
| 7 | fill | Enter a third incorrect OTP for the final attempt | The OTP input field displays the new entered value |
| 8 | click | Submit the third incorrect OTP | The account is locked, and a corresponding message or page i |
| 9 | assert_text | Verify the account locked message is displayed after the thi | The specific account locked message is visible on the page |

#### TC-32 (ID 589): Verify redirection to mandatory password change screen when 'Force Password Reset' flag is set


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 8
- **Description:** This test ensures that users whose accounts have the 'Force Password Reset' flag enabled are correctly redirected to the password change screen immediately after successful authentication. This is crucial for security compliance and account recovery.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page | The login page is displayed with fields for username/email a |
| 2 | fill | Enter the username/email of the user account with 'Force Pas | The username/email field displays the entered value |
| 3 | fill | Enter the current password for the user account | The password field displays masked characters |
| 4 | click | Click the Login button to submit credentials | The system processes the login request (and any 2FA if appli |
| 5 | assert_url | Verify that the user is redirected to the mandatory password | The browser URL ends with '/password-change' or a similar pa |
| 6 | assert_visible | Confirm that the 'New Password' input field is visible | The 'New Password' input field is displayed on the page |
| 7 | assert_visible | Confirm that the 'Confirm New Password' input field is visib | The 'Confirm New Password' input field is displayed on the p |
| 8 | assert_text | Verify that a message indicating a mandatory password change | A message like 'Password Change Required' or 'You must chang |

#### TC-33 (ID 590): Verify no redirection to password change when 'Force Password Reset' flag is NOT set


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-4
- **Steps:** 7
- **Description:** This test ensures that users are NOT redirected to a mandatory password change screen if the 'Force Password Reset' flag is explicitly NOT set. It verifies that the system correctly interprets the flag's state and only enforces a reset when required.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page | The login page is displayed with input fields for credential |
| 2 | fill | Enter the registered user's username or email | The username/email field displays the entered value |
| 3 | fill | Enter the user's valid password | The password field displays masked characters |
| 4 | click | Click the Login button to submit credentials | The system processes the login request (and 2FA if applicabl |
| 5 | assert_url | Verify the user is redirected to the expected post-login pag | The browser URL ends with '/dashboard' or the application's  |
| 6 | assert_text | Verify a welcome message or typical dashboard content is vis | A welcome message or dashboard elements are displayed, indic |
| 7 | assert_visible | Verify that no password change form or 'Force Password Reset | The password change form or any mandatory password reset pro |

#### TC-34 (ID 591): Verify no redirection to password change if 'Force Password Reset' flag is missing or null


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-4
- **Steps:** 7
- **Description:** This test ensures that if the 'Force Password Reset' flag is missing or has a null value, the system defaults to not forcing a password reset. It verifies robust handling of potentially undefined flag states.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page | The login page is displayed with fields for username/email a |
| 2 | fill | Enter the username/email for a registered user with a missin | The username/email field displays the entered value |
| 3 | fill | Enter the correct password for the user | The password field displays masked characters |
| 4 | click | Click the Login button to submit credentials (assuming 2FA i | The system processes the login request |
| 5 | assert_url | Verify the user is redirected to the main dashboard or home  | The browser URL indicates the user is on the dashboard or ho |
| 6 | assert_visible | Confirm that the dashboard or home page content is visible | The main content of the dashboard or home page is displayed, |
| 7 | assert_text | Verify that no 'Password Change' or 'Reset Password' prompt  | The text 'Password Change' or 'Reset Password' is NOT visibl |

#### TC-35 (ID 592): Verify Last_Login_Timestamp is logged upon successful login


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 8
- **Description:** This test confirms that the system accurately records the Last_Login_Timestamp in the user's profile or audit logs after a successful login. This is crucial for security auditing and user activity tracking.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page | The login page is displayed with fields for credentials |
| 2 | fill | Enter the registered user's email or username | The email/username field displays the entered value |
| 3 | fill | Enter the correct password for the user | The password field displays masked characters |
| 4 | click | Click the Login button to submit credentials | The system either redirects to the dashboard or prompts for  |
| 5 | fill | If prompted, enter the valid 2FA code | The 2FA code is accepted, and the user is redirected to the  |
| 6 | click | Navigate to the user's profile or account settings page | The user profile or account settings page is displayed |
| 7 | assert_text | Verify that a 'Last Login' or similar timestamp label is vis | A label indicating 'Last Login' or 'Last Activity' is presen |
| 8 | assert_text | Verify the displayed Last Login Timestamp reflects the curre | The Last Login Timestamp shows a value corresponding to the  |

#### TC-36 (ID 593): Verify IP Address is logged upon successful login


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 8
- **Description:** This test confirms that the system accurately records the user's IP address in the user's profile or audit logs after a successful login. This is crucial for security auditing and identifying potential unauthorized access.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page. | The login page is displayed, showing fields for email/userna |
| 2 | fill | Enter the registered user's email or username. | The email/username field displays the entered value. |
| 3 | fill | Enter the correct password for the registered user. | The password field displays masked characters. |
| 4 | click | Click the Login button to submit credentials. | The user is successfully logged in and redirected to the das |
| 5 | assert_url | Verify that the user is on the expected post-login page. | The browser URL matches the dashboard or home page URL (e.g. |
| 6 | click | Click on the user profile icon or open the user dropdown men | The user profile menu or a link to 'Settings'/'Profile'/'Sec |
| 7 | click | Navigate to the user's settings, security, or profile page w | The user's settings, security, or profile page is displayed. |
| 8 | assert_text | Verify that the user's current public IP address (which was  | The system displays the IP address that matches the public I |

#### TC-37 (ID 594): Successful Login with 2FA and Dashboard Redirection


- **Story:** US-329 — As a User, I can securely log in with two-factor authentication so that my accou
- **Status:** ready | **Priority:** medium | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 9
- **Description:** Verify that a registered, active user can successfully log in by providing correct credentials and a valid 2FA code, and is then redirected to the main application dashboard.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page. | The login page is displayed with input fields for username/e |
| 2 | fill | Enter the registered username 'testuser'. | The username/email field displays 'testuser'. |
| 3 | fill | Enter the correct password for 'testuser'. | The password field displays masked characters. |
| 4 | click | Click the Login button to submit credentials. | The user is redirected to the Two-Factor Authentication (2FA |
| 5 | assert_visible | Verify that the 2FA input field is displayed. | A field to enter the 2FA code is visible on the page. |
| 6 | fill | Enter the valid, unexpired 2FA code received on 'testuser's  | The 2FA code field displays the entered code. |
| 7 | click | Click the button to submit the 2FA code. | The application processes the 2FA code and redirects the use |
| 8 | assert_url | Verify that the browser URL has changed to the main applicat | The browser URL ends with '/dashboard' or a similar pattern  |
| 9 | assert_visible | Confirm that the main application dashboard content is loade | Key dashboard elements are visible, indicating a successful  |

#### TC-38 (ID 595): Verify system sends OTP to registered email


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 4
- **Description:** This test verifies that upon a password recovery request, the system successfully sends a secure, time-bound One-Time Password (OTP) to the user's registered email address. This ensures the initial step of the password recovery process functions as expected.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter the registered email address into the email input fiel | The email input field displays 'testuser@example.com' |
| 2 | click | Click the button to request a One-Time Password | The system processes the request, and a success indication o |
| 3 | assert_text | Verify that a success message confirms the OTP has been sent | A message like 'OTP sent to your email' or 'A One-Time Passw |
| 4 | assert_url | Verify that the user is redirected to the OTP verification p | The browser URL ends with '/otp-verification' or a similar p |

#### TC-39 (ID 596): Verify system validates correct OTP successfully


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 5
- **Description:** This test verifies that the system correctly validates a valid and unexpired OTP entered by the user. Successful validation is crucial for proceeding to the password reset stage.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter the valid and unexpired OTP received by the user | The OTP input field displays the entered 6-digit code |
| 2 | click | Click the button to submit the entered OTP for verification | The system processes the OTP |
| 3 | wait | Wait for the page to transition after OTP submission | The page navigates away from the OTP verification screen |
| 4 | assert_url | Verify that the user is redirected to the password reset pag | The browser URL ends with '/reset-password' or similar |
| 5 | assert_visible | Confirm that the password reset form is displayed | Input fields for 'New Password' and 'Confirm New Password' a |

#### TC-40 (ID 597): Verify redirection to Reset Password screen after successful OTP validation


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 6
- **Description:** This test ensures that after a user successfully validates their OTP, the system correctly redirects them to the 'Reset Password' screen. This is a critical step in the password recovery flow, allowing the user to set a new password.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | wait | Wait for the system to redirect to the Reset Password page a | The browser navigates to the Reset Password page |
| 2 | assert_url | Verify the URL reflects the Reset Password screen | The browser URL ends with '/reset-password' or similar |
| 3 | assert_text | Verify the page title or header indicates 'Reset Password' | The text 'Reset Password' is prominently displayed on the pa |
| 4 | assert_visible | Verify the 'New Password' input field is visible | An input field labeled 'New Password' is present |
| 5 | assert_visible | Verify the 'Confirm New Password' input field is visible | An input field labeled 'Confirm New Password' is present |
| 6 | assert_visible | Verify the 'Reset Password' button is visible | A button labeled 'Reset Password' is present and enabled |

#### TC-41 (ID 598): Verify new password meets complexity requirements (8-15 chars, alphanumeric)


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 12
- **Description:** This test verifies that the system enforces the specified complexity requirements for a new password: minimum 8 characters, maximum 15 characters, and alphanumeric. This ensures account security by preventing weak passwords.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a password that is too short (7 characters, less than  | The 'New Password' field displays the entered text. |
| 2 | fill | Enter the same too-short password into the confirmation fiel | The 'Confirm New Password' field displays the entered text. |
| 3 | click | Attempt to reset the password with the too-short password. | An error message indicating the password is too short is dis |
| 4 | assert_text | Verify the system displays an error for insufficient passwor | The specified error message is visible on the page. |
| 5 | fill | Enter a password that is too long (19 characters, more than  | The 'New Password' field displays the entered text. |
| 6 | fill | Enter the same too-long password into the confirmation field | The 'Confirm New Password' field displays the entered text. |
| 7 | click | Attempt to reset the password with the too-long password. | An error message indicating the password is too long is disp |
| 8 | assert_text | Verify the system displays an error for excessive password l | The specified error message is visible on the page. |
| 9 | fill | Enter a password that contains a special character (not alph | The 'New Password' field displays the entered text. |
| 10 | fill | Enter the same non-alphanumeric password into the confirmati | The 'Confirm New Password' field displays the entered text. |

*… and 2 more steps*


#### TC-42 (ID 599): Verify new password meets complexity at minimum and maximum character limits


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** medium | **Category:** regression
- **Scenario:** boundary | **AC Ref:** AC-4
- **Steps:** 9
- **Description:** This test verifies the system's behavior when a new password is provided exactly at the minimum (8 characters) and maximum (15 characters) length boundaries, while also being alphanumeric. This ensures the boundary conditions for password length are correctly handled.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a new password with the minimum required length (8 alp | The New Password field displays the entered characters. |
| 2 | fill | Re-enter the same password in the Confirm New Password field | The Confirm New Password field displays the entered characte |
| 3 | click | Click the Reset Password button to submit the new password. | A success message is displayed, or the user is redirected to |
| 4 | assert_text | Verify that the password reset was successful for the minimu | A confirmation message indicating successful password reset  |
| 5 | assert_visible | Manually re-access the Reset Password screen to test the max | The Reset Password screen is displayed with the New Password |
| 6 | fill | Enter a new password with the maximum allowed length (15 alp | The New Password field displays the entered characters. |
| 7 | fill | Re-enter the same password in the Confirm New Password field | The Confirm New Password field displays the entered characte |
| 8 | click | Click the Reset Password button to submit the new password. | A success message is displayed, or the user is redirected to |
| 9 | assert_text | Verify that the password reset was successful for the maximu | A confirmation message indicating successful password reset  |

#### TC-43 (ID 600): Verify new password is not identical to current password


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 5
- **Description:** This test ensures that the system prevents users from setting a new password that is identical to their existing (current) password. This is a security measure to encourage stronger password practices.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter the current password into the 'New Password' field | The 'New Password' field displays the entered password |
| 2 | fill | Enter the current password into the 'Confirm New Password' f | The 'Confirm New Password' field displays the entered passwo |
| 3 | click | Click the 'Reset Password' button to submit the new password | The system attempts to process the password change |
| 4 | assert_text | Verify that an error message is displayed indicating the new | An error message 'New password cannot be the same as the cur |
| 5 | assert_url | Verify the user remains on the Reset Password screen | The browser URL remains on the /reset-password page |

#### TC-44 (ID 601): Verify system displays error message for expired OTP


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 4
- **Description:** This test verifies that the system correctly identifies an expired OTP and displays an appropriate error message to the user. This ensures that time-bound OTPs are enforced for security.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter an expired One-Time Password into the OTP field | The OTP field displays the entered expired OTP |
| 2 | click | Click the 'Verify OTP' button to submit the expired OTP | The system processes the OTP |
| 3 | assert_text | Verify that an error message for expired OTP is displayed | An error message 'The OTP has expired. Please request a new  |
| 4 | assert_visible | Verify that an option to request a new OTP is available | A 'Request New OTP' button or link is visible, allowing the  |

#### TC-45 (ID 602): Verify system displays error message for invalid OTP


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-6
- **Steps:** 5
- **Description:** This test verifies that the system correctly identifies an invalid OTP (e.g., incorrect digits) and displays an appropriate error message to the user. This prevents unauthorized access through brute-force or incorrect OTP attempts.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter an invalid 6-digit OTP into the OTP input field | The OTP input field displays the entered invalid digits |
| 2 | click | Click the Verify button to submit the OTP | The system attempts to validate the entered OTP |
| 3 | assert_visible | Verify that an error message is displayed on the screen | An error message is visible, typically near the OTP field or |
| 4 | assert_text | Verify the content of the error message | The error message text explicitly states 'Invalid OTP. Pleas |
| 5 | assert_url | Verify the user remains on the OTP Verification screen | The browser URL still points to the OTP verification page |

#### TC-46 (ID 603): Verify system displays error message for OTP with incorrect format (too short)


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** medium | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-6
- **Steps:** 3
- **Description:** This test verifies that the system correctly identifies an OTP that does not meet the expected format (e.g., too few digits) and displays an appropriate error message. This ensures robust input validation for OTPs.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter an OTP that is too short (e.g., 3 digits instead of 6) | The OTP input field displays the entered short code |
| 2 | click | Click the Verify button to submit the OTP | The system attempts to validate the OTP |
| 3 | assert_text | Verify that an error message indicating an incorrect OTP for | An error message like 'Please enter a valid 6-digit OTP.' or |

#### TC-47 (ID 604): Verify user's password is updated successfully


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 3
- **Description:** This test verifies that after a user successfully provides a new password that meets all requirements, the system correctly updates the user's password in the database. This is the core functionality of the password reset process.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click the button to submit the new password. | The system processes the password change request. |
| 2 | assert_text | Verify that a success message indicating the password update | A message like 'Your password has been successfully updated. |
| 3 | assert_url | Verify the user is redirected to the login page. | The browser URL ends with '/login' and the login page is dis |

#### TC-48 (ID 605): Verify redirection to login screen upon successful password reset


- **Story:** US-330 — As a User, I can recover my password via email so that I can regain access to my
- **Status:** ready | **Priority:** high | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-8
- **Steps:** 6
- **Description:** This test ensures that upon successful completion of the password reset process, the system redirects the user to the login screen. This allows the user to immediately attempt to log in with their newly set password.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_text | Verify that a success message indicating the password reset  | The message 'Password reset successful!' is visible on the p |
| 2 | click | Click the button to proceed to the login screen. | The browser starts navigating to the login page. |
| 3 | assert_url | Verify that the browser is redirected to the login page URL. | The current URL ends with '/login'. |
| 4 | assert_visible | Verify that the Email input field is visible on the login pa | The Email input field is displayed, ready for user input. |
| 5 | assert_visible | Verify that the Password input field is visible on the login | The Password input field is displayed, ready for user input. |
| 6 | assert_visible | Verify that the Login button is visible on the login page. | The Login button is displayed, allowing the user to submit c |

#### TC-49 (ID 606): Verify user can upload a valid JPG avatar within size limit


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 5
- **Description:** This test ensures users can successfully upload a JPG image as their avatar, adhering to the specified file type and size constraints. It confirms the system's ability to process valid avatar uploads.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click the element to initiate the avatar upload process | A file selection dialog or an upload field becomes active |
| 2 | fill | Select a valid JPG image file from the local system | The selected file name is displayed next to the upload field |
| 3 | click | Click the button to submit the selected avatar for upload | The page processes the upload, and a loading indicator may a |
| 4 | assert_text | Verify that a success message confirms the avatar upload | A message indicating successful avatar upload is visible on  |
| 5 | assert_visible | Confirm the newly uploaded JPG image is displayed as the use | The updated avatar image is visible on the profile editing p |

#### TC-50 (ID 607): Verify avatar upload succeeds with a 5MB JPG file


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** boundary | **AC Ref:** AC-1
- **Steps:** 9
- **Description:** This test checks the system's boundary condition for avatar file size. It ensures that an avatar file exactly at the maximum allowed size (5MB) can be successfully uploaded without error.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_url | Verify the user is on the profile editing page as per precon | The browser URL indicates the profile editing page. |
| 2 | assert_visible | Ensure the avatar upload section is visible. | The avatar image or an 'Upload Avatar' button is displayed. |
| 3 | click | Initiate the avatar upload process. | A file selection dialog or an upload widget appears. |
| 4 | fill | Select a 5MB JPG file from the local system. | The selected file name (5MB_avatar.jpg) is displayed near th |
| 5 | click | Confirm the file upload. | The page indicates the upload is in progress or has complete |
| 6 | wait | Wait for the upload process to complete and the UI to update | The page finishes loading the new avatar or displays a confi |
| 7 | assert_visible | Verify that the new 5MB JPG avatar is displayed. | The profile picture area shows the recently uploaded 5MB JPG |
| 8 | assert_text | Verify a success message is displayed. | A 'Avatar updated successfully' or similar confirmation mess |
| 9 | assert_text | Verify no error messages related to file size or type are di | No error messages such as 'File too large' or 'Invalid file  |

#### TC-51 (ID 608): Verify avatar updates immediately across historical leagues


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 7
- **Description:** This test ensures that when a user changes their avatar, the new avatar is immediately reflected in all historical leagues they have participated in. This confirms consistent identity across past activities.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user's profile or settings page where avatar | The user's profile or settings page is displayed |
| 2 | click | Initiate the process to change the user's avatar | An avatar selection modal or page is displayed |
| 3 | click | Select a different avatar for the user's profile | The new avatar is highlighted or selected |
| 4 | click | Confirm and save the new avatar selection | The profile page reloads or updates, displaying the newly se |
| 5 | click | Navigate to the section listing all past leagues the user pa | A page displaying a list of historical leagues is shown |
| 6 | click | Open the details page for one of the historical leagues | The details page for the selected historical league is displ |
| 7 | assert_visible | Verify that the new avatar is immediately reflected in the h | The new avatar is clearly visible for the logged-in user in  |

#### TC-52 (ID 609): Verify avatar updates immediately across active leagues


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 7
- **Description:** This test ensures that when a user changes their avatar, the new avatar is immediately reflected in all active leagues they are currently participating in. This confirms consistent identity across ongoing activities.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Open the user dropdown menu. | A dropdown menu with profile-related options is displayed. |
| 2 | click | Navigate to the user's profile settings page. | The Profile Settings page is displayed, showing the current  |
| 3 | click | Initiate the process to change the user's avatar. | The avatar selection or upload interface (e.g., a modal or n |
| 4 | click | Select a different avatar image. | The new avatar is selected or previewed within the avatar ch |
| 5 | click | Confirm and save the new avatar selection. | The avatar change interface closes, and the new avatar is di |
| 6 | click | Navigate to an active league page where the user is particip | The selected active league's page is displayed, showing leag |
| 7 | assert_visible | Verify that the user's avatar in the active league is the ne | The new avatar is visible for the user within the active lea |

#### TC-53 (ID 610): Verify user can edit First Name, Last Name, and Username


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 8
- **Description:** This test ensures that users can successfully update their personal details including First Name, Last Name, and Username. It verifies the system's ability to save these changes correctly.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a new first name into the First Name field | The First Name field displays 'NewFirstName' |
| 2 | fill | Enter a new last name into the Last Name field | The Last Name field displays 'NewLastName' |
| 3 | fill | Enter a new username into the Username field | The Username field displays 'newusername123' |
| 4 | click | Click the Save Changes button to apply updates | The page attempts to save the profile information |
| 5 | assert_text | Verify that a success message is displayed | A 'Profile updated successfully' message is visible |
| 6 | assert_text | Verify the First Name field still displays the updated value | The First Name field contains 'NewFirstName' |
| 7 | assert_text | Verify the Last Name field still displays the updated value | The Last Name field contains 'NewLastName' |
| 8 | assert_text | Verify the Username field still displays the updated value | The Username field contains 'newusername123' |

#### TC-54 (ID 611): Verify user can edit Bio and update Username with unique value


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 6
- **Description:** This test ensures users can successfully update their Bio and change their Username to a new, unique value. It verifies the system's uniqueness validation for the Username field.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter new text into the Bio field. | The Bio text area displays the entered text. |
| 2 | fill | Enter a new, unique username into the Username field. | The Username input field displays the new unique username. |
| 3 | click | Click the button to save the profile changes. | The page reloads or a success message is displayed. |
| 4 | assert_text | Verify that a success message confirms the profile update. | A 'Profile updated successfully' message is visible on the p |
| 5 | assert_text | Verify the updated Bio text is displayed. | The profile's Bio section shows 'This is my updated bio desc |
| 6 | assert_text | Verify the updated unique Username is displayed. | The profile's Username section shows 'newuniqueuser123'. |

#### TC-55 (ID 612): Verify Email, Phone, DOB, XP, and Tier Badge fields are read-only


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 6
- **Description:** This test ensures that specific profile fields such as Email, Phone, Date of Birth, XP Points, and Tier Badge are displayed as read-only and cannot be edited by the user. This confirms data integrity for these system-managed fields.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Confirm that the profile editing page is fully loaded and di | The profile editing page is visible with all user profile in |
| 2 | assert_visible | Locate the Email field on the profile editing page. | The Email field is visible, displays the user's email addres |
| 3 | assert_visible | Locate the Phone field. | The Phone field is visible, displays the user's phone number |
| 4 | assert_visible | Locate the Date of Birth field. | The Date of Birth field is visible, displays the user's date |
| 5 | assert_visible | Locate the XP Points field. | The XP Points field is visible, displays the user's experien |
| 6 | assert_visible | Locate the Tier Badge field. | The Tier Badge field is visible, displays the user's current |

#### TC-56 (ID 613): Verify profile updates successfully when all mandatory fields are valid


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 8
- **Description:** This test ensures that when all mandatory profile fields are filled with valid data and all validations pass, the system successfully updates the user's profile. This is a positive test for the profile update mechanism.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a valid first name into the mandatory First Name field | The First Name field displays 'John' |
| 2 | fill | Enter a valid last name into the mandatory Last Name field | The Last Name field displays 'Doe' |
| 3 | fill | Enter a new, valid email address into the mandatory Email fi | The Email field displays 'john.doe@example.com' |
| 4 | click | Click the button to submit the profile updates | The page attempts to process the profile update |
| 5 | assert_text | Verify that a success message is displayed after saving | A message indicating successful profile update is visible |
| 6 | assert_text | Verify the First Name field still displays the updated value | The First Name field retains 'John' |
| 7 | assert_text | Verify the Last Name field still displays the updated value | The Last Name field retains 'Doe' |
| 8 | assert_text | Verify the Email field still displays the updated value | The Email field retains 'john.doe@example.com' |

#### TC-57 (ID 614): Verify profile update fails when a mandatory field (First Name) is empty


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-7
- **Steps:** 4
- **Description:** This test ensures the system prevents profile updates if a mandatory field, such as First Name, is left empty. It verifies the validation mechanism for required fields.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Clear the content of the First Name input field, leaving it  | The First Name input field is empty |
| 2 | click | Click the button to submit the profile changes | The system attempts to process the profile update |
| 3 | assert_visible | Verify that an error message is displayed for the empty Firs | An error message like 'First Name is required' or 'This fiel |
| 4 | assert_url | Verify that the user remains on the profile editing page | The browser URL is still the profile editing page URL, indic |

#### TC-58 (ID 615): Verify profile update fails when Username is not unique


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-7
- **Steps:** 6
- **Description:** This test ensures the system prevents profile updates if the provided Username already exists, enforcing the uniqueness validation rule. It verifies the system's rejection behavior for duplicate usernames.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_url | Verify the user is on the profile editing page as per precon | The browser URL indicates the profile editing page |
| 2 | fill | Enter an already existing username into the Username field | The Username field displays 'ExistingUser' |
| 3 | click | Click the Save Changes button to attempt updating the profil | The page attempts to process the profile update |
| 4 | assert_text | Verify an error message indicating the username is not uniqu | An error message 'Username is already taken' or similar is v |
| 5 | assert_url | Verify the URL remains the profile editing page, indicating  | The browser URL is still the profile editing page |
| 6 | assert_visible | Verify the profile editing form is still visible, indicating | The profile editing form and its elements are still displaye |

#### TC-59 (ID 616): Verify system handles null input for a mandatory field (Username) gracefully


- **Story:** US-331 — As a Logged-In User, I can set up my profile and avatar so that I have a consist
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** edge | **AC Ref:** AC-7
- **Steps:** 5
- **Description:** This edge case test verifies that the system gracefully handles attempts to update the profile with a null or absent value for a mandatory field like Username, preventing crashes or data corruption.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Clear the existing value in the Username input field, effect | The Username input field is empty. |
| 2 | click | Click the Save Profile button to submit the form with an emp | The page attempts to process the profile update. |
| 3 | assert_visible | Verify that an error message is displayed for the Username f | An error message indicating the Username is mandatory or can |
| 4 | assert_text | Verify the specific text of the error message for the Userna | The error message explicitly states 'Username is required' o |
| 5 | assert_url | Verify that the user remains on the profile editing page. | The browser URL is still the profile editing page, indicatin |

#### TC-60 (ID 617): Verify Super Admin can create new staff account with valid details


- **Story:** US-332 — As a Super Admin, I can create and manage internal staff accounts and their role
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 9
- **Description:** This test verifies that a Super Admin can successfully create a new staff account by providing all required valid information: email, name, phone number, and an assigned role. It ensures the account creation process functions as expected.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the staff management section | The staff management page is displayed, showing a list of ex |
| 2 | click | Initiate the process to add a new staff member | The 'Create Staff Account' form or page is displayed |
| 3 | fill | Enter a unique and valid email address for the new staff mem | The email input field displays 'newstaff@example.com' |
| 4 | fill | Enter the full name of the new staff member | The name input field displays 'New Staff Member' |
| 5 | fill | Enter a valid phone number for the new staff member | The phone number input field displays '123-456-7890' |
| 6 | select | Select an appropriate role for the new staff member | The 'Role' dropdown displays 'Admin' as the selected option |
| 7 | click | Submit the new staff account details | The system processes the request, and a success message is d |
| 8 | assert_text | Verify that a success message confirms the account creation | A message indicating successful staff account creation is vi |
| 9 | assert_visible | Verify the newly created staff account appears in the staff  | The staff list now includes 'New Staff Member' with the emai |

#### TC-61 (ID 618): Verify activation link is sent to new staff member's email


- **Story:** US-332 — As a Super Admin, I can create and manage internal staff accounts and their role
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 10
- **Description:** This test verifies that upon successful creation of a new staff account, the system automatically sends a time-bound, single-use activation link to the provided email address for password setup. It ensures the onboarding process initiates correctly.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the email client or service where 'newstaff@example.com | The email client login page or inbox is displayed |
| 2 | fill | Enter the new staff member's email address | The email address is entered into the field |
| 3 | fill | Enter the password for the 'newstaff@example.com' email acco | The password is entered into the field |
| 4 | click | Click the login button to access the email inbox | The email inbox for 'newstaff@example.com' is displayed |
| 5 | wait | Wait a few moments for any new emails to appear in the inbox | The inbox content is refreshed |
| 6 | assert_visible | Verify that an activation email has been received | An email with the expected subject line is visible in the in |
| 7 | click | Open the activation email to view its content | The full content of the activation email is displayed |
| 8 | assert_text | Verify the email body contains text indicating account activ | The text 'activate your account' or similar is present in th |
| 9 | assert_text | Verify the email body contains instructions to set a passwor | The text 'click here to set your password' or similar is pre |
| 10 | assert_visible | Verify that a distinct, clickable link is present for accoun | A hyperlink for account activation is clearly visible in the |

#### TC-62 (ID 619): Verify new staff account status is PENDING_ACTIVATION


- **Story:** US-332 — As a Super Admin, I can create and manage internal staff accounts and their role
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 7
- **Description:** This test verifies that immediately after a new staff account is created and before the staff member sets their password via the activation link, the account's status is correctly set to 'PENDING_ACTIVATION'. This ensures proper account lifecycle management.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application login page | The login page is displayed with username/email and password |
| 2 | fill | Enter the Super Admin's email address | The email field shows 'superadmin@example.com' |
| 3 | fill | Enter the Super Admin's password | The password field shows masked characters |
| 4 | click | Click the Login button to sign in | The Super Admin is redirected to the dashboard or admin home |
| 5 | click | Navigate to the staff management section | The Staff Management page is displayed, showing a list of st |
| 6 | assert_visible | Verify the newly created staff account is listed | The row corresponding to 'newstaff@example.com' is visible i |
| 7 | assert_text | Verify the status of the 'newstaff@example.com' account | The status displayed for 'newstaff@example.com' is 'PENDING_ |

#### TC-63 (ID 620): Verify Super Admin can set staff account status to Active


- **Story:** US-332 — As a Super Admin, I can create and manage internal staff accounts and their role
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 5
- **Description:** This test verifies that a Super Admin can successfully change an existing staff account's status to 'Active'. This ensures Super Admins have control over enabling staff access.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the staff management section of the application. | The Staff Accounts list page is displayed. |
| 2 | click | Open the details or edit page for the target staff account. | The staff account details page for 'existingstaff@example.co |
| 3 | select | Change the staff account's status to 'Active'. | The 'Active' option is selected in the Status dropdown. |
| 4 | click | Submit the changes to update the staff account. | A success message is displayed, and the page reloads or redi |
| 5 | assert_text | Verify that the staff account's status is now 'Active'. | The text 'Active' is clearly visible as the status for the s |

#### TC-64 (ID 621): Verify Super Admin can set staff account status to Inactive and revoke access


- **Story:** US-332 — As a Super Admin, I can create and manage internal staff accounts and their role
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 9
- **Description:** This test verifies that a Super Admin can successfully change an existing staff account's status to 'Inactive', and that this action immediately revokes the staff member's access to the system. This ensures immediate security control.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Staff Management section of the admin panel | The Staff Management page is displayed, showing a list of st |
| 2 | click | Locate the staff account 'activeuser@example.com' and click  | The staff account's details page or edit form is displayed |
| 3 | select | Change the account status from 'Active' to 'Inactive' | The 'Account Status' field now shows 'Inactive' |
| 4 | click | Click the button to save the changes to the staff account | A success message is displayed, and the user is redirected b |
| 5 | click | Log out the Super Admin to prepare for verifying access revo | The user is redirected to the login page |
| 6 | fill | Enter the email address of the deactivated staff account | The email field shows 'activeuser@example.com' |
| 7 | fill | Enter the password for the deactivated staff account | The password field shows masked characters |
| 8 | click | Attempt to log in as the deactivated staff account | The system attempts to process the login |
| 9 | assert_text | Verify that an error message indicating inactive status or d | An error message like 'Your account is inactive' or 'Access  |

#### TC-65 (ID 622): Verify Super Admin can modify an existing staff member's role


- **Story:** US-332 — As a Super Admin, I can create and manage internal staff accounts and their role
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 6
- **Description:** This test verifies that a Super Admin can successfully change the assigned role of an existing staff member. This ensures flexibility in managing staff permissions and responsibilities.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the staff management section of the application | The staff list page is displayed, showing a list of existing |
| 2 | fill | Enter the email of the staff member to modify into the searc | The staff list filters to show only the 'opsadmin@example.co |
| 3 | click | Click the edit button to open the staff member's details for | The staff member's profile or edit form is displayed, showin |
| 4 | select | Select 'Super Admin' from the available roles in the dropdow | The 'Role' dropdown now displays 'Super Admin' as the select |
| 5 | click | Click the button to save the updated role | A success message is displayed, and the user is redirected b |
| 6 | assert_text | Verify that the staff member's role has been successfully up | The text 'Super Admin' is visible next to 'opsadmin@example. |

#### TC-66 (ID 623): Verify successful login with valid registered email and password


- **Story:** US-333 — As an F2MX Staff Member, I can securely log in to the Admin Console so that I ca
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 6
- **Description:** This test ensures that a staff member can successfully initiate the login process by providing a valid, registered email and password, confirming the system's basic authentication requirement.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the F2MX application login page. | The login page is displayed, showing input fields for email  |
| 2 | fill | Enter a valid registered staff email address into the email  | The email input field displays the entered email address. |
| 3 | fill | Enter the correct password associated with the staff email. | The password input field displays masked characters. |
| 4 | click | Click the Login button to submit the credentials. | The application attempts to authenticate the user and redire |
| 5 | assert_url | Verify that the browser URL has changed to the staff dashboa | The browser URL ends with '/dashboard' (or similar post-logi |
| 6 | assert_visible | Confirm that the main content of the staff dashboard is visi | Elements specific to the logged-in staff dashboard (e.g., na |

#### TC-67 (ID 624): Verify 2FA enforcement after successful credential entry


- **Story:** US-333 — As an F2MX Staff Member, I can securely log in to the Admin Console so that I ca
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 8
- **Description:** This test confirms that after a staff member enters valid login credentials, the system correctly enforces and prompts for a Two-Factor Authentication (2FA) code, either via email or phone, as a mandatory security step.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the F2MX staff login page | The login page is displayed with fields for email/username a |
| 2 | fill | Enter the valid email/username for a staff account with 2FA  | The email/username field displays the entered value |
| 3 | fill | Enter the correct password for the staff account | The password field displays masked characters |
| 4 | click | Click the Login button to submit credentials | The system processes the login request |
| 5 | assert_visible | Verify that the 2FA verification interface is displayed | A page or modal prompting for a 2FA code is visible |
| 6 | assert_text | Confirm the 2FA prompt indicates where the code was sent (e. | Text like 'Enter the code sent to your email' or 'Enter the  |
| 7 | assert_visible | Verify that an input field for the 2FA code is present | An input field where the user can type the 2FA code is displ |
| 8 | assert_url | Verify the URL reflects the 2FA verification state | The browser URL ends with a path indicating 2FA verification |

#### TC-68 (ID 625): Verify automatic routing to Admin Console upon full successful authentication


- **Story:** US-333 — As an F2MX Staff Member, I can securely log in to the Admin Console so that I ca
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 8
- **Description:** This test ensures that once a staff member has successfully completed both credential entry and 2FA verification, the system automatically redirects them to the F2MX Admin Console, providing seamless access to their operational tools.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the F2MX staff login page. | The login page is displayed, showing fields for email and pa |
| 2 | fill | Enter the registered staff email address. | The email input field displays the entered email. |
| 3 | fill | Enter the correct password for the staff account. | The password input field displays masked characters. |
| 4 | click | Click the Login button to proceed. | The system navigates to the Two-Factor Authentication (2FA)  |
| 5 | fill | Enter a valid 2FA code (e.g., from an authenticator app). | The 2FA code input field displays the entered code. |
| 6 | click | Click the Verify button to complete 2FA. | The system processes the 2FA code and automatically redirect |
| 7 | assert_url | Verify that the browser URL has changed to the F2MX Admin Co | The browser URL ends with '/admin/console', indicating succe |
| 8 | assert_visible | Confirm that elements specific to the F2MX Admin Console are | The Admin Console interface is fully loaded and displayed, c |

#### TC-69 (ID 626): Verify login attempt is blocked for an inactive staff account


- **Story:** US-333 — As an F2MX Staff Member, I can securely log in to the Admin Console so that I ca
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 6
- **Description:** This test confirms that the system correctly identifies and blocks login attempts from staff accounts that have an 'Inactive' or 'Deactivated' status, preventing unauthorized access and maintaining security.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the F2MX staff login page. | The login page is displayed with fields for email and passwo |
| 2 | fill | Enter the email address of the inactive staff account. | The email input field displays the entered email address. |
| 3 | fill | Enter the password for the inactive staff account. | The password input field displays masked characters. |
| 4 | click | Click the Login button to attempt to log in. | The system processes the login attempt. |
| 5 | assert_text | Verify that an error message indicating the account is inact | An error message like 'Your account is inactive. Please cont |
| 6 | assert_url | Verify that the user remains on the login page. | The browser URL is still the login page URL. |

#### TC-70 (ID 627): Verify logout option redirects to the login screen


- **Story:** US-333 — As an F2MX Staff Member, I can securely log in to the Admin Console so that I ca
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 8
- **Description:** This test ensures that the logout functionality correctly terminates the user's session and redirects them back to the initial login screen, providing a secure way to end an active session.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify the staff member is currently logged into the F2MX Ad | The admin console interface is visible, indicating an active |
| 2 | click | Click on the user profile icon or dropdown to reveal the use | A dropdown menu containing user-related options is displayed |
| 3 | click | Select the 'Logout' option from the displayed user menu | The application initiates the logout process |
| 4 | wait | Wait for the application to redirect to the login page | The browser navigates to the login screen |
| 5 | assert_url | Verify the browser URL has changed to the login page's path | The URL ends with '/login' or a similar login endpoint |
| 6 | assert_visible | Confirm the Email input field is visible on the page | The Email input field is displayed, indicating the login scr |
| 7 | assert_visible | Confirm the Password input field is visible on the page | The Password input field is displayed |
| 8 | assert_visible | Confirm the Login button is visible on the page | The Login button is displayed, allowing a user to log in aga |

#### TC-71 (ID 628): Verify all registered user accounts are displayed in a searchable list


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 4
- **Description:** This test ensures that an F2MX Admin can successfully access the Admin Console and view a comprehensive list of all registered user accounts, confirming the initial display functionality and presence of search capabilities.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the Admin Console | The User Accounts page is displayed |
| 2 | assert_visible | Verify that a list of registered user accounts is visible on | A list containing multiple user accounts is displayed |
| 3 | assert_visible | Confirm that a search input field is present for filtering u | A search input field is clearly visible on the page |
| 4 | assert_text | Verify that common user attributes like 'Email' are displaye | The 'Email' column header or label is visible within the use |

#### TC-72 (ID 629): Verify user accounts list is filterable within the Admin Console


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 7
- **Description:** This test confirms that the user account list presented to the F2MX Admin is not only searchable but also provides filtering capabilities, allowing for more refined data exploration.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the User Accounts management page within the Adm | The User Accounts list page is displayed, showing a list of  |
| 2 | assert_visible | Verify that filtering options are available on the page | A filter control (e.g., 'Filter by Status', 'Filter by Role' |
| 3 | click | Open the status filter options | A list of status options (e.g., 'Active', 'Inactive', 'Pendi |
| 4 | click | Select 'Inactive' to filter the user list by status | The filter dropdown closes, and the user accounts list updat |
| 5 | assert_text | Verify that only user accounts with an 'Inactive' status are | All displayed user accounts have a status of 'Inactive', and |
| 6 | click | Clear the applied 'Inactive' status filter | The filter is removed, and the user accounts list updates |
| 7 | assert_visible | Confirm that the full list of user accounts, including those | The user accounts list now includes users with all statuses, |

#### TC-73 (ID 630): Verify search by Username, Email, or Phone Number with partial and exact matching


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 12
- **Description:** This test ensures that the search functionality correctly identifies user accounts when searching by Username, Email, or Phone Number, supporting both partial and exact matches.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter the exact username 'JohnDoe' into the search field and | The search results display only the user 'JohnDoe'. |
| 2 | assert_text | Verify that 'JohnDoe' is the only user displayed in the sear | The search results table shows 'JohnDoe' and indicates a sin |
| 3 | fill | Enter a partial username 'John' into the search field and cl | The search results are updated. |
| 4 | assert_text | Verify that 'JohnDoe' is included in the search results for  | The search results table includes 'JohnDoe' among the displa |
| 5 | fill | Enter the exact email address 'john.doe@example.com' into th | The search results display only the user 'JohnDoe'. |
| 6 | assert_text | Verify that 'JohnDoe' is the only user displayed for an exac | The search results table shows 'JohnDoe' and indicates a sin |
| 7 | fill | Enter a partial email address 'john.doe' into the search fie | The search results are updated. |
| 8 | assert_text | Verify that 'JohnDoe' is included in the search results for  | The search results table includes 'JohnDoe' among the displa |
| 9 | fill | Enter the exact phone number '555-123-4567' into the search  | The search results display only the user 'JohnDoe'. |
| 10 | assert_text | Verify that 'JohnDoe' is the only user displayed for an exac | The search results table shows 'JohnDoe' and indicates a sin |

*… and 2 more steps*


#### TC-74 (ID 631): Verify search by Username, Email, or Phone Number supports case-insensitive matching


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 12
- **Description:** This test confirms that the search functionality is robust enough to handle variations in casing, ensuring that administrators can find accounts regardless of how they type the search query.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the admin console | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter a known username in all lowercase (different casing fr | The search input field displays 'johndoe'. |
| 3 | click | Click the Search button to filter the user list | The user list updates to show search results. |
| 4 | assert_text | Verify that the user 'JohnDoe' is found and displayed in the | The user 'JohnDoe' (or their full user entry) is visible in  |
| 5 | click | Clear the current search query to prepare for the next test | The search input field is empty, and the full list of users  |
| 6 | fill | Enter a known email address in all uppercase (different casi | The search input field displays 'JOHN.DOE@EXAMPLE.COM'. |
| 7 | click | Click the Search button to filter the user list | The user list updates to show search results. |
| 8 | assert_text | Verify that the user with email 'john.doe@example.com' is fo | The user with email 'john.doe@example.com' (or their full us |
| 9 | click | Clear the current search query | The search input field is empty, and the full list of users  |
| 10 | fill | Enter a known phone number into the search field | The search input field displays '555-123-4567'. |

*… and 2 more steps*


#### TC-75 (ID 632): Verify filters for Account Status, Verification Status, Tier, and Joined Date range are functional


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 12
- **Description:** This test validates that all specified filtering options (Account Status, Verification Status, Tier, and Joined Date range) are present and correctly apply filters to the user account list.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the User Accounts management page in the Admin C | The User Accounts page is displayed, showing a list of all u |
| 2 | assert_visible | Verify the 'Account Status' filter dropdown is visible. | The 'Account Status' filter dropdown is present on the page. |
| 3 | assert_visible | Verify the 'Verification Status' filter dropdown is visible. | The 'Verification Status' filter dropdown is present on the  |
| 4 | assert_visible | Verify the 'Tier' filter dropdown is visible. | The 'Tier' filter dropdown is present on the page. |
| 5 | assert_visible | Verify the 'Joined Date range' filter control is visible. | The 'Joined Date range' filter control is present on the pag |
| 6 | select | Select 'Active' from the Account Status filter. | The user list updates to show only accounts with 'Active' st |
| 7 | select | Select 'Verified' from the Verification Status filter. | The user list updates to show only accounts that are 'Active |
| 8 | select | Select 'Premium' from the Tier filter. | The user list updates to show only accounts that are 'Active |
| 9 | select | Select 'Last 30 days' from the Joined Date range filter. | The user list updates to show only accounts that are 'Active |
| 10 | click | Click the 'Clear Filters' button to reset all applied filter | All filter selections are cleared, and the user list reverts |

*… and 2 more steps*


#### TC-76 (ID 633): Verify all required key user details are displayed for each account


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 9
- **Description:** This test ensures that the user account list correctly presents all specified key details for each user, providing administrators with comprehensive information at a glance.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user accounts management section | The user accounts list page is displayed |
| 2 | assert_visible | Verify that the list of user accounts is visible on the page | A table or list containing user accounts is present |
| 3 | assert_text | Verify that the 'User ID' detail is displayed for the first  | The 'User ID' label and its corresponding value are visible  |
| 4 | assert_text | Verify that the 'Username' detail is displayed for the first | The 'Username' label and its corresponding value are visible |
| 5 | assert_text | Verify that the 'Email' detail is displayed for the first us | The 'Email' label and its corresponding value are visible wi |
| 6 | assert_text | Verify that the 'Status' detail (e.g., Active, Inactive) is  | The 'Status' label and its corresponding value are visible w |
| 7 | assert_text | Verify that the 'Role' detail (e.g., Admin, Standard User) i | The 'Role' label and its corresponding value are visible wit |
| 8 | screenshot | Capture a screenshot of the user accounts list to document d | A screenshot of the user accounts list is taken |
| 9 | wait | Manually inspect other user accounts in the list to ensure a | All displayed user accounts show their respective 'User ID', |

#### TC-77 (ID 634): Verify pagination controls function correctly for large user lists


- **Story:** US-334 — As an F2MX Admin, I can view and filter user accounts so that I can efficiently 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 6
- **Description:** This test confirms that when a large number of user accounts are present, the system correctly displays pagination controls and allows the administrator to navigate between different pages of the user list.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the admin console | The user list page is displayed, showing a list of user acco |
| 2 | assert_visible | Verify that pagination controls are present at the bottom of | Pagination controls are clearly visible, indicating multiple |
| 3 | click | Click the 'Next' button to advance to the subsequent page of | The user list updates to display a different set of users, a |
| 4 | assert_text | Verify that the page number indicator shows the correct next | The page number indicator displays '2' (or the next sequenti |
| 5 | click | Click the 'Previous' button to return to the prior page of u | The user list updates to display the initial set of users, a |
| 6 | assert_text | Verify that the page number indicator shows the correct prev | The page number indicator displays '1' (or the initial page  |

#### TC-78 (ID 635): Verify Support Admin can unlock a locked user account


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 5
- **Description:** This test ensures that a Support Admin can successfully unlock a user account that was automatically locked due to failed login attempts. It confirms the system's ability to restore access for legitimate users through authorized personnel.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the section for managing user accounts. | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter the username of the locked account into the search fie | The search results are filtered, showing 'user123'. |
| 3 | assert_text | Verify that the account status for 'user123' is currently 'L | The status displayed next to 'user123' is 'Locked'. |
| 4 | click | Initiate the unlock process for the 'user123' account. | A confirmation dialog appears, or the account status immedia |
| 5 | assert_text | Verify that the account status for 'user123' has changed to  | The status displayed next to 'user123' is 'Active' or 'Unloc |

#### TC-79 (ID 636): Verify Super Admin can unlock a locked user account


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 6
- **Description:** This test confirms that a Super Admin can successfully unlock a user account that was automatically locked due to failed login attempts. It validates the highest level of administrative privilege for account recovery.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the F2MX Admin po | The user list or user management page is displayed. |
| 2 | fill | Enter the username of the locked account ('user456') into th | The user list filters to display 'user456'. |
| 3 | assert_text | Verify that the user account 'user456' is currently displaye | The status for 'user456' is clearly shown as 'Locked'. |
| 4 | click | Click the action to unlock the 'user456' account. | A confirmation dialog appears, or the status immediately beg |
| 5 | click | Confirm the unlock action if a confirmation dialog is displa | The confirmation dialog closes, and the unlock process compl |
| 6 | assert_text | Verify that the user account 'user456' is now displayed with | The status for 'user456' is clearly shown as 'Active' or 'Un |

#### TC-80 (ID 637): Verify Ops Admin can suspend a user account for a defined duration


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 8
- **Description:** This test ensures that an Ops Admin can successfully suspend a user account for a specified period. It verifies the system's functionality for temporary account restriction by authorized personnel.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the User Management section of the admin portal | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter the username 'user789' into the search field | The search results are filtered, displaying 'user789' in the |
| 3 | click | Click on the 'user789' entry to view their details | The user details page for 'user789' is displayed |
| 4 | click | Click the button to initiate the account suspension process | A 'Suspend Account' dialog or form appears, prompting for su |
| 5 | select | Select '7 Days' as the duration for the account suspension | The selected duration '7 Days' is displayed in the field |
| 6 | click | Confirm the suspension with the specified duration | The suspension dialog closes, and a success message is displ |
| 7 | assert_text | Verify that the user's account status has changed to 'Suspen | The text 'Suspended' is visible next to the account status |
| 8 | assert_text | Verify that the specified suspension duration is displayed | The suspension details indicate the account is suspended for |

#### TC-81 (ID 638): Verify Super Admin can suspend a user account for a custom duration


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 9
- **Description:** This test confirms that a Super Admin can successfully suspend a user account for a custom-defined duration. It validates the system's flexibility in applying temporary account restrictions by the highest-privileged administrators.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the User Management section of the F2MX Admin po | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter 'user101' into the search field to find the target use | The user list filters to show 'user101' |
| 3 | click | Click on the user 'user101' to view their details or actions | The user detail page or a user action menu for 'user101' is  |
| 4 | click | Initiate the account suspension process for 'user101' | A suspension configuration dialog or section appears |
| 5 | click | Select the option to define a custom suspension duration | Input fields for custom duration (e.g., days, hours, minutes |
| 6 | fill | Enter '7' into the days input field for the custom duration | The days input field shows '7' |
| 7 | click | Confirm and apply the custom duration suspension | A success message is displayed, and the suspension dialog cl |
| 8 | assert_text | Verify that 'user101''s account status has changed to 'Suspe | The user status clearly indicates 'Suspended' |
| 9 | assert_text | Verify that suspension details, including an end date, are d | Text indicating 'Suspended until' followed by a date approxi |

#### TC-82 (ID 639): Verify Super Admin can suspend a user account for minimum allowed duration


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** boundary | **AC Ref:** AC-4
- **Steps:** 9
- **Description:** This test verifies the system's behavior when a Super Admin attempts to suspend a user account for the shortest possible valid duration. It ensures that the system correctly processes boundary values for suspension periods.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the User Management section of the F2MX Admin po | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter the username 'user112' into the search field | The search field displays 'user112' |
| 3 | click | Initiate the search for 'user112' | The user list is filtered, showing 'user112' as a result |
| 4 | click | Click the suspend action for 'user112' | A 'Suspend User' confirmation or configuration dialog appear |
| 5 | fill | Enter '1' as the suspension duration | The duration input field shows '1' |
| 6 | select | Select 'Minutes' from the duration unit dropdown | The duration unit dropdown displays 'Minutes' |
| 7 | click | Confirm the suspension for the specified duration | The dialog closes, and a success message is displayed |
| 8 | assert_text | Verify that the status of 'user112' has changed to 'Suspende | The user 'user112' is listed with a 'Suspended' status |
| 9 | assert_text | Verify a confirmation message indicating the successful susp | A message confirming the suspension duration is visible |

#### TC-83 (ID 640): Verify Super Admin can permanently ban a user account


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 8
- **Description:** This test ensures that a Super Admin can successfully permanently ban a user account. It validates the system's critical functionality for enforcing severe policy violations by the highest-privileged administrators.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the User Management section of the F2MX Admin po | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter the username 'user131' into the search field | The search results are filtered to show 'user131' |
| 3 | click | Click on the user 'user131' to view their details | The User Details page for 'user131' is displayed |
| 4 | click | Click the 'Actions' dropdown or button to reveal available a | A menu of actions, including 'Ban User', is displayed |
| 5 | click | Select the 'Permanently Ban User' option from the actions me | A confirmation dialog for banning the user appears |
| 6 | click | Click the 'Confirm Ban' button to finalize the action | The confirmation dialog closes, and a success message is dis |
| 7 | assert_text | Verify that the user's status has changed to 'Permanently Ba | The user's status is clearly displayed as 'Permanently Banne |
| 8 | assert_text | Verify a success message confirming the ban is displayed | A notification confirms that 'user131' has been permanently  |

#### TC-84 (ID 641): Verify active user is immediately logged out upon account suspension


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 9
- **Description:** This test verifies that a user who is actively logged in is immediately logged out when their account is suspended by an administrator. This ensures prompt enforcement of account status changes for security and policy compliance.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_url | Verify 'user141' is currently logged into the F2MX applicati | The browser URL indicates the user is on the dashboard or an |
| 2 | assert_visible | Confirm 'user141' is logged in and their session is active. | Elements indicating 'user141' is logged in are visible on th |
| 3 | navigate | As the Ops Admin, navigate to the User Management section in | The User Management page is displayed, showing a list of use |
| 4 | fill | Search for 'user141' in the user list. | The user list filters to show 'user141'. |
| 5 | click | Initiate the account suspension for 'user141'. | A confirmation dialog for account suspension appears. |
| 6 | click | Confirm the account suspension. | A success message for account suspension is displayed, and ' |
| 7 | navigate | Switch back to the 'user141' browser session and attempt to  | The user is immediately redirected to the login page, indica |
| 8 | assert_url | Verify the user is on the login page. | The browser URL ends with '/login' or '/signin'. |
| 9 | assert_visible | Confirm the login form elements are visible. | The Email and Password input fields, along with the Login bu |

#### TC-85 (ID 642): Verify suspended user is blocked from logging in


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 6
- **Description:** This test confirms that a user whose account has been suspended is prevented from logging into the system. It ensures that account status changes effectively restrict access as intended.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application login page | The login page is displayed with email and password input fi |
| 2 | fill | Enter the email address of the suspended user | The email input field displays 'user151@example.com' |
| 3 | fill | Enter the password for the suspended user | The password input field displays masked characters |
| 4 | click | Click the Login button to attempt login | The system attempts to process the login request |
| 5 | assert_url | Verify that the user remains on the login page or is redirec | The browser URL is still '/login', indicating login failure |
| 6 | assert_text | Verify that an error message indicating account suspension i | A visible error message states 'Your account has been suspen |

#### TC-86 (ID 643): Verify account status change requires a reason


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-8
- **Steps:** 9
- **Description:** This test ensures that any attempt to change a user's account status (e.g., unlock, suspend, ban) necessitates providing a reason. This validates the system's enforcement of audit trail requirements.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the admin portal. | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter the username 'user161' into the search field. | The search field displays 'user161'. |
| 3 | click | Initiate the search for the specified user. | Search results are displayed, with 'user161' visible in the  |
| 4 | click | Select 'user161' to view their detailed profile. | The user profile page for 'user161' is displayed, showing th |
| 5 | click | Initiate the process to change the user's account status fro | A modal or form appears, prompting for a reason for the stat |
| 6 | click | Attempt to submit the status change without providing a reas | An error message is displayed, indicating that the 'Reason'  |
| 7 | fill | Enter a valid reason into the 'Reason for change' input fiel | The 'Reason for change' field displays the entered text. |
| 8 | click | Submit the status change with the provided reason. | The status change is successfully processed, and the modal/f |
| 9 | assert_text | Verify that 'user161's account status has been updated to 'A | The user's account status is displayed as 'Active' or 'Unloc |

#### TC-87 (ID 644): Verify audit log records all required details for account status change


- **Story:** US-335 — As an F2MX Admin, I can manage user account statuses (unlock, suspend, ban) so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-9
- **Steps:** 9
- **Description:** This test confirms that every account status change action is comprehensively recorded in the audit log, including the Admin ID, Target User ID, Action Type, Timestamp, and Reason. This ensures full traceability and accountability for administrative actions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the User Management section of the F2MX Admin po | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter 'user171' into the search field to locate the target u | The user list is filtered, displaying 'user171' |
| 3 | click | Click on 'user171' to open their account details page | The account details page for 'user171' is displayed |
| 4 | click | Initiate the process to change the user's account status | A modal or form for changing account status appears |
| 5 | select | Select 'Suspended' as the new account status | The dropdown displays 'Suspended' |
| 6 | fill | Provide a reason for the account status change | The reason text 'Temporary suspension due to inactivity.' is |
| 7 | click | Submit the account status change | A success message is displayed, and 'user171''s status is up |
| 8 | navigate | Navigate to the Audit Log section of the F2MX Admin portal | The Audit Log page is displayed, showing a chronological lis |
| 9 | assert_text | Verify that the audit log contains an entry for the status c | The audit log entry clearly shows 'ops_admin_001' as the Adm |

#### TC-88 (ID 645): Verify Support Admin can force password reset for a user


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 7
- **Description:** This test ensures that a user with 'Support Admin' role can successfully initiate a password reset for another user account. This is critical for security incident response and administrative control.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the application | The user management page is displayed, showing a list of use |
| 2 | fill | Enter the username of the target user ('user123') into the s | The search field displays 'user123' |
| 3 | click | Initiate the search for the target user | The search results display 'user123' in the list |
| 4 | click | Click on the target user's entry to view their details or ac | The user details page for 'user123' is displayed |
| 5 | click | Click the option to force a password reset for 'user123' | A confirmation dialog or a success message appears |
| 6 | click | Confirm the password reset action | The confirmation dialog closes, and a success notification i |
| 7 | assert_text | Verify that a success message indicating the password reset  | A message like 'Password reset initiated successfully' or 'U |

#### TC-89 (ID 646): Verify Super Admin can force password reset for a user


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 6
- **Description:** This test ensures that a user with 'Super Admin' role can successfully initiate a password reset for another user account. This verifies administrative control over user security.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the application | The user list page is displayed, showing all active user acc |
| 2 | fill | Enter the username of the target user ('user456') into the s | The user list filters to show 'user456' as the primary resul |
| 3 | click | Open the action menu for the target user 'user456' | A dropdown menu with administrative actions for 'user456' is |
| 4 | click | Select the option to initiate a password reset for 'user456' | A confirmation dialog for the password reset action appears |
| 5 | click | Confirm the password reset action in the dialog | The confirmation dialog closes, and a success notification i |
| 6 | assert_text | Verify that a success message confirming the password reset  | A clear message indicating successful password reset initiat |

#### TC-90 (ID 647): Verify user is redirected to mandatory password change after force reset


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 9
- **Description:** This test confirms that after an admin forces a password reset, the affected user is immediately redirected to a mandatory password change screen upon their next successful login attempt. This ensures security enforcement.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application login page | The login page is displayed with username/email and password |
| 2 | fill | Enter the username of the account with the forced password r | The username field shows 'user789' |
| 3 | fill | Enter the user's current password (before the forced reset) | The password field shows masked characters |
| 4 | click | Click the Login button to attempt to log in | The user is redirected to a password change page instead of  |
| 5 | assert_url | Verify the browser URL indicates a password change page (e.g | The URL ends with or contains '/password-change' or similar |
| 6 | assert_visible | Verify the 'New Password' input field is visible on the page | The 'New Password' field is displayed |
| 7 | assert_visible | Verify the 'Confirm New Password' input field is visible on  | The 'Confirm New Password' field is displayed |
| 8 | assert_visible | Verify a button to submit the new password is visible | A 'Change Password' or 'Submit' button is displayed |
| 9 | assert_text | Verify a message indicating a mandatory password change is d | Text like 'Mandatory Password Change' or 'Your password has  |

#### TC-91 (ID 648): Verify user cannot bypass mandatory password change after force reset


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-3
- **Steps:** 5
- **Description:** This test ensures that a user, after a forced password reset, cannot bypass the mandatory password change screen by attempting to navigate directly to another application page. The system must enforce the password change before granting full access.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_url | Verify the user is currently on the mandatory password chang | The browser URL indicates the mandatory password change page |
| 2 | assert_visible | Confirm the password change form is displayed | The 'New Password' and 'Confirm New Password' fields, along  |
| 3 | navigate | Attempt to navigate directly to an internal application page | The system attempts to load the dashboard page |
| 4 | assert_url | Verify the user is redirected back to or remains on the mand | The browser URL is still the mandatory password change page  |
| 5 | assert_text | Verify a message indicating the mandatory password change is | A message like 'You must change your password before proceed |

#### TC-92 (ID 649): Verify mandatory password change rejects invalid new password


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** negative | **AC Ref:** AC-3
- **Steps:** 6
- **Description:** This test confirms that when a user is on the mandatory password change screen after a forced reset, the system properly validates the new password input and rejects invalid formats. This ensures the new password meets security requirements.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter the current (temporary) password into the Current Pass | The Current Password field displays the entered password (ma |
| 2 | fill | Enter an invalid new password (e.g., too short) into the New | The New Password field displays the entered password (masked |
| 3 | fill | Re-enter the same invalid new password into the Confirm New  | The Confirm New Password field displays the entered password |
| 4 | click | Click the Change Password button to submit the new password. | The system attempts to process the password change. |
| 5 | assert_text | Verify that an error message indicating the password does no | An error message like 'Password must be at least 8 character |
| 6 | assert_url | Verify that the user remains on the mandatory password chang | The browser URL indicates the user is still on the /change-p |

#### TC-93 (ID 650): Verify Super Admin can initiate soft delete of a user account


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 7
- **Description:** This test ensures that a user with 'Super Admin' role can successfully initiate a soft delete for another user account. This is crucial for compliance with data privacy regulations.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user management section of the application | The user management page is displayed, showing a list of use |
| 2 | fill | Enter the target user's username into the search field | The search results are filtered to show 'user131' |
| 3 | click | Initiate the delete action for the target user | A confirmation dialog for user deletion is displayed |
| 4 | assert_text | Verify the confirmation message for soft deletion | The dialog text confirms a soft delete action |
| 5 | click | Confirm the soft deletion of the user account | The confirmation dialog closes, and the user list updates |
| 6 | assert_text | Verify that 'user131' is now marked as 'Soft Deleted' | The status of 'user131' clearly indicates 'Soft Deleted' |
| 7 | assert_visible | Verify a success notification is displayed | A message like 'User user131 has been soft deleted successfu |

#### TC-94 (ID 651): Verify soft deleted user record is marked as 'Deleted'


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 3
- **Description:** This test confirms that after a soft delete operation, the target user's record status is updated to 'Deleted' within the system. This is essential for tracking account status and compliance.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Admin User Management page | The User Management page is displayed, showing a list of use |
| 2 | fill | Enter the username 'user142' into the search field | The search results are filtered to display 'user142' in the  |
| 3 | assert_text | Verify that the status displayed for 'user142' is 'Deleted' | The status for 'user142' is clearly marked as 'Deleted' on t |

#### TC-95 (ID 652): Verify PII anonymization and historical data integrity after soft delete


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 11
- **Description:** This test ensures that after a soft delete, the user's Personally Identifiable Information (PII) such as email and name is anonymized, while associated historical data (e.g., activity logs, orders) remains intact and linked to the anonymized record. This balances privacy with data integrity.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the administrator login page of the application | The admin login page is displayed |
| 2 | fill | Enter valid administrator username | The username field is populated |
| 3 | fill | Enter valid administrator password | The password field is populated with masked characters |
| 4 | click | Click the Login button to access the admin dashboard | The administrator dashboard is displayed |
| 5 | click | Navigate to the user management area | The user list or user management page is displayed |
| 6 | fill | Search for the soft-deleted user using their original identi | Search results are filtered, showing the 'user153' entry |
| 7 | click | Click on the soft-deleted user's entry to view their details | The user detail page for 'user153' is displayed |
| 8 | assert_text | Verify that the user's email address is anonymized (e.g., re | The email field displays an anonymized value, not the origin |
| 9 | assert_text | Verify that the user's name is anonymized | The name field displays an anonymized value, not the origina |
| 10 | click | Navigate to the historical data section for the soft-deleted | The historical data section (e.g., activity logs, order hist |

*… and 1 more steps*


#### TC-96 (ID 653): Verify force password reset actions require a reason and are audit logged


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 11
- **Description:** This test confirms that when an admin forces a password reset, a reason for the action is required and the entire event, including the reason, is recorded in the system's audit log. This ensures accountability and traceability for security actions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user management page in the admin panel | The user management page is displayed, showing a list of use |
| 2 | fill | Enter the target user's identifier 'user164' into the search | The user list is filtered, showing 'user164' |
| 3 | click | Click on the user 'user164' to view their details or actions | The user detail page or a context menu for 'user164' is disp |
| 4 | click | Initiate the force password reset action for 'user164' | A confirmation dialog or a form for password reset appears |
| 5 | assert_visible | Verify that a 'Reason' field is present in the password rese | The 'Reason' input field is visible |
| 6 | click | Attempt to confirm the password reset without providing a re | An error message indicating that the 'Reason' field is requi |
| 7 | fill | Enter a reason for the password reset | The 'Reason' field displays the entered text |
| 8 | click | Confirm the password reset with the provided reason | A success message is displayed, and the dialog closes |
| 9 | navigate | Navigate to the system's audit log page | The audit log page is displayed, showing recent system event |
| 10 | fill | Search for audit log entries related to 'user164' | The audit log is filtered, showing entries for 'user164' |

*… and 1 more steps*


#### TC-97 (ID 654): Verify soft delete actions require a reason and are audit logged


- **Story:** US-336 — As an F2MX Admin, I can force password resets and soft delete user accounts so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-8
- **Steps:** 9
- **Description:** This test confirms that when an admin performs a soft delete, a reason for the action is required and the entire event, including the reason, is recorded in the system's audit log. This ensures accountability and traceability for data privacy actions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the User Management page. | The User Management page is displayed, showing a list of use |
| 2 | fill | Search for the target user 'user175'. | The user list is filtered, showing 'user175'. |
| 3 | click | Initiate the soft delete action for 'user175'. | A confirmation modal or prompt appears, requesting a reason  |
| 4 | fill | Enter a valid reason for the soft delete. | The reason input field displays the entered text. |
| 5 | click | Confirm the soft delete action. | The modal closes, and 'user175' is marked as soft-deleted (e |
| 6 | navigate | Navigate to the Audit Log page. | The Audit Log page is displayed, showing recent system event |
| 7 | fill | Search or filter the audit log for events related to 'user17 | The audit log displays entries related to 'user175'. |
| 8 | assert_text | Verify that an audit log entry exists for the 'Soft Delete'  | An audit log entry clearly indicates a 'Soft Delete' action  |
| 9 | assert_text | Verify that the audit log entry includes the exact reason pr | The audit log entry details contain the reason 'User request |

#### TC-98 (ID 655): Verify user is redirected to Mobile Leagues module after successful login


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** critical | **Category:** smoke
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 6
- **Description:** This test verifies that upon successful authentication, the system correctly redirects the user to the Mobile Leagues module, ensuring the primary entry point for league management is accessible.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the application's login page | The login page is displayed with fields for email and passwo |
| 2 | fill | Enter a valid email address into the email field | The email field displays the entered email address |
| 3 | fill | Enter the correct password for the user | The password field displays masked characters |
| 4 | click | Click the Login button to submit credentials | The system attempts to log in the user |
| 5 | assert_url | Verify the browser URL redirects to the Mobile Leagues modul | The browser URL ends with '/mobile-leagues' |
| 6 | assert_visible | Confirm that the Mobile Leagues module content is displayed | The 'Mobile Leagues' title or a key element of the module is |

#### TC-99 (ID 656): Verify display of Total Active and Upcoming Leagues counts


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 4
- **Description:** This test ensures that the Mobile Leagues module accurately displays the aggregated counts for 'Total Active Leagues' and 'Total Upcoming Leagues', providing a quick overview of the user's current and future participation.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's dashboard or home page after login | The dashboard page is displayed |
| 2 | click | Click on the link or module to access the Mobile Leagues sec | The Mobile Leagues module or page is displayed |
| 3 | assert_visible | Verify that the aggregated count for 'Total Active Leagues'  | The 'Total Active Leagues' count is displayed, showing a num |
| 4 | assert_visible | Verify that the aggregated count for 'Total Upcoming Leagues | The 'Total Upcoming Leagues' count is displayed, showing a n |

#### TC-100 (ID 657): Verify display of Total Completed Leagues count


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 2
- **Description:** This test confirms that the Mobile Leagues module correctly displays the aggregated count for 'Total Completed Leagues', allowing users to track their past participation.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click the navigation item to access the Mobile Leagues modul | The Mobile Leagues page or module is displayed |
| 2 | assert_visible | Verify that the 'Total Completed Leagues' count is visible o | The 'Total Completed Leagues' count is displayed, showing a  |

#### TC-101 (ID 658): Verify filtering 'My Leagues' list by Active status


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 6
- **Description:** This test ensures that selecting a league status (e.g., 'Active') from the overview section correctly filters the 'My Leagues' list to display only leagues matching that status.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Open the filter options for league status. | A list of status options (e.g., 'Active', 'Upcoming', 'Compl |
| 2 | click | Select 'Active' to filter the 'My Leagues' list. | The filter dropdown closes, and the 'My Leagues' list update |
| 3 | assert_text | Verify that the filter now indicates 'Active' is the selecte | The filter component clearly shows 'Active' as the current s |
| 4 | assert_text | Verify that all displayed leagues in the 'My Leagues' list h | Every visible league entry in the list shows an 'Active' sta |
| 5 | assert_text | Verify that no leagues with 'Upcoming' status are visible in | The word 'Upcoming' is not present as a status indicator for |
| 6 | assert_text | Verify that no leagues with 'Completed' status are visible i | The word 'Completed' is not present as a status indicator fo |

#### TC-102 (ID 659): Verify league card displays status, name, and type


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** medium | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 5
- **Description:** This test confirms that each league card presented in the 'My Leagues' list correctly renders essential information including the league's status, name, and type, providing users with key details at a glance.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the 'My Leagues' page | The 'My Leagues' page loads, displaying a list of league car |
| 2 | assert_visible | Verify that at least one league card is displayed on the pag | A league card element is visible, indicating leagues are loa |
| 3 | assert_visible | Verify that the status (e.g., 'Active', 'Pending') is displa | The league's current status is clearly visible on the card |
| 4 | assert_visible | Verify that the name of the league is displayed on a league  | The league's name is prominently displayed on the card |
| 5 | assert_visible | Verify that the type of the league (e.g., 'Fantasy Football' | The league's type is visible on the card, providing context |

#### TC-103 (ID 660): Verify league card displays other relevant information


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** medium | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 5
- **Description:** This test ensures that league cards include additional relevant details beyond basic status, name, and type, such as start date, end date, or location, enhancing the user's understanding of each league.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Leagues overview page where league cards are | The Leagues overview page loads, showing a list of league ca |
| 2 | assert_visible | Verify that a league card with comprehensive details is pres | The 'Premier League 2024' card is visible |
| 3 | assert_visible | Check if the league's start date is displayed on the card | The start date is visible within the league card |
| 4 | assert_visible | Check if the league's end date is displayed on the card | The end date is visible within the league card |
| 5 | assert_visible | Check if the league's location is displayed on the card | The location is visible within the league card |

#### TC-104 (ID 661): Verify empty state message and action buttons for user with no leagues


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 5
- **Description:** This test confirms that if a user is not associated with any leagues, the system displays an informative empty state message along with relevant action buttons to guide the user, improving usability.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the 'My Leagues' or equivalent page where league | The page for managing leagues is loaded. |
| 2 | assert_visible | Verify that an empty state message is displayed. | An empty state message is visible on the page. |
| 3 | assert_text | Verify the content of the empty state message. | The empty state message displays the expected text. |
| 4 | assert_visible | Verify that the 'Create New League' action button is visible | The 'Create New League' button is displayed. |
| 5 | assert_visible | Verify that the 'Join Existing League' action button is visi | The 'Join Existing League' button is displayed. |

#### TC-105 (ID 662): Verify empty state message when user's league data is null or empty


- **Story:** US-337 — As a User, I can view and manage my active, upcoming, and completed leagues so t
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** edge | **AC Ref:** AC-7
- **Steps:** 4
- **Description:** This edge case test ensures that the system gracefully handles scenarios where a user's league data is explicitly null or an empty array from the backend, correctly displaying the empty state message without errors or crashes.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the page where the user's leagues are displayed | The page loads, displaying content related to user leagues |
| 2 | assert_visible | Verify that an empty state message is displayed on the page | An empty state message, indicating no leagues, is visible |
| 3 | assert_text | Verify the specific text of the empty state message | The empty state message text matches 'You don't have any lea |
| 4 | assert_visible | Verify that a call-to-action to create a league is present | A button or link to 'Create League' is visible, prompting th |

#### TC-106 (ID 663): Verify navigation to League Dashboard from League Card


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 5
- **Description:** This test verifies that tapping a league card successfully navigates the user to the League Dashboard, specifically the Matchup view. This ensures the primary entry point to league details is functional.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Ensure the user is on the main dashboard page | The main dashboard page is displayed, showing available leag |
| 2 | click | Click on any available league card to view its details | The application starts loading the League Dashboard page |
| 3 | wait | Wait for the League Dashboard content to become visible | The League Dashboard content is displayed |
| 4 | assert_url | Verify the URL has changed to the League Dashboard URL, indi | The browser URL contains '/league/' followed by a league ide |
| 5 | assert_visible | Verify that the 'Matchup' view is the default or active view | The 'Matchup' content or tab is clearly visible and active |

#### TC-107 (ID 664): Verify current week's matchup displays user's team details


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 5
- **Description:** This test ensures that upon entering the League Dashboard, the current week's matchup view correctly displays the logged-in user's team information, including avatar, team name, live score, and projected final score. This is crucial for users to identify their own matchup.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify that the current week's matchup section is displayed  | The current week's matchup section is visible, showing two c |
| 2 | assert_visible | Confirm that the avatar representing the logged-in user's te | The user's team avatar is clearly displayed. |
| 3 | assert_text | Verify that the correct team name for the logged-in user is  | The text 'User's Team Name' (or the actual user's team name) |
| 4 | assert_visible | Check that the live score for the logged-in user's team is d | A numerical live score is visible next to the user's team na |
| 5 | assert_visible | Verify that the projected final score for the logged-in user | A numerical projected final score is visible for the user's  |

#### TC-108 (ID 665): Verify current week's matchup displays opponent details


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 4
- **Description:** This test confirms that the League Dashboard's Matchup view accurately presents the opponent's details for the current week. This includes their avatar, team name, live score, and projected final score, which is essential for matchup context.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify that the opponent's avatar is displayed in the matchu | The opponent's avatar image is visible. |
| 2 | assert_visible | Verify that the opponent's team name is displayed. | The opponent's team name is visible. |
| 3 | assert_visible | Verify that the opponent's live score is displayed. | The opponent's live score is visible and updating (if applic |
| 4 | assert_visible | Verify that the opponent's projected final score is displaye | The opponent's projected final score is visible. |

#### TC-109 (ID 666): Verify navigation to past and current weeks in Matchup view


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 8
- **Description:** This test ensures that users can successfully navigate to past and the current weeks within the Matchup view. This functionality is vital for reviewing historical performance and understanding the current state of the league.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_text | Verify that the Matchup view initially displays the current  | The text 'Current Week' or the current week number is visibl |
| 2 | click | Click the button to navigate to the previous week. | The Matchup view updates to display the matchups for the pre |
| 3 | assert_text | Verify that a past week (e.g., 'Week X' where X is less than | The week display area shows a past week number, and the matc |
| 4 | click | Click the 'Previous Week' button again to navigate to an eve | The Matchup view updates to display the matchups for an even |
| 5 | assert_text | Verify that an even older past week is now displayed. | The week display area shows a week number that is earlier th |
| 6 | click | Click the 'Next Week' button repeatedly until the current we | The Matchup view updates through subsequent weeks until the  |
| 7 | assert_text | Verify that the Matchup view has successfully returned to di | The text 'Current Week' or the current week number is visibl |
| 8 | assert_visible | Verify that the 'Next Week' button is disabled or no longer  | The 'Next Week' button is either grayed out, unclickable, or |

#### TC-110 (ID 667): Verify navigation to future weeks in Matchup view


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 8
- **Description:** This test confirms that users can navigate to future weeks within the Matchup view, and that the system dynamically loads relevant data for those upcoming matchups. This allows users to plan and anticipate future games.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify the user is currently on the Matchup view of the Leag | The Matchup view, displaying the current week's games, is vi |
| 2 | assert_text | Confirm the initial displayed week is 'Week 1' (or the curre | The text 'Week 1' (or similar current week indicator) is vis |
| 3 | click | Click the control to advance to the next scheduled week | The page updates to display the matchups for the subsequent  |
| 4 | assert_text | Verify the displayed week has advanced to 'Week 2' | The text 'Week 2' (or similar next week indicator) is visibl |
| 5 | assert_visible | Confirm that matchup data specific to Week 2 is displayed | New matchup entries corresponding to Week 2 are visible on t |
| 6 | click | Click the control again to advance to another future week | The page updates to display the matchups for the week after  |
| 7 | assert_text | Verify the displayed week has advanced to 'Week 3' | The text 'Week 3' (or similar future week indicator) is visi |
| 8 | assert_visible | Confirm that matchup data specific to Week 3 is displayed | New matchup entries corresponding to Week 3 are visible on t |

#### TC-111 (ID 668): Verify History module displays finalized weekly matchups and results


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 4
- **Description:** This test ensures the 'History' module on the League Dashboard correctly displays finalized weekly matchups and their outcomes (WIN/LOSS/TIE). This is crucial for users to review past performance and league events.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click on the History tab to navigate to the past league even | The History module content is displayed, showing a list of p |
| 2 | assert_visible | Confirm that at least one completed week is listed in the Hi | A section for a completed week is visible, indicating past l |
| 3 | assert_visible | Verify that the individual matchups for a selected completed | Matchups, showing participating teams, are visible for the c |
| 4 | assert_visible | For each displayed matchup, verify that its final outcome (W | Each matchup clearly shows its result as WIN, LOSS, or TIE. |

#### TC-112 (ID 669): Verify History module displays player trade history with P&L


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 4
- **Description:** This test confirms that the 'History' module accurately presents player trade history, including profit and loss (P&L) for each trade. This provides users with valuable insights into their team management decisions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the History section of the league. | The History page or section loads, displaying a chronologica |
| 2 | assert_visible | Confirm that the trade history is clearly presented. | A 'Trade History' section is prominently displayed on the pa |
| 3 | assert_visible | Check that individual trade records are present. | At least one trade entry, detailing players involved and dat |
| 4 | assert_text | Confirm that the Profit & Loss (P&L) information is displaye | The trade entry clearly shows a 'P&L' label followed by a nu |

#### TC-113 (ID 670): Verify Standings module displays ranked teams by W-L-T records


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-8
- **Steps:** 10
- **Description:** This test ensures the 'Standings' module on the League Dashboard correctly ranks teams based on their win-loss-tie records. This is fundamental for users to understand their team's position within the league.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Ensure the user is on the League Dashboard page. | The League Dashboard page is fully loaded and visible. |
| 2 | click | Click on the 'Standings' section to view the league standing | The Standings module or page is displayed. |
| 3 | assert_visible | Verify that the standings information is visible on the scre | A table or list showing team standings is displayed. |
| 4 | assert_text | Verify that the 'Team' column header is present. | The 'Team' header is visible in the standings table. |
| 5 | assert_text | Verify that the 'W' (Wins) column header is present. | The 'W' (Wins) header is visible in the standings table. |
| 6 | assert_text | Verify that the 'L' (Losses) column header is present. | The 'L' (Losses) header is visible in the standings table. |
| 7 | assert_text | Verify that the 'T' (Ties) column header is present. | The 'T' (Ties) header is visible in the standings table. |
| 8 | assert_visible | Visually inspect the order of teams in the standings. | Teams are ranked primarily by 'Wins' in descending order (hi |
| 9 | assert_visible | For teams with the same number of Wins, verify their seconda | Teams with identical 'Wins' are ranked by 'Losses' in ascend |
| 10 | assert_visible | For teams with identical Wins and Losses, verify their terti | Teams with identical 'Wins' and 'Losses' are ranked by 'Ties |

#### TC-114 (ID 671): Verify Standings module applies tie-breakers and highlights current user


- **Story:** US-338 — As a User, I can access a detailed League Dashboard so that I can view matchups,
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-9
- **Steps:** 5
- **Description:** This test confirms that the 'Standings' module correctly applies tie-breaker rules when teams have identical records and highlights the logged-in user's team. This provides accurate ranking and easy identification for the user.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click on the 'Standings' tab or link to view the league stan | The Standings module is displayed, showing a table or list o |
| 2 | assert_visible | Verify that the standings table is visible and contains mult | The standings table is displayed, and it's evident that some |
| 3 | assert_text | Manually examine the ranking of teams with identical records | Teams with identical records are ranked according to the lea |
| 4 | assert_visible | Locate the entry corresponding to the logged-in user's team  | The current user's team is clearly identifiable in the stand |
| 5 | assert_visible | Confirm that the current user's team entry is visually highl | The current user's team entry is visually highlighted (e.g., |

#### TC-115 (ID 672): Verify 'Public Leagues' category is displayed on Leagues module


- **Story:** US-339 — As a User, I can browse and join public leagues so that I can easily find new co
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 2
- **Description:** This test ensures that the 'Public Leagues' category is visible to users, allowing them to discover public competitions. It confirms the system's adherence to the UI requirement for league browsing.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the Leagues module | The Leagues module page is displayed, showing various league |
| 2 | assert_visible | Verify that the 'Public Leagues' category is displayed on th | The 'Public Leagues' category is clearly visible to the user |

#### TC-116 (ID 673): Verify available public leagues are listed with correct details


- **Story:** US-339 — As a User, I can browse and join public leagues so that I can easily find new co
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 5
- **Description:** This test confirms that the system accurately displays a list of public leagues, including essential information like name, size, and status. This is crucial for users to make informed decisions about which leagues to join.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify that the section dedicated to public leagues is visib | The 'Public Leagues' section is clearly displayed. |
| 2 | assert_visible | Confirm that at least one public league is listed, as per pr | A list item representing a public league is visible within t |
| 3 | assert_visible | Verify that the name of the first public league is displayed | The league's name is visible and readable. |
| 4 | assert_visible | Verify that the size (e.g., 'X players', 'Capacity: Y') of t | The league's size or capacity information is visible. |
| 5 | assert_visible | Verify that the current status of the first public league is | The league's status is visible and indicates its availabilit |

#### TC-117 (ID 674): Verify user can successfully join an open public league


- **Story:** US-339 — As a User, I can browse and join public leagues so that I can easily find new co
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 5
- **Description:** This test ensures that the core functionality of joining an open public league works as expected. It validates the user's ability to participate in new competitions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click the button to initiate joining an available open publi | The system processes the request, potentially showing a load |
| 2 | assert_text | Verify that a success message is displayed after joining | A banner or toast message confirms successful league joining |
| 3 | assert_url | Verify the user is redirected to the specific league's detai | The browser URL updates to reflect the league's unique page  |
| 4 | assert_visible | Confirm the league's name is prominently displayed on the de | The title or heading of the page shows the name of the leagu |
| 5 | assert_visible | Verify that the UI indicates the user is now a member of the | A 'Leave League' button is visible (replacing 'Join') or a ' |

#### TC-118 (ID 675): Verify 'My Leagues' list updates after joining a public league


- **Story:** US-339 — As a User, I can browse and join public leagues so that I can easily find new co
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 2
- **Description:** This test confirms that a user's personal league list is immediately updated after successfully joining a public league. This ensures data consistency and provides the user with an accurate overview of their active competitions.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the user's personal leagues page. | The 'My Leagues' page is displayed, showing a list of joined |
| 2 | assert_text | Verify that the newly joined public league is now present in | The name of the public league that was joined is visible wit |

#### TC-119 (ID 676): Verify system prevents joining a full or started public league


- **Story:** US-339 — As a User, I can browse and join public leagues so that I can easily find new co
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 5
- **Description:** This test ensures the system correctly enforces rules against joining leagues that are full or have already commenced. It validates the integrity of league participation and prevents invalid entries.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the page displaying available leagues. | The page listing public leagues is displayed. |
| 2 | assert_visible | Identify the specific league that should be unjoinable. | The target league is visible in the list. |
| 3 | click | Click the action button to attempt joining the identified le | The system attempts to process the join request. |
| 4 | assert_text | Check for a message indicating that joining is not possible  | An error message or notification is displayed, stating the l |
| 5 | assert_url | Confirm the user was not successfully redirected into the le | The browser remains on the league listing page, or the user  |

#### TC-120 (ID 677): Verify continuously scrolling ticker displays real-time player names and values


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 4
- **Description:** This test ensures the real-time ticker is visible and correctly displays player names and their current market values as it scrolls. It confirms the basic functionality of the market data display.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify that the real-time market ticker is visible on the pa | The market ticker is displayed at its expected location on t |
| 2 | assert_text | Confirm that the ticker displays at least one player's name  | Player names and market values are visible within the ticker |
| 3 | wait | Wait for a few seconds to allow the ticker content to scroll | The ticker content visibly scrolls. |
| 4 | assert_text | Observe that the ticker has scrolled and is now displaying d | New player names and market values are visible, indicating c |

#### TC-121 (ID 678): Verify player value changes are correctly color-coded in the ticker


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 5
- **Description:** This test checks that positive value changes are displayed in green and negative changes in red within the real-time ticker. This visual cue is critical for users to quickly assess market trends.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | wait | Allow time for the real-time player market ticker to populat | The real-time ticker is visible and displaying actively upda |
| 2 | assert_visible | Locate an entry in the ticker that indicates a player's valu | An entry showing a positive value change is visible in the t |
| 3 | assert_text | Verify that the positive value change is displayed in green. | The positive value change text/indicator is colored green. |
| 4 | assert_visible | Locate an entry in the ticker that indicates a player's valu | An entry showing a negative value change is visible in the t |
| 5 | assert_text | Verify that the negative value change is displayed in red. | The negative value change text/indicator is colored red. |

#### TC-122 (ID 679): Verify player values in the ticker update at the defined interval


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 7
- **Description:** This test confirms that the player values shown in the real-time ticker are refreshed at the specified interval (e.g., 45 seconds). Consistent updates are essential for providing real-time market data.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Confirm the real-time player value ticker is visible on the  | The ticker displaying player values is clearly visible and a |
| 2 | assert_visible | Observe and note down the current values displayed for at le | The initial values for the selected players are visible and  |
| 3 | wait | Wait for the defined update interval of 45 seconds. | The application pauses for 45 seconds, allowing time for the |
| 4 | assert_visible | Re-observe the value for Player A in the ticker. | The ticker displays a new value for Player A. |
| 5 | assert_text | Compare the current value for Player A with the initial valu | The current value for Player A is different from the initial |
| 6 | assert_visible | Re-observe the value for Player B in the ticker. | The ticker displays a new value for Player B. |
| 7 | assert_text | Compare the current value for Player B with the initial valu | The current value for Player B is different from the initial |

#### TC-123 (ID 680): Verify ticker updates precisely at the 45-second interval boundary


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** boundary | **AC Ref:** AC-3
- **Steps:** 5
- **Description:** This test verifies that the system's ticker update mechanism triggers exactly at the 45-second mark, not before or after. This ensures the update interval is precisely adhered to, preventing stale data or excessive updates.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | screenshot | Observe and record the current ticker value and the exact sy | The market page is displayed with active ticker data. |
| 2 | wait | Monitor the system clock to approach the 45-second mark. | The system clock reaches approximately 40 seconds past the m |
| 3 | assert_visible | At exactly 44 seconds past the minute, visually confirm that | The ticker value has NOT changed from the initial value. |
| 4 | wait | Continuously monitor the ticker display and the system clock | The ticker value changes, and the exact update time is noted |
| 5 | assert_visible | Confirm that the ticker value has changed from the value obs | The ticker value has updated, and the update occurred exactl |

#### TC-124 (ID 681): Verify user can successfully buy shares of an available player


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 5
- **Description:** This test confirms that a user can successfully execute a buy order for shares of a player who is available on the market. It validates the core functionality of purchasing player shares.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Go to the page where players are listed for trade. | The player market page is displayed, showing available playe |
| 2 | click | Select an available player to purchase shares from. | A buy order form or modal appears for the selected player. |
| 3 | fill | Enter the desired number of shares to buy (e.g., 1 share). | The quantity input field displays the entered value. |
| 4 | click | Confirm and submit the buy order. | A processing indicator or confirmation message appears. |
| 5 | assert_text | Verify that a success message is displayed. | A message confirming 'Shares purchased successfully' or simi |

#### TC-125 (ID 682): Verify user can successfully sell shares of a player they own


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 9
- **Description:** This test confirms that a user can successfully execute a sell order for shares of a player they currently own. It validates the core functionality of divesting player shares.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's portfolio page to view owned players. | The 'My Portfolio' page is displayed, showing a list of owne |
| 2 | click | Click on the specific player to view their detailed page. | The player's detailed page is displayed, showing options lik |
| 3 | click | Click the 'Sell Shares' button to initiate the sell order pr | A sell order form or modal is displayed, prompting for the n |
| 4 | fill | Enter the quantity of shares to sell (e.g., 1 share). | The input field displays '1' share. |
| 5 | click | Click the button to review or confirm the sell order. | A confirmation screen or a final 'Place Sell Order' button i |
| 6 | click | Click the 'Place Sell Order' button to finalize the transact | A success message or notification indicating the sell order  |
| 7 | assert_text | Verify that a success message confirms the sell order. | The text 'Sell order placed successfully' (or similar) is vi |
| 8 | navigate | Navigate back to the user's portfolio page. | The 'My Portfolio' page is displayed. |
| 9 | assert_text | Verify that the player's share count in the portfolio has de | The displayed share count for the player reflects the succes |

#### TC-126 (ID 683): Verify trades execute at the exact displayed global price, preventing slippage


- **Story:** US-340 — As a User, I can view real-time player market prices and trade player shares so 
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 10
- **Description:** This test ensures that when a trade (buy or sell) is executed, the transaction price precisely matches the global market price displayed at the moment of execution. This prevents "slippage," where the actual trade price differs from the expected price.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the trading interface. | The trading interface is displayed, showing a list of player |
| 2 | click | Select a player to view its trading details. | The selected player's detailed view, including its current g |
| 3 | custom | Note down the exact global market price displayed for the se | The tester has recorded the current global market price for  |
| 4 | click | Initiate a buy order for the player. | A trade confirmation modal or section appears, pre-filled wi |
| 5 | click | Finalize the buy order. | A success message is displayed, and the trade is processed.  |
| 6 | custom | Locate the executed price for the recent buy trade. | The executed trade price exactly matches the global market p |
| 7 | custom | Note down the exact global market price displayed for the se | The tester has recorded the current global market price for  |
| 8 | click | Initiate a sell order for the player. | A trade confirmation modal or section appears, pre-filled wi |
| 9 | click | Finalize the sell order. | A success message is displayed, and the trade is processed.  |
| 10 | custom | Locate the executed price for the recent sell trade. | The executed trade price exactly matches the global market p |

#### TC-127 (ID 684): Verify Ops Admin can adjust player valuation pricing weights


- **Story:** US-341 — As an Ops Admin, I can configure market pricing parameters so that I can manage 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 8
- **Description:** This test ensures that an Ops Admin can successfully modify the pricing weights used for player valuations, confirming the system's core functionality for market parameter adjustment.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the Market Configuration settings page. | The Market Configuration page loads, displaying various mark |
| 2 | assert_visible | Verify that the section for adjusting player valuation prici | The 'Player Valuation Pricing Weights' section is clearly vi |
| 3 | fill | Enter a new value for the 'Skill Weight' pricing parameter. | The 'Skill Weight' input field displays '0.40'. |
| 4 | fill | Enter a new value for the 'Market Demand Weight' pricing par | The 'Market Demand Weight' input field displays '0.30'. |
| 5 | click | Click the 'Save Changes' button to apply the modified pricin | A success message is displayed, indicating that the changes  |
| 6 | click | Re-navigate to the Market Configuration page to ensure the c | The Market Configuration page reloads. |
| 7 | assert_text | Verify that the 'Skill Weight' input field still displays th | The 'Skill Weight' input field shows '0.40'. |
| 8 | assert_text | Verify that the 'Market Demand Weight' input field still dis | The 'Market Demand Weight' input field shows '0.30'. |

#### TC-128 (ID 685): Verify Ops Admin can configure bid/ask spread for player shares


- **Story:** US-341 — As an Ops Admin, I can configure market pricing parameters so that I can manage 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 6
- **Description:** This test confirms that an Ops Admin can successfully set the bid/ask spread percentage for player shares, ensuring control over market liquidity and pricing.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Market Configuration page in the admin panel | The Market Configuration page is displayed, showing various  |
| 2 | fill | Enter a new bid/ask spread percentage (e.g., 2.5%) | The input field displays '2.5' |
| 3 | click | Click the button to save the updated configuration | A success message is displayed, indicating the settings have |
| 4 | assert_text | Verify that a success message confirms the changes were save | The text 'Market settings updated successfully' is visible o |
| 5 | navigate | Re-navigate to the Market Configuration page to ensure the c | The Market Configuration page reloads |
| 6 | assert_text | Verify that the 'Bid/Ask Spread Percentage' input field now  | The input field for 'Bid/Ask Spread Percentage' shows '2.5' |

#### TC-129 (ID 686): Verify Ops Admin can set platform market opening dates


- **Story:** US-341 — As an Ops Admin, I can configure market pricing parameters so that I can manage 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 5
- **Description:** This test ensures that an Ops Admin can successfully configure a future opening date for the platform market, allowing for scheduled market operations.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the market configuration settings page. | The Market Configuration page is displayed, showing various  |
| 2 | assert_visible | Verify that the field for setting the market opening date is | The 'Market Opening Date' field is clearly visible on the pa |
| 3 | fill | Enter a future date into the market opening date field. | The input field displays '2024-12-31'. |
| 4 | click | Click the button to save the new market opening date. | A success message is displayed, or the page reloads/updates  |
| 5 | assert_text | Verify that the 'Market Opening Date' field now displays the | The 'Market Opening Date' field shows '2024-12-31', confirmi |

#### TC-130 (ID 687): Verify configured market parameters apply globally and in real-time


- **Story:** US-341 — As an Ops Admin, I can configure market pricing parameters so that I can manage 
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 10
- **Description:** This test verifies that any changes made to market parameters by an Ops Admin are immediately applied across the entire platform, ensuring real-time market adjustments.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | As an Ops Admin, navigate to the market configuration page. | The market configuration page is displayed, showing a list o |
| 2 | click | Click the 'Edit' button for a chosen market to modify its pa | The market's configuration details are displayed in an edita |
| 3 | select | Change the 'Market Status' from 'Open' to 'Closed' (or vice- | The 'Market Status' dropdown now shows 'Closed'. |
| 4 | click | Save the updated market parameters. | A success message is displayed, and the market configuration |
| 5 | navigate | Open the player login page in a separate browser context or  | The player login page is displayed. |
| 6 | fill | Enter the player's email address. | The email field shows the entered address. |
| 7 | fill | Enter the player's password. | The password field shows masked characters. |
| 8 | click | Click the 'Login' button to access the player dashboard. | The player is redirected to their dashboard or home page. |
| 9 | navigate | Navigate to the specific market page ('Market X') as the pla | The page for 'Market X' is displayed. |
| 10 | assert_text | Verify that the market status for 'Market X' is immediately  | The market status indicator clearly shows 'Closed', confirmi |

#### TC-131 (ID 688): Verify market parameter changes are recorded in audit log


- **Story:** US-341 — As an Ops Admin, I can configure market pricing parameters so that I can manage 
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 6
- **Description:** This test ensures that every modification made to market parameters by an Ops Admin is accurately recorded in the audit log, including the Admin_ID, Action_Type, Timestamp, and a specified Reason for the change.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Navigate to the market configuration settings page. | The market configuration page is displayed, showing various  |
| 2 | fill | Change the value of the 'Maximum Order Size' parameter to a  | The 'Maximum Order Size' input field displays '500'. |
| 3 | fill | Enter a specific reason for the parameter modification. | The 'Reason for Change' text area contains the entered text. |
| 4 | click | Submit the modified market parameters. | A success message is displayed, confirming the changes have  |
| 5 | click | Navigate to the audit log page to review the recorded change | The audit log page is displayed, showing a list of system ev |
| 6 | assert_text | Verify that a new audit log entry is present for the market  | A new audit log entry is visible, containing the Ops Admin's |

#### TC-132 (ID 689): Verify XP points are awarded for league performance


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 6
- **Description:** This test ensures that users correctly receive XP points after participating in a league, based on their performance. It confirms the core mechanism for XP acquisition.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's Profile page to check current XP. | The User Profile page is displayed, showing the user's total |
| 2 | assert_text | Note down the current total XP displayed. | The total XP is visible and can be recorded (e.g., '1500 XP' |
| 3 | navigate | Navigate to the League Results page for the recently complet | The League Results page is displayed, showing details of the |
| 4 | assert_text | Verify that a specific amount of XP is displayed as awarded  | The page clearly shows 'Y XP' awarded for the match (e.g., ' |
| 5 | navigate | Return to the user's Profile page. | The User Profile page is displayed again. |
| 6 | assert_text | Verify that the total XP has been updated to reflect the awa | The total XP displayed on the profile page is now the sum of |

#### TC-133 (ID 690): Verify system accurately tracks user's total XP


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 8
- **Description:** This test confirms that the system maintains an accurate cumulative count of a user's earned XP points. It's crucial for tier progression and overall user experience.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's Profile page to view current XP. | The Profile page is displayed, showing user details and stat |
| 2 | assert_text | Verify the initial total XP displayed on the profile page, b | The 'Total XP' value is displayed as 200. |
| 3 | click | Click on the 'Leagues' section to find an activity that gran | The Leagues page is displayed, showing available leagues and |
| 4 | click | Initiate a new league match to earn additional XP. | The system starts a new league match or navigates to the mat |
| 5 | click | Simulate the completion of the league match, expecting an XP | A success message is displayed, indicating XP earned from th |
| 6 | assert_text | Verify that a notification confirms the XP gain from the com | A notification 'You earned 50 XP!' is visible on the screen. |
| 7 | click | Return to the Profile page to check the updated total XP. | The Profile page is reloaded and displayed. |
| 8 | assert_text | Verify that the total XP has been accurately updated to refl | The 'Total XP' value is displayed as 250 (initial 200 + earn |

#### TC-134 (ID 691): Verify user is assigned to the correct tier based on XP


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 3
- **Description:** This test ensures that the system correctly categorizes users into tiers (e.g., Rookie, Amateur, Pro) based on their accumulated XP points. It validates the tier assignment logic.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's profile page where XP and tier inform | The user's profile page loads successfully, showing user det |
| 2 | assert_text | Verify that the displayed XP matches the precondition (500 X | The profile page clearly shows '500 XP' or similar text indi |
| 3 | assert_text | Verify that the user's assigned tier is 'Amateur' based on 5 | The profile page displays 'Amateur' as the user's current ti |

#### TC-135 (ID 692): Verify user's current XP points are displayed on profile


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 3
- **Description:** This test confirms that the user's profile accurately shows their current total XP points. This is essential for users to track their progress.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's profile page | The user's profile page is displayed |
| 2 | assert_visible | Verify that the XP points section is visible on the profile  | A section labeled 'XP Points' or similar is present |
| 3 | assert_text | Verify that the displayed XP points match the expected value | The text '750 XP' is visible within the XP points section |

#### TC-136 (ID 693): Verify user's current tier status is displayed on profile


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 3
- **Description:** This test ensures that the user's profile correctly displays their current tier status. This provides users with clear visibility into their progression.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Click the profile icon or link to navigate to the user's pro | The user is redirected to their personal profile page. |
| 2 | assert_url | Verify that the browser's URL reflects the profile page. | The URL ends with '/profile' or contains 'profile' as a segm |
| 3 | assert_text | Verify that the user's current tier status, 'Pro Tier', is d | The text 'Pro Tier' is clearly visible within the user's pro |

#### TC-137 (ID 694): Verify automatic tier update upon reaching next XP threshold


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 7
- **Description:** This test confirms that the system automatically promotes a user to the next tier once they accumulate the required XP. It validates the automated progression mechanism.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the user's profile page where tier and XP are di | The user's profile page is loaded, showing current tier and  |
| 2 | assert_text | Verify the user's initial tier is 'Amateur'. | The page displays 'Amateur' as the current tier. |
| 3 | assert_text | Verify the user's initial XP is 950. | The page displays '950 XP' as the current experience points. |
| 4 | click | Click the button to complete a challenge that grants 100 XP. | A success message is displayed, indicating the challenge was |
| 5 | navigate | Navigate back to the user's profile page to refresh the tier | The user's profile page is reloaded. |
| 6 | assert_text | Verify the user's XP has increased to 1050 (950 + 100). | The page displays '1050 XP'. |
| 7 | assert_text | Verify the user's tier has automatically updated to 'Pro' (t | The page displays 'Pro' as the current tier. |

#### TC-138 (ID 695): Verify XP gating grants access to a restricted league/feature


- **Story:** US-342 — As a User, I can earn XP and progress through tiers so that I am rewarded for my
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-7
- **Steps:** 6
- **Description:** This test ensures that users with sufficient XP are granted access to leagues or features that are gated by an XP requirement. It validates the access control mechanism.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the 'Leagues' section of the application | The 'Leagues' page is displayed, showing available leagues |
| 2 | assert_visible | Verify that the 'Elite League' is visible on the page | The 'Elite League' entry is present, indicating it's an opti |
| 3 | click | Click on the 'Elite League' to attempt to access it | The application attempts to grant access to the 'Elite Leagu |
| 4 | assert_url | Verify that the URL has changed to the 'Elite League' specif | The browser URL ends with '/leagues/elite', confirming succe |
| 5 | assert_text | Verify that the 'Elite League Dashboard' title is displayed | The page title 'Elite League Dashboard' is visible, confirmi |
| 6 | assert_visible | Verify that content unique to the 'Elite League' is displaye | Specific 'Elite League' features like leaderboards or challe |

#### TC-139 (ID 696): Verify Ops Admin can configure XP award parameter ranges


- **Story:** US-343 — As an Ops Admin, I can configure XP award parameters and ensure consistent Half-
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 4
- **Description:** This test verifies that an Ops Admin can successfully set and save parameter ranges for XP awards, ensuring the system accepts valid configuration inputs.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Enter a valid minimum XP award value | The Minimum XP Award Value field displays '100' |
| 2 | fill | Enter a valid maximum XP award value, greater than the minim | The Maximum XP Award Value field displays '500' |
| 3 | click | Click the button to save the new XP award parameter ranges | The system processes the configuration update |
| 4 | assert_text | Verify that a success message is displayed confirming the sa | A message indicating successful saving of XP award parameter |

#### TC-140 (ID 697): Verify Ops Admin can configure XP rank levels and tier definitions


- **Story:** US-343 — As an Ops Admin, I can configure XP award parameters and ensure consistent Half-
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 11
- **Description:** This test verifies that an Ops Admin can successfully define and save XP rank levels and tier definitions, ensuring the progression system can be properly structured.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | click | Initiate the creation of a new XP rank level | New input fields for a rank level appear on the page |
| 2 | fill | Enter a name for the new rank level | The 'Rank Name' field displays 'Novice' |
| 3 | fill | Set the XP required for the 'Novice' rank | The 'XP Required' field displays '0' |
| 4 | click | Add a second rank level to demonstrate multiple ranks | Another set of input fields for a rank level appears |
| 5 | fill | Enter a name for the second new rank level | The 'Rank Name' field displays 'Apprentice' |
| 6 | fill | Set the XP required for the 'Apprentice' rank | The 'XP Required' field displays '100' |
| 7 | click | Initiate the creation of a new XP tier definition | New input fields for a tier definition appear on the page |
| 8 | fill | Enter a name for the new tier definition | The 'Tier Name' field displays 'Starter Tier' |
| 9 | select | Associate the newly created rank levels with the 'Starter Ti | Both 'Novice' and 'Apprentice' ranks are selected for the 'S |
| 10 | click | Save all the defined XP rank levels and tier definitions | A confirmation or success message is displayed, and the chan |

*… and 1 more steps*


#### TC-141 (ID 698): Verify system automatically applies Half-PPR scoring rules


- **Story:** US-343 — As an Ops Admin, I can configure XP award parameters and ensure consistent Half-
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 8
- **Description:** This test verifies that the system automatically applies the fixed Half-PPR scoring rules to player performances in all leagues, ensuring consistent scoring without manual intervention.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the main application page. | The application's login page or dashboard is displayed. |
| 2 | fill | Enter valid user credentials. | The email field is populated. |
| 3 | fill | Enter the corresponding password. | The password field is populated. |
| 4 | click | Click to log into the application. | The user is redirected to the dashboard or league overview p |
| 5 | click | Select an existing league to view its details. | The selected league's main page is displayed. |
| 6 | click | Navigate to the section displaying player performance and sc | The player scores and stats page for a recent week is displa |
| 7 | click | Click on a player to view their detailed game statistics and | The detailed player stats page, including raw stats and tota |
| 8 | assert_text | Manually calculate the player's total fantasy points using H | The displayed total fantasy points for 'Player X' exactly ma |

#### TC-142 (ID 699): Verify scoring calculations are consistent across leagues


- **Story:** US-343 — As an Ops Admin, I can configure XP award parameters and ensure consistent Half-
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 12
- **Description:** This test verifies that the system performs consistent scoring calculations for identical player performances across different leagues, ensuring fairness and reliability.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the player performance entry page | The performance entry page is displayed with options to sele |
| 2 | select | Select 'League A' from the available leagues | League A is selected, and relevant player data for League A  |
| 3 | select | Select 'Player X' from the list of players in League A | Player X is selected, and their performance entry fields are |
| 4 | fill | Enter '2' into the Goals performance metric field | The Goals field displays '2' |
| 5 | fill | Enter '1' into the Assists performance metric field | The Assists field displays '1' |
| 6 | click | Click the button to calculate and save the performance for P | The calculated score for Player X in League A is displayed |
| 7 | assert_text | Verify the calculated score for Player X in League A is '25  | The text '25 points' is visible as Player X's score |
| 8 | select | Change the selected league to 'League B' | League B is selected, and the page updates to reflect League |
| 9 | select | Ensure 'Player X' is selected (or re-select if necessary) in | Player X is selected, and their performance entry fields are |
| 10 | fill | Enter '2' into the Goals performance metric field for Player | The Goals field displays '2' |

*… and 2 more steps*


#### TC-143 (ID 700): Verify scoring calculations are accurate across all leagues


- **Story:** US-343 — As an Ops Admin, I can configure XP award parameters and ensure consistent Half-
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 10
- **Description:** This test verifies that the system performs accurate scoring calculations based on Half-PPR rules for player performances across all leagues, ensuring correct point assignments.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Open the main application page where leagues are listed or a | The application home page or dashboard is displayed, showing |
| 2 | click | Select and enter the first league to begin verification. | The main page for 'My Fantasy League 1' is displayed, showin |
| 3 | click | Navigate to the section displaying player performance and th | A list of players with their scores for a recent week is vis |
| 4 | assert_visible | Locate a player with recent performance data and note their  | Player A's detailed statistics for the selected week are cle |
| 5 | assert_text | Verify that Player A's displayed total fantasy points match  | Player A's total points accurately reflect the Half-PPR calc |
| 6 | click | Return to the list of all leagues to select another league f | The list of all available leagues is displayed. |
| 7 | click | Select and enter a second, different league to verify its sc | The main page for 'My Fantasy League 2' is displayed. |
| 8 | click | Navigate to the player performance and scores section within | A list of players with their scores for a recent week in 'My |
| 9 | assert_visible | Locate a player in the second league with recent performance | Player B's detailed statistics for the selected week are cle |
| 10 | assert_text | Verify that Player B's displayed total fantasy points in the | Player B's total points in 'My Fantasy League 2' accurately  |

#### TC-144 (ID 701): Verify XP configuration changes are recorded in the audit log


- **Story:** US-343 — As an Ops Admin, I can configure XP award parameters and ensure consistent Half-
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 5
- **Description:** This test verifies that any modifications made to XP configuration parameters by an Ops Admin are accurately recorded in the system's audit log, ensuring traceability and accountability.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | fill | Toggle the 'XP Feature Toggle' checkbox to change its state  | The 'XP Feature Toggle' checkbox state is updated |
| 2 | click | Click the Save Changes button to apply the configuration mod | A confirmation message indicating successful save appears, o |
| 3 | click | Navigate to the Audit Log section of the application | The Audit Log page is displayed, showing a list of recent ac |
| 4 | assert_text | Verify that an entry related to the XP configuration change  | The audit log contains an entry indicating 'XP Feature Toggl |
| 5 | assert_text | Verify the details of the audit log entry accurately reflect | The audit log entry details show the specific parameter chan |

#### TC-145 (ID 702): Verify email confirmation sent on successful password change


- **Story:** US-344 — As a User, I can receive important account and league notifications so that I st
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 9
- **Description:** This test verifies that an email confirmation is sent to the user's registered email address after they successfully change their password. This ensures users are informed of critical account security changes.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the account security settings page. | The account security settings page is displayed, showing opt |
| 2 | click | Click on the option to change the password. | The password change form is displayed with fields for curren |
| 3 | fill | Enter the user's current password. | The 'Current Password' field is populated with the entered t |
| 4 | fill | Enter a new, strong password. | The 'New Password' field is populated with the entered text  |
| 5 | fill | Re-enter the new password to confirm it. | The 'Confirm New Password' field is populated with the enter |
| 6 | click | Click the button to submit the password change. | A success message indicating the password has been changed i |
| 7 | assert_text | Verify that a success message confirms the password change. | A message like 'Password updated successfully' is visible on |
| 8 | navigate | Navigate to the user's registered email inbox (e.g., Gmail,  | The email inbox is displayed, showing recent emails. |
| 9 | assert_text | Verify that an email confirming the password change has been | An email with the subject 'Your password has been changed' ( |

#### TC-146 (ID 703): Verify notification sent on account status change to suspended


- **Story:** US-344 — As a User, I can receive important account and league notifications so that I st
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 9
- **Description:** This test verifies that the system sends a notification to the user when their account status changes, specifically to 'suspended'. This ensures users are immediately aware of changes affecting their account access.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | As an administrator, navigate to the user management section | The user management page is displayed, showing a list of use |
| 2 | fill | Enter the email address of the target user account into the  | The user list is filtered, showing only the target user acco |
| 3 | click | Click the 'Edit' button or link to view and modify the targe | The user's profile or edit page is displayed. |
| 4 | select | Change the account status from 'Active' to 'Suspended' using | The 'Account Status' dropdown now displays 'Suspended'. |
| 5 | click | Click the 'Save' or 'Update' button to apply the status chan | A confirmation message appears, and the user's status is upd |
| 6 | navigate | Navigate to the email inbox associated with the target user  | The user's email inbox is displayed. |
| 7 | assert_text | Verify that a new email with the subject 'Account Suspended  | An email with the subject 'Account Suspended Notification' i |
| 8 | click | Click on the notification email to open it. | The content of the 'Account Suspended Notification' email is |
| 9 | assert_text | Verify that the email body contains a message indicating the | The email content clearly states that the user's account has |

#### TC-147 (ID 704): Verify push notification sent for league matchup update


- **Story:** US-344 — As a User, I can receive important account and league notifications so that I st
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 5
- **Description:** This test verifies that the system sends a push notification to the user for a relevant league activity, such as a matchup update. This ensures users stay informed about their league's progress and events.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | wait | Wait for the system to process a league matchup update that  | The system processes the update and prepares to send a notif |
| 2 | assert_visible | Observe the push notification appearing on the device's noti | A push notification related to a league matchup update is di |
| 3 | assert_text | Verify the notification text accurately describes a league m | The notification text states 'Your league's matchup has been |
| 4 | click | Tap on the push notification to open the app. | The app opens and navigates to the relevant league matchup d |
| 5 | assert_visible | Confirm the app has navigated to the correct screen displayi | The League Matchup Details screen is displayed, showing the  |

#### TC-148 (ID 705): Verify in-app message displayed for critical system alert


- **Story:** US-344 — As a User, I can receive important account and league notifications so that I st
- **Status:** ready | **Priority:** critical | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 5
- **Description:** This test verifies that the system displays an in-app message for critical alerts or important information. This ensures users receive immediate and prominent notifications for urgent matters while using the application.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the application dashboard page where the alert i | The dashboard page loads successfully |
| 2 | assert_visible | Verify that the critical system alert message is displayed p | A banner or modal containing the critical system alert is vi |
| 3 | assert_text | Verify the content of the critical system alert message | The alert message contains the text 'Critical System Mainten |
| 4 | click | Click the button to dismiss the critical system alert | The critical system alert banner or modal disappears from th |
| 5 | assert_visible | Verify that the critical system alert message is no longer d | The critical system alert banner or modal is no longer visib |

#### TC-149 (ID 706): Verify user can toggle push notification preference


- **Story:** US-344 — As a User, I can receive important account and league notifications so that I st
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 9
- **Description:** This test verifies that the system provides a mechanism for users to manage their notification preferences, specifically by toggling push notifications on or off. This ensures users have control over the types of notifications they receive.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Notification Settings page | The Notification Settings page is displayed, showing various |
| 2 | click | Click the 'Push Notifications' toggle switch to change its s | The 'Push Notifications' toggle switch visually changes to t |
| 3 | custom | Verify the visual state of the 'Push Notifications' toggle s | The toggle switch visually indicates the new state (e.g., 'O |
| 4 | click | Click the 'Save Changes' button to apply the preference upda | A loading indicator may appear briefly, and then a success m |
| 5 | assert_text | Verify that a success message confirms the changes were save | A message like 'Settings updated successfully' or similar is |
| 6 | click | Click the 'Push Notifications' toggle switch again to revert | The 'Push Notifications' toggle switch visually changes back |
| 7 | custom | Verify the visual state of the 'Push Notifications' toggle s | The toggle switch visually indicates the reverted state (e.g |
| 8 | click | Click the 'Save Changes' button to apply the reverted prefer | A loading indicator may appear briefly, and then a success m |
| 9 | assert_text | Verify that a success message confirms the changes were save | A message like 'Settings updated successfully' or similar is |

#### TC-150 (ID 707): Verify Ops Admin can send targeted message to a specific user


- **Story:** US-345 — As an Ops Admin, I can send targeted messages and emergency broadcasts so that I
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-1
- **Steps:** 8
- **Description:** This test verifies that an Ops Admin can successfully send a targeted message to a specific individual user. It confirms the core functionality for direct, user-level communication as per AC-1.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Ops Admin dashboard | The Ops Admin dashboard is displayed |
| 2 | click | Click on the User Management section to view users | The User Management page, displaying a list of users, is sho |
| 3 | fill | Enter the name of the specific user to message | The search results are filtered to show 'Test User' |
| 4 | click | Click to view the details of the specific user | The profile page for 'Test User' is displayed |
| 5 | click | Initiate sending a message to the user | A message composition modal or page is displayed |
| 6 | fill | Type the message content into the message field | The message content is visible in the input field |
| 7 | click | Click the Send button to dispatch the message | The message is sent, and a confirmation message appears |
| 8 | assert_text | Verify that a success message is displayed | A notification confirming 'Message sent successfully' is vis |

#### TC-151 (ID 708): Verify Ops Admin can send emergency broadcast to all users


- **Story:** US-345 — As an Ops Admin, I can send targeted messages and emergency broadcasts so that I
- **Status:** ready | **Priority:** critical | **Category:** e2e
- **Scenario:** positive | **AC Ref:** AC-2
- **Steps:** 7
- **Description:** This test confirms that an Ops Admin can successfully send an emergency broadcast message to all users, triggering both an in-app banner and push notifications. This validates the system's capability for critical, platform-wide communication as per AC-2.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Admin Broadcasts management page. | The Broadcasts management page is displayed. |
| 2 | click | Click the button to initiate sending a new broadcast. | A form or modal for creating a new broadcast appears. |
| 3 | fill | Enter the emergency broadcast message content. | The message text area displays the entered emergency message |
| 4 | select | Select 'All Users' as the target audience for the broadcast. | The 'Target Audience' field shows 'All Users' selected. |
| 5 | check | Enable the 'Emergency Broadcast' option to trigger special h | The 'Emergency Broadcast' option is activated. |
| 6 | click | Click the button to send the emergency broadcast. | A confirmation message or success notification is displayed. |
| 7 | assert_text | Verify that a success message confirms the broadcast was sen | The confirmation message 'Emergency broadcast sent successfu |

#### TC-152 (ID 709): Verify targeted message requires a valid reason code


- **Story:** US-345 — As an Ops Admin, I can send targeted messages and emergency broadcasts so that I
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-3
- **Steps:** 8
- **Description:** This test ensures that the system enforces the requirement for a reason code when an Ops Admin sends a targeted message. A valid reason code should allow the message to be sent successfully, confirming compliance with AC-3.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the 'Send Targeted Message' page in the admin pa | The 'Send Targeted Message' form is displayed |
| 2 | select | Select an existing valid league-level group from the recipie | The selected league-level group is displayed in the dropdown |
| 3 | fill | Enter a test message into the 'Message Content' field | The message content field contains the entered text |
| 4 | click | Attempt to send the message without providing a reason code | An error message indicating a missing reason code is display |
| 5 | assert_text | Verify that an error message explicitly states the reason co | The text 'Reason code is required' or similar is visible on  |
| 6 | fill | Enter a valid reason code into the 'Reason Code' field | The 'Reason Code' field contains the entered value |
| 7 | click | Click the 'Send Message' button again with the reason code p | The message is successfully sent, and a confirmation message |
| 8 | assert_text | Verify that a success message confirms the targeted message  | A 'Message sent successfully' notification is displayed |

#### TC-153 (ID 710): Verify emergency broadcast requires a valid reason code


- **Story:** US-345 — As an Ops Admin, I can send targeted messages and emergency broadcasts so that I
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-4
- **Steps:** 9
- **Description:** This test confirms that the system enforces the requirement for a reason code when an Ops Admin sends an emergency broadcast message. A valid reason code should allow the broadcast to be sent successfully, ensuring all critical communications are categorized as per AC-3.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the 'New Emergency Broadcast' page | The 'New Emergency Broadcast' form is displayed |
| 2 | fill | Enter a subject for the broadcast | The subject field displays 'Test Emergency Broadcast' |
| 3 | fill | Enter the content of the emergency message | The message content area displays the entered text |
| 4 | select | Select a recipient group for the broadcast | The 'All Users' option is selected in the dropdown |
| 5 | click | Attempt to send the broadcast without selecting a reason cod | The broadcast is not sent, and an error message appears |
| 6 | assert_text | Verify that a validation error message indicates the reason  | The text 'Reason Code is required' is visible on the page |
| 7 | select | Select a valid reason code from the dropdown | The 'System Outage' option is selected in the Reason Code dr |
| 8 | click | Click the Send Broadcast button again with a valid reason co | The broadcast is sent successfully, and a confirmation messa |
| 9 | assert_text | Verify that a success message is displayed | A success message like 'Broadcast Sent Successfully' is visi |

#### TC-154 (ID 711): Verify system logs all sent communications


- **Story:** US-345 — As an Ops Admin, I can send targeted messages and emergency broadcasts so that I
- **Status:** ready | **Priority:** high | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-5
- **Steps:** 7
- **Description:** This test verifies that after a communication is successfully sent, the system correctly logs all required details, including Admin_ID, message content, target audience, and timestamp. This ensures auditability and traceability of all communications as per AC-4.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | navigate | Navigate to the Communication Logs or Audit Trail section of | The Communication Logs page is displayed, showing a list of  |
| 2 | wait | Wait for the log entries to fully load on the page. | Log entries are visible and interactive. |
| 3 | assert_visible | Locate and verify the presence of the log entry correspondin | The specific log entry for the sent communication is visible |
| 4 | assert_text | Verify that the 'Admin ID' in the log entry matches the ID o | The 'Admin ID' field correctly displays 'Ops Admin's ID'. |
| 5 | assert_text | Verify that the 'Message Content' in the log entry accuratel | The 'Message Content' field correctly displays 'The prepared |
| 6 | assert_text | Verify that the 'Target Audience' in the log entry matches t | The 'Target Audience' field correctly displays 'The specifie |
| 7 | assert_text | Verify that the 'Timestamp' in the log entry is recent and a | The 'Timestamp' field displays a timestamp corresponding to  |

#### TC-155 (ID 712): Verify Ops Admin can enable/disable reminder timing offsets


- **Story:** US-345 — As an Ops Admin, I can send targeted messages and emergency broadcasts so that I
- **Status:** ready | **Priority:** medium | **Category:** regression
- **Scenario:** positive | **AC Ref:** AC-6
- **Steps:** 16
- **Description:** This test confirms that Ops Admins can successfully enable and configure reminder timing offsets for communications. This ensures flexibility in scheduling follow-up notifications or reminders as per AC-5.

| # | Action | Description | Expected |
| --- | --- | --- | --- |
| 1 | assert_visible | Verify the Ops Admin is on the communication drafting or edi | The communication drafting/editing interface is fully displa |
| 2 | click | Click to enable the reminder timing offsets feature | The toggle/checkbox is switched to 'On' or 'Enabled' state,  |
| 3 | assert_visible | Verify that the 'Days' offset input field is now visible | The 'Days' input field is displayed and editable |
| 4 | fill | Enter '2' into the Days offset field | The 'Days' field displays '2' |
| 5 | fill | Enter '3' into the Hours offset field | The 'Hours' field displays '3' |
| 6 | fill | Enter '30' into the Minutes offset field | The 'Minutes' field displays '30' |
| 7 | click | Save the changes to the communication | A success message is displayed, and the page may refresh or  |
| 8 | navigate | Reload the communication editing page to ensure settings per | The communication editing page reloads |
| 9 | assert_visible | Verify the reminder timing offsets feature is still enabled | The toggle/checkbox is displayed in the 'On' or 'Enabled' po |
| 10 | assert_text | Verify the 'Days' offset value persisted | The 'Days' input field shows '2' |

*… and 6 more steps*


## Appendix C — Sample Manual→AI Match Pairs


Top similarity matches (manual case → best AI analog):

| Manual ID | Sheet | Manual Objective | AI TC# | AI Title | Score |
| --- | --- | --- | --- | --- | --- |
| TC_003 | User story -1.5 My Profile (Un | Verify UI elements in the Edit Profile screen | TC-36 | Verify IP Address is logged upon successful login | 0.64 |
| TC_016 | User story -1.12  Admin & Staf | Verify successful login with correct OTP | TC-66 | Verify successful login with valid registered emai | 0.64 |
| TC_015 | User story -1.3 Forgot Passwor | Verify Enter received OTP after 30 minutes | TC-38 | Verify system sends OTP to registered email | 0.62 |
| TC_051 | User story -1.5 My Profile (Un | Verify Avatar Visibility Across the Mobile App | TC-36 | Verify IP Address is logged upon successful login | 0.61 |
| TC_036 | User story -1.3 Forgot Passwor | Verify matching password into the Confirm password | TC-43 | Verify new password is not identical to current pa | 0.61 |
| TC_014 | User story-1.1 User Account Ad | Validate the actions displayed according to the ro | TC-88 | Verify Support Admin can force password reset for  | 0.59 |
| TC_017 | User story -1.3 Forgot Passwor | Verify “Wrong email? Go back” hyperlink during act | TC-38 | Verify system sends OTP to registered email | 0.59 |
| TC_021 | User story -1.3 Forgot Passwor | Verify expired otp entered after resend code | TC-38 | Verify system sends OTP to registered email | 0.59 |
| TC_012 | User story -1.12  Admin & Staf | Verify login with registered Username and valid pa | TC-67 | Verify 2FA enforcement after successful credential | 0.59 |
| TC_001 | User story -1.5 My Profile (Un | Verify the Edit Profile option in Profile tab | TC-36 | Verify IP Address is logged upon successful login | 0.58 |
| TC_014 | User story -1.2  Unlock Accoun | Verify unlock account without entering reason | TC-86 | Verify account status change requires a reason | 0.58 |
| TC_015 | User story -1.2  Unlock Accoun | Verify unlock account with reason | TC-78 | Verify Support Admin can unlock a locked user acco | 0.58 |
| TC_013 | User story -1.2 User Login | Verify the OTP Screen | TC-38 | Verify system sends OTP to registered email | 0.58 |
| TC_016 | User story -1.3 Forgot Passwor | Verify “Wrong email? Go back” after timer expiry | TC-38 | Verify system sends OTP to registered email | 0.57 |
| TC_055 | User story -1.3 Force Password | Verify password fields are masked | TC-90 | Verify user is redirected to mandatory password ch | 0.57 |
| TC_073 | User story -1.3 Force Password | Verify password fields are masked | TC-90 | Verify user is redirected to mandatory password ch | 0.57 |
| TC_015 | User story -1.12  Admin & Staf | Verify the OTP Screen | TC-61 | Verify activation link is sent to new staff member | 0.57 |
| TC_020 | User story -1.4 Change Passwor | Verify enter matching password into the Confirm Ne | TC-43 | Verify new password is not identical to current pa | 0.56 |
| TC_002 | User story -1.13 Forgot Passwo | Verify UI elements displayed on the Forgot Passwor | TC-61 | Verify activation link is sent to new staff member | 0.56 |
| TC_025 | User story -1.3 Forgot Passwor | Verify system should not allow new password same a | TC-43 | Verify new password is not identical to current pa | 0.56 |
| TC_053 | User story -1.6 Account Deleti | Verify Delete account with Expired OTP | TC-34 | Verify no redirection to password change if 'Force | 0.56 |
| TC_011 | User story -1.12  Admin & Staf | Verify login with registered Email and valid passw | TC-68 | Verify automatic routing to Admin Console upon ful | 0.56 |
| TC_049 | User story -1.3 Force Password | Verify the Change password screen | TC-90 | Verify user is redirected to mandatory password ch | 0.56 |
| TC_064 | User story -1.3 Force Password | Verify password fields are masked | TC-90 | Verify user is redirected to mandatory password ch | 0.55 |
| TC_038 | User story -1.3 Forgot Passwor | Verify Click on Reset Password button | TC-40 | Verify redirection to Reset Password screen after  | 0.55 |
| TC_073 | Web-User Story -1.1 Public Lea | Verify enter data into the Buy-In conversion Rate  | TC-98 | Verify user is redirected to Mobile Leagues module | 0.55 |
| TC_020 | User story -1.6 Account Deleti | Verify Send verification code for SMS | TC-38 | Verify system sends OTP to registered email | 0.55 |
| TC_022 | User story -1.3 Forgot Passwor | Verify Reset Password page | TC-32 | Verify redirection to mandatory password change sc | 0.55 |
| TC_005 | User story -1.5 My Profile (Un | Verify the displaying of the Player Card in the Ed | TC-36 | Verify IP Address is logged upon successful login | 0.55 |
| TC_004 | User story - 1.4 Leagues - “Pu | Verify Private leagues are displayed in the listin | TC-115 | Verify 'Public Leagues' category is displayed on L | 0.55 |
| TC074 | User story -1.3 Members Teams  | Verify the Freeze/Unfreeze Wallet functionality. | TC-98 | Verify user is redirected to Mobile Leagues module | 0.55 |
| TC082 | User story -1.3 Members Teams  | Verify the functionality of the Unfreeze option | TC-98 | Verify user is redirected to Mobile Leagues module | 0.55 |
| TC_030 | User story -1.3 Forgot Passwor | Verify empty validation for New Password field | TC-42 | Verify new password meets complexity at minimum an | 0.55 |
| TC_035 | User story -1.3 Forgot Passwor | Verify empty validation for Confirm New Password | TC-42 | Verify new password meets complexity at minimum an | 0.55 |
| TC_041 | User story -1.8 Internal Admin | Verify OTP expiry | TC-61 | Verify activation link is sent to new staff member | 0.55 |
| TC_037 | User story -1.3 Forgot Passwor | Verify password mismatch validation | TC-39 | Verify system validates correct OTP successfully | 0.55 |
| TC-019 | User story -1.5 BAN User | Verify Ban Action Attempt on Already Banned User | TC-86 | Verify account status change requires a reason | 0.55 |
| TC_038 | User story -1.8 Internal Admin | Verify 2FA setup mandatory after password creation | TC-62 | Verify new staff account status is PENDING_ACTIVAT | 0.54 |
| TC_028 | User story -1.2 User Login | Verify successful password change during forced re | TC-32 | Verify redirection to mandatory password change sc | 0.54 |
| TC_005 | User story -1.3 Forgot Passwor | Verify Received OTP time limit | TC-38 | Verify system sends OTP to registered email | 0.54 |
| TC_028 | User story -1.3 Forgot Passwor | Verify password fields are masked | TC-37 | Successful Login with 2FA and Dashboard Redirectio | 0.54 |
| TC_007 | User story -1.10 Deactivate Ad | Verify inactive admin cannot login | TC-69 | Verify login attempt is blocked for an inactive st | 0.54 |
| TC_006 | User story -1.2  Unlock Accoun | Verify Reason field | TC-86 | Verify account status change requires a reason | 0.54 |
| TC_014 | User story -1.5 My Profile (Un | Verify the selection of the avatars from the Selec | TC-36 | Verify IP Address is logged upon successful login | 0.54 |
| TC_136 | User story -1.3 Leagues Dashbo | Verify Week value is displayed correctly | TC-99 | Verify display of Total Active and Upcoming League | 0.54 |
| TC_171 | User story -1.3 Leagues Dashbo | Verify Week value is displayed correctly | TC-99 | Verify display of Total Active and Upcoming League | 0.54 |
| TC_019 | User story -1.12  Admin & Staf | Verify OTP expiry validation | TC-61 | Verify activation link is sent to new staff member | 0.54 |
| TC_059 | User story -1.1 User Registrat | Verify default wallet creation | TC-26 | Verify system assigns default Global Wallet with 0 | 0.54 |
| TC_002 | User story -1.3 Forgot Passwor | Verify UI elements are displayed on the Forgot Pas | TC-38 | Verify system sends OTP to registered email | 0.54 |
| TC-002 | User Story -1.1 Post Login Lea | Verify the elements displayed in the Mobile League | TC-99 | Verify display of Total Active and Upcoming League | 0.54 |

## Appendix D — Unmatched AI Test Cases


AI cases with no strong manual analog (similarity < 12%): **71**

| TC# | Title | Story ID | Type |
| --- | --- | --- | --- |
| 1 | Verify registration prevented for users under 18 | 326 | positive |
| 2 | Verify registration rejected with future Date of Birth | 326 | negative |
| 3 | Verify registration rejected with malformed Date of Birth | 326 | negative |
| 4 | Verify explicit consent for Terms of Service allows registration progr | 326 | positive |
| 5 | Verify timestamp logging for Privacy Policy consent | 326 | positive |
| 6 | Verify timestamp logging for all legal consent actions | 326 | positive |
| 7 | Verify IP address logging for all legal consent actions | 326 | positive |
| 8 | Verify publicly accessible URL for Terms of Service document | 326 | positive |
| 9 | Verify publicly accessible URL for Privacy Policy document | 326 | positive |
| 10 | Verify Super Admin can successfully configure organization accounts fo | 327 | positive |
| 11 | Verify Super Admin can successfully define a new In-App Purchase (IAP) | 327 | positive |
| 12 | Verify Super Admin can successfully manage (edit) an existing In-App P | 327 | positive |
| 13 | Verify Super Admin can successfully link to an App Store developer acc | 327 | positive |
| 14 | Verify Super Admin can successfully link to a Google Play developer ac | 327 | positive |
| 15 | Verify Super Admin can successfully manage app metadata and submission | 327 | positive |
| 16 | Verify system collects Date of Birth during registration | 328 | positive |
| 17 | Verify registration proceeds for user aged 18 or older | 328 | positive |
| 19 | Verify registration is blocked for user aged 1 day old | 328 | negative |
| 20 | Verify system ensures entered Email is unique during registration | 328 | positive |
| 21 | Verify system ensures entered Username is unique during registration | 328 | positive |
| 22 | Verify Username adheres to specified constraints (valid chars, no spac | 328 | positive |
| 23 | Verify Username adheres to maximum length constraint (20 characters) | 328 | boundary |
| 24 | Verify explicit acceptance of Terms of Service is required for registr | 328 | positive |
| 25 | Verify explicit acceptance of Privacy Policy is required for registrat | 328 | positive |
| 27 | Verify system assigns 'Rookie' Tier status upon successful registratio | 328 | positive |
| 29 | Verify system prompts for 2FA after successful username/password valid | 329 | positive |
| 30 | Verify account locks for 30 minutes after 3 failed OTP attempts | 329 | positive |
| 44 | Verify system displays error message for expired OTP | 330 | positive |
| 45 | Verify system displays error message for invalid OTP | 330 | negative |
| 49 | Verify user can upload a valid JPG avatar within size limit | 331 | positive |
| 50 | Verify avatar upload succeeds with a 5MB JPG file | 331 | boundary |
| 51 | Verify avatar updates immediately across historical leagues | 331 | positive |
| 52 | Verify avatar updates immediately across active leagues | 331 | positive |
| 53 | Verify user can edit First Name, Last Name, and Username | 331 | positive |
| 54 | Verify user can edit Bio and update Username with unique value | 331 | positive |
| 56 | Verify profile updates successfully when all mandatory fields are vali | 331 | positive |
| 58 | Verify profile update fails when Username is not unique | 331 | negative |
| 59 | Verify system handles null input for a mandatory field (Username) grac | 331 | edge |
| 60 | Verify Super Admin can create new staff account with valid details | 332 | positive |
| 72 | Verify user accounts list is filterable within the Admin Console | 334 | positive |
| 74 | Verify search by Username, Email, or Phone Number supports case-insens | 334 | positive |
| 76 | Verify all required key user details are displayed for each account | 334 | positive |
| 77 | Verify pagination controls function correctly for large user lists | 334 | positive |
| 80 | Verify Ops Admin can suspend a user account for a defined duration | 335 | positive |
| 82 | Verify Super Admin can suspend a user account for minimum allowed dura | 335 | boundary |
| 87 | Verify audit log records all required details for account status chang | 335 | positive |
| 91 | Verify user cannot bypass mandatory password change after force reset | 336 | negative |
| 92 | Verify mandatory password change rejects invalid new password | 336 | negative |
| 93 | Verify Super Admin can initiate soft delete of a user account | 336 | positive |
| 97 | Verify soft delete actions require a reason and are audit logged | 336 | positive |
| 109 | Verify navigation to past and current weeks in Matchup view | 338 | positive |
| 110 | Verify navigation to future weeks in Matchup view | 338 | positive |
| 113 | Verify Standings module displays ranked teams by W-L-T records | 338 | positive |
| 114 | Verify Standings module applies tie-breakers and highlights current us | 338 | positive |
| 122 | Verify player values in the ticker update at the defined interval | 340 | positive |
| 123 | Verify ticker updates precisely at the 45-second interval boundary | 340 | boundary |
| 124 | Verify user can successfully buy shares of an available player | 340 | positive |
| 137 | Verify automatic tier update upon reaching next XP threshold | 342 | positive |
| 140 | Verify Ops Admin can configure XP rank levels and tier definitions | 343 | positive |
| 143 | Verify scoring calculations are accurate across all leagues | 343 | positive |
| 145 | Verify email confirmation sent on successful password change | 344 | positive |
| 146 | Verify notification sent on account status change to suspended | 344 | positive |
| 147 | Verify push notification sent for league matchup update | 344 | positive |
| 148 | Verify in-app message displayed for critical system alert | 344 | positive |
| 149 | Verify user can toggle push notification preference | 344 | positive |
| 150 | Verify Ops Admin can send targeted message to a specific user | 345 | positive |
| 151 | Verify Ops Admin can send emergency broadcast to all users | 345 | positive |
| 152 | Verify targeted message requires a valid reason code | 345 | positive |
| 153 | Verify emergency broadcast requires a valid reason code | 345 | positive |
| 154 | Verify system logs all sent communications | 345 | positive |
| 155 | Verify Ops Admin can enable/disable reminder timing offsets | 345 | positive |

---

## Related: UI Discovery Pipeline

See [F2MX-UI-Discovery-Pipeline-Validation-Addendum.md](./F2MX-UI-Discovery-Pipeline-Validation-Addendum.md) for the f2mx-2 pilot validation checklist and expected coverage delta after enabling UI Discovery → Stories → Test Cases generation.