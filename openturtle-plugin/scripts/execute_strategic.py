#!/usr/bin/env python3
"""战略分析 Workflow 执行脚本。

两种模式：
  --list            列出项目可用的战略分析技能
  --workflow XXX    执行指定 workflow（动态发现 group_id）

用法：
  # 列出可用技能
  python execute_strategic.py \\
    --base-url http://localhost:8000/api \\
    --token <jwt_token> \\
    --project-id <project_id> \\
    --list

  # 执行指定 workflow
  python execute_strategic.py \\
    --base-url http://localhost:8000/api \\
    --token <jwt_token> \\
    --project-id <project_id> \\
    --workflow strategic-analysis \\
    --company-name "比亚迪"
"""

import argparse
import json
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path

# CLI 名称 → 用于模糊匹配的技能名关键字
_WORKFLOW_ALIASES = {
    "strategic-analysis": "战略分析",
    "competitiveness-report": "竞争力评估",
    "action-suggestions": "动作建议",
    "key-issues": "关键议题",
    "report-summary": "报告摘要",
    "scorecard": "评分卡",
    "quarterly-tracking": "季度行业跟踪",
    "simple-wf": "simple-wf",
    "file-creator-wf": "file-creator-wf",
    "research-pipeline": "research-pipeline",
    "retrospective": "复盘",
}

# 依赖公司名称的 workflow（需要 --company-name）
_COMPANY_DEPENDENT = {"competitiveness-report"}

