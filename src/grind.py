"""
This file handles all automated actions for points farming and includes all three farming types – text, images, and video
"""

import asyncio
import json
import random
from collections.abc import Callable
from pathlib import Path

import nodriver as uc
from rich.color import Color, ColorParseError
from rich.console import Console

import config

console = Console()


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


async def wait(*args: float) -> None:
    if len(args) == 1:
        seconds = float(args[0])
    elif len(args) == 2:
        seconds = random.uniform(float(args[0]), float(args[1]))
    else:
        raise ValueError("wait() requires 1 or 2 arguments")
    await asyncio.sleep(seconds)


async def is_page_closed(page: uc.Tab) -> bool:
    """Проверяет, закрыта ли вкладка"""
    try:
        await page.evaluate("1")
        return False
    except Exception:
        return True


async def get_bounding_box(page: uc.Tab, selector: str) -> dict | None:
    """Получает bounding box элемента через JS"""
    try:
        result = await page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return JSON.stringify({{
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                }});
            }})()
        """
        )

        if result and isinstance(result, str):
            return json.loads(result)
        return None
    except Exception:
        return None


async def move_mouse(
    page: uc.Tab,
    from_x: float,
    from_y: float,
    to_x: float,
    to_y: float,
    steps: int = 15,
) -> bool:
    """Плавное движение мыши"""
    for i in range(steps):
        if await is_page_closed(page):
            return False
        t = (i + 1) / steps
        x = from_x + (to_x - from_x) * t
        y = from_y + (to_y - from_y) * t
        try:
            await page.send(
                uc.cdp.input_.dispatch_mouse_event(
                    type_="mouseMoved",
                    x=x,
                    y=y,
                )
            )
        except Exception:
            return False
        await asyncio.sleep(random.uniform(0.01, 0.03))
    return True


async def click_at(page: uc.Tab, x: float, y: float, delay: float = 0.1) -> bool:
    """Клик в указанных координатах"""
    try:
        await page.send(
            uc.cdp.input_.dispatch_mouse_event(
                type_="mousePressed",
                x=x,
                y=y,
                button=uc.cdp.input_.MouseButton.LEFT,
                click_count=1,
            )
        )
        await asyncio.sleep(delay)
        await page.send(
            uc.cdp.input_.dispatch_mouse_event(
                type_="mouseReleased",
                x=x,
                y=y,
                button=uc.cdp.input_.MouseButton.LEFT,
                click_count=1,
            )
        )
        return True
    except Exception:
        return False


async def key_press(page: uc.Tab, key: str) -> None:
    """Нажатие клавиши"""
    try:
        await page.send(
            uc.cdp.input_.dispatch_key_event(
                type_="keyDown",
                key=key,
            )
        )
        await page.send(
            uc.cdp.input_.dispatch_key_event(
                type_="keyUp",
                key=key,
            )
        )
    except Exception:
        pass


async def type_text(page: uc.Tab, text: str) -> bool:
    """Печатает текст посимвольно"""
    for char in text:
        if await is_page_closed(page):
            return False

        try:
            await page.send(
                uc.cdp.input_.dispatch_key_event(
                    type_="keyDown",
                    text=char,
                )
            )
            await page.send(
                uc.cdp.input_.dispatch_key_event(
                    type_="keyUp",
                    text=char,
                )
            )
        except Exception:
            return False

        await asyncio.sleep(random.randint(6, 24) / 1000)

        if random.random() < 0.05:
            if await is_page_closed(page):
                return False
            await asyncio.sleep(random.uniform(0.01, 0.014))

    return True


async def get_inner_text(page: uc.Tab, selector: str) -> str | None:
    """Получает innerText элемента"""
    try:
        text = await page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                return el ? el.innerText : null;
            }})()
        """
        )
        return text
    except Exception:
        return None


async def query_selector_exists(page: uc.Tab, selector: str) -> bool:
    """Проверяет существование элемента"""
    try:
        result = await page.evaluate(
            f"""
            (() => {{
                return document.querySelector({json.dumps(selector)}) !== null;
            }})()
        """
        )
        return bool(result)
    except Exception:
        return False


