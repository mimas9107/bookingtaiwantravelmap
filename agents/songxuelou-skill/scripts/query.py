#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error


def _base_url() -> str:
    url = os.environ.get("SONGXUELOU_URL", "").rstrip("/")
    if not url:
        print("error: SONGXUELOU_URL 未設定", file=sys.stderr)
        sys.exit(1)
    return url


def _get(path: str) -> dict:
    url = f"{_base_url()}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"連線失敗: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"錯誤: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_ping():
    data = _get("/api/ping")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_cache(meta_only: bool = False):
    if meta_only:
        data = _get("/api/latest-meta")
        meta = data.get("meta")
        if meta is None:
            print("無快取資料")
            return
        print(f"掃描時間: {meta['scanned_at']}")
        print(f"總掃描天數: {meta['total_days']}")
        print(f"有空房天數: {meta['available_days']}")
    else:
        data = _get("/api/latest")
        print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_query(date: str, detail: bool = False):
    path = f"/api/query?date={date}&rooms={1 if detail else 0}"
    data = _get(path)
    if data.get("in_cache") is False:
        print(f"⚠  該日 ({date}) 不在快取中，請先執行掃描")
        return
    if detail and "rooms" in data:
        rooms = data.pop("rooms", [])
        print(f"📅 {date} {'✅ 有空房' if data['available'] else '❌ 無空房'}")
        print(f"   可訂房數: {data['room_count']}")
        print(f"   掃描時間: {data['scanned_at']}")
        for r in rooms:
            icon = "✅" if r["available"] else "❌"
            print(f"   {icon} {r['name']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print("用法: query.py <ping|cache|query> [--meta|--rooms]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "ping":
        cmd_ping()
    elif cmd == "cache":
        meta_only = "--meta" in sys.argv[2:]
        cmd_cache(meta_only)
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("用法: query.py query YYYY-MM-DD [--rooms]", file=sys.stderr)
            sys.exit(1)
        date = sys.argv[2]
        detail = "--rooms" in sys.argv[3:]
        cmd_query(date, detail)
    else:
        print(f"未知子命令: {cmd}", file=sys.stderr)
        print("可用命令: ping, cache, query", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
