"""
This file contains the logic for launching profiles, configuring their startup, and reading points 
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


import win32con
import win32gui
import yaml
from rich.color import Color, ColorParseError
from rich.console import Console

from autologin import (
    human_click_if_exists,
    input_mail,
    set_login_false,
    set_login_true,
)
from grind import (
    key_press, 
    main, 
    type, 
    wait
)
from imap import get_code

console = Console()

hue = 300  # magenta
direction = 1  # 1 = Increasing, -1 = Decreasing
step = 2  

def hue_to_hex(h):
    # Converts H (0-360) to HEX color via HSL 
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h/360, 0.5, 1)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def next_color():
    global hue, direction
    hue += step * direction
    
    if hue > 300:
        hue = 300 - (hue - 300) 
        direction = -1
    elif hue < 220:
        hue = 220 + (220 - hue)
        direction = 1
        
    return hue_to_hex(hue)


def safe_style(value: str | None, fallback: str = "#404040") -> str:
    if not value or str(value).lower() == "none":
        return fallback

    value = str(value).strip()
    try:
        Color.parse(value)
        return value
    except ColorParseError:
        return fallback


config_path = Path(__file__).parent.parent / "config.yaml"

try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    config = {}


logColor = safe_style(config.get("logColor"), "#404040")
warnColor = safe_style(config.get("warnColor"), "#b84c44")


def _get_proxy_for_email(email: str) -> dict | None:
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
        try:
            local_part = email.split("@", 1)
        except ValueError:
            local_part = email, ""
        difference = points - prev_points
        color = next_color() 
        console.print(f"[{color}]ASKJUNE[/{color}] {email} | [{color}]+{difference}[/{color}] pts")


   

async def _run_farm_profile_async(email: str, wait_for_close: bool = True) -> None:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        print(f"Error: {exc}")
        return

    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {}

    retries = int(config.get("retries", 3))
    attempt = 0

    while attempt < retries:
        attempt += 1
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

                

                async def handle_response(response):
                    try:
                        url = response.url
                        if "points" in url:
                            if response.headers.get("content-type", "").startswith(
                                "application/json"
                            ):
                                data = await response.json()
                                if isinstance(data, dict) and "points" in data:
                                    points = int(data["points"])
                                    update_points_and_log(email, points)
                    except Exception:
                        pass

                page.on("response", handle_response)

                try:
                    await page.goto("https://askjune.ai/app/chat")
                except Exception:
                    console.print(
                        f"{email} | Page did not load, retry {attempt}/{retries}",
                        style=warnColor,
                    )
                    await context.close()
                    continue

                points_selector = "span.tabular-nums"
                signin_selector = 'button:has-text("Sign in")'

                points_task = asyncio.create_task(
                    page.wait_for_selector(points_selector, state="visible")
                )
                signin_task = asyncio.create_task(
                    page.wait_for_selector(signin_selector, state="visible")
                )

                done, pending = await asyncio.wait(
                    [points_task, signin_task], return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()

                points_element = None
                signin_element = None

                for task in done:
                    try:
                        element = task.result()
                        if not element:
                            continue
                        tag_text = await element.text_content() or ""
                        if "Sign in" in tag_text:
                            signin_element = element
                        else:
                            points_element = element
                    except Exception:
                        continue
                await wait(5, 6)
                if points_element:
                    current_points = await points_element.inner_text()
                    console.print(f"{email} | current points: {current_points}")
                    set_login_true(email)

                elif signin_element:
                    set_login_false(email)
                    await signin_element.click()
                    await input_mail(page, email)
                    await human_click_if_exists(
                        page, 'input[aria-label="Verification code"]'
                    )
                    await wait(7, 9)

                    with open("profiles.json", "r", encoding="utf-8") as f:
                        profiles = json.load(f)
                    profile = next(
                        (p for p in profiles if p.get("email") == email), None
                    )
                    if profile and "imapPassword" in profile:
                        try:
                            code = get_blockchain_code(email)
                            await type(page, code)
                            await key_press(page, "Enter")
                        except RuntimeError as e:
                            if "imapPassword not found" in str(e):
                                console.print(
                                    f"{email} imap is not connected", style=logColor
                                )
                            else:
                                raise

                else:
                    console.print(
                        f"{email} | Element 'points' and 'Sign in' button not found",
                        style=warnColor,
                    )
                    await context.close()
                    continue

                await page.evaluate("(email) => { document.title = email; }", email)

                await page.evaluate(r"""
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
                """)

                page_closed = asyncio.Event()
                page.on("close", lambda: page_closed.set())

                result = await main(page, email)
                if result == "close":
                    console.print(f"[INFO] {email} | Farming completed", style=logColor)
                    break

                break

        except Exception as e:
            console.print(
                f"{email} | Error on attempt {attempt}/{retries}: {e}", style=warnColor
            )
            try:
                await context.close()
            except Exception:
                pass
            if attempt >= retries:
                console.print(
                    f"{email} | All attempts exhausted",
                    style=warnColor,
                )


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
            args=["--no-sandbox", 
                "--disable-dev-shm-usage", 
                "--use-gl=desktop"
                ],
        )

        page = context.pages[0] if context.pages else await context.new_page()

      

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
                        try:
                            data = await safe_parse_json(response)
                            if isinstance(data, dict) and "points" in data:
                                points = int(data["points"])
                                update_points_and_log(email, points)
                        except Exception as e_json:
                            print(f"[ERROR] JSON ошибка {url}: {e_json}")
                            text = await response.text()
                            print(f"[DEBUG] Ответ:\n{text}")
            except Exception as e:
                print(f"[ERROR] handle_response: {e}")
                import traceback

                traceback.print_exc()

        page.on("response", handle_response)
        await page.goto("https://askjune.ai/app/chat")


        button = await page.query_selector('button:has-text("Sign in")')
        if button:
            set_login_false(email)
        else:
            set_login_true(email)

            current_points = await page.inner_text("span.tabular-nums")
            console.print(f"{email} | current points: " + current_points)

        clicked = await human_click_if_exists(page, 'button:has-text("Sign in")')
        if clicked:
            await input_mail(page, email)
            await human_click_if_exists(page, 'input[aria-label="Verification code"]')
            await wait(7, 10)

            with open("profiles.json", "r", encoding="utf-8") as f:
                profiles = json.load(f)
            profile = next((p for p in profiles if p.get("email") == email), None)
            if profile and "imapPassword" in profile:
                try:
                    code = get_blockchain_code(email)
                    await type(page, code)
                    await key_press(page, "Enter")
                except RuntimeError as e:
                    if "не найден imapPassword" in str(e):
                        console.print(f"{email} imap is not connected", style=logColor)
                    else:
                        raise

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

        await page.evaluate(r"""
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
        """)

        button = await page.query_selector('button:has-text("Sign in")')
        if button:
            set_login_false(email)
        else:
            set_login_true(email)

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
