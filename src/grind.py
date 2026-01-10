"""
This file handles all automated actions for points farming and includes all three farming types – text, images, and video
"""
import os
import sys

import asyncio
import random
from pathlib import Path
from typing import Union

import playwright._impl._errors as pw_errors
import yaml
from playwright.async_api import Page, TimeoutError
from rich.color import Color, ColorParseError
from rich.console import Console

console = Console()


async def wait_for_update(
    page: Page,
    selector: str,
    previous_state: str,
    max_timeout: float = 30.0,
    interval: float = 0.2,
) -> str | None:
    elapsed = 0
    while elapsed < max_timeout:
        try:
            element = await page.query_selector(selector)
            if element:
                current_state = await element.inner_text()
                if current_state != previous_state:
                    return current_state
        except Exception:
            pass
        await asyncio.sleep(interval)
        elapsed += interval
    return None


def safe_style(value: str | None, fallback: str = "#404040") -> str:
    if not value or str(value).lower() == "none":
        return fallback

    value = str(value).strip()
    try:
        _ = Color.parse(value)
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


async def wait(*args: float) -> None:
    if len(args) == 1:
        seconds = float(args[0])
    elif len(args) == 2:
        seconds = random.uniform(float(args[0]), float(args[1]))
    else:
        raise ValueError("wait() requires 1 or 2 arguments")
    await asyncio.sleep(seconds)


async def key_press(page: Page, key: str) -> None:
    await page.keyboard.down(key)
    await page.keyboard.up(key)


async def new_chat(
    page: Page, selector: str = 'button[data-tour="new-chat-button"]', steps: int = 15
) -> bool:
    if page.is_closed():
        return False
    try:
        await wait(0.08, 1)
        element = await page.wait_for_selector(selector, timeout=5000)
    except TimeoutError:
        return False
    except pw_errors.TargetClosedError:
        return False

    if page.is_closed():
        return False

    box = await element.bounding_box() if element is not None else None

    start_x, start_y = random.uniform(0, 200), random.uniform(0, 200)
    end_x = box["x"] + box["width"] / 2
    end_y = box["y"] + box["height"] / 2

    for i in range(steps):
        if page.is_closed():
            return False
        t = (i + 1) / steps
        x = start_x + (end_x - start_x) * t
        y = start_y + (end_y - start_y) * t
        try:
            await page.mouse.move(x, y)
        except pw_errors.TargetClosedError:
            return False

    if page.is_closed():
        return False
    try:
        await page.mouse.click(end_x, end_y, delay=random.randint(50, 200))
    except pw_errors.TargetClosedError:
        return False
    return True


async def click_mode(
    page: Page, mode: str, email: str, timeout: int = 10000
) -> bool | None:
    if page.is_closed():
        return False

    # selectors use SVG path attributes to find the desired button
    selectors = {
        "text": 'button:has(svg.lucide-message-circle)',
        "images": 'button:has(svg.lucide-image)',
        "videos": 'button:has(svg.lucide-tv-minimal-play)',
    }

    selector = selectors.get(mode)

    if not selector:
        print(f"[ERROR] {email} | Неизвестный режим: {mode}")
        return False

    try:
        element = await page.wait_for_selector(
            selector, timeout=timeout, state="visible"
        )
        if page.is_closed():
            return False
        await element.click(force=True)
    except TimeoutError:
        print(f"[WARN] {email} | Mode '{mode}' element did not appear within {timeout} ms")
    except Exception as e:
        if not page.is_closed():
            print(f"[ERROR] {email} | Failed to click mode '{mode}': {e}")
    return True


async def check_limit_reached(page: Page) -> bool:
    element = await page.query_selector(
        'div:has-text("You have reached your 5-hour usage limit")'
    )
    return element is not None


async def humanClick(page: Page, selector: str) -> None:
    box = await page.locator(selector).bounding_box()
    if not box:
        raise ValueError(f"Element {selector} not found")

    start_x = box["x"] + box["width"] + random.randint(50, 150)
    start_y = box["y"] + box["height"] + random.randint(50, 150)

    end_x = box["x"] + random.uniform(5, box["width"] - 5)
    end_y = box["y"] + random.uniform(5, box["height"] - 5)

    steps = random.randint(8, 15)
    for i in range(steps):
        x = start_x + (end_x - start_x) * (i / steps)
        y = start_y + (end_y - start_y) * (i / steps)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.05))

    await page.mouse.click(end_x, end_y, delay=random.randint(50, 200))


