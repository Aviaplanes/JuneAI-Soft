"""
This file contains the logic for entering email into the input field
"""

import asyncio
import json
import random

import nodriver as uc


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
) -> None:
    """Плавное движение мыши"""
    for i in range(steps):
        t = i / steps
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
            pass
        await asyncio.sleep(random.uniform(0.005, 0.015))


async def click_at(page: uc.Tab, x: float, y: float, delay: float = 0.1) -> None:
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
    except Exception:
        pass


async def type_text_human(
    page: uc.Tab, text: str, min_delay: int = 10, max_delay: int = 59
) -> None:
    """Печатает текст посимвольно с человеческими задержками"""
    for char in text:
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
            pass
        await asyncio.sleep(random.randint(min_delay, max_delay) / 1000)


async def find_email_input(page: uc.Tab) -> str | None:
    """Ищет поле ввода email по разным селекторам"""
    selectors = [
        "#email",
        'input[type="email"]',
        'input[name="email"]',
        'input[placeholder*="email" i]',
        'input[placeholder*="Email" i]',
        'input[autocomplete="email"]',
    ]

    for selector in selectors:
        try:
            exists = await page.evaluate(
                f"""
                (() => {{
                    const el = document.querySelector({json.dumps(selector)});
                    return el !== null;
                }})()
            """
            )
            if exists:
                return selector
        except Exception:
            pass

    return None


async def input_mail(page: uc.Tab, email: str) -> None:
    # Ждём появления формы
    await asyncio.sleep(1)

    mouse_x, mouse_y = random.uniform(100, 200), random.uniform(100, 200)

    # Ищем поле email
    selector = await find_email_input(page)

    if not selector:
        print(f"[WARN] Email input not found, trying JS focus...")
        # Пробуем через JS найти и кликнуть
        try:
            await page.evaluate(
                """
                (() => {
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {
                        if (inp.type === 'email' || inp.name === 'email' || inp.id === 'email') {
                            inp.focus();
                            inp.click();
                            return true;
                        }
                    }
                    // Если не нашли по типу, берём первый input
                    if (inputs.length > 0) {
                        inputs[0].focus();
                        inputs[0].click();
                        return true;
                    }
                    return false;
                })()
            """
            )
        except Exception:
            pass

        await asyncio.sleep(0.3)
        await type_text_human(page, email)
        return

    # Клик по полю email и ввод
    try:
        box = await get_bounding_box(page, selector)

        if box:
            x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)

            await move_mouse(page, mouse_x, mouse_y, x, y, steps=random.randint(10, 25))
            mouse_x, mouse_y = x, y

            await asyncio.sleep(random.uniform(0.1, 0.3))
            await click_at(page, x, y, delay=random.uniform(0.05, 0.15))
            await asyncio.sleep(0.2)

            await type_text_human(page, email, min_delay=10, max_delay=59)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        else:
            # Если box не получили — фокус через JS
            await page.evaluate(
                f"""
                (() => {{
                    const el = document.querySelector({json.dumps(selector)});
                    if (el) {{
                        el.focus();
                        el.click();
                    }}
                }})()
            """
            )
            await asyncio.sleep(0.2)
            await type_text_human(page, email)
    except Exception as e:
        print(f"[WARN] input_mail error: {e}")

    # Клик по кнопке submit
    try:
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button:has-text("Sign in")',
        ]

        for sel in submit_selectors:
            # Для :has-text используем JS
            if ":has-text(" in sel:
                text = sel.split(':has-text("')[1].split('")')[0]
                clicked = await page.evaluate(
                    f"""
                    (() => {{
                        const btns = [...document.querySelectorAll('button')];
                        const btn = btns.find(b => b.textContent.includes('{text}'));
                        if (btn) {{
                            btn.click();
                            return true;
                        }}
                        return false;
                    }})()
                """
                )
                if clicked:
                    break
            else:
                box = await get_bounding_box(page, sel)
                if box:
                    bx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
                    by = box["y"] + box["height"] / 2 + random.uniform(-3, 3)

                    await move_mouse(
                        page, mouse_x, mouse_y, bx, by, steps=random.randint(10, 25)
                    )
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    await click_at(page, bx, by, delay=random.uniform(0.05, 0.15))
                    break

        await asyncio.sleep(random.uniform(0.3, 0.6))
    except Exception:
        pass
