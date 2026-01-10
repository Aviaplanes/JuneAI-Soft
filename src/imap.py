"""
This file handles all IMAP logic – it retrieves and returns codes from email
"""
import imaplib
import json
import os
import re
from email.header import decode_header
from typing import Optional

PROFILES_FILENAME = "profiles.json"


def _decode_subject(raw_bytes: bytes) -> str:
    try:
        raw = raw_bytes.decode(errors="replace")
    except Exception:
        raw = raw_bytes.decode("utf-8", errors="replace")

    if raw.lower().startswith("subject:"):
        subj_raw = raw[len("Subject:") :].strip()
    else:
        subj_raw = raw.strip()

    parts = decode_header(subj_raw)
    pieces = []
    for bytes_part, charset in parts:
        if isinstance(bytes_part, bytes):
            try:
                pieces.append(bytes_part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                pieces.append(bytes_part.decode("utf-8", errors="replace"))
        else:
            pieces.append(bytes_part)
    return "".join(pieces)


def _get_password_for_email(email: str, path: str = PROFILES_FILENAME) -> str:
    if not os.path.exists(path):
        raise RuntimeError(f"Profile file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        raise RuntimeError("profiles.json must contain an array of profiles")

    for p in data:
        if isinstance(p, dict) and p.get("email") == email:
            return p.get("imapPassword")

    raise RuntimeError(f"Email {email} not found in {path}")


def get_code(
    email: str,
    imap_host: Optional[str] = None,
    imap_port: Optional[int] = None,
    mailbox: str = "INBOX",
    sender: str = "notify@wallet-tx.blockchain.com",
    search_limit: int = 100,
    profiles_path: str = PROFILES_FILENAME,
) -> Optional[str]:
    imap_password = _get_password_for_email(email, profiles_path)
    if not imap_password:
        raise RuntimeError(f"No imapPassword found for {email}")

    imap_host = imap_host or os.getenv("IMAP_HOST") or "imap.gmail.com"
    imap_port = imap_port or int(os.getenv("IMAP_PORT") or 993)

    imap = imaplib.IMAP4_SSL(imap_host, imap_port)
    try:
        imap.login(email, imap_password)

        status, _ = imap.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Failed to open email {mailbox}")

        typ, data = imap.search(None, f'FROM "{sender}"')
        if typ != "OK":
            return None

        uids = data[0].split()
        if not uids:
            return None

        uids_to_check = uids[-search_limit:]
        for uid in reversed(uids_to_check):
            res, fetched = imap.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
            if res != "OK" or not fetched or not fetched[0]:
                continue

            raw_header = fetched[0][1] or b""
            subject = _decode_subject(raw_header)
            m = re.search(r"(\d{6})", subject)
            if m:
                return m.group(1)
        return None
    finally:
        try:
            imap.logout()
        except Exception:
            pass
            