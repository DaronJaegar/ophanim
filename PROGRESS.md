# Chakravyuh + Sahayak — full progress report (Team INCOGNITO, Kodikon 6.0)

Prepared for: Aaron (Module B, brain + console + eval). Last updated: 2026-11-01 (night, before Gate 2).
Project folder: `C:\Users\aaron\Downloads\chakravyuh-starter\chakravyuh`
GitHub: https://github.com/DaronJaegar/ophanim (**public**). Everything is on `main` (latest pushes: Drive fixes `d30cc4b`, Aradhya's Ask Sahayak `7a5772f`, delivery audit `9281962`, Section A of the plan check). Always `git pull` first.
Plan file: `C:\Users\aaron\.claude\plans\c-users-aaron-downloads-03-setup-guide-lexical-whale.md`

---

## 1. Where the project is right now (short answer)

**Current phase: Phase 0, before the event (setup only). Close to done, not complete.**
- Module B (brain, console, eval) is at the level the docs ask for by Gate 2 *in the starter*: graph + Risk 12.45, scorer, correlation, audit chain, policy, heartbeat watcher, console. Verified by tests, eval and smoke runs, **but only in isolation** (no live sensor, bot or agent has posted to it yet).
- The team is now active on GitHub: Bruce pushed 3 sensor fixes, Aradhya pushed a large Sahayak update. All merged on `main`; **88 tests pass** (incl. Aradhya's 20 Ask Sahayak scenario tests).
- Real credentials now work on Aaron's laptop: Google OAuth (clinic account, Gmail + Drive read OK) and the Telegram bot token (`@sahayak_incognito_bot`, `getMe` OK).
- What still blocks the Phase 0 gate: chat IDs and honeytokens in `.env`, organiser answers, and each teammate's own smoke test (section 8).

### Next actions (2026-10-31 evening, in order)
State now: **Remove it worked on a real phone (2026-10-31 14:15 UTC run, see section 13)**; clinic Gmail has 0 filters (forwarding address still accepted, kept for reruns); Drive set up (Patient records, Invoices, Netbanking login, all private); decoy email sent; local `main` = GitHub + this file.
1. ~~Gate 1 core: Remove it on a real phone~~ **done**. Still to measure: seconds from Bruce creating the filter to the alert on the phone (< 45 s); confirm the phone said "We checked: it's gone" and the console path went grey.
2. Same session: tap **What does this mean? / Show me how / Call my IT helper**; forward "our bank account has changed" to the bot -> vendor taps **No** -> owner sees **FAKE INVOICE**; check the AI-worded alerts read well on the phone.
3. Repeat the email story 3 times from a clean reset; `git tag gate1`.
4. **Ayan:** send the `ALL PASS` screenshot; run the false-trigger tests (zip, backup copy, 40 photo renames, 30 quick edits) and 5 timed runs (median files locked + seconds to contain) in dry run; check the new meter, backup line, suspension and restore on Linux.
5. **Gate 2 (whole team):** `DRY_RUN=0` on Ayan's PC -> google blocked, brain reachable, contained < 10 s -> Release (back in 3-5 s) -> Restore; 3 full kill-chain runs; `git tag gate2`.
6. **Setup gaps:** ~~Drive upload + decoy email~~ done; confirm 2-step login is off; ask organisers (starter code, hotspot); share CONTRACTS.md.
7. **After the gates:** venue alerts-per-hour run, expert view (MITRE), reset script, offline test, dry runs, pitch rehearsal.

### Phase checklist
| Phase | Gate | Status |
| --- | --- | --- |
| 0 Before event (setup only) | all four pass smoke test | **Nearly done**: credentials, bot, chat IDs, vendor, honeytokens, AI wording, agent token all set; open: Drive upload, 2-step check, organiser answers, Ayan's ALL PASS screenshot |
| 1 Brain alone + console (Sessions 1-2) | Review 1, 2:30 pm | **Done** (console projector-ready, events from teammates' laptops); rehearsal left |
| 2 Golden path part 1, email (Session 3) | Gate 1, 7:30 pm | **Core done**: real filter (score 7) -> alert -> owner taps Remove it -> deleted + verified in Gmail. Left: timing, explanation buttons, Paisa Pause, 3 clean runs |
| 3 Golden path part 2, PC + correlation (Session 4) | Gate 2, 2:30 am | **In progress**: agent -> brain, heartbeat alert (16 s), email+PC merge, agent token all live in dry run; real containment not yet |
| 4 Proof + Should features | Freeze 5:30 am | Eval A/B/C done (A now 17 attacks / 32 normal); expert view done (MITRE + report); Ask Sahayak (RAG) merged; venue baseline not run |
| 5 Freeze, reset, offline, dry runs | Dry runs 7:15 / 8:35 | Not started |
| 6 Final review + pitch | 9 am - 12 pm | Not started |

---

## 2. What the project is
Chakravyuh is a virtual security team for a small clinic. Four sensors send one event format to one brain (FastAPI + SQLite + networkx). The brain scores events, keeps an attack-path graph (Risk = sum over paths of product of edge eases x target value), merges email and PC alerts into one incident, and decides auto-vs-tap. Sahayak (Telegram bot) and a Cytoscape console are the outputs.
Golden path: Gmail filter -> red path -> fake ransomware on Priya's PC -> automatic containment -> one merged critical incident -> runbook in the right order -> all paths grey.
Key decisions from doc 01: ransomware is the only auto action; the PC contains itself with its own firewall (allow only the brain IP); no network gateway (cut); passwords are rotated from a clean device; deterministic detection, AI only rewords messages.

Team: Bruce = A (account sensors), Aaron = B (brain + console + eval), Ayan = C (PC agent), Aradhya = D (Sahayak + story).

---

## 3. Documents read (all seven read in full)
| Doc | Read | Main content used |
| --- | --- | --- |
| 01 Final combined project | yes | architecture, kill chain, scoring, STRIDE, CISO table, demo script, cut list |
| 02 Event-day working plan | yes | gates, sessions, review playbooks, sleep shifts, risks, kit |
| 03 Setup guide | yes | per-person setup steps, laptop roles, team check |
| 04 Bruce (A) | yes | OAuth, snapshot/diff poller, fixes, Drive watcher, honeytokens, upgrades |
| 05 Aaron (B) | yes | graph/Risk, scoring, correlation, audit, heartbeat, evaluation, upgrades |
| 06 Ayan (C) | yes | entropy, 2-of-3 rule, containment, heartbeat, upgrades, measurements |
| 07 Aradhya (D) | yes | signed buttons, roles, templates, LLM, Paisa Pause, runbook chat, usability test |

---

## 4. What the code contains (per module, with state)
Run all commands from the project folder. `pytest`: **88 passed** (brain, brain flow, Drive, detector, Sahayak, Ask Sahayak scenarios). Eval: A **17/17 caught, 0/32 false alarms** at thresholds 3-4, B 10/10, C 9/9.

### 4.1 Brain (Aaron) - `brain/`
- `app.py`: `POST /events`, `POST /actions`, `POST /heartbeat`, `GET /agent/commands`, `GET /graph`, `/paths`, `/incidents`, `/audit`, `/audit/verify`, `/console`, honeytoken router mount, background heartbeat watcher (5 s tick, 15 s silence = `heartbeat_missing`), Sahayak notifier plugged in at startup. Aaron's fixes: section 5.3 and 7.1.
- `graph.py`: demo graph, Risk 12.45, `paths`, `one_fix` (greedy, deep-copies factor dicts), `mark_live` / `clear_live` (saves normal values in `orig`), `apply_fix`, `path_sentence`, `to_json`.
- `scoring.py`: filter markers (outside forward 3, hides mail 2, money/security words 2, catch-all 1, recent change 2); 5+ alert, 3-4 ask, <3 digest.
- `correlate.py`: entity expansion to `person:<name>` via `PEOPLE`, 24 h merge window, severity +1 for account+device, runbook ordering, `Incidents.public`.
- `audit.py`: SHA-256 hash chain in SQLite (`chakravyuh.db`), `verify`, `rows`.
- `console/index.html`: Cytoscape 3.28.1 from cdnjs, polls `/graph`, `/audit/verify`, `/incidents` every 2 s; red live edges, dashed unverified edges.
- `common/config.py` (env settings, `PEOPLE`; now also `IT_CHAT_ID`, `CLINIC_NAME`, `USED_TAPS_FILE`), `common/contracts.py` (`make_event`).

### 4.2 Sensors (Bruce) - `sensors/`
`google_auth.py` (OAuth, scopes `gmail.settings.basic` + `drive.metadata.readonly`, write scope only for Make private), `gmail_watch.py` (snapshot/diff), `drive_watch.py` (changes API, public-file detection), `fixes.py` (`delete_filter`, `make_private`, evidence saved first, re-read to verify), `honeytoken.py` (`GET /t/<token>`, skips link-preview bots, generic login page), `pwned.py`, `run.py` (poll loop to the brain, Drive included).
Bruce's fixes pushed 2026-10-31:
- `db2c8f3`: a 404 on filter delete counts as already removed (a second Remove it tap, or `remove_attacker_rules` after Remove it, used to give the brain a 500).
- `b27ad79`: the Gmail snapshot only advances after the brain accepts the event, so a brain restart or wrong `BRAIN_URL` no longer loses alerts; Drive errors can no longer block Gmail alerts.
- `3984ffe`: Drive watcher skips removed files / per-file permission errors instead of freezing the change token, and forgets a file once private so a second demo run alerts again.

State: **Google auth works on Aaron's laptop** (`credentials.json` for project `chakravyuh-demo`, Desktop-app client; `token_basic.json` signed in to the clinic account, matches `CLINIC_EMAIL`, has a refresh token; both git-ignored). Read-only check: Gmail 0 filters, 0 forwarding addresses (clean baseline at first). **Drive set up (2026-10-31, checked via API):** `Patient records/` (8 notes), `Invoices/` (3), `Netbanking login.pdf` at the top of My Drive; nothing shared publicly. Decoy email sent to the clinic inbox (confirmed by Aaron; the read-only scopes cannot see mail). Both decoy links point at `10.215.200.40`: rebuild + re-upload + resend on the event hotspot. `sensors.run` has not yet been run against the brain.
New `sensors/demo_files.py` (2026-10-31): `python -m sensors.demo_files` writes `demo_files/` (git-ignored): `Patient records/` with 8 fake patient notes, `Invoices/` with 3 fake vendor invoices, a decoy `Netbanking login.pdf` holding the decoy-doc honeytoken link, and `decoy_email.txt` with the decoy-email link. Every file is marked DEMO DATA; names and vendors are made up. Upload is manual: creating files would need the Drive write scope, which the design asks for only on the first "Make private" tap. **Re-run on event day** after `BRAIN_URL` changes to the hotspot IP, because the decoy links point at the brain.

### 4.3 PC agent (Ayan) - `agent/`
`detector.py` (entropy, 2-of-3 rule, decoys, skip extensions), `contain.py` (nftables on Linux, netsh on Windows, DRY_RUN), `agent.py` (watchdog, heartbeat every 5 s, command poll every 3 s, fire = contain first then report), `fake_ransomware.py` (refuses without marker file), `testfolder.py` (make / restore), `upgrades.py` (`top_writer_now`, `backup_age_days`).
State: detector tests pass (3); containment never run for real; defaults to `DRY_RUN=1`. No commits from Ayan on GitHub yet.
New `agent/hand_test_containment.sh` (2026-10-31): `sudo bash agent/hand_test_containment.sh <brain-ip>` runs the same 7 nft commands as `contain.py`, checks google.com fails and `<brain>/graph` still answers, and always deletes the table afterwards (also on Ctrl+C). Prints ALL PASS before Ayan sets `DRY_RUN=0`. Syntax-checked only; not run on Linux yet.
**Level 3 + upgrades written (2026-10-31, by Aaron for Ayan; Ayan to review and run on Linux):**
- `fire()`: contain first, then **suspend** the process writing most right now (`upgrades.top_writer_now`, frozen not killed; `SUSPEND=1`); event carries `suspended_process`, `suspended_pid`, `backup_age_days`.
- **Backup-age check** at start-up: prints the newest backup's age; older than 7 days (or missing) -> `backup_old` event (low, never merges).
- **Live signal meter** (`SIGNAL_METER=1`): one terminal line with 3 dots (decoy / random writes / renames) and `[watching | FIRED | CONTAINED]`; plain `[X]` fallback on consoles without Unicode.
- **Extension-change signal** in `detector.py`: 5 renames to an unusual extension (`.txt -> .locked`) count as a rename burst; familiar ones (`.jpeg -> .jpg`, Office `.tmp`) never count. 2-of-3 rule unchanged.
- **Agent token**: sends `X-Agent-Token` on every call when `AGENT_TOKEN` is set.
- **Tamper alarm**: Ctrl+C / SIGTERM posts `agent_stopping` before exiting.
- **Restore helper**: `restore` command copies `<WATCH_DIR>_backup` over the folder (refuses unless the backup holds the test marker), re-plants decoys, re-arms the detector, reports `files_restored`.
- `agent/install.sh <brain-ip> [--service]` (Linux, systemd) and `agent/install.ps1 -BrainIp <ip> [-Service]` (Windows, NSSM): syntax-checked only.
- Verified on Aaron's laptop (Windows, dry run, isolated brain): token rejects forged heartbeat (401); fake ransomware fired after 4 files (decoy + entropy); owner release; staff restore refused (403), owner restore put back 60 notes, 0 locked left; meter fallback works. Suspension not run on Windows (python.exe is SAFE there).

### 4.4 Sahayak (Aradhya) - `sahayak/`
Aradhya's update (`e2091ea`, merged in `9ac5b58`, 617 lines changed):
- `signing.py`: HMAC buttons, 15 min expiry, one-time; used taps now saved to `.sahayak_used_taps` (git-ignored) so one-time taps survive a bot restart; `reset_used()` for the reset script.
- `notify.py`: security code header, owner and staff copies differ, explain buttons; **voice notes now wired** (`send_voice_later` for `hi`/`kn` chats).
- `bot.py`: `/start`, button taps, text and **photo** messages, roles (owner / staff / vendor / IT helper / not set up), Paisa Pause, vendor check, runbook step buttons, "Call my IT helper" sends technical details to `IT_CHAT_ID`.
- `messages.py`: templates for every signal type; Hindi/Kannada for filter, ransomware, bank change and the merged incident (others English); step labels/texts/how/why; jargon check.
- `llm.py`: optional reword with 6 s timeout and safety check, falls back to the template.
- `voice.py`: gTTS, sent in the background.
- Tests: 4 -> 12 (one-time tap, tamper/expiry, owner vs staff copies, jargon, max 3 lines, every step has words, merged runbook walk-through, owner-only release, unsafe AI fallback, roles, Paisa Pause stays its own incident).

State: bot token valid; bot not yet run against the brain; chat IDs not yet in `.env`.

---

## 5. Work done (Aaron's side), in order
### 5.1 Environment
- Tooling: Python 3.13.3, git 2.52.0, Node 25.2.1, pip 26.1.
- `.venv` created, all of `requirements.txt` installed with no errors (re-checked: nothing missing; Aradhya's update added no packages).
- Baseline: 11 tests passed; eval set A 15/15 caught, 0/20 false alarms at thresholds 3 and 4.

### 5.2 Analysis: gaps found in the starter (brain/integration)
1. Merged-incident "Remove it" never deleted the Gmail filter. **Fixed.**
2. `contain_pc` was never marked done, so ransomware incidents could not close. **Fixed.**
3. Honeytoken entity (`honeytoken:<token>`) has no person link, so a hit does not merge with Priya's incident. Left as is, documented in eval set C.
4. `@app.on_event("startup")` is deprecated in FastAPI (works; ignored).
5. Issues found after reading docs 04/06/07: section 7.

### 5.3 Fixes made in `brain/app.py`
- New helper `_remove_filters(inc)`: runs Bruce's `delete_filter` for every filter in the incident, then clears the live Gmail edges (`attacker->gmail`, `gmail->invoices`) so paths go grey.
- `remove_filter` action uses the helper.
- `step_done` with `remove_attacker_rules` runs the helper once, then records the step; steps are no longer appended twice.
- On `ransomware_suspected`, `contain_pc` is marked done automatically (the agent already contained locally).
- `save_evidence` is marked done automatically in `post_event` (section 7.1).

### 5.4 Tests added
`tests/test_brain_flow.py` (FastAPI TestClient, in-memory audit log, stubbed `sensors.fixes`): merged remove deletes filter and greys Gmail edges; ransomware incident closes; merged incident's next step is `confirm_with_owner`.

### 5.5 Smoke run of the brain
| Check | Result |
| --- | --- |
| Initial graph | Risk 12.45, 4 open paths, fix "Turn on 2-step login for Priya" |
| Invoice-forwarding filter event | score 5, level alert, incident opened (7 needs the recent-change bonus) |
| Ransomware event on `device:frontdesk-pc` | merged, severity critical, title "Priya's email and her computer are both under attack" |
| Runbook | contain_pc > save_evidence > confirm_with_owner > remove_attacker_rules > change_password_from_clean_device > sign_out_other_devices > check_payments > report |
| Unrelated device | not merged |
| Risk during attack | 26.2 (matches doc) |
| `/audit/verify` | `{"ok": true}` |
| `/console` | HTTP 200 (not checked visually) |
Re-run 2026-10-31 evening after all merges: graph 12.45 / 4 open, `/audit/verify` ok, no incidents, console 200.

### 5.6 GitHub
- Repo `DaronJaegar/ophanim`; local commit email `DaronJaegar@users.noreply.github.com` (GH007 fix).
- Aaron's commits: `0429f95` starter + brain fixes; `eeba8fd` save_evidence fix, CONTRACTS.md, eval sets B and C, progress report; `32c8e96` 10 real Gmail filters in set A.
- All four team members are collaborators (confirmed by Aaron). Bruce and Aradhya have pushed; their branches `feature/sensors-gmail` and `aradhya/sahayak-improvements` are fully merged into `main`.
- Local `main` now tracks `origin/main` (plain `git pull` works).
- Never pushed: `.env`, `credentials.json`, `token_*.json`, `chakravyuh.db`, `.venv`, `.pytest_cache`, `.sahayak_used_taps`.

### 5.7 Phase 0 files
- `CONTRACTS.md`: event format, event types, endpoints, `graph.json`, incident JSON, runbook steps, merge rule.
- Eval set A: 15 bad filters vs 30 benign (20 starter + 10 real exported Gmail filters; account email not copied into the repo).
- `eval/cases_pc.json` (set B, 10 scenarios) and `eval/cases_incidents.json` (set C, 9 pairs); `eval/run_eval.py` prints A, B, C.
- Results (re-run after merges): **A 15/15 caught, 0/30 false alarms (thresholds 3-4); 7/15 at threshold 5. B 10/10. C 9/9.** Caveat: B and C were written by Aaron, so they are a sanity check, not independent proof.

### 5.8 Credentials and settings (2026-10-31)
| Item | State |
| --- | --- |
| `credentials.json`, `token_basic.json` | Working, clinic account, git-ignored (4.2) |
| `TELEGRAM_TOKEN` | Valid (`@sahayak_incognito_bot`) |
| `SECURITY_CODE` | Team-chosen code set (no longer the public `MANGO-42` default); value kept out of this public file |
| `HMAC_SECRET` | Long random value set, no `#` (the `env()` reader cuts at `#`) |
| `BRAIN_URL` / `BRAIN_IP` | `10.215.200.40` (current Wi-Fi). Redo whenever the network changes, and on the event hotspot (then re-run `python -m sensors.demo_files`, because the decoy links use it) |
| `IT_CHAT_ID` | **Set** (by Aaron, 2026-10-31) |
| `POLL_SECONDS` | **10** (demo speed). Note: an editor save once reverted `.env` (POLL back to 30, honeytokens back to CHANGE-ME); restored and honeytokens regenerated. Close `.env` without saving before editing elsewhere |
| `CHAT_LANGS` | **Empty on purpose: English only** for now (team decision 2026-10-31). Hindi/Kannada templates stay unused |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | **Set**: Groq, `openai/gpt-oss-20b` (reasoning model). Live test: 6/6 English alerts reworded in 0.9-2.0 s. Ransomware, agent-stopped and merged alerts are never reworded (`llm.NO_AI`) |
| Windows Firewall | Inbound Allow for Python 3.13 (Private, Public); venv python uses the same interpreter |
| `OWNER_CHAT_ID`, `STAFF_CHAT_IDS` | **Set** (owner = Aradhya, staff = Ayan, from the chats that messaged the bot). From now on every incident sends real Telegram messages to their phones. |
| `VENDOR_CHAT_IDS` | **Set** as `Nimbus Pharma:<chat id>` (format is `name:chat_id`; a bare number is read as empty) |
| `AGENT_TOKEN` | **Set and live on both sides** (Aaron's brain + Ayan's agent, same value, shared privately). Checked: no token 401, wrong token 401, right token 200; Ayan's agent shows `(agent token on)` with no refusals |
| `HONEY_TOKENS` | **Set**: two random 12-character tokens (decoy-doc, decoy-email). Brain restarted to load them |
| `IT_CHAT_ID`, `CLINIC_NAME` | New, optional; not in `.env` (defaults: empty, "Sunrise Clinic") |

### 5.9 Risk numbers paper-checked
- Start **12.45** = 4.03 (gmail->bank) + 3.02 (gmail->invoices) + 3.00 (drive) + 2.40 (pc).
- During attack **26.2** = 7.2 + 6.0 + 3.0 + 10.0 (attacker->gmail, gmail->invoices, attacker->pc, pc->records live).
- After the one fix (2-step login) **6.41** = 0.58 + 0.43 + 3.00 + 2.40.
- After all three fixes (2-step, make private, patch PC) **1.81**.
- Note: 6.41 is the Risk after the *one* fix, not after all fixes (corrected in section 11).

---

## 6. Per-person status (what each teammate still has to do)
### Bruce (A)
Done: Google Cloud project `chakravyuh-demo`, OAuth client, first sign-in on the brain laptop works; 3 sensor reliability fixes pushed.
Done: Drive demo data uploaded and decoy email sent (2026-10-31). Still needed: 2-step login off on the clinic account (myaccount.google.com -> Security; cannot be done or checked through the API); hand rehearsal of forwarding + filter; honeytoken decoy doc/email; `sensors/reset_gmail.py` (Level 2 upgrade); SPF/DMARC check.
Checks he owns: hand-made filter -> event in one poll; `forwarding_added` while pending; Remove it -> `verified: true`; public share -> alert -> Make private; honeytoken in browser alerts, in Telegram does not.
Reminders: 7-day token expiry in Testing mode (delete `token_basic.json` and sign in again on event morning); `POLL_SECONDS=10` for demo.

### Ayan (C)
Has messaged the bot (chat ID known). No commits yet.
Needs: Linux laptop/VM as front-desk PC (an Ubuntu 24.04 ISO and a Kali VirtualBox image are already in Aaron's Downloads if a VM is used); Python 3.11 + `watchdog`/`psutil`; `nftables`; `python -m agent.testfolder make`; hand-test the 7 nft commands with `agent/hand_test_containment.sh` BEFORE `DRY_RUN=0`; his own `.env` (`WATCH_DIR`, `DEVICE_ID`, `BRAIN_URL`/`BRAIN_IP`).
Code: all Level 3 items and upgrades are now written (section 4.3); Ayan should `git pull`, read them, and run them on the Linux PC. To turn on the agent token, put the same `AGENT_TOKEN` in the brain's and the agent's `.env` (leave both empty until then, or the agent is refused).
To measure: median files locked and seconds to contain over 5 runs; the four false-trigger tests on a real folder.

### Aradhya (D)
Done: BotFather token; Sahayak update pushed (4.4); voice notes wired; Hindi/Kannada extended; IT helper role.
Still needed: confirm owner/staff/vendor roles and send chat IDs (or confirm Aaron's plan); `CHAT_LANGS` for the Kannada/Hindi demo chat; optional LLM key; 5 non-technical volunteers; native speaker check of Hindi/Kannada; printed demo script and usability sheet.
Still missing in code: `/lang`, `/setup` onboarding, weekly digest, report button, WhatsApp.

### Aaron (B)
Done: sections 5.1-5.9. Still to do: section 8.

---

## 7. Issues found after reading docs 04, 06, 07
1. **FIXED:** `save_evidence` is marked done automatically in `post_event`; test added.
2. **FIXED by Aradhya (`e2091ea`):** voice notes are now sent from `notify.py` for `hi`/`kn` chats.
3. **Written (2026-10-31):** process suspension and backup-age check are in `agent/agent.py`; not yet run on Linux.
4. **Open:** the brain checks `by` only on `release_pc`; other actions are trusted from the bot (which enforces roles).
5. **Accepted:** `confirm_with_owner` and `report` only tick off; the incident closes when all steps are tapped.
6. **DONE (2026-10-31):** agent token (`AGENT_TOKEN` + `X-Agent-Token`) checked on `/heartbeat`, `/agent/commands` and agent `/events`; switched on for Aaron's brain and Ayan's agent; refusals tested (401) and logged as `rejected_agent`.
7. **Open:** `POLL_SECONDS=10` needed for the 45 s alert requirement.
8. **Open:** Windows containment path (`netsh`) is untested; Linux is the recommended demo PC.
9. **Open:** `python.exe` is in `SAFE` in `upgrades.py`, so suspension would skip the fake ransomware on a Windows PC.
10. **New:** the repo is public and `.env.example` now holds the real clinic Gmail address and a LAN IP (from `e2091ea`). No secrets leaked, but consider putting placeholders back or making the repo private if the organisers allow.
11. **New:** if two brain servers run at once (seen on ports 8000 and 8001), sensors and the agent may post to the wrong one. Run exactly one brain on 8000. "Errno 10048 ... only one usage of each socket address" means a brain is already running on 8000.
12. **New (found 2026-10-31):** the "one fix" only models prevention. During a live public share it still says "2-step login" (the incident's Make private button is the real answer), and with every edge live every fix drops Risk by 0. Idea: when the best drop is 0 or an incident is open, show "Follow the incident steps first".
13. **New:** a honeytoken hit marks Attacker -> Gmail, but the decoy doc lives in Drive; arguably it should mark Attacker -> Records folder. Decide with Bruce.
14. **FIXED:** CONTRACTS.md now lists `bank_change_request` with entity `vendor:payment`, plus the new `agent_stopping`, `backup_old`, `files_restored`, `restore_files` and the agent token.
15. **Note:** with the chat IDs set, every incident now sends real Telegram messages to Aradhya and Ayan. Warn them before tests.

---

## 8. What is left, by phase
### Phase 0 (now)
- [ ] Ask organisers: starter code allowed? setup before event allowed? hotspot allowed?
- [x] All four are GitHub collaborators and pushing code.
- [ ] Each teammate passes `pytest` and `python -m eval.run_eval` on their own laptop (Bruce and Aradhya clearly set up; Ayan not yet seen).
- [x] 10 real Gmail filters added to the benign list (now 30).
- [x] Paper-check 12.45, 26.2, 6.41 (and 1.81 after all fixes).
- [ ] Share `CONTRACTS.md` in the team chat.
- [x] `.env` created; firewall rule for Python present. (Brain IP to be redone on the hotspot.)
- [x] `save_evidence` fix.
- [x] Commit and push local files.
- [x] `credentials.json` + `token_basic.json` working on the brain laptop.
- [x] Telegram token, team `SECURITY_CODE`, random `HMAC_SECRET`.
- [x] `OWNER_CHAT_ID` (Aradhya) and `STAFF_CHAT_IDS` (Ayan) in `.env`.
- [x] `VENDOR_CHAT_IDS` set (`Nimbus Pharma:<chat id>`).
- [x] `IT_CHAT_ID` set.
- [x] `BRAIN_URL` / `BRAIN_IP` = current IP (`10.215.200.40`); `POLL_SECONDS=10`.
- [x] Random `HONEY_TOKENS` in `.env`.
- [x] Demo files generated (`python -m sensors.demo_files`).
- [x] Demo files uploaded to the clinic Drive (2 folders, 12 files, all private) and decoy email sent (2026-10-31).
- [ ] 2-step login off on the clinic account (manual, Google account settings).
- [x] Containment hand-test script written for Ayan.
- [x] Ayan's agent installed and reporting to the brain (first live event 2026-10-31 12:24 UTC, see section 13).
- [ ] Ayan's `hand_test_containment.sh` prints ALL PASS (not confirmed yet: ask for the screenshot).
- [x] Commit this updated `PROGRESS.md` (with the Phase 1 console changes).
### Phase 1 (Review 1)
- [x] Console polish (2026-10-31): "Top attack paths" list (top 3 open paths from `/paths`, with risk); click a box or arrow to see its factors, e.g. "breached password 0.8 × no 2-step login 0.7 = 0.56" (kept across the 2 s refresh). `/graph` edges now carry `factors` (CONTRACTS.md updated).
- [x] Projector check (headless Chrome, 1920x1080): graph now fits its panel, Attacker box no longer cut off, edge numbers readable, larger side text. Clean state shows 12.45 / 4 open / closes 2.
- [x] Event over the network IP (from Aaron's own laptop): filter event -> score 7 -> incident #1 high -> two red edges -> Risk 18.6; during the attack the one fix switches to "Make the records folder private" (2-step no longer helps once the attacker is inside). Reset to clean afterwards.
- [x] Events from teammates' laptops over the LAN: Bruce's `sensors.run` and Ayan's agent both posted to Aaron's brain at `10.215.200.40` (section 13). Repeat once on the event hotspot.
- [ ] Rehearse the 30-second formula explanation and the architecture slide (script given in chat 2026-10-31).
### Phase 2 (Gate 1)
Aradhya's Level 2 order (doc 07), mapped here. All four are **written in code; none has run live on real phones yet.**
Runs as three programs on Aaron's laptop: `uvicorn brain.app:app --host 0.0.0.0 --port 8000`, `python -m sensors.run`, `python -m sahayak.bot`. The brain sends the alerts itself (it loads `sahayak.notify` at startup); the bot is needed to receive taps.
- [x] Prerequisites: `POLL_SECONDS=10`; current IP in `.env`; attacker forwarding address **accepted** in the clinic Gmail. (Delete `chakravyuh.db` before each run.)
- [x] Detection half of item 1: Bruce's real filters reached the brain as `filter_added` and merged into the incident.
- [x] A signed button tap from a real phone reached the brain (Ayan tapped "Okay" on the ransomware alert -> `ack` in the audit log).
- [x] Demo filter now **skips the inbox** (scored 7 in the 14:15 run). Was: the current invoice filter only forwards, so it scores **5** ("sends mail to another account" 3 + "invoice" 2). With "Skip the Inbox (Archive it)" ticked it scores **7**.
- [x] **1. Taps do real things (critical). DONE 2026-10-31:** Aradhya tapped Remove it -> both attacker rules: evidence saved, deleted, re-read `verified: true`; Ayan's second tap on his copy hit Gmail's 404 and still reported removed. (Alert-time < 45 s still to be timed.) Bruce makes the invoice filter by hand -> `filter_added -> 200` -> console red, Risk 18.6 -> Aradhya's phone gets the alert -> she taps Remove it -> phone says "We checked: it's gone", filter gone from Gmail, path grey, `/audit/verify` ok. Code: `rm` -> `remove_filter` -> `delete_filter` (evidence, delete, re-read).
- [ ] **2. Explanation buttons** on real phones: What does this mean? / Show me how / Call my IT helper (the last needs `IT_CHAT_ID`).
- [ ] **3. Paisa Pause** on real phones: forward "our bank account has changed" -> "Don't pay yet" -> Check with the vendor -> vendor taps no -> owner sees "FAKE INVOICE" (needs `VENDOR_CHAT_IDS`). New (Aradhya, `0f62ad5`): if the attacker's mail rule is still open, the FAKE INVOICE message also has a signed **Remove it** button; otherwise only Call my IT helper. Test this too.
- [x] **4. AI wording:** Groq `gpt-oss-20b` set; reasoning-model support; safety-critical alerts never reworded (in testing the AI turned "cut the computer off" into "turned off her computer"); Markdown stripped for Telegram. Still to see on a real phone.
- [x] Languages: English only for now (decision); `CHAT_LANGS` left empty.
- [x] Onboarding baseline (Bruce's first-snapshot rule treats existing filters as normal).
- [x] Venue baseline tool: `python -m eval.venue_baseline [--since <ISO time>]` reads the audit log (read-only, safe while the brain runs) and prints alerts/asks per hour.
- [ ] Venue benign baseline measured: run brain + sensors during normal use only (no tests), then run the tool with `--since` the start time.
- [ ] Join-up: the full email story 3 times on real phones from a clean reset, alert < 45 s, `/audit/verify` ok; tag `gate1`.
### Session 4 (Drive + bait links) and plan check, Section A (2026-10-31 night)
- [x] Drive write token (`token_drive_write.json`) and Gmail baseline (`python -m sensors.reset_gmail --save`).
- [x] Drive test on real phones: share Patient records -> **one** alert (was 9: one per PDF) -> owner taps Make it private -> `verified: true` -> re-share alerts again. Owner delivery confirmed (`OWNER ...523 ok`).
- [x] Fixes behind it: files public only through their folder are skipped; Make it private on a file makes its folder private (Google refuses to remove an inherited link).
- [x] Every Telegram send is audited per phone (`notify` rows); `python -m eval.check_session4` shows them.
- [x] Same alert is not re-sent within 10 min (audited as `notify_skipped`); a new filter/file or an email+PC merge is always sent.
- [x] Failure replies no longer start with "Done." (`sahayak/bot.py`).
- [x] F1: Indian billing money words (gst, remittance, beneficiary, kyc, cheque, a/c, swift, imps, payout). Not "refund": it turned "archive Amazon refund mail" into a false alarm; that case stays in the eval as a guard.
- [ ] Bait-link test 4a/4b: open the decoy link in Chrome (1 hit, `decoy-email`); paste it **only into Telegram Saved Messages, never the bot chat** (the bot would send it to the AI via Ask Sahayak); hit count must not rise.
- [ ] Section B of the plan check: one item at a time, each needs Aaron's "go" (Windows hand test for Gate 2, reset script, BRAIN_TOKEN, ask level, digest, F2-F7, POP, /status, IT summary, reminders, link check, PC health).
- Note: Ayan's demo PC is **Windows** now (Linux is out); the Gate 2 hand test needs a Windows PowerShell version (Section B).
### Phase 3 (Gate 2)
- [x] Agent -> brain with Ayan (dry run): fake ransomware fired on decoy + entropy (2 of 3), incident #1 critical.
- [x] Agent stopped -> `heartbeat_missing` after 16 s, merged into the same incident (< 20 s target met).
- [x] Email + PC merge on live data: two real `filter_added` events joined incident #1 (PC first, then email).
- [x] Agent token on (brain + Ayan's agent): forged / wrong-token calls refused (401), real agent accepted.
- [ ] Real containment: `DRY_RUN=0` on Ayan's PC, google blocked, brain still reachable, contained < 10 s, still heartbeating.
- [x] Owner Release tap from a real phone reaches the brain (`release_pc` by Aradhya's chat, audit row 10; PC edges cleared). Dry run, so nothing was really cut off.
- [ ] Owner taps Release with `DRY_RUN=0` -> PC back online in 3-5 s.
- [ ] Three clean kill-chain runs; tag `gate2`.
### Phase 4
- [x] Expert view: console **Expert view** tick box shows MITRE IDs per incident (one map: `sahayak/ask.TECHNIQUE`, now with T1078) and links `GET /incidents/<id>/report` (incident + techniques + audit trail + verify). `GET /mitre`. The report holds attacker-written evidence: never fed to Ask Sahayak or the AI.
- [ ] Re-run eval on all sets with real data; write numbers honestly.
### Phase 5
- [ ] One-command reset: delete `chakravyuh.db`, clear attacker filters, re-privatise files, restore test folder, release PC, reset graph/honeytokens, `signing.reset_used()`.
- [ ] Offline test; two dry runs from reset; freeze at 5:30 am.
### Phase 6
- [ ] Rehearse demo (about 4 min) and CISO Q&A. Aaron answers: architecture, scoring, graph, correlation, false positives, evaluation, "is it just an LLM wrapper?".

---

## 9. Files: pushed vs local
All code is on `main`; check with `git status -sb` (should show no `ahead`/`behind`).
Local only, never pushed (git-ignored): `.env`, `credentials.json`, `token_basic.json`, `token_drive_write.json`, `gmail_baseline.json`, `chakravyuh.db`, `.venv`, `.pytest_cache`, `.sahayak_used_taps`, `demo_files/` (holds the honeytoken links).

## 10. How to run
```
cd C:\Users\aaron\Downloads\chakravyuh-starter\chakravyuh
.venv\Scripts\Activate.ps1
git pull
python -m pytest tests -q
python -m eval.run_eval
uvicorn brain.app:app --host 0.0.0.0 --port 8000
python -m sensors.run          # second terminal, polls the real clinic account
python -m sahayak.bot          # third terminal, needs chat IDs in .env
```
Open `http://127.0.0.1:8000/console` and `/docs`. Delete `chakravyuh.db` between clean runs. Always run from the project root (not inside `brain/`). Run only one brain at a time.
Laptop roles on the day: Aaron = brain + `sensors.run` + `sahayak.bot` (holds credentials and tokens); Bruce = attacker laptop; Ayan = clinic PC (`sudo -E python -m agent.agent`); Aradhya = owner's phone.

## 11. Gate checklists (from the docs)
- Brain: graph prints 12.45; eval 15/15 and 0 false alarms; invoice filter scores 7 with recent change (5 without); merge returns `merged: true`; unrelated device not merged; audit verify ok and tamper gives `broken_at`; killing the agent raises `heartbeat_missing` in < 20 s; Risk after the 2-step fix 6.41, after all three fixes 1.81 (both below 12.45).
- Sensors: filter within one poll; `forwarding_added` while pending; Remove it -> `verified: true`; public share -> Make private; honeytoken browser vs Telegram.
- Agent: 3 detector tests; decoys planted; marker refusal; contained = google fails, brain works; release in 3-5 s; Ctrl+C -> alert < 20 s; zip/backup/40 photos/30 edits quiet; reset afterwards.
- Sahayak: 12 tests; code header; double tap rejected (also after a bot restart); staff Release refused; unknown phone refused; Remove it gone in Gmail; Paisa Pause "FAKE INVOICE" reaches owner; LLM off works; Kannada note plays.

## 12. Known limits of what has been verified
- Executed: brain, detector, Sahayak unit tests, eval sets, Google auth (read-only calls), Telegram token (`getMe`), and the live run in section 13 (Bruce's sensors, Ayan's agent in dry run, a real phone tap).
- Not yet executed: a "Remove it" tap deleting a real filter, real firewall containment (`DRY_RUN=0`), owner Release, Paisa Pause with a vendor, the event hotspot.
- Console loaded (HTTP 200) but not checked visually in a browser.
- Sets B and C are self-written sanity checks. Hindi/Kannada texts are unverified drafts.

## 13. Live run log
### 2026-10-31, 12:24-12:28 UTC (17:54-17:58 IST): first multi-laptop run
Read from that run's audit log (`chakravyuh.db`, chain `{"ok": true}`, 9 rows):

| Row | What happened | Shows |
| --- | --- | --- |
| 1-2 | Ayan's agent: `ransomware_suspected` on `device:frontdesk-pc`, signals decoy + entropy (2 of 3), `contained: true` (dry run: commands printed, 0.0 s) -> incident #1 **critical** | Agent -> brain over the LAN works; detector fires on the real folder |
| 3 | `ack` by Ayan's chat (staff) on incident #1 | Alert reached a real phone; the signed tap reached the brain via `sahayak.bot` |
| 4-5 | `heartbeat_missing` after **16 s**, merged into #1 | Dead-agent detection < 20 s |
| 6-9 | Two real `filter_added` from Bruce's `sensors.run`, both merged into #1 | Gmail sensor -> brain works; email + PC merge on live data |
| 10 | `release_pc` by Aradhya's chat (owner) | Owner-only Release tap works from a real phone |

Not covered by this run: Remove it (both filters still in Gmail), the other owner steps, real containment.
Gmail now: forwarding address **accepted**; 2 filters: `invoice` -> forward (scores 5; add "skip inbox" for 7) and `from:no-reply@accounts.google.com` -> Trash (scores 4, "ask"). Drive: demo data uploaded (2 folders, 12 files, private).

### 2026-10-31, 14:15 UTC (19:45 IST): Remove it on a real phone
Audit log (`chakravyuh.db`, 14 rows, chain `{"ok": true}`):

| Row | What happened | Shows |
| --- | --- | --- |
| 1-4 | Bruce's two `filter_added` (14:15:01, 14:15:53): `invoice` -> forward (score 5), then `invoice` -> forward + skip inbox (**score 7**), one incident | Demo filter scores 7 |
| 5-9 | `remove_filter` by Aradhya (owner): for each rule `evidence` saved, `delete_filter`, re-read -> `verified: true` | **Gate 1 core: a tap deletes the real rule and checks it is gone** |
| 6-14 | `remove_filter` by Ayan (staff) on his copy: Gmail 404 treated as already removed, `verified: true` | Double taps are harmless (Bruce's 404 fix) |

The IT helper also received the technical details message for incident #1. Gmail afterwards: 0 filters; forwarding address still accepted (kept so the demo can be rerun).
Note: both owner and staff can tap Remove it; the first tap does the work, the second is a harmless no-op.

