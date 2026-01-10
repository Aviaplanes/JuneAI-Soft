"""
This file handles the parallel execution of profiles – running multiple browsers simultaneously
"""
import os
import sys

import asyncio
import json
from pathlib import Path
import random

import yaml
from rich.color import Color, ColorParseError
from rich.console import Console

import soft
from grind import wait

console = Console()



def parse_hms(time_str: str) -> int:
    # Parses a 'HH:MM:SS' string into seconds 
    try:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return 0
    



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
THREAD_LIMIT = int(config.get("threadCount", 3))


start_delay_cfg = config.get("startDelay", ["00:00:00", "00:00:00"])

try:
    min_delay = parse_hms(start_delay_cfg[0])
    max_delay = parse_hms(start_delay_cfg[1])
except:
    min_delay, max_delay = 0, 0




async def random_start_delay():
    if max_delay <= min_delay:
        await asyncio.sleep(min_delay)
    else:
        await asyncio.sleep(random.randint(min_delay, max_delay))




def load_accounts(path: str = "profiles.json") -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    emails: list[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                emails.append(item)
            elif isinstance(item, dict):
                email = item.get("email") or item.get("mail") or item.get("login")

                login_flag = item.get("login", True)
                if isinstance(login_flag, str):
                    login_flag = login_flag.strip().lower() not in ("false", "0", "no")

                imap_password = item.get("imapPassword")
                has_imap_password = bool(imap_password and str(imap_password).strip())

                if email and (login_flag or has_imap_password):
                    emails.append(str(email))
    return [e for e in (str(x).strip() for x in emails) if e]


async def safe_run_profile(email: str, sem: asyncio.Semaphore) -> None:
    async with sem:
        try:
            await soft._run_farm_profile_async(email, wait_for_close=True)
        except Exception as e:
            console.print(
                f"[ERROR] {email} | Profile ended with an error: {e}", style=warnColor
            )
        finally:
            await wait(2, 6)


async def _launch_all_async(emails: list[str]) -> None:
    sem = asyncio.Semaphore(THREAD_LIMIT)
    tasks = []

    for email in emails:
        await sem.acquire()

        console.print(f"{email} | Starting profile", style=logColor)

        async def _runner(e=email):
            try:
                await soft._run_farm_profile_async(e, wait_for_close=True)
            except Exception as exc:
                console.print(
                    f"[ERROR] {e} | Profile ended with an error: {exc}",
                    style=warnColor,
                )
            finally:
                sem.release()
                await random_start_delay()


        tasks.append(asyncio.create_task(_runner()))
        await random_start_delay()


    await asyncio.gather(*tasks, return_exceptions=True)


def launch_all() -> None:
    emails = load_accounts()
    if not emails:
        console.print("No profiles in profiles.json", style=warnColor)
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.ensure_future(_launch_all_async(emails))
    else:
        loop.run_until_complete(_launch_all_async(emails))
