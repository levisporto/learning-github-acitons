#!/usr/bin/env python3
"""Send one motivational Telegram message, chosen by the local time of day.

Environment variables:
  TELEGRAM_BOT_TOKEN  bot token from @BotFather (required to send)
  TELEGRAM_CHAT_ID    your chat id (required to send)
  TZ_NAME             IANA timezone, default America/Fortaleza
  ACTIVE_START        first local hour that sends, default 6
  ACTIVE_END          last local hour that sends, default 22
  DRY_RUN             set to 1 to print the message instead of sending
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

EMOJI = {"morning": "🌅", "midday": "☀️", "afternoon": "⚡", "evening": "🌙"}


def slot_for(hour: int) -> str:
    if hour < 12:
        return "morning"
    if hour < 15:
        return "midday"
    if hour < 19:
        return "afternoon"
    return "evening"


def pick_message(now: datetime, messages: dict) -> tuple[str, str]:
    """Rotate through the slot's messages plus the 'anytime' pool.

    The index moves by one each hour and by three each day, so the same
    message never appears twice in a row and each day starts somewhere new.
    """
    slot = slot_for(now.hour)
    pool = messages[slot] + messages.get("anytime", [])
    index = (now.toordinal() * 3 + now.hour) % len(pool)
    return slot, pool[index]


def send(token: str, chat_id: str, text: str) -> None:
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")
        sys.exit(f"Telegram rejected the message: HTTP {err.code} {detail}")
    except urllib.error.URLError as err:
        sys.exit(f"Could not reach Telegram: {err.reason}")
    if not body.get("ok"):
        sys.exit(f"Telegram rejected the message: {body}")


def main() -> None:
    tz = ZoneInfo(os.environ.get("TZ_NAME") or "America/Fortaleza")
    start = int(os.environ.get("ACTIVE_START") or 6)
    end = int(os.environ.get("ACTIVE_END") or 22)
    now = datetime.now(tz)

    if not start <= now.hour <= end:
        print(f"{now:%H:%M} is outside {start}:00-{end}:59, nothing sent.")
        return

    messages = json.loads(
        (Path(__file__).parent / "messages.json").read_text(encoding="utf-8")
    )
    slot, message = pick_message(now, messages)
    text = f"{EMOJI[slot]} {message}"

    if os.environ.get("DRY_RUN") == "1":
        print(f"[dry run {now:%Y-%m-%d %H:%M} {slot}] {text}")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        sys.exit("Set the TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID secrets.")
    send(token, chat_id, text)
    print(f"Sent ({slot}): {text}")


if __name__ == "__main__":
    main()
