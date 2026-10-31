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

`ransomware_suspected` evidence also carries `suspended_process`, `suspended_pid`, `backup_age_days`.
Unknown types return `{"ok": true, "ignored": <type>}`. A `filter_added` that scores below 3 returns `level: "digest"` and opens no incident.

## 2. Other endpoints
- `POST /actions` `{incident_id, action, by, step}`; action = `remove_filter | make_private | contain_pc | release_pc | restore_files | ack | step_done | vendor_said_yes | vendor_said_no`. `release_pc` and `restore_files` are owner-only (`by` must equal `OWNER_CHAT_ID`, else 403); both return `queued: true`. `step_done` with `remove_attacker_rules` deletes the filters; `change_password*` applies the 2-step fix.
- `POST /heartbeat` `{device}` every 5 s; 15 s of silence raises `heartbeat_missing`.
- `GET /agent/commands?device=` returns and clears `{"commands": ["release" | "contain" | "restore"]}`.
- **Agent token:** when `AGENT_TOKEN` is set on the brain, `/heartbeat`, `/agent/commands` and every `/events` call with `source: "agent"` need the header `X-Agent-Token: <same value>`; otherwise 401 and a `rejected_agent` audit row. Sensors and Sahayak are not affected.
- `GET /graph`, `/paths`, `/incidents`, `/audit`, `/audit/verify`, `/console`, `GET /t/<token>`.

## 3. graph.json (`GET /graph`)
`{nodes: [{data: {id, label, kind: attacker|asset|jewel}}], edges: [{data: {id, source, target, ease, factors, verified, live}}], risk, open_paths, one_fix: {fix, text, risk_drop, paths_closed}}`

## 4. Incident JSON (`GET /incidents`, passed to `sahayak.notify.send_incident`)
`{id, title, severity: low|medium|high|critical, signals: [{type, entity, evidence, score?}], entities[], kinds[] (device|account|other), policy: auto|tap, status: open|closed, runbook[], done[], created, updated}`

Runbook steps: `contain_pc, save_evidence, confirm_with_owner, remove_attacker_rules, change_password | change_password_from_clean_device, sign_out_other_devices, check_payments, report`.

## 5. Merge rule
Two signals join one incident if they share an entity (after expanding accounts and devices to `person:<name>` via `PEOPLE` in `common/config.py`) and the incident was updated within 24 h. Email + PC in one incident raises severity one level.
