# 个人 cs_ Custom：创建结账后怎样确认支付

只用于个人 Plus，且会话是 cs_ 开头。从你刚收到的**创建结账响应**开始：

```json
{
  "checkout_session_id": "cs_live_DEMO",
  "url": "https://chatgpt.com/checkout/openai_llc/cs_live_DEMO",
  "publishable_key": "pk_live_DEMO"
}
```

DEMO 是假数据。下面三项全部换成你**同一次响应**里的真实值：

| 要替换什么 | 去哪里复制 |
| --- | --- |
| 会话编号（cs_live_DEMO） | 创建结果 JSON 最外层 checkout_session_id；实际若叫 session_id / id，就复制那个值 |
| pk_live_DEMO | 创建结果 JSON 最外层 publishable_key；实际若叫 publishableKey，就复制那个值 |
| 完整结账地址 | 创建结果 JSON 最外层 url；实际若叫 checkout_url，就复制那个值 |

**创建结果 JSON**就是上面这份；**第N步响应 JSON**就是发送第N步后，Postman 下方 Body 返回的内容。比如 `payment_intent.client_secret`，就是展开 payment_intent，复制里面 client_secret 的值。

每步都按 **Import 整条 cURL → 按表替换 → Send** 操作。Authorization 选 No Auth；Stripe 的 Body 用 x-www-form-urlencoded，ChatGPT 的 Body 用 raw JSON。缺少三个创建字段、请求报错或需要验证时先停。确认步骤可能扣款，只发一次，超时先查询。

下面响应是字段结构示例，不是真实测试结果；只保留本流程用到的字段。DEMO、金额、币种都要以你自己的实际响应为准。

## 开始前：复制一次动态参数

已安装项目依赖后，在 PowerShell 运行折叠区整段命令；按提示填**原始 session JSON 文件路径**、刚才的结账地址、国家和会话编号。国家取创建请求 Body 的 billing_details.country。processor_entity 没返回就回车，脚本尝试从真实结账地址取。

<details>
<summary>展开复制命令，不用读 Python 代码</summary>

```powershell
Set-Location 'G:\aa\kaiyuanxinagmu\gpt-subscribe-studio-1'
$env:PYTHONPATH = "$PWD\packages\contracts\src;$PWD\packages\core\src"
$env:NODE_PATH = "$PWD\.tmp\sentinel-node\node_modules"
$env:PYTHONIOENCODING = 'utf-8'
$env:GSS_PROXY_CONFIG = "$PWD\runtime\proxy-gateways.json"
$env:GSS_PAYMENT_SESSION_FILE = (Read-Host '完整 session JSON 文件路径').Trim().Trim('"')
$env:GSS_PAYMENT_CHECKOUT_URL = (Read-Host '本次 ChatGPT 结账完整 URL').Trim()
$env:GSS_PAYMENT_COUNTRY = (Read-Host '本次账单国家代码，例如 US / PH / JP').Trim()
$env:GSS_PAYMENT_CHECKOUT_ID = (Read-Host '本次完整会话ID').Trim()
$env:GSS_PAYMENT_PROCESSOR = (Read-Host '创建响应的processor_entity，没有留空').Trim()
@'
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, unquote
from gss_core.chatgpt import ChatGPTClient, stripe_verify_url
from gss_core.countries import is_supported, normalize_country, locale_for, timezone_for
from gss_core.proxies import GatewayStore
from gss_core.proxy_relay import relay_manager

client = None
try:
    country = normalize_country(os.environ["GSS_PAYMENT_COUNTRY"])
    sid = os.environ["GSS_PAYMENT_CHECKOUT_ID"]
    page = os.environ["GSS_PAYMENT_CHECKOUT_URL"]
    p = urlsplit(page)
    if not is_supported(country):
        raise ValueError("国家不正确")
    if not sid.startswith("cs_"):
        raise ValueError("会话ID与流程不符")
    if p.scheme != "https" or p.hostname not in {"chatgpt.com", "pay.openai.com", "checkout.stripe.com"}:
        raise ValueError("需要本次真实结账HTTPS地址")
    if not Path(os.environ["GSS_PROXY_CONFIG"]).is_file():
        raise ValueError("找不到保存的代理配置")
    raw = Path(os.environ["GSS_PAYMENT_SESSION_FILE"]).read_text(encoding="utf-8-sig")
    json.loads(raw)
    gateway = GatewayStore().get("checkout")
    proxy = gateway.effective_proxy_url()
    client = ChatGPTClient.from_raw_session(raw, proxy=proxy)
    client.language, client.timezone = locale_for(country), timezone_for(country)
    processor = os.environ["GSS_PAYMENT_PROCESSOR"]
    parts = p.path.strip("/").split("/")
    if not processor and len(parts) > 1 and parts[0] == "checkout" and parts[1].startswith("openai_"):
        processor = parts[1]
    device = {k: str(uuid.uuid4()) + uuid.uuid4().hex[:6] for k in ("guid", "muid", "sid")}
    stripe_js_id = str(uuid.uuid4())
    timing = ""
    client.prepare_risk(flow="checkout_session_approval", page_url=page, country=country)
    device["client_session_id"] = stripe_js_id
    headers = {k.lower(): v for k, v in client._identity_headers().items()}
    headers["openai-sentinel-token"] = client.sentinel_token
    headers["openai-sentinel-so-token"] = client.sentinel_so
    headers["oai-web-deployment-attestation"] = client.attestation
    result = {
        "billing_country": country, "language": client.language,
        "locale_short": client.language.split("-")[0], "timezone": client.timezone,
        "checkout_url": page, "processor_entity": processor,
        "return_url": stripe_verify_url(sid, processor=processor, plan="plus"),
        "stripe_js_id": stripe_js_id, "device": device,
        "rv_timestamp": timing, "started_ms": int(time.time() * 1000), "headers": headers,
    }
    print("\n===== 准备结果 JSON（不另存文件） =====")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("方便直接复制的原始请求头（不含JSON转义）：")
    for key, value in headers.items():
        if value:
            print(key + "=" + value)
    if proxy:
        p = urlsplit(proxy)
        print("Postman代理协议、主机、端口：", p.scheme, p.hostname, p.port)
        print("代理用户名：", unquote(p.username or ""))
        print("代理密码：", unquote(p.password or ""))
    else:
        print("未启用应用代理，Postman应使用相同电脑网络路由。")
    print("下面请求需要的动态参数已经输出，没有确认支付。", flush=True)
    if gateway.enabled and gateway.use_clash:
        print("保持Clash和此窗口运行；请求完成后按Ctrl+C退出。", flush=True)
        while True:
            time.sleep(1)
except (KeyboardInterrupt, EOFError):
    print("已结束。")
except Exception:
    print("准备失败，请检查输入、文件、依赖和代理，不使用旧参数。")
finally:
    try:
        if client is not None:
            client.close()
    finally:
        relay_manager.close()
'@ | .\.venv\Scripts\python.exe -u -
```

