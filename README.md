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

## Run it

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill it in (see below)
```

| Part | Command |
| --- | --- |
| Chakravyuh, the brain | `uvicorn brain.app:app --host 0.0.0.0 --port 8000`, then open `http://<ip>:8000/console` |
| Sensors | `python -m sensors.run` (needs `credentials.json` from Google Cloud) |
| PC agent | `python -m agent.testfolder make <folder>`, then `python -m agent.agent` as administrator (Linux: `sudo -E python -m agent.agent`) |
| Sahayak | `python -m sahayak.bot` |
| Tests | `python -m pytest tests -q` |
| Evaluation | `python -m eval.run_eval` |
| Demo reset | `python -m sensors.reset_gmail --yes` |

### Settings (`.env`)

Copy `.env.example` and fill in: the Telegram bot token and chat IDs (owner, staff, vendor, IT helper), the
brain's address, the shared secrets (`HMAC_SECRET`, `BRAIN_TOKEN`, `AGENT_TOKEN`), and optionally an
OpenAI-compatible AI endpoint (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) and contact names and phone numbers.
Everything works without the AI.

**Never commit `.env`, `credentials.json` or `token_*.json`.**

### Demo safety

- `agent.fake_ransomware` only runs in a folder containing `.chakravyuh_test_folder` (made by `agent.testfolder make`), and only scrambles copies.
- Keep `DRY_RUN=1` (firewall commands are printed, not run) until containment has been tested by hand.

## Tech stack

Python · FastAPI · python-telegram-bot · Google Gmail and Drive APIs · SQLite · networkx · watchdog · psutil ·
Groq API · pytest

## Team Incognito

Bruce Michael C · Aaron Darrel Dsouza · Ayan Karma Pradhan · Aradhya Kothari
