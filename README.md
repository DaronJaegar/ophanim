# Ophanim: a virtual security team for small businesses

**Team Incognito · Kodikon 6.0**

Small businesses and MSMEs, like shops, clinics, CA offices and small manufacturers, hold customer data and pay
vendors every week, but have no IT team. Ophanim watches their email, files and front-desk computer, stops
attacks on its own, and tells each person exactly what to do on Telegram, in plain words.

We demo it on a small clinic, because it has exactly four roles we can show on four phones: **owner, staff,
vendor and IT helper**.

## What it catches

| Threat | How Ophanim responds |
| --- | --- |
| Hidden email rules that forward or hide invoices | Scores the rule; 5+ points alerts, with a one-tap **Remove it** |
| Forwarding, send-as, POP/IMAP turned on by an attacker | Alerts the owner and staff |
| Private files shared with "anyone with the link" | Alerts, with a one-tap **Make it private** |
| Someone opening our hidden fake bank login (trap link) | Alerts: only an intruder would open it |
| Fake vendor bills ("our bank account changed") | **Paisa Pause**: "Don't pay yet", then confirms with the vendor on the saved number |
| Ransomware on the front-desk PC | Cuts the PC off in about 3 seconds and freezes the program doing it |
| The PC protection being switched off | Tamper alarm and heartbeat check |

## How it works

```
 Sensors (Gmail, Drive, traps) ─┐
                                ├─ events ─▶  Chakravyuh (the brain) ─ one incident ─▶  Sahayak (Telegram)
 PC agent (front-desk PC) ──────┘  ◀─ commands ─┘          ▲                               │
                                                           └──────── button taps ◀─────────┤
                                                                                           ▼
                                                                Owner · Staff · Vendor · IT helper
```

1. **Sensors** watch Gmail settings and Drive sharing every 10 to 30 seconds, and report anything new.
2. **The PC agent** watches files on the front-desk computer and acts on its own when ransomware starts.
3. **Chakravyuh**, the brain, joins related signs into one incident, decides how serious it is, and orders the fix steps.
4. **Sahayak**, the assistant, sends each person a plain message with one next step and signed buttons, and answers questions.

## The four parts

