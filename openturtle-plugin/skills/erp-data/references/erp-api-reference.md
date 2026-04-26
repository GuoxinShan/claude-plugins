# ERP Financial Data Skill API Reference

所有接口统一通过金钥财报企业版服务的 OpenAPI 提供，使用 `Authorization: Bearer {api_key}` 鉴权。

基础地址：运行 `--setup` 配置，或通过环境变量 `DFA_ERP_SERVER_URL` 指定

## 查询有财务数据的公司列表

```
GET /api/v1/skill/fin-report-companies
Authorization: Bearer {api_key}
```

无请求参数。

返回示例：

```json
{
  "code": 200,
  "data": [
    {
      "companyNumber": "1201",
      "companyName": "NCMC十二L轨道交通有限公司"
    },
    {
      "companyNumber": "LHRG",
      "companyName": "蓝海人工"
    }
  ]
}
```

## 查询财务报表明细数据

```
POST /api/v1/skill/fin-report-data
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "companyNumber": "1201",
  "reportType": "1",
  "year": 2025,
  "period": 1,
  "itemCodes": ["ZC.01.01", "FZ.01"],
  "dataType": "terminal"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyNumber | string | 是 | 公司组织编号，通过 fin-report-companies 接口获取 |
| reportType | string | 是 | 报表类型：1=资产负债表, 2=利润表, 3=现金流量表 |
| year | int | 是 | 年度，如 2025 |
| period | int | 否 | 期间，不传则查询该年度所有期间 |
| itemCodes | list[string] | 否 | 报表项目编码列表，不传则返回全部项目 |
| dataType | string | 否 | 数据类型过滤：terminal/opening/currentperiod/entrygrid |

返回示例：

```json
{
  "code": 200,
  "data": [
    {
      "itemCode": "ZC.01.01",
      "itemName": "货币资金",
      "dataType": "terminal",
      "amount": 8700000.00
    },
    {
      "itemCode": "FZ.01",
      "itemName": "流动负债合计",
      "dataType": "terminal",
      "amount": 1506574.27
    }
  ]
}
```

## 文件结构

```
dfa-erp-skill/
  SKILL.md                     # Skill 主文档
  reference.md                 # API 详细文档（本文件）
  scripts/
    dfa_erp_client.py          # 共享 HTTP 客户端（鉴权、配置管理、首次引导）
    query_fin_report.py        # ERP 财务报表数据查询脚本
~/.dfa-erp-skill/
  config.json                  # 用户本地配置（首次使用时自动创建）
```
