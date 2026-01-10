"""
This file contains the logic for entering email into the input field
"""
import os
import sys

import asyncio
import random

from playwright.async_api import Page


async def input_mail(page: Page, email: str) -> None:
    try:
        element = await page.wait_for_selector("#email", timeout=5000)
        box = await element.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            await page.mouse.move(x, y, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y, delay=random.uniform(50, 150))
            for char in email:
                await element.type(char, delay=random.randint(10, 59))  # type speed
            await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception:
        pass
    try:
        button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
        button_box = await button.bounding_box()
        if button_box:
            bx = button_box["x"] + button_box["width"] / 2 + random.uniform(-3, 3)
            by = button_box["y"] + button_box["height"] / 2 + random.uniform(-3, 3)
            await page.mouse.move(bx, by, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(bx, by, delay=random.uniform(50, 150))
            await asyncio.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass
    try:
        final_button = await page.wait_for_selector("div.sc-aaec2400-4", timeout=5000)
        final_box = await final_button.bounding_box()
        if final_box:
            fx = final_box["x"] + final_box["width"] / 2 + random.uniform(-3, 3)
            fy = final_box["y"] + final_box["height"] / 2 + random.uniform(-3, 3)
            await page.mouse.move(fx, fy, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(fx, fy, delay=random.uniform(50, 150))
            await asyncio.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass
