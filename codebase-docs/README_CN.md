# codebase-docs

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg) ![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

[English](README.md) | 中文

**Claude Code 自动化代码库文档生成器，支持渐进式加载。**

通过并行 subagent 扫描代码库，生成结构化文档，并在 CLAUDE.md 中维护轻量级索引。Agent 按需渐进式导航 —— 先看索引，按需加载文档，最后才看源码。

## 为什么需要它？

没有它，Agent 需要读大量源码才能理解你的代码库，浪费上下文。有了它，Agent 只需读 CLAUDE.md 中每篇文档一行的索引，然后按需加载相关文档。更少上下文浪费，更快得到答案。

## 安装

在 Claude Code 中，**逐行**执行以下命令：

```
/plugin marketplace add https://github.com/GuoxinShan/claude-plugins
```

然后：

```
/plugin install codebase-docs
```

## 功能

| 功能 | 命令 | 说明 |
|------|------|------|
| 全量初始化 | `/codebase-docs:init` | 并行扫描所有模块、架构模式、API 端点 |
| 增量更新 | `/codebase-docs:update` | 只重新扫描有变更的模块 |
| 文件整理 | `/codebase-docs:organize` | 重新分类放错位置的文档和测试文件（默认 dry-run） |
| 渐进式阅读 | _自动激活 skill_ | Agent 读索引 → 按需加载文档 → 最后才看源码 |

### 渐进式加载

核心思路 —— Agent 永远不会一次性加载所有内容：

```
第一层：CLAUDE.md 索引    ← 始终在上下文中（每篇文档一行）
第二层：具体文档文件      ← 按需加载
第三层：源代码            ← 最后手段
```

### 并行扫描

`/codebase-docs:init` 并行启动多个 subagent：

```
├── module-scanner  ×N  →  docs/design/*.md       （每个模块一篇）
├── pattern-scanner     →  docs/design/architecture-overview.md
└── api-scanner         →  docs/api/api-reference.md
└── generate-index.py   →  CLAUDE.md 文档索引已更新
```

中等规模项目（约 1 万行代码），初始化需要 2-5 分钟。

### 增量更新

`/codebase-docs:update` 通过 git diff 检测变更模块，只重新扫描这些模块。通过 `.docs-manifest.json` 跟踪生成状态。

### 自动 Hooks

| Hook | 触发时机 | 作用 |
|------|---------|------|
| SessionStart | 会话启动 | 检查文档是否过期（超过 24 小时或源码更新）。建议更新。 |
| Stop | 会话结束 | 检测哪些已文档化的模块发生了变更。建议同步。 |

### doc-organize（整合 repo-cleanser）

扫描放错位置的文档、不在 `tests/` 下的测试文件、重复或孤立的文档。移动前先展示 dry-run 预览。始终使用 `git mv` 保留历史。

## 使用方法

```bash
# 首次使用
/codebase-docs:init

# 代码变更后
/codebase-docs:update

# 整理散落文件（先 dry-run 预览）
/codebase-docs:organize
/codebase-docs:organize --no-dry-run    # 确认执行

# 强制全量重新扫描
/codebase-docs:update --force
```

## 生成结果

```
your-project/
├── .docs-manifest.json                    # 跟踪生成状态
├── CLAUDE.md                              # 已更新文档索引
├── docs/
│   ├── design/
│   │   ├── architecture-overview.md       # 系统架构
│   │   ├── task.md                        # 模块文档
│   │   └── ...
│   ├── api/
│   │   └── api-reference.md              # 所有端点
│   └── reference/
```

## 插件架构

```
codebase-docs/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── module-scanner.md      # 扫描单个模块
│   ├── pattern-scanner.md     # 检测架构模式
│   └── api-scanner.md         # 映射 API 端点
├── hooks/
│   └── hooks.json             # SessionStart + Stop hooks
├── scripts/
│   ├── generate-index.py      # 生成 CLAUDE.md 文档索引
│   ├── detect-changes.py      # 检测变更模块
│   └── check-staleness.py     # 检查文档是否过期
└── skills/
    ├── doc-init/              # 全量初始化
    ├── doc-update/            # 增量更新
    ├── doc-read/              # 渐进式阅读（自动激活）
    └── doc-organize/          # 文件整理
```

## 环境要求

- Python 3.10+
- Git（用于变更检测）
- Claude Code CLI

## 许可证

MIT
