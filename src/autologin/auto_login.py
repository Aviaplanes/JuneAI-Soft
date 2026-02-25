"""
This file contains the auto-login logic for profiles that are not logged in
"""

import asyncio
import json
import math
import random

import nodriver as uc


def set_login_true(email: str, path: str = "profiles.json") -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    for profile in data:
        if isinstance(profile, dict) and profile.get("email") == email:
            profile["login"] = True
            break

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def set_login_false(email: str, path: str = "profiles.json") -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    for profile in data:
        if isinstance(profile, dict) and profile.get("email") == email:
            profile["login"] = False
            break

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def human_click_if_exists(page: uc.Tab, selector: str) -> bool:
    """
    Ищет элемент по CSS-селектору и кликает с имитацией человеческого движения мыши.
    Возвращает True если клик выполнен, False если элемент не найден.
    """
    try:
        element = await page.select(selector, timeout=2)
    except Exception:
        return False

    if not element:
        return False

    # Получаем bounding box через JS
    try:
        box = await page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {{
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                }};
            }})()
        """
        )
    except Exception:
        box = None

    if not box:
        # Если не получили box — просто кликаем стандартно
        await element.click()
        return True

    target_x = box["x"] + random.uniform(2, box["width"] - 2)
    target_y = box["y"] + random.uniform(2, box["height"] - 2)

    mouse_x, mouse_y = random.uniform(0, 50), random.uniform(0, 50)

    steps_range = (10, 15)
    sleep_range = (0.01, 0.03)

    steps = random.randint(*steps_range)

    # Движение мыши через CDP
    for i in range(steps):
        t = i / steps
        x = (
            mouse_x
            + (target_x - mouse_x) * t
            + math.sin(t * math.pi * 2) * random.uniform(1, 3)
        )
        y = (
            mouse_y
            + (target_y - mouse_y) * t
            + math.sin(t * math.pi * 2) * random.uniform(1, 3)
        )

        await page.send(
            uc.cdp.input_.dispatch_mouse_event(
                type_="mouseMoved",
                x=x,
                y=y,
            )
        )
        await asyncio.sleep(random.uniform(*sleep_range))

    # Клик: mousePressed + mouseReleased
    await page.send(
        uc.cdp.input_.dispatch_mouse_event(
            type_="mousePressed",
            x=target_x,
            y=target_y,
            button=uc.cdp.input_.MouseButton.LEFT,
            click_count=1,
        )
    )
    await page.send(
        uc.cdp.input_.dispatch_mouse_event(
            type_="mouseReleased",
            x=target_x,
            y=target_y,
            button=uc.cdp.input_.MouseButton.LEFT,
            click_count=1,
        )
    )

    return True


async def human_click_by_text(page: uc.Tab, text: str) -> bool:
    """
    Ищет элемент по тексту и кликает.
    """
    try:
        element = await page.find(text, timeout=2)
    except Exception:
        return False

    if not element:
        return False

    await element.click()
    return True
