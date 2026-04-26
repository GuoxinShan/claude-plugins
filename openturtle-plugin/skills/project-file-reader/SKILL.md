---
name: project-file-reader
description: 通过相对路径查看项目工作区文件。当上下文中出现 "project-xxx/"、"preset/" 开头的相对路径需要读取文件内容，或用户说"查看文件"、"读取这个文件"时使用此 skill。
tags: [main-agent]
---

# 项目文件读取 Skill

通过 `/api/strategic/projects/{project_id}/file` 接口，按相对路径读取项目工作区文件。

## API 连接信息

`<context>` 中的 **API 连接信息** 段已自动注入以下字段：
- `base_url`：API 服务地址
- `token`：当前用户的 JWT token 或 Cookie 值
- `auth_type`：认证方式（`jwt` 或 `cookie`）
- `project_id`：当前项目 ID

直接从上下文中读取即可，无需向用户询问。

## 用法

### 读取文本文件并输出到 stdout

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/fetch_file.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --path "<相对路径>"
```

### 保存到本地文件（适合二进制文件如图片、PDF）

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/fetch_file.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --path "<相对路径>" \
  --output <本地文件名>
```

### 仅获取文件元信息（不下载内容）

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/fetch_file.py \
  --base-url <base_url> \
  --token <token> \
  --auth-type <auth_type> \
  --project-id <project_id> \
  [--no-verify-ssl] \
  --path "<相对路径>" \
  --meta
```

返回 JSON：`{"filename": "...", "content_type": "...", "size": 1234}`

## 路径说明

`--path` 参数是相对于项目目录的路径，常见路径模式：
- `outputs/xxx_report.md` — task 产出的报告文件
- `assets/cover_xxx.png` — 封面图等资源
- `datasources/report.xlsx` — 上传的数据源文件

## 错误处理

脚本在 HTTP 错误时输出 JSON 并以非零退出码退出：
- 400：非法路径（路径穿越）
- 403：无权访问该项目
- 404：项目或文件不存在

## 示例

**用户：** "帮我读取这个项目 outputs 目录下的竞争力报告"

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/fetch_file.py \
  --base-url http://localhost:8000/api \
  --token eyJhbGc... \
  --project-id 069e71ee-xxxx \
  --path "outputs/competitiveness_report.md"
```
