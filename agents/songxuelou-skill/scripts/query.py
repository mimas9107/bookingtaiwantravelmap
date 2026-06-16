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


def main():
    if len(sys.argv) < 2:
        print("用法: query.py <ping|cache> [--meta]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "ping":
        cmd_ping()
    elif cmd == "cache":
        meta_only = "--meta" in sys.argv[2:]
        cmd_cache(meta_only)
    else:
        print(f"未知子命令: {cmd}", file=sys.stderr)
        print("可用命令: ping, cache", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
