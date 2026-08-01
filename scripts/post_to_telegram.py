"""
Sends every pending Telegram notification message queued in
notify/telegram/pending/, then moves each sent file to
notify/telegram/sent/ so it's never sent twice.
Zero third-party dependencies (stdlib urllib only) so it runs on a bare
GitHub Actions ubuntu-latest runner with no pip install step.

Required environment variables (set as GitHub repo secrets):
  TELEGRAM_BOT_TOKEN   bot token issued by @BotFather
  TELEGRAM_CHAT_ID     numeric chat id to deliver messages to
"""
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

PENDING_DIR = Path("notify/telegram/pending")
SENT_DIR = Path("notify/telegram/sent")
API_BASE = "https://api.telegram.org"
MAX_LEN = 4000  # Telegram's hard limit is 4096 chars; stay safely under it


def send_message(token, chat_id, text):
    url = f"{API_BASE}/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"sendMessage failed: HTTP {e.code} {body}") from e


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — skipping.")
        return 0

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    SENT_DIR.mkdir(parents=True, exist_ok=True)

    pending = sorted(p for p in PENDING_DIR.glob("*.txt"))
    if not pending:
        print("No pending Telegram messages in queue. Nothing to do.")
        return 0

    for target in pending:
        text = target.read_text(encoding="utf-8").strip()
        if not text:
            print(f"Skipping empty file {target.name}")
            target.rename(SENT_DIR / target.name)
            continue
        if len(text) > MAX_LEN:
            text = text[: MAX_LEN - 1].rstrip() + "…"
        print(f"Sending {target.name} ({len(text)} chars)...")
        send_message(token, chat_id, text)
        target.rename(SENT_DIR / target.name)
        print(f"Moved {target.name} -> {SENT_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
