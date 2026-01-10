# <img src="icons/juneai.png" width="20" /> June AI Soft

⚠️ **DISCLAIMER**  
By using this software, you take full responsibility for your actions.  
During early testing **3 out of 9 accounts were blocked due to automation**.  
Use this software **at your own risk**.

---

## 📦 Installation Guide

### 1️⃣ Install Python
Install **Python 3.13.3** and **make sure to add it to PATH**.

🔗 Download: https://www.python.org/downloads/

---

### 2️⃣ Install dependencies

After installing Python, run:

- `install.bat` — installs required Python dependencies  
- `install browser.bat` — installs the browser required for the software  

⚠️ **Both steps are mandatory**

---

### 3️⃣ Add accounts
Open the file:

```
src/profiles.json
```

Add emails associated with your **June** accounts.

---

### 4️⃣ First launch & login
Start the software **only via**:

```
start.bat
```

> Running without `start.bat` may cause library errors.

Steps inside the app:
1. Select **Launch profile**
2. Open each profile
3. Register or log in to the corresponding **June** account  
   - Profile email **must match** the June account email

---

### 5️⃣ Start farming
Once all profiles are logged in:
- Select **Start farm** from the menu

---

## ♻️ Updating the software (important)

To avoid re-login after updating to a new version:

```
Copy the folder:
src/profiles
```

Into the new version of the software.

📌 This folder contains **browser cookies** for each profile.

---

## 📄 profiles.json structure

Example:

```json
{
    "email": "aviasales@gmail.com",
    "points": 22491,
    "login": false,
    "proxy": "",
    "imapPassword": ""
}
```

### Field description:
- **email** — June account email (used for logging and IMAP auto-login)
- **points** — current points (auto-detected and updated)
- **login** — session state (used for auto-login)
- **proxy** — proxy settings  
  ⚠️ Barely tested — you may need to adjust logic (`soft.py`, line ~89)
- **imapPassword** — IMAP app password for auto-login

---

## ⚙️ Configuration

You can customize colors and some settings in:

```
config.yaml
```

---

## 📬 IMAP Auto-login Guide (Gmail)

Allows the software to automatically fetch login codes from email.

### Steps:
1. Enable **2FA**  
   https://myaccount.google.com/security

2. Create an **App Password**  
   https://myaccount.google.com/apppasswords  
   (Name can be anything)

3. Paste the generated password into:

```
src/profiles.json → imapPassword
```

---

## ❗ Notes
- Automation always carries risk
- Use fresh or warmed accounts
- Proxies are recommended for large-scale usage

---

## ⭐ Support
If this project helped you — consider starring the repository 🙂
