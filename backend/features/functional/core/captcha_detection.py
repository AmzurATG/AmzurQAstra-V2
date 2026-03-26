"""
Heuristic CAPTCHA detection for integrity-check runs.

Policy: staging/test builds should disable CAPTCHA or use test keys.
We do not automate solving production CAPTCHAs.
"""
import re
from typing import Optional

_CAPTCHA_MARKERS = [
    r"google\.com/recaptcha",
    r"grecaptcha",
    r"recaptcha/api\.js",
    r"hcaptcha\.com",
    r"h-captcha",
    r"challenges\.cloudflare\.com",
    r"turnstile",
    r"cf-turnstile",
    r"arkoselabs\.com",
    r"funcaptcha",
]


def detect_captcha_signals(html: str, url: str = "") -> Optional[str]:
    """
    Return a short reason string if CAPTCHA-like content is detected, else None.
    """
    if not html and not url:
        return None
    combined = f"{url}\n{html}".lower()
    for pattern in _CAPTCHA_MARKERS:
        if re.search(pattern, combined, re.I):
            return f"CAPTCHA marker matched: {pattern}"
    if re.search(r"\bcaptcha\b", combined) and (
        "iframe" in combined or "challenge" in combined
    ):
        return "Page appears to contain a CAPTCHA challenge"
    return None
