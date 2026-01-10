"""
This file contains the logic for modifying the 'login' setting in a profile
"""
import json
from pathlib import Path


def set_login_true(email: str) -> None:
    _set_login(email, True)

def set_login_false(email: str) -> None:
    _set_login(email, False)

def _set_login(email: str, value: str) -> None:
    path = Path(__file__).resolve().parent.parent / "profiles.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        data = []
        
    changed = False
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                em = item.get("email")
                if em and str(em).strip().lower() == email.strip().lower():
                    if item.get("login") != value:
                        item["login"] = value
                        changed = True
                    break
    if changed:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
