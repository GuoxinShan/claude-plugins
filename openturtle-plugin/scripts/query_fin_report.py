#!/usr/bin/env python3
"""
ERP 财务报表数据查询脚本

查询星空旗舰 ERP 同步到金钥财报企业版的三大财务报表明细数据。
支持按公司、报表类型、年度、期间、科目编码、数据类型等多维度查询。

使用示例:
    python query_fin_report.py --list-companies
    python query_fin_report.py --list-periods -c HYJT
    python query_fin_report.py -c HYJT -t 利润表 -y 2024 -p 12
    python query_fin_report.py -c HYJT -t 2 -y 2024 -p 12 -d terminal --hide-zero
    python query_fin_report.py -c HYJT -t bs -y 2024 --items ZC FZ
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dfa_erp_client import DfaErpClient

# ── 报表类型映射（支持数字 / 中文别名 / 英文缩写） ────────────────────────
REPORT_TYPE_MAP = {
    # 数字
    "1": "1", "2": "2", "3": "3",
    # 中文
    "资产负债表": "1", "资产负债": "1",
    "利润表": "2", "利润": "2",
    "现金流量表": "3", "现金流量": "3", "现金流": "3",
    # 英文缩写
    "bs": "1", "balance": "1",
    "pl": "2", "income": "2", "profit": "2",
    "cf": "3", "cashflow": "3", "cash": "3",
}
REPORT_TYPE_NAMES = {"1": "资产负债表", "2": "利润表", "3": "现金流量表"}
DATA_TYPE_NAMES = {
    "terminal": "期末值", "opening": "期初值",
    "currentperiod": "本期发生额", "entrygrid": "录入栏",
}


def _resolve_report_type(raw: str) -> str:
    """将用户输入的报表类型标识统一转为 '1'/'2'/'3'"""
    key = raw.strip().lower()
    if key in REPORT_TYPE_MAP:
        return REPORT_TYPE_MAP[key]
    # 尝试原始值（保留中文大写等场景）
    if raw in REPORT_TYPE_MAP:
        return REPORT_TYPE_MAP[raw]
    raise ValueError(
        f"不支持的报表类型 '{raw}'，可用值：\n"
        "  数字:    1=资产负债表  2=利润表  3=现金流量表\n"
        "  中文:    资产负债表 / 利润表 / 现金流量表\n"
        "  英文:    bs / pl / cf"
    )


# ── 终端输出宽度工具 ────────────────────────────────────────────────────────
def _display_width(s: str) -> int:
    """计算字符串在终端的实际显示宽度（中文=2，英文=1）"""
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)


def _ljust_display(s: str, width: int) -> str:
    """按终端显示宽度左对齐填充"""
    pad = width - _display_width(s)
    return s + " " * max(pad, 0)


def _rjust_display(s: str, width: int) -> str:
    """按终端显示宽度右对齐填充"""
    pad = width - _display_width(s)
    return " " * max(pad, 0) + s

def _resolve_company(client: DfaErpClient, raw: str) -> tuple[str, str]:
    """
    将用户输入的公司标识解析为 (companyNumber, companyName)。
    - 若输入能精确匹配某个 companyNumber，直接使用
    - 否则对 companyName 做模糊匹配（不区分大小写、支持部分匹配）
    - 多个匹配时列出候选项并退出，提示用户精确指定
    """
    resp = client.get("/api/v1/skill/fin-report-companies")
    companies = resp.get("data", [])

    # 1. 精确匹配编号（大小写不敏感）
    for c in companies:
        if c.get("companyNumber", "").upper() == raw.upper():
            return c["companyNumber"], c.get("companyName", "")

    # 2. 模糊匹配名称
    keyword = raw.strip().lower()
    matched = [
        c for c in companies
        if keyword in c.get("companyName", "").lower()
        or keyword in c.get("companyNumber", "").lower()
    ]

    if len(matched) == 1:
        num = matched[0]["companyNumber"]
        name = matched[0].get("companyName", "")
        print(f"已自动匹配公司：{name}（编号: {num}）\n")
        return num, name

    if len(matched) == 0:
        print(f"未找到匹配公司 '{raw}'，当前可用公司：\n", file=sys.stderr)
        for c in companies:
            print(f"  {_ljust_display(c.get('companyNumber',''), 12)}  {c.get('companyName','')}", file=sys.stderr)
        sys.exit(1)

    # 多个匹配
    print(f"'{raw}' 匹配到多家公司，请用 -c 精确指定编号：\n", file=sys.stderr)
    for c in matched:
        print(f"  {_ljust_display(c.get('companyNumber',''), 12)}  {c.get('companyName','')}", file=sys.stderr)
    sys.exit(1)



def list_companies(client: DfaErpClient):
    resp = client.get("/api/v1/skill/fin-report-companies")
    companies = resp.get("data", [])

    if not companies:
        print("暂无公司有财务报表数据。")
        return

    print(f"共 {len(companies)} 家公司有财务报表数据：\n")
    for c in companies:
        num = c.get("companyNumber", "")
        name = c.get("companyName", "")
        print(f"  {_ljust_display(num, 12)}  {name}")

        # 按报表类型聚合年份
        coverage: list = c.get("coverage", [])
        by_type: dict[str, list] = {}
        for item in coverage:
            rt_name = item.get("reportTypeName", item.get("reportType", ""))
            year = item.get("year")
            by_type.setdefault(rt_name, []).append(year)

        for rt_name, years in by_type.items():
            years_str = ", ".join(str(y) for y in sorted(set(years), reverse=True))
            print(f"    {_ljust_display(rt_name, 12)}  {years_str} 年")
        print()


# ── 列出可用期间 ─────────────────────────────────────────────────────────
def list_periods(client: DfaErpClient, company_raw: str, report_type: str = None):
    company, company_name = _resolve_company(client, company_raw)
    params = {"companyNumber": company}
    if report_type:
        params["reportType"] = report_type

    resp = client.get("/api/v1/skill/fin-report-periods", params=params)
    periods = resp.get("data", [])

    if not periods:
        print(f"公司 {company}（{company_name}）暂无财务报表数据记录。")
        return

    rt_filter = f"（{REPORT_TYPE_NAMES.get(report_type, report_type)}）" if report_type else ""
    print(f"公司 {company}（{company_name}）{rt_filter} 可用数据范围：\n")

    by_type: dict[str, dict] = {}
    for p in periods:
        rt_name = p.get("reportTypeName", p.get("reportType", ""))
        year = str(p.get("year", ""))
        period = p.get("period")
        by_type.setdefault(rt_name, {}).setdefault(year, []).append(period)

    for rt_name, years_map in by_type.items():
        print(f"  {rt_name}")
        for year in sorted(years_map.keys(), reverse=True):
            ps = sorted(set(years_map[year]))
            ps_str = ", ".join(str(p) for p in ps)
            print(f"    {year} 年  期间: {ps_str}")
        print()

    print("使用示例:")
    sample = periods[0]
    rt = sample.get("reportType", "2")
    y = sample.get("year", 2024)
    p = sample.get("period", 12)
    print(f"  python query_fin_report.py -c {company} -t {rt} -y {y} -p {p}")

# ── 查询财务报表明细 ───────────────────────────────────────────────────────
def query_fin_report_data(client: DfaErpClient, args):
    try:
        report_type_code = _resolve_report_type(str(args.type))
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 解析公司（支持名称模糊匹配）
    company_number, company_name = _resolve_company(client, args.company)

    body = {
        "companyNumber": company_number,
        "reportType": report_type_code,
        "year": int(args.year),
    }
    if args.period is not None:
        body["period"] = int(args.period)
    if args.items:
        body["itemCodes"] = args.items
    if args.data_type:
        body["dataType"] = args.data_type

    resp = client.post("/api/v1/skill/fin-report-data", body)
    raw_data: list = resp.get("data", [])

    # ── 空结果友好提示 ──────────────────────────────────────────────────
    if not raw_data:
        report_name = REPORT_TYPE_NAMES.get(report_type_code, f"类型{report_type_code}")
        period_hint = f" 第{args.period}期" if args.period else ""
        print(f"⚠  公司 {company_name}（{company_number}）{args.year}年{period_hint}{report_name} 无数据。")
        print()
        print("可用数据范围（运行下方命令查看）：")
        print(f"  python {Path(__file__).name} --list-periods -c {company_number} -t {report_type_code}")
        return

    # ── 过滤零值 ────────────────────────────────────────────────────────
    if args.hide_zero:
        raw_data = [d for d in raw_data if d.get("amount") not in (None, 0, 0.0)]

    # ── 按期间分组 ──────────────────────────────────────────────────────
    # 如果指定了 period，数据只有一组；否则可能包含多个期间
    groups: dict[str, list] = {}
    for item in raw_data:
        year = item.get("year", args.year)
        period = item.get("period")
        key = f"{year}年 第{period}期" if period else f"{year}年（全年）"
        groups.setdefault(key, []).append(item)

    report_name = REPORT_TYPE_NAMES.get(report_type_code, f"类型{report_type_code}")
    data_type_label = f"  数据类型: {DATA_TYPE_NAMES.get(args.data_type, args.data_type)}" if args.data_type else ""
    hide_hint = "  (已过滤零值)" if args.hide_zero else ""

    print(f"【{company_name}（{company_number}）  {report_name}】{data_type_label}{hide_hint}")
    print("=" * 70)

    total = 0
    for group_key, items in sorted(groups.items()):
        if args.output == "json":
            print(f"\n── {group_key} ──")
            print(json.dumps(items, ensure_ascii=False, indent=2, default=str))
        else:
            print(f"\n── {group_key} ({'共' + str(len(items)) + '项'})")
            _print_table(items)
        total += len(items)

    if args.output != "json":
        print(f"\n{'─' * 70}")
        print(f"合计 {total} 条记录" + ("（已过滤零值）" if args.hide_zero else ""))


def _print_table(items: list):
    """按显示宽度对齐打印表格"""
    # 列宽（终端显示宽度）
    CODE_W, NAME_W, TYPE_W, AMT_W = 22, 22, 14, 18

    header = (
        _ljust_display("科目编码", CODE_W) + "  " +
        _ljust_display("科目名称", NAME_W) + "  " +
        _ljust_display("数据类型", TYPE_W) + "  " +
        _rjust_display("金额", AMT_W)
    )
    print(header)
    print("─" * (CODE_W + NAME_W + TYPE_W + AMT_W + 6))

    for item in items:
        code = item.get("itemCode", "")
        name = item.get("itemName", "")
        dtype = DATA_TYPE_NAMES.get(item.get("dataType", ""), item.get("dataType", ""))
        amount = item.get("amount")
        amount_str = f"{float(amount):>18,.2f}" if amount is not None else "N/A".rjust(18)

        # 名称过长时截断
        if _display_width(name) > NAME_W:
            while _display_width(name) > NAME_W - 2:
                name = name[:-1]
            name += "…"

        row = (
            _ljust_display(code, CODE_W) + "  " +
            _ljust_display(name, NAME_W) + "  " +
            _ljust_display(dtype, TYPE_W) + "  " +
            amount_str
        )
        print(row)


# ── main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ERP 财务报表数据查询",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
报表类型（--type / -t）支持以下写法：
  数字:    1  2  3
  中文:    资产负债表  利润表  现金流量表
  英文:    bs  pl  cf

数据类型（--data-type / -d）:
  terminal=期末值  opening=期初值  currentperiod=本期发生额  entrygrid=录入栏

示例:
  python query_fin_report.py --list-companies
  python query_fin_report.py --list-periods -c HYJT
  python query_fin_report.py --list-periods -c HYJT -t 利润表
  python query_fin_report.py -c HYJT -t 利润表 -y 2024 -p 12 -d terminal --hide-zero
  python query_fin_report.py -c HYJT -t bs -y 2024 --items ZC FZ ZC.01
  python query_fin_report.py -c HYJT -t 2 -y 2024 -p 12 -o json
        """,
    )

    parser.add_argument("--list-companies", action="store_true", help="列出所有有数据的公司（含报表覆盖范围）")
    parser.add_argument("--list-periods", action="store_true", help="列出指定公司的可用年份和期间")
    parser.add_argument("-c", "--company", help="公司组织编号")
    parser.add_argument(
        "-t", "--type",
        help="报表类型：数字(1/2/3) | 中文(资产负债表/利润表/现金流量表) | 英文(bs/pl/cf)"
    )
    parser.add_argument("-y", "--year", type=int, help="年度")
    parser.add_argument("-p", "--period", type=int, help="期间（可选，不传则查全年）")
    parser.add_argument("--items", nargs="+", help="报表项目编码列表（空格分隔）")
    parser.add_argument(
        "-d", "--data-type",
        choices=["terminal", "opening", "currentperiod", "entrygrid"],
        help="数据类型过滤"
    )
    parser.add_argument("--hide-zero", action="store_true", help="过滤金额为零的科目")
    parser.add_argument("-o", "--output", choices=["table", "json"], default="table", help="输出格式")
    parser.add_argument("--api-key", help="API Key（可选，覆盖本地配置）")
    parser.add_argument("--server-url", help="服务地址（可选，覆盖默认）")

    args = parser.parse_args()
    client = DfaErpClient(server_url=args.server_url, api_key=args.api_key)

    if args.list_companies:
        list_companies(client)

    elif args.list_periods:
        if not args.company:
            parser.error("--list-periods 需要同时指定 -c/--company")
        report_type_code = None
        if args.type:
            try:
                report_type_code = _resolve_report_type(str(args.type))
            except ValueError as e:
                print(f"错误: {e}", file=sys.stderr)
                sys.exit(1)
        list_periods(client, args.company, report_type_code)

    elif args.company and args.type and args.year:
        query_fin_report_data(client, args)

    else:
        parser.print_help()
        print()
        if args.company and not args.type:
            print("提示: 缺少 -t/--type，例如: -t 利润表 或 -t 2")
        elif args.company and not args.year:
            print("提示: 缺少 -y/--year，例如: -y 2024")
        sys.exit(1)


if __name__ == "__main__":
    main()
