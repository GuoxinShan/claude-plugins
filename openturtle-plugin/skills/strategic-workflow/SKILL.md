---
name: strategic-workflow
description: 创建并执行战略分析相关的 workflow task。当用户说"帮我做战略分析"、"执行竞争力分析"、"生成报告摘要"、"跑评分卡"、"季度跟踪"、"关键议题"、"行动建议"等时使用此 skill。
tags: [main-agent]
---

# 战略分析 Workflow Skill

创建并启动战略分析相关的 workflow task。

## API 连接信息

`<context>` 中的 **API 连接信息** 段已自动注入以下字段：
- `base_url`：API 服务地址
- `token`：当前用户的 JWT token 或 Cookie 值
- `auth_type`：认证方式（`jwt` 或 `cookie`）
- `project_id`：当前项目 ID

直接从上下文中读取即可，无需向用户询问。

## 两类 Workflow 及其依赖

### A 类：公司依赖型（需要公司名称 + 数据源）

| CLI 名称 | 说明 |
|-----------|------|
| `competitiveness-report` | 竞争力评估报告 |

必填参数：`--company-name`（可选 `--stock-code`、`--input-file-paths`）

**公司名称校验**：如果用户输入的公司名称明显不合理（如乱码、虚构公司、非正式名称），应主动提示用户确认或纠正，避免生成无意义的分析结果。

### B 类：报告依赖型（需要已有的竞争力评估报告）

| CLI 名称 | 说明 |
|-----------|------|
| `strategic-analysis` | 战略分析 |
| `scorecard` | 竞争力评分 |
| `quarterly-tracking` | 季度行业跟踪报告 |
| `key-issues` | 关键议题 |
| `action-suggestions` | 行动建议 |
| `report-summary` | 报告摘要 |

必填参数：`--source-task-id`（上游竞争力评估报告的 task_id）

除竞争力评估报告本身外，所有其他 workflow 都必须基于一份已完成的竞争力评估报告。在用户表达意图时就应告知此依赖关系，而非等到执行时才报错。

**MUST 执行以下流程**：
1. 调用 `--list-results --filter-workflow 竞争力评估` 查询当前项目已有的竞争力评估报告
2. 如果有报告：用 `AskUserQuestion` 列出可选报告（显示 workflow_name、filename、created_at），让用户选择一份作为数据源
3. 如果没有报告：立即告知用户"当前项目还没有竞争力评估报告，需要先生成一份竞争力评估报告后才能执行此分析"，并引导用户先跑 A 类的 `competitiveness-report`

## 执行步骤

### Step 1：发现可用技能

从上下文的「API 连接信息」段读取连接参数，用 `--list` 查询可用技能：

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --list
```

### Step 2：识别目标技能

- **用户明确指定了场景**（如"做战略分析"、"生成报告摘要"）：根据用户描述匹配技能 name
- **用户未指定**：用 `AskUserQuestion` 让用户从 `--list` 返回的技能中选择

如果 `--list` 返回空，告知用户"项目暂无可用的战略分析技能"。

### Step 3：收集输入

根据目标技能所属类别收集不同的输入：

**A 类（公司依赖型）**：
- 公司名称（必填）— 若用户输入可疑公司名，提示确认
- 股票代码（可选）
- 输入文件路径（从上下文的「项目文件」段选择）

**B 类（报告依赖型）**：
- 先查询已有的竞争力评估报告：

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --list-results --filter-workflow 竞争力评估
```

- 如果有多份报告，用 `AskUserQuestion` 让用户选择
- 如果没有可用报告，告知用户需要先执行竞争力评估报告（A 类），再回来执行当前 workflow

### Step 4：执行

**A 类**：

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --workflow <workflow> \
  --company-name "<公司名称>" \
  [--stock-code "<股票代码>"] \
  [--input-file-paths "<文件路径1>" "<文件路径2>"]
```

**B 类**：

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --workflow <workflow> \
  --source-task-id "<竞争力评估报告的task_id>"
```

`--workflow` 支持的值：`competitiveness-report`、`strategic-analysis`、`scorecard`、`quarterly-tracking`、`key-issues`、`action-suggestions`、`report-summary`。

### Step 5：汇报结果

脚本输出 JSON，解析后告知用户：
- 成功：`已创建 {workflow名称} 任务，task_id: {task_id}，状态: {status}`
- 失败：`创建失败：{error}`

## 示例

**用户：** "帮我对比亚迪做竞争力评估"

```bash
# Step 1: 发现可用技能
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx --list

# Step 4: A 类执行（竞争力评估报告是唯一的 A 类）
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx \
  --workflow competitiveness-report --company-name "比亚迪" --stock-code "002594"
```

**用户：** "帮我做战略分析"

```bash
# Step 1: 发现可用技能
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx --list

# Step 3: B 类 — 先查询可用的竞争力评估报告
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx \
  --list-results --filter-workflow 竞争力评估

# → 有报告：用 AskUserQuestion 让用户选择
# → 无报告：告知用户需先跑竞争力评估报告

# Step 4: B 类执行（用户选择了某份报告的 task_id）
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx \
  --workflow strategic-analysis --source-task-id "abc123-task-id"
```

**用户：** "帮我生成关键议题分析"

```bash
# 同上 B 类流程：先查报告 → 让用户选 → 执行
python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx \
  --list-results --filter-workflow 竞争力评估

python $CLAUDE_PLUGIN_ROOT/scripts/execute_strategic.py \
  --base-url http://localhost:8000/api --token eyJhbGc... --project-id 069e71ee-xxxx \
  --workflow key-issues --source-task-id "abc123-task-id"
```

**用户：** "帮我对 XYZ 做竞争力评估"（XYZ 是不存在的公司）

→ 提示用户："XYZ 看起来不是一个常见的公司名称，请确认是否正确，或提供完整的公司名称。"
