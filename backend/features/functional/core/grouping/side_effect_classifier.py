"""Side-effect classification for safe sub-grouping."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class SideEffectClass(str, Enum):
    READ_ONLY = "read_only"
    MUTATING = "mutating"
    DESTRUCTIVE = "destructive"
    AUTH = "auth"


_DESTRUCTIVE = ("delete", "ban", "remove account", "hard delete", "purge")
_MUTATING = (
    "unlock", "lock", "suspend", "freeze", "force password", "password reset",
    "merge duplicate", "change role", "deactivate", "create ", "edit ", "update ",
)
_AUTH = ("login", "log in", "signin", "logout", "forgot password")
_READONLY = ("verify the data", "verify display", "verify pagination", "verify search", "verify filter", "verify column")


def _hay(case: Dict[str, Any]) -> str:
    parts = [str(case.get("title") or ""), str(case.get("description") or "")]
    for s in case.get("steps") or []:
        if isinstance(s, dict):
            parts.append(str(s.get("description") or ""))
    return " ".join(parts).lower()


def classify_side_effect(case: Dict[str, Any]) -> SideEffectClass:
    hay = _hay(case)
    if any(k in hay for k in _DESTRUCTIVE):
        return SideEffectClass.DESTRUCTIVE
    title = str(case.get("title") or "").lower()
    if any(k in title for k in ("login", "logout", "forgot password")):
        return SideEffectClass.AUTH
    if any(k in hay for k in _MUTATING):
        return SideEffectClass.MUTATING
    if any(k in hay for k in _READONLY):
        return SideEffectClass.READ_ONLY
    return SideEffectClass.MUTATING


def classify_role_facet(case: Dict[str, Any]) -> Optional[str]:
    hay = _hay(case)
    if "super admin" in hay:
        return "Super Admin"
    if "ops admin" in hay:
        return "Ops Admin"
    if "support" in hay:
        return "Support"
    return None


def facet_label(side: SideEffectClass, role: Optional[str], chunk_idx: int) -> str:
    base = {
        SideEffectClass.READ_ONLY: "Visibility",
        SideEffectClass.MUTATING: "Actions",
        SideEffectClass.DESTRUCTIVE: "Destructive",
        SideEffectClass.AUTH: "Auth",
    }[side]
    if role:
        base = f"{base} · {role}"
    if chunk_idx > 0:
        base = f"{base} ({chunk_idx + 1})"
    return base


def max_cases_for(side: SideEffectClass) -> int:
    from config import settings
    if side == SideEffectClass.READ_ONLY:
        return int(getattr(settings, "SUBGROUP_MAX_CASES_READONLY", 12) or 12)
    return int(getattr(settings, "SUBGROUP_MAX_CASES_MUTATING", 8) or 8)
