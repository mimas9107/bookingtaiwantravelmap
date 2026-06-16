import re
from datetime import datetime, timedelta

YEAR = datetime.now().year


def _resolve(m: int, d: int) -> str:
    dt = datetime(YEAR, m, d)
    if dt.date() < datetime.now().date():
        dt = datetime(YEAR + 1, m, d)
    return dt.strftime("%Y-%m-%d")


def parse(text: str) -> dict | None:
    t = text.strip()

    if t in ("/start", "/help", "help", "說明"):
        return {"action": "help"}

    if re.search(r"(快取|最近|現狀|狀況|latest|現況)", t):
        return {"action": "latest"}

    m = re.search(
        r"查\s*(\d{1,2})[/\-](\d{1,2})"
        r"\s*[到~\-]\s*"
        r"(\d{1,2})[/\-](\d{1,2})",
        t,
    )
    if m:
        return {
            "action": "scan",
            "start": _resolve(int(m.group(1)), int(m.group(2))),
            "end": _resolve(int(m.group(3)), int(m.group(4))),
        }

    m = re.search(r"查\s*(\d{1,2})[/\-](\d{1,2})", t)
    if m:
        return {
            "action": "rooms",
            "date": _resolve(int(m.group(1)), int(m.group(2))),
        }

    m = re.match(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", t)
    if m:
        return {"action": "rooms", "date": m.group(1).replace("/", "-")}

    return {"action": "help"}
