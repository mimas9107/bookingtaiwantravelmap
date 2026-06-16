#!/usr/bin/env python3
"""
松雪樓儀表板 — 資料庫下載／上傳工具

Usage:
  ./scripts/db_tool.py download [--host URL] [-o FILE]
  ./scripts/db_tool.py upload <file> [--host URL]
  ./scripts/db_tool.py info [--host URL]

Examples:
  ./scripts/db_tool.py download
  ./scripts/db_tool.py download -o backup.db
  ./scripts/db_tool.py download --host http://localhost:8000
  ./scripts/db_tool.py upload ~/backup.db
  ./scripts/db_tool.py info
"""
import sys, os, argparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime


def _req(method: str, url: str, data: bytes | None = None,
         content_type: str | None = None):
    headers = {"User-Agent": "db_tool/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    return Request(url, data=data, headers=headers, method=method)


def _multipart(field: str, filename: str, data: bytes):
    """Build multipart/form-data body with a single file field."""
    import uuid
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, boundary


def cmd_download(host: str, output: str | None):
    api = f"{host.rstrip('/')}/api/db/export"
    try:
        with urlopen(_req("GET", api)) as resp:
            content = resp.read()
    except HTTPError as e:
        msg = e.read().decode(errors="replace") if e.code != 404 else "資料庫不存在"
        print(f"❌ 下載失敗 ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"❌ 無法連線至 {host}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if not output:
        today = datetime.now().strftime("%Y%m%d")
        output = f"songxuelou_scans_{today}.db"

    with open(output, "wb") as f:
        f.write(content)
    print(f"✅ 已下載 {len(content)} bytes → {output}")


def cmd_upload(host: str, filepath: str):
    if not os.path.exists(filepath):
        print(f"❌ 檔案不存在: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "rb") as f:
        data = f.read()

    fname = os.path.basename(filepath)
    body, boundary = _multipart("file", fname, data)
    api = f"{host.rstrip('/')}/api/db/import"
    try:
        with urlopen(_req("POST", api, body,
                          content_type=f"multipart/form-data; boundary={boundary}")) as resp:
            import json
            result = json.loads(resp.read())
    except HTTPError as e:
        msg = e.read().decode(errors="replace")
        print(f"❌ 上傳失敗 ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"❌ 無法連線至 {host}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ {result['message']}")


def cmd_info(host: str):
    api = f"{host.rstrip('/')}/api/latest-meta"
    try:
        with urlopen(_req("GET", api)) as resp:
            import json
            meta = json.loads(resp.read()).get("meta")
    except HTTPError as e:
        msg = e.read().decode(errors="replace") if e.code != 404 else "無資料"
        print(f"❌ 查詢失敗 ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"❌ 無法連線至 {host}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if not meta:
        print("ℹ️  資料庫為空（尚無掃描記錄）")
        return

    print(f"📊 資料庫狀態")
    print(f"   掃描時間: {meta['scanned_at']}")
    print(f"   總天數:   {meta['total_days']}")
    print(f"   可訂天數: {meta['available_days']}")


def main():
    p = argparse.ArgumentParser(description="松雪樓儀表板 — 資料庫下載／上傳工具")
    p.add_argument("--host", default="http://localhost:8000",
                   help="儀表板網址 (default: http://localhost:8000)")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("download", help="下載資料庫")
    d.add_argument("-o", "--output", help="儲存檔名 (default: songxuelou_scans_YYYYMMDD.db)")

    u = sub.add_parser("upload", help="上傳資料庫")
    u.add_argument("file", help="要上傳的 .db 檔案路徑")

    sub.add_parser("info", help="顯示資料庫摘要")

    args = p.parse_args()

    match args.command:
        case "download":
            cmd_download(args.host, args.output)
        case "upload":
            cmd_upload(args.host, args.file)
        case "info":
            cmd_info(args.host)


if __name__ == "__main__":
    main()
