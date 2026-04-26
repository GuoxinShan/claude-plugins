---
name: dfa-erp-data-skill
description: Query ERP financial statement data (balance sheet, income statement, cash flow statement) synced from Kingdee Galaxy Flagship to 金钥财报企业版. Use when the user wants to query internal company financial data, check specific financial report items like revenue, assets, liabilities, or net profit from the ERP system. Triggers on keywords like ERP财务数据, 三表数据, 资产负债表, 利润表, 现金流量表, 公司财务, 报表项目, 财务明细.
tags: [workflow]
---

# ERP Financial Data Skill

查询星空旗舰 ERP 同步到金钥财报企业版的三大财务报表原始数据（资产负债表、利润表、现金流量表）。

## Prerequisites

1. Python 3（无需安装额外依赖）
2. 内置默认 API Key 和域名，开箱即用；连接失败时自动提示用户输入正确配置

## Quick Start

```bash
# 列出所有有财务数据的公司
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --list-companies

# 查询资产负债表（期末值）
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --company 1201 --type 1 --year 2025 --data-type terminal

# 查询利润表指定期间
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --company 1201 --type 2 --year 2025 --period 1

# 查询指定科目
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --company 1201 --type 1 --year 2025 --items ZC.01.01 FZ.01 ZC
```

首次运行时提示输入 API Key，配置后保存到 `~/.dfa-erp-skill/config.json`，后续无需重复。

## Capabilities

### 1. List Companies

查询系统中所有已同步过财务报表数据的公司。

```bash
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --list-companies
```

返回公司编号和名称列表，用于后续查询时确认 `--company` 参数。

### 2. Query Financial Report Data

按公司、报表类型、年度等多维度查询三大报表明细数据。

```bash
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --company <编号> --type <类型> --year <年度> [选项]
```

**必填参数：**

| 参数 | 说明 |
|------|------|
| `--company`, `-c` | 公司组织编号（从 --list-companies 获取） |
| `--type`, `-t` | 报表类型：1=资产负债表, 2=利润表, 3=现金流量表 |
| `--year`, `-y` | 年度，如 2025 |

**可选参数：**

| 参数 | 说明 |
|------|------|
| `--period`, `-p` | 期间（不传则查全年所有期间） |
| `--items` | 报表项目编码列表（空格分隔，不传则查全部） |
| `--data-type`, `-d` | 数据类型过滤：terminal / opening / currentperiod / entrygrid |

**Examples:**

```bash
# 查看某公司 2025 年资产负债表全部数据
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py -c 1201 -t 1 -y 2025

# 只看期末值
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py -c 1201 -t 1 -y 2025 -d terminal

# 查利润表第 3 期
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py -c 1201 -t 2 -y 2025 -p 3

# 查指定科目：货币资金 + 负债合计 + 资产总计
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py -c 1201 -t 1 -y 2025 --items ZC.01.01 FZ ZC -d terminal
```

## Reference Data

### 报表类型

| 值 | 名称 | 编号 |
|----|------|------|
| 1 | 资产负债表 | HBZCFZB |
| 2 | 利润表 | HBLRB |
| 3 | 现金流量表 | HBXZLLB |

### 数据类型

| dataType | 含义 | 说明 |
|----------|------|------|
| terminal | 期末值 | 最常用，表示报表期末余额 |
| opening | 期初值 | 期初余额 |
| currentperiod | 本期发生额 | 本期增减变动 |
| entrygrid | 录入栏 | ERP 录入数据 |

### 常用报表项目编码

**资产负债表项目：**

| 编码 | 名称 |
|------|------|
| ZC | 资产总计 |
| ZC.01 | 流动资产合计 |
| ZC.01.01 | 货币资金 |
| ZC.01.10 | 应收账款 |
| ZC.01.22 | 存货 |
| ZC.02 | 非流动资产合计 |
| ZC.02.11 | 固定资产 |
| FZ | 负债合计 |
| FZ.01 | 流动负债合计 |
| FZ.01.10 | 应付账款 |
| FZ.01.17 | 应交税费 |
| QY.01.10 | 未分配利润 |

**利润表项目：**

| 编码 | 名称 |
|------|------|
| SR.01 | 营业收入 |
| CB.01 | 营业成本 |
| CB.12 | 销售费用 |
| CB.13 | 管理费用 |
| CB.04 | 财务费用 |
| CB.14 | 研发费用 |
| LRZE | 利润总额 |
| JLR | 净利润 |

**现金流量表项目：**

| 编码 | 名称 |
|------|------|
| JYLR.01 | 经营活动产生的现金流量净额 |
| CZLR.01 | 投资活动产生的现金流量净额 |
| CZLC.01 | 筹资活动产生的现金流量净额 |
| XJJZJ | 现金及现金等价物净增加额 |

> 编码规则：一级项目如 `ZC`、`FZ`、`SR`；二级用 `.01`、`.02` 分层；三级如 `ZC.01.01`。

## Natural Language Workflow

当用户用自然语言描述需求时（如"查一下XX公司的资产负债情况"），按以下步骤编排：

### Step 1: 确认公司

若用户给出公司名称但不确定编号，先列出可用公司：

```bash
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py --list-companies
```

### Step 2: 映射参数

根据用户描述确定查询参数：

| 用户表述 | 映射 |
|----------|------|
| 资产负债、资产、负债 | `--type 1` |
| 利润、收入、成本、费用 | `--type 2` |
| 现金流 | `--type 3` |
| XX年 | `--year XX` |
| 第N期 / N月 | `--period N` |
| 期末 / 余额 | `--data-type terminal` |
| 期初 | `--data-type opening` |

### Step 3: 执行查询

组装参数调用脚本：

```bash
python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py -c <编号> -t <类型> -y <年度> [选项]
```

### Complete Example

用户输入: **"帮我查一下1201公司2025年的资产负债表期末数据"**

执行流程:
1. 公司编号 → `1201`
2. "资产负债表" → `--type 1`
3. "2025年" → `--year 2025`
4. "期末数据" → `--data-type terminal`
5. `python CLAUDE_PLUGIN_ROOT/scripts/query_fin_report.py -c 1201 -t 1 -y 2025 -d terminal`

## Configuration

内置默认配置，首次运行自动探测连通性：
- 连通 → 自动保存到 `~/.dfa-erp-skill/config.json`，后续无需重复
- Key 鉴权失败 → 提示用户输入新的 API Key
- 域名不通 → 提示用户输入正确的服务地址

凭证优先级：参数传入 > `~/.dfa-erp-skill/config.json` > 环境变量 `DFA_ERP_API_KEY` > 内置默认 Key
域名优先级：参数传入 > `~/.dfa-erp-skill/config.json` > 环境变量 `DFA_ERP_SERVER_URL` > 内置默认域名

```bash
python CLAUDE_PLUGIN_ROOT/scripts/dfa_erp_client.py --setup   # 重新配置
python CLAUDE_PLUGIN_ROOT/scripts/dfa_erp_client.py --show    # 查看当前配置
```

## API Reference

HTTP 接口详情见 [reference.md](reference.md)。
