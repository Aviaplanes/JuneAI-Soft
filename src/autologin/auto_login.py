"""
This file contains the auto-login logic for profiles that are not logged in
"""
import os
import sys

import asyncio
import math
import random

from playwright.async_api import Page


async def human_click_if_exists(page: Page, selector: str) -> bool:
    button = await page.query_selector(selector)
    if not button:
        return False

    box = await button.bounding_box()
    if not box:
        return False

    target_x = box["x"] + random.uniform(2, box["width"] - 2)
    target_y = box["y"] + random.uniform(2, box["height"] - 2)

    mouse_x, mouse_y = random.uniform(0, 50), random.uniform(0, 50)

    steps_range = (10, 15)
    sleep_range = (0.01, 0.03)

    steps = random.randint(*steps_range)
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
        await page.mouse.move(x, y, steps=1)
        await asyncio.sleep(random.uniform(*sleep_range))

    await page.mouse.click(target_x, target_y)
    return True
