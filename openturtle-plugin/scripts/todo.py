#!/usr/bin/env python3
"""Todo 待办任务管理脚本。

通过 HTTP API 操作待办任务，agent 经 Bash 调用。

用法：
  python todo.py --base-url <url> --token <jwt> --project-id <id> <command> [options]

命令：
  list            查询我被指派的待办
  list-project    查看项目全部待办
  list-tasks      查询项目任务列表
  search-users    搜索用户
  get             查看待办详情
  create          创建待办
  update          修改待办
  update-status   更新状态
  delete          删除待办
  dispatch        下发给指定人员
  remind          催办
"""

import argparse
import json
import os
import sys
import ssl
import urllib.error
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


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _headers(token: str, auth_type: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if auth_type == "cookie":
        headers["Cookie"] = f"dfa_ee_cross_user={token}"
    else:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api(method: str, base_url: str, path: str, hdr: dict,
         body: dict | None = None) -> dict | list:
    url = f"{base_url}/api{path}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl._create_unverified_context()) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        err_text = ""
        if hasattr(e, 'read'):
            err_text = e.read().decode("utf-8", errors="replace")
        elif isinstance(e, urllib.error.URLError):
            err_text = str(e.reason)

        try:
            err_data = json.loads(err_text) if err_text else err_text
        except Exception:
            err_data = err_text

        error_type = "http_error" if isinstance(e, urllib.error.HTTPError) else "url_error"
        return {"_http_error": True, "status": getattr(e, 'code', 0),
                "type": error_type, "detail": err_data}


def _out(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _err(error: str) -> None:
    _out({"success": False, "error": error})
    sys.exit(1)


def _check(resp: dict) -> dict | None:
    if isinstance(resp, dict) and resp.get("_http_error"):
        _err(f"HTTP {resp['status']}: {json.dumps(resp['detail'], ensure_ascii=False)}")
        return None
    return resp


# ---------------------------------------------------------------------------
# 格式化
# ---------------------------------------------------------------------------

def _fmt_todo(t: dict) -> str:
    parts = [f"**{t.get('title', '?')}**"]
    if t.get("description"):
        parts.append(f"  描述：{t['description']}")
    parts.append(f"  状态：{t.get('status', '?')}")
    if t.get("assignee_id"):
        parts.append(f"  指派人：{t['assignee_id']}")
    if t.get("due_date"):
        parts.append(f"  截止日期：{t['due_date']}")
    if t.get("task_id"):
        parts.append(f"  关联任务：{t['task_id']}")
    parts.append(f"  ID：{t.get('id', '?')}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_list(args, hdr, base_url):
    params = []
    if args.status:
        params.append(f"status={args.status}")
    if args.page:
        params.append(f"page={args.page}")
    if args.page_size:
        params.append(f"page_size={args.page_size}")
    qs = "&".join(params)
    path = "/todos/" + (f"?{qs}" if qs else "")
    resp = _check(_api("GET", base_url, path, hdr))
    if not resp:
        return
    items = resp.get("items", [])
    if not items:
        _out({"success": True, "message": "暂无被指派给你的待办任务。"})
        return
    lines = [f"共 {resp.get('total', len(items))} 条待办：", ""]
    for t in items:
        lines.append(_fmt_todo(t))
        lines.append("")
    _out({"success": True, "todos": items, "total": resp.get("total", len(items)),
          "formatted": "\n".join(lines)})


def cmd_list_project(args, hdr, base_url):
    pid = args.project_id
    params = []
    if args.status:
        params.append(f"status={args.status}")
    if args.page:
        params.append(f"page={args.page}")
    if args.page_size:
        params.append(f"page_size={args.page_size}")
    qs = "&".join(params)
    path = f"/todos/projects/{pid}/todos" + (f"?{qs}" if qs else "")
    resp = _check(_api("GET", base_url, path, hdr))
    if not resp:
        return
    items = resp.get("items", [])
    if not items:
        _out({"success": True, "message": "该项目暂无待办任务。"})
        return
    lines = [f"项目共 {resp.get('total', len(items))} 条待办：", ""]
    for t in items:
        lines.append(_fmt_todo(t))
        lines.append("")
    _out({"success": True, "todos": items, "total": resp.get("total", len(items)),
          "formatted": "\n".join(lines)})


def cmd_list_tasks(args, hdr, base_url):
    pid = args.project_id
    params = []
    if args.status:
        params.append(f"status={args.status}")
    if args.page:
        params.append(f"page={args.page}")
    if args.page_size:
        params.append(f"page_size={args.page_size}")
    qs = "&".join(params)
    path = f"/projects/{pid}/tasks/" + (f"?{qs}" if qs else "")
    resp = _check(_api("GET", base_url, path, hdr))
    if not resp:
        return
    items = resp.get("items", [])
    if args.task_type:
        items = [t for t in items if t.get("task_type") == args.task_type]
    if not items:
        _out({"success": True, "message": "项目暂无任务。", "tasks": []})
        return
    result = []
    for t in items:
        result.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "status": t.get("status"),
            "task_type": t.get("task_type"),
        })
    _out({"success": True, "tasks": result, "total": resp.get("total", len(result))})


def cmd_search_users(args, hdr, base_url):
    params = []
    if args.keyword:
        params.append(f"keyword={args.keyword}")
    params.append(f"page={args.page or 1}")
    params.append(f"page_size={args.page_size or 20}")
    qs = "&".join(params)
    path = "/users/?" + qs
    resp = _check(_api("GET", base_url, path, hdr))
    if not resp:
        return
    items = resp.get("items", [])
    if not items:
        _out({"success": True, "message": "未找到匹配的用户。", "users": []})
        return
    result = []
    for u in items:
        result.append({
            "id": str(u.get("id", "")),
            "username": u.get("username", ""),
            "nickname": u.get("nickname", "") or u.get("display_name", ""),
            "email": u.get("email", ""),
        })
    lines = [f"共 {resp.get('total', len(result))} 个用户：", ""]
    for u in result:
        label = u["nickname"] or u["username"] or u["email"]
        lines.append(f"- {label}（用户名：{u['username']}）")
        lines.append(f"  assignee_id：{u['id']}")
    _out({"success": True, "users": result, "total": resp.get("total", len(result)),
          "formatted": "\n".join(lines)})


def cmd_get(args, hdr, base_url):
    resp = _check(_api("GET", base_url, f"/todos/{args.todo_id}", hdr))
    if not resp:
        return
    _out({"success": True, "todo": resp, "formatted": _fmt_todo(resp)})


def cmd_create(args, hdr, base_url):
    body = {
        "project_id": args.project_id,
        "title": args.title,
    }
    if args.description:
        body["description"] = args.description
    if args.assignee_id:
        body["assignee_id"] = args.assignee_id
    if args.due_date:
        body["due_date"] = args.due_date
    if args.task_id:
        body["task_id"] = args.task_id
    resp = _check(_api("POST", base_url, "/todos/", hdr, body))
    if not resp:
        return
    _out({"success": True, "todo": resp,
          "message": f"已创建待办：{resp.get('title', '')}，ID：{resp.get('id', '')}"})


def cmd_update(args, hdr, base_url):
    body = {}
    if args.title:
        body["title"] = args.title
    if args.description is not None:
        body["description"] = args.description
    if args.assignee_id:
        body["assignee_id"] = args.assignee_id
    if args.due_date:
        body["due_date"] = args.due_date
    resp = _check(_api("PATCH", base_url, f"/todos/{args.todo_id}", hdr, body))
    if not resp:
        return
    _out({"success": True, "todo": resp,
          "message": f"已更新待办：{resp.get('title', '')}"})


def cmd_update_status(args, hdr, base_url):
    body = {"status": args.status}
    resp = _check(_api("PATCH", base_url, f"/todos/{args.todo_id}/status", hdr, body))
    if not resp:
        return
    _out({"success": True, "todo": resp,
          "message": f"状态已更新为：{args.status}"})


def cmd_delete(args, hdr, base_url):
    resp = _check(_api("DELETE", base_url, f"/todos/{args.todo_id}", hdr))
    if not resp:
        return
    _out({"success": True, "message": f"已删除待办 {args.todo_id}"})


def cmd_dispatch(args, hdr, base_url):
    body = {"assignee_id": args.assignee_id}
    resp = _check(_api("POST", base_url, f"/todos/{args.todo_id}/dispatch", hdr, body))
    if not resp:
        return
    _out({"success": True, "todo": resp,
          "message": f"已下发给 {args.assignee_id}，对方会收到通知"})


def cmd_remind(args, hdr, base_url):
    resp = _check(_api("POST", base_url, f"/todos/{args.todo_id}/remind", hdr, {}))
    if not resp:
        return
    _out({"success": True, "message": f"已发送催办通知"})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COMMANDS = {
    "list": cmd_list,
    "list-project": cmd_list_project,
    "list-tasks": cmd_list_tasks,
    "search-users": cmd_search_users,
    "get": cmd_get,
    "create": cmd_create,
    "update": cmd_update,
    "update-status": cmd_update_status,
    "delete": cmd_delete,
    "dispatch": cmd_dispatch,
    "remind": cmd_remind,
}


def main():
    parser = argparse.ArgumentParser(description="Todo 待办任务管理脚本")
    # 通用参数（可选，自动从 session 加载）
    parser.add_argument("--base-url", default=None, help="API 服务地址（默认从 session 加载）")
    parser.add_argument("--token", default=None, help="JWT token 或 Cookie 值（默认从 session 加载）")
    parser.add_argument("--auth-type", choices=["jwt", "cookie"], default=None)
    parser.add_argument("--project-id", required=True, help="项目 ID")

    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="查询我被指派的待办")
    p_list.add_argument("--status")
    p_list.add_argument("--page", type=int)
    p_list.add_argument("--page-size", type=int)

    # list-project
    p_lp = sub.add_parser("list-project", help="查看项目全部待办")
    p_lp.add_argument("--status")
    p_lp.add_argument("--page", type=int)
    p_lp.add_argument("--page-size", type=int)

    # list-tasks
    p_lt = sub.add_parser("list-tasks", help="查询项目任务列表")
    p_lt.add_argument("--status")
    p_lt.add_argument("--task-type", help="按任务类型过滤: standard / retrospective")
    p_lt.add_argument("--page", type=int)
    p_lt.add_argument("--page-size", type=int)

    # search-users
    p_su = sub.add_parser("search-users", help="搜索用户")
    p_su.add_argument("--keyword")
    p_su.add_argument("--page", type=int)
    p_su.add_argument("--page-size", type=int)

    # get
    p_get = sub.add_parser("get", help="查看待办详情")
    p_get.add_argument("--todo-id", required=True)

    # create
    p_create = sub.add_parser("create", help="创建待办")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--description")
    p_create.add_argument("--assignee-id")
    p_create.add_argument("--due-date")
    p_create.add_argument("--task-id")

    # update
    p_update = sub.add_parser("update", help="修改待办")
    p_update.add_argument("--todo-id", required=True)
    p_update.add_argument("--title")
    p_update.add_argument("--description")
    p_update.add_argument("--assignee-id")
    p_update.add_argument("--due-date")

    # update-status
    p_us = sub.add_parser("update-status", help="更新状态")
    p_us.add_argument("--todo-id", required=True)
    p_us.add_argument("--status", required=True, choices=["pending", "in_progress", "completed"])

    # delete
    p_del = sub.add_parser("delete", help="删除待办")
    p_del.add_argument("--todo-id", required=True)

    # dispatch
    p_disp = sub.add_parser("dispatch", help="下发给指定人员")
    p_disp.add_argument("--todo-id", required=True)
    p_disp.add_argument("--assignee-id", required=True)

    # remind
    p_remind = sub.add_parser("remind", help="催办")
    p_remind.add_argument("--todo-id", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 自动加载 session（与 otcli.py 共享 ~/.openturtle/session.json）
    session = _load_session() or {}
    base_url = (args.base_url or session.get("base_url", "")).rstrip("/")
    token = args.token or session.get("token", "")
    auth_type = args.auth_type or session.get("auth_type", "jwt")
    if not base_url:
        _err("未指定 API 地址且无保存的 session。请先运行: python otcli.py auth login ...")
    if not token:
        _err("未指定 token 且无保存的 session。请先运行: python otcli.py auth login ...")

    hdr = _headers(token, auth_type)
    COMMANDS[args.command](args, hdr, base_url)


if __name__ == "__main__":
    main()
