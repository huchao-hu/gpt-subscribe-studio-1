"""Generate checkout Sentinel headers for manual Postman requests; never create checkout."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import shutil
import sys
import uuid
from urllib.parse import quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="交互填写 session 字段，仅生成供 Postman 复制的 Sentinel 与请求头，不创建结账。"
    )
    parser.parse_args()
    for source in ("packages/contracts/src", "packages/core/src"):
        sys.path.insert(0, str(ROOT / source))
    node_modules = str(ROOT / ".tmp/sentinel-node/node_modules")
    os.environ["NODE_PATH"] = os.pathsep.join(
        item for item in (node_modules, os.environ.get("NODE_PATH", "")) if item
    )
    os.environ.setdefault("GSS_PROXY_CONFIG", str(ROOT / "runtime/proxy-gateways.json"))
    node = os.environ.get("SENTINEL_NODE") or "node"
    if not shutil.which(node):
        print("未找到 Node.js，请先完成启动文档中的 Node 安装。")
        return 1
    if not Path(os.environ["GSS_PROXY_CONFIG"]).is_file():
        print("找不到已保存的代理配置，请核对 runtime/proxy-gateways.json。")
        return 1
    try:
        from gss_core.chatgpt import ChatGPTClient
        from gss_core.countries import REGIONS, currency_for, is_supported, normalize_country
        from gss_core.proxies import GatewayStore
        from gss_core.proxy_relay import relay_manager
    except ImportError as exc:
        print(f"缺少项目依赖（{exc.name}），请先完成启动文档中的依赖安装。")
        return 1

    client = None
    try:
        print("只在本机使用。Token 输入时不显示字符，粘贴后直接回车。")
        access = getpass.getpass("1. JSON 最外层 accessToken: ").strip()
        session = getpass.getpass("2. JSON 最外层 sessionToken: ").strip()
        device = input("3. JSON 中 statsigContext.deviceId: ").strip()
        campaign = input("4. 优惠活动 ID（普通结账直接回车）: ").strip()
        if not access or not session or not device:
            print("前三项都需要填写，复制 JSON 字段值时不要带外层引号。")
            return 1
        if len(campaign) > 120:
            print("活动 ID 过长，请重新核对优惠查询返回的活动 ID。")
            return 1
        print("支持的账单国家：" + "、".join(f"{code}（{name}）" for code, name, _, _ in REGIONS))
        while True:
            country = normalize_country(input("5. 选择账单国家代码（例如 US、PH、JP）: "))
            if is_supported(country):
                break
            print("请输入上面列出的国家代码，不能留空。")

        gateway = GatewayStore().get("checkout")
        # Keep the saved region and SID so Postman can reuse this exact route.
        proxy = gateway.effective_proxy_url()
        raw = json.dumps({
            "accessToken": access,
            "sessionToken": session,
            "statsigContext": {"deviceId": device},
        })
        client = ChatGPTClient.from_raw_session(raw, proxy=proxy)
        page = "https://chatgpt.com/"
        if campaign:
            page += "?promo_campaign=" + quote(campaign, safe="")
        print("正在读取页面并调用 Node SDK 联网生成 Sentinel，请等待……", flush=True)
        # Do not refresh accessToken: the user copies the original token into cURL.
        client.prepare_risk(flow="chatgpt_checkout", page_url=page, country=country)
        print("\n===== 生成成功：复制等号后面的完整值 =====")
        values = {
            "BILLING_COUNTRY_EXAMPLE": country,
            "CURRENCY_EXAMPLE": currency_for(country),
            "LANGUAGE_EXAMPLE": client.language,
            "ACCEPT_LANGUAGE_EXAMPLE": client._identity_headers()["Accept-Language"],
            "SENTINEL_TOKEN_EXAMPLE": client.sentinel_token,
            "SESSION_ID_EXAMPLE": client.oai_session_id,
            "CLIENT_VERSION_EXAMPLE": client.client_version,
            "CLIENT_BUILD_EXAMPLE": client.client_build_number,
            "COOKIE_EXAMPLE": client._cookie_header(),
            "PURCHASE_ATTEMPT_ID_EXAMPLE": str(uuid.uuid4()),
        }
        for name, value in values.items():
            print(f"\n{name}={value}")
        print(f"\n生成 Sentinel 使用的时区：{client.timezone}（无需填到请求头）")
        print("账单国家不会自动改变代理出口，本脚本沿用保存的代理地区和 SID。")
        print("\n===== 以下请求头只在有值时添加；没有值就不用添加 =====")
        optional = {
            "openai-sentinel-so-token": client.sentinel_so,
            "oai-web-deployment-attestation": client.attestation,
        }
        for name, value in optional.items():
            print(f"{name}: {value or '（未生成，不添加这一行）'}")
        print("\n===== Postman 代理设置 =====")
        if proxy:
            parsed = urlsplit(proxy)
            print("协议:", parsed.scheme)
            print("主机:", parsed.hostname)
            print("端口:", parsed.port)
            print("用户名:", unquote(parsed.username or "") or "（留空）")
            print("密码:", unquote(parsed.password or "") or "（留空）")
        else:
            print("未启用项目代理。Postman 关闭系统、自定义及环境变量代理；VPN/TUN 仍可能影响路由。")
        print("\n未创建结账、未付款，也未保存输入的凭证。")
        print("请尽快完成 Postman 请求；改账号、活动或出口后重新生成。")
        if gateway.enabled and gateway.use_clash:
            print("Clash 中转已开启。保持 Clash 和此窗口运行，按本次端口配置 Postman。")
            input("请求完成后回到这里按回车，关闭本次临时转发：")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\n已结束。")
        return 130
    except Exception:
        # Do not echo upstream errors, which may contain credentials or proxy URLs.
        print("\n生成失败。请检查 session、Node SDK 依赖、checkout 代理和 Clash；不要发送旧令牌。")
        return 1
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            relay_manager.close()


if __name__ == "__main__":
    raise SystemExit(main())
