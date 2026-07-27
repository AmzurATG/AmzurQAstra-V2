"""Screenshot evidence agent — keep the right shots, drop agent-frame spam.

Captures during browser-use can produce dozens of near-duplicate frames per
case (especially on long failures). This agent curates a small evidence set
for the UI / PDF while leaving enough proof for accuracy gates.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from config import settings


def _max_evidence(overall: Optional[str]) -> int:
    status = (overall or "").lower()
    if status in ("failed", "error"):
        return int(getattr(settings, "SCREENSHOT_EVIDENCE_MAX_FAIL", 8) or 8)
    return int(getattr(settings, "SCREENSHOT_EVIDENCE_MAX_PASS", 6) or 6)


def _raw_cap() -> int:
    return int(getattr(settings, "SCREENSHOT_RAW_CAP", 24) or 24)


def should_capture_agent_frame(
    *,
    current_count: int,
    agent_step: int,
    force: bool = False,
) -> bool:
    """Throttle mid-run captures so a single case cannot explode disk/UI."""
    if force:
        return True
    cap = _raw_cap()
    if current_count >= cap:
        return False
    every_n = max(1, int(getattr(settings, "SCREENSHOT_CAPTURE_EVERY_N", 1) or 1))
    if every_n <= 1:
        return True
    # Always keep early frames + every Nth thereafter.
    if agent_step <= 2:
        return True
    return agent_step % every_n == 0


def _indexed_shots(
    agent_logs: Sequence[Dict[str, Any]],
    screenshots: Optional[Sequence[str]] = None,
) -> List[Tuple[int, str, Dict[str, Any]]]:
    """Return (list_index, path, log_entry) for entries with screenshots."""
    out: List[Tuple[int, str, Dict[str, Any]]] = []
    seen: set[str] = set()
    for i, entry in enumerate(agent_logs or []):
        if not isinstance(entry, dict):
            continue
        path = entry.get("screenshot_path")
        if not path or str(path) in seen:
            continue
        seen.add(str(path))
        out.append((i, str(path), entry))
    for path in screenshots or []:
        if path and str(path) not in seen:
            seen.add(str(path))
            out.append((-1, str(path), {"screenshot_path": path, "description": "Case screenshot"}))
    return out


def pick_evidence_indices(n: int, max_keep: int) -> List[int]:
    """Pick evenly spaced indices always including first and last."""
    if n <= 0:
        return []
    if n <= max_keep:
        return list(range(n))
    if max_keep == 1:
        return [n - 1]
    # first, last, and evenly spaced middles
    keep = {0, n - 1}
    middles = max_keep - 2
    for j in range(1, middles + 1):
        idx = round(j * (n - 1) / (middles + 1))
        keep.add(min(n - 1, max(0, idx)))
    # If collisions left us short, fill from the end
    ordered = sorted(keep)
    k = 0
    while len(ordered) < max_keep and k < n:
        if k not in keep:
            keep.add(k)
            ordered = sorted(keep)
        k += 1
    return ordered[:max_keep]


class ScreenshotAgent:
    """Curate agent-frame screenshots into a stable evidence set."""

    @staticmethod
    def curate(
        agent_logs: Optional[Sequence[Dict[str, Any]]] = None,
        screenshots: Optional[Sequence[str]] = None,
        *,
        overall: Optional[str] = None,
        max_evidence: Optional[int] = None,
    ) -> Dict[str, Any]:
        logs = [dict(e) for e in (agent_logs or []) if isinstance(e, dict)]
        shots = list(screenshots or [])
        indexed = _indexed_shots(logs, shots)
        limit = max(1, int(max_evidence if max_evidence is not None else _max_evidence(overall)))
        pick = pick_evidence_indices(len(indexed), limit)
        evidence_paths: List[str] = []
        evidence_set: set[str] = set()
        for pi in pick:
            _, path, _ = indexed[pi]
            if path not in evidence_set:
                evidence_set.add(path)
                evidence_paths.append(path)

        # Tag logs: evidence True for kept paths; clear non-evidence paths from UI payload
        curated_logs: List[Dict[str, Any]] = []
        for entry in logs:
            e = dict(entry)
            path = e.get("screenshot_path")
            if path and str(path) in evidence_set:
                e["evidence"] = True
            elif path:
                e["evidence"] = False
                # Keep path in raw_screenshot_path for ops; UI uses evidence only
                e["raw_screenshot_path"] = path
                e["screenshot_path"] = None
            else:
                e.setdefault("evidence", False)
            curated_logs.append(e)

        # Prefer last evidence as primary
        primary = evidence_paths[-1] if evidence_paths else (shots[-1] if shots else None)
        return {
            "agent_logs": curated_logs,
            "evidence_screenshots": evidence_paths,
            "evidence_screenshot_count": len(evidence_paths),
            "raw_screenshot_count": len(indexed),
            "screenshot_path": primary,
            "screenshots": evidence_paths or shots[:limit],
        }

    @staticmethod
    def apply_to_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate a runner/case result dict in place with curated evidence."""
        curated = ScreenshotAgent.curate(
            result.get("logs") or result.get("agent_logs"),
            result.get("screenshots"),
            overall=result.get("overall") or result.get("status"),
        )
        if "logs" in result:
            result["logs"] = curated["agent_logs"]
        if "agent_logs" in result:
            result["agent_logs"] = curated["agent_logs"]
        result["screenshots"] = curated["screenshots"]
        result["screenshot_path"] = curated["screenshot_path"]
        result["evidence_screenshots"] = curated["evidence_screenshots"]
        result["evidence_screenshot_count"] = curated["evidence_screenshot_count"]
        result["raw_screenshot_count"] = curated["raw_screenshot_count"]
        return result
