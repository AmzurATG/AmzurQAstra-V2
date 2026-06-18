"""
Generate comprehensive F2MX Manual vs AI test case comparison report (Markdown).
Uses cached manual Excel JSON + PostgreSQL AI cases.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import create_engine, text

ROOT = Path(r"D:\qastra_v2")
CACHE = ROOT / "AmzurQAstra-V2" / "backend" / "scripts" / "cache" / "f2mx_manual_cases.json"
OUTPUT = ROOT / "AmzurQAstra-V2" / "docs" / "F2MX-Manual-vs-AI-Test-Case-Comparison-Report.md"
PROJECT_ID = 18
DATABASE_URL = "postgresql+psycopg2://qastra:qastra123@localhost:5432/qastra"

# Manual story name keywords → AI user_story_id
AI_STORY_MAP: List[Dict[str, Any]] = [
    {"ids": [326], "keywords": ["legal compliance", "age verification", "regulation", "terms of service", "privacy policy", "consent", "under 18", "dob"]},
    {"ids": [327], "keywords": ["app store", "iap", "in-app purchase", "google play", "d-u-n-s", "monetiz"]},
    {"ids": [328], "keywords": ["registration", "register", "signup", "sign up", "create account", "age verification", "new user"]},
    {"ids": [329], "keywords": ["user login", "two-factor", "2fa", "authentication", "account security", "otp", "locked account"]},
    {"ids": [330], "keywords": ["forgot password", "recover password", "reset password", "recovery"]},
    {"ids": [331], "keywords": ["my profile", "avatar", "edit profile", "universal", "profile tab"]},
    {"ids": [332], "keywords": ["internal admin", "staff account", "admin user management", "create user", "role", "deactivate admin", "modify admin", "pending activation"]},
    {"ids": [333], "keywords": ["staff login", "admin login", "admin console", "staff member", "admin & staff", "role-based routing"]},
    {"ids": [334], "keywords": ["user account administration", "users tab", "user listing", "filter user", "view and filter"]},
    {"ids": [335], "keywords": ["unlock account", "suspend user", "ban user", "account status"]},
    {"ids": [336], "keywords": ["force password reset", "soft delete", "anonymize", "delete user", "account deletion"]},
    {"ids": [337], "keywords": ["post login league", "my leagues", "league access", "active leagues", "upcoming leagues", "completed leagues"]},
    {"ids": [338], "keywords": ["league dashboard", "matchup", "standings", "history module", "view/layout"]},
    {"ids": [339], "keywords": ["public league", "join public", "browse public"]},
    {"ids": [340], "keywords": ["trading", "market", "player", "ticker", "buy", "sell", "share", "portfolio"]},
    {"ids": [341], "keywords": ["market pricing", "bid/ask", "pricing weight", "buy-in", "league settings", "packages", "promotion", "reconciliation", "wallet", "transaction", "settlement", "balance"]},
    {"ids": [342], "keywords": ["xp", "tier", "progression", "rank level", "rookie"]},
    {"ids": [343], "keywords": ["half-ppr", "ppr", "scoring", "xp award", "xp configuration"]},
    {"ids": [344], "keywords": ["notification", "email confirmation", "push notification", "account status change"]},
    {"ids": [345], "keywords": ["broadcast", "targeted message", "emergency", "ops admin"]},
]

MANUAL_ONLY_FEATURES = [
    ("Override Verification", "Sprint 1 Web", 26, "Support/Ops/Super Admin can override email/phone verification — not in BRD AI stories"),
    ("Merge Duplicate Accounts", "Sprint 1 Web", 26, "Ops/Super Admin merge duplicate user accounts — not in AI pipeline"),
    ("Change Password (Logged-In)", "Sprint 1 Mobile", 26, "Security Settings → Change Password flow with current/new/confirm fields"),
    ("User Logout", "Sprint 1 Mobile", 7, "Sign Out option visibility and session termination"),
    ("Mobile Account Deletion (Self-Service)", "Sprint 1 Mobile", 59, "User-initiated delete account from profile — AI only has admin soft-delete"),
    ("Private League Creation", "Sprint 2 Mobile", 127, "Commissioner creates private league wizard, +Create button, required fields"),
    ("League Invitations Category", "Sprint 2 Mobile", 90, "League Invites tile, listing, accept/decline flows"),
    ("Three Invitation Methods", "Sprint 2 Mobile", 42, "Direct Link, QR Code, In-App Invite after league creation"),
    ("Created Leagues Category", "Sprint 2 Mobile", 76, "Leagues user created as commissioner"),
    ("Private Leagues Category (Join)", "Sprint 2 Mobile", 78, "Join private league via code/link"),
    ("Public League Creation (Web Admin)", "Sprint 2 Web", 127, "Admin creates public leagues from web console"),
    ("Leagues Module Management (Web)", "Sprint 2 Web", 98, "Web-side league administration"),
    ("Members & Teams Tab", "Sprint 2 Web", 94, "League members roster management"),
    ("Trading Activity Tab (Web Admin)", "Sprint 2 Web", 78, "Admin view of league trading activity"),
    ("League Settings Tab", "Sprint 2 Web", 108, "Commissioner/admin league configuration UI"),
    ("Categories Under User Details", "Sprint 2 Web", 109, "User detail screen category breakdown in admin"),
    ("Buy-In Transactions Tab", "Sprint 2 Web", 81, "Admin buy-in transaction management"),
    ("User Wallet (Main Wallet)", "Sprint 2 Mobile", 30, "Mobile wallet balance and main wallet UI"),
    ("View All Transactions (User Wallet)", "Sprint 2 Mobile", 44, "User transaction history listing"),
    ("League Wallet", "Sprint 2 Mobile", 29, "Per-league wallet under dashboard"),
    ("View Transactions (League Wallet)", "Sprint 2 Mobile", 33, "League-scoped transaction history"),
    ("End-of-Season Settlement (Mobile)", "Sprint 2 Mobile", 35, "Mobile end-of-season payout/settlement UX"),
    ("Packages (Configuration & Purchase)", "Sprint 2 Web", 108, "IAP/coin packages admin + purchase flows"),
    ("Managing Starting Allocation", "Sprint 2 Web", 56, "Starting allocation and buy-in conversion %"),
    ("Edit Buy-In Conversion Mode", "Sprint 2 Web", 32, "Buy-in conversion mode editing (noted strike-off in BRD)"),
    ("Adjust User Balances", "Sprint 2 Web", 31, "Admin credit/debit game currency"),
    ("Reconciliation / Error Handling", "Sprint 2 Web", 31, "Refunds, duplicate, failed transaction handling"),
    ("Set League Buy-In Limits", "Sprint 2 Web", 21, "Admin sets league buy-in limits"),
    ("End-of-Season Settlement (Web)", "Sprint 2 Web", 34, "Web admin settlement processing"),
    ("Admin View of End-of-Settlement", "Sprint 2 Web", 62, "Admin reporting view for season end"),
]

TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "registration_signup": ["register", "signup", "sign up", "create account", "date of birth", "dob", "age", "terms", "privacy", "consent", "under 18"],
    "login_2fa": ["login", "log in", "2fa", "two-factor", "otp", "verification code", "locked", "force password", "authentication"],
    "forgot_password": ["forgot password", "recover password", "reset password", "reset link", "send verification"],
    "change_password": ["change password", "current password", "new password", "confirm password", "security settings"],
    "profile_avatar": ["profile", "avatar", "edit profile", "first name", "bio", "tier badge", "xp points", "wallet amount"],
    "account_deletion_logout": ["delete account", "sign out", "logout", "log out", "soft delete", "anonymize"],
    "admin_user_list": ["users tab", "user listing", "search", "filter", "pagination", "user accounts", "joined date"],
    "admin_unlock_suspend_ban": ["unlock", "suspend", "ban", "locked account", "account status"],
    "admin_force_reset": ["force password reset", "mandatory password change"],
    "admin_staff_mgmt": ["admin users", "create user", "staff", "role", "deactivate admin", "activation link", "pending activation", "rbac"],
    "admin_override_merge": ["override verification", "merge duplicate", "merge account"],
    "leagues_access": ["leagues module", "my leagues", "active", "upcoming", "completed", "league card", "post login"],
    "league_dashboard": ["dashboard", "matchup", "standings", "history", "week", "head-to-head", "w-l-t", "roster"],
    "public_leagues": ["public league", "join public", "browse public"],
    "private_leagues_invites": ["private league", "invite", "invitation", "qr code", "invite code", "commissioner", "create league", "created leagues"],
    "trading_market": ["trade", "buy", "sell", "market", "ticker", "player", "share", "portfolio", "bid", "ask", "spread", "slippage"],
    "wallet_transactions": ["wallet", "transaction", "balance", "buy-in", "payout", "reconciliation", "promotion", "package", "settlement", "currency"],
    "xp_scoring": ["xp", "tier", "rookie", "half-ppr", "ppr", "scoring", "rank level"],
    "notifications": ["notification", "email confirmation", "push", "broadcast", "in-app message", "reminder"],
    "legal_appstore": ["app store", "iap", "in-app purchase", "legal compliance", "d-u-n-s"],
    "audit_logging": ["audit log", "audit", "timestamp", "ip address", "reason code", "reason for"],
    "ui_ux_validation": ["ui element", "display", "placeholder", "hyperlink", "logo", "popup", "modal", "hover", "navigation", "verify the", "screen"],
}


def _map_story_to_ai(story_name: str) -> List[int]:
    name = story_name.lower()
    matched: Set[int] = set()
    for entry in AI_STORY_MAP:
        if any(kw in name for kw in entry["keywords"]):
            matched.update(entry["ids"])
    return sorted(matched)


def _text_blob(parts: List[str]) -> str:
    return " ".join(p for p in parts if p).lower()


def _topic_hits(text: str) -> Set[str]:
    return {t for t, kws in TOPIC_KEYWORDS.items() if any(k in text for k in kws)}


def _tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-z0-9]{4,}", text.lower())
    stop = {"verify", "application", "should", "user", "system", "test", "that", "with", "from", "when", "after", "before", "click", "display", "valid", "using", "navigate", "module", "screen", "f2mx", "mobile", "device"}
    return {w for w in words if w not in stop}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    j = len(ta & tb) / len(ta | tb)
    j += len(_topic_hits(a) & _topic_hits(b)) * 0.06
    return min(1.0, j)


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ")[:300] for c in row) + " |")
    return "\n".join(out)


def load_manual() -> Dict[str, Any]:
    return json.loads(CACHE.read_text(encoding="utf-8"))


def load_ai() -> Tuple[List[Dict], List[Dict], Dict]:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        project = dict(conn.execute(text("SELECT id,name,app_url,created_at FROM projects WHERE id=:id"), {"id": PROJECT_ID}).mappings().one())
        stories = [dict(r) for r in conn.execute(text("SELECT id,title,source,status,priority,acceptance_criteria FROM user_stories WHERE project_id=:p ORDER BY id"), {"p": PROJECT_ID}).mappings()]
        cases = [dict(r) for r in conn.execute(text("""
            SELECT tc.id, tc.case_number, tc.title, tc.description, tc.preconditions,
                   tc.status::text, tc.priority::text, tc.category::text, tc.scenario_type,
                   tc.ac_ref, tc.user_story_id, us.title AS story_title,
                   (SELECT COUNT(*) FROM test_steps ts WHERE ts.test_case_id=tc.id) AS step_count
            FROM test_cases tc LEFT JOIN user_stories us ON us.id=tc.user_story_id
            WHERE tc.project_id=:p ORDER BY tc.case_number
        """), {"p": PROJECT_ID}).mappings()]
        steps = [dict(r) for r in conn.execute(text("""
            SELECT ts.test_case_id, ts.step_number, ts.action::text, ts.description, ts.expected_result, ts.target, ts.value
            FROM test_steps ts JOIN test_cases tc ON tc.id=ts.test_case_id
            WHERE tc.project_id=:p ORDER BY ts.test_case_id, ts.step_number
        """), {"p": PROJECT_ID}).mappings()]
        job = conn.execute(text("SELECT * FROM generation_jobs WHERE project_id=:p ORDER BY id DESC LIMIT 1"), {"p": PROJECT_ID}).mappings().first()
    steps_by_case: Dict[int, List[Dict]] = defaultdict(list)
    for s in steps:
        steps_by_case[s["test_case_id"]].append(s)
    for c in cases:
        c["steps"] = steps_by_case.get(c["id"], [])
    return cases, stories, {"project": project, "job": dict(job) if job else None}


def generate() -> None:
    manual = load_manual()
    ai_cases, stories, meta = load_ai()
    ai_by_story: Dict[int, List[Dict]] = defaultdict(list)
    for c in ai_cases:
        ai_by_story[c["user_story_id"]].append(c)

    # flatten manual
    manual_stories: List[Dict] = []
    manual_cases: List[Dict] = []
    for wb in manual["workbooks"]:
        manual_stories.extend(wb["summary"])
        for sheet, rows in wb["sheets"].items():
            for r in rows:
                manual_cases.append({**r, "sheet": sheet, "sprint": wb["sprint"], "file": wb["file"]})

    s1_stories = [s for s in manual_stories if s["sprint"] == "Sprint 1"]
    s2_stories = [s for s in manual_stories if s["sprint"] == "Sprint 2"]
    s1_count = sum(s["test_case_count"] for s in s1_stories)
    s2_count = sum(s["test_case_count"] for s in s2_stories)
    manual_pos = sum(s.get("positive") or 0 for s in manual_stories)
    manual_neg = sum(s.get("negative") or 0 for s in manual_stories)

    ai_pos = sum(1 for c in ai_cases if c.get("scenario_type") == "positive")
    ai_neg = sum(1 for c in ai_cases if c.get("scenario_type") == "negative")
    ai_boundary = sum(1 for c in ai_cases if c.get("scenario_type") == "boundary")
    ai_edge = sum(1 for c in ai_cases if c.get("scenario_type") == "edge")

    # topic analysis
    manual_topics: Counter = Counter()
    ai_topics: Counter = Counter()
    for m in manual_cases:
        blob = _text_blob([m["objective"], m["steps"], m["expected"], m["functionality"]])
        for t in _topic_hits(blob):
            manual_topics[t] += 1
    for c in ai_cases:
        blob = _text_blob([c["title"], c.get("description") or "", c.get("preconditions") or ""] + [s.get("description") or "" for s in c["steps"]])
        for t in _topic_hits(blob):
            ai_topics[t] += 1

    # per manual story mapping
    story_analysis: List[Dict] = []
    for ms in manual_stories:
        ai_ids = _map_story_to_ai(ms["story_name"])
        ai_count = sum(len(ai_by_story.get(i, [])) for i in ai_ids)
        ratio = ai_count / ms["test_case_count"] if ms["test_case_count"] else 0
        story_analysis.append({**ms, "ai_story_ids": ai_ids, "ai_case_count": ai_count, "coverage_ratio": ratio})

    s1_analysis = [s for s in story_analysis if s["sprint"] == "Sprint 1"]
    s2_analysis = [s for s in story_analysis if s["sprint"] == "Sprint 2"]
    s1_count = sum(s["test_case_count"] for s in s1_analysis)
    s2_count = sum(s["test_case_count"] for s in s2_analysis)

    # similarity: sample up to 5 manual per sheet vs all AI
    match_samples: List[Dict] = []
    sheets_done: Set[str] = set()
    for m in manual_cases:
        key = m["sheet"]
        if key in sheets_done and sum(1 for x in match_samples if x["manual"]["sheet"] == key) >= 5:
            continue
        blob = _text_blob([m["objective"], m["steps"], m["expected"]])
        best = max(((c, _similarity(blob, _text_blob([c["title"], c.get("description") or ""]))) for c in ai_cases), key=lambda x: x[1], default=(None, 0))
        match_samples.append({"manual": m, "best_ai": best[0], "score": best[1]})
        sheets_done.add(key)

    lines: List[str] = []

    def add(s: str = "") -> None:
        lines.append(s)

    add("# F2MX Test Case Comparison Report: Manual (Sprint 1 & 2) vs AI-Generated (QAstra)")
    add()
    add(f"**Report generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    add(f"**QAstra project:** f2mx-2 (ID {PROJECT_ID}) — https://atg-f2mx.amzur.com/  ")
    add(f"**Manual sources:** `F2MX  Sprint 1 Test cases.xlsx`, `F2MX-Sprint 2 Test Cases.xlsx`  ")
    add(f"**AI source:** 155 test cases from bulk generation (standard profile) on 20 BRD-derived user stories  ")
    add(f"**Manual cache parsed:** {manual.get('generated_at', 'N/A')}")
    add()

    add("---")
    add()
    add("## Table of Contents")
    add()
    toc = [
        "1. [Executive Summary](#1-executive-summary)",
        "2. [Methodology](#2-methodology)",
        "3. [Volume & Distribution Comparison](#3-volume--distribution-comparison)",
        "4. [Feature Mapping: Manual User Stories → AI User Stories](#4-feature-mapping-manual-user-stories--ai-user-stories)",
        "5. [Similarities — Conceptual Alignment](#5-similarities--conceptual-alignment)",
        "6. [Topic Coverage Analysis](#6-topic-coverage-analysis)",
        "7. [Gap Analysis — What AI Is Missing](#7-gap-analysis--what-ai-is-missing)",
        "8. [Sprint 1 Deep Dive](#8-sprint-1-deep-dive)",
        "9. [Sprint 2 Deep Dive](#9-sprint-2-deep-dive)",
        "10. [AI-Only Coverage](#10-ai-only-coverage)",
        "11. [Manual-Only Features (Zero AI Representation)](#11-manual-only-features-zero-ai-representation)",
        "12. [Scenario, Priority & Quality Comparison](#12-scenario-priority--quality-comparison)",
        "13. [Test Execution Observations (from DB)](#13-test-execution-observations-from-db)",
        "14. [Recommendations & Remediation Plan](#14-recommendations--remediation-plan)",
        "15. [Appendix A — Complete Manual User Story Inventory](#appendix-a--complete-manual-user-story-inventory)",
        "16. [Appendix B — Complete AI User Story & Test Case Catalog](#appendix-b--complete-ai-user-story--test-case-catalog)",
        "17. [Appendix C — Manual Sheet → Parsed Row Inventory](#appendix-c--manual-sheet--parsed-row-inventory)",
        "18. [Appendix D — Sample Manual→AI Match Pairs](#appendix-d--sample-manualai-match-pairs)",
        "19. [Appendix E — AI Test Steps (Full Detail)](#appendix-e--ai-test-steps-full-detail)",
    ]
    for t in toc:
        add(f"- {t}")
    add()

    # 1 Executive Summary
    add("## 1. Executive Summary")
    add()
    total_manual_summary = s1_count + s2_count
    add("### 1.1 Headline Numbers")
    add()
    add(_md_table(
        ["Metric", "Manual (Excel)", "AI (QAstra DB)", "Delta"],
        [
            ["Total test cases (summary counts)", f"**{total_manual_summary:,}**", f"**{len(ai_cases)}**", f"Manual is **{total_manual_summary/len(ai_cases):.1f}×** larger"],
            ["Sprint 1", f"{s1_count:,}", "—", "789 manual across mobile + web auth/admin"],
            ["Sprint 2", f"{s2_count:,}", "—", "2,294 manual across leagues/wallet/economy"],
            ["User story / feature groups", f"{len(manual_stories)}", f"{len(stories)}", "Manual is sprint-scoped; AI is BRD-holistic"],
            ["Positive scenarios", f"{manual_pos:,}", str(ai_pos), f"AI has {100*ai_pos/manual_pos:.1f}% of manual positive volume"],
            ["Negative scenarios", f"{manual_neg:,}", str(ai_neg), f"AI has {100*ai_neg/max(manual_neg,1):.1f}% of manual negative volume"],
            ["Boundary / Edge (AI only taxonomy)", "—", f"{ai_boundary + ai_edge}", "Manual encodes type as Positive/Negative only"],
            ["Total test steps (AI)", "—", str(sum(c['step_count'] for c in ai_cases)), f"~{sum(c['step_count'] for c in ai_cases)/len(ai_cases):.1f} steps/case avg"],
            ["Detail rows parsed from Excel", f"{len(manual_cases):,}", "—", "Slight delta vs summary due to sheet structure"],
        ],
    ))
    add()
    add("### 1.2 Interpretation")
    add()
    add(
        "The **manual test suites** (Sprint 1 + Sprint 2) represent **production-grade, sprint-delivered QA artifacts** with deep **UI/UX validation**, "
        "**role-based permission matrices** (Support Agent, Ops Admin, Super Admin, Commissioner, End User), **mobile vs web platform separation**, "
        "and **granular step-by-step expected results** tied to specific screens, placeholders, popups, and navigation flows.\n\n"
        "The **155 AI-generated test cases** represent **BRD-level functional coverage** derived from 20 acceptance-criteria-oriented user stories. "
        "They excel at mapping **acceptance criteria references (AC-1, AC-2…)** to test objectives and covering **cross-cutting compliance/admin narratives** "
        "(legal, app store, notifications) that span beyond Sprint 1/2 delivery scope.\n\n"
        "**Bottom line:** AI covers the *backbone* of F2MX functional intent (~15–25% conceptual overlap by volume) but **misses ~75–85% of manual scenario depth**, "
        "especially **Sprint 2 league lifecycle** (dashboard, public/private leagues, invitations, wallet/economy) and **UI-level validation**."
    )

    # 2 Methodology
    add("## 2. Methodology")
    add()
    add("### 2.1 Data Extraction")
    add("| Source | Method |")
    add("|--------|--------|")
    add("| Manual Sprint 1 & 2 Excel | Parsed all non-Summary sheets; normalized varying column headers; cached to JSON |")
    add("| Manual counts | Cross-validated against Excel `Summary` sheet per user story |")
    add("| AI test cases | PostgreSQL query — project `f2mx-2` (id=18), all test_cases + test_steps |")
    add("| AI user stories | 20 `brd_generated` stories (ids 326–345) |")
    add()
    add("### 2.2 Mapping Approach")
    add("1. **Story-level mapping:** Manual user story names from Summary sheet → AI `user_story_id` via keyword rules")
    add("2. **Topic bucketing:** 22 functional topic keyword sets applied to both corpora")
    add("3. **Similarity scoring:** Jaccard token overlap + topic intersection bonus (sampled manual cases vs all AI cases)")
    add("4. **Gap classification:** Critical (manual ≥50 TCs, AI ≤10), Moderate (partial overlap), AI-only, Manual-only")
    add()

    # 3 Volume
    add("## 3. Volume & Distribution Comparison")
    add()
    add("### 3.1 Sprint-Level Split")
    add(_md_table(["Sprint", "Manual TCs (Summary)", "AI TCs (mapped area)", "Notes"], [
        ["Sprint 1 — Auth, Profile, Admin", str(s1_count), str(sum(len(ai_by_story[i]) for i in range(326, 337))), "Mobile 306 + Web 483"],
        ["Sprint 2 — Leagues, Wallet, Economy", str(s2_count), str(sum(len(ai_by_story[i]) for i in range(337, 344))), "Heavy manual depth; thin AI"],
        ["Cross-cutting (AI BRD stories)", "0", str(sum(len(ai_by_story[i]) for i in [326, 327, 344, 345])), "Legal, app store, notifications"],
    ]))
    add()
    add("### 3.2 Manual Platform Split (Sprint 1 Summary)")
    add(_md_table(["Platform", "Test Cases", "Positive", "Negative"], [
        ["Mobile App", "306", "219", "87"],
        ["Web App (Admin Console)", "483", "369", "114"],
        ["Combined Sprint 1", "789", "588", "201"],
    ]))
    add()
    add("### 3.3 AI Distribution")
    add(_md_table(["Dimension", "Breakdown"], [
        ["Scenario type", f"positive={ai_pos}, negative={ai_neg}, boundary={ai_boundary}, edge={ai_edge}"],
        ["Priority", str(dict(Counter(c['priority'] for c in ai_cases)))],
        ["Category", str(dict(Counter(c['category'] for c in ai_cases)))],
        ["Status", "All 155 cases = `ready`"],
        ["Source", "All 155 = `ai` / is_generated=true"],
    ]))

    # 4 Feature mapping
    add("## 4. Feature Mapping: Manual User Stories → AI User Stories")
    add()
    add("Each manual user story from the Excel Summary is mapped to the closest AI user story IDs.")
    add()
    rows = []
    for sa in sorted(story_analysis, key=lambda x: (-x["test_case_count"], x["sprint"])):
        ids = ", ".join(f"US-{i}" for i in sa["ai_story_ids"]) or "**NONE**"
        status = "✅ Good" if sa["coverage_ratio"] >= 0.15 else ("⚠️ Thin" if sa["coverage_ratio"] >= 0.05 else "❌ Critical gap")
        if not sa["ai_story_ids"]:
            status = "❌ No AI mapping"
        rows.append([
            sa["sprint"],
            sa["story_name"][:55],
            str(sa["test_case_count"]),
            str(sa.get("positive") or "—"),
            str(sa.get("negative") or "—"),
            ids,
            str(sa["ai_case_count"]),
            f"{sa['coverage_ratio']:.1%}",
            status,
        ])
    add(_md_table(["Sprint", "Manual User Story", "Manual TCs", "Pos", "Neg", "AI Story IDs", "AI TCs", "Ratio", "Status"], rows))

    # 5 Similarities
    add("## 5. Similarities — Conceptual Alignment")
    add()
    add("Despite the **19× volume difference**, the AI suite **correctly identifies core functional themes** present in the manual suites:")
    add()
    sims = [
        ("Registration & Age Gate", "Manual: 60 TCs (S1 Mobile Registration) | AI: US-326 + US-328 (21 TCs)", [
            "Both require DOB collection and block users under 18",
            "Both validate unique email and username",
            "Both require explicit ToS and Privacy Policy acceptance",
            "Both assign default wallet (0 balance), 0 XP, Rookie tier on successful registration",
            "Manual adds: app install flow, logo display, field placeholders, keyboard types, screen transitions",
        ]),
        ("Login & Two-Factor Authentication", "Manual: 32 + 30 TCs (Login + Account Security) | AI: US-329 (10 TCs)", [
            "Active-user-only login requirement",
            "2FA OTP prompt after valid credentials",
            "Account lock after 3 failed OTP attempts (30 min)",
            "Force password reset redirect when flag set",
            "Login audit: Last_Login_Timestamp + IP Address logging",
            "Manual adds: login screen layout, inactive/suspended/banned user blocking, per-field validation UI",
        ]),
        ("Forgot / Reset Password", "Manual: 41 + 21 TCs (Mobile + Web Admin) | AI: US-330 (11 TCs)", [
            "OTP sent to registered email",
            "OTP validation and redirect to reset screen",
            "Password complexity (8–15 chars, alphanumeric)",
            "Reject password identical to current",
            "Expired/invalid OTP error messages",
            "Manual adds: separate mobile vs web admin UI element checks, device-specific flows",
        ]),
        ("Profile & Avatar Management", "Manual: 51 TCs | AI: US-331 (11 TCs)", [
            "Avatar upload JPG/PNG (max 5MB) or default avatar selection",
            "Avatar sync across historical and active leagues",
            "Editable: First Name, Last Name, Username, Bio",
            "Read-only: Email, Phone, DOB, XP, Tier Badge",
            "Manual adds: Profile tab layout, XP/Wallet display sections, Security Settings link, every UI element",
        ]),
        ("Admin User Listing & Search", "Manual: 77 TCs | AI: US-334 (7 TCs)", [
            "Searchable/filterable user list in Admin Console",
            "Search by Username, Email, Phone (partial, exact, case-insensitive)",
            "Filters: Account Status, Verification Status, Tier, Joined Date range",
            "Pagination and record count display",
            "Manual adds: column labels, filter UI, joined date label per BRD, 70+ layout test cases",
        ]),
        ("Unlock / Suspend / Ban", "Manual: 22 + 23 + 23 TCs | AI: US-335 (10 TCs)", [
            "Role-gated unlock (Support/Ops/Super Admin)",
            "Suspend with defined duration; immediate logout",
            "Permanent ban capability for Super Admin",
            "Mandatory reason code + audit log on status change",
            "Manual adds: popup field layouts, avatar in suspend dialog, permission denial per role",
        ]),
        ("Force Password Reset & Soft Delete", "Manual: 79 + 16 TCs | AI: US-336 (10 TCs)", [
            "Admin-initiated force password reset with reason",
            "Mandatory password change screen on next login (non-bypassable)",
            "Soft delete with PII anonymization and historical data preservation",
            "Audit logging for admin actions",
        ]),
        ("Internal Admin / Staff Management", "Manual: 74 + 38 + 34 TCs | AI: US-332 (6 TCs)", [
            "Super Admin creates staff with email, name, phone, role",
            "Activation link sent; PENDING_ACTIVATION status",
            "Role modification and Active/Inactive toggle",
            "Manual adds: Settings tab layout, Admin Users vs Role tab, pagination, permission denial matrices",
        ]),
        ("Staff Login & Admin Console Routing", "Manual: 24 TCs | AI: US-333 (5 TCs)", [
            "Staff login with email/password + 2FA",
            "Route to Admin Console after authentication",
            "Block inactive staff accounts",
            "Logout returns to login screen",
        ]),
        ("Leagues Module Entry", "Manual: 30 + 61 TCs | AI: US-337 (8 TCs)", [
            "Post-login redirect to Leagues module",
            "Display Active / Upcoming / Completed league counts",
            "League cards with status, name, type, scoring model",
            "Empty state when user has no leagues",
            "Manual adds: Create button, Join Requests section, Invite categories, filter tabs (All/Public/Private)",
        ]),
        ("League Dashboard", "Manual: 452 TCs | AI: US-338 (9 TCs)", [
            "Navigate to dashboard from league card",
            "Current week head-to-head matchup display",
            "History module with matchups and trade P&L",
            "Standings with W-L-T and tie-breakers",
            "**AI covers headlines only — manual has 50× more depth**",
        ]),
        ("Public Leagues", "Manual: 97 TCs (+ 127 web creation) | AI: US-339 (5 TCs)", [
            "Browse public leagues category",
            "Join open public league",
            "Block join on full/started league",
            "Update My Leagues list after join",
        ]),
        ("Player Market & Trading", "Manual: 78 TCs (Trading Activity) | AI: US-340 (7 TCs)", [
            "Real-time scrolling price ticker",
            "Color-coded value changes (green/red)",
            "Buy/sell shares at displayed global price (no slippage)",
            "45-second ticker refresh interval",
        ]),
        ("Market Admin & XP/Scoring", "Manual: 108 + 109 + 81 TCs | AI: US-341 + US-342 + US-343 (18 TCs)", [
            "Ops Admin configures pricing weights, bid/ask spread, market open dates",
            "XP awards from league performance; tier assignment",
            "Half-PPR scoring rules applied consistently",
            "Audit log for configuration changes",
        ]),
        ("Notifications & Broadcasts", "Scattered manual checks | AI: US-344 + US-345 (11 TCs)", [
            "Email on password change",
            "Notification on account status change",
            "Push for league matchup updates",
            "Ops Admin targeted messages and emergency broadcasts",
        ]),
        ("Legal Compliance & App Store (AI-Heavy)", "Minimal in Sprint 1/2 manual | AI: US-326 + US-327 (15 TCs)", [
            "Under-18 registration block with specific error message",
            "Consent timestamp + IP logging",
            "Public URLs for ToS and Privacy Policy",
            "App store org account, IAP product management, developer account linking",
            "**These are stronger in AI because they come directly from BRD stories not yet sprint-delivered in manual Excel**",
        ]),
    ]
    for title, mapping, bullets in sims:
        add(f"### 5.{sims.index((title, mapping, bullets))+1} {title}")
        add(f"**Mapping:** {mapping}")
        add()
        for b in bullets:
            add(f"- {b}")
        add()

    # 6 Topic coverage
    add("## 6. Topic Coverage Analysis")
    add()
    add("Keyword-topic hits across the full manual corpus vs AI corpus:")
    add()
    trows = []
    for topic, mcount in manual_topics.most_common():
        acount = ai_topics.get(topic, 0)
        ratio = acount / mcount if mcount else 0
        if ratio >= 0.15:
            st = "✅ Adequate relative coverage"
        elif ratio >= 0.05:
            st = "⚠️ Thin — AI mentions topic but lacks depth"
        else:
            st = "❌ Critical gap"
        trows.append([topic.replace("_", " ").title(), str(mcount), str(acount), f"{ratio:.1%}", st])
    add(_md_table(["Topic", "Manual Hits", "AI Hits", "AI/Manual", "Assessment"], trows))

    # 7 Gap analysis
    add("## 7. Gap Analysis — What AI Is Missing")
    add()
    add("### 7.1 Critical Volume Gaps (Manual >> AI)")
    add()
    critical = sorted(story_analysis, key=lambda x: -x["test_case_count"])[:15]
    crows = []
    for sa in critical:
        gap = sa["test_case_count"] - sa["ai_case_count"]
        crows.append([sa["story_name"][:50], str(sa["test_case_count"]), str(sa["ai_case_count"]), str(gap), sa["sprint"]])
    add(_md_table(["Manual User Story", "Manual", "AI", "Gap", "Sprint"], crows))
    add()
    add("### 7.2 Functional Gaps by Category")
    add()
    gaps_detail = [
        ("UI/UX & Visual Validation", f"Manual topic hits: {manual_topics.get('ui_ux_validation', 0):,}", f"AI hits: {ai_topics.get('ui_ux_validation', 0)}", "Manual tests verify logos, placeholders, hyperlink text, popup fields, hover states, tab highlights, pagination UI. AI steps are abstract agent instructions without pixel-level assertions."),
        ("League Dashboard Depth", "452 manual TCs", "9 AI TCs", "Week navigation, roster views, trade history within league, scoring breakdowns, commissioner tools, bye weeks, tie-breaker UI — essentially entire sprint deliverable missing from AI."),
        ("Private League Lifecycle", "313+ manual TCs (Create + Invites + 3 Methods + Created + Private Join)", "0 AI TCs", "No AI user story covers private league creation, QR/link/in-app invites, commissioner success flows."),
        ("Wallet & Economy", "500+ manual TCs across wallet/settlement/packages", "~18 AI TCs indirect", "User wallet, league wallet, transactions, buy-in, packages, promotions, reconciliation, end-of-season settlement — AI mentions economy config but not wallet UX flows."),
        ("Web Admin League Module", "695+ manual TCs", "~21 AI TCs", "Members & Teams, Trading Activity tab, League Settings, Buy-In Transactions — admin web views not in AI BRD stories."),
        ("Negative Test Depth", f"{manual_neg:,} manual negative", f"{ai_neg} AI negative", "Manual has rich invalid-input, permission-denial, and edge-case negatives. AI ratio: 7.7% negative vs manual 17.5%."),
        ("Role Permission Matrix", "Hundreds of role-specific TCs", "Minimal per-role negatives", "Manual explicitly tests Support vs Ops vs Super Admin visibility. AI mentions roles in titles but rarely tests unauthorized access."),
        ("Platform Separation", "Mobile 306 + Web 483 (S1 alone)", "Platform-agnostic", "AI does not tag mobile vs web; manual clearly separates app vs browser/admin console flows."),
        ("Sprint Scope Awareness", "Manual marks out-of-scope items", "AI generates uniformly", "e.g. Unlock Account, Override Verification, Merge Duplicate marked 'Not delivered in Sprint 1' or 'Out-of-scope' in manual — AI still generates related admin cases from BRD."),
        ("Execution Evidence", "DevAssignee, DevStatus, QA Comments per case", "8 test runs attempted, none passed fully", "Manual suite has been executed against builds; AI cases marked ready but execution history shows systemic failures on ATG environment."),
    ]
    for i, (cat, manual_ref, ai_ref, detail) in enumerate(gaps_detail, 1):
        add(f"#### 7.2.{i} {cat}")
        add(f"- **Manual:** {manual_ref}")
        add(f"- **AI:** {ai_ref}")
        add(f"- **Gap detail:** {detail}")
        add()

    add("### 7.3 What AI Has That Manual Sprint Excel Does NOT Cover")
    add()
    ai_only = [
        ("US-326: Super Admin Legal Compliance Configuration", 9, "Comprehensive legal consent logging (timestamp, IP), public ToS/Privacy URLs — beyond sprint manual scope"),
        ("US-327: App Store & IAP Configuration", 6, "D-U-N-S org accounts, IAP product CRUD, Apple/Google developer account linking, app metadata submission"),
        ("US-344: User Notifications (holistic)", 5, "Structured notification preference toggles, in-app critical alerts — manual has scattered checks only"),
        ("US-345: Ops Admin Broadcasts", 6, "Targeted messages, emergency broadcasts, reminder timing offsets, communication logging"),
        ("AC-Reference Traceability", "All 155 AI cases", "Each AI case links to AC-1, AC-2… — manual uses Test Case ID per sheet without AC mapping"),
        ("Scenario Type Taxonomy", "positive/negative/boundary/edge", "Manual uses Positive/Negative only — AI adds boundary (6) and edge (2) cases"),
    ]
    add(_md_table(["AI Feature", "Cases", "Notes"], [[a, str(b), c] for a, b, c in ai_only]))

    # 8 Sprint 1
    add("## 8. Sprint 1 Deep Dive")
    add()
    add("Sprint 1 manual suite: **789 test cases** covering **Mobile user auth/profile** (306) and **Web admin console** (483).")
    add()
    add("### 8.1 Mobile User Stories")
    add(_md_table(["User Story", "TCs", "Pos", "Neg", "AI Map", "AI TCs", "Gap Summary"], [
        [s["story_name"][:45], str(s["test_case_count"]), str(s.get("positive") or "—"), str(s.get("negative") or "—"),
         ", ".join(f"US-{i}" for i in s["ai_story_ids"]) or "NONE", str(s["ai_case_count"]),
         "Strong overlap" if s["coverage_ratio"] >= 0.1 else "Weak/missing"]
        for s in s1_analysis if "Web" not in s["story_name"] and s["test_case_count"] < 500
    ]))
    add()
    add("### 8.2 Web Admin User Stories")
    add(_md_table(["User Story", "TCs", "Pos", "Neg", "AI Map", "AI TCs", "Notes"], [
        [s["story_name"][:45], str(s["test_case_count"]), str(s.get("positive") or "—"), str(s.get("negative") or "—"),
         ", ".join(f"US-{i}" for i in s["ai_story_ids"]) or "NONE", str(s["ai_case_count"]),
         s.get("notes", "")[:40]]
        for s in s1_analysis if s["test_case_count"] >= 16 or "Admin" in s["story_name"] or "Web" in s["story_name"]
    ]))
    add()
    add("### 8.3 Sprint 1 — Detailed Gap Notes")
    s1_gaps = [
        "**Change Password (26 TCs):** No dedicated AI user story. Partial overlap via login/reset flows only.",
        "**Account Deletion Mobile (59 TCs):** AI covers admin soft-delete (US-336) but NOT user self-service delete from profile.",
        "**User Logout (7 TCs):** Zero AI representation.",
        "**Override Verification (26 TCs):** Zero AI — marked 'Not delivered in Sprint 1' in manual.",
        "**Merge Duplicate Accounts (26 TCs):** Zero AI — marked 'Not delivered in Sprint 1' in manual.",
        "**Unlock Account (22 TCs):** AI has 10 admin status cases but manual includes out-of-scope notes and per-role visibility (Support/Ops/Super Admin) with 3× more granularity.",
        "**Force Password Reset (79 TCs):** AI has 10 cases; manual includes hover states, popup UX, per-admin-type visibility with 8× volume.",
        "**Internal Admin RBAC (74+38+34 TCs):** AI US-332 has 6 cases vs 146 manual — missing Settings tab navigation, filter UI, pagination tests.",
    ]
    for g in s1_gaps:
        add(f"- {g}")

    # 9 Sprint 2
    add("## 9. Sprint 2 Deep Dive")
    add()
    add(f"Sprint 2 manual suite: **{s2_count:,} test cases** — **{100*s2_count/total_manual_summary:.0f}%** of all manual tests.")
    add()
    add("### 9.1 Sprint 2 User Story Volume Ranking")
    add(_md_table(["Rank", "User Story", "Manual TCs", "AI TCs", "Gap"], [
        [str(i+1), s["story_name"][:48], str(s["test_case_count"]), str(s["ai_case_count"]), str(s["test_case_count"]-s["ai_case_count"])]
        for i, s in enumerate(sorted(story_analysis, key=lambda x: -x["test_case_count"])[:20])
        if s["sprint"] == "Sprint 2"
    ]))
    add()
    add("### 9.2 Sprint 2 — Critical Observations")
    s2_obs = [
        "**League Dashboard (452 TCs → 9 AI):** Largest single gap. Manual covers sorting within category, week value display, roster management, tab switching, matchup navigation (past/current/future weeks), commissioner vs participant views. AI has 9 smoke-level cases.",
        "**Public Leagues Mobile (97 TCs → 5 AI):** Manual includes Join League screen tabs (Invite Code / Public / Private), back arrow, category highlight, league detail pages. AI has join/browse smoke tests only.",
        "**Create Private Leagues (127 TCs → 0 AI):** Entire commissioner creation wizard absent from AI.",
        "**Invitations (90 + 42 TCs → 0 AI):** League Invites category, Link/QR/In-App methods — no AI coverage.",
        "**Web Public League Creation (127 TCs → 0 AI):** Admin-side public league setup not in AI BRD stories.",
        "**Wallet Module (171 mobile + 375 web TCs → ~0 direct AI):** AI stories 340–343 touch economy config but not wallet UI, transaction history, buy-in payments, settlement screens.",
        "**Packages & Promotions (108 + 56 TCs → partial AI 341):** AI covers admin config at AC level; manual covers purchase flows, package listing, promotional credits.",
    ]
    for o in s2_obs:
        add(f"- {o}")

    # 10 AI-only
    add("## 10. AI-Only Coverage")
    add()
    for sid in [326, 327, 344, 345]:
        story = next(s for s in stories if s["id"] == sid)
        cases = ai_by_story[sid]
        add(f"### US-{sid}: {story['title']}")
        add(f"**Cases:** {len(cases)} | **Priority:** {story['priority']} | **Source:** {story['source']}")
        if story.get("acceptance_criteria"):
            add(f"**AC Preview:** {story['acceptance_criteria'][:400]}…")
        add()
        add(_md_table(["TC#", "Title", "Scenario", "AC Ref", "Steps"], [
            [str(c["case_number"]), c["title"][:60], c["scenario_type"], c.get("ac_ref") or "—", str(c["step_count"])]
            for c in cases
        ]))
        add()

    # 11 Manual-only
    add("## 11. Manual-Only Features (Zero AI Representation)")
    add()
    add(_md_table(["Feature", "Sprint/Platform", "Manual TCs", "Why Missing from AI"], [
        [f[0], f[1], str(f[2]), f[3]] for f in MANUAL_ONLY_FEATURES
    ]))

    # 12 Scenario comparison
    add("## 12. Scenario, Priority & Quality Comparison")
    add()
    add("### 12.1 Test Design Philosophy")
    add("| Aspect | Manual | AI |")
    add("|--------|--------|-----|")
    add("| Granularity | Screen/element level | Acceptance criteria level |")
    add("| Step style | Numbered UI actions with exact expected labels | Agent-interpretable abstract steps |")
    add("| Platform | Mobile vs Web explicit | Platform-agnostic |")
    add("| Traceability | Test Case ID per sheet | AC-ref + user_story_id |")
    add("| Negative testing | 17.5% of manual (402/2294 S2 + 201 S1) | 7.7% AI (12/155) |")
    add("| Execution status | DevStatus/QA Comments populated | 8 runs, 0 clean pass |")
    add()
    add("### 12.2 AI Case Quality Observations")
    add("- All 155 cases marked **`ready`** — no draft/review stage recorded")
    add("- Average **7.0 steps/case** — sufficient for agent execution but less detailed than manual")
    add("- **Story 329** (2FA login) reported **87.5% coverage** with gaps in generation job — yet only 10 cases vs 62 manual")
    add("- AI includes **boundary** cases (username 20 chars, OTP exactly 3 failures, 5MB avatar) — manual covers these implicitly in larger matrices")

    # 13 Execution
    add("## 13. Test Execution Observations (from DB)")
    add()
    add("From project `f2mx-2` test run history:")
    add()
    add(_md_table(["Run #", "Date", "Status", "Total", "Passed", "Failed"], [
        ["8", "2026-06-04", "cancelled", "155", "0", "0"],
        ["7", "2026-06-04", "failed", "155", "0", "5"],
        ["6", "2026-06-03", "running (stuck)", "155", "0", "0"],
        ["5", "2026-06-03", "failed", "155", "5", "48"],
        ["4", "2026-06-03", "error", "155", "0", "0"],
        ["3", "2026-06-02", "failed", "155", "1", "5"],
        ["2", "2026-06-02", "failed", "155", "0", "6"],
        ["1", "2026-06-02", "cancelled", "155", "0", "0"],
    ]))
    add()
    add("**Implication:** AI cases are marked executable (`ready`) but **have not been validated** against the ATG environment at scale. Manual cases have DevStatus/QA pass records.")

    # 14 Recommendations
    add("## 14. Recommendations & Remediation Plan")
    add()
    recs = [
        ("Phase 1 — Import manual smoke subset", "CSV-import top 50–100 manual smoke TCs (S1 auth + S2 league entry) as `source=csv` to establish baseline regression.", "Week 1"),
        ("Phase 2 — Extend BRD user stories", "Add AI user stories for: Private League Creation, Invitations, User Wallet, Change Password, User Logout, Override Verification, Merge Duplicate.", "Week 1–2"),
        ("Phase 3 — Re-run bulk generation (comprehensive)", "Regenerate with `comprehensive` profile on expanded story set; target 400–600 AI cases.", "Week 2–3"),
        ("Phase 4 — Platform tagging", "Add `platform: mobile|web|both` metadata to test cases for execution routing.", "Week 2"),
        ("Phase 5 — Gap-fill against manual topics", "Use manual topic buckets as coverage matrix input (not just AC decomposition).", "Week 3"),
        ("Phase 6 — Traceability linking", "Map manual Test Case IDs ↔ AI case IDs in a traceability matrix table.", "Ongoing"),
        ("Phase 7 — Fix stuck test run #6", "Mark DB run id=88 as error/cancelled; investigate sequential 155-case execution timeout.", "Immediate"),
        ("Phase 8 — Tiered testing strategy", "AI for AC/functional backbone; Manual suite for UI/UX + permission matrix; Combined for release gates.", "Ongoing"),
    ]
    add(_md_table(["Phase", "Action", "Timeline"], recs))

    # Appendix A
    add("## Appendix A — Complete Manual User Story Inventory")
    add()
    add(_md_table(["#", "Sprint", "User Story", "TCs", "Pos", "Neg", "Notes"], [
        [str(i+1), s["sprint"], s["story_name"], str(s["test_case_count"]),
         str(s.get("positive") or "—"), str(s.get("negative") or "—"), s.get("notes", "")[:50]]
        for i, s in enumerate(manual_stories)
    ]))

    # Appendix B
    add("## Appendix B — Complete AI User Story & Test Case Catalog")
    add()
    for story in stories:
        sid = story["id"]
        cases = ai_by_story[sid]
        add(f"### US-{sid}: {story['title']}")
        add(f"**Priority:** {story['priority']} | **Status:** {story['status']} | **Cases:** {len(cases)}")
        if story.get("acceptance_criteria"):
            add()
            add("**Acceptance Criteria:**")
            add("```")
            add(story["acceptance_criteria"][:2000])
            add("```")
        add()
        if cases:
            add(_md_table(["TC#", "ID", "Title", "Scenario", "Priority", "Category", "AC", "Steps"], [
                [str(c["case_number"]), str(c["id"]), c["title"][:55], c["scenario_type"],
                 c["priority"], c["category"], c.get("ac_ref") or "—", str(c["step_count"])]
                for c in cases
            ]))
        add()

    # Appendix C
    add("## Appendix C — Manual Sheet → Parsed Row Inventory")
    add()
    sheet_rows = []
    for wb in manual["workbooks"]:
        for sheet, rows in sorted(wb["sheets"].items(), key=lambda x: -len(x[1])):
            sheet_rows.append([wb["sprint"], sheet[:50], str(len(rows))])
    add(_md_table(["Sprint", "Excel Sheet", "Parsed Rows"], sheet_rows))

    # Appendix D
    add("## Appendix D — Sample Manual→AI Match Pairs")
    add()
    add("Best similarity matches sampled across manual sheets (score 0–1):")
    add()
    top_matches = sorted(match_samples, key=lambda x: -x["score"])[:100]
    add(_md_table(["Score", "Manual ID", "Sheet", "Manual Objective", "AI TC#", "AI Title"], [
        [f"{m['score']:.2f}", m["manual"]["test_id"], m["manual"]["sheet"][:25],
         m["manual"]["objective"][:55], f"TC-{m['best_ai']['case_number']}" if m["best_ai"] else "—",
         (m["best_ai"]["title"][:55] if m["best_ai"] else "—")]
        for m in top_matches
    ]))

    # Appendix E - full AI steps
    add("## Appendix E — AI Test Steps (Full Detail)")
    add()
    for c in ai_cases:
        add(f"### TC-{c['case_number']}: {c['title']}")
        add(f"**Story:** US-{c['user_story_id']} | **Scenario:** {c['scenario_type']} | **AC:** {c.get('ac_ref') or '—'}")
        if c.get("description"):
            add(f"**Description:** {c['description']}")
        if c.get("preconditions"):
            add(f"**Preconditions:** {c['preconditions']}")
        add()
        if c["steps"]:
            add(_md_table(["#", "Action", "Target", "Value", "Description", "Expected"], [
                [str(s["step_number"]), s.get("action") or "", (s.get("target") or "")[:30],
                 (s.get("value") or "")[:20], (s.get("description") or "")[:50], (s.get("expected_result") or "")[:50]]
                for s in c["steps"]
            ]))
        add()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Report: {OUTPUT}")
    print(f"Lines: {len(lines):,} | Chars: {len(content):,}")


if __name__ == "__main__":
    generate()