</details>

终端打印的 **准备结果 JSON** 用于下面的取值表。请求头优先复制终端 `头名=值` 等号后的原始整行，不带引号或 JSON 转义符。脚本生成本次支付需要的 Sentinel，不用浏览器抓包，也不使用创建结账时的旧令牌。 若准备结果 headers.openai-sentinel-so-token 或 headers.oai-web-deployment-attestation 有值，给 ChatGPT 请求添加同名头；空值不添加，不发给 Stripe。

**代理只设置一次：**按终端打印的协议、主机、端口和认证配置 Postman；网页代理不会自动传给 Postman。Clash 中转开启时保持 Clash 和这个命令窗口运行；未启用项目代理时，Postman 使用相同电脑路由。

## 第1步：把卡片换成支付方式 pm_【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_methods' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'type=card' \
  --data-urlencode 'card[number]=CARD_NUMBER_EXAMPLE' \
  --data-urlencode 'card[exp_month]=EXP_MONTH_EXAMPLE' \
  --data-urlencode 'card[exp_year]=EXP_YEAR_EXAMPLE' \
  --data-urlencode 'card[cvc]=CVC_EXAMPLE' \
  --data-urlencode 'billing_details[name]=NAME_EXAMPLE' \
  --data-urlencode 'billing_details[email]=EMAIL_EXAMPLE' \
  --data-urlencode 'billing_details[address][country]=COUNTRY_EXAMPLE' \
  --data-urlencode 'billing_details[address][line1]=LINE1_EXAMPLE' \
  --data-urlencode 'billing_details[address][city]=CITY_EXAMPLE' \
  --data-urlencode 'billing_details[address][state]=STATE_EXAMPLE' \
  --data-urlencode 'billing_details[address][postal_code]=POSTAL_CODE_EXAMPLE' \
  --data-urlencode '_stripe_version=2025-03-31.basil'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| CARD_NUMBER_EXAMPLE | Body → card[number] | 自己填写本人获授权使用的卡号，只填数字（不在 JSON 里） |
| EXP_MONTH_EXAMPLE | Body → card[exp_month] | 自己填写卡片到期月份，例如 09（不在 JSON 里） |
| EXP_YEAR_EXAMPLE | Body → card[exp_year] | 自己填写卡片到期四位年份（不在 JSON 里） |
| CVC_EXAMPLE | Body → card[cvc] | 自己填写卡片安全码（不在 JSON 里） |
| NAME_EXAMPLE | Body → billing_details[name] | 自己填写持卡人真实账单姓名（不在 JSON 里） |
| EMAIL_EXAMPLE | Body → billing_details[email] | 自己填写持卡人真实账单邮箱（不在 JSON 里） |
| COUNTRY_EXAMPLE | Body → billing_details[address][country] | 准备结果 JSON → billing_country；它来自创建请求 JSON → billing_details.country |
| LINE1_EXAMPLE | Body → billing_details[address][line1] | 自己填写卡片账单街道地址（不在 JSON 里） |
| CITY_EXAMPLE | Body → billing_details[address][city] | 自己填写卡片账单城市（不在 JSON 里） |
| STATE_EXAMPLE | Body → billing_details[address][state] | 自己填写卡片账单州/省；当地不适用时留空，美国通常填真实州代码（不在 JSON 里） |
| POSTAL_CODE_EXAMPLE | Body → billing_details[address][postal_code] | 自己填写卡片账单邮编（不在 JSON 里） |

**响应示例（节选）：**

```json
{
  "id": "pm_PERSONALDEMO",
  "type": "card"
}
```

**看这里：**复制最外层 id 的完整 pm_ 值，填到第2步 payment_method。

**成功后：**保存响应 JSON 最外层 id（完整 pm_），做第2步。

## 第2步：把 pm_ 换成 ctoken_【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/confirmation_tokens' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'payment_method=PAYMENT_METHOD_EXAMPLE' \
  --data-urlencode 'setup_future_usage=off_session' \
  --data-urlencode '_stripe_version=2025-03-31.basil'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| PAYMENT_METHOD_EXAMPLE | Body → payment_method | 第1步响应 JSON → id |

**响应示例（节选）：**

```json
{
  "id": "ctoken_PERSONALDEMO"
}
```

