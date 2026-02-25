<a id="readme-top"></a>
<div align="center">

# <img src="icons/juneai.png" width="32" /> JuneAI Soft

**Automated point farming for JuneAI · nodriver branch**

[![Python](https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white)](https://python.org)
[![Chrome](https://img.shields.io/badge/chrome-required-orange?logo=googlechrome&logoColor=white)](https://google.com/chrome)
[![License](https://img.shields.io/badge/license-MIT-green)](#)

</div>



> [!WARNING]
> Use at your own risk. During early testing **3 / 9 accounts were blocked** due to automation.



## What is this

Fully automated multi-account point farmer for **JuneAI**. This branch uses **nodriver** — an undetectable Chrome automation library that bypasses Cloudflare and other anti-bot systems.

- 🛡 Undetectable by anti-bot systems
- ⚡ Parallel multi-account farming
- 🔄 Auto text / image / video requests
- 📊 Live points tracking in TUI
- 🌐 Uses your installed Chrome — nothing extra to download

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Quick Start

**1.** Install [Python 3.13.3](https://python.org/downloads/) (add to PATH) and [Google Chrome](https://google.com/chrome)

**2.** Run `install.bat`

**3.** Add accounts to `src/profiles.json`:
```json
[
  {
    "email": "your@gmail.com",
    "points": 0,
    "login": false,
    "proxy": "",
    "imapPassword": ""
  }
]
```

**4.** Run `start.bat` → **Launch profile** → log in to each account

**5.** **Start farm** 🚀



## profiles.json

| Field | Description |
|:---|:---|
| `email` | June account email |
| `points` | Auto-updated points |
| `login` | Session state |
| `proxy` | Proxy (`--proxy-server` arg) |
| `imapPassword` | Gmail app password for auto-login |



## IMAP Auto-login (Gmail)

1. Enable [2FA](https://myaccount.google.com/security)
2. Create [App Password](https://myaccount.google.com/apppasswords)
3. Paste into `profiles.json` → `imapPassword`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Updating

Copy `src/profiles` folder to the new version to keep sessions.



## Configuration

Edit `config.yaml` to customize colors, thread count, delays.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Playwright vs nodriver

| | Playwright | nodriver |
|:---|:---:|:---:|
| Anti-detection | ❌ | ✅ |
| Browser install | Required | Uses Chrome |
| Cloudflare | ❌ | ✅ |


<p align="right">(<a href="#readme-top">back to top</a>)</p>

<details>
<summary><b>Project Structure</b></summary>

```
start.bat
config.yaml
src/
├─ main.py              # TUI menu
├─ soft.py              # Browser sessions & login
├─ profile_utils.py     # Proxy, profiles, logging
├─ launcher.py          # Parallel execution
├─ grind.py             # Farming automation
├─ imap.py              # Email code fetching
├─ config.py            # Config loader
├─ autologin/
│  ├─ auto_login.py     # Human-like clicks
│  ├─ email_input.py    # Email form input
│  └─ login_check.py    # Login state management
├─ prompts/
│  ├─ text.txt
│  ├─ images.txt
│  └─ videos.txt
├─ profiles/            # Session data
└─ profiles.json        # Account data
```

</details>


<details>
<summary><b>Notes</b></summary>

- Automation always carries risk
- Use fresh or warmed accounts
- Proxies recommended for large-scale usage
- Google Chrome must be installed

</details>



<div align="center">

⭐ If this helped you — star the repo

