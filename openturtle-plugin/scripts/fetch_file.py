#!/usr/bin/env python3
"""通过 API 获取项目工作区文件内容。

用法：
  python fetch_file.py \
    --base-url http://localhost:8000/api \
    --token <jwt_token> \
    --project-id <project_id> \
    --path "outputs/report.md"

  # Cookie 认证
  python fetch_file.py \
    --base-url http://localhost:8000/api \
    --token <cookie_value> \
    --auth-type cookie \
    --project-id <project_id> \
    --path "assets/cover.png" \
    --output cover.png
"""

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Session auto-loading (shared with otcli.py)
# ---------------------------------------------------------------------------

_SESSION_FILE = Path.home() / ".openturtle" / "session.json"


def _load_session() -> dict | None:
    if not _SESSION_FILE.exists():
        return None
    try:
        sessions = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
        return sessions.get("default")
    except (json.JSONDecodeError, OSError):
        return None


def _headers(token: str, auth_type: str) -> dict:
    headers = {}
    if auth_type == "cookie":
        headers["Cookie"] = f"dfa_ee_cross_user={token}"
    else:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _build_url(base_url: str, project_id: str, path: str) -> str:
    base = base_url.rstrip("/")
    encoded_path = urllib.parse.quote(path, safe="/")
    return f"{base}/api/strategic/projects/{project_id}/file?path={encoded_path}"


def fetch_file(
    base_url: str,
    token: str,
    auth_type: str,
    project_id: str,
    path: str,
    no_verify_ssl: bool = False,
) -> tuple[bytes, str, str]:
    """获取文件，返回 (content_bytes, content_type, filename)。"""
    url = _build_url(base_url, project_id, path)
    headers = _headers(token, auth_type)
    req = urllib.request.Request(url, headers=headers)

    ctx = None
    if no_verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, context=ctx) as resp:
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        disposition = resp.headers.get("Content-Disposition", "")
        filename = os.path.basename(path)
        if "filename=" in disposition:
            for part in disposition.split(";"):
                part = part.strip()
                if part.startswith("filename="):
                    filename = part.split("=", 1)[1].strip('"')
        data = resp.read()
    return data, content_type, filename


def main():
    parser = argparse.ArgumentParser(description="获取项目工作区文件")
    parser.add_argument("--base-url", default=None, help="API 地址（默认从 session 加载）")
    parser.add_argument("--token", default=None, help="JWT token 或 Cookie 值（默认从 session 加载）")
    parser.add_argument("--auth-type", default=None, choices=["jwt", "cookie"])
    parser.add_argument("--project-id", required=True, help="项目 ID")
    parser.add_argument("--path", required=True, help="相对于项目目录的文件路径")
    parser.add_argument("--output", "-o", help="保存到本地文件（不指定则输出到 stdout）")
    parser.add_argument("--no-verify-ssl", action="store_true", help="跳过 SSL 验证")
    parser.add_argument("--meta", action="store_true", help="输出 JSON 元信息而非文件内容")
    args = parser.parse_args()

    # 自动加载 session（与 otcli.py 共享 ~/.openturtle/session.json）
    session = _load_session() or {}
    base_url = (args.base_url or session.get("base_url", "")).rstrip("/")
    token = args.token or session.get("token", "")
    auth_type = args.auth_type or session.get("auth_type", "jwt")
    if not base_url:
        print(json.dumps({"error": True, "detail": "未指定 API 地址且无保存的 session。请先运行: python otcli.py auth login ..."}, ensure_ascii=False))
        sys.exit(1)
    if not token:
        print(json.dumps({"error": True, "detail": "未指定 token 且无保存的 session。请先运行: python otcli.py auth login ..."}, ensure_ascii=False))
        sys.exit(1)

    try:
        data, content_type, filename = fetch_file(
            base_url=base_url,
            token=token,
            auth_type=auth_type,
            project_id=args.project_id,
            path=args.path,
            no_verify_ssl=args.no_verify_ssl
        )
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"error": True, "status": e.code, "detail": body}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "detail": str(e)}, ensure_ascii=False))
        sys.exit(1)

    if args.meta:
        print(json.dumps({
            "filename": filename,
            "content_type": content_type,
            "size": len(data),
        }, ensure_ascii=False))
        return

    if args.output:
        with open(args.output, "wb") as f:
            f.write(data)
        print(json.dumps({
            "saved": args.output,
            "size": len(data),
            "content_type": content_type,
        }, ensure_ascii=False))
    else:
        if content_type.startswith("text/") or content_type in (
            "application/json", "application/xml", "application/javascript",
        ):
            sys.stdout.write(data.decode("utf-8", errors="replace"))
        else:
            sys.stdout.buffer.write(data)


if __name__ == "__main__":
    main()
