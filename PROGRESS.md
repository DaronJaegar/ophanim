# Chakravyuh + Sahayak — full progress report (Team INCOGNITO, Kodikon 6.0)

Prepared for: Aaron (Module B, brain + console + eval). Last updated: 2026-10-31.
Project folder: `C:\Users\aaron\Downloads\chakravyuh-starter\chakravyuh`
GitHub: https://github.com/DaronJaegar/ophanim (last push: commit `0429f95`; newer local files listed in section 9)
Plan file: `C:\Users\aaron\.claude\plans\c-users-aaron-downloads-03-setup-guide-lexical-whale.md`

---

## 1. Where the project is right now (short answer)

**Current phase: Phase 0, before the event (setup only). The event has not started.**
- Your code (Module B) is already at the level the docs ask for by Gate 2 *in the starter*: graph + Risk 12.45, scorer, correlation, audit chain, policy, heartbeat watcher, console. It is verified by tests and one smoke run, **but only in isolation** (no live Gmail, Telegram or real PC agent has touched it yet).
- The Phase 1 deliverables (Review 1: graph on projector with 12.45 / 4 open / closes 2) are met locally.
- Phase 2 onward needs teammates' credentials and hardware, and the event clock.
- Phase 0 items still open are all on the team/organiser side (rules, collaborators, credentials, hardware), plus 10 real Gmail filters for you.

