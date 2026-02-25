"""
Utility functions for profile management, proxy configuration, and points logging
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from rich.color import Color, ColorParseError
from rich.console import Console

import config

console = Console()

# Gradient settings
color1 = "#f40752"
color2 = "#f9ab8f"
position = 0
direction = 1
steps = 40


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _interpolate(t: float) -> str:
    """Linearly interpolate between color1 and color2"""
    rgb1 = _hex_to_rgb(color1)
    rgb2 = _hex_to_rgb(color2)
    r = rgb1[0] + (rgb2[0] - rgb1[0]) * t
    g = rgb1[1] + (rgb2[1] - rgb1[1]) * t
    b = rgb1[2] + (rgb2[2] - rgb1[2]) * t
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def next_color() -> str:
    """Get next color in the repeating gradient cycle"""
    global position, direction

    t = position / steps
    color = _interpolate(t)

    position += direction
    if position >= steps:
        direction = -1
    elif position <= 0:
        direction = 1

    return color


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


def get_proxy_for_email(email: str) -> dict[str, str] | None:
    """
    Возвращает конфиг прокси для nodriver.
    Для nodriver прокси задаётся через browser_args.
    """
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
                    return {
                        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
                        "username": parsed.username or "",
                        "password": parsed.password or "",
                    }
    return None


def get_proxy_arg(email: str) -> str | None:
    """Возвращает строку для --proxy-server аргумента"""
    proxy = get_proxy_for_email(email)
    if proxy:
        return proxy["server"]
    return None


def profile_dir_for_email(email: str) -> str:
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

        difference = points - (prev_points or 0)
        color = next_color()
        console.print(
            f"[{color}]ASKJUNE[/{color}] {email} | [{color}]+{difference}[/{color}] pts"
        )


def load_profile_config() -> dict:
    """Загружает config.yaml"""
    import yaml

    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
