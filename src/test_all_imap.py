"""
Тест IMAP подключения для всех профилей из profiles.json
"""

import imaplib
import json
from pathlib import Path


def test_imap(
    email: str, password: str, imap_host: str = "imap.gmail.com", imap_port: int = 993
) -> dict:
    """Тестирует подключение к IMAP"""
    result = {
        "email": email,
        "password_preview": (
            f"{password[:4]}***{password[-2:]}" if len(password) > 6 else "***"
        ),
        "connection": False,
        "login": False,
        "emails_found": 0,
        "error": None,
    }

    if not password:
        result["error"] = "imapPassword is empty"
        return result

    try:
        # Подключение
        imap = imaplib.IMAP4_SSL(imap_host, imap_port)
        result["connection"] = True

        # Логин
        imap.login(email, password)
        result["login"] = True

        # Проверяем письма от Blockchain
        imap.select("INBOX", readonly=True)
        typ, data = imap.search(None, 'FROM "notify@wallet-tx.blockchain.com"')
        if typ == "OK":
            uids = data[0].split()
            result["emails_found"] = len(uids)

        imap.logout()

    except imaplib.IMAP4.error as e:
        result["error"] = f"IMAP: {e}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def main():
    # Читаем profiles.json
    profiles_path = Path("profiles.json")

    if not profiles_path.exists():
        # Пробуем в родительской папке
        profiles_path = Path("../profiles.json")

    if not profiles_path.exists():
        print("❌ profiles.json not found!")
        return

    try:
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to read profiles.json: {e}")
        return

    if not isinstance(profiles, list):
        print("❌ profiles.json must contain an array")
        return

    print("=" * 70)
    print("IMAP CONNECTION TEST FOR ALL PROFILES")
    print("=" * 70)
    print()

    total = 0
    success = 0
    failed = 0
    no_imap = 0

    for profile in profiles:
        if not isinstance(profile, dict):
            continue

        email = profile.get("email", "")
        imap_password = profile.get("imapPassword", "")

        if not email:
            continue

        total += 1

        if not imap_password:
            print(f"⚪ {email}")
            print(f"   └── No imapPassword configured")
            print()
            no_imap += 1
            continue

        result = test_imap(email, imap_password)

        if result["login"]:
            print(f"✅ {email}")
            print(f"   ├── Password: {result['password_preview']}")
            print(f"   └── Emails from Blockchain: {result['emails_found']}")
            success += 1
        else:
            print(f"❌ {email}")
            print(f"   ├── Password: {result['password_preview']}")
            print(f"   └── Error: {result['error']}")
            failed += 1

        print()

    # Итоги
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total profiles:     {total}")
    print(f"✅ Success:         {success}")
    print(f"❌ Failed:          {failed}")
    print(f"⚪ No IMAP config:  {no_imap}")
    print()

    if failed > 0:
        print("=" * 70)
        print("HOW TO FIX FAILED ACCOUNTS:")
        print("=" * 70)
        print(
            """
1. Open https://myaccount.google.com/security
2. Enable "2-Step Verification" if not enabled
3. Go to https://myaccount.google.com/apppasswords
4. Generate App Password for "Mail"
5. Copy 16-character password (like: abcd efgh ijkl mnop)
6. Update profiles.json with this password
        """
        )


if __name__ == "__main__":
    main()
