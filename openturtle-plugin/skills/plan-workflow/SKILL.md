---
name: plan-workflow
description: 通过自然语言描述一键创建完整 workflow（skill + agent + workflow）。当用户说"帮我建一个 XXX 流程"、"创建一个工作流"、"帮我设计一个自动化流程"、"我想要一个审批+AI分析的流程"时触发。自动解析需求、生成 plan.json、创建所有资源。
---

# Plan 模式：一键创建 Workflow

从自然语言描述自动创建完整的 workflow，包括所需的 skill 和 agent。

## 连接信息

Session 自动从 `~/.openturtle/session.json` 加载。首次使用先登录：
```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py auth login --base-url <base-url> --username <user> --password <pass>
```

## 理解用户需求

从用户的自然语言描述中提取：

- **流程名称**：workflow 的名字
- **节点列表**：每步是 AI 执行、人工执行、还是子流程
- **执行顺序**：串行 / 并行 / 条件分支
- **每个 AI 节点需要什么能力**（对应 skill）
- **Agent 模式**：
  - 用户只说"AI 做某事" → **general** 模式（直接绑 skills，无需预建 Agent）
  - 用户要复用某个已有 Agent → **specific** 模式

如果描述不清晰，追问关键信息。注意：
- `sub_workflow_node` 需要目标 workflow 的 `group_id`
- `human_node` 需要执行者 ID（不确定时可填 `"TBD"`）

## 规划并确认

向用户展示理解和计划，等确认后再执行：

```
我理解的工作流：

流程名称：XXX

Skills（需创建）：
  - skill-a：[描述]
  - skill-b：[描述]

Agents（仅 specific 模式需要）：
  - Agent X：绑定 skill-a

Workflow 节点：
  start → [general] 分析数据（skill-a）→ [specific] Agent X 审核 → 人工确认 → end

确认后开始创建？
```

## 生成 plan.json 并执行

确认后，生成 plan JSON 文件，然后调用脚本。

### plan.json 格式

```json
{
  "skills": [
    {
      "name": "skill-name",
      "description": "能力描述（最长 1024 字符）",
      "content": "# Skill 标题\n\n详细的 skill 使用说明（Markdown）",
      "scope": "user"
    }
  ],
  "agents": [
    {
      "name": "Agent 名称",
      "description": "Agent 职责描述",
      "skill_names": ["skill-name"]
    }
  ],
  "workflow": {
    "name": "工作流名称",
    "description": "工作流描述",
    "max_parallelism": 4,
    "nodes": [
      {"key": "start", "node_type": "start_node", "label": "开始", "position": {"x": 0, "y": 0}},
      {
        "key": "node_1",
        "node_type": "agent_node",
        "label": "显示名称",
        "position": {"x": 200, "y": 0},
        "objective": "节点工作目标",
        "agent_mode": "general",
        "skill_names": ["skill-name"]
      },
      {"key": "end", "node_type": "end_node", "label": "结束", "position": {"x": 400, "y": 0}}
    ],
    "edges": [
      {"from_node": "start", "to_node": "node_1", "priority": 1},
      {"from_node": "node_1", "to_node": "end", "priority": 1}
    ]
  }
}
```

**关键规则：**
- `workflow.nodes` 中用 `skill_names`（name 占位符）而非 `skill_ids`，脚本会自动替换
- `workflow.nodes` 中用 `agent_name`（name 占位符）而非 `agent_id`，脚本会自动替换
- `skills` 和 `agents` 数组可以为空（如果没有需要创建的）
- **必须包含 start_node 和 end_node 各恰好 1 个**（不会自动注入）
- `agent_mode` **必须显式传 `"general"`**（默认值是 `"specific"`）
- 驳回跳回：设置 `max_jump_cycles` > 0 + `jump_to_node` 即可启用，需配合 `approval_policy: "chain"` 使用

### 调用脚本

```bash
# 先 dry-run 验证
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py plan \
  --plan /tmp/workflow-plan.json \
  --dry-run

# 正式创建
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py plan \
  --plan /tmp/workflow-plan.json
```

### ZIP 导入 Skill

如果用户已有 `.skill` 文件，在 skills 数组中用 `zip_path` 替代 JSON 字段：

```json
{
  "name": "my-skill",
  "zip_path": "/path/to/skill.zip",
  "overwrite": false
}
```

## 汇报结果

Workflow 创建后为 draft 状态，告知用户如何发布：

```bash
python CLAUDE_PLUGIN_ROOT/scripts/otcli.py workflow publish --group-id <group_id>
```

## 节点类型速查

完整字段参考见 `admin` skill 的 `references/node-types.md`。

| node_type | 必填额外字段 | 说明 |
|-----------|-------------|------|
| `start_node` | — | 入口，必须有且只有 1 个 |
| `end_node` | — | 出口，必须有且只有 1 个 |
| `agent_node` | `objective`, `agent_mode` | general 需 `skill_ids`，specific 需 `agent_id` |
| `human_node` | `objective`, `assignee_id` | assignee_id 可填 "TBD" |
| `sub_workflow_node` | `objective`, `workflow_ref` | 引用子流程的 group_id |

## agent_mode 互斥规则

| 模式 | agent_id | skill_ids |
|------|----------|-----------|
| `specific` | **必填** | **禁止传** |
| `general` | **禁止传** | **必填 ≥1** |
