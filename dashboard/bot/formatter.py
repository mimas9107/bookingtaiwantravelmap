from datetime import datetime

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
NAME_LABEL = {"松雪樓精緻兩人房": "精緻雙人", "松雪樓景觀兩人房": "景觀雙人", "松雪樓四人房": "四人房"}


def _wd(ds: str) -> str:
    return WEEKDAYS[datetime.strptime(ds, "%Y-%m-%d").weekday()]


def _short(ds: str) -> str:
    d = datetime.strptime(ds, "%Y-%m-%d")
    return f"{d.month}/{d.day}"


def help_text() -> str:
    return (
        "🏔 <b>松雪樓空房查詢機器人</b>\n\n"
        "指令：\n"
        "  <code>查 7/1</code>         → 查詢單日房型\n"
        "  <code>查 7/1~7/5</code>     → 掃描日期區間\n"
        "  <code>快取</code> / <code>最近</code> → 讀取上次查詢結果\n"
        "  <code>help</code> / <code>說明</code>    → 顯示此訊息\n\n"
        "範例：<code>查 6/20~7/5</code>"
    )


def rooms(result: dict, changes: list = None) -> str:
    ds = result["date"]
    lines = [f"🏔 <b>松雪樓  {ds} ({_wd(ds)})</b>"]
    lines.append("─" * 16)
    change_map = {c["name"]: c for c in changes} if changes else {}
    for r in result.get("rooms", []):
        label = NAME_LABEL.get(r["name"], r["name"])
        c = change_map.get(r["name"])
        if r["available"]:
            seg = f"✅ {label}"
            if c:
                seg += " ⬇釋出" if not c["from"] else ""
        else:
            label = NAME_LABEL.get(r["name"], r["name"])
            seg = f"❌ <s>{label}</s>"
            if c:
                seg += " ⬆被訂" if c["from"] else ""
        lines.append(seg)
    if changes:
        lines.append("─" * 8)
        lines.append("🔄 較前次掃描有變動")
    return "\n".join(lines)


def scan(results: list) -> str:
    if not results:
        return "⚠️ 查無資料"

    start = results[0]["date"]
    end = results[-1]["date"]
    avail_days = [r for r in results if r["available"]]

    lines = [f"📅 <b>{_short(start)} ~ {_short(end)} 掃描結果</b>"]
    lines.append("─" * 16)

    row = []
    for r in results:
        ds = r["date"]
        d = datetime.strptime(ds, "%Y-%m-%d")
        change_mark = "🔄" if r.get("changes") else ""
        if r["available"]:
            badge = f"✅{r['room_count']}"
        else:
            badge = "❌"
        row.append(f"{d.month}/{d.day}({_wd(ds)}){badge}{change_mark}")

    lines.extend(row)
    lines.append("")
    total = len(results)
    lines.append(
        f"✅ {total} 天中 {len(avail_days)} 天有空房"
        if avail_days
        else "📭 全數售完"
    )
    return "\n".join(lines)


def latest(data: list, meta: dict | None) -> str:
    if not data:
        return "ℹ️ 資料庫為空，請先執行查詢"

    scanned_at = ""
    if meta and meta.get("scanned_at"):
        try:
            ts = datetime.fromisoformat(meta["scanned_at"].replace("Z", "+00:00"))
            scanned_at = f" (上次查詢: {ts.strftime('%m/%d %H:%M')})"
        except Exception:
            pass

    lines = [f"📊 <b>快取資料{scanned_at}</b>"]
    lines.append("─" * 16)
    row = []
    for r in data:
        ds = r["date"]
        d = datetime.strptime(ds, "%Y-%m-%d")
        change_mark = "🔄" if r.get("changes") else ""
        row.append(f"{d.month}/{d.day}({_wd(ds)}){'✅' if r['available'] else '❌'}{change_mark}")
    lines.extend(row)
    lines.append("")
    avail = sum(1 for r in data if r["available"])
    lines.append(f"✅ 共 {len(data)} 天，{avail} 天有空房")
    return "\n".join(lines)


def error(msg: str) -> str:
    return f"⚠️ 查詢失敗：{msg}"
