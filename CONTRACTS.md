# Shared contracts (owner: Aaron). Do not change without telling Aaron.

## 1. POST /events (every sensor)
```json
{"source": "gmail|drive|agent|honeytoken|sahayak|brain",
 "type": "<event type>", "entity": "<what it is about>", "evidence": {}, "ts": "ISO-8601 UTC"}
```
Build it with `common.contracts.make_event(source, type_, entity, evidence)`.

| type | sent by | entity example | evidence the brain reads | policy |
| --- | --- | --- | --- | --- |
| `filter_added` | Bruce (gmail) | `gmail:clinic` | `filter` = Gmail API filter dict (with `id`) | tap |
| `forwarding_added` | Bruce | `gmail:clinic` | address, pending/accepted | tap |
| `autoforward_on` / `sendas_added` | Bruce | `gmail:clinic` | `autoforward_on`: `{to: <address>}`; `sendas_added`: `{address: <address>}` (brain does not read these fields) | tap |
| `file_public` | Bruce (drive) | `file:<id>` | `file_id` | tap |
| `honeytoken_hit` | honeytoken route | `honeytoken:<token>` | planted_in, ip, user_agent | tap |
| `ransomware_suspected` | Ayan (agent) | `device:frontdesk-pc` | signals, contained, seconds_to_contain | **auto** |
| `heartbeat_missing` | brain | `device:<id>` | last_seen_seconds_ago | tap |
| `agent_stopping` | Ayan (agent, on Ctrl+C / SIGTERM) | `device:<id>` | contained | tap (merges; suppresses the later heartbeat alert) |
| `backup_old` | Ayan (agent, at start-up, backup > 7 days or missing) | `backup:<id>` | backup_age_days, folder | tap, severity low, **never merges** |
| `files_restored` | Ayan (agent, after a restore command) | `device:<id>` | files, from, ok | logged only, no incident |
| `bank_change_request` | Aradhya (sahayak) | `vendor:payment` (own entity, never merges with email/PC) | text | tap |
| `mail_download_on` | Bruce (gmail, POP or IMAP switched off -> on; first snapshot is the baseline) | `gmail:clinic` | pop, imap (true = just switched on) | tap, high; counts as a recent change |
| `pc_health` | Ayan (agent, `PC_HEALTH=1`, Windows, start-up + every 6 h) | `pchealth:<id>` | defender_on, realtime_on, signature_age_days, days_since_update | sets the graph's attacker->pc factor (0.1 healthy / 0.6 not); unhealthy (protection off, update > 30 days, signatures > 7 days) = low alert, never merges; healthy = logged only |

`ransomware_suspected` evidence `signals` may also carry `note` (a ransom-note file name) when the agent runs with `RANSOM_NOTES=1`.
A `filter_added` scoring 3-4 opens a **medium "ask"** incident (Sahayak type `filter_ask`: owner-only "Yes, it's mine" / "No, remove it"). A filter the owner confirmed returns `level: "confirmed"` and never opens an incident again.

`ransomware_suspected` evidence also carries `suspended_process`, `suspended_pid`, `backup_age_days`.
Unknown types return `{"ok": true, "ignored": <type>}`. A `filter_added` that scores below 3 returns `level: "digest"` and opens no incident.

## 2. Other endpoints
- `POST /actions` `{incident_id, action, by, step}`; action = `remove_filter | make_private | contain_pc | release_pc | restore_files | ack | step_done | vendor_said_yes | vendor_said_no`. `release_pc` and `restore_files` are owner-only (`by` must equal `OWNER_CHAT_ID`, else 403); both return `queued: true`. `step_done` with `remove_attacker_rules` deletes the filters; `change_password*` applies the 2-step fix. `rule_is_mine` (owner-only, else 403) removes only the incident's ask-level filter signals and remembers their ids; it closes the incident only if nothing else is left (a merged ransomware incident stays open). `called_it_helper` and `asked_vendor` are recorded only. Any action stops reminders for that incident.
- **Reminders:** an open high/critical incident nobody acted on is re-sent after 10 min with fixed words (no AI), at most twice; the second also tells `IT_CHAT_ID`. Audited as `reminder`.
- `GET /digest`: `{count, by_marker, latest}` for low-score rules (score and our marker labels only, never rule text).
- `POST /heartbeat` `{device}` every 5 s; 15 s of silence raises `heartbeat_missing`.
- `GET /agent/commands?device=` returns and clears `{"commands": ["release" | "contain" | "restore"]}`.
- **Agent token:** when `AGENT_TOKEN` is set on the brain, `/heartbeat`, `/agent/commands` and every `/events` call with `source: "agent"` need the header `X-Agent-Token: <same value>`; otherwise 401 and a `rejected_agent` audit row. Sensors and Sahayak are not affected.
- **Brain token:** when `BRAIN_TOKEN` is set, `POST /actions` and every `POST /events` with a source other than `agent` need the header `X-Brain-Token: <same value>` (use `common.config.brain_headers()`); otherwise 401 and a `rejected_call` audit row. Reads (`GET /incidents` etc.) stay open, so Ask Sahayak keeps its alert context. The honeytoken route posts internally and is not affected.
- `GET /graph`, `/paths`, `/incidents`, `/audit`, `/audit/verify`, `/console`, `GET /t/<token>`.
- `GET /mitre` (signal type -> MITRE technique, one map: `sahayak/ask.TECHNIQUE`); `GET /incidents/<id>/report` (incident, techniques, audit trail, verify). The report holds attacker-written evidence: for people only, never for Ask Sahayak or the AI.
- Repeat alerts: the same (type, entity, filter/file id) is sent to phones at most once per 10 min; repeats are audited as `notify_skipped`. Every send is audited as `notify` with per-phone ok/status.

### Filter score markers (`brain/scoring.py`; labels are fixed, Ask Sahayak's `KNOWN_MARKERS`/`MARKER_POINTS` must match)
sends mail outside / to another account +3 · forwards to an anonymous mailbox +1 · hides mail +2 · targets money or security words +2 (or targets a vendor's email +2, never both; `VENDOR_DOMAINS`) · hides and marks as read +1 (only with money/security words) · copies mail the clinic sends +2 · matches almost every email +1 · other risky change in the last 24 h +2 (forwarding/auto-forward/send-as changes and any rule scoring 3+). Levels: 5+ alert, 3-4 ask, below 3 digest.

## 3. graph.json (`GET /graph`)
`{nodes: [{data: {id, label, kind: attacker|asset|jewel}}], edges: [{data: {id, source, target, ease, factors, verified, live}}], risk, open_paths, one_fix: {fix, text, risk_drop, paths_closed}}`

## 4. Incident JSON (`GET /incidents`, passed to `sahayak.notify.send_incident`)
`{id, title, severity: low|medium|high|critical, signals: [{type, entity, evidence, score?}], entities[], kinds[] (device|account|other), policy: auto|tap, status: open|closed, runbook[], done[], created, updated}`

Runbook steps: `contain_pc, save_evidence, confirm_with_owner, remove_attacker_rules, change_password | change_password_from_clean_device, sign_out_other_devices, check_payments, report`.

## 5. Merge rule
Two signals join one incident if they share an entity (after expanding accounts and devices to `person:<name>` via `PEOPLE` in `common/config.py`) and the incident was updated within 24 h. Email + PC in one incident raises severity one level.
