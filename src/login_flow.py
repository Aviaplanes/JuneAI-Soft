"""
Автологин через state machine с Enum.
Порядок: Sign in → Email → Continue → Code → Checkbox → Continue → Verify
"""

import asyncio
import json
from enum import Enum, auto
from pathlib import Path
from datetime import datetime, timezone  # ← Добавлено

from playwright.async_api import Page
from rich.console import Console

from autologin import (
    input_email_only,
    click_continue_button,
    click_checkbox,
    set_login_false,
    set_login_true,
)
from grind import type, wait
from imap import get_code

console = Console()


class AuthStatus(Enum):
    ALREADY_LOGGED = auto()
    NEED_LOGIN = auto()
    UNKNOWN = auto()


class LoginState(Enum):
    CLICK_SIGN_IN = auto()
    INPUT_EMAIL = auto()
    CLICK_CONTINUE_EMAIL = auto()
    WAIT_CODE_FIELD = auto()
    FETCH_AND_INPUT_CODE = auto()
    CLICK_CHECKBOX = auto()
    CLICK_CONTINUE_CODE = auto()
    VERIFY_LOGIN = auto()
    DONE = auto()
    FAILED = auto()


class LoginResult(Enum):
    ALREADY_LOGGED_IN = auto()
    LOGIN_SUCCESS = auto()
    LOGIN_FAILED = auto()
    PAGE_CLOSED = auto()


def _get_imap_password(email: str) -> str | None:
    path = Path("profiles.json")
    if not path.exists():
        return None
    try:
        profiles = json.loads(path.read_text(encoding="utf-8"))
        profile = next((p for p in profiles if p.get("email") == email), None)
        if profile:
            return profile.get("imapPassword")
    except Exception:
        pass
    return None


