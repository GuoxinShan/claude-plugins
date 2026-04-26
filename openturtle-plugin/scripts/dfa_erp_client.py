"""
ERP Financial Data Skill HTTP 客户端
封装与金钥财报企业版 OpenAPI 的交互，自动处理鉴权、配置持久化和连通性检测。

凭证优先级（从高到低）:
    1. 构造参数直接传入
    2. 本地配置文件 ~/.dfa-erp-skill/config.json
    3. 环境变量 DFA_ERP_API_KEY

域名优先级（从高到低）:
    1. 构造参数直接传入
    2. 本地配置文件 ~/.dfa-erp-skill/config.json
    3. 环境变量 DFA_ERP_SERVER_URL

首次使用时提示用户提供 Key 和域名，保存到本地配置文件后无需重复输入。

注意：此为临时直连方案，后续迁移到后端统一封装后移除。
"""

import os
import ssl
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

DEFAULT_SERVER_URL = ""
DEFAULT_API_KEY = ""

CONFIG_DIR = Path.home() / ".dfa-erp-skill"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 跳过自签名证书校验
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _probe_connectivity(server_url: str, api_key: str, timeout: int = 10) -> tuple[bool, str]:
    """
    探测 server_url + api_key 是否可用。
    返回 (success, error_hint)：
      - (True, "")  连通且鉴权通过
      - (False, "AUTH_FAILED")  连通但 key 无效（401/403）
      - (False, "CONN_FAILED:<detail>")  无法连接（域名/端口/网络问题）
    """
    url = server_url.rstrip("/") + "/api/v1/skill/fin-report-companies"
    headers = {"Authorization": f"Bearer {api_key}"}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("code") in (200, None):
                return True, ""
            return False, f"AUTH_FAILED"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, "AUTH_FAILED"
        return False, f"HTTP_{e.code}"
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return False, f"CONN_FAILED:{e}"


def _interactive_setup(current_server: str = None, current_key: str = None, hint: str = "") -> dict:
    """交互式引导用户输入正确的域名和 API Key"""
    print("=" * 50)
    print("  ERP Financial Data Skill 配置")
    print("=" * 50)
    if hint:
        print(f"\n⚠  {hint}\n")

    config = _load_config()

    server = current_server or config.get("server_url") or DEFAULT_SERVER_URL
    print(f"当前服务地址: {server}")
    new_server = input("服务地址（回车保持不变）: ").strip()
    if new_server:
        server = new_server.rstrip("/")

    key = current_key or config.get("api_key") or DEFAULT_API_KEY
    masked = key[:10] + "..." if len(key) > 10 else key
    print(f"当前 API Key: {masked}")
    new_key = input("API Key（回车保持不变）: ").strip()
    if new_key:
        key = new_key

    config["server_url"] = server
    config["api_key"] = key
    _save_config(config)

    print(f"\n配置已保存到 {CONFIG_FILE}")
    return {"server_url": server, "api_key": key}


class DfaErpClient:
    """DFA ERP Financial Data HTTP 客户端"""

    def __init__(self, server_url: str = None, api_key: str = None):
        config = _load_config()

        self.server_url = (
            server_url
            or config.get("server_url")
            or os.environ.get("DFA_ERP_SERVER_URL")
            or DEFAULT_SERVER_URL
        ).rstrip("/")

        self.api_key = (
            api_key
            or config.get("api_key")
            or os.environ.get("DFA_ERP_API_KEY")
            or DEFAULT_API_KEY
        )

        ok, err = _probe_connectivity(self.server_url, self.api_key)
        if ok:
            if not config.get("api_key"):
                config["api_key"] = self.api_key
                config["server_url"] = self.server_url
                _save_config(config)
            return

        if "AUTH_FAILED" in err:
            hint = f"API Key 鉴权失败（{self.server_url}），请提供有效的 API Key。"
        elif "CONN_FAILED" in err:
            hint = f"无法连接到 {self.server_url}，请检查域名/网络。"
        else:
            hint = f"连接异常（{err}），请检查配置。"

        guided = _interactive_setup(self.server_url, self.api_key, hint)
        self.server_url = guided["server_url"].rstrip("/")
        self.api_key = guided["api_key"]

        ok2, err2 = _probe_connectivity(self.server_url, self.api_key)
        if not ok2:
            print(f"仍然无法连接: {err2}", file=sys.stderr)
            print("请确认域名和 API Key 后重试。", file=sys.stderr)
            sys.exit(1)

    def _request(self, method: str, url: str, data: bytes = None, timeout: int = 60) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if data is not None:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            print(f"HTTP {e.code} 错误: {error_body}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"连接失败: {e.reason}", file=sys.stderr)
            sys.exit(1)

    def get(self, path: str, params: dict = None, timeout: int = 60) -> dict:
        url = self.server_url + path
        if params:
            query_string = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            if query_string:
                url += "?" + query_string
        return self._request("GET", url, timeout=timeout)

    def post(self, path: str, body: dict, timeout: int = 60) -> dict:
        url = self.server_url + path
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return self._request("POST", url, data=data, timeout=timeout)


def _show_config():
    config = _load_config()
    env_key = os.environ.get("DFA_ERP_API_KEY", "")

    print("当前 ERP Financial Data Skill 配置:")
    print(f"  配置文件:  {CONFIG_FILE}")
    print(f"  服务地址:  {config.get('server_url') or '(未配置，请运行 --setup)'}")
    print()

    key = config.get("api_key", "")
    if key:
        masked_key = key[:10] + "..." if len(key) > 10 else key
        print(f"  [本地配置] API Key: {masked_key}")
    else:
        print(f"  [本地配置] API Key: (未设置，将使用内置默认)")

    if env_key:
        masked_env_key = env_key[:10] + "..." if len(env_key) > 10 else env_key
        print(f"  [环境变量] DFA_ERP_API_KEY: {masked_env_key}")
    else:
        print("  [环境变量] DFA_ERP_API_KEY: (未设置)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        _interactive_setup()
    elif len(sys.argv) > 1 and sys.argv[1] == "--show":
        _show_config()
    else:
        print("用法:")
        print(f"  python {sys.argv[0]} --setup   重新配置域名和 API Key")
        print(f"  python {sys.argv[0]} --show    查看当前配置")