**看这里：**复制最外层 id 的完整 ctoken_ 值，填到第8步 confirmation_token；仅在仍可使用时，条件步骤第12步也使用它。

**成功后：**保存响应 JSON 最外层 id（完整 ctoken_），做第3步。

## 第3步：同步账单税费【准备】

```bash
curl --request POST 'https://chatgpt.com/backend-api/payments/checkout/taxes' \
  --header 'Authorization: Bearer ACCESS_TOKEN_EXAMPLE' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Accept: */*' \
  --header 'Accept-Language: ACCEPT_LANGUAGE_EXAMPLE' \
  --header 'Origin: https://chatgpt.com' \
  --header 'Content-Type: application/json' \
  --header 'oai-did: DEVICE_ID_EXAMPLE' \
  --header 'oai-device-id: DEVICE_ID_EXAMPLE' \
  --header 'oai-language: LANGUAGE_EXAMPLE' \
  --header 'oai-telemetry: production' \
  --header 'oai-session-id: SESSION_ID_EXAMPLE' \
  --header 'oai-client-version: CLIENT_VERSION_EXAMPLE' \
  --header 'oai-client-build-number: CLIENT_BUILD_EXAMPLE' \
  --header 'sec-fetch-dest: empty' \
  --header 'sec-fetch-mode: cors' \
  --header 'sec-fetch-site: same-origin' \
  --header 'sec-ch-ua: "Google Chrome";v="136", "Not.A/Brand";v="8", "Chromium";v="136"' \
  --header 'sec-ch-ua-mobile: ?0' \
  --header 'sec-ch-ua-platform: "Windows"' \
  --header 'Cookie: COOKIE_EXAMPLE' \
  --header 'chatgpt-account-id: ACCOUNT_ID_EXAMPLE' \
  --header 'openai-sentinel-token: APPROVAL_SENTINEL_EXAMPLE' \
  --header 'x-openai-target-path: /backend-api/payments/checkout/taxes' \
  --header 'x-openai-target-route: /backend-api/payments/checkout/taxes' \
  --header 'originator: Codex Browser' \
  --header 'x-openai-web-frontend: codex_webview' \
  --header 'x-openai-codex-window-type: browser' \
  --header 'x-oai-mcp-form-version: 2' \
  --header 'x-openai-checkout-source: chatgpt_web_merged' \
  --header 'Referer: CHECKOUT_URL_EXAMPLE' \
  --data-raw '{
  "checkout_session_id": "cs_live_DEMO",
  "tax_id": null,
  "processor_entity": "PROCESSOR_EXAMPLE",
  "currency": "CURRENCY_EXAMPLE",
  "billing_country": "COUNTRY_EXAMPLE",
  "billing_name": "NAME_EXAMPLE",
  "billing_address": {
    "line1": "LINE1_EXAMPLE",
    "city": "CITY_EXAMPLE",
    "state": "STATE_EXAMPLE",
    "postal_code": "POSTAL_CODE_EXAMPLE",
    "country": "COUNTRY_EXAMPLE"
  }
}'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| ACCESS_TOKEN_EXAMPLE | Headers → Authorization | 原始 session JSON 最外层 → accessToken；只复制值，Authorization 中保留 Bearer 和空格 |
| ACCEPT_LANGUAGE_EXAMPLE | Headers → Accept-Language | 准备结果 JSON → headers.accept-language |
| DEVICE_ID_EXAMPLE | Headers → oai-did；Headers → oai-device-id | 原始 session JSON → statsigContext → deviceId；两处设备头填同一个值 |
| LANGUAGE_EXAMPLE | Headers → oai-language | 准备结果 JSON → language |
| SESSION_ID_EXAMPLE | Headers → oai-session-id | 准备结果 JSON → headers.oai-session-id |
| CLIENT_VERSION_EXAMPLE | Headers → oai-client-version | 准备结果 JSON → headers.oai-client-version |
| CLIENT_BUILD_EXAMPLE | Headers → oai-client-build-number | 准备结果 JSON → headers.oai-client-build-number |
| COOKIE_EXAMPLE | Headers → Cookie | 准备结果 JSON → headers.cookie，复制完整值 |
| ACCOUNT_ID_EXAMPLE | Headers → chatgpt-account-id | 原始 session JSON → account → id；只复制 id 的值 |
| APPROVAL_SENTINEL_EXAMPLE | Headers → openai-sentinel-token | 准备结果 JSON → headers.openai-sentinel-token，完整复制；不是创建结账用途的旧令牌 |
| CHECKOUT_URL_EXAMPLE | Headers → Referer | 创建结果 JSON 最外层 → url（实际字段若叫 checkout_url 就取它）；完整复制 https 地址 |
| cs_live_DEMO | Body.checkout_session_id | 创建结果 JSON → checkout_session_id，复制完整值 |
| PROCESSOR_EXAMPLE | Body.processor_entity | 准备结果 JSON 最外层 → processor_entity；脚本从创建结果的真实 URL 中提取 openai_ 商户段；为空先停止 |
| CURRENCY_EXAMPLE | Body.currency | 创建请求 JSON → billing_details.currency，如 PHP / USD；ChatGPT 税费 JSON 沿用这次创建结账的币种 |
| COUNTRY_EXAMPLE | Body.billing_country；Body.billing_address.country | 准备结果 JSON → billing_country；它来自创建请求 JSON → billing_details.country |
| NAME_EXAMPLE | Body.billing_name | 自己填写持卡人真实账单姓名（不在 JSON 里） |
| LINE1_EXAMPLE | Body.billing_address.line1 | 自己填写卡片账单街道地址（不在 JSON 里） |
| CITY_EXAMPLE | Body.billing_address.city | 自己填写卡片账单城市（不在 JSON 里） |
| STATE_EXAMPLE | Body.billing_address.state | 自己填写卡片账单州/省；当地不适用时留空，美国通常填真实州代码（不在 JSON 里） |
| POSTAL_CODE_EXAMPLE | Body.billing_address.postal_code | 自己填写卡片账单邮编（不在 JSON 里） |

**响应示例（节选）：**

```json
{
  "snapshot": {
    "amount_total": 1000
  },
  "currency": "php"
}
```

**看这里：**展开 snapshot，保存 amount_total 的整数；后面第7步和第8步优先用这个金额。1000、php 都只是示例。

**成功后：**保存本步响应 JSON，特别是 snapshot.amount_total，做第4步。

## 第4步：清除税号字段【准备】

```bash
curl --request POST 'https://chatgpt.com/backend-api/payments/checkout/update_tax_id' \
  --header 'Authorization: Bearer ACCESS_TOKEN_EXAMPLE' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Accept: */*' \
  --header 'Accept-Language: ACCEPT_LANGUAGE_EXAMPLE' \
  --header 'Origin: https://chatgpt.com' \
  --header 'Content-Type: application/json' \
  --header 'oai-did: DEVICE_ID_EXAMPLE' \
  --header 'oai-device-id: DEVICE_ID_EXAMPLE' \
  --header 'oai-language: LANGUAGE_EXAMPLE' \
  --header 'oai-telemetry: production' \
  --header 'oai-session-id: SESSION_ID_EXAMPLE' \
  --header 'oai-client-version: CLIENT_VERSION_EXAMPLE' \
  --header 'oai-client-build-number: CLIENT_BUILD_EXAMPLE' \
  --header 'sec-fetch-dest: empty' \
  --header 'sec-fetch-mode: cors' \
  --header 'sec-fetch-site: same-origin' \
  --header 'sec-ch-ua: "Google Chrome";v="136", "Not.A/Brand";v="8", "Chromium";v="136"' \
  --header 'sec-ch-ua-mobile: ?0' \
  --header 'sec-ch-ua-platform: "Windows"' \
  --header 'Cookie: COOKIE_EXAMPLE' \
  --header 'chatgpt-account-id: ACCOUNT_ID_EXAMPLE' \
  --header 'openai-sentinel-token: APPROVAL_SENTINEL_EXAMPLE' \
  --header 'x-openai-target-path: /backend-api/payments/checkout/update_tax_id' \
  --header 'x-openai-target-route: /backend-api/payments/checkout/update_tax_id' \
  --header 'originator: Codex Browser' \
  --header 'x-openai-web-frontend: codex_webview' \
  --header 'x-openai-codex-window-type: browser' \
  --header 'x-oai-mcp-form-version: 2' \
  --header 'x-openai-checkout-source: chatgpt_web_merged' \
  --header 'Referer: CHECKOUT_URL_EXAMPLE' \
  --data-raw '{
  "checkout_session_id": "cs_live_DEMO",
  "tax_id_info": null
}'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| ACCESS_TOKEN_EXAMPLE | Headers → Authorization | 原始 session JSON 最外层 → accessToken；只复制值，Authorization 中保留 Bearer 和空格 |
| ACCEPT_LANGUAGE_EXAMPLE | Headers → Accept-Language | 准备结果 JSON → headers.accept-language |
| DEVICE_ID_EXAMPLE | Headers → oai-did；Headers → oai-device-id | 原始 session JSON → statsigContext → deviceId；两处设备头填同一个值 |
| LANGUAGE_EXAMPLE | Headers → oai-language | 准备结果 JSON → language |
| SESSION_ID_EXAMPLE | Headers → oai-session-id | 准备结果 JSON → headers.oai-session-id |
| CLIENT_VERSION_EXAMPLE | Headers → oai-client-version | 准备结果 JSON → headers.oai-client-version |
| CLIENT_BUILD_EXAMPLE | Headers → oai-client-build-number | 准备结果 JSON → headers.oai-client-build-number |
| COOKIE_EXAMPLE | Headers → Cookie | 准备结果 JSON → headers.cookie，复制完整值 |
| ACCOUNT_ID_EXAMPLE | Headers → chatgpt-account-id | 原始 session JSON → account → id；只复制 id 的值 |
| APPROVAL_SENTINEL_EXAMPLE | Headers → openai-sentinel-token | 准备结果 JSON → headers.openai-sentinel-token，完整复制；不是创建结账用途的旧令牌 |
| CHECKOUT_URL_EXAMPLE | Headers → Referer | 创建结果 JSON 最外层 → url（实际字段若叫 checkout_url 就取它）；完整复制 https 地址 |
| cs_live_DEMO | Body.checkout_session_id | 创建结果 JSON → checkout_session_id，复制完整值 |

**响应示例（节选）：**

```json
{}
```

**看这里：**本步不取响应字段；空对象只是示意，项目不读取这个接口的响应体，实际也可能为空。

**成功后：**正常返回且没有 error，做第5步。

## 第5步：初始化 Stripe Custom 会话【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_DEMO/init' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'browser_locale=LANGUAGE_EXAMPLE' \
  --data-urlencode 'browser_timezone=TIMEZONE_EXAMPLE' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode '_stripe_version=2025-03-31.basil; checkout_server_update_beta=v1; checkout_manual_approval_preview=v1' \
  --data-urlencode 'elements_session_client[client_betas][0]=custom_checkout_server_updates_1' \
  --data-urlencode 'elements_session_client[client_betas][1]=custom_checkout_manual_approval_1' \
  --data-urlencode 'elements_session_client[elements_init_source]=custom_checkout' \
  --data-urlencode 'elements_session_client[referrer_host]=chatgpt.com' \
  --data-urlencode 'elements_session_client[stripe_js_id]=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'elements_session_client[locale]=LOCALE_SHORT_EXAMPLE' \
  --data-urlencode 'elements_session_client[is_aggregation_expected]=false'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_DEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| LANGUAGE_EXAMPLE | Body → browser_locale | 准备结果 JSON → language |
| TIMEZONE_EXAMPLE | Body → browser_timezone | 准备结果 JSON → timezone |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| STRIPE_JS_ID_EXAMPLE | Body → elements_session_client[stripe_js_id] | 准备结果 JSON → stripe_js_id，后续保持相同 |
| LOCALE_SHORT_EXAMPLE | Body → elements_session_client[locale] | 准备结果 JSON → locale_short，例如 en-PH 对应 en |

**响应示例（节选）：**

```json
{
  "config_id": "config_PERSONAL_INIT_DEMO",
  "currency": "php",
  "total_summary": {
    "due": 1000
  },
  "elements_session_id": "es_PERSONAL_INIT_DEMO"
}
```

**看这里：**保存 config_id、currency、total_summary.due、elements_session_id。示例没有返回校验字段，第8步按参数表删除没有实际值的校验字段，不自己编。

**成功后：**保存本步响应 JSON 的 currency、config_id、total_summary.due，以及实际返回的校验字段，做第6步。

## 第6步：更新真实账单地址和报价【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_DEMO' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode '_stripe_version=2025-03-31.basil; checkout_server_update_beta=v1; checkout_manual_approval_preview=v1' \
  --data-urlencode 'elements_session_client[client_betas][0]=custom_checkout_server_updates_1' \
  --data-urlencode 'elements_session_client[client_betas][1]=custom_checkout_manual_approval_1' \
  --data-urlencode 'elements_session_client[elements_init_source]=custom_checkout' \
  --data-urlencode 'elements_session_client[referrer_host]=chatgpt.com' \
  --data-urlencode 'elements_session_client[stripe_js_id]=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'elements_session_client[locale]=LOCALE_SHORT_EXAMPLE' \
  --data-urlencode 'elements_session_client[is_aggregation_expected]=false' \
  --data-urlencode 'tax_region[country]=COUNTRY_EXAMPLE' \
  --data-urlencode 'tax_region[state]=STATE_EXAMPLE' \
  --data-urlencode 'tax_region[postal_code]=POSTAL_CODE_EXAMPLE' \
  --data-urlencode 'tax_region[line1]=LINE1_EXAMPLE' \
  --data-urlencode 'tax_region[city]=CITY_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_DEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| STRIPE_JS_ID_EXAMPLE | Body → elements_session_client[stripe_js_id] | 准备结果 JSON → stripe_js_id，后续保持相同 |
| LOCALE_SHORT_EXAMPLE | Body → elements_session_client[locale] | 准备结果 JSON → locale_short，例如 en-PH 对应 en |
| COUNTRY_EXAMPLE | Body → tax_region[country] | 准备结果 JSON → billing_country；它来自创建请求 JSON → billing_details.country |
| STATE_EXAMPLE | Body → tax_region[state] | 自己填写卡片账单州/省；当地不适用时留空，美国通常填真实州代码（不在 JSON 里） |
| POSTAL_CODE_EXAMPLE | Body → tax_region[postal_code] | 自己填写卡片账单邮编（不在 JSON 里） |
| LINE1_EXAMPLE | Body → tax_region[line1] | 自己填写卡片账单街道地址（不在 JSON 里） |
| CITY_EXAMPLE | Body → tax_region[city] | 自己填写卡片账单城市（不在 JSON 里） |

**响应示例（节选）：**

```json
{
  "config_id": "config_PERSONAL_ADDRESS_DEMO",
  "currency": "php",
  "total_summary": {
    "due": 1000
  }
}
```

**看这里：**保存本步 config_id 和 total_summary.due。第3步若没有金额，后面才改用本步 due；实际为 0 就填 0。

**成功后：**保存本步响应 JSON，做第7步。金额优先取第3步 snapshot.amount_total；没有才取本步 total_summary.due，再没有才取第5步 total_summary.due。真实的 0 保留，没有金额就停止。

## 第7步：取得支付组件上下文【准备】

```bash
curl --request GET 'https://api.stripe.com/v1/elements/sessions' --get \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'type=deferred_intent' \
  --data-urlencode 'deferred_intent[mode]=subscription' \
  --data-urlencode 'deferred_intent[amount]=AMOUNT_MINOR_EXAMPLE' \
  --data-urlencode 'deferred_intent[currency]=CURRENCY_EXAMPLE' \
  --data-urlencode 'deferred_intent[setup_future_usage]=off_session' \
  --data-urlencode 'deferred_intent[payment_method_types][0]=card' \
  --data-urlencode 'deferred_intent[payment_method_types][1]=link' \
  --data-urlencode 'checkout_session_id=cs_live_DEMO' \
  --data-urlencode 'stripe_js_id=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode '_stripe_version=2025-03-31.basil; checkout_server_update_beta=v1; checkout_manual_approval_preview=v1' \
  --data-urlencode 'elements_init_source=custom_checkout' \
  --data-urlencode 'referrer_host=chatgpt.com' \
  --data-urlencode 'locale=LOCALE_SHORT_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| AMOUNT_MINOR_EXAMPLE | Params → deferred_intent[amount] | 优先第3步响应 JSON → snapshot.amount_total；缺失才取 第6步 total_summary.due，再缺失才取 第5步 total_summary.due；复制实际整数，含 0 |
| CURRENCY_EXAMPLE | Params → deferred_intent[currency] | 第5步响应 JSON → currency，转小写；缺失取创建请求 JSON → billing_details.currency，转小写；仍没有就停止 |
| cs_live_DEMO | Params → checkout_session_id | 创建结果 JSON → checkout_session_id，复制完整值 |
| STRIPE_JS_ID_EXAMPLE | Params → stripe_js_id | 准备结果 JSON → stripe_js_id，后续保持相同 |
| pk_live_DEMO | Params → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| LOCALE_SHORT_EXAMPLE | Params → locale | 准备结果 JSON → locale_short，例如 en-PH 对应 en |

**响应示例（节选）：**

```json
{
  "session_id": "es_PERSONALDEMO",
  "config_id": "config_PERSONAL_ELEMENTS_DEMO"
}
```

**看这里：**session_id 填第8步所有 ELEMENTS_ID_EXAMPLE；config_id 填第8步所有 CONFIG_ID_EXAMPLE。同一标记出现多处时全部替换。

**成功后：**保存响应 JSON 最外层 session_id 和 config_id，做第8步；若缺少，按第8步参数表处理，不自己编。

## 第8步：确认支付【可能扣款】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_DEMO/confirm' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode '_stripe_version=2025-03-31.basil; checkout_server_update_beta=v1; checkout_manual_approval_preview=v1' \
  --data-urlencode 'confirmation_token=CONFIRMATION_TOKEN_EXAMPLE' \
  --data-urlencode 'expected_payment_method_type=card' \
  --data-urlencode 'expected_amount=AMOUNT_MINOR_EXAMPLE' \
  --data-urlencode 'return_url=RETURN_URL_EXAMPLE' \
  --data-urlencode 'consent[terms_of_service]=accepted' \
  --data-urlencode 'guid=GUID_EXAMPLE' \
  --data-urlencode 'muid=MUID_EXAMPLE' \
  --data-urlencode 'sid=SID_EXAMPLE' \
  --data-urlencode 'time_on_page=TIME_ON_PAGE_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[client_session_id]=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[checkout_session_id]=cs_live_DEMO' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_source]=checkout' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_version]=custom_checkout' \
  --data-urlencode 'client_attribution_metadata[payment_method_selection_flow]=automatic' \
  --data-urlencode 'elements_session_client[client_betas][0]=custom_checkout_server_updates_1' \
  --data-urlencode 'elements_session_client[client_betas][1]=custom_checkout_manual_approval_1' \
  --data-urlencode 'elements_session_client[elements_init_source]=custom_checkout' \
  --data-urlencode 'elements_session_client[referrer_host]=chatgpt.com' \
  --data-urlencode 'elements_session_client[stripe_js_id]=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'elements_session_client[locale]=LOCALE_SHORT_EXAMPLE' \
  --data-urlencode 'elements_session_client[is_aggregation_expected]=false' \
  --data-urlencode 'elements_session_client[session_id]=ELEMENTS_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[elements_session_config_id]=CONFIG_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[checkout_config_id]=CONFIG_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[elements_session_id]=ELEMENTS_ID_EXAMPLE' \
  --data-urlencode 'init_checksum=INIT_CHECKSUM_EXAMPLE' \
  --data-urlencode 'js_checksum=JS_CHECKSUM_EXAMPLE' \
  --data-urlencode 'rv_timestamp=CUSTOM_RV_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_DEMO | URL；Body → client_attribution_metadata[checkout_session_id] | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| CONFIRMATION_TOKEN_EXAMPLE | Body → confirmation_token | 第2步响应 JSON → id，完整 ctoken_ |
| AMOUNT_MINOR_EXAMPLE | Body → expected_amount | 优先第3步响应 JSON → snapshot.amount_total；缺失才取 第6步 total_summary.due，再缺失才取 第5步 total_summary.due；复制实际整数，含 0 |
| RETURN_URL_EXAMPLE | Body → return_url | 准备结果 JSON 最外层 → return_url；这是脚本按会话 ID、商户和套餐拼好的完整地址，不是把结账 URL 原样填进来 |
| GUID_EXAMPLE | Body → guid | 准备结果 JSON → device.guid |
| MUID_EXAMPLE | Body → muid | 准备结果 JSON → device.muid |
| SID_EXAMPLE | Body → sid | 准备结果 JSON → device.sid；不是代理供应商账号的 SID |
| TIME_ON_PAGE_EXAMPLE | Body → time_on_page | 取最初准备结果 JSON → started_ms，在 PowerShell 执行 `[Math]::Max(8000, [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - [long](Read-Host "粘贴started_ms"))`；粘贴 started_ms 后回车，把输出整数填到这里 |
| STRIPE_JS_ID_EXAMPLE | Body → client_attribution_metadata[client_session_id]；Body → elements_session_client[stripe_js_id] | 准备结果 JSON → stripe_js_id，后续保持相同 |
| LOCALE_SHORT_EXAMPLE | Body → elements_session_client[locale] | 准备结果 JSON → locale_short，例如 en-PH 对应 en |
| ELEMENTS_ID_EXAMPLE | Body → elements_session_client[session_id]；Body → client_attribution_metadata[elements_session_id] | 第7步响应 JSON → session_id；没有时取 第5步 elements_session_id；仍没有则删除所有含 ELEMENTS_ID_EXAMPLE 的表单行 |
| CONFIG_ID_EXAMPLE | Body → client_attribution_metadata[elements_session_config_id]；Body → client_attribution_metadata[checkout_config_id] | 第7步响应 JSON → config_id；没有时取 第5步 config_id；仍没有则删除全部含 CONFIG_ID_EXAMPLE 的表单行 |
| INIT_CHECKSUM_EXAMPLE | Body → init_checksum | 第5步响应 JSON → init_checksum；缺失才看 第6步 同名字段；都无值则删除整行 |
| JS_CHECKSUM_EXAMPLE | Body → js_checksum | 第5步响应 JSON → js_checksum；缺失才看 第6步 同名字段；都无值则删除整行 |
| CUSTOM_RV_EXAMPLE | Body → rv_timestamp | 第5步响应 JSON → rv_timestamp；缺失才看 第6步 同名字段；都无值则删除整行 |

**响应示例（节选）：**

```json
{
  "submission_attempt": {
    "state": "processing"
  },
  "payment_intent": {
    "id": "pi_CUSTOMDEMO",
    "client_secret": "pi_CUSTOMDEMO_secret_DEMO",
    "status": "processing"
  }
}
```

**看这里：**processing 表示正在处理。保存完整 payment_intent.id、payment_intent.client_secret；第11步查询时可能要用，不把 secret 当会话 ID。

**成功后：**只发送一次，然后做第9步查询。确认超时也先查询，不重复本步。

## 第9步：查询本次支付页【只读】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_DEMO/poll' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode '_stripe_version=2025-03-31.basil; checkout_server_update_beta=v1; checkout_manual_approval_preview=v1' \
  --data-urlencode 'elements_session_client[client_betas][0]=custom_checkout_server_updates_1' \
  --data-urlencode 'elements_session_client[client_betas][1]=custom_checkout_manual_approval_1' \
  --data-urlencode 'elements_session_client[elements_init_source]=custom_checkout' \
  --data-urlencode 'elements_session_client[referrer_host]=chatgpt.com' \
  --data-urlencode 'elements_session_client[stripe_js_id]=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'elements_session_client[locale]=LOCALE_SHORT_EXAMPLE' \
  --data-urlencode 'elements_session_client[is_aggregation_expected]=false' \
  --data-urlencode 'elements_session_client[session_id]=ELEMENTS_ID_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_DEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| STRIPE_JS_ID_EXAMPLE | Body → elements_session_client[stripe_js_id] | 准备结果 JSON → stripe_js_id，后续保持相同 |
| LOCALE_SHORT_EXAMPLE | Body → elements_session_client[locale] | 准备结果 JSON → locale_short，例如 en-PH 对应 en |
| ELEMENTS_ID_EXAMPLE | Body → elements_session_client[session_id] | 第7步响应 JSON → session_id；没有时取 第5步 elements_session_id；仍没有则删除所有含 ELEMENTS_ID_EXAMPLE 的表单行 |

**响应示例（节选）：**

```json
{
  "submission_attempt": {
    "state": "requires_approval"
  },
  "payment_intent": {
    "id": "pi_CUSTOMDEMO",
    "client_secret": "pi_CUSTOMDEMO_secret_DEMO",
    "status": "processing"
  }
}
```

**看这里：**这个例子 submission_attempt.state=requires_approval，才做第10步。审批后回本步再查，状态可能改变；不要照着示例期待它一直是 requires_approval。

**成功后：**本次 payment_intent.status=succeeded：结束并核对订阅。仅 submission_attempt.state=requires_approval 或 pending_approval 时，做第10步。返回了 payment_intent.id 和 client_secret 可做第11步核对；处理中只继续本步查询，验证要求或错误先停止。

## 第10步：仅第9步明确需要审批时，批准结账

```bash
curl --request POST 'https://chatgpt.com/backend-api/payments/checkout/approve' \
  --header 'Authorization: Bearer ACCESS_TOKEN_EXAMPLE' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Accept: */*' \
  --header 'Accept-Language: ACCEPT_LANGUAGE_EXAMPLE' \
  --header 'Origin: https://chatgpt.com' \
  --header 'Content-Type: application/json' \
  --header 'oai-did: DEVICE_ID_EXAMPLE' \
  --header 'oai-device-id: DEVICE_ID_EXAMPLE' \
  --header 'oai-language: LANGUAGE_EXAMPLE' \
  --header 'oai-telemetry: production' \
  --header 'oai-session-id: SESSION_ID_EXAMPLE' \
  --header 'oai-client-version: CLIENT_VERSION_EXAMPLE' \
  --header 'oai-client-build-number: CLIENT_BUILD_EXAMPLE' \
  --header 'sec-fetch-dest: empty' \
  --header 'sec-fetch-mode: cors' \
  --header 'sec-fetch-site: same-origin' \
  --header 'sec-ch-ua: "Google Chrome";v="136", "Not.A/Brand";v="8", "Chromium";v="136"' \
  --header 'sec-ch-ua-mobile: ?0' \
  --header 'sec-ch-ua-platform: "Windows"' \
  --header 'Cookie: COOKIE_EXAMPLE' \
  --header 'chatgpt-account-id: ACCOUNT_ID_EXAMPLE' \
  --header 'openai-sentinel-token: APPROVAL_SENTINEL_EXAMPLE' \
  --header 'x-openai-target-path: /backend-api/payments/checkout/approve' \
  --header 'x-openai-target-route: /backend-api/payments/checkout/approve' \
  --header 'originator: Codex Browser' \
  --header 'x-openai-web-frontend: codex_webview' \
  --header 'x-openai-codex-window-type: browser' \
  --header 'x-oai-mcp-form-version: 2' \
  --header 'x-openai-checkout-source: chatgpt_web_merged' \
  --header 'Referer: CHECKOUT_URL_EXAMPLE' \
  --header 'x-oai-is-client-observation: true' \
  --data-raw '{
  "checkout_session_id": "cs_live_DEMO",
  "processor_entity": "PROCESSOR_EXAMPLE"
}'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| ACCESS_TOKEN_EXAMPLE | Headers → Authorization | 原始 session JSON 最外层 → accessToken；只复制值，Authorization 中保留 Bearer 和空格 |
| ACCEPT_LANGUAGE_EXAMPLE | Headers → Accept-Language | 准备结果 JSON → headers.accept-language |
| DEVICE_ID_EXAMPLE | Headers → oai-did；Headers → oai-device-id | 原始 session JSON → statsigContext → deviceId；两处设备头填同一个值 |
| LANGUAGE_EXAMPLE | Headers → oai-language | 准备结果 JSON → language |
| SESSION_ID_EXAMPLE | Headers → oai-session-id | 准备结果 JSON → headers.oai-session-id |
| CLIENT_VERSION_EXAMPLE | Headers → oai-client-version | 准备结果 JSON → headers.oai-client-version |
| CLIENT_BUILD_EXAMPLE | Headers → oai-client-build-number | 准备结果 JSON → headers.oai-client-build-number |
| COOKIE_EXAMPLE | Headers → Cookie | 准备结果 JSON → headers.cookie，复制完整值 |
| ACCOUNT_ID_EXAMPLE | Headers → chatgpt-account-id | 原始 session JSON → account → id；只复制 id 的值 |
| APPROVAL_SENTINEL_EXAMPLE | Headers → openai-sentinel-token | 再运行页首准备命令，复制这次新输出的 headers.openai-sentinel-token；本步其它 ChatGPT 请求头也用这次新值，原 Stripe 参数仍保留第一次的值 |
| CHECKOUT_URL_EXAMPLE | Headers → Referer | 创建结果 JSON 最外层 → url（实际字段若叫 checkout_url 就取它）；完整复制 https 地址 |
| cs_live_DEMO | Body.checkout_session_id | 创建结果 JSON → checkout_session_id，复制完整值 |
| PROCESSOR_EXAMPLE | Body.processor_entity | 准备结果 JSON 最外层 → processor_entity；脚本从创建结果的真实 URL 中提取 openai_ 商户段；为空先停止 |

