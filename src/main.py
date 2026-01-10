"""
This file is called first and contains the logic for user interaction – a TUI control panel
"""
import json
import os
import sys
import time
from pathlib import Path

from collections.abc import Sequence
from typing import TypedDict

import InquirerPy.inquirer as inquirer
import yaml
from rich import box
from rich.color import Color, ColorParseError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import soft
from autologin import set_login_false
from launcher import launch_all

console = Console()

COOKIES_DIR = Path(__file__).parent / "profiles"


class Account(TypedDict, total=False):
    email: str
    points: int
    login: bool
    proxy: str
    imapPassword: str


def update_login_status_from_cookies(profiles: list[Account]) -> None:
    for profile in profiles:
        email: str | None = profile.get("email")
        if not email:
            continue

        folder_name: str = email.replace("@", "_").replace(".", "_")
        folder_path = COOKIES_DIR / folder_name

        if not (folder_path.exists() and folder_path.is_dir()):
            set_login_false(email)
            profile["login"] = False


def safe_style(value: str | None, fallback: str = "magenta2") -> str:
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


def cls() -> None:
    _ = os.system("cls")


def select_menu(message: str, choices: list[str], default: str | None = None) -> str:
    return inquirer.select(
        message=message,
        choices=choices,
        default=default,
        pointer=">",
        instruction="",
        qmark="",
        amark="",
    ).execute()


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

                if email:
                    emails.append(str(email))
    return [e for e in (str(x).strip() for x in emails) if e]


def load_accounts_with_points(path: str = "profiles.json") -> list[Account]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    result: list[Account] = []
    if isinstance(data, list):
        for item in data:
            email = None
            points = 0
            login = True
            proxy = ""
            imapPassword = ""

            if isinstance(item, str):
                email = item
            elif isinstance(item, dict):
                email = item.get("email") or item.get("mail") or item.get("login")
                pts = item.get("points") or item.get("pts") or item.get("point")
                if isinstance(pts, (int, float)):
                    points = int(pts)
                elif isinstance(pts, str) and pts.isdigit():
                    points = int(pts)
                login_val = item.get("login", True)
                login = (
                    bool(login_val)
                    if not isinstance(login_val, str)
                    else login_val.strip().lower() not in ("false", "0", "no")
                )
                proxy = item.get("proxy", "")
                imapPassword = item.get("imapPassword", "")

            if email:
                result.append(
                    {
                        "email": str(email).strip(),
                        "points": points,
                        "login": login,
                        "proxy": proxy,
                        "imapPassword": imapPassword,
                    }
                )
    return result


def render_accounts_panel(accounts: Sequence[Account]) -> None:
    console = Console()
    frameColor = safe_style(config.get("frameColor"), "slate_blue3")
    pointsColor = safe_style(config.get("pointsColor"), "magenta2")

    accounts_sorted = sorted(accounts, key=lambda acc: not acc.get("login", True))

    table = Table(
        expand=True,
        box=box.SQUARE,
        show_edge=True,
        show_header=False,
        show_lines=False,
        border_style=frameColor,
    )
    table.add_column("", overflow="fold", justify="left", style="bold", ratio=1)
    table.add_column(
        "", overflow="fold", justify="left", style=f"bold {pointsColor}", ratio=1
    )

    for i, acc in enumerate(accounts_sorted, start=1):
        email = str(acc.get("email", ""))
        pts = str(acc.get("points", 0))
        login = acc.get("login", True)

        prefix = f"[black]{i}. [/black]"
        if not login:
            email = f"{prefix} [red]![/red] {email}"
        else:
            email = f"{prefix} {email}"

        table.add_row(email, pts)

    total_points = sum(int(acc.get("points", 0)) for acc in accounts)
    user = os.getlogin()

    panel = Panel(
        table,
        title=f"Greetings {user}! ({total_points})",
        padding=(1, 1),
        expand=True,
        box=box.ROUNDED,
        border_style=frameColor,
    )
    console.print(panel)


def show_accounts_menu() -> None:
    while True:
        cls()
        profiles = load_accounts_with_points()
        render_accounts_panel(profiles)
        emails = load_accounts()
        choices = emails + ["Back"] if emails else ["No profiles", "Back"]
        choice = select_menu(
            "? Choose profile:", choices, default=(emails[0] if emails else "Back")
        )
        cls()
        if choice == "Back":
            return
        if choice == "No profiles":
            continue

        console.print(f"Starting profile: {choice}", style=logColor)
        soft.run_profile(choice)


def show_farm_menu() -> None:
    while True:
        cls()
        profiles = load_accounts_with_points()
        render_accounts_panel(profiles)

        emails = (
            [email for a in profiles if (email := a.get("email")) is not None]
            if profiles
            else load_accounts()
        )

        if not emails:
            choice = select_menu("? No profiles", ["Back"], default="Back")
            cls()
            return

        # Compose choices
        choices = ["Run all"] + emails + ["Back"]
        choice = select_menu("? Start farming:", choices, default="Run all")

        cls()

        if choice == "Back":
            return
        elif choice == "Run all":
            profiles = load_accounts_with_points()
            render_accounts_panel(profiles)
            launch_all()
        else:
            console.print(f"Starting farming: {choice}", style=logColor)
            soft.run_farm_profile(choice)


def show_longfarm_menu() -> None:
    while True:
        cls()
        profiles = load_accounts_with_points()
        render_accounts_panel(profiles)
        emails = (
            [a.get("email") for a in profiles if "email" in a]
            if profiles
            else load_accounts()
        )

        if not emails:
            choice = select_menu("? No profiles", ["Back"], default="Back")
            cls()
            return

        choices = ["Run all"] + emails + ["Back"]
        choices = [c for c in choices if c is not None]
        choice = select_menu("? 24/7-часовой фарм:", choices, default="Запустить все")
        cls()

        if choice == "Back":
            return

        while True:
            if choice == "Run all":
                profiles = load_accounts_with_points()
                render_accounts_panel(profiles)
                print("[+] Starting 24/7 farming for all profiles...")
                launch_all()
            else:
                print(f"[+] Starting 24/7 farming for profile: {choice}")
                soft.run_farm_profile(choice)

            print("[✓] Cycle completed. Next run in 5 hours 5 minutes.")
            time.sleep(5 * 3600 + 5 * 60)


def main() -> None:
    while True:
        cls()
        profiles_raw = load_accounts_with_points()
        profiles: list[Account] = [
            {
                "email": d.get("email", ""),
                "points": int(d.get("points", 0)),
                "login": bool(d.get("login", True)),
                "proxy": d.get("proxy", ""),
                "imapPassword": d.get("imapPassword", ""),
            }
            for d in profiles_raw
        ]
        update_login_status_from_cookies(profiles)
        render_accounts_panel(profiles)

        choice = select_menu(
            f"? Select an action (use ↑↓ arrows):",
            [
                "Start farm",
                "Launch profile",
                "Start 24/7 farm",
                "Exit",
            ],
            default="Start farming",
        )
        cls()

        if choice.lower() == "Exit":
            break
        elif choice == "Launch profile":
            show_accounts_menu()
        elif choice == "Start farm":
            show_farm_menu()
        elif choice == "Start 24/7 farm":
            show_longfarm_menu()


if __name__ == "__main__":
    main()
