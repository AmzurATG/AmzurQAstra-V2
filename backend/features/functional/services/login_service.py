"""
Login Service

Handles automated login to target applications before running integrity checks.

Login priority (credentials flow):
1. Try standard CSS selectors that match most login forms — no LLM needed.
2. If standard selectors miss, fall back to LLM-based form detection.

Also supports:
- Pre-saved sessions — restores encrypted Playwright storageState (Google OAuth)

The service does NOT manage browser lifecycle — it receives an already-started
BrowserRunner from the caller.
"""
import json
from typing import Optional, List, Tuple
from urllib.parse import urlparse

from features.functional.core.browser.base import BrowserRunner
from features.functional.core.llm_prompts.integrity_diagnosis import build_login_detection_prompt
from features.functional.core.captcha_detection import detect_captcha_signals
from common.llm.factory import get_llm_client
from common.llm.base import Message
from common.utils.logger import logger


# Standard selector candidates ordered by specificity.
# Each tuple: (css_selector, description)
_USERNAME_SELECTORS: List[Tuple[str, str]] = [
    ('input[autocomplete="username"]', "autocomplete=username"),
    ('input[autocomplete="email"]', "autocomplete=email"),
    ('input[name="email"]', "name=email"),
    ('input[name="username"]', "name=username"),
    ('input[name="user"]', "name=user"),
    ('input[name="login"]', "name=login"),
    ('input[id="email"]', "id=email"),
    ('input[id="username"]', "id=username"),
    ('input[type="email"]', "type=email"),
    ('input[placeholder*="email" i]', "placeholder~email"),
    ('input[placeholder*="user" i]', "placeholder~user"),
]

_PASSWORD_SELECTORS: List[Tuple[str, str]] = [
    ('input[type="password"]', "type=password"),
    ('input[name="password"]', "name=password"),
    ('input[id="password"]', "id=password"),
    ('input[autocomplete="current-password"]', "autocomplete=current-password"),
]

_SUBMIT_SELECTORS: List[Tuple[str, str]] = [
    ('button[type="submit"]', "button[type=submit]"),
    ('input[type="submit"]', "input[type=submit]"),
    ("button:has-text('Sign in')", "Sign in button"),
    ("button:has-text('Log in')", "Log in button"),
    ("button:has-text('Login')", "Login button"),
    ("button:has-text('Submit')", "Submit button"),
    ("button:has-text('Continue')", "Continue button"),
    ('form button', "first button in form"),
]

# Tabs/links that reveal a hidden email+password form (e.g. "Email & Password" tab
# next to a "Google Sign-In" tab). Clicked before probing username/password fields.
_EMAIL_TAB_SELECTORS: List[Tuple[str, str]] = [
    (":text('Email & Password')", "Email & Password tab"),
    (":text('Email and Password')", "Email and Password tab"),
    (":text('Sign in with email')", "Sign in with email link"),
    (":text('Use email instead')", "Use email instead link"),
    (":text('Sign in with password')", "Sign in with password link"),
    ("button:has-text('Email')", "Email button/tab"),
    ("a:has-text('Email')", "Email link/tab"),
    ("[role='tab']:has-text('Email')", "Email role=tab"),
    ("[role='tab']:has-text('Password')", "Password role=tab"),
]

# In-app "Sign in with Google" / SSO entry points (first visible wins).
_GOOGLE_SSO_SELECTORS: List[Tuple[str, str]] = [
    ("button:has-text('Continue with Google')", "Continue with Google"),
    ("button:has-text('Sign in with Google')", "Sign in with Google"),
    ("a:has-text('Sign in with Google')", "Sign in with Google link"),
    ("div[role='button']:has-text('Google')", "Google role=button"),
    ("[aria-label*='Google' i]", "aria-label Google"),
    ("button:has-text('Google')", "Google button"),
]


class LoginResult:
    """Outcome of a login attempt."""
    def __init__(self, success: bool, method: str, error: Optional[str] = None):
        self.success = success
        self.method = method    # 'credentials' | 'storage_state' | 'skipped'
        self.error = error