async def click(page: Page, selector: str) -> None:
    box = await page.locator(selector).bounding_box()
    if not box:
        raise ValueError(f"Element {selector} not found")

    x = box["x"] + random.uniform(5, box["width"] - 5)
    y = box["y"] + random.uniform(5, box["height"] - 5)
    await page.mouse.click(x, y, delay=random.randint(50, 200))


def get_random_prompt(prompts: str) -> str:
    prompts_path = Path(prompts)
    if not prompts_path.exists():
        raise FileNotFoundError(f"File not found: {prompts_path}")
    with prompts_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        raise ValueError(f"File is empty: {prompts_path}")

    return random.choice(lines)


async def type(page: Page, text: str) -> bool:
    for char in text:
        if page.is_closed():
            return False

        await page.keyboard.type(char, delay=random.randint(6, 24))

        if page.is_closed():
            return False
        if random.random() < 0.05:
            if page.is_closed():
                return False

            pause = random.uniform(0.01, 0.014)

            elapsed = 0
            interval = 0.001
            while elapsed < pause:
                if page.is_closed():
                    return False
                await asyncio.sleep(interval)
                elapsed += interval
    return True


async def wait_for_points_or_limit(
    page: Page, check_points_func, timeout: float = 18.0
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


async def grind(page: Page, timeout: int, email, prompt_file: str) -> bool:
    last_points = 0
    while True:
        if page.is_closed():
            return False

        await wait(0.21, 0.554)
        if page.is_closed():
            return False
        await wait(0.24, 0.56)

        textarea_selector = None
        for sel in [
            'textarea[placeholder="Type your question here..."]',
            'textarea[placeholder="Describe an image here..."]',
            'textarea[placeholder="Describe a video here..."]',
        ]:
            if page.is_closed():
                return False

            element = await page.query_selector(sel)
            if not element:
                continue

            cursor_style = await page.evaluate(
                "(el) => window.getComputedStyle(el).cursor", element
            )
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

        if page.is_closed():
            return False

        await humanClick(page, textarea_selector)
        if page.is_closed():
            return False

        await wait(0.5, 0.9)
        if page.is_closed():
            return False

        prompt = get_random_prompt(prompt_file)
        if page.is_closed():
            return False
        _ = await type(page, prompt)

        if page.is_closed():
            return False
        await wait(0.06, 0.15)

        if page.is_closed():
            return False
        await key_press(page, "Enter")

        elapsed = 0
        interval = 0.5

        try:
            raw = await page.inner_text("span.tabular-nums")
            current_points = int("".join(c for c in raw if c.isdigit()))
        except (ValueError, TypeError, TimeoutError):
            current_points = last_points

        while elapsed < timeout:
            if page.is_closed():
                return False

            limit = await check_limit_reached(page)
            if limit:
                console.print(
                    f"[INFO] {email} | Usage limit reached", style=logColor
                )
                await wait(0.2, 0.411)
                if page.is_closed():
                    return False
                await new_chat(page)
                return True
            try:
                raw = await page.inner_text("span.tabular-nums")
                new_points = int("".join(c for c in raw if c.isdigit()))
            except (ValueError, TypeError, TimeoutError):
                new_points = current_points

            if new_points != current_points:
                last_points = new_points
                await wait(0.5, 2)
                await new_chat(page)
                break

            await asyncio.sleep(interval)
            elapsed += interval
        else:
            return "close"


async def main(page: Page, email) -> bool | str | None:
    if page.is_closed():
        return False

    await click_mode(page, "text", email)
    result = await grind(page, 60, email, "prompts/text.txt")

    if page.is_closed():
        return False

    await click_mode(page, "images", email)
    result = await grind(page, 60, email, "prompts/images.txt")

    if page.is_closed():
        return False

    await click_mode(page, "videos", email)
    result = await grind(page, 60, email, "prompts/videos.txt")

    if page.is_closed():
        return False

    return result
