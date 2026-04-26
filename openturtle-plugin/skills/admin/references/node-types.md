# 节点类型完整参考

所有节点定义均基于 `WorkflowDefinition` 的 `nodes` 数组，通过 `node_type` 字段做类型判别。

## 通用字段（所有节点共有）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | 是 | 节点唯一标识，workflow 内不可重复 |
| `node_type` | string | 是 | 节点类型，见下方各类型 |
| `label` | string | 是 | 显示名称 |
| `position` | object | 是 | 画布坐标 `{x, y}` |

## start_node

流程入口，**必须恰好 1 个**。

```json
{"key": "start", "node_type": "start_node", "label": "开始", "position": {"x": 0, "y": 0}}
```

无额外字段。缺少 start_node 会 422 报错（不会自动注入）。

## end_node

流程出口，**必须恰好 1 个**。

```json
{"key": "end", "node_type": "end_node", "label": "结束", "position": {"x": 800, "y": 0}}
```

无额外字段。缺少 end_node 会 422 报错（不会自动注入）。

## agent_node

AI Agent 执行节点。继承执行节点通用字段，额外有 `agent_mode` 互斥校验。

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `objective` | string | 节点工作目标 |
| `agent_mode` | string | `"specific"` 或 `"general"`（**注意：默认是 specific，必须显式传 general**） |

### 模式 A：general（通用 Agent，推荐）

直接绑定 skills，运行时动态组装 Agent。**无需预先创建 Agent 实体**。

```json
{
  "key": "write",
  "node_type": "agent_node",
  "label": "撰写报告",
  "position": {"x": 200, "y": 0},
  "objective": "根据输入数据撰写分析报告",
  "agent_mode": "general",
  "skill_ids": ["069dc4de-fd3c-7903-8000-65876a533140"]
}
```

- `skill_ids`：**必填**，至少 1 个
- `agent_id`：**不得传**

### 模式 B：specific（绑定已有 Agent）

绑定预先创建好的 Agent 实体。

```json
{
  "key": "review",
  "node_type": "agent_node",
  "label": "审核报告",
  "position": {"x": 400, "y": 0},
  "objective": "审核报告质量并提出修改意见",
  "agent_mode": "specific",
  "agent_id": "069dc4df-db00-70fb-8000-55af24d7f78c"
}
```

- `agent_id`：**必填**
- `skill_ids`：**不得传**（skills 已通过 Agent 实体绑定）

### 可选字段（两种模式通用）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_retries` | int | 3 | 失败重试次数，0-10 |
| `approval_policy` | string | `"none"` | `"none"` 或 `"chain"` |
| `chain_approvers` | list | — | 链式审批人列表，见下方 |
| `max_jump_cycles` | int | 0 | 驳回跳转最大次数，0 = 不启用。审批驳回时跳回 `jump_to_node` 或 jump_back 边 |
| `jump_to_node` | string | — | 驳回目标节点 key，配合 `max_jump_cycles > 0` 使用。优先于 jump_back 边 |
| `artifact_rules` | list | — | 产物校验规则引用 |
| `summary_rules` | list | — | 总结校验规则引用 |
| `summary_formats` | list | `["md"]` | 总结格式，可选 `"md"` / `"html"` |

## human_node

人类执行节点。

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `objective` | string | 节点工作目标 |
| `assignee_id` | string | 执行者 ID，min_length=1（可填 `"TBD"` 占位） |

```json
{
  "key": "approve",
  "node_type": "human_node",
  "label": "人工审核",
  "position": {"x": 600, "y": 0},
  "objective": "审核并确认结果",
  "assignee_id": "TBD"
}
```

### 可选字段

同 agent_node 的 `approval_policy`、`chain_approvers`、`artifact_rules`、`summary_rules`、`summary_formats`。

## sub_workflow_node

子工作流引用节点。

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `objective` | string | 节点工作目标 |
| `workflow_ref` | string | 目标 workflow 的 `group_id` |

```json
{
  "key": "sub_1",
  "node_type": "sub_workflow_node",
  "label": "执行子流程",
  "position": {"x": 600, "y": 0},
  "objective": "执行子流程完成数据分析",
  "workflow_ref": "069dc4e0-acbe-7b7c-8000-bef4623cff2f"
}
```

### 可选字段

`max_retries`（默认 3）、`approval_policy`、`chain_approvers` 等，同 agent_node。

## chain_approvers 格式

```json
"chain_approvers": [
  {"type": "human", "id": "user-uuid-1", "order": 1},
  {"type": "ai_agent", "id": "agent-uuid-1", "order": 2}
]
```

- `type`：`"human"` 或 `"ai_agent"`
- `order`：从 1 开始，必须连续（1, 2, 3...）
- `approval_policy` 必须为 `"chain"` 时才生效

## Edge（边）定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `from_node` | string | 是 | 源节点 key |
| `to_node` | string | 是 | 目标节点 key |
| `priority` | int | 是 | 优先级排序，多出边时按此排序 |
| `condition_expr` | string | 否 | 条件表达式，为 true 时才遍历此边（条件分支） |

```json
{"from_node": "start", "to_node": "write", "priority": 1}
```

条件分支示例：
```json
{"from_node": "check", "to_node": "fix", "priority": 1, "condition_expr": "result.score < 80"},
{"from_node": "check", "to_node": "end", "priority": 2, "condition_expr": "result.score >= 80"}
```

## WorkflowDefinition 顶层字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `nodes` | list | — | 节点列表（必填） |
| `edges` | list | — | 边列表（必填） |
| `max_parallelism` | int | 4 | 最大并行执行节点数，1-32 |

## 常见 422 校验错误速查

| 错误信息 | 原因 | 修复 |
|----------|------|------|
| 工作流必须包含一个 start_node | nodes 中无 start_node | 添加 start_node |
| 工作流只能包含一个 start_node | 有多个 start_node | 只保留一个 |
| SPECIFIC 模式下 agent_id 必填 | agent_mode=specific 但无 agent_id | 补充 agent_id |
| SPECIFIC 模式下不应设置 skill_ids | specific 同时传了 skill_ids | 删掉 skill_ids |
| GENERAL 模式下 skill_ids 至少需要一个 | general 但 skill_ids 为空 | 补充至少 1 个 skill_id |
| GENERAL 模式下不应设置 agent_id | general 同时传了 agent_id | 删掉 agent_id |
