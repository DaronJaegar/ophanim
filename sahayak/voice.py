"""Voice notes in Kannada / Hindi / English (Aradhya, Module D). gTTS makes an mp3; Telegram sends it as audio."""
import tempfile, requests
from gtts import gTTS
from common.config import TELEGRAM_TOKEN

def send_voice(chat_id, text, lang="kn"):
    path = tempfile.mktemp(suffix=".mp3")
    gTTS(text=text, lang=lang).save(path)
    with open(path, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendAudio",
                      data={"chat_id": chat_id, "title": "Sahayak voice note"}, files={"audio": f}, timeout=20)