| Part | Folder | Built by | What it does |
| --- | --- | --- | --- |
| Sensors | `sensors/` | Bruce Michael C ([@bleng0](https://github.com/bleng0)) | Snapshots Gmail settings (rules, forwarding, auto-forward, send-as, POP/IMAP) and Drive sharing; trap links; one-tap fixes that save evidence first |
| Chakravyuh, the brain | `brain/`, `eval/` | Aaron Darrel Dsouza ([@DaronJaegar](https://github.com/DaronJaegar)) | Scores rules, merges incidents, runbooks, tamper-evident audit log, risk map, reminders, web console, evaluation sets |
| PC agent | `agent/` | Ayan Karma Pradhan | 2-of-3 ransomware rule, network containment, freezes the writing process, heartbeat, tamper alarm, restore from backup |
| Sahayak, the assistant | `sahayak/` | Aradhya Kothari ([@aradhy4](https://github.com/aradhy4)) | Telegram bot: plain-word alerts, HMAC-signed buttons, Paisa Pause, IT helper view, Ask Sahayak (RAG) |

### Sensors: scoring a new email rule

| Warning sign | Points |
| --- | --- |
| Sends mail outside, or to another account | 3 |
| Forwards to an anonymous mailbox | +1 |
| Hides mail (skip inbox, trash, spam, mark read) | 2 |
| Targets money or security words, or a known vendor's email | 2 |
| Copies mail the business sends | 2 |
| Another risky change in the last 24 hours | 2 |
| Matches almost every email | 1 |

**5 or more:** alert now. **3 to 4:** ask the owner "did you make this rule?". **Below 3:** quiet summary (`/digest`).

### Chakravyuh: joining the dots

- Signs about the same thing, or the same person (Priya's Gmail and Priya's PC), within 24 hours become **one incident**. Email plus PC raises it one severity level.
- Fix steps follow a safe order: cut off the PC first, save evidence, remove the attacker's rules, change the password **from a phone**, sign out other devices, check payments, report.
- Every event, alert and tap goes into a **tamper-evident log**: each row's SHA-256 includes the previous one, and `/audit/verify` shows where a chain breaks.
- An **attack-path risk map** shows how much each fix helps (demo: 12.45 → 6.41 with 2-step login → 1.81 with all fixes).

### PC agent: the 2-of-3 rule

| Sign | Counts when |
| --- | --- |
| Decoys touched | One of the hidden decoy files changes |
| Scrambled data | 5 files rewritten with entropy above 7.5 bits per byte |
| Rename burst | 20 renames, or 5 renames to an unusual extension like `.locked` |

Any 2 different signs within 60 seconds: the agent blocks all network traffic except to Chakravyuh (works offline),
freezes (not kills) the process writing the files, and reports. Only the owner can release the PC or restore files.

### Sahayak: Ask Sahayak (RAG)

1. **Guard rails:** refuses hacking requests, masks typed OTPs and passwords, sends general IT problems to the IT helper.
2. **Search:** BM25 over 53 written safety guides (`sahayak/guides.md`), with typo and synonym handling.
3. **AI wording (optional):** a Groq model (`openai/gpt-oss-20b`) rewords only the guides that were found.
4. **Safety check:** no dangerous advice (pay, share the OTP, switch off the PC), no jargon for staff, short replies. If a check fails or the AI is down, the guide's own text is sent.

Questions about the live alert ("what is happening to my system?") are answered from the alert's own data, never by the AI.
The AI never sees text an attacker wrote.

## Results

Run from the public code: `python -m pytest tests -q` and `python -m eval.run_eval`.

| Measure | Result |
| --- | --- |
| Set A: attack email rules caught (3+ points) | 24/24 |
| Set A: false alarms on normal rules | 0/39 |
| Set B: PC activity (ransomware vs zip, backup, bulk rename, edits) | 10/10 |
| Set C: incident joining (24-hour window, same person) | 9/9 |
| Time to cut off the PC | about 3 seconds |
| Automated tests | 135 passing |

Sets B and C were written by the team, so they are sanity checks rather than independent proof.

## Project structure

```
agent/      PC agent: ransomware detector, network containment, safe fake ransomware, install scripts
brain/      Chakravyuh: FastAPI app, incident joining, scoring, audit log, risk map, web console (brain/web)
common/     Shared settings (config.py reads .env) and the event format (contracts.py)
sahayak/    Telegram bot: alerts, signed buttons, Paisa Pause, Ask Sahayak (guides.md), voice notes
sensors/    Gmail and Drive watchers, trap links (honeytokens), one-tap fixes, demo data
eval/       Evaluation sets A, B, C and the runner
scripts/    reset_demo.py: one-command reset between demo runs
tests/      pytest suite
```

## Setup

### 1. Requirements

- Python 3.11 or newer
- A Telegram account (for the bot) and a Google account to act as the clinic's Gmail and Drive
- Windows or Linux for the PC agent (containment needs administrator / root rights)

### 2. Install

```bash
git clone https://github.com/DaronJaegar/ophanim.git
cd ophanim
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
```

### 3. Fill in `.env`

All settings live in `.env` (see `.env.example` for every key, with comments). The minimum to run:

| Setting | What to put |
| --- | --- |
| `BRAIN_URL`, `BRAIN_IP` | The brain laptop's address, e.g. `http://192.168.1.10:8000` (find it with `ipconfig` / `ip addr`). Use `127.0.0.1` if everything runs on one machine |
| `CLINIC_EMAIL` | The Gmail address the sensors watch |
| `TELEGRAM_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `OWNER_CHAT_ID`, `STAFF_CHAT_IDS`, `VENDOR_CHAT_IDS`, `IT_CHAT_ID` | Telegram chat IDs. Start the bot, send it `/start` from each phone, and it replies with that chat's ID. Vendors use `name:chat_id` |
| `HMAC_SECRET`, `BRAIN_TOKEN`, `AGENT_TOKEN` | Long random strings (no `#`). Use the same values on every laptop that runs a part |
| `SECURITY_CODE` | A code your team picks; never leave the default |
| `HONEY_TOKENS` | Two random tokens for the trap links, e.g. `decoy-doc:<random>,decoy-email:<random>` |

Optional: `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` for any OpenAI-compatible endpoint (we used Groq). Without
them Sahayak sends its written templates. Also optional: contact names and phone numbers (`OWNER_PHONE`, `IT_PHONE`, ...),
`VENDOR_DOMAINS`, and `CHAT_LANGS` for Hindi or Kannada chats.

To make a random secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 4. Google access (for the sensors)

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable the **Gmail API** and **Google Drive API**.
2. Set up the OAuth consent screen in **Testing** mode and add the clinic Gmail as a test user.
3. Create an **OAuth client ID** of type **Desktop app**, download it, and save it as `credentials.json` in the project folder.
4. The first run of the sensors opens a browser to sign in, then saves `token_basic.json`. In Testing mode this
   token expires after 7 days; delete it and sign in again.

Scopes used: `gmail.settings.basic` and `drive.metadata.readonly` for watching; full Drive access only for **Make it private**.

### 5. Run it

Start each part in its own terminal (all from the project folder, with the virtual environment active):

| Part | Command |
| --- | --- |
| Chakravyuh, the brain | `uvicorn brain.app:app --host 0.0.0.0 --port 8000`, then open `http://<ip>:8000/` (landing) or `/console` |
| Sensors | `python -m sensors.run` |
| Sahayak | `python -m sahayak.bot` (run on one machine only; Telegram allows one bot instance per token) |
| PC agent | `python -m agent.testfolder make <folder>`, then `python -m agent.agent` as administrator (Linux: `sudo -E python -m agent.agent`) |

The PC agent can also be installed on a separate Windows PC in one step, from an Administrator PowerShell:
`powershell -ExecutionPolicy Bypass -File agent\install.ps1 -BrainIp <brain ip>` (Linux: `agent/install.sh`).

### 6. Try the demo

| Step | How |
| --- | --- |
| Make demo files | `python -m sensors.demo_files` writes fake patient notes, invoices and decoy documents to `demo_files/` to upload to Drive |
| Bad email rule | In the clinic Gmail, add a filter that forwards invoice mail to an outside address, then tap **Remove it** on the phone |
| Public file | Share a Drive file with "anyone with the link", then tap **Make it private** |
| Fake vendor bill | Forward "our bank account has changed" to the bot to trigger Paisa Pause |
| Ransomware | `python -m agent.fake_ransomware <test folder>` (only works in a folder made by `agent.testfolder make`) |
| Reset | `python -m scripts.reset_demo --dry-run`, then `python -m scripts.reset_demo` |

Bot commands: `/start`, `/ask <question>`, `/status`, `/digest`, `/help`.

### 7. Tests and evaluation

```bash
python -m pytest tests -q
python -m eval.run_eval
```

### Demo safety

- `agent.fake_ransomware` only runs in a folder containing `.chakravyuh_test_folder` (made by `agent.testfolder make`), and only scrambles copies.
- Keep `DRY_RUN=1` (firewall commands are printed, not run) until containment has been tested by hand.
- **Never commit `.env`, `credentials.json`, `token_*.json` or `chakravyuh.db`.** They are listed in `.gitignore`.

## Tech stack

Python · FastAPI · python-telegram-bot · Google Gmail and Drive APIs · SQLite · networkx · watchdog · psutil ·
Groq API · pytest

## Team Incognito

Bruce Michael C · Aaron Darrel Dsouza · Ayan Karma Pradhan · Aradhya Kothari