async def check_auth(page: Page, timeout: int = 15000) -> AuthStatus:
    points_task = asyncio.create_task(
        page.wait_for_selector("span.tabular-nums", state="visible", timeout=timeout)
    )
    signin_task = asyncio.create_task(
        page.wait_for_selector(
            'button:has-text("Sign in")', state="visible", timeout=timeout
        )
    )

    done, pending = await asyncio.wait(
        [points_task, signin_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    for task in done:
        try:
            element = task.result()
            if not element:
                continue
            text = await element.text_content() or ""
            if "Sign in" in text:
                return AuthStatus.NEED_LOGIN
            else:
                return AuthStatus.ALREADY_LOGGED
        except Exception:
            continue

    return AuthStatus.UNKNOWN


async def run_login_flow(
    page: Page,
    email: str,
    log_style: str = "#404040",
    warn_style: str = "#b84c44",
) -> LoginResult:
    """
    State machine автологина.
    """

    if page.is_closed():
        return LoginResult.PAGE_CLOSED

    auth = await check_auth(page)

    if auth == AuthStatus.ALREADY_LOGGED:
        try:
            points = await page.inner_text("span.tabular-nums")
            console.print(
                f"{email} | Already logged in, points: {points}", style=log_style
            )
        except Exception:
            console.print(f"{email} | Already logged in", style=log_style)
        set_login_true(email)
        return LoginResult.ALREADY_LOGGED_IN

    if auth == AuthStatus.UNKNOWN:
        console.print(f"{email} | Cannot determine auth state", style=warn_style)
        return LoginResult.LOGIN_FAILED

    set_login_false(email)
    state = LoginState.CLICK_SIGN_IN

    # ══════════════════════════════════════════════
    # Время нажатия Continue (для фильтрации писем)
    # ══════════════════════════════════════════════
    code_request_time: datetime | None = None

    while state not in (LoginState.DONE, LoginState.FAILED):
        if page.is_closed():
            return LoginResult.PAGE_CLOSED

        match state:

            # ── 1. Нажать Sign in ──
            case LoginState.CLICK_SIGN_IN:
                console.print(f"{email} | Clicking Sign in...", style=log_style)
                try:
                    btn = await page.wait_for_selector(
                        'button:has-text("Sign in")', timeout=10000
                    )
                    if btn:
                        await btn.click()
                        await wait(1, 2)
                        state = LoginState.INPUT_EMAIL
                    else:
                        state = LoginState.FAILED
                except Exception as e:
                    console.print(f"{email} | Sign in error: {e}", style=warn_style)
                    state = LoginState.FAILED

            # ── 2. ТОЛЬКО ввести email ──
            case LoginState.INPUT_EMAIL:
                console.print(f"{email} | Entering email...", style=log_style)
                try:
                    success = await input_email_only(page, email)
                    if success:
                        await wait(0.5, 1)
                        state = LoginState.CLICK_CONTINUE_EMAIL
                    else:
                        console.print(
                            f"{email} | Failed to input email", style=warn_style
                        )
                        state = LoginState.FAILED
                except Exception as e:
                    console.print(f"{email} | Email input error: {e}", style=warn_style)
                    state = LoginState.FAILED

            # ── 3. Нажать Continue после email ──
            case LoginState.CLICK_CONTINUE_EMAIL:
                console.print(f"{email} | Clicking Continue...", style=log_style)

                # ═══════════════════════════════════════════════════════
                # ЗАПОМИНАЕМ ВРЕМЯ перед нажатием Continue!
                # Все письма СТАРШЕ этого времени будут игнорироваться
                # ═══════════════════════════════════════════════════════
                code_request_time = datetime.now(timezone.utc)
                console.print(
                    f"{email} | Code request time: {code_request_time.strftime('%H:%M:%S')} UTC",
                    style=log_style,
                )

                try:
                    success = await click_continue_button(page)
                    if not success:
                        await page.keyboard.press("Enter")
                    await wait(2, 3)
                    state = LoginState.WAIT_CODE_FIELD
                except Exception:
                    await page.keyboard.press("Enter")
                    await wait(2, 3)
                    state = LoginState.WAIT_CODE_FIELD

            # ── 4. Ждать поле кода ──
            case LoginState.WAIT_CODE_FIELD:
                console.print(f"{email} | Waiting for code field...", style=log_style)
                try:
                    await page.wait_for_selector(
                        'input[aria-label="Verification code"]', timeout=30000
                    )
                    state = LoginState.FETCH_AND_INPUT_CODE
                except Exception:
                    console.print(f"{email} | Code field not found", style=warn_style)
                    state = LoginState.FAILED

            # ── 5. Получить код через IMAP и ввести ──
            case LoginState.FETCH_AND_INPUT_CODE:
                console.print(
                    f"{email} | Waiting for verification code...", style=log_style
                )

                imap_pass = _get_imap_password(email)
                if not imap_pass:
                    console.print(f"{email} | IMAP not configured", style=warn_style)
                    state = LoginState.FAILED
                    continue

                code = None
                max_attempts = 30
                check_interval = 2

                for attempt_num in range(max_attempts):
                    if page.is_closed():
                        return LoginResult.PAGE_CLOSED

                    try:
                        # ═══════════════════════════════════════════════════════
                        # ПЕРЕДАЁМ sent_after — ищем только новые письма!
                        # ═══════════════════════════════════════════════════════
                        code = get_code(email, sent_after=code_request_time)

                        if code:
                            elapsed = attempt_num * check_interval
                            console.print(
                                f"{email} | ✅ Code received after {elapsed}s: {code}",
                                style=log_style,
                            )
                            break
                    except Exception as e:
                        if attempt_num == 0:
                            console.print(
                                f"{email} | IMAP check error: {e}",
                                style=warn_style,
                            )

                    if attempt_num > 0 and attempt_num % 5 == 0:
                        elapsed = attempt_num * check_interval
                        console.print(
                            f"{email} | Still waiting for NEW code... ({elapsed}s)",
                            style=log_style,
                        )

                    await asyncio.sleep(check_interval)

                if not code:
                    console.print(
                        f"{email} | Code not received after 60s",
                        style=warn_style,
                    )
                    state = LoginState.FAILED
                    continue

                console.print(f"{email} | Entering code...", style=log_style)
                await type(page, code)
                await wait(0.5, 1)
                state = LoginState.CLICK_CHECKBOX

            # ── 6. Нажать checkbox ──
            case LoginState.CLICK_CHECKBOX:
                console.print(f"{email} | Waiting for checkbox...", style=log_style)
                clicked = False

                for _ in range(120):
                    if page.is_closed():
                        return LoginResult.PAGE_CLOSED

                    clicked = await click_checkbox(page)
                    if clicked:
                        console.print(f"{email} | Checkbox clicked", style=log_style)
                        await wait(1, 2)
                        break

                    await asyncio.sleep(0.5)

                if clicked:
                    state = LoginState.CLICK_CONTINUE_CODE
                else:
                    console.print(f"{email} | Checkbox not found", style=warn_style)
                    state = LoginState.FAILED

            # ── 7. Нажать Continue после кода ──
            case LoginState.CLICK_CONTINUE_CODE:
                console.print(f"{email} | Clicking Submit...", style=log_style)
                try:
                    success = await click_continue_button(page)
                    if not success:
                        await page.keyboard.press("Enter")
                except Exception:
                    await page.keyboard.press("Enter")
                await wait(2, 3)
                state = LoginState.VERIFY_LOGIN

            # ── 8. Проверить вход ──
            case LoginState.VERIFY_LOGIN:
                console.print(f"{email} | Verifying login...", style=log_style)
                try:
                    await page.wait_for_selector(
                        "span.tabular-nums", state="visible", timeout=30000
                    )
                    points = await page.inner_text("span.tabular-nums")
                    console.print(
                        f"{email} | ✅ Login OK, points: {points}", style=log_style
                    )
                    set_login_true(email)
                    state = LoginState.DONE
                except Exception:
                    console.print(
                        f"{email} | Login verification failed", style=warn_style
                    )
                    state = LoginState.FAILED

    if state == LoginState.DONE:
        return LoginResult.LOGIN_SUCCESS
    return LoginResult.LOGIN_FAILED