### Phase checklist
| Phase | Gate | Status |
| --- | --- | --- |
| 0 Before event (setup only) | all four pass smoke test | **In progress** (Aaron's code part done; team/organiser items open) |
| 1 Brain alone + console (Sessions 1-2) | Review 1, 2:30 pm | Code ready, not rehearsed on a projector |
| 2 Golden path part 1, email (Session 3) | Gate 1, 7:30 pm | Not started (needs Bruce's Google + Aradhya's bot) |
| 3 Golden path part 2, PC + correlation (Session 4) | Gate 2, 2:30 am | Not started (needs Ayan's PC); merge logic itself verified |
| 4 Proof + Should features | Freeze 5:30 am | Eval sets A/B/C done; expert view etc. not started |
| 5 Freeze, reset, offline, dry runs | Dry runs 7:15 / 8:35 | Not started |
| 6 Final review + pitch | 9 am - 12 pm | Not started |

---

## 2. What the project is
Chakravyuh is a virtual security team for a small clinic. Four sensors send one event format to one brain (FastAPI + SQLite + networkx). The brain scores events, keeps an attack-path graph (Risk = sum over paths of product of edge eases x target value), merges email and PC alerts into one incident, and decides auto-vs-tap. Sahayak (Telegram bot) and a Cytoscape console are the outputs.
Golden path: Gmail filter -> red path -> fake ransomware on Priya's PC -> automatic containment -> one merged critical incident -> runbook in the right order -> all paths grey.
Key decisions from doc 01: ransomware is the only auto action; the PC contains itself with its own firewall (allow only the brain IP); no network gateway (cut); passwords are rotated from a clean device; deterministic detection, AI only rewords messages.

Team: Bruce = A (account sensors), Aaron = B (brain + console + eval), Ayan = C (PC agent), Aradhya = D (Sahayak + story).

---

## 3. Documents read (all seven now read in full)
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

## 4. What the starter code contains (per module, with state)
Run all commands from the project folder. `pytest` currently: **13 passed**.

### 4.1 Brain (Aaron) - `brain/`
- `app.py`: `POST /events`, `POST /actions`, `POST /heartbeat`, `GET /agent/commands`, `GET /graph`, `/paths`, `/incidents`, `/audit`, `/audit/verify`, `/console`, honeytoken router mount, background heartbeat watcher (5 s tick, 15 s silence = `heartbeat_missing`), Sahayak notifier plugged in at startup.
- `graph.py`: demo graph, Risk 12.45, `paths`, `one_fix` (greedy, deep-copies factor dicts), `mark_live` / `clear_live` (saves normal values in `orig`), `apply_fix`, `path_sentence`, `to_json`.
- `scoring.py`: filter markers (outside forward 3, hides mail 2, money/security words 2, catch-all 1, recent change 2); 5+ alert, 3-4 ask, <3 digest.
- `correlate.py`: entity expansion to `person:<name>` via `PEOPLE`, 24 h merge window, severity +1 for account+device, runbook ordering, `Incidents.public`.
- `audit.py`: SHA-256 hash chain in SQLite (`chakravyuh.db`), `verify`, `rows`.
- `console/index.html`: Cytoscape 3.28.1 from cdnjs, polls `/graph`, `/audit/verify`, `/incidents` every 2 s; red live edges, dashed unverified edges.
- `common/config.py` (env settings, `PEOPLE`), `common/contracts.py` (`make_event`).

### 4.2 Sensors (Bruce) - `sensors/`
`google_auth.py` (OAuth, scopes `gmail.settings.basic` + `drive.metadata.readonly`, write scope only for Make private), `gmail_watch.py` (snapshot/diff), `drive_watch.py` (changes API, public-file detection), `fixes.py` (`delete_filter`, `make_private`, evidence saved first, re-read to verify), `honeytoken.py` (`GET /t/<token>`, skips link-preview bots, generic login page), `pwned.py`, `run.py` (poll loop to the brain, Drive included).
State: **never run**; needs `credentials.json` and Google test users.

### 4.3 PC agent (Ayan) - `agent/`
`detector.py` (entropy, 2-of-3 rule, decoys, skip extensions), `contain.py` (nftables on Linux, netsh on Windows, DRY_RUN), `agent.py` (watchdog, heartbeat every 5 s, command poll every 3 s, fire = contain first then report), `fake_ransomware.py` (refuses without marker file), `testfolder.py` (make / restore), `upgrades.py` (`top_writer_now`, `backup_age_days`).
State: detector tests pass (3); containment never run for real; defaults to `DRY_RUN=1`.

### 4.4 Sahayak (Aradhya) - `sahayak/`
`signing.py` (HMAC buttons, 15 min expiry, one-time), `notify.py` (render, buttons, security code header, send to owner + staff), `bot.py` (taps, roles, `/start`, Paisa Pause regex, vendor check, runbook step buttons), `messages.py` (English templates; Hindi/Kannada for filter + ransomware only, drafts), `llm.py` (optional reword), `voice.py` (gTTS `send_voice`).
State: sahayak tests pass (4); bot never run against Telegram.

---

## 5. Work done in this session (Aaron's side), in order
### 5.1 Environment
- Tooling present: Python 3.13.3, git 2.52.0, Node 25.2.1, pip 26.1.
- Created `.venv`, installed all of `requirements.txt` on Python 3.13 with no errors.
- Baseline results: 11 tests passed; eval set A 15/15 caught, 0/20 false alarms at thresholds 3 and 4; 7/15 caught at threshold 5.

### 5.2 Analysis: gaps found in the starter (brain/integration)
1. Merged-incident "Remove it" never deleted the Gmail filter (merged view only has step-done buttons). **Fixed.**
2. `contain_pc` was never marked done, so ransomware incidents could not close. **Fixed.**
3. Honeytoken entity (`honeytoken:<token>`) has no person link, so a hit does not merge with Priya's incident. Left as is, documented in eval set C.
4. `@app.on_event("startup")` is deprecated in FastAPI (works; ignored).
5. Found after reading docs 04/06/07 (**new, not fixed**): see section 7.

### 5.3 Fixes made in `brain/app.py`
- New helper `_remove_filters(inc)`: runs Bruce's `delete_filter` for every filter in the incident, then clears the live Gmail edges (`attacker->gmail`, `gmail->invoices`) so paths go grey.
- `remove_filter` action uses the helper.
- `step_done` with `remove_attacker_rules` runs the helper once, then records the step; steps are no longer appended twice.
- On `ransomware_suspected`, `contain_pc` is marked done automatically (the agent already contained locally).

### 5.4 Tests added
`tests/test_brain_flow.py` (FastAPI TestClient, in-memory audit log, stubbed `sensors.fixes`):
- merged incident: remove step deletes filter `f1` and Gmail edges stop being live.
- ransomware incident: `contain_pc` is done and the incident closes after the other steps.
Totals: test_brain 4, test_brain_flow 2, test_detector 3, test_sahayak 4 = **13 passed**.

### 5.5 Smoke run of the brain (server started, then stopped, db deleted)
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

### 5.6 GitHub push
- `git init` in the project folder, remote `https://github.com/DaronJaegar/ophanim` (it held one commit: a one-line README, replaced by the project README).
- First push rejected (GH007, private email). Set this repo's local commit email to `DaronJaegar@users.noreply.github.com`, amended the commit, pushed. Commit `0429f95` is on `main`.
- Excluded: `.env`, `chakravyuh.db`, `.venv`, `.pytest_cache`, tokens, credentials (`.pytest_cache/` added to `.gitignore`).
- Commit carries the Co-Authored-By line for Claude.

### 5.7 Phase 0 files (local only, not pushed)
- `CONTRACTS.md`: event format, all event types with sender/entity/evidence/policy, endpoints, `graph.json`, incident JSON, runbook step names, merge rule.
- `eval/cases_pc.json` (set B, 10 scenarios): ransomware with decoy, ransomware without decoy, encrypt-in-place with decoy -> must fire; zip, backup copy of 50 files, bulk rename of 40 docs, rename 40 photos, edit 30 docs, extract 40 .7z, download 10 PDFs -> must not fire.
- `eval/cases_incidents.json` (set C, 9 pairs): merge at 5 min (both orders), merge at 23 h, no merge at 25 h, same account twice merges, different person's PC, two PCs, Drive file vs PC, honeytoken vs email -> no merge.
- `eval/run_eval.py` rewritten: prints sets A, B, C.
- Results: **A 15/15, 0/20 FA (th 3-4); B 10/10; C 9/9**. Caveat: B and C were written by me, so they are a sanity check, not independent proof.
- This `PROGRESS.md`.

---

## 6. Per-person status against their own docs (what each teammate still has to do)
### Bruce (A)
Needs: two Google accounts used for a day on both laptops; Cloud project with Gmail + Drive APIs; consent screen in Testing with test users; `credentials.json`; first sign-in producing `token_basic.json`; hand rehearsal of forwarding + filter; Patient records folder and 3 fake invoices; 2-step off on clinic account.
Code state: all listed files exist in the starter. Not yet present: `sensors/reset_gmail.py` (Level 2 upgrade, part of the one-command reset); SPF/DMARC check; honeytoken decoy doc/email not created.
Checks he owns: hand-made filter -> event in one poll; `forwarding_added` while pending; Remove it -> `verified: true`; public share -> alert -> Make private; honeytoken in browser alerts, in Telegram does not.
Reminders: 7-day token expiry (delete `token_basic.json` and re-consent on event morning); `POLL_SECONDS=10` for demo; credentials must sit on the brain laptop.

### Ayan (C)
Needs: Linux laptop/VM as front-desk PC; Python 3.11 + `watchdog`/`psutil`; `nftables`; test folder via `python -m agent.testfolder make`; hand-test the 7 nft commands (google fails, brain works, release restores) BEFORE `DRY_RUN=0`.
Code state: detector, containment, heartbeat, command loop, fake ransomware, upgrades all exist. Not yet wired: process suspension in `fire()` (commented out), `backup_age_days` call at startup, agent token (`X-Agent-Token`), `agent_stopping` event, extension-change signal, Windows service, install script.
To measure: median files locked and seconds to contain over 5 runs; the four false-trigger tests (zip, backup copy, 40 photo renames, 30 quick edits) - my set B covers these in simulation, but Ayan's real-folder runs are still needed.

### Aradhya (D)
Needs: BotFather token; chat IDs for owner/staff/vendor; `SECURITY_CODE`; long `HMAC_SECRET`; optional LLM key; 5 non-technical volunteers; native speaker for Hindi/Kannada; printed demo script and usability sheet.
Code state: signing, notify, bot, templates, Paisa Pause exist. Not yet wired / missing: voice notes are not called from `send_incident` (`send_voice` exists but is unused); Hindi/Kannada exist only for the filter and ransomware templates (the rest fall back to English); no `/lang`, `/setup` onboarding, photo invoices, weekly digest, report button, WhatsApp.
Checks: 4 sahayak tests pass; message headers; replayed tap rejected; staff Release refused; unknown phone refused; LLM off still works.

### Aaron (B)
Done: sections 5.3-5.7. Still to do: section 8.

---

## 7. New issues found after reading docs 04, 06, 07 (not fixed yet)
1. **FIXED (2026-10-31): `save_evidence` is now marked done automatically** in `post_event` (the event and its evidence are written to the audit log first); test `test_merged_incident_next_step_is_confirm_with_owner` added, 14 tests pass. Original problem: after my `contain_pc` fix, a merged incident's first Sahayak button becomes "Done: Save the evidence (done automatically)". The brain saves evidence inside `delete_filter`, but nothing marks the step. Fix idea: mark `save_evidence` done when an incident with an account signal opens (or when the filter evidence is written). Without it, staff must tap a step labelled "automatic".
2. **Voice notes are unwired**: `sahayak/notify.py` never calls `send_voice`, though doc 07 says to add it after `_send` for `kn`/`hi` chats. Aradhya's task, but affects the demo.
3. **Process suspension and backup-age check are not enabled** in `agent/agent.py` (Ayan's Level 3 items).
4. **Brain does not check `by` on actions other than `release_pc`**. The bot enforces allowlist/roles; doc 05 says the brain should also check the owner's ID for release (it does) - other actions are trusted from the bot.
5. **`confirm_with_owner` and `report` steps** have no brain-side effect; they only tick off (acceptable for the demo; incident closes only when all steps are tapped).
6. **No agent authentication** on `/heartbeat`, `/agent/commands`, `/events` (doc lists it as a Review 2 upgrade, STRIDE spoofing answer).
7. **Alert timing**: Bruce's loop polls every 30 s by default; the 45 s requirement needs `POLL_SECONDS=10` in `.env` for the demo.
8. **Containment on Windows**: Ayan's doc recommends Linux; the Windows netsh path is untested (and Windows Firewall must be on).
9. **Windows demo PC note**: `python.exe` is in `SAFE` in `upgrades.py`, so suspension would skip the fake ransomware process unless changed on the demo PC.

---

## 8. What is left for Aaron, by phase
### Phase 0 (now)
- [ ] Ask organisers: starter code allowed? setup before event allowed? hotspot allowed? (If code is not allowed, use the repo only as a study guide and retype on the day.)
- [ ] Add Bruce, Ayan, Aradhya as GitHub collaborators; each clones, makes venv, passes `pytest` and `python -m eval.run_eval`.
- [ ] Add 10 real filters from your own Gmail to `eval/cases_filters.json` (conditions only).
- [ ] Paper-check the 12.45 table; hand-compute 26.2 and 6.41.
- [ ] Share `CONTRACTS.md` in the team chat.
- [ ] Create `.env` from `.env.example` with the hotspot IP (`ipconfig`) as `BRAIN_URL` and `BRAIN_IP`; allow Python through Windows Firewall (Private).
- [ ] Decide on the `save_evidence` fix (section 7.1).
- [ ] Commit and push the local files (waiting for your go-ahead).
### Phase 1 (Review 1)
- [ ] Console polish: top 3 path sentences from `/paths`; node click showing factors.
- [ ] Rehearse the 30-second formula explanation and the architecture slide.
### Phase 2 (Gate 1)
- [ ] Pair with Bruce: real loop filter -> score -> incident -> Sahayak -> tap -> delete -> re-read -> grey.
- [ ] Onboarding baseline (existing filters treated as normal; Bruce's first-snapshot rule already does this at the sensor level).
- [ ] Venue benign baseline: alerts per hour (for the eval slide).
- [ ] Three clean runs, alert < 45 s, `/audit/verify` ok; tag `gate1`.
### Phase 3 (Gate 2)
- [ ] Agent -> brain with Ayan; contained < 10 s and still heartbeating; heartbeat-missing < 20 s joins the incident.
- [ ] Three clean kill-chain runs; tag `gate2`.
### Phase 4
- [ ] Expert view (MITRE IDs T1114.003, T1564.008, T1486, T1078, T1562.001), live audit panel, `GET /incidents/<id>/report`, "Next fix" after each fix.
- [ ] Re-run eval on all sets with real data; write numbers honestly.
### Phase 5
- [ ] One-command reset: delete `chakravyuh.db`, clear attacker filters, re-privatise files, restore test folder, release PC, reset graph/honeytokens.
- [ ] Offline test; two dry runs from reset; freeze at 5:30 am.
### Phase 6
- [ ] Rehearse demo (about 4 min) and CISO Q&A. You answer: architecture, scoring, graph, correlation, false positives, evaluation, "is it just an LLM wrapper?".

---

## 9. Files: pushed vs local
Pushed (commit `0429f95`): all starter code, `brain/app.py` fixes, `tests/test_brain_flow.py`, `.gitignore`.
Local only (not pushed): `CONTRACTS.md`, `eval/cases_pc.json`, `eval/cases_incidents.json`, updated `eval/run_eval.py`, this `PROGRESS.md`.

## 10. How to run
```
cd C:\Users\aaron\Downloads\chakravyuh-starter\chakravyuh
.venv\Scripts\activate
copy .env.example .env
python -m pytest tests -q
python -m eval.run_eval
uvicorn brain.app:app --host 0.0.0.0 --port 8000
```
Open `http://127.0.0.1:8000/console` and `/docs`. Delete `chakravyuh.db` between clean runs. Always run from the project root (not inside `brain/`).
Laptop roles on the day: Aaron = brain + `sensors.run` + `sahayak.bot` (holds credentials and tokens); Bruce = attacker laptop; Ayan = clinic PC (`sudo -E python -m agent.agent`); Aradhya = owner's phone.

## 11. Gate checklists (from the docs)
- Brain: graph prints 12.45; eval 15/15 and 0/20; invoice filter scores 7 with recent change (5 without); merge returns `merged: true`; unrelated device not merged; audit verify ok and tamper gives `broken_at`; killing the agent raises `heartbeat_missing` in < 20 s; risk after all fixes < start (6.41).
- Sensors: filter within one poll; `forwarding_added` while pending; Remove it -> `verified: true`; public share -> Make private; honeytoken browser vs Telegram.
- Agent: 3 detector tests; decoys planted; marker refusal; contained = google fails, brain works; release in 3-5 s; Ctrl+C -> alert < 20 s; zip/backup/40 photos/30 edits quiet; reset afterwards.
- Sahayak: 4 tests; code header; double tap rejected; staff Release refused; unknown phone refused; Remove it gone in Gmail; Paisa Pause "FAKE INVOICE" reaches owner; LLM off works; Kannada note plays.

## 12. Known limits of what has been verified
- Only the brain, the detector, signing/templates and the eval sets have been executed. Live Gmail/Drive, Telegram, real firewall containment and the hotspot network have not.
- Console loaded (HTTP 200) but not checked visually in a browser.
- Sets B and C are self-written sanity checks. Hindi/Kannada texts are unverified drafts.
