"""出口代理配置。提链与支付分阶段，互不覆盖。"""

from __future__ import annotations

import ipaddress
import time
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Request

from gss_core.proxies import ROLES, GatewayStore, describe_gateway, gateway_from_input
from gss_core.proxy_relay import relay_manager

router = APIRouter(prefix="/api/settings/proxies", tags=["settings"])


def store(request: Request) -> GatewayStore:
    return request.app.state.gateway_store


@router.get("")
async def get_proxies(request: Request):
    try:
        return {role: store(request).get(role).public() for role in ROLES}
    except (OSError, ValueError, TypeError):
        raise HTTPException(500, "代理配置读取失败")


@router.post("/parse")
async def parse_proxy(request: Request):
    """预览：把粘贴的代理串拆开，不保存。"""
    try:
        values = await request.json()
        return describe_gateway(gateway_from_input(str(values.get("raw", ""))))
    except ValueError as exc:
        raise HTTPException(400, str(exc) if type(exc) is ValueError else "代理格式不正确")
    except (TypeError, AttributeError):
        raise HTTPException(400, "代理格式不正确")


@router.put("")
async def save_proxy_all(request: Request):
    """保存同一个代理到提链与支付两个阶段，保证同一订单出口一致。"""
    try:
        values = await request.json()
        if not isinstance(values, dict) or set(values) - {"raw", "enabled", "use_clash", "clash_proxy_url"}:
            raise ValueError("代理配置字段不正确")
        # New raw input replaces credentials and resets routing defaults. Omitting
        # raw updates the saved settings without ever returning its credentials.
        gateway = (gateway_from_input(str(values["raw"])) if "raw" in values
                   else store(request).get("checkout"))
        for key in ("enabled", "use_clash", "clash_proxy_url"):
            if key in values:
                setattr(gateway, key, values[key])
        gateway = store(request).save_all(gateway)
        return describe_gateway(gateway)
    except ValueError as exc:
        raise HTTPException(400, str(exc) if type(exc) is ValueError else "代理格式不正确")
    except (TypeError, AttributeError, OSError):
        raise HTTPException(400, "代理配置保存失败，请检查参数与文件权限")


@router.put("/{role}")
async def save_proxy(role: str, request: Request):
    if role not in ROLES:
        raise HTTPException(404, "未知代理阶段")
    try:
        values = await request.json()
        gateway = store(request).save(role, values)
        return gateway.public()
    except ValueError as exc:
        message = str(exc) if type(exc) is ValueError else "代理配置格式不正确"
        raise HTTPException(400, message)
    except (TypeError, OSError):
        raise HTTPException(400, "代理配置保存失败，请检查参数与文件权限")


async def probe_gateway(proxy_url: str | None) -> dict:
    start = time.perf_counter()
    async with httpx.AsyncClient(
        proxy=proxy_url, timeout=12.0, follow_redirects=False, trust_env=False
    ) as client:
        response = await client.get("https://api64.ipify.org?format=json")
        response.raise_for_status()
        ip = str(ipaddress.ip_address(response.json()["ip"]))
    return {"ip": ip, "elapsed_ms": round((time.perf_counter() - start) * 1000)}


@router.post("/{role}/test")
async def test_proxy(role: str, request: Request):
    if role not in ROLES:
        raise HTTPException(404, "未知代理阶段")
    proxy_url = None
    try:
        gateway = store(request).get(role)
        proxy_url = gateway.effective_proxy_url()
        result = await probe_gateway(proxy_url)
        return {"role": role, "mode": gateway.mode, "region": gateway.region, "sid": gateway.sid, **result}
    except HTTPException:
        raise
    except Exception as exc:
        # socksio also raises errors outside httpx.HTTPError. Never return its
        # raw message, which can include a credential-bearing proxy URL.
        relay_error = None
        if proxy_url:
            parsed = urlsplit(proxy_url)
            if parsed.hostname == "127.0.0.1" and parsed.port:
                relay_error = relay_manager.failure_for(parsed.port)
        if relay_error:
            message = relay_error
        elif isinstance(exc, httpx.HTTPStatusError):
            message = f"出口测试网站返回 HTTP {exc.response.status_code}，不代表 ChatGPT 的可用性"
        elif isinstance(exc, httpx.ProxyError) or type(exc).__module__.startswith("socksio"):
            message = "供应商代理握手或认证失败，请检查协议、账号密码及来源 IP 限制"
        elif isinstance(exc, (ValueError, TypeError)):
            message = "代理配置或出口测试响应无效，请检查代理设置"
        else:
            message = "出口连接失败或超时，请检查网络、代理网关和测试网站是否可达"
        raise HTTPException(502, message) from None
