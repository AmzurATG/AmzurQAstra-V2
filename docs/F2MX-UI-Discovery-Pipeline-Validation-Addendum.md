
---

## Addendum: UI Discovery Pipeline Validation (f2mx-2)

**Date:** 2026-06-11  
**Feature:** UI Discovery → Stories → Test Cases pipeline (web v1)  
**Target project:** f2mx-2 (ID 18) — https://atg-f2mx.amzur.com/

### What changed

QAstra now supports a **UI Discovery** build check that captures structured page/element inventory from the live app and feeds it into:

1. **BRD story generation** (Pass 1b UI merge, up to 60 stories, UI-grounded AC)
2. **Bulk test generation** (`production_web` profile — comprehensive matrix + UI smoke rows)
3. **Test step generation** (exact labels from inventory when available)

### Validation checklist (f2mx-2 pilot)

| Step | Action | Expected outcome | Baseline (pre-pipeline) |
|------|--------|------------------|-------------------------|
| 1 | Run UI Discovery (web, end_user) against ATG URL | Inventory includes Login, Leagues (tabs), Profile/Security | 0 integrity/discovery runs |
| 2 | Compare inventory modules to Sprint 1/2 manual sheets | Modules align with Authentication, Leagues, Profile, Wallet areas | Text-only BRD decomposition |
| 3 | Re-generate stories with **Include UI context** (max 40–60) | **40+ stories** vs prior 20 | 20 `brd_generated` stories |
| 4 | Bulk gen **Production Web** profile on all new stories | **400–700 cases** vs prior 155 | 155 cases (`standard`, ~10/story) |
| 5 | Spot-check 10 generated test steps | Labels match discovered UI (Email, Leagues tabs, etc.) | Plain-English generic labels |
| 6 | Run smoke subset (30 cases) via test execution | Measure pass rate vs prior runs (baseline: 0 fully successful runs) | 8 runs, none fully successful |

### Expected coverage delta

| Dimension | Before | After (expected) |
|-----------|--------|------------------|
| User stories | 20 | 40–60 (BRD + UI-only pages) |
| Test cases | 155 | 400–700 (`production_web`) |
| UI smoke rows | 0 | ~5 per story (capped) |
| Step label grounding | None | Inventory labels in prompts |
| Platform metadata on cases | None | `platform=web`, `actor_role`, optional `ui_page_ref` |

### How to run the pilot

1. **Integrity Check** → Run UI Discovery (End User role, project credentials)
2. **Requirements** → Generate Stories (Include UI context ON, max stories 60)
3. Accept stories → auto-navigate to **User Stories** with Production Web bulk gen modal
4. Poll job completion; export sample cases for manual label comparison
5. Update this addendum with actual counts after the run completes

### Notes

- Admin-role discovery (support_admin) is supported in API but secondary for f2mx pilot; end-user path validates the primary ATG experience first.
- Full manual parity (~3,000 cases) still requires multi-role discovery, mobile scope, and additional matrix profiles — out of v1 scope.
- Re-run discovery if inventory is **>7 days stale** (Requirements page shows banner).
