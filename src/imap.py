"""
This file handles all IMAP logic – it retrieves and returns codes from email
"""

import imaplib
import json
import os
import re
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

PROFILES_FILENAME = "profiles.json"


def _decode_payload(msg: email.message.Message) -> str:
    """Декодирует тело письма"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body += payload.decode(charset, errors="replace")
                except Exception:
                    pass
            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body += payload.decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
        except Exception:
            pass

    return body


def _decode_subject(msg: email.message.Message) -> str:
    """Декодирует тему письма"""
    subject = msg.get("Subject", "")
    if not subject:
        return ""

    try:
        decoded_parts = decode_header(subject)
        pieces = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                pieces.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                pieces.append(part)
        return "".join(pieces)
    except Exception:
        return str(subject)


def _get_password_for_email(email_addr: str, path: str = PROFILES_FILENAME) -> str:
    """Получает IMAP пароль из profiles.json"""
    profiles_path = Path(path)
    if not profiles_path.exists():
        raise RuntimeError(f"Profile file not found: {path}")

    with open(profiles_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        raise RuntimeError("profiles.json must contain an array of profiles")

    for p in data:
        if isinstance(p, dict) and p.get("email") == email_addr:
            return p.get("imapPassword", "")

    raise RuntimeError(f"Email {email_addr} not found in {path}")


def _parse_email_date(msg: email.message.Message) -> datetime | None:
    """Парсит дату письма в UTC"""
    date_str = msg.get("Date", "")
    if not date_str:
        return None

    try:
        dt = parsedate_to_datetime(date_str)
        # Конвертируем в UTC для сравнения
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def get_code(
    email_addr: str,
    sent_after: datetime | None = None,  # ← НОВЫЙ ПАРАМЕТР
    imap_host: str | None = None,
    imap_port: int | None = None,
    mailbox: str = "INBOX",
    sender: str = "notify@wallet-tx.blockchain.com",
    search_limit: int = 20,
    profiles_path: str = PROFILES_FILENAME,
) -> str | None:
    """
    Получает 6-значный код из письма.

    Args:
        email_addr: Email аккаунта
        sent_after: Искать только письма ПОСЛЕ этого времени (UTC)
        sender: От кого искать письмо

    Returns:
        6-значный код или None
    """
    imap_password = _get_password_for_email(email_addr, profiles_path)
    if not imap_password:
        raise RuntimeError(f"No imapPassword found for {email_addr}")

    imap_host = imap_host or os.getenv("IMAP_HOST") or "imap.gmail.com"
    imap_port = imap_port or int(os.getenv("IMAP_PORT") or 993)

    imap = imaplib.IMAP4_SSL(imap_host, imap_port)
    try:
        imap.login(email_addr, imap_password)

        status, _ = imap.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Failed to open mailbox {mailbox}")

        # Ищем письма от sender
        typ, data = imap.search(None, f'FROM "{sender}"')
        if typ != "OK":
            return None

        uids = data[0].split()
        if not uids:
            return None

        # Проверяем последние письма (от новых к старым)
        uids_to_check = uids[-search_limit:]

        for uid in reversed(uids_to_check):
            # Получаем полное письмо
            res, fetched = imap.fetch(uid, "(RFC822)")
            if res != "OK" or not fetched or not fetched[0]:
                continue

            raw_email = fetched[0][1]
            if not isinstance(raw_email, bytes):
                continue

            msg = email.message_from_bytes(raw_email)

            # ══════════════════════════════════════════════
            # КЛЮЧЕВОЕ: Проверяем дату письма
            # ══════════════════════════════════════════════
            if sent_after is not None:
                email_date = _parse_email_date(msg)

                if email_date is None:
                    # Не можем распарсить дату — пропускаем письмо
                    continue

                # Убеждаемся что sent_after тоже в UTC
                if sent_after.tzinfo is None:
                    sent_after = sent_after.replace(tzinfo=timezone.utc)

                # Пропускаем письма, отправленные ДО нажатия Continue
                if email_date < sent_after:
                    continue

            # Ищем код в Subject
            subject = _decode_subject(msg)
            if subject:
                m = re.search(r"\b(\d{6})\b", subject)
                if m:
                    return m.group(1)

            # Ищем код в Body
            body = _decode_payload(msg)
            if body:
                m = re.search(r"\b(\d{6})\b", body)
                if m:
                    return m.group(1)

        return None

    finally:
        try:
            imap.logout()
        except Exception:
            pass
