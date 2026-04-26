#!/usr/bin/env python3
"""OpenTurtle Admin CLI -- 完整后台管理工具（Plugin 版）。

涵盖所有 API 端点的 CLI 管理工具，基于表驱动的资源注册架构。
支持自动 session 持久化、Cookie/JWT 双认证、SSE 流式输出。

用法:
    # 首次登录（自动保存 session）
    python otcli.py auth login --base-url URL --username USER --password PASS

    # 后续操作自动复用 session，无需再传 --base-url/--token
    python otcli.py workflow list
    python otcli.py task list --project-id 123
    python otcli.py task stream --project-id 123 --task-id 456
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

SESSION_DIR = Path.home() / ".openturtle"
SESSION_FILE = SESSION_DIR / "session.json"


def save_session(base_url: str, token: str, auth_type: str = "jwt",
                 profile: str = "default") -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    sessions: dict = {}
    if SESSION_FILE.exists():
        try:
            sessions = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            sessions = {}
    sessions[profile] = {
        "base_url": base_url.rstrip("/"),
        "token": token,
        "auth_type": auth_type,
    }
    SESSION_FILE.write_text(json.dumps(sessions, indent=2, ensure_ascii=False),
                            encoding="utf-8")


def load_session(profile: str = "default") -> dict | None:
    if not SESSION_FILE.exists():
        return None
    try:
        sessions = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        return sessions.get(profile)
    except (json.JSONDecodeError, OSError):
        return None


def resolve_connection(args: argparse.Namespace) -> tuple[str, str, str]:
    base_url = getattr(args, "base_url", None)
    token = getattr(args, "token", None)
    auth_type = getattr(args, "auth_type", None) or "jwt"
    session = load_session()
    if session:
        base_url = base_url or session.get("base_url")
        token = token or session.get("token")
        if not auth_type or auth_type == "jwt":
            auth_type = session.get("auth_type", "jwt")
    if not base_url:
        print("错误: 未指定 API 地址且无保存的 session。请先登录:")
        print("  python otcli.py auth login --base-url <url> --username <user> --password <pass>")
        sys.exit(1)
    return base_url, token or "", auth_type


# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------

class ApiClient:
    """轻量 HTTP 客户端，支持 JWT/Cookie 双认证。"""

    def __init__(self, base_url: str, token: str = "", auth_type: str = "jwt"):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.auth_type = auth_type

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if not self.token:
            return headers
        if self.auth_type == "cookie":
            headers["Cookie"] = f"dfa_ee_cross_user={self.token}"
        else:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self, method: str, path: str,
        body: dict | None = None, params: dict | None = None,
    ) -> tuple[int, dict]:
        qs = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}/api{path}{qs}"
        data = json.dumps(body).encode() if body else None
        headers = self._auth_headers()
        req = Request(url, data=data, headers=headers, method=method)
        try:
            ctx = ssl._create_unverified_context()
            resp = urlopen(req, timeout=30, context=ctx)
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
        except HTTPError as e:
            try:
                raw = e.read().decode()
                return e.code, json.loads(raw) if raw else {"detail": str(e)}
            except Exception:
                return e.code, {"detail": str(e)}

    def get(self, path: str, params: dict | None = None) -> tuple[int, dict]:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict | None = None) -> tuple[int, dict]:
        return self._request("POST", path, body)

    def patch(self, path: str, body: dict | None = None) -> tuple[int, dict]:
        return self._request("PATCH", path, body)

    def put(self, path: str, body: dict | None = None) -> tuple[int, dict]:
        return self._request("PUT", path, body)

    def delete(self, path: str) -> tuple[int, dict]:
        return self._request("DELETE", path)

    def post_file(
        self, path: str, file_path: str,
        field_name: str = "file", extra_fields: dict | None = None,
    ) -> tuple[int, dict]:
        """multipart 上传文件。"""
        import uuid
        boundary = uuid.uuid4().hex
        file_data = Path(file_path).read_bytes()
        filename = Path(file_path).name

        parts = []
        if extra_fields:
            for k, v in extra_fields.items():
                parts.append(
                    f"--{boundary}\r\n"
                    f"Content-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}"
                )
        parts.append(
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n"
        )
        body = b"\r\n".join(p.encode() for p in parts) + file_data + f"\r\n--{boundary}--\r\n".encode()

        url = f"{self.base_url}/api{path}"
        req = Request(url, data=body, method="POST")
        headers = self._auth_headers()
        headers.pop("Content-Type", None)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            ctx = ssl._create_unverified_context()
            resp = urlopen(req, timeout=60, context=ctx)
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
        except HTTPError as e:
            try:
                raw = e.read().decode()
                return e.code, json.loads(raw) if raw else {"detail": str(e)}
            except Exception:
                return e.code, {"detail": str(e)}

    def stream_sse(self, path: str) -> None:
        """读取 SSE 流并实时输出事件。"""
        url = f"{self.base_url}/api{path}"
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path_and_query = parsed.path + (f"?{parsed.query}" if parsed.query else "")

        ctx = ssl._create_unverified_context() if parsed.scheme == "https" else None
        if parsed.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, context=ctx, timeout=120)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=120)

        headers = self._auth_headers()
        headers["Accept"] = "text/event-stream"
        headers["Cache-Control"] = "no-cache"
        conn.request("GET", path_and_query, headers=headers)
        resp = conn.getresponse()

        if resp.status != 200:
            raw = resp.read().decode()
            try:
                err = json.loads(raw)
            except Exception:
                err = raw
            print(f"SSE 连接失败  status={resp.status}")
            print(f"  detail: {err}")
            return

        buffer = ""
        while True:
            chunk = resp.read(1)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.rstrip("\r")
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        print(data)
                elif line.startswith("event:"):
                    pass
                elif line == "":
                    pass
        conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_json(data: dict | list) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"错误: 文件不存在: {p}")
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def _print_result(status: int, resp: dict, ok_status: int = 200) -> None:
    """统一输出：成功打印 JSON，失败打印错误。"""
    if status == ok_status or (ok_status == 201 and status == 201):
        _print_json(resp)
    else:
        print(f"请求失败  status={status}")
        detail = resp.get("detail", resp)
        if isinstance(detail, list):
            for err in detail:
                loc = " → ".join(str(x) for x in err.get("loc", []))
                print(f"  {loc}: {err.get('msg', err)}")
        else:
            print(f"  detail: {detail}")


def _resolve_path(template: str, args: argparse.Namespace) -> str:
    """将 /{group_id}/publish 中的占位符替换为 args 中的值。"""
    import re
    def _sub(m):
        return str(getattr(args, m.group(1), m.group(0)))
    return re.sub(r"\{(\w+)\}", _sub, template)


def _collect_params(args: argparse.Namespace, names: list[str]) -> dict | None:
    """从 args 中收集非 None 的查询参数。"""
    params = {}
    for n in names:
        v = getattr(args, n, None)
        if v is not None:
            # 将 Python 的 page_size 转为 API 的 page_size
            params[n] = v
    return params or None


# ---------------------------------------------------------------------------
# Action Spec (表驱动)
# ---------------------------------------------------------------------------

@dataclass
class ActionDef:
    """声明式端点定义。"""
    method: str
    path: str
    help: str = ""
    body_src: str | None = None     # "data" → 从 --data 文件读取
    query_args: list[str] = field(default_factory=list)
    path_args: list[str] = field(default_factory=list)
    ok_status: int = 200
    is_upload: bool = False
    upload_field: str = "file"
    upload_extra: dict | None = None
    custom: str | None = None       # 自定义处理函数名


# ---------------------------------------------------------------------------
# Resource Definitions
# ---------------------------------------------------------------------------

RESOURCES: dict[str, dict] = {
    # ── 工作流 ──────────────────────────────────────────────────────
    "workflow": {
        "help": "工作流管理",
        "prefix": "/workflows",
        "actions": {
            "list": ActionDef("GET", "/", "列出工作流",
                              query_args=["status", "keyword", "page", "page_size"]),
            "get": ActionDef("GET", "/{group_id}", "获取最新已发布版本",
                             path_args=["group_id"]),
            "create": ActionDef("POST", "/", "创建工作流", body_src="data", ok_status=201),
            "from-json": ActionDef("POST", "/from-json", "从 JSON 创建工作流",
                                   body_src="data", ok_status=201),
            "update-draft": ActionDef("PATCH", "/{group_id}/draft", "更新草稿定义",
                                      body_src="data", path_args=["group_id"]),
            "publish": ActionDef("POST", "/{group_id}/publish", "发布草稿",
                                 path_args=["group_id"]),
            "versions": ActionDef("GET", "/{group_id}/versions", "获取所有版本",
                                  path_args=["group_id"]),
            "version": ActionDef("GET", "/{group_id}/versions/{version}", "获取指定版本",
                                 path_args=["group_id", "version"]),
            "new-version": ActionDef("POST", "/{group_id}/versions", "创建新草稿版本",
                                     path_args=["group_id"], ok_status=201),
            "export": ActionDef("GET", "/{group_id}/export", "导出工作流",
                                path_args=["group_id"], query_args=["version", "deep"]),
            "import": ActionDef("POST", "/import", "导入工作流（JSON 文件）",
                                is_upload=True, upload_field="file", ok_status=201),
            "composition": ActionDef("GET", "/{group_id}/composition", "获取展开后的组合视图",
                                     path_args=["group_id"]),
            "change-proposal": ActionDef("POST", "/{group_id}/change-proposals",
                                         "提交变更建议", body_src="data",
                                         path_args=["group_id"], ok_status=201),
            "change-logs": ActionDef("GET", "/{group_id}/change-logs", "获取变更日志",
                                     path_args=["group_id"],
                                     query_args=["page", "page_size"]),
        },
    },

    # ── Skill ───────────────────────────────────────────────────────
    "skill": {
        "help": "Skill 管理",
        "prefix": "/skills",
        "actions": {
            "list": ActionDef("GET", "/", "列出 Skills",
                              query_args=["scope", "status", "page", "page_size"]),
            "create": ActionDef("POST", "/", "创建 Skill", body_src="data", ok_status=201),
            "import": ActionDef("POST", "/import/zip", "ZIP 导入 Skill",
                                is_upload=True, upload_extra={"overwrite": "false"},
                                ok_status=201),
            "get": ActionDef("GET", "/{skill_id}", "获取 Skill 详情",
                             path_args=["skill_id"]),
            "export": ActionDef("GET", "/{skill_id}/export", "导出 Skill",
                                path_args=["skill_id"]),
            "update": ActionDef("PUT", "/{skill_id}", "更新 Skill",
                                body_src="data", path_args=["skill_id"]),
            "status": ActionDef("PATCH", "/{skill_id}/status", "切换 Skill 状态",
                                custom="skill_status"),
            "delete": ActionDef("DELETE", "/{skill_id}", "删除 Skill",
                                path_args=["skill_id"], ok_status=204),
        },
    },

    # ── Agent ───────────────────────────────────────────────────────
    "agent": {
        "help": "Agent 管理",
        "prefix": "/agents",
        "actions": {
            "list": ActionDef("GET", "/", "列出 Agents",
                              query_args=["name", "status", "page", "page_size"]),
            "create": ActionDef("POST", "/", "创建 Agent", body_src="data", ok_status=201),
            "get": ActionDef("GET", "/{agent_id}", "获取 Agent 详情",
                             path_args=["agent_id"]),
            "update": ActionDef("PATCH", "/{agent_id}", "更新 Agent",
                                body_src="data", path_args=["agent_id"]),
            "status": ActionDef("PATCH", "/{agent_id}/status", "切换 Agent 状态",
                                custom="agent_status"),
            "delete": ActionDef("DELETE", "/{agent_id}", "删除 Agent",
                                path_args=["agent_id"], ok_status=204),
        },
    },

    # ── 项目 ────────────────────────────────────────────────────────
    "project": {
        "help": "项目管理",
        "prefix": "/projects",
        "actions": {
            "list": ActionDef("GET", "/", "列出项目",
                              query_args=["page", "page_size", "status", "keyword"]),
            "create": ActionDef("POST", "/", "创建项目", body_src="data", ok_status=201),
            "get": ActionDef("GET", "/{project_id}", "获取项目详情",
                             path_args=["project_id"]),
            "update": ActionDef("PATCH", "/{project_id}", "更新项目",
                                body_src="data", path_args=["project_id"]),
            "delete": ActionDef("DELETE", "/{project_id}", "删除项目",
                                path_args=["project_id"], ok_status=204),
        },
    },

    # ── 任务 ────────────────────────────────────────────────────────
    "task": {
        "help": "任务管理（需要 --project-id）",
        "prefix": "/projects/{project_id}/tasks",
        "actions": {
            "list": ActionDef("GET", "/", "列出任务",
                              query_args=["page", "page_size", "status"]),
            "create": ActionDef("POST", "/", "创建任务", body_src="data", ok_status=201),
            "get": ActionDef("GET", "/{task_id}", "获取任务详情",
                             path_args=["task_id"]),
            "start": ActionDef("POST", "/{task_id}/start", "启动任务",
                               path_args=["task_id"]),
            "retry": ActionDef("POST", "/{task_id}/retry", "重试任务",
                               body_src="data", path_args=["task_id"]),
            "pause": ActionDef("POST", "/{task_id}/pause", "暂停任务",
                               path_args=["task_id"]),
            "resume": ActionDef("POST", "/{task_id}/resume", "恢复任务",
                                path_args=["task_id"]),
            "node-runs": ActionDef("GET", "/{task_id}/node-runs", "查询节点运行列表",
                                   path_args=["task_id"]),
            "node-run": ActionDef("GET", "/{task_id}/node-runs/{node_run_id}",
                                  "获取节点运行详情",
                                  path_args=["task_id", "node_run_id"]),
            "submit": ActionDef("POST", "/{task_id}/nodes/{node_key}/submit",
                                "提交人工节点产物", body_src="data",
                                path_args=["task_id", "node_key"]),
            "approve": ActionDef("POST", "/{task_id}/nodes/{node_key}/approve",
                                 "审批通过", body_src="data",
                                 path_args=["task_id", "node_key"]),
            "reject": ActionDef("POST", "/{task_id}/nodes/{node_key}/reject",
                                "审批驳回", body_src="data",
                                path_args=["task_id", "node_key"]),
            "artifacts": ActionDef("GET", "/{task_id}/artifacts", "查询产物列表",
                                   path_args=["task_id"], query_args=["node_key"]),
            "artifact-download": ActionDef("GET",
                                           "/{task_id}/artifacts/{artifact_id}/download",
                                           "下载产物文件",
                                           path_args=["task_id", "artifact_id"]),
            "logs": ActionDef("GET", "/{task_id}/nodes/{node_key}/logs",
                              "查询节点日志",
                              path_args=["task_id", "node_key"],
                              query_args=["log_type", "level"]),
            "approval-records": ActionDef(
                "GET", "/{task_id}/nodes/{node_key}/approval-records",
                "查询节点审批记录",
                path_args=["task_id", "node_key"]),
            "inputs": ActionDef("GET", "/{task_id}/inputs", "列出输入文件",
                                path_args=["task_id"]),
            "input-upload": ActionDef("POST", "/{task_id}/inputs", "上传输入文件",
                                      is_upload=True, upload_field="files",
                                      path_args=["task_id"], ok_status=201),
            "input-download": ActionDef(
                "GET", "/{task_id}/inputs/{input_file_id}/download",
                "下载输入文件",
                path_args=["task_id", "input_file_id"]),
            "input-delete": ActionDef("DELETE", "/{task_id}/inputs/{input_file_id}",
                                      "删除输入文件",
                                      path_args=["task_id", "input_file_id"],
                                      ok_status=204),
            "stream": ActionDef("GET", "", "SSE 流式读取 Agent 节点实时执行日志",
                                path_args=["task_id"], custom="task_stream"),
        },
    },

    # ── 待办任务 ────────────────────────────────────────────────────
    "pending-task": {
        "help": "待办任务管理",
        "prefix": "/pending-tasks",
        "actions": {
            "list": ActionDef("GET", "/", "列出待办任务",
                              query_args=["status", "page", "page_size"]),
            "get": ActionDef("GET", "/{task_id}", "获取待办任务详情",
                             path_args=["task_id"]),
            "update": ActionDef("PATCH", "/{task_id}", "更新待办任务状态",
                                body_src="data", path_args=["task_id"]),
            "artifact-upload": ActionDef("POST", "/{task_id}/artifacts",
                                         "上传产物",
                                         is_upload=True, path_args=["task_id"],
                                         ok_status=201),
            "artifacts": ActionDef("GET", "/{task_id}/artifacts", "查询产物列表",
                                   path_args=["task_id"]),
            "artifact-delete": ActionDef(
                "DELETE", "/{task_id}/artifacts/{artifact_id}",
                "删除产物", path_args=["task_id", "artifact_id"], ok_status=204),
            "pre-check": ActionDef("POST", "/{task_id}/pre-check", "预检",
                                   path_args=["task_id"]),
        },
    },

    # ── 用户管理 ────────────────────────────────────────────────────
    "user": {
        "help": "用户管理（Admin）",
        "prefix": "/users",
        "actions": {
            "list": ActionDef("GET", "/", "列出用户",
                              query_args=["page", "page_size"]),
            "create": ActionDef("POST", "/", "创建用户", body_src="data", ok_status=201),
            "get": ActionDef("GET", "/{user_id}", "获取用户详情",
                             path_args=["user_id"]),
            "update": ActionDef("PATCH", "/{user_id}", "更新用户",
                                body_src="data", path_args=["user_id"]),
            "delete": ActionDef("DELETE", "/{user_id}", "删除用户",
                                path_args=["user_id"], ok_status=204),
            "activate": ActionDef("POST", "/{user_id}/activate", "激活用户",
                                  path_args=["user_id"]),
            "reset-password": ActionDef("POST", "/{user_id}/reset-password",
                                        "重置密码", body_src="data",
                                        path_args=["user_id"]),
            "roles": ActionDef("PUT", "/{user_id}/roles", "设置用户角色",
                               body_src="data", path_args=["user_id"]),
        },
    },

    # ── 认证 ────────────────────────────────────────────────────────
    "auth": {
        "help": "用户认证",
        "prefix": "/auth",
        "actions": {
            "register": ActionDef("POST", "/register", "注册新用户",
                                  custom="auth_register", ok_status=201),
            "login": ActionDef("POST", "/login", "登录获取 Token",
                               custom="auth_login"),
        },
    },

    # ── LLM 配置 ────────────────────────────────────────────────────
    "llm": {
        "help": "LLM 配置管理（Admin）",
        "prefix": "/system-config",
        "actions": {
            "list": ActionDef("GET", "/providers", "列出所有 LLM 配置"),
            "create": ActionDef("POST", "/providers", "新增 LLM 配置",
                                body_src="data", ok_status=201),
            "get": ActionDef("GET", "/providers/{config_id}", "查询 LLM 配置",
                             path_args=["config_id"]),
            "update": ActionDef("PUT", "/providers/{config_id}", "更新 LLM 配置",
                                body_src="data", path_args=["config_id"]),
            "delete": ActionDef("DELETE", "/providers/{config_id}", "删除 LLM 配置",
                                path_args=["config_id"], ok_status=204),
            "enable": ActionDef("POST", "/providers/{config_id}/enable", "启用 LLM 配置",
                                path_args=["config_id"]),
            "disable": ActionDef("POST", "/providers/{config_id}/disable", "禁用 LLM 配置",
                                 path_args=["config_id"]),
        },
    },

    # ── Guard 规则 ──────────────────────────────────────────────────
    "guard-rule": {
        "help": "Guard 规则管理",
        "prefix": "/guard-rules",
        "actions": {
            "list": ActionDef("GET", "/", "列出 Guard 规则"),
            "create": ActionDef("POST", "/", "创建 Guard 规则",
                                body_src="data", ok_status=201),
            "get": ActionDef("GET", "/{rule_id}", "获取 Guard 规则详情",
                             path_args=["rule_id"]),
            "update": ActionDef("PATCH", "/{rule_id}", "更新 Guard 规则",
                                body_src="data", path_args=["rule_id"]),
            "delete": ActionDef("DELETE", "/{rule_id}", "删除 Guard 规则",
                                path_args=["rule_id"], ok_status=204),
        },
    },

    # ── 审批 ────────────────────────────────────────────────────────
    "approval": {
        "help": "审批管理",
        "prefix": "/approvals",
        "actions": {
            "list": ActionDef("GET", "", "查询审批列表",
                              query_args=["page", "page_size"]),
            "get": ActionDef("GET", "/{action_id}", "查询审批详情",
                             path_args=["action_id"]),
            "summary": ActionDef("GET", "/{action_id}/summary", "查询审批摘要",
                                 path_args=["action_id"]),
            "artifacts": ActionDef("GET", "/{action_id}/artifacts", "查询审批产物",
                                   path_args=["action_id"]),
            "artifact-download": ActionDef(
                "GET", "/{action_id}/artifacts/{artifact_id}/download",
                "下载审批产物", path_args=["action_id", "artifact_id"]),
            "decide": ActionDef("POST", "/{action_id}/decide", "审批决定",
                                body_src="data", path_args=["action_id"]),
        },
    },

    # ── 通知 ────────────────────────────────────────────────────────
    "notification": {
        "help": "通知管理",
        "prefix": "/notifications",
        "actions": {
            "list": ActionDef("GET", "/", "查询通知列表",
                              query_args=["page", "page_size"]),
            "unread-count": ActionDef("GET", "/unread-count", "查询未读数量"),
            "preferences": ActionDef("GET", "/preferences", "获取通知偏好"),
            "update-preferences": ActionDef("PUT", "/preferences", "更新通知偏好",
                                            body_src="data"),
            "get": ActionDef("GET", "/{notification_id}", "获取通知详情",
                             path_args=["notification_id"]),
            "acknowledge": ActionDef("PUT", "/{notification_id}/acknowledge",
                                     "确认通知", path_args=["notification_id"]),
            "dismiss": ActionDef("PUT", "/{notification_id}/dismiss",
                                 "忽略通知", path_args=["notification_id"]),
            "batch-acknowledge": ActionDef("PUT", "/batch-acknowledge",
                                           "批量确认通知", body_src="data"),
        },
    },

    # ── 个人中心 ────────────────────────────────────────────────────
    "me": {
        "help": "个人中心",
        "prefix": "/me",
        "actions": {
            "profile": ActionDef("GET", "/profile", "获取个人信息"),
            "update-profile": ActionDef("PATCH", "/profile", "更新个人信息",
                                        body_src="data"),
            "change-password": ActionDef("POST", "/change-password", "修改密码",
                                         body_src="data"),
            "bind-feishu": ActionDef("PUT", "/feishu", "绑定飞书",
                                     body_src="data"),
        },
    },

    # ── Agent 会话 ──────────────────────────────────────────────────
    "agent-session": {
        "help": "Agent 会话管理",
        "prefix": "/me/agent",
        "actions": {
            "start": ActionDef("POST", "/start", "启动 Agent 会话"),
            "stop": ActionDef("DELETE", "/stop", "停止 Agent 会话",
                              ok_status=204),
            "status": ActionDef("GET", "/status", "查询 Agent 状态"),
            "briefing": ActionDef("GET", "/briefing", "获取个人简报"),
            "task-briefing": ActionDef("GET", "/briefing/{task_id}",
                                       "获取任务简报", path_args=["task_id"]),
            "preview": ActionDef("POST", "/acts/preview", "预览委派操作",
                                 body_src="data"),
            "execute": ActionDef("POST", "/acts/execute", "执行委派操作",
                                 body_src="data"),
            "history": ActionDef("GET", "/acts/history", "查询委派历史"),
            "pending-actions": ActionDef("GET", "/pending-actions",
                                         "查询待处理操作"),
            "dismiss-action": ActionDef("PUT",
                                        "/pending-actions/{action_id}/dismiss",
                                        "忽略待处理操作",
                                        path_args=["action_id"], ok_status=204),
            "snooze-action": ActionDef("PUT",
                                       "/pending-actions/{action_id}/snooze",
                                       "延迟待处理操作",
                                       body_src="data", path_args=["action_id"]),
            "artifacts": ActionDef("GET", "/artifacts", "查询个人产物列表",
                                   query_args=["page", "page_size"]),
            "create-artifact": ActionDef("POST", "/artifacts", "创建个人产物",
                                         body_src="data", ok_status=201),
            "artifact": ActionDef("GET", "/artifacts/{artifact_id}",
                                  "获取个人产物详情",
                                  path_args=["artifact_id"]),
            "sync-artifact": ActionDef("POST",
                                       "/artifacts/{artifact_id}/sync",
                                       "同步产物", path_args=["artifact_id"]),
            "delete-artifact": ActionDef("DELETE",
                                         "/artifacts/{artifact_id}",
                                         "删除个人产物",
                                         path_args=["artifact_id"], ok_status=204),
        },
    },

    # ── 记忆 ────────────────────────────────────────────────────────
    "memory": {
        "help": "记忆管理",
        "prefix": "/memory",
        "actions": {
            "objects": ActionDef("GET", "/objects", "查询记忆对象列表",
                                 query_args=["page", "page_size", "scope"]),
            "object": ActionDef("GET", "/objects/{memory_id}", "获取记忆对象详情",
                                path_args=["memory_id"]),
            "task-memories": ActionDef("GET", "/tasks/{task_id}",
                                       "查询任务记忆",
                                       path_args=["task_id"]),
        },
    },

    # ── 审计日志 ────────────────────────────────────────────────────
    "audit": {
        "help": "审计日志",
        "prefix": "/tasks",
        "actions": {
            "log": ActionDef("GET", "/{task_id}/audit-log", "查询 Task 审计日志",
                             path_args=["task_id"], query_args=["stage", "actor"]),
            "entry": ActionDef("GET", "/{task_id}/audit-log/{entry_id}",
                               "获取单条审计详情",
                               path_args=["task_id", "entry_id"]),
        },
    },

    # ── Replay ──────────────────────────────────────────────────────
    "replay": {
        "help": "工作流回放",
        "prefix": "",
        "actions": {
            "trigger": ActionDef("POST", "/workflows/{workflow_id}/replay",
                                 "触发回放", path_args=["workflow_id"],
                                 body_src="data"),
            "proposals": ActionDef("GET", "/workflows/{workflow_id}/proposals",
                                   "查询回放提案", path_args=["workflow_id"]),
            "accept": ActionDef("POST", "/proposals/{proposal_id}/accept",
                                "接受提案", body_src="data",
                                path_args=["proposal_id"]),
            "reject": ActionDef("POST", "/proposals/{proposal_id}/reject",
                                "拒绝提案", body_src="data",
                                path_args=["proposal_id"]),
        },
    },
}


# ---------------------------------------------------------------------------
# Custom Handlers
# ---------------------------------------------------------------------------

def _auth_login(client: ApiClient, args: argparse.Namespace) -> None:
    """登录并保存 session。"""
    body = {"username": args.username, "password": args.password}
    status, resp = client.post("/auth/login", body)
    if status == 200:
        token = resp.get("access_token", "")
        save_session(args.base_url, token, "jwt")
        print(f"登录成功!")
        print(f"  token: {token}")
        print(f"  session 已保存到: {SESSION_FILE}")
        if args.save:
            Path(args.save).write_text(token, encoding="utf-8")
            print(f"  token 已保存到: {args.save}")
    else:
        print(f"登录失败  status={status}  detail={resp.get('detail', resp)}")


def _auth_register(client: ApiClient, args: argparse.Namespace) -> None:
    """注册新用户并打印 Token。"""
    body = {"username": args.username, "email": args.email, "password": args.password}
    status, resp = client.post("/auth/register", body)
    if status == 201:
        token = resp.get("access_token", "")
        print(f"注册成功!")
        print(f"  token: {token}")
    else:
        print(f"注册失败  status={status}  detail={resp.get('detail', resp)}")


def _skill_status(client: ApiClient, args: argparse.Namespace) -> None:
    """切换 Skill 状态。"""
    status, resp = client.patch(f"/skills/{args.skill_id}/status",
                                {"status": args.new_status})
    if status == 200:
        print(f"状态已更新  id={resp.get('id')}  status={resp.get('status')}")
    else:
        print(f"更新失败  status={status}  detail={resp.get('detail', resp)}")


def _agent_status(client: ApiClient, args: argparse.Namespace) -> None:
    """切换 Agent 状态。"""
    status, resp = client.patch(f"/agents/{args.agent_id}/status",
                                {"status": args.new_status})
    if status == 200:
        print(f"状态已更新  id={resp.get('id')}  status={resp.get('status')}")
    else:
        print(f"更新失败  status={status}  detail={resp.get('detail', resp)}")


def _task_stream(client: ApiClient, args: argparse.Namespace) -> None:
    """SSE 流式读取 Agent 节点实时执行日志。"""
    import re
    prefix = re.sub(
        r"\{(\w+)\}",
        lambda m: str(getattr(args, m.group(1), m.group(0))),
        "/projects/{project_id}/tasks",
    )
    path = prefix + f"/{args.task_id}/node-runs/{args.node_run_id}/agent-stream"
    client.stream_sse(path)


CUSTOM_HANDLERS = {
    "auth_login": _auth_login,
    "auth_register": _auth_register,
    "skill_status": _skill_status,
    "agent_status": _agent_status,
    "task_stream": _task_stream,
}


# ---------------------------------------------------------------------------
# Generic Action Handler
# ---------------------------------------------------------------------------

def handle_action(
    client: ApiClient, res_name: str, action_name: str, args: argparse.Namespace,
) -> None:
    """通用 action 处理器：根据 ActionDef 构造请求并输出结果。"""
    res = RESOURCES[res_name]
    action: ActionDef = res["actions"][action_name]

    # 自定义处理
    if action.custom:
        handler = CUSTOM_HANDLERS.get(action.custom)
        if handler:
            handler(client, args)
            return

    # 构造路径
    prefix = res["prefix"]
    # 替换 prefix 中的路径参数（如 {project_id}）
    import re
    prefix = re.sub(
        r"\{(\w+)\}",
        lambda m: str(getattr(args, m.group(1), m.group(0))),
        prefix,
    )
    path = prefix + _resolve_path(action.path, args)

    # 收集查询参数
    params = _collect_params(args, action.query_args)

    # 构造请求体
    body = None
    if action.body_src == "data":
        body = _load_json(args.data)
    elif action.body_src == "inline":
        body = {}

    # 文件上传
    if action.is_upload:
        file_path = getattr(args, "file", None)
        if not file_path:
            print("错误: 缺少 --file 参数")
            sys.exit(1)
        extra = action.upload_extra or {}
        if hasattr(args, "overwrite") and args.overwrite:
            extra["overwrite"] = "true"
        status, resp = client.post_file(path, file_path,
                                        field_name=action.upload_field,
                                        extra_fields=extra or None)
    else:
        # 发送请求
        method = action.method.upper()
        if method == "GET":
            status, resp = client.get(path, params)
        elif method == "POST":
            status, resp = client.post(path, body)
        elif method == "PATCH":
            status, resp = client.patch(path, body)
        elif method == "PUT":
            status, resp = client.put(path, body)
        elif method == "DELETE":
            status, resp = client.delete(path)
        else:
            print(f"不支持的方法: {method}")
            return

    # 输出结果
    if action.ok_status == 204 and status == 204:
        print(f"操作成功 (204)")
    else:
        _print_result(status, resp, action.ok_status)


# ---------------------------------------------------------------------------
# Plan Subcommand (original workflow creation flow)
# ---------------------------------------------------------------------------

def create_skills(client: ApiClient, skills: list[dict]) -> dict[str, str]:
    """创建 Skills，返回 {name: id} 映射。"""
    name_to_id: dict[str, str] = {}
    print(f"\n{'='*50}")
    print(f"  创建 Skills ({len(skills)} 个)")
    print(f"{'='*50}")

    for skill_def in skills:
        name = skill_def["name"]
        if "zip_path" in skill_def:
            overwrite = skill_def.get("overwrite", False)
            print(f"  [{name}] 从 ZIP 导入: {skill_def['zip_path']}")
            extra = {"overwrite": str(overwrite).lower()}
            status, resp = client.post_file("/skills/import/zip",
                                            skill_def["zip_path"],
                                            extra_fields=extra)
        else:
            print(f"  [{name}] JSON 创建...")
            status, resp = client.post("/skills", {
                "name": name,
                "description": skill_def.get("description", ""),
                "content": skill_def.get("content", ""),
                "scope": skill_def.get("scope", "user"),
            })

        if status == 201:
            skill_id = resp.get("id", "")
            name_to_id[name] = skill_id
            print(f"  [{name}] 创建成功  id={skill_id}")
        elif status == 409:
            skill_id = resp.get("id", "")
            if skill_id:
                name_to_id[name] = skill_id
                print(f"  [{name}] 已存在，复用  id={skill_id}")
            else:
                print(f"  [{name}] 已存在但无法获取 id，跳过")
        else:
            print(f"  [{name}] 创建失败  status={status}  detail={resp.get('detail', resp)}")

    return name_to_id


def create_agents(
    client: ApiClient, agents: list[dict], skill_name_map: dict[str, str],
) -> dict[str, str]:
    """创建 Agents，返回 {name: id} 映射。"""
    name_to_id: dict[str, str] = {}
    if not agents:
        print("\n  无需创建 Agent（全部使用 general 模式）")
        return name_to_id

    print(f"\n{'='*50}")
    print(f"  创建 Agents ({len(agents)} 个)")
    print(f"{'='*50}")

    for agent_def in agents:
        name = agent_def["name"]
        skill_ids = [skill_name_map[s] for s in agent_def.get("skill_names", [])
                     if s in skill_name_map]
        print(f"  [{name}] 创建中... (skills={len(skill_ids)})")
        status, resp = client.post("/agents/", {
            "name": name,
            "description": agent_def.get("description", ""),
            "skill_ids": skill_ids,
        })

        if status == 201:
            agent_id = resp.get("id", "")
            name_to_id[name] = agent_id
            print(f"  [{name}] 创建成功  id={agent_id}")
        elif status == 409:
            agent_id = resp.get("id", "")
            if agent_id:
                name_to_id[name] = agent_id
                print(f"  [{name}] 已存在，复用  id={agent_id}")
            else:
                print(f"  [{name}] 已存在但无法获取 id，跳过")
        else:
            print(f"  [{name}] 创建失败  status={status}  detail={resp.get('detail', resp)}")

    return name_to_id


def resolve_workflow(
    workflow_def: dict, skill_name_map: dict[str, str], agent_name_map: dict[str, str],
) -> dict:
    """替换 workflow 定义中的占位符 name → id。"""
    nodes = []
    for node in workflow_def.get("nodes", []):
        node = dict(node)
        if node.get("node_type") == "agent_node":
            mode = node.get("agent_mode", "specific")
            if mode == "general":
                node["skill_ids"] = [skill_name_map[s]
                                     for s in node.get("skill_names", [])
                                     if s in skill_name_map]
                node.pop("agent_id", None)
                node.pop("agent_name", None)
            elif mode == "specific":
                agent_name = node.get("agent_name", "")
                if agent_name and agent_name in agent_name_map:
                    node["agent_id"] = agent_name_map[agent_name]
                node.pop("skill_ids", None)
                node.pop("skill_names", None)
        node.pop("skill_names", None)
        node.pop("agent_name", None)
        nodes.append(node)

    result = dict(workflow_def)
    result["nodes"] = nodes
    return result


def cmd_plan(client: ApiClient, args: argparse.Namespace) -> None:
    """从 plan.json 一键创建 skill/agent/workflow。"""
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"错误: 计划文件不存在: {plan_path}")
        sys.exit(1)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    print(f"OpenTurtle Workflow Builder")
    print(f"  API:  {client.base_url}")
    print(f"  Plan: {plan_path.name}")

    if args.dry_run:
        print("\n[dry-run] 计划解析结果:")
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    # Step 1: Skills
    skill_name_map = create_skills(client, plan.get("skills", []))

    # Step 2: Agents
    agent_name_map = create_agents(client, plan.get("agents", []), skill_name_map)

    # Step 3: Workflow
    resolved = resolve_workflow(plan.get("workflow", {}), skill_name_map, agent_name_map)
    workflow_payload = {
        "name": resolved.get("name", ""),
        "description": resolved.get("description", ""),
        "definition": {
            "nodes": resolved.get("nodes", []),
            "edges": resolved.get("edges", []),
        },
    }
    if "max_parallelism" in resolved:
        workflow_payload["definition"]["max_parallelism"] = resolved["max_parallelism"]

    print(f"\n{'='*50}")
    print(f"  创建 Workflow: {workflow_payload.get('name')}")
    print(f"{'='*50}")

    status, resp = client.post("/workflows/from-json", workflow_payload)

    if status == 201:
        print(f"  创建成功!")
        print(f"    name:      {resp.get('name')}")
        print(f"    group_id:  {resp.get('group_id')}")
        print(f"    version:   v{resp.get('version')}")
        print(f"    status:    {resp.get('status')}")
        print(f"    nodes:     {len(resp.get('definition', {}).get('nodes', []))} 个")
        result = resp
    else:
        print(f"  创建失败  status={status}")
        detail = resp.get("detail", resp)
        if isinstance(detail, list):
            for err in detail:
                loc = " → ".join(str(x) for x in err.get("loc", []))
                print(f"    {loc}: {err.get('msg', err)}")
        else:
            print(f"    detail: {detail}")
        result = None

    # Summary
    print(f"\n{'='*50}")
    print(f"  创建完成!")
    print(f"{'='*50}")
    print(f"  Skills:  {len(skill_name_map)} 个")
    print(f"  Agents:  {len(agent_name_map)} 个")
    if result:
        print(f"  Workflow: {result.get('name')} (group_id={result.get('group_id')})")
        print(f"\n  发布: curl -X POST {client.base_url}/api/workflows/{result.get('group_id')}/publish "
              f"-H 'Authorization: Bearer {client.token[:8]}...'")


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def add_common_args(sub: argparse.ArgumentParser, *, need_token: bool = True) -> None:
    sub.add_argument("--base-url", default=None, help="API 地址（默认从 session 加载）")
    if need_token:
        sub.add_argument("--token", default=None, help="Bearer Token（默认从 session 加载）")
    sub.add_argument("--auth-type", choices=["jwt", "cookie"], default=None,
                     help="认证方式（默认从 session 加载）")


def _add_data_arg(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--data", required=True, help="JSON 数据文件路径")


def _add_file_arg(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--file", required=True, help="文件路径")


def _add_pagination(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--page", type=int, default=1, help="页码")
    sub.add_argument("--page-size", type=int, default=20, help="每页大小")


def register_resource(
    subparsers: argparse._SubParsersAction, name: str, res: dict,
) -> None:
    """从 RESOURCES 定义注册 argparse 子命令。"""
    p = subparsers.add_parser(name, help=res["help"])
    res_sub = p.add_subparsers(dest="action")

    for act_name, act_def in res["actions"].items():
        s = res_sub.add_parser(act_name, help=act_def.help)

        # 自定义处理不需要 token
        need_token = act_def.custom != "auth_login" and act_def.custom != "auth_register"
        if act_name in ("login", "register") and name == "auth":
            need_token = False
        add_common_args(s, need_token=need_token)

        # 路径参数
        for pa in act_def.path_args:
            flag = pa.replace("_", "-")
            s.add_argument(f"--{flag}", required=True,
                           help=f"{pa} (路径参数)")

        # 查询参数
        for qa in act_def.query_args:
            arg_name = qa.replace("_", "-")
            kwargs: dict = {"default": None, "help": qa}
            if qa in ("page", "page_size"):
                kwargs["type"] = int
                kwargs["default"] = 20 if qa == "page_size" else 1
            s.add_argument(f"--{arg_name}", **kwargs)

        # Body from file
        if act_def.body_src == "data":
            _add_data_arg(s)

        # File upload
        if act_def.is_upload:
            _add_file_arg(s)
            if name == "skill" and act_name == "import":
                s.add_argument("--overwrite", action="store_true")

        # Custom args
        if act_def.custom == "auth_login":
            s.add_argument("--username", required=True)
            s.add_argument("--password", required=True)
            s.add_argument("--save", default=None, help="保存 Token 到文件")
        elif act_def.custom == "auth_register":
            s.add_argument("--username", required=True)
            s.add_argument("--email", required=True)
            s.add_argument("--password", required=True)
        elif act_def.custom in ("skill_status", "agent_status"):
            id_name = "skill_id" if "skill" in act_def.custom else "agent_id"
            s.add_argument(f"--{id_name.replace('_', '-')}", required=True,
                           help=f"{id_name}")
            s.add_argument("--new-status", required=True,
                           choices=["enabled", "disabled"],
                           help="目标状态")

        # project_id 是 task 资源的必填参数
        if name == "task":
            s.add_argument("--project-id", required=True,
                           help="项目 ID")
            # stream 还需要 node-run-id
            if act_name == "stream":
                s.add_argument("--node-run-id", required=True,
                               help="NodeRun ID")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OpenTurtle Admin CLI -- 完整后台管理工具",
    )
    subparsers = parser.add_subparsers(dest="resource")

    # ---- plan (原有功能) ----
    p_plan = subparsers.add_parser("plan", help="从 plan.json 一键创建 skill/agent/workflow")
    add_common_args(p_plan)
    p_plan.add_argument("--plan", required=True, help="计划 JSON 文件路径")
    p_plan.add_argument("--dry-run", action="store_true", help="仅解析不调用 API")

    # ---- 动态注册所有资源 ----
    for res_name, res_def in RESOURCES.items():
        register_resource(subparsers, res_name, res_def)

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.resource:
        parser.print_help()
        sys.exit(1)

    # Plan 子命令
    if args.resource == "plan":
        base_url, token, auth_type = resolve_connection(args)
        client = ApiClient(base_url, token, auth_type)
        cmd_plan(client, args)
        return

    # 动态资源子命令
    res_name = args.resource
    action_name = getattr(args, "action", None)

    if not action_name:
        parser.parse_args([res_name, "--help"])
        return

    res = RESOURCES.get(res_name)
    if not res or action_name not in res["actions"]:
        print(f"未知操作: {res_name} {action_name}")
        sys.exit(1)

    # Auth 的 login/register 不需要 token，但仍需要 base_url
    if res_name == "auth" and action_name in ("login", "register"):
        base_url = getattr(args, "base_url", None)
        if not base_url:
            session = load_session()
            base_url = session.get("base_url") if session else None
        if not base_url:
            print("错误: 登录/注册需要 --base-url 参数或已有 session")
            sys.exit(1)
        client = ApiClient(base_url, "", "jwt")
    else:
        base_url, token, auth_type = resolve_connection(args)
        client = ApiClient(base_url, token, auth_type)

    handle_action(client, res_name, action_name, args)


if __name__ == "__main__":
    main()