async def get_cursor_style(page: uc.Tab, selector: str) -> str | None:
    """Получает cursor style элемента"""
    try:
        style = await page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                return window.getComputedStyle(el).cursor;
            }})()
        """
        )
        return style
    except Exception:
        return None


def get_random_prompt(prompts: str) -> str:
    prompts_path = Path(prompts)
    if not prompts_path.exists():
        raise FileNotFoundError(f"File not found: {prompts_path}")
    with prompts_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        raise ValueError(f"File is empty: {prompts_path}")
    return random.choice(lines)


async def dismiss_tour_overlay(page: uc.Tab, interval: float = 0.5) -> None:
    """
    Фоновая задача: закрывает всплывающие окна (тур, модалки).
    Работает пока страница открыта.
    """
    selectors = [
        "button.reactour__close-button",
        'button[aria-label="Continue with selected mode"]',
        "#CybotCookiebotDialogBodyButtonAccept",
    ]

    while not await is_page_closed(page):
        for selector in selectors:
            try:
                if await query_selector_exists(page, selector):
                    await page.evaluate(
                        f"""
                        (() => {{
                            const el = document.querySelector({json.dumps(selector)});
                            if (el) el.click();
                        }})()
                    """
                    )
                    await asyncio.sleep(0.3)
            except Exception:
                pass
        await asyncio.sleep(interval)


async def wait_for_update(
    page: uc.Tab,
    selector: str,
    previous_state: str,
    max_timeout: float = 30.0,
    interval: float = 0.2,
) -> str | None:
    elapsed = 0
    while elapsed < max_timeout:
        try:
            current_state = await get_inner_text(page, selector)
            if current_state and current_state != previous_state:
                return current_state
        except Exception:
            pass
        await asyncio.sleep(interval)
        elapsed += interval
    return None


async def new_chat(
    page: uc.Tab, selector: str = 'button[data-tour="new-chat-button"]', steps: int = 15
) -> bool:
    if await is_page_closed(page):
        return False

    try:
        await wait(0.08, 1)
        element = await page.wait_for(selector, timeout=5)
    except Exception:
        return False

    if await is_page_closed(page):
        return False

    if element is None:
        return False

    box = await get_bounding_box(page, selector)
    if box is None:
        return False

    start_x, start_y = random.uniform(0, 200), random.uniform(0, 200)
    end_x = box["x"] + box["width"] / 2
    end_y = box["y"] + box["height"] / 2

    if not await move_mouse(page, start_x, start_y, end_x, end_y, steps):
        return False

    if await is_page_closed(page):
        return False

    return await click_at(page, end_x, end_y, delay=random.randint(50, 200) / 1000)


async def click_mode(
    page: uc.Tab, mode: str, email: str, timeout: int = 10
) -> bool | None:
    if await is_page_closed(page):
        return False

    selectors = {
        "text": "button:has(svg.lucide-message-circle)",
        "images": "button:has(svg.lucide-image)",
        "videos": "button:has(svg.lucide-tv-minimal-play)",
    }

    selector = selectors.get(mode)

    if not selector:
        print(f"[ERROR] {email} | unknown mode: {mode}")
        return False

    try:
        element = await page.wait_for(selector, timeout=timeout)
        if await is_page_closed(page):
            return False
        if element is None:
            return False

        # force click через JS
        await page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (el) el.click();
            }})()
        """
        )
    except Exception as e:
        if not await is_page_closed(page):
            print(f"[ERROR] {email} | Failed to click mode '{mode}': {e}")
        return False

    return True


async def check_limit_reached(page: uc.Tab) -> bool:
    try:
        result = await page.evaluate(
            """
            (() => {
                const el = document.body.innerText;
                return el.includes("Usage Limit Reached");
            })()
        """
        )
        return bool(result)
    except Exception:
        return False


async def humanClick(page: uc.Tab, selector: str) -> bool:
    """Возвращает True если клик успешен, False если элемент не найден"""
    box = await get_bounding_box(page, selector)
    if not box or not isinstance(box, dict):
        return False

    try:
        start_x = box["x"] + box["width"] + random.randint(50, 150)
        start_y = box["y"] + box["height"] + random.randint(50, 150)

        end_x = box["x"] + random.uniform(5, box["width"] - 5)
        end_y = box["y"] + random.uniform(5, box["height"] - 5)

        steps = random.randint(8, 15)
        await move_mouse(page, start_x, start_y, end_x, end_y, steps)
        await click_at(page, end_x, end_y, delay=random.randint(50, 200) / 1000)
        return True
    except Exception:
        return False


