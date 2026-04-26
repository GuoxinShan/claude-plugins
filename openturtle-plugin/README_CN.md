# openturtle-plugin

[English](README.md) | 中文

OpenTurtle OS 无头管理插件，通过 Claude Code 实现完整的后端控制：CLI 脚本、SSE 流式输出、战略分析工作流、待办任务管理、项目文件访问和 ERP 数据查询。

## 安装

在 Claude Code 中，**逐行**执行以下命令：

```
/plugin marketplace add https://github.com/GuoxinShan/claude-plugins
```

然后：

```
/plugin install openturtle-plugin
```

## 快速开始

```bash
# 1. 登录（自动保存 session 到 ~/.openturtle/session.json）
python scripts/otcli.py auth login --base-url http://localhost:8000 --username admin --password pass

# 2. 后续命令自动加载 session，无需重复传参
python scripts/otcli.py workflow list
python scripts/otcli.py task list --project-id <pid>
python scripts/otcli.py agent list

# 3. 其他脚本同样支持自动加载 session
python scripts/todo.py --project-id <pid> list
python scripts/execute_strategic.py --project-id <pid> --list
python scripts/fetch_file.py --project-id <pid> --path "outputs/report.md"
```

## 技能 (7)

| 技能 | 说明 |
|------|------|
| `admin` | 17 种资源类型 CRUD — 工作流、技能、Agent、项目、任务、待办任务、用户、认证、LLM、校验规则、审批、通知、个人中心、Agent 会话、记忆、审计、回放 |
| `plan-workflow` | 自然语言创建工作流 — 自动生成技能、Agent 和工作流定义 |
| `stream` | SSE 流式读取 Agent 节点实时输出 + 后台任务监控 Agent |
| `strategic-workflow` | 战略分析工作流 — 竞争力报告、评分卡等 |
| `todo` | 待办任务管理 — 创建、下发、催办、跟进 |
| `project-file-reader` | 通过相对路径读取项目工作区文件 |
| `erp-data` | ERP 财务数据查询（临时直连方案，后续迁移到后端） |

## 智能体 (1)

| 智能体 | 说明 |
|--------|------|
| `task-monitor` | 后台任务状态轮询 — 监控长时间运行的任务，完成后带回完整结果 |

## 脚本 (6)

| 脚本 | 说明 |
|------|------|
| `otcli.py` | 核心 CLI — session 管理、17 种资源类型、SSE 流式输出、JWT/Cookie 认证 |
| `execute_strategic.py` | 战略分析工作流执行 |
| `todo.py` | 待办 CRUD + 下发 + 催办 |
| `fetch_file.py` | 项目文件读取 |
| `query_fin_report.py` | ERP 财务报表查询（临时） |
| `dfa_erp_client.py` | ERP API 客户端（临时） |

## Session 管理

所有脚本共享 `~/.openturtle/session.json` 中的 session。只需通过 otcli.py 登录一次，后续所有脚本无需手动传参：

```bash
# 登录后自动保存 session
python scripts/otcli.py auth login --base-url <url> --username <user> --password <pass>

# 所有脚本自动加载 session — 无需传 --base-url/--token
python scripts/otcli.py workflow list
python scripts/todo.py --project-id <pid> list
python scripts/execute_strategic.py --project-id <pid> --list
python scripts/fetch_file.py --project-id <pid> --path "file.txt"

# 需要时可手动覆盖 session 参数
python scripts/otcli.py workflow list --base-url <other-url> --token <other-token>
```

## 认证

支持两种认证方式：
- **JWT**（默认）：`Authorization: Bearer <token>`
- **Cookie**：`Cookie: dfa_ee_cross_user=<token>`

```bash
python scripts/otcli.py workflow list --auth-type cookie
```

## SSE 流式输出

通过 SSE 实时查看 Agent 节点的执行输出：

```bash
# 先获取 node-run-id
python scripts/otcli.py task node-runs --project-id <pid> --task-id <tid>

# 流式读取指定 Agent 节点
python scripts/otcli.py task stream --project-id <pid> --task-id <tid> --node-run-id <nrid>
```

## 版本

0.1.0