# 依赖已有竞争力评估报告的 workflow（需要 --source-task-id）
_REPORT_DEPENDENT = {"strategic-analysis", "scorecard", "quarterly-tracking", "key-issues", "action-suggestions", "report-summary"}

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
    headers = {"Content-Type": "application/json"}
    if auth_type == "cookie":
        headers["Cookie"] = f"dfa_ee_cross_user={token}"
    else:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _ssl_ctx(no_verify: bool) -> ssl.SSLContext | None:
    if no_verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def _api_get(base_url: str, path: str, headers: dict, no_verify: bool = False) -> dict | list:
    req = urllib.request.Request(f"{base_url}/api{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx(no_verify)) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _discover_skill(skills: list[dict], workflow: str) -> dict | None:
    alias = _WORKFLOW_ALIASES.get(workflow, workflow)
    for s in skills:
        if s.get("name") == alias or s.get("group_id") == workflow:
            return s
    for s in skills:
        if alias in s.get("name", ""):
            return s
    return None


def list_skills(base_url: str, project_id: str, hdr: dict, no_verify: bool = False) -> None:
    """列出项目可用的战略分析技能。"""
    try:
        skills = _api_get(base_url, f"/strategic/projects/{project_id}/skills", hdr, no_verify)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {body_text}"}, ensure_ascii=False))
        sys.exit(1)

    if not skills:
        print(json.dumps({"success": True, "skills": [], "message": "项目暂无可用的战略分析技能"}, ensure_ascii=False))
        return

    result = []
    for s in skills:
        result.append({
            "name": s.get("name", ""),
            "description": s.get("description", ""),
            "group_id": s.get("group_id", ""),
        })
    print(json.dumps({"success": True, "skills": result}, ensure_ascii=False))


def list_results(base_url: str, project_id: str, hdr: dict, no_verify: bool = False,
                 workflow_name_filter: str | None = None) -> None:
    """查询项目已完成的任务结果（可按 workflow 名称过滤）。"""
    try:
        data = _api_get(base_url, f"/strategic/projects/{project_id}/results?page_size=50", hdr, no_verify)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {body_text}"}, ensure_ascii=False))
        sys.exit(1)

    items = data.get("items", []) if isinstance(data, dict) else data
    if workflow_name_filter:
        items = [r for r in items if workflow_name_filter in (r.get("workflow_name") or "")]

    result = []
    for r in items:
        result.append({
            "task_id": r.get("task_id", ""),
            "workflow_name": r.get("workflow_name", ""),
            "filename": r.get("filename", ""),
            "created_at": r.get("created_at", ""),
        })
    print(json.dumps({"success": True, "results": result, "total": len(result)}, ensure_ascii=False))


def execute_workflow(base_url: str, project_id: str, workflow: str,
                     company_name: str | None, stock_code: str | None,
                     input_file_paths: list[str] | None,
                     source_task_id: str | None,
                     hdr: dict, no_verify: bool = False) -> None:
    """动态发现并执行指定 workflow。"""
    try:
        skills = _api_get(base_url, f"/strategic/projects/{project_id}/skills", hdr, no_verify)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"获取技能列表失败: HTTP {e.code}: {body_text}"}, ensure_ascii=False))
        sys.exit(1)

    if not skills:
        print(json.dumps({"success": False, "error": "项目暂无可用的战略分析技能"}, ensure_ascii=False))
        sys.exit(1)

    skill = _discover_skill(skills, workflow)
    if skill is None:
        available = [s.get("name", s.get("group_id", "?")) for s in skills]
        print(json.dumps({
            "success": False,
            "error": f"未找到匹配的技能 '{workflow}'，可用技能：{', '.join(available)}",
        }, ensure_ascii=False))
        sys.exit(1)

    group_id = skill["group_id"]
    skill_name = skill.get("name", workflow)

    url = f"{base_url}/api/strategic/projects/{project_id}/skills/{group_id}/execute"
    body: dict = {}
    if company_name:
        body["company_name"] = company_name
    if stock_code:
        body["stock_code"] = stock_code
    if input_file_paths:
        body["input_file_paths"] = input_file_paths
    if source_task_id:
        body["source_task_id"] = source_task_id

    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=hdr, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx(no_verify)) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(json.dumps({
                "success": True,
                "workflow": skill_name,
                "task_id": result.get("id"),
                "task_name": result.get("name"),
                "status": result.get("status"),
            }, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {body_text}"}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="战略分析 workflow 执行脚本")
    parser.add_argument("--base-url", default=None, help="API 地址（默认从 session 加载）")
    parser.add_argument("--token", default=None, help="JWT token 或 Cookie 值（默认从 session 加载）")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--auth-type", choices=["jwt", "cookie"], default=None)
    parser.add_argument("--list", action="store_true", help="列出项目可用技能")
    parser.add_argument("--list-results", action="store_true", help="查询已完成的任务结果")
    parser.add_argument("--filter-workflow", default=None, help="按 workflow 名称过滤结果（配合 --list-results）")
    parser.add_argument("--workflow", help="要执行的 workflow（动态匹配技能名）")
    parser.add_argument("--company-name", default=None, help="公司名称（公司依赖型 workflow 必填）")
    parser.add_argument("--stock-code", default=None)
    parser.add_argument("--input-file-paths", nargs="*", default=None)
    parser.add_argument("--source-task-id", default=None, help="上游竞争力评估报告的 task_id（报告依赖型 workflow 必填）")
    parser.add_argument("--no-verify-ssl", action="store_true", help="跳过 SSL 证书校验（内网自签名证书）")
    args = parser.parse_args()

    # 自动加载 session（与 otcli.py 共享 ~/.openturtle/session.json）
    session = _load_session() or {}
    base_url = (args.base_url or session.get("base_url", "")).rstrip("/")
    token = args.token or session.get("token", "")
    auth_type = args.auth_type or session.get("auth_type", "jwt")
    if not base_url:
        print(json.dumps({"success": False, "error": "未指定 API 地址且无保存的 session。请先运行: python otcli.py auth login ..."}, ensure_ascii=False))
        sys.exit(1)
    if not token:
        print(json.dumps({"success": False, "error": "未指定 token 且无保存的 session。请先运行: python otcli.py auth login ..."}, ensure_ascii=False))
        sys.exit(1)

    hdr = _headers(token, auth_type)
    no_verify = args.no_verify_ssl

    if args.list:
        list_skills(base_url, args.project_id, hdr, no_verify)
    elif args.list_results:
        list_results(base_url, args.project_id, hdr, no_verify, args.filter_workflow)
    elif args.workflow:
        if args.workflow in _COMPANY_DEPENDENT and not args.company_name:
            print(json.dumps({"success": False, "error": f"workflow '{args.workflow}' 依赖公司名称，请提供 --company-name"}, ensure_ascii=False))
            sys.exit(1)
        if args.workflow in _REPORT_DEPENDENT and not args.source_task_id:
            print(json.dumps({"success": False, "error": f"workflow '{args.workflow}' 依赖竞争力评估报告，请提供 --source-task-id（可通过 --list-results --filter-workflow 竞争力评估 查询）"}, ensure_ascii=False))
            sys.exit(1)
        execute_workflow(base_url, args.project_id, args.workflow,
                         args.company_name, args.stock_code,
                         args.input_file_paths, args.source_task_id, hdr, no_verify)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