async def click_element(page: uc.Tab, selector: str) -> None:
    box = await get_bounding_box(page, selector)
    if not box:
        raise ValueError(f"Element {selector} not found")

    x = box["x"] + random.uniform(5, box["width"] - 5)
    y = box["y"] + random.uniform(5, box["height"] - 5)
    await click_at(page, x, y, delay=random.randint(50, 200) / 1000)


async def wait_for_points_or_limit(
    page: uc.Tab, check_points_func: Callable[[], bool], timeout: float = 18.0
) -> bool:
    elapsed = 0
    interval = 0.1
    while elapsed < timeout:
        limit = await check_limit_reached(page)
        if limit:
            return True
        if check_points_func():
            return False
        await asyncio.sleep(interval)
        elapsed += interval
    return False


async def grind(page: uc.Tab, timeout: int, email: str, prompt_file: str) -> bool | str:
    last_points = 0

    while True:
        if await is_page_closed(page):
            return False

        await wait(0.21, 0.554)
        if await is_page_closed(page):
            return False
        await wait(0.24, 0.56)

        textarea_selector = None
        for sel in [
            'textarea[placeholder="Type your question here..."]',
            'textarea[placeholder="Describe an image here..."]',
            'textarea[placeholder="Describe a video here..."]',
        ]:
            if await is_page_closed(page):
                return False

            if not await query_selector_exists(page, sel):
                continue

            cursor_style = await get_cursor_style(page, sel)

            if cursor_style == "not-allowed":
                console.print(
                    "[WARN] Element is not clickable (cursor: not-allowed)",
                    style=warnColor,
                )
                return False

            textarea_selector = sel
            break

        if not textarea_selector:
            console.print("[WARN] No available textarea", style=warnColor)
            return False

        if await is_page_closed(page):
            return False

        clicked = await humanClick(page, textarea_selector)
        if not clicked:
            console.print("[WARN] Could not click textarea", style=warnColor)
            return False

        if await is_page_closed(page):
            return False

        await wait(0.5, 0.9)
        if await is_page_closed(page):
            return False

        prompt = get_random_prompt(prompt_file)
        if await is_page_closed(page):
            return False

        _ = await type_text(page, prompt)

        if await is_page_closed(page):
            return False
        await wait(0.06, 0.15)

        if await is_page_closed(page):
            return False
        await key_press(page, "Enter")

        elapsed = 0
        interval = 0.5

        try:
            raw = await get_inner_text(page, "span.tabular-nums")
            current_points = int("".join(c for c in (raw or "") if c.isdigit()) or "0")
        except (ValueError, TypeError):
            current_points = last_points

        while elapsed < timeout:
            if await is_page_closed(page):
                return False

            limit = await check_limit_reached(page)
            if limit:
                console.print(f"[INFO] {email} | Usage limit reached", style=logColor)
                await wait(0.2, 0.411)
                if await is_page_closed(page):
                    return False
                _ = await new_chat(page)
                return True

            try:
                raw = await get_inner_text(page, "span.tabular-nums")
                new_points = int("".join(c for c in (raw or "") if c.isdigit()) or "0")
            except (ValueError, TypeError):
                new_points = current_points

            if new_points != current_points:
                last_points = new_points
                await wait(0.5, 2)
                _ = await new_chat(page)
                break

            await asyncio.sleep(interval)
            elapsed += interval
        else:
            return "close"


async def main(page: uc.Tab, email: str) -> bool | str | None:
    if await is_page_closed(page):
        return False

    # Запускаем фоновый "убийца" тура
    tour_task = asyncio.create_task(dismiss_tour_overlay(page))

    try:
        _ = await click_mode(page, "text", email)
        result = await grind(page, 60, email, "prompts/text.txt")

        if await is_page_closed(page):
            return False

        _ = await click_mode(page, "images", email)
        result = await grind(page, 60, email, "prompts/images.txt")

        if await is_page_closed(page):
            return False

        _ = await click_mode(page, "videos", email)
        result = await grind(page, 60, email, "prompts/videos.txt")

        if await is_page_closed(page):
            return False

        return result

    finally:
        _ = tour_task.cancel()
        try:
            await tour_task
        except asyncio.CancelledError:
            pass
