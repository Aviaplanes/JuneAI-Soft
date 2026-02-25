"""
This file contains the logic for launching profiles and farming
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import nodriver as uc
from rich.console import Console

from profile_utils import (
    console,
    logColor,
    warnColor,
    get_proxy_arg,
    profile_dir_for_email,
    update_points_and_log,
    load_profile_config,
)
from autologin.auto_login import human_click_if_exists
from autologin.email_input import input_mail
from autologin.login_check import set_login_false, set_login_true
from grind import (
    dismiss_tour_overlay,
    key_press,
    type_text,
    wait,
    main as grind_main,
    is_page_closed,
    get_inner_text,
    query_selector_exists,
)
from imap import get_code


async def setup_points_watcher(page: uc.Tab, email: str) -> None:
    """Устанавливает JS-watcher для отслеживания изменений поинтов"""
    await page.evaluate(f"document.title = {json.dumps(email)}")

    await page.evaluate(
        r"""
    (() => {
        if (window.__pointsWatcherInstalled) return;
        window.__pointsWatcherInstalled = true;
        const selectors = ['.text-arcticNights .tabular-nums', 'span.tabular-nums'];
        const pick = () => {
            for (const s of selectors) {
                const el = document.querySelector(s);
                if (el) return el;
            }
            return null;
        };
        const parse = el => {
            if (!el) return null;
            const raw = el.textContent || '';
            const n = parseInt(raw.replace(/\D/g, ''), 10);
            return Number.isFinite(n) ? n : null;
        };
        let lastVal = null;
        const poll = () => {
            const el = pick();
            const v = parse(el);
            if (v != null && v !== lastVal) {
                lastVal = v;
                window.__currentPoints = v;
            }
        };
        setInterval(poll, 1000);
        poll();
    })();
    """
    )


async def get_current_points(page: uc.Tab) -> int | None:
    """Получает текущие поинты со страницы"""
    try:
        points = await page.evaluate("window.__currentPoints || null")
        return int(points) if points else None
    except Exception:
        return None


async def setup_network_interception(page: uc.Tab, email: str) -> None:
    """Настраивает перехват сетевых запросов для отслеживания поинтов"""
    await page.send(uc.cdp.network.enable())

    async def handle_response(event: uc.cdp.network.ResponseReceived):
        try:
            url = event.response.url

            if "points" in url and "api/account/points" in url:
                try:
                    body = await page.send(
                        uc.cdp.network.get_response_body(event.request_id)
                    )

                    # body это tuple: (json_string, is_base64)
                    if body and isinstance(body, tuple) and len(body) >= 1:
                        json_str = body[0]
                        data = json.loads(json_str)

                        if isinstance(data, dict) and "points" in data:
                            points = int(data["points"])
                            update_points_and_log(email, points)
                except Exception:
                    pass
        except Exception:
            pass

    page.add_handler(uc.cdp.network.ResponseReceived, handle_response)


async def check_login_status(page: uc.Tab) -> tuple[bool, str | None]:
    """
    Проверяет статус логина.
    Возвращает (is_logged_in, current_points)
    """
    await asyncio.sleep(3)

    for _ in range(20):
        if await is_page_closed(page):
            return False, None

        try:
            points = await page.evaluate(
                """
                (() => {
                    const selectors = [
                        'span.tabular-nums',
                        '.tabular-nums',
                        '[class*="tabular"]'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText && /\\d/.test(el.innerText)) {
                            return el.innerText.trim();
                        }
                    }
                    return null;
                })()
            """
            )

            if points:
                return True, str(points)

            has_signin = await page.evaluate(
                """
                (() => {
                    const btns = [...document.querySelectorAll('button')];
                    return btns.some(b => b.textContent.includes('Sign in'));
                })()
            """
            )

            if has_signin:
                return False, None

        except Exception:
            pass

        await asyncio.sleep(0.5)

    return False, None


async def perform_login(page: uc.Tab, email: str) -> bool:
    """Выполняет процесс логина. Возвращает True если успешно."""

    # 1. Клик по Sign in
    clicked = await human_click_if_exists(page, 'button:has-text("Sign in")')
    if not clicked:
        try:
            await page.evaluate(
                """
                (() => {
                    const btns = [...document.querySelectorAll('button')];
                    const btn = btns.find(b => b.textContent.includes('Sign in'));
                    if (btn) btn.click();
                })()
            """
            )
        except Exception:
            return False

    # 2. Ждём загрузки страницы логина — ищем поле email
    console.print(f"{email} | Waiting for login page...", style=logColor)

    email_field_found = False
    for i in range(30):  # 15 секунд
        if await is_page_closed(page):
            return False

        found = await page.evaluate(
            """
            (() => {
                const selectors = [
                    '#email',
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[autocomplete="email"]'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) return true;
                }
                return false;
            })()
        """
        )

        if found:
            email_field_found = True
            break

        await asyncio.sleep(0.5)

    if not email_field_found:
        console.print(f"{email} | Login page did not load", style=warnColor)
        return False

    await wait(0.5, 1)

    # 3. Кликаем по полю email и вводим
    try:
        box = await get_bounding_box_safe(
            page, '#email, input[type="email"], input[name="email"]'
        )
        if box:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            await click_at(page, x, y, delay=0.1)
            await wait(0.2, 0.4)
        else:
            await page.evaluate(
                """
                (() => {
                    const el = document.querySelector('#email') || 
                               document.querySelector('input[type="email"]') ||
                               document.querySelector('input[name="email"]');
                    if (el) { el.focus(); el.click(); }
                })()
            """
            )
            await wait(0.2, 0.4)
    except Exception:
        pass

    await type_text(page, email)
    await wait(0.5, 1)

    # 4. Нажимаем Continue/Submit
    console.print(f"{email} | Clicking Continue...", style=logColor)

    submitted = await page.evaluate(
        """
        (() => {
            // Ищем кнопку submit
            const submitBtn = document.querySelector('button[type="submit"]');
            if (submitBtn) { submitBtn.click(); return "submit"; }
            
            // Ищем кнопку с текстом Continue
            const btns = [...document.querySelectorAll('button')];
            const cont = btns.find(b => b.textContent.includes('Continue'));
            if (cont) { cont.click(); return "continue"; }
            
            // Ищем любую кнопку
            const any = btns.find(b => b.textContent.trim().length > 0);
            if (any) { any.click(); return "any:" + any.textContent.trim(); }
            
            // Пробуем submit формы
            const form = document.querySelector('form');
            if (form) { form.submit(); return "form"; }
            
            return null;
        })()
    """
    )

    if not submitted:
        # Пробуем Enter
        await key_press(page, "Enter")

    await wait(2, 3)

    # 5. Ждём поле кода верификации
    console.print(f"{email} | Waiting for verification code...", style=logColor)

    code_field_found = False
    for i in range(40):  # 20 секунд
        if await is_page_closed(page):
            return False

        # Может уже залогинились
        points_text = await get_inner_text(page, "span.tabular-nums")
        if points_text:
            console.print(f"{email} | logged in, points: {points_text}")
            set_login_true(email)
            return True

        # Ищем поле кода по разным селекторам
        code_found = await page.evaluate(
            """
            (() => {
                const selectors = [
                    'input[aria-label="Verification code"]',
                    'input[name="code"]',
                    'input[type="number"]',
                    'input[placeholder*="code" i]',
                    'input[placeholder*="Code" i]',
                    'input[autocomplete="one-time-code"]'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) return sel;
                }
                return null;
            })()
        """
        )

        if code_found:
            console.print(f"{email} | Code field found: {code_found}", style=logColor)
            code_field_found = True
            break

        await asyncio.sleep(0.5)

    if not code_field_found:
        console.print(f"{email} | Verification code field not found", style=warnColor)
        return False

    # 6. Клик по полю кода
    try:
        await page.evaluate(
            """
            (() => {
                const selectors = [
                    'input[aria-label="Verification code"]',
                    'input[name="code"]',
                    'input[type="number"]',
                    'input[placeholder*="code" i]',
                    'input[autocomplete="one-time-code"]'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) { el.focus(); el.click(); return; }
                }
            })()
        """
        )
    except Exception:
        pass

    await wait(5, 7)

    # 7. IMAP
    profiles_path = Path(__file__).resolve().parent / "profiles.json"
    try:
        with open(profiles_path, "r", encoding="utf-8") as f:
            profiles = json.load(f)
    except Exception:
        profiles = []

    profile = next((p for p in profiles if p.get("email") == email), None)

    if profile and profile.get("imapPassword"):
        try:
            code = get_code(email)
            if code:
                await type_text(page, code)
                await key_press(page, "Enter")
            else:
                console.print(f"{email} | No verification code found", style=warnColor)
        except Exception as e:
            error_msg = str(e).lower()
            if "authentication" in error_msg or "credentials" in error_msg:
                console.print(
                    f"{email} | IMAP auth failed - check imapPassword", style=warnColor
                )
            else:
                console.print(f"{email} | IMAP error: {e}", style=warnColor)
    else:
        console.print(
            f"{email} | No imapPassword - enter code manually", style=logColor
        )

    # 8. Ждём поинты
    for _ in range(60):
        if await is_page_closed(page):
            return False

        points_text = await get_inner_text(page, "span.tabular-nums")
        if points_text:
            console.print(f"{email} | logged in, points: {points_text}")
            set_login_true(email)
            return True

        await asyncio.sleep(0.5)

    console.print(f"{email} | Login failed, points not found", style=warnColor)
    return False


async def _run_farm_profile_async(email: str, wait_for_close: bool = True) -> None:
    """Основная функция фарма профиля"""
    _ = wait_for_close

    cfg = load_profile_config()
    retries = int(cfg.get("retries", 3))
    attempt = 0

    while attempt < retries:
        attempt += 1
        browser = None

        try:
            user_data_dir = profile_dir_for_email(email)
            proxy_arg = get_proxy_arg(email)

            browser_args = ["--start-maximized"]

            if proxy_arg:
                browser_args.append(f"--proxy-server={proxy_arg}")

            browser = await uc.start(
                user_data_dir=user_data_dir,
                headless=False,
                browser_args=browser_args,
                lang="en-US",
            )

            page = await browser.get("https://askjune.ai/app/chat")

            if await is_page_closed(page):
                if browser:
                    try:
                        await browser.stop()
                    except Exception:
                        pass
                continue

            await setup_network_interception(page, email)

            tour_task = asyncio.create_task(dismiss_tour_overlay(page))

            is_logged_in, current_points = await check_login_status(page)

            can_grind = False

            if is_logged_in:
                console.print(f"{email} | current points: {current_points}")
                set_login_true(email)
                can_grind = True
            else:
                set_login_false(email)
                can_grind = await perform_login(page, email)

            if not can_grind:
                console.print(
                    f"{email} | Could not login or find points",
                    style=warnColor,
                )
                tour_task.cancel()
                try:
                    await tour_task
                except asyncio.CancelledError:
                    pass
                if browser:
                    try:
                        await browser.stop()
                    except Exception:
                        pass
                continue

            await setup_points_watcher(page, email)

            result = await grind_main(page, email)

            tour_task.cancel()
            try:
                await tour_task
            except asyncio.CancelledError:
                pass

            if result == "close":
                console.print(f"{email} | Farming completed", style=logColor)

            # Всегда закрываем браузер после завершения
            if browser:
                try:
                    await browser.stop()
                except Exception:
                    pass

            break

        except Exception as e:
            console.print(
                f"{email} | Error on attempt {attempt}/{retries}: {e}",
                style=warnColor,
            )

            # Обязательно закрываем браузер при ошибке
            if browser:
                try:
                    await browser.stop()
                except Exception:
                    pass

                # Ждём чтобы процесс Chrome точно завершился
                await asyncio.sleep(2)

            if attempt >= retries:
                console.print(
                    f"{email} | All attempts exhausted",
                    style=warnColor,
                )


async def _run_profile_async(email: str, wait_for_close: bool = True) -> None:
    """Запуск профиля без автоматизации (только просмотр)"""
    user_data_dir = profile_dir_for_email(email)
    proxy_arg = get_proxy_arg(email)

    browser_args = []

    if proxy_arg:
        browser_args.append(f"--proxy-server={proxy_arg}")

    browser = await uc.start(
        user_data_dir=user_data_dir,
        headless=False,
        browser_args=browser_args,
        lang="en-US",
    )

    page = await browser.get("https://askjune.ai/app/chat")

    await setup_network_interception(page, email)

    is_logged_in, current_points = await check_login_status(page)

    if is_logged_in:
        set_login_true(email)
        console.print(f"{email} | current points: {current_points}")
    else:
        set_login_false(email)

    await setup_points_watcher(page, email)

    if wait_for_close:
        while not await is_page_closed(page):
            await asyncio.sleep(1)


def run_farm_profile(email: str, wait_for_close: bool = True) -> None:
    if not email:
        console.print("Empty email", style=warnColor)
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