**响应示例（节选）：**

```json
{}
```

**看这里：**本步不需要复制响应字段；源码不要求固定响应结构，这里用空对象示意。HTTP 正常返回也不代表已付款，仍回第9步查。

**成功后：**只更新本步 ChatGPT 请求头；若准备脚本输出新代理端口，同步更新 Postman 代理。第9步查询仍使用第一次的 stripe_js_id 等 Stripe 参数。然后回第9步查询，不重新执行第8步。

## 第11步：仅返回了实际 pi_ 和 client_secret 时，查询这笔付款

```bash
curl --request GET 'https://api.stripe.com/v1/payment_intents/INTENT_ID_EXAMPLE' --get \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'client_secret=INTENT_SECRET_EXAMPLE' \
  --data-urlencode '_stripe_version=2025-03-31.basil'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| INTENT_ID_EXAMPLE | URL | 第8步 或 第9步响应 JSON → payment_intent.id，完整 pi_；只有 secret 时取 _secret_ 前部分 |
| pk_live_DEMO | Params → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| INTENT_SECRET_EXAMPLE | Params → client_secret | 同一步、同一个 payment_intent.client_secret，或实际顶层 client_secret |

**响应示例（节选）：**

```json
{
  "id": "pi_CUSTOMDEMO",
  "client_secret": "pi_CUSTOMDEMO_secret_DEMO",
  "status": "requires_confirmation"
}
```

**看这里：**只看本次真实 status。示例是 requires_confirmation，才考虑第12步；如果实际是 succeeded，直接结束，不再确认。

**成功后：**status=succeeded：结束并核对订阅；仅 requires_confirmation 且第2步 ctoken_ 仍未被消耗时做第12步。processing 只继续查询；需要验证、待扣款授权或错误先停。

## 第12步：仅第11步查到 requires_confirmation 时，确认这笔付款【可能扣款】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_intents/INTENT_ID_EXAMPLE/confirm' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'client_secret=INTENT_SECRET_EXAMPLE' \
  --data-urlencode '_stripe_version=2025-03-31.basil' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_source]=l1' \
  --data-urlencode 'confirmation_token=CONFIRMATION_TOKEN_EXAMPLE' \
  --data-urlencode 'return_url=RETURN_URL_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| INTENT_ID_EXAMPLE | URL | 第11步响应 JSON → id；未执行查询时取 第8步 / 第9步 响应 → payment_intent.id |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| INTENT_SECRET_EXAMPLE | Body → client_secret | 第8步 / 第9步 返回的同一 Intent 的 client_secret |
| CONFIRMATION_TOKEN_EXAMPLE | Body → confirmation_token | 第2步 ctoken_，须仍可用于本次确认，不跨会话复用 |
| RETURN_URL_EXAMPLE | Body → return_url | 准备结果 JSON 最外层 → return_url；这是脚本按会话 ID、商户和套餐拼好的完整地址，不是把结账 URL 原样填进来 |

**响应示例（节选）：**

```json
{
  "id": "pi_CUSTOMDEMO",
  "status": "succeeded"
}
```

**看这里：**status=succeeded 表示这笔付款成功；回第11步核对，不重新发送第8步。

**成功后：**回第11步查询；不要再发送第8步。实际返回 seti_ 时停止，不塞进 pi_ 的 URL。

源码：[chatgpt.py](../packages/core/src/gss_core/chatgpt.py)。仅离线核对文档，未执行真实支付。
