# openturtle-plugin

English | [中文](README_CN.md)

OpenTurtle OS headless management plugin for Claude Code. Complete backend control via CLI scripts, SSE streaming, strategic workflows, todo management, project file access, and ERP data queries.

## Installation

Copy to your Claude Code plugins directory, or install via marketplace:

```bash
claude --plugin-dir /path/to/openturtle-plugin
```

## Quick Start

```bash
# 1. Login (auto-saves session to ~/.openturtle/session.json)
python scripts/otcli.py auth login --base-url http://localhost:8000 --username admin --password pass

# 2. All subsequent commands auto-load session
python scripts/otcli.py workflow list
python scripts/otcli.py task list --project-id <pid>
python scripts/otcli.py agent list

# 3. Other scripts also auto-load session
python scripts/todo.py --project-id <pid> list
python scripts/execute_strategic.py --project-id <pid> --list
python scripts/fetch_file.py --project-id <pid> --path "outputs/report.md"
```

## Skills (7)

| Skill | Description |
|-------|-------------|
| `admin` | 17 resource types CRUD — workflow, skill, agent, project, task, pending-task, user, auth, llm, guard-rule, approval, notification, me, agent-session, memory, audit, replay |
| `plan-workflow` | Natural language workflow creation — auto-generates skills, agents, and workflow |
| `stream` | SSE streaming for agent node real-time output + background task monitoring agent |
| `strategic-workflow` | Strategic analysis workflows — competitiveness reports, scorecards, etc. |
| `todo` | Todo task management — create, dispatch, remind, track follow-ups |
| `project-file-reader` | Read project workspace files via relative paths |
| `erp-data` | ERP financial data queries (临时直连方案，后续迁移到后端) |

## Agents (1)

| Agent | Description |
|-------|-------------|
| `task-monitor` | Background task status polling — monitors long-running tasks and reports back with full results |

## Scripts (6)

| Script | Description |
|--------|-------------|
| `otcli.py` | Core CLI — session management, 17 resource types, SSE streaming, JWT/Cookie auth |
| `execute_strategic.py` | Strategic workflow execution |
| `todo.py` | Todo CRUD + dispatch + remind |
| `fetch_file.py` | Project file reader |
| `query_fin_report.py` | ERP financial report queries (临时) |
| `dfa_erp_client.py` | ERP API client (临时) |

## Session Management

All scripts share session from `~/.openturtle/session.json`. Login once via otcli.py, then all scripts work without explicit credentials:

```bash
# Login saves session automatically
python scripts/otcli.py auth login --base-url <url> --username <user> --password <pass>

# All scripts auto-load session — no need for --base-url/--token
python scripts/otcli.py workflow list
python scripts/todo.py --project-id <pid> list
python scripts/execute_strategic.py --project-id <pid> --list
python scripts/fetch_file.py --project-id <pid> --path "file.txt"

# Override session with explicit args if needed
python scripts/otcli.py workflow list --base-url <other-url> --token <other-token>
```

## Authentication

Supports two auth modes:
- **JWT** (default): `Authorization: Bearer <token>`
- **Cookie**: `Cookie: dfa_ee_cross_user=<token>`

```bash
python scripts/otcli.py workflow list --auth-type cookie
```

## SSE Streaming

Real-time agent node output via SSE:

```bash
# Get node-run-id first
python scripts/otcli.py task node-runs --project-id <pid> --task-id <tid>

# Stream specific agent node
python scripts/otcli.py task stream --project-id <pid> --task-id <tid> --node-run-id <nrid>
```

## Version

0.1.0
