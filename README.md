# Chakravyuh + Sahayak — starter code (Team INCOGNITO)

Starter skeleton for the Kodikon 6.0 build. **Check the hackathon rules before using it:** if pre-written
code is not allowed, use this only as a study guide before the event and type your own version on the day.

| Folder | Owner | Run |
| --- | --- | --- |
| `brain/` | Aaron (B) | `uvicorn brain.app:app --host 0.0.0.0 --port 8000` then open `http://<ip>:8000/console` |
| `sensors/` | Bruce (A) | `python -m sensors.run` (needs `credentials.json` from Google Cloud) |
| `agent/` | Ayan (C) | `python -m agent.testfolder make <folder>` then `sudo -E python -m agent.agent` |
| `sahayak/` | Aradhya (D) | `python -m sahayak.bot` |
| `eval/` | Aaron (B) | `python -m eval.run_eval` |
| `tests/` | everyone | `python -m pytest tests -q` (21 tests: graph numbers, scoring, correlation, detector, signed buttons, messages, roles, Paisa Pause) |
| `common/` | everyone | settings (`config.py`) and the shared event format (`contracts.py`) |

Setup: `python -m venv .venv`, activate it, `pip install -r requirements.txt`, copy `.env.example` to `.env`
and fill it in. Never commit `.env`, `credentials.json` or `token_*.json`.

Demo safety: `agent.fake_ransomware` only runs in a folder containing `.chakravyuh_test_folder`
(created by `agent.testfolder make`). Keep `DRY_RUN=1` until you have tested containment by hand.

## Sahayak, the assistant (Module D, Aradhya Kothari)

The Telegram assistant: the only part of Ophanim the clinic's people see.

- **Plain-word alerts**: what happened, how serious, the next step; a jargon filter keeps technical words out of staff messages
- **Signed buttons**: HMAC-signed, one-time, 15-minute expiry; only the owner can reconnect the PC or restore files
- **Paisa Pause**: forward a "bank details changed" message and get "Don't pay yet", confirmed with the vendor on the saved number
- **Ask Sahayak**: questions in your own words, answered by RAG over 53 written guides (`sahayak/guides.md`), optional Groq LLM rewording, safety checks on every reply, and it still works with the AI off
- **Whom to call**: "call IT help", "owner number" or "who do I call" gives names and numbers from `.env` (never stored in the repo)
- Tests: `tests/test_sahayak.py` and `tests/test_ask_scenarios.py` (20 real-life scenarios: hacked email, ransomware, stolen bank details, OTP scams)
