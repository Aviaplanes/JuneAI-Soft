"""
This file contains the logic for launching profiles, configuring their startup, and reading points
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext
from rich.color import Color, ColorParseError
from rich.console import Console

import config
from autologin import (
    human_click_if_exists,
    input_mail,
    set_login_false,
    set_login_true,
)
from grind import dismiss_tour_overlay, key_press, main, type, wait
from imap import get_code

console = Console()

# Gradient settings
color1 = "#f40752"  # magenta (was hue 300)
color2 = "#f9ab8f"  # blue (was hue 220)
position = 0
direction = 1  # 1 = toward color2, -1 = toward color1
steps = 40  # smoothness of gradient


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _interpolate(t: float) -> str:
    """Linearly interpolate between color1 and color2"""
    rgb1 = _hex_to_rgb(color1)
    rgb2 = _hex_to_rgb(color2)
    r = rgb1[0] + (rgb2[0] - rgb1[0]) * t
    g = rgb1[1] + (rgb2[1] - rgb1[1]) * t
    b = rgb1[2] + (rgb2[2] - rgb1[2]) * t
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def next_color() -> str:
    """Get next color in the repeating gradient cycle"""
    global position, direction

    t = position / steps
    color = _interpolate(t)

    position += direction
    if position >= steps:
        direction = -1
    elif position <= 0:
        direction = 1

    return color


def safe_style(value: str | None, fallback: str = "#404040") -> str:
    if not value or str(value).lower() == "none":
        return fallback

    value = str(value).strip()
    try:
        _ = Color.parse(value)
        return value
    except ColorParseError:
        return fallback


logColor = safe_style(config.logColor, "#404040")
warnColor = safe_style(config.warnColor, "#b84c44")


def _get_proxy_for_email(email: str) -> dict[str, str] | None:
    path = Path(__file__).resolve().parent / "profiles.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict):
            em = item.get("email") or item.get("mail") or item.get("login")
            if em and str(em).strip().lower() == email.strip().lower():
                proxy_str = item.get("proxy", "").strip()
                if proxy_str:
                    parsed = urlparse(proxy_str)
                    proxy_conf = {
                        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                    }
                    if parsed.username and parsed.password:
                        proxy_conf["username"] = parsed.username
                        proxy_conf["password"] = parsed.password
                    return proxy_conf
    return None


def _write_profiles_json(path: Path, data: list) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _profile_dir_for_email(email: str) -> str:
    base_dir = Path(__file__).resolve().parent / "profiles"
    base_dir.mkdir(exist_ok=True)
    safe_email = re.sub(r"[^a-zA-Z0-9_-]", "_", email)
    profile_dir = base_dir / safe_email
    profile_dir.mkdir(exist_ok=True)
    return str(profile_dir)


def update_points_and_log(email: str, points: int) -> None:
    path = Path(__file__).resolve().parent / "profiles.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    changed = False
    prev_points = None
    for i, item in enumerate(data):
        if isinstance(item, dict):
            em = item.get("email") or item.get("mail") or item.get("login")
            if em and str(em).strip().lower() == email.strip().lower():
                prev_points = item.get("points")
                if prev_points != points:
                    item["points"] = points
                    changed = True
                break
        elif isinstance(item, str) and item.strip().lower() == email.strip().lower():
            prev_points = None
            data[i] = {"email": item, "points": points}
            changed = True
            break
    else:
        data.append({"email": email, "points": points})
        changed = True
    if changed:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

        difference = points - (prev_points or 0)
        color = next_color()
        console.print(
            f"[{color}]ASKJUNE[/{color}] {email} | [{color}]+{difference}[/{color}] pts"
        )


async def _run_farm_profile_async(email: str, wait_for_close: bool = True) -> None:
    _ = wait_for_close

    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        print(f"Error: {exc}")
        return

    import config

    retries = config.retries

    for attempt in range(1, retries + 1):
        context: BrowserContext | None = None

        try:
            async with async_playwright() as p:
                user_data_dir = _profile_dir_for_email(email)
                proxy = _get_proxy_for_email(email)

                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    viewport=None,
                    locale="en-US",
                    proxy=proxy if proxy else None,
                    args=[
                        "--start-maximized",
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                )

                page = context.pages[0] if context.pages else await context.new_page()
                if page.is_closed():
                    await context.close()
                    continue

                page.set_default_timeout(30000)

                # ── Перехват ответов для отслеживания поинтов ──
                async def handle_response(response):
                    try:
                        if "points" in response.url:
                            ct = response.headers.get("content-type", "")
                            if ct.startswith("application/json"):
                                data = await response.json()
                                if isinstance(data, dict) and "points" in data:
                                    update_points_and_log(email, int(data["points"]))
                    except Exception:
                        pass

                page.on("response", handle_response)

                # ══════════════════════════════════════════════════════════
                # ЗАГРУЗКА СТРАНИЦЫ (с защитой от зависания)
                # ══════════════════════════════════════════════════════════
                page_loaded = False

                # Попытка 1: domcontentloaded (быстрее, не ждёт все ресурсы)
                try:
                    console.print(f"{email} | Loading page...", style=logColor)
                    await page.goto(
                        "https://askjune.ai/app/chat",
                        wait_until="domcontentloaded",
                        timeout=20000,
                    )
                    page_loaded = True
                except Exception:
                    console.print(
                        f"{email} | DOM load timeout, trying minimal load...",
                        style=logColor,
                    )

                # Попытка 2: commit (минимум — только начало ответа сервера)
                if not page_loaded:
                    try:
                        await page.goto(
                            "https://askjune.ai/app/chat",
                            wait_until="commit",
                            timeout=15000,
                        )
                        page_loaded = True
                    except Exception:
                        pass

                # Попытка 3: просто открыть и ждать элемент
                if not page_loaded:
                    try:
                        await page.goto("https://askjune.ai/app/chat", timeout=10000)
                        page_loaded = True
                    except Exception:
                        console.print(
                            f"{email} | Page did not load, retry {attempt}/{retries}",
                            style=warnColor,
                        )
                        await context.close()
                        continue

                # Ждём появления ключевых элементов (Sign in ИЛИ points)
                console.print(f"{email} | Waiting for page elements...", style=logColor)
                try:
                    await page.wait_for_selector(
                        'button:has-text("Sign in"), span.tabular-nums',
                        state="visible",
                        timeout=20000,
                    )
                except Exception:
                    # Может страница ещё грузится — пробуем подождать и перезагрузить
                    console.print(
                        f"{email} | Elements not visible, reloading...",
                        style=logColor,
                    )
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=15000)
                        await page.wait_for_selector(
                            'button:has-text("Sign in"), span.tabular-nums',
                            state="visible",
                            timeout=15000,
                        )
                    except Exception:
                        console.print(
                            f"{email} | Key elements not found, retry {attempt}/{retries}",
                            style=warnColor,
                        )
                        await context.close()
                        continue

                console.print(f"{email} | Page loaded successfully", style=logColor)

                # ══════════════════════════════════════════════════════════
                # ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ
                # ══════════════════════════════════════════════════════════

                # ── Фоновое закрытие туров ──
                tour_task = asyncio.create_task(dismiss_tour_overlay(page))

                # ── Автологин ──
                from login_flow import run_login_flow, LoginResult

                login_result = await run_login_flow(
                    page, email, log_style=logColor, warn_style=warnColor
                )

                can_grind = login_result in (
                    LoginResult.ALREADY_LOGGED_IN,
                    LoginResult.LOGIN_SUCCESS,
                )

                if login_result == LoginResult.PAGE_CLOSED:
                    tour_task.cancel()
                    await context.close()
                    continue

                if not can_grind:
                    console.print(
                        f"{email} | Skipping grind — not logged in",
                        style=warnColor,
                    )
                    tour_task.cancel()
                    await context.close()
                    continue

                # ── Настройка страницы ──
                await page.evaluate("(e) => { document.title = e; }", email)
                await page.evaluate(
                    r"""
                    (() => {
                        if (window.__pointsWatcherInstalled) return;
                        window.__pointsWatcherInstalled = true;
                        const selectors = ['.text-arcticNights .tabular-nums', 'span.tabular-nums'];
                        const pick = () => { for (const s of selectors) { const el = document.querySelector(s); if (el) return el; } return null; };
                        const parse = el => { if (!el) return null; const raw = el.textContent || ''; const n = parseInt(raw.replace(/\D/g, ''), 10); return Number.isFinite(n) ? n : null; };
                        const notify = v => { try { window.pyPointsUpdate && window.pyPointsUpdate(v); } catch(e) {} };
                        let observedEl = null; let lastVal = null; let obs = null;
                        const attach = () => {
                            const el = pick();
                            if (!el || el === observedEl) return;
                            if (obs && observedEl) { try { obs.disconnect(); } catch(_) {} }
                            observedEl = el;
                            const sendNow = () => { const v = parse(observedEl); if (v != null && v !== lastVal) { lastVal = v; notify(v); } };
                            obs = new MutationObserver(sendNow);
                            obs.observe(observedEl, { childList: true, characterData: true, subtree: true });
                            sendNow();
                        };
                        const rootObs = new MutationObserver(attach);
                        rootObs.observe(document.documentElement, { childList: true, subtree: true });
                        const poll = () => { attach(); if (observedEl) { const v = parse(observedEl); if (v != null && v !== lastVal) { lastVal = v; notify(v); } } };
                        setInterval(poll, 1000); attach(); poll();
                    })();
                    """
                )

                # ── Гринд ──
                result = await main(page, email)

                # ── Очистка ──
                tour_task.cancel()
                try:
                    await tour_task
                except asyncio.CancelledError:
                    pass

                if result == "close":
                    console.print(f"{email} | Farming completed", style=logColor)

                break

        except Exception as e:
            console.print(
                f"{email} | Error on attempt {attempt}/{retries}: {e}",
                style=warnColor,
            )
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

            if attempt >= retries:
                console.print(f"{email} | All attempts exhausted", style=warnColor)


def run_farm_profile(email: str, wait_for_close: bool = True) -> None:
    if not email:
        console.print("Пустой email профиля", style=warnColor)
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.ensure_future(
            _run_farm_profile_async(email, wait_for_close=wait_for_close)
        )
    else:
        loop.run_until_complete(
            _run_farm_profile_async(email, wait_for_close=wait_for_close)
        )


async def _run_profile_async(email: str, wait_for_close: bool = True) -> None:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        print(f"Ошибка: {exc}")
        return

    async with async_playwright() as p:
        user_data_dir = _profile_dir_for_email(email)
        proxy = _get_proxy_for_email(email)

        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            no_viewport=True,
            locale="en-US",
            timezone_id="Europe/London",
            proxy=proxy if proxy else None,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--use-gl=desktop"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # --- Отслеживание поинтов через перехват ответов ---
        async def safe_parse_json(response):
            try:
                text = await response.text()
                text = text.strip()
                if not text or text.startswith("event:") or text[0] not in "{[":
                    return None
                return json.loads(text)
            except Exception:
                return None

        async def handle_response(response):
            try:
                url = response.url
                if "points" in url:
                    content_type = response.headers.get("content-type", "")
                    if content_type.startswith("application/json"):
                        data = await safe_parse_json(response)
                        if isinstance(data, dict) and "points" in data:
                            points = int(data["points"])
                            update_points_and_log(email, points)
            except Exception:
                pass

        page.on("response", handle_response)

        await page.goto("https://askjune.ai/app/chat")

        # --- Проверка статуса логина ---
        button = await page.query_selector('button:has-text("Sign in")')
        if button:
            set_login_false(email)
        else:
            set_login_true(email)
            try:
                current_points = await page.inner_text("span.tabular-nums")
                console.print(f"{email} | current points: {current_points}")
            except Exception:
                pass

        # --- JS-watcher для поинтов ---
        async def _py_points_update(value: int | None = None):
            if value is None:
                return
            try:
                points = int(value)
            except Exception:
                return
            update_points_and_log(email, points)

        if not page.is_closed():
            await page.expose_function("pyPointsUpdate", _py_points_update)

        await page.evaluate("(email) => { document.title = email; }", email)

        await page.evaluate(
            r"""
        (() => {
            if (window.__pointsWatcherInstalled) return;
            window.__pointsWatcherInstalled = true;
            const selectors = ['.text-arcticNights .tabular-nums', 'span.tabular-nums'];
            const pick = () => {
                for (const s of selectors) { const el = document.querySelector(s); if (el) return el; }
                return null;
            };
            const parse = el => {
                if (!el) return null;
                const raw = el.textContent || '';
                const n = parseInt(raw.replace(/\D/g, ''), 10);
                return Number.isFinite(n) ? n : null;
            };
            const notify = v => { try { window.pyPointsUpdate && window.pyPointsUpdate(v); } catch(e) {} };
            let observedEl = null; let lastVal = null; let obs = null;
            const attach = () => {
                const el = pick();
                if (!el || el === observedEl) return;
                if (obs && observedEl) { try { obs.disconnect(); } catch(_) {} }
                observedEl = el;
                const sendNow = () => { const v = parse(observedEl); if (v != null && v !== lastVal) { lastVal = v; notify(v); } };
                obs = new MutationObserver(sendNow);
                obs.observe(observedEl, { childList: true, characterData: true, subtree: true });
                sendNow();
            };
            const rootObs = new MutationObserver(attach);
            rootObs.observe(document.documentElement, { childList: true, subtree: true });
            const poll = () => {
                attach();
                if (observedEl) {
                    const v = parse(observedEl);
                    if (v != null && v !== lastVal) { lastVal = v; notify(v); }
                }
            };
            setInterval(poll, 1000);
            attach();
            poll();
        })();
        """
        )

        if wait_for_close:
            context.set_default_timeout(0)
            page.set_default_timeout(0)
            await page.wait_for_event("close", timeout=0)


def run_profile(email: str, wait_for_close: bool = True) -> None:
    if not email:
        console.print(f"{email} | profile is empty", style=logColor)
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.ensure_future(_run_profile_async(email, wait_for_close=wait_for_close))
    else:
        loop.run_until_complete(
            _run_profile_async(email, wait_for_close=wait_for_close)
        )
