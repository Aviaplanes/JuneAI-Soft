<a id="readme-top"></a>




# <img src="icons/juneai.png" width="40" /> JuneAI Soft

⚠️ **DISCLAIMER**  
By using this software, you take full responsibility for your actions.  
During early testing **3 out of 9 accounts were blocked due to automation**.  
Use this software **at your own risk**.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## About JuneAI Soft 

**JuneAI Soft** is a fully automated tool for farming points in the **JuneAI** project. Originally created for personal use, it is now shared on GitHub as a portfolio project. These points can potentially be used for project airdrops.

**Key features:**  
- Supports multiple accounts running in parallel.  
- Automates text, image, and video requests, creating new chats until points stop accumulating.  
- Tracks daily account limits automatically.  
- Displays up-to-date points for each account in a clean TUI table.  
- Switches seamlessly between different request modules for maximum efficiency.

**JuneAI Soft** saves time, simplifies multi-account management, and provides a transparent interface for point farming.

developed on Windows 10/11

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## 📦 Installation Guide

### 1️⃣ Install Python
Install **Python 3.13.3** and **make sure to add it to PATH**.

🔗 Download: https://www.python.org/downloads/

### 2️⃣ Install dependencies

After installing Python, run:

- `install.bat` — installs required Python dependencies  
- `install_browser.bat` — installs the browser required for the software  
- `cleanup.bat` — removes files and folders that are no longer needed after setup (readme, icons folder for github readme, changelog, ...)

⚠️ **Both steps are mandatory**

### 3️⃣ Add accounts
Open the file:

```
src/profiles.json
```

Add emails associated with your **June** accounts.

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

### 5️⃣ Start farming
Once all profiles are logged in:
- Select **Start farm** from the menu

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## ♻️ Updating the soft

To avoid re-login after updating to a new version:

```
Copy the folder:
src/profiles
```

Into the new version of the software.

📌 This folder contains **browser cookies** for each profile.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## 📄 profiles.json structure

Example:

```json
[
   {
       "email": "aviasales@gmail.com",
       "points": 22491,
       "login": false,
       "proxy": "",
       "imapPassword": ""
   },
   {
       "email": "aviasales2@gmail.com",
       "points": 222,
       "login": false,
       "proxy": "",
       "imapPassword": "abcd abcd abcd abcd"
   }
]
```

### Field description:
- **email** — June account email (used for logging and IMAP auto-login)
- **points** — current points (auto-detected and updated)
- **login** — session state (used for auto-login)
- **proxy** — proxy settings  
  ⚠️ Barely tested — you may need to adjust logic (`soft.py`, line ~89)
- **imapPassword** — IMAP app password for auto-login

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## ⚙️ Configuration

You can customize colors and some settings in:

```
config.yaml
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>



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

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## ❗ Notes
- Automation always carries risk
- Use fresh or warmed accounts
- Proxies are recommended for large-scale usage

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## 🗂️ Project Structure

Below is the folder and file structure of the JuneAI Soft project, with a brief description of each file:
```
start.bat          # Batch file to launch the soft with the virtual environment and settings
config.yaml        # Configuration: colors, thread count, delays
venv/              # Python virtual environment containing installed dependencies
src/
├─ main.py           # Entry point: TUI control panel, user interaction, account management
├─ soft.py           # Launches profiles, manages browser sessions, reads/updates points, handles auto-login
├─ launcher.py       # Runs multiple profiles in parallel with thread limits and delays
├─ grind.py          # Automates actions for points farming: text, image, video
├─ imap.py           # Fetches verification codes via IMAP for auto-login
├─ autologin/
│  ├─ __init__.py
│  ├─ auto_login.py   # Human-like clicks on login buttons
│  ├─ email_input.py  # Enters email in login forms
│  └─ login_check.py  # Sets 'login' status in profiles.json
├─ prompts/
│  ├─ text.txt        # Text prompts, 1 per line
│  ├─ images.txt      # Image prompts, 1 per line
│  └─ videos.txt      # Video prompts, 1 per line
├─ profiles/          # Contains profile folders with cookies/session data
└─ profiles.json      # Stores account info: email, points, login state, proxy, imapPassword
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## ⭐ Support
If this project helped you — consider starring the repository 🙂

<p align="right">(<a href="#readme-top">back to top</a>)</p>