class LoginService:
    """
    Automates the login step for a given app URL.

    Usage:
        svc = LoginService()
        result = await svc.login(runner, app_url, username="u", password="p")
    """

    async def login(
        self,
        runner: BrowserRunner,
        app_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        storage_state: Optional[dict] = None,
        custom_selectors: Optional[dict] = None,
        login_url: Optional[str] = None,
        relax_captcha: bool = False,
    ) -> LoginResult:
        """
        Attempt to authenticate the browser session.

        Priority:
        1. storage_state — replay a saved OAuth/session (no form interaction)
        2. custom_selectors — user-provided CSS selectors (highest confidence)
        3. username + password — try standard selectors, then LLM fallback
        4. neither — skip login
        """
        if storage_state:
            return await self._restore_storage_state(runner, app_url, storage_state)

        if username and password:
            return await self._fill_login_form(
                runner, app_url, username, password, custom_selectors,
                login_url=login_url,
                relax_captcha=relax_captcha,
            )

        logger.info("[Login] No credentials provided — skipping login step")
        return LoginResult(success=True, method="skipped")

    async def google_sso_login_with_credentials(
        self,
        runner: BrowserRunner,
        app_url: str,
        username: str,
        password: str,
        login_url: Optional[str] = None,
        relax_captcha: bool = False,
    ) -> LoginResult:
        """
        Open the app (or login URL), click in-page Google SSO, then fill the Google account
        email/password on accounts.google.com. Requires Playwright tab switching
        (``focus_page_url_contains``). CAPTCHA may be handled by Steel when ``relax_captcha`` is True.
        """
        logger.info("[Login] Google SSO flow with supplied credentials…")
        start = (login_url or "").strip() or app_url
        nav = await runner.navigate(start)
        if not nav.success:
            return LoginResult(
                success=False,
                method="google_sso",
                error=nav.error or "Could not open start URL",
            )
        await runner.wait(2500)

        html_probe = await runner.get_page_html()
        cur = await runner.get_current_url()
        captcha = detect_captcha_signals(html_probe, cur or "")
        if captcha and not relax_captcha:
            return LoginResult(
                success=False,
                method="google_sso",
                error=(
                    "CAPTCHA detected before Google SSO. Use Steel with CAPTCHA solving, "
                    f"or a test build without CAPTCHA. ({captcha})"
                ),
            )
        if captcha and relax_captcha:
            logger.warning(
                "[Login] CAPTCHA-like signals before Google SSO (%s) — continuing (Steel may solve)",
                captcha,
            )

        sso_sel = await self._find_first_visible(runner, _GOOGLE_SSO_SELECTORS)
        if not sso_sel:
            return LoginResult(
                success=False,
                method="google_sso",
                error="No visible Google / SSO sign-in control on the page.",
            )

        cr = await runner.click(sso_sel)
        if not cr.success:
            return LoginResult(
                success=False,
                method="google_sso",
                error=f"Could not click Google SSO control: {cr.error}",
            )

        await runner.wait(2000)
        focused = await runner.focus_page_url_contains("accounts.google.com", timeout_ms=45_000)
        if not focused:
            return LoginResult(
                success=False,
                method="google_sso",
                error="Google sign-in page did not open (no accounts.google.com tab within 45s).",
            )

        email_sel = None
        for cand in ('#identifierId', 'input[name="identifier"]', 'input[type="email"]'):
            vis = await runner.assert_visible(cand)
            if vis.success:
                email_sel = cand
                break
        if not email_sel:
            return LoginResult(
                success=False,
                method="google_sso",
                error="Google email step did not appear (unexpected Google UI or blocked).",
            )

        fe = await runner.fill(email_sel, username)
        if not fe.success:
            return LoginResult(success=False, method="google_sso", error=f"Email field: {fe.error}")

        for next_sel in ('#identifierNext', 'button:has-text("Next")', 'button[type="button"]:has-text("Next")'):
            if await runner.is_visible(next_sel):
                ne = await runner.click(next_sel)
                if not ne.success:
                    return LoginResult(
                        success=False, method="google_sso",
                        error=f"Could not click Next after email: {ne.error}",
                    )
                break
        else:
            return LoginResult(
                success=False, method="google_sso",
                error="Could not find Next after entering email on Google.",
            )

        await runner.wait(2000)

        pwd_sel = None
        for _ in range(30):
            for cand in ('input[name="Passwd"]', 'input[type="password"]'):
                if await runner.is_visible(cand):
                    pwd_sel = cand
                    break
            if pwd_sel:
                break
            await runner.wait(1000)

        if not pwd_sel:
            cur2 = await runner.get_current_url()
            if "challenge" in cur2.lower() or "signin/v2/challenge" in cur2.lower():
                return LoginResult(
                    success=False,
                    method="google_sso",
                    error="Google requested extra verification (2FA / challenge). Complete manually or use an app password.",
                )
            return LoginResult(
                success=False,
                method="google_sso",
                error="Google password field did not appear in time.",
            )

        fp = await runner.fill(pwd_sel, password)
        if not fp.success:
            return LoginResult(success=False, method="google_sso", error=f"Password field: {fp.error}")

        await runner.wait(500)
        for pwd_next in ('#passwordNext', 'button:has-text("Next")'):
            if await runner.is_visible(pwd_next):
                pe = await runner.click(pwd_next)
                if not pe.success:
                    return LoginResult(
                        success=False, method="google_sso",
                        error=f"Could not submit Google password: {pe.error}",
                    )
                break

        await runner.wait(3000)
        if await runner.wait_for_post_oauth_app_page(app_url, timeout_ms=120_000):
            return LoginResult(success=True, method="google_sso")

        cur3 = await runner.get_current_url()
        if "accounts.google.com" in cur3.lower():
            return LoginResult(
                success=False,
                method="google_sso",
                error="Still on Google after password — check credentials, CAPTCHA, or 2FA.",
            )

        ok, err = await self._verify_credential_login_success(
            runner, start, extra_wait_ms=2000,
        )
        if ok:
            return LoginResult(success=True, method="google_sso")
        return LoginResult(
            success=False,
            method="google_sso",
            error=err or "Google SSO did not return to the application successfully.",
        )

    async def try_in_page_google_signin(
        self,
        runner: BrowserRunner,
        app_url: str,
    ) -> LoginResult:
        """
        After username/password fails, click a visible Google (or similar) SSO control
        so the user can continue in the visible browser. Does not complete OAuth alone.
        """
        logger.info("[Login] Looking for an in-page Google / SSO sign-in control…")
        sel = await self._find_first_visible(runner, _GOOGLE_SSO_SELECTORS)
        if not sel:
            logger.warning(
                "[Login] No visible Google/SSO control found — cannot switch to Google sign-in on this view."
            )
            return LoginResult(
                success=False,
                method="google_ui",
                error="No visible Google / SSO sign-in control on the page.",
            )

        url_before = await runner.get_current_url()
        logger.info(f"[Login] Clicking SSO control: {sel} (was on {url_before})")
        cr = await runner.click(sel)
        if not cr.success:
            return LoginResult(
                success=False, method="google_ui",
                error=f"Could not click SSO control: {cr.error}",
            )

        logger.info("[Login] SSO control clicked — allowing popup/redirect; scanning all tabs (up to 90s)…")
        await runner.wait(3000)

        if await runner.wait_for_post_oauth_app_page(app_url, timeout_ms=90_000):
            post = await runner.get_current_url()
            logger.info(f"[Login] Google/SSO completed — active tab URL: {post}")
            return LoginResult(success=True, method="google_ui")

        await runner.wait(2000)
        ok, err = await self._verify_credential_login_success(
            runner, url_before, extra_wait_ms=0,
        )
        if ok:
            post = await runner.get_current_url()
            logger.info(f"[Login] Google/SSO flow appears successful — URL now: {post}")
            return LoginResult(success=True, method="google_ui")

        cur = (await runner.get_current_url()).lower()
        if "accounts.google.com" in cur:
            return LoginResult(
                success=False,
                method="google_ui",
                error=(
                    "Google is still open in the focused tab — complete sign-in in any browser window. "
                    "The runner watches all tabs for up to 90s; if you finished late, re-run the check."
                ),
            )

        return LoginResult(
            success=False,
            method="google_ui",
            error=(
                err
                or "Google sign-in did not return to the application in time. "
                "Complete OAuth in the visible browser (all tabs are monitored), then re-run if needed."
            ),
        )

    # ------------------------------------------------------------------
    # Storage state restore (Google OAuth / saved session)
    # ------------------------------------------------------------------

    async def _restore_storage_state(
        self, runner: BrowserRunner, app_url: str, state: dict,
    ) -> LoginResult:
        logger.info("[Login] Restoring saved OAuth / storage session…")
        try:
            await runner.load_storage_state(state)
            nav = await runner.navigate(app_url)
            if not nav.success:
                return LoginResult(
                    success=False, method="storage_state",
                    error=nav.error or "Navigation after OAuth session failed",
                )
            await runner.wait(2000)
            post_url = await runner.get_current_url()
            html_probe = await runner.get_page_html()
            captcha = detect_captcha_signals(html_probe, post_url or "")
            if captcha:
                return LoginResult(
                    success=False, method="storage_state",
                    error=(
                        "CAPTCHA detected after OAuth session. Use a staging build without CAPTCHA "
                        f"or test keys. ({captcha})"
                    ),
                )
            logger.info(f"[Login] Storage state restored — post-reload URL: {post_url}")
            return LoginResult(success=True, method="storage_state")
        except Exception as e:
            logger.error(f"[Login] Storage state restore failed: {e}")
            return LoginResult(success=False, method="storage_state", error=str(e))

    # ------------------------------------------------------------------
    # Credential-based login (standard selectors → LLM fallback)
    # ------------------------------------------------------------------

    async def _fill_login_form(
        self,
        runner: BrowserRunner,
        app_url: str,
        username: str,
        password: str,
        custom_selectors: Optional[dict] = None,
        login_url: Optional[str] = None,
        relax_captcha: bool = False,
    ) -> LoginResult:
        logger.info("[Login] Starting username/password form flow…")
        if login_url:
            nav = await runner.navigate(login_url)
            if not nav.success:
                return LoginResult(
                    success=False, method="credentials",
                    error=f"Could not open login URL: {nav.error}",
                )
            await runner.wait(2000)

        html_probe = await runner.get_page_html()
        cur = await runner.get_current_url()
        captcha = detect_captcha_signals(html_probe, cur or "")
        if captcha and not relax_captcha:
            return LoginResult(
                success=False, method="credentials",
                error=(
                    "CAPTCHA detected on the login page. Integrity checks require a staging/test "
                    f"build without CAPTCHA or with test keys. ({captcha})"
                ),
            )
        if captcha and relax_captcha:
            logger.warning(
                "[Login] CAPTCHA-like signals on login page (%s) — continuing (Steel CAPTCHA solve may apply)",
                captcha,
            )

        # --- Attempt 0: user-provided custom selectors ---
        if custom_selectors:
            logger.info("[Login] Trying user-provided custom selectors")
            result = await self._apply_selectors(
                runner, username, password,
                custom_selectors.get("username_selector"),
                custom_selectors.get("password_selector"),
                custom_selectors.get("submit_selector"),
            )
            if result.success:
                return result
            logger.info(f"[Login] Custom selectors failed ({result.error}), trying standard…")

        # --- Attempt 1: standard CSS selectors ---
        std_result = await self._try_standard_selectors(runner, username, password)
        if std_result and std_result.success:
            return std_result

        if std_result:
            logger.info(f"[Login] Standard selectors failed ({std_result.error}), trying LLM…")
        else:
            logger.info("[Login] No standard selectors matched, trying LLM…")

        # --- Attempt 2: LLM-detected selectors ---
        return await self._try_llm_selectors(runner, app_url, username, password)

    async def _try_standard_selectors(
        self,
        runner: BrowserRunner,
        username: str,
        password: str,
    ) -> Optional[LoginResult]:
        """Try well-known CSS selectors — fast, no LLM call needed."""
        username_sel = await self._find_first_visible(runner, _USERNAME_SELECTORS)
        password_sel = await self._find_first_visible(runner, _PASSWORD_SELECTORS)

        # If no fields visible, look for a tab/link that reveals the email form
        if not username_sel and not password_sel:
            tab_clicked = await self._try_reveal_email_form(runner)
            if tab_clicked:
                username_sel = await self._find_first_visible(runner, _USERNAME_SELECTORS)
                password_sel = await self._find_first_visible(runner, _PASSWORD_SELECTORS)

        if not username_sel and not password_sel:
            return None

        submit_sel = await self._find_first_visible(runner, _SUBMIT_SELECTORS)

        logger.info(
            f"[Login] Standard selectors — user: {username_sel} "
            f"pass: {password_sel} submit: {submit_sel}"
        )

        return await self._apply_selectors(
            runner, username, password, username_sel, password_sel, submit_sel,
        )

    async def _try_reveal_email_form(self, runner: BrowserRunner) -> bool:
        """Click a tab or link that switches from SSO to email+password login."""
        tab_sel = await self._find_first_visible(runner, _EMAIL_TAB_SELECTORS)
        if not tab_sel:
            return False
        try:
            result = await runner.click(tab_sel)
            if result.success:
                logger.info(f"[Login] Clicked email/password tab: {tab_sel}")
                await runner.wait(1000)
                return True
        except Exception:
            pass
        return False

    async def _try_llm_selectors(
        self,
        runner: BrowserRunner,
        app_url: str,
        username: str,
        password: str,
    ) -> LoginResult:
        """Fall back to LLM-based form detection."""
        try:
            current_url = await runner.get_current_url()
            html = await runner.get_page_html()

            selectors = await self._detect_login_form_llm(current_url or app_url, html)
            if not selectors:
                return LoginResult(
                    success=False, method="credentials",
                    error="Could not identify login form (standard selectors + LLM both failed)",
                )

            username_sel = selectors.get("username_selector")
            password_sel = selectors.get("password_selector")
            submit_sel   = selectors.get("submit_selector")

            if not username_sel and not password_sel:
                return LoginResult(
                    success=False, method="credentials",
                    error="LLM returned empty selectors — page may not have a login form",
                )

            logger.info(
                f"[Login] LLM selectors — user: {username_sel} "
                f"pass: {password_sel} submit: {submit_sel}"
            )

            return await self._apply_selectors(
                runner, username, password, username_sel, password_sel, submit_sel,
            )

        except Exception as e:
            logger.error(f"[Login] LLM form fill error: {e}")
            return LoginResult(success=False, method="credentials", error=str(e))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _verify_credential_login_success(
        runner: BrowserRunner,
        url_before_submit: str,
        extra_wait_ms: int = 2500,
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect failed logins where the form submits but the app stays on the login page.
        """
        if extra_wait_ms > 0:
            await runner.wait(extra_wait_ms)
        post_url = await runner.get_current_url()
        try:
            path_before = urlparse(url_before_submit).path.rstrip("/").lower() or "/"
            path_after = urlparse(post_url).path.rstrip("/").lower() or "/"
        except Exception:
            path_before = path_after = ""

        pwd_visible = await runner.is_visible('input[type="password"]')
        url_l = post_url.lower()
        login_like_path = any(
            seg in url_l for seg in ("/login", "/signin", "/sign-in", "/auth/login")
        )

        if login_like_path and pwd_visible:
            return False, (
                "Still on a login URL with a visible password field — credentials were not accepted."
            )

        if post_url == url_before_submit and pwd_visible:
            return False, "Login form still visible after submit — credentials may be wrong."

        if login_like_path and path_before == path_after and pwd_visible:
            return False, "No navigation away from login after submit — authentication likely failed."

        logger.info(f"[Login] Post-submit check passed — current URL: {post_url}")
        return True, None

    @staticmethod
    async def _apply_selectors(
        runner: BrowserRunner,
        username: str,
        password: str,
        username_sel: Optional[str],
        password_sel: Optional[str],
        submit_sel: Optional[str],
    ) -> LoginResult:
        """Fill a login form using explicit selectors."""
        try:
            url_before = await runner.get_current_url()
            if username_sel:
                result = await runner.fill(username_sel, username)
                if not result.success:
                    return LoginResult(
                        success=False, method="credentials",
                        error=f"Could not fill username ({username_sel}): {result.error}",
                    )

            if password_sel:
                result = await runner.fill(password_sel, password)
                if not result.success:
                    return LoginResult(
                        success=False, method="credentials",
                        error=f"Could not fill password ({password_sel}): {result.error}",
                    )

            if submit_sel:
                result = await runner.click(submit_sel)
                if not result.success:
                    return LoginResult(
                        success=False, method="credentials",
                        error=f"Could not click submit ({submit_sel}): {result.error}",
                    )

            ok, v_err = await LoginService._verify_credential_login_success(runner, url_before)
            post_url = await runner.get_current_url()
            logger.info(f"[Login] Post-login URL: {post_url}")
            if not ok:
                return LoginResult(success=False, method="credentials", error=v_err)
            return LoginResult(success=True, method="credentials")
        except Exception as e:
            return LoginResult(success=False, method="credentials", error=str(e))

    @staticmethod
    async def _find_first_visible(
        runner: BrowserRunner,
        candidates: List[Tuple[str, str]],
    ) -> Optional[str]:
        """Return the first selector whose element is visible on the page (instant, no wait)."""
        for selector, desc in candidates:
            try:
                if await runner.is_visible(selector):
                    return selector
            except Exception:
                continue
        return None

    async def _detect_login_form_llm(self, url: str, html: str) -> Optional[dict]:
        """Ask the LLM to identify login form selectors from page HTML."""
        providers = [None, "gemini"]
        for provider in providers:
            try:
                system_prompt, user_prompt = build_login_detection_prompt(url, html)
                llm = get_llm_client(provider=provider)
                response = await llm.chat(
                    messages=[
                        Message(role="system", content=system_prompt),
                        Message(role="user", content=user_prompt),
                    ],
                    temperature=0.1,
                    max_tokens=300,
                )
                raw = response.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                return json.loads(raw)
            except Exception as e:
                label = provider or "default"
                logger.warning(f"[Login] LLM form detection failed ({label}): {e}")
                continue
        return None
