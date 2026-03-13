"""
This file contains the logic for entering email into the input field
"""

import asyncio
import random

from playwright.async_api import Page


async def input_email_only(page: Page, email: str) -> bool:
    """
    ТОЛЬКО вводит email в поле. Ничего больше не нажимает.

    Returns:
        True если email введён успешно
    """
    try:
        element = await page.wait_for_selector("#email", timeout=5000)
        if not element:
            return False

        box = await element.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            await page.mouse.move(x, y, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y, delay=random.uniform(50, 150))

            for char in email:
                await element.type(char, delay=random.randint(10, 59))

            await asyncio.sleep(random.uniform(0.1, 0.3))
            return True

    except Exception:
        return False

    return False


async def click_continue_button(page: Page) -> bool:
    """
    Нажимает кнопку Continue/Submit.

    Returns:
        True если кнопка нажата
    """
    try:
        button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
        if not button:
            return False

        box = await button.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            await page.mouse.move(x, y, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y, delay=random.uniform(50, 150))
            await asyncio.sleep(random.uniform(0.2, 0.5))
            return True

    except Exception:
        return False

    return False


async def click_checkbox(page: Page) -> bool:
    """
    Нажимает checkbox верификации.

    Returns:
        True если checkbox нажат
    """
    # Селекторы для поиска checkbox
    checkbox_selectors = [
        "div.sc-351891fb-4.fSAsia",
        "div.sc-351891fb-4",
        "div.sc-aaec2400-4",
        'div:has(svg polyline[points="20 6 9 17 4 12"])',
    ]

    for selector in checkbox_selectors:
        try:
            element = await page.query_selector(selector)
            if not element:
                continue

            box = await element.bounding_box()
            if box:
                x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
                y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
                await page.mouse.move(x, y, steps=random.randint(10, 25))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await page.mouse.click(x, y, delay=random.uniform(50, 150))
                await asyncio.sleep(random.uniform(0.2, 0.5))
                return True

        except Exception:
            continue

    return False


# Оставляем старую функцию для совместимости, но помечаем как deprecated
async def input_mail(page: Page, email: str) -> None:
    """
    DEPRECATED: Используй input_email_only() + click_continue_button() отдельно.

    Эта функция делает слишком много: вводит email, нажимает continue, нажимает checkbox.
    """
    await input_email_only(page, email)
    await click_continue_button(page)
    await click_checkbox(page)
