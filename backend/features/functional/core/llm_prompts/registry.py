"""Prompt registry — versioned prompt templates for reproducibility + A/B.

Every prompt used to drive the LLM is registered here under a name + version.
The runner resolves the active version from settings (PROMPT_*_VERSION), stamps
the resolved version onto each run/result, and logs it — so a prompt change is
traceable and instantly revertible (just point the setting at the old version).

Adding a new version:
  1. Add a new template string below.
  2. Register it under the same name with a new version id.
  3. Bump the corresponding PROMPT_*_VERSION setting to roll it out.
The previous version stays available for rollback / comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from config import settings
from common.utils.logger import logger

# v3 == the current production template. Kept as the single source of truth in
# test_execution.py so existing imports keep working; registered here for
# versioning/traceability.
from features.functional.core.llm_prompts.test_execution import (
    TEST_EXECUTION_PROMPT as _TEST_EXECUTION_V3,
)
from features.functional.core.llm_prompts.ui_validation import (
    UI_VALIDATION_SYSTEM_V1 as _UI_VALIDATION_V1,
)


@dataclass(frozen=True)
class PromptEntry:
    name: str
    version: str
    template: str


# name -> {version -> PromptEntry}
_REGISTRY: Dict[str, Dict[str, PromptEntry]] = {}


def register(name: str, version: str, template: str) -> None:
    _REGISTRY.setdefault(name, {})[version] = PromptEntry(name, version, template)


register("test_execution", "v3", _TEST_EXECUTION_V3)
register("ui_validation", "v1", _UI_VALIDATION_V1)


def _active_version(name: str) -> str:
    mapping = {
        "test_execution": getattr(settings, "PROMPT_TEST_EXECUTION_VERSION", "v3") or "v3",
        "ui_validation": getattr(settings, "PROMPT_UI_VALIDATION_VERSION", "v1") or "v1",
    }
    return mapping.get(name, "v3")


def get_prompt(name: str, version: str | None = None) -> Tuple[str, str]:
    """Return (resolved_version, template).

    Falls back to the newest registered version if the requested one is missing,
    logging a warning so misconfiguration is visible rather than silent.
    """
    versions = _REGISTRY.get(name)
    if not versions:
        raise KeyError(f"No prompt registered under name={name!r}")
    want = version or _active_version(name)
    entry = versions.get(want)
    if entry is None:
        newest = sorted(versions.keys())[-1]
        logger.warning(
            "[PromptRegistry] version %r for %r not found; falling back to %r",
            want, name, newest,
        )
        entry = versions[newest]
    return entry.version, entry.template


def list_versions(name: str) -> list[str]:
    return sorted(_REGISTRY.get(name, {}).keys())
