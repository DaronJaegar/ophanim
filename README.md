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
| `tests/` | everyone | `python -m pytest tests -q` (11 tests: graph numbers, scoring, correlation, detector, signed buttons) |
| `common/` | everyone | settings (`config.py`) and the shared event format (`contracts.py`) |

Setup: `python -m venv .venv`, activate it, `pip install -r requirements.txt`, copy `.env.example` to `.env`
and fill it in. Never commit `.env`, `credentials.json` or `token_*.json`.

Demo safety: `agent.fake_ransomware` only runs in a folder containing `.chakravyuh_test_folder`
(created by `agent.testfolder make`). Keep `DRY_RUN=1` until you have tested containment by hand.
