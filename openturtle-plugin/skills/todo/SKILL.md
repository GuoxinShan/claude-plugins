---
name: todo
description: 待办任务管理。用于创建、查询、修改、删除跟进任务，以及将任务下发给指定人员。当用户提到"待办"、"任务"、"跟进"、"提醒"、"指派"、"下发"等关键词时，或需要管理项目中的跟进事项时，使用此 skill。即使用户没有明确说"todo"，只要涉及任务管理和分配就应触发。注意：此 skill 不负责创建复盘流程，复盘流程由 strategic-workflow skill 创建。Todo 只能关联已有的复盘任务（task_type=retrospective），不能关联普通任务。
tags: [main-agent]
---

# Todo 待办任务管理

## 重要约束

- **Todo 不是用来创建复盘流程的。** 复盘流程通过 `strategic-workflow` skill 创建，创建后系统自动生成 Task。
- **Todo 只能关联复盘任务（task_type=retrospective）。** 如果用户想为非复盘任务创建 Todo，应告知用户：当前任务不是复盘流程，无法创建 Todo。
- **Task 处于 running 状态时不能创建 Todo。** 需等待任务执行完成后再创建。

## API 连接信息

`<context>` 中的 **API 连接信息** 段已自动注入以下字段：
- `base_url`：API 服务地址
- `token`：当前用户的 JWT token 或 Cookie 值
- `auth_type`：认证方式（`jwt` 或 `cookie`）
- `project_id`：当前项目 ID

直接从上下文中读取即可，无需向用户询问。

## 核心原则：先收集上下文，预填表单，用户只改改就行

不要让用户从零开始填表。你身处项目对话中，拥有大量上下文，应该主动利用。

### 你能收集到的信息

| 信息 | 方法 |
|------|------|
| 项目有哪些任务在跑 | `list-tasks` |
| 项目有哪些待办 | `list-project` |
| 对话上下文 | 用户在聊什么、刚做了什么分析、当前关注什么 |
| 项目文件 | `<context>` 中注入的 datasources |
| 现有用户 | `search-users` |

## 脚本调用方式

所有操作通过脚本调用，统一返回 JSON：

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  <command> [options]
```

### 可用命令

#### 上下文查询

| 命令 | 用途 | 示例 |
|------|------|------|
| `search-users` | 搜索用户，获取 assignee_id | `--keyword "张三"` |
| `list-tasks` | 查询项目任务列表 | `--status in_progress`，`--task-type retrospective` |

#### CRUD

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `create` | 创建待办 | `--title` |
| `list` | 查询我被指派的任务 | （无必填） |
| `get` | 查看任务详情 | `--todo-id` |
| `update` | 修改任务 | `--todo-id` |
| `update-status` | 更新状态 | `--todo-id --status pending/in_progress/completed` |
| `delete` | 删除任务 | `--todo-id` |
| `dispatch` | 下发给指定人员（触发通知） | `--todo-id --assignee-id` |
| `remind` | 催办 | `--todo-id` |
| `list-project` | 查看项目全部任务 | （无必填） |

### 创建待办的标准流程

**第一步：查询可用的复盘任务**

用户要创建 Todo 时，必须先确定关联哪个复盘任务。调用 strategic 接口获取复盘任务列表：

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url <base_url> --token <token> --auth-type <auth_type> --project-id <project_id> \
  list-tasks --task-type retrospective
```

- 如果没有复盘任务，告知用户：当前项目没有复盘流程，需先通过 `strategic-workflow` 创建。
- 如果有复盘任务，展示列表让用户选择。
- 检查所选任务的 `status`：如果是 `running`，告知用户任务正在执行中，无法创建 Todo，需等待完成。

**第二步：主动收集上下文**

根据用户意图，预填信息：
- 用户提到人名 → `search-users` 查到 assignee_id
- 用户没提人名 → 不填 assignee_id，后续再指派
- 用对话上下文提炼标题和描述

**第三步：用 AskUserQuestion 展示预填表单，让用户微调**

把收集到的信息预填好，用户只需要确认或改个别字段。

关键是让用户看到的是**已经填好的表单**，而不是空白问卷。

**第四步：创建**

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url <base_url> --token <token> --auth-type <auth_type> --project-id <project_id> \
  create --title "跟进Q2财报分析" --description "基于已上传的Q2数据，完成竞争对手对比分析" \
  --task-id <task_id> --due-date "2026-04-30T18:00:00"
```

**第五步：如果指定了指派人，问是否下发**

## 状态流转

```
pending → in_progress → completed
           ↑                 ↓
           └─────────────────┘
```

## 写操作都要确认

| 操作 | 确认方式 |
|------|----------|
| 创建 | 展示预填表单，用户确认 |
| 下发 | 问是否立即下发 |
| 修改 | 展示修改前后对比 |
| 删除 | 展示任务详情，二次确认 |
| 状态变更 | 简单确认即可 |

查询操作不需要确认，直接展示。

## 示例场景

### 场景1：用户说"帮我跟进一下这个复盘"

```bash
# 查询复盘任务
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url $BASE --token $TOKEN --auth-type jwt --project-id $PID \
  list-tasks --task-type retrospective

# 确认任务状态不是 running 后，创建待办
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url $BASE --token $TOKEN --auth-type jwt --project-id $PID \
  create --title "跟进XX复盘" --task-id <复盘task_id>
```

### 场景2：用户说"给李四建个跟进，关于那个复盘任务"

```bash
# 查用户
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url $BASE --token $TOKEN --auth-type jwt --project-id $PID \
  search-users --keyword "李四"

# 查复盘任务
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url $BASE --token $TOKEN --auth-type jwt --project-id $PID \
  list-tasks --task-type retrospective

# 确认任务状态不是 running 后，创建待办
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url $BASE --token $TOKEN --auth-type jwt --project-id $PID \
  create --title "跟进复盘任务" --assignee-id <李四的UUID> --task-id <task_id>
```

### 场景3：用户想为普通任务创建 Todo

直接告知用户：当前任务不是复盘流程（task_type 不是 retrospective），无法创建 Todo。如需创建复盘流程，请使用 `strategic-workflow` skill。

### 场景4：用户说"看看我有什么待办"

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/todo.py \
  --base-url $BASE --token $TOKEN --auth-type jwt --project-id $PID \
  list
```

## 注意事项

- assignee_id 必须是有效的用户 UUID，先用 `search-users` 查找
- 截止日期（due_date）使用 ISO 8601 格式，如 "2026-04-30T18:00:00"
- 创建和删除仅创建人可操作；状态更新创建人和被指派人均可
- 下发（dispatch）会触发 agent 通知，适合正式分配场景
- description 里可以写清楚背景和期望，方便被指派人快速理解
