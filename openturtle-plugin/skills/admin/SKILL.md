---
name: admin
description: OpenTurtle OS 资源管理。通过 CLI 管理 17 种后端资源（workflow、skill、agent、project、task、pending-task、user、auth、llm、guard-rule、approval、notification、me、agent-session、memory、audit、replay）。当用户需要查看/创建/更新/删除任何后端资源、操作 API 端点、或说"列出所有 XXX"、"查看 XXX 详情"、"创建一个 XXX"、"删除 XXX"、"更新 XXX"时触发。
---

# 资源管理

通过 `otcli.py` 脚本管理所有 17 种后端资源。

## 连接信息

Session 自动从 `~/.openturtle/session.json` 加载。**执行任何操作前，先检查 session 是否存在**：

1. 运行任意命令（如 `workflow list`），如果返回"未指定 API 地址且无保存的 session"则说明需要登录
2. 此时主动询问用户的 base URL、用户名和密码
3. 执行登录并保存 session：
```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py auth login --base-url <base-url> --username <user> --password <pass>
```

构造 base URL 规则：
- `IP:Port` → `http://<ip>:<port>`
- 域名无协议 → `https://<domain>`
- 已有协议 → 直接用

登录成功后，后续所有操作自动使用保存的 session，无需再传认证参数。

## 通用调用模式

```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py <resource> <action> [选项]
```

## 资源总览

| 资源 | 子命令数 | 说明 |
|------|---------|------|
| `workflow` | 14 | 工作流 CRUD、版本管理、发布、导入导出 |
| `skill` | 8 | Skill CRUD + ZIP 导入导出 |
| `agent` | 6 | Agent CRUD + 启停 |
| `project` | 5 | 项目 CRUD |
| `task` | 19 | 任务生命周期管理（需 --project-id） |
| `pending-task` | 7 | 待办任务管理 |
| `user` | 8 | 用户管理（Admin） |
| `auth` | 2 | 注册/登录 |
| `llm` | 7 | LLM 配置管理（Admin） |
| `guard-rule` | 5 | Guard 规则 CRUD |
| `approval` | 6 | 审批管理 |
| `notification` | 8 | 通知管理 |
| `me` | 4 | 个人中心 |
| `agent-session` | 15 | Agent 会话管理 |
| `memory` | 3 | 记忆管理 |
| `audit` | 2 | 审计日志 |
| `replay` | 4 | 工作流回放 |

每个资源的详细命令用法，**读取 `references/resource-commands.md`**。

---

# 常见踩坑

| 资源 | 正确字段 | 常见误用 | 说明 |
|------|---------|---------|------|
| `task create` | **`name`** | ~~`title`~~ | 任务名称字段是 `name` |
| `task create` | `workflow_group_id` | — | 关联工作流时必传 |
| `plan` nodes | **`skill_names`** | ~~`skill_ids`~~ | plan 模式用 name 占位 |
| `plan` nodes | `agent_mode` | — | 必须显式传 `"general"` 或 `"specific"` |
| `plan` nodes | `start_node` / `end_node` | — | 必须各恰好 1 个 |

---

# 错误处理

| HTTP 状态码 | 含义 | 处理 |
|------------|------|------|
| 401 | Token 无效/过期 | 提示用户重新登录 |
| 403 | 权限不足 | 告知用户需要相应权限 |
| 404 | 资源不存在 | 检查 ID 是否正确 |
| 409 | 冲突 | 检查资源名称或当前状态 |
| 422 | 请求格式错误 | 检查 JSON 数据格式 |
| 503 | 服务不可用 | 检查后端服务是否启动 |
