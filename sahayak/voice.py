"""Voice notes in Kannada / Hindi (Aradhya, Module D). gTTS makes an mp3; Telegram sends it as audio.
gTTS needs internet: test it on the venue Wi-Fi. A failed voice note never breaks the text alert."""
import os, tempfile, threading, requests
from common.config import TELEGRAM_TOKEN


def send_voice(chat_id, text, lang="kn"):
    if not TELEGRAM_TOKEN:
        print(f"[Sahayak] would send a {lang} voice note to {chat_id}")
        return
    path = None
    try:
        from gtts import gTTS
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        gTTS(text=text, lang=lang).save(path)
        with open(path, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendAudio",
                          data={"chat_id": chat_id, "title": "Sahayak voice note"}, files={"audio": f}, timeout=20)
    except Exception as e:
        print("[Sahayak] voice note failed:", e)
    finally:
        if path and os.path.exists(path):
            os.remove(path)


def send_voice_later(chat_id, text, lang="kn"):
    """Runs in the background so a slow voice note never delays the brain."""
    threading.Thread(target=send_voice, args=(chat_id, text, lang), daemon=True).start()
