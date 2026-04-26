---
name: stream
description: SSE 流式读取 task 执行输出和 AI Agent 对话。当用户启动了 task 后需要实时查看执行进度、或说"看看任务输出"、"监控这个任务"、"等它跑完"时触发。也负责长时 task 的后台监控：启动 task-monitor agent 后台轮询，完成后带回完整结果。
---

# 流式输出 & Task 监控

## 连接信息

Session 自动从 `~/.openturtle/session.json` 加载。

## 两种模式

### 模式 1：SSE 实时流式输出

直接读取 task 的 SSE 输出流，适合短时间任务或用户想实时看进度。

```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py task stream \
  --project-id <pid> --task-id <tid> --node-run-id <nrid>
```

`--node-run-id` 是 Agent 节点运行的 ID，可通过 `task node-runs` 获取。SSE 会推送该节点的实时执行日志（agent_text_delta、agent_tool_call_start 等），直到流结束。

脚本会持续输出 SSE 事件，直到 task 结束或连接断开。

**何时使用**：用户明确说"看实时输出"、"等它跑"且预计几分钟内完成。

### 模式 2：后台 Agent 监控（推荐用于长时任务）

启动 `task-monitor` agent 后台运行，定期轮询 task 状态。用户可以继续做其他事，task 完成后 agent 自动带回完整结果。

**何时使用**：
- 用户启动了 task 但不想干等（"帮我跑这个，完了告诉我"）
- task 预计耗时较长（>5 分钟）
- 用户想继续对话做其他事

**操作步骤**：

1. 启动 task（如果还没启动）：
```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py task start \
  --project-id <pid> --task-id <tid>
```

2. spawn task-monitor agent（后台运行）：
   - 使用 Agent 工具，设置 `run_in_background: true`
   - 传入 task 信息：base_url, token, auth_type, project_id, task_id
   - agent 会定期用 `otcli task get` 查询状态

3. 告知用户：已启动后台监控，完成后会自动通知。

## task-monitor Agent 调用方式

```
使用 Agent 工具:
  subagent_type: general-purpose
  run_in_background: true
  prompt: |
    你是 task-monitor agent。监控 OpenTurtle task 执行状态直到完成。

    连接信息：
    - base_url: {base_url}
    - token: {token}
    - auth_type: {auth_type}
    - project_id: {project_id}
    - task_id: {task_id}

    工作流程：
    1. 调用脚本查询 task 状态：
       python CLAUDE_PLUGIN_ROOT/scripts/otcli.py task get --project-id {project_id} --task-id {task_id}
    2. 解析返回的 JSON，检查 status 字段
    3. 如果 status 是 running/pending → 等 60 秒后再查
       用 Bash: sleep 60
    4. 重复步骤 1-3，直到 status 变为 completed/failed/cancelled
    5. 完成后，收集完整信息：
       - task 详情：otcli task get
       - node runs：otcli task node-runs
       - artifacts：otcli task artifacts
    6. 汇总结果，用 SendMessage 报告给主会话

    注意：总共最多轮询 120 次（约 2 小时），超时后报告超时。
```

## 查询 Task 状态（手动）

如果只想查一次状态而不做持续监控：

```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py task get \
  --project-id <pid> --task-id <tid>
```

返回 JSON 包含 `status` 字段：
- `pending` — 等待启动
- `running` — 执行中
- `completed` — 已完成
- `failed` — 失败
- `cancelled` — 已取消
- `paused` — 已暂停

## 查询 Node Runs

查看 task 中各节点的执行情况：

```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py task node-runs \
  --project-id <pid> --task-id <tid>
```

## 查询 Artifacts

查看 task 产出的文件：

```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py task artifacts \
  --project-id <pid> --task-id <tid>
```
