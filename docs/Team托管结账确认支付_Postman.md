# Team：创建托管结账后怎样确认支付

只用于已经创建的 Team 托管结账。从你刚收到的**创建结账响应**开始：

```json
{
  "checkout_session_id": "cs_live_TEAMDEMO",
  "url": "https://pay.openai.com/c/pay/cs_live_TEAMDEMO",
  "publishable_key": "pk_live_DEMO"
}
```

DEMO 是假数据。下面三项全部换成你**同一次响应**里的真实值：

| 要替换什么 | 去哪里复制 |
| --- | --- |
| 会话编号（cs_live_TEAMDEMO） | 创建结果 JSON 最外层 checkout_session_id；实际若叫 session_id / id，就复制那个值 |
| pk_live_DEMO | 创建结果 JSON 最外层 publishable_key；实际若叫 publishableKey，就复制那个值 |
| 完整结账地址 | 创建结果 JSON 最外层 url；实际若叫 checkout_url，就复制那个值 |

**创建结果 JSON**就是上面这份；**第N步响应 JSON**就是发送第N步后，Postman 下方 Body 返回的内容。比如 `payment_intent.client_secret`，就是展开 payment_intent，复制里面 client_secret 的值。

每步都按 **Import 整条 cURL → 按表替换 → Send** 操作。Authorization 选 No Auth；Stripe 的 Body 用 x-www-form-urlencoded，ChatGPT 的 Body 用 raw JSON。缺少三个创建字段、请求报错或需要验证时先停。确认步骤可能扣款，只发一次，超时先查询。

下面响应是字段结构示例，不是真实测试结果；只保留本流程用到的字段。DEMO、金额、币种都要以你自己的实际响应为准。

## 开始前：复制一次动态参数

已安装项目依赖后，在 PowerShell 运行下面整段命令，只输入**真实卡片账单国家**和**创建结果 JSON → checkout_session_id**。脚本准备设备标识、语言和时区，不读取 session JSON，也不需要 Sentinel。

<details>
<summary>展开复制命令，不用读 Python 代码</summary>

```powershell
Set-Location 'G:\aa\kaiyuanxinagmu\gpt-subscribe-studio-1'
$env:PYTHONPATH = "$PWD\packages\contracts\src;$PWD\packages\core\src"
$env:PYTHONIOENCODING = 'utf-8'
$env:GSS_PROXY_CONFIG = "$PWD\runtime\proxy-gateways.json"
$env:GSS_PAYMENT_COUNTRY = (Read-Host '本次账单国家代码，例如 US / PH / JP').Trim()
$env:GSS_PAYMENT_CHECKOUT_ID = (Read-Host '本次完整会话ID').Trim()
@'
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, unquote
from gss_core.chatgpt import ChatGPTClient
from gss_core.countries import is_supported, normalize_country, locale_for, timezone_for
from gss_core.proxies import GatewayStore
from gss_core.proxy_relay import relay_manager

client = None
try:
    country = normalize_country(os.environ["GSS_PAYMENT_COUNTRY"])
    sid = os.environ["GSS_PAYMENT_CHECKOUT_ID"]
    if not is_supported(country):
        raise ValueError("国家不正确")
    if not sid.startswith("cs_"):
        raise ValueError("会话ID与流程不符")
    if not Path(os.environ["GSS_PROXY_CONFIG"]).is_file():
        raise ValueError("找不到保存的代理配置")
    gateway = GatewayStore().get("checkout")
    proxy = gateway.effective_proxy_url()
    client = ChatGPTClient(access_token="", proxy=proxy)
    client.language, client.timezone = locale_for(country), timezone_for(country)
    stripe_js_id = str(uuid.uuid4())
    timing = ""
    from gss_core.hosted import TeamHostedClient
    from gss_core.fingerprint import register_device
    hosted = TeamHostedClient(client)
    device = register_device(client.stripe_http)
    timing = hosted.current_timing(sid)
    device["client_session_id"] = stripe_js_id
    result = {
        "billing_country": country, "language": client.language,
        "timezone": client.timezone,
        "stripe_js_id": stripe_js_id, "device": device,
        "rv_timestamp": timing,
    }
    print("\n===== 准备结果 JSON（不另存文件） =====")
    print(json.dumps(result, ensure_ascii=False, indent=2))
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

终端打印的 **准备结果 JSON** 就是下面参数表要用的那份 JSON；只复制字段的值，不带外层引号。

**代理只设置一次：**按终端打印的协议、主机、端口和认证配置 Postman；网页代理不会自动传给 Postman。Clash 中转开启时保持 Clash 和这个命令窗口运行；未启用项目代理时，Postman 使用相同电脑路由。

## 第1步：初始化 Team 页面【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO/init' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'eid=NA' \
  --data-urlencode 'redirect_type=url' \
  --data-urlencode 'browser_locale=LANGUAGE_EXAMPLE' \
  --data-urlencode 'browser_timezone=TIMEZONE_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| LANGUAGE_EXAMPLE | Body → browser_locale | 准备结果 JSON → language |
| TIMEZONE_EXAMPLE | Body → browser_timezone | 准备结果 JSON → timezone |

**响应示例（节选）：**

```json
{
  "eid": "eid_TEAMDEMO",
  "config_id": "config_TEAM_INIT_DEMO",
  "currency": "usd",
  "total_summary": {
    "due": 10000
  }
}
```

**看这里：**保存最外层 eid、config_id、currency，再展开 total_summary 保存 due。10000 是示例整数，不是固定 Team 价格。

**成功后：**保存响应 JSON 最外层 eid、config_id、currency 和 total_summary.due，做第2步；没有 eid 时按项目代码使用 NA。

## 第2步：选择真实卡片账单国家【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'eid=EID_EXAMPLE' \
  --data-urlencode 'tax_region[country]=COUNTRY_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| EID_EXAMPLE | Body → eid | 第1步响应 JSON → eid；没有该字段时固定填 NA |
| COUNTRY_EXAMPLE | Body → tax_region[country] | 准备结果 JSON → billing_country，就是刚才输入的真实卡片账单国家 |

**响应示例（节选）：**

```json
{
  "config_id": "config_TEAM_COUNTRY_DEMO",
  "currency": "usd",
  "total_summary": {
    "due": 10000
  }
}
```

**看这里：**这是国家设置后的报价示意；本步不需要额外复制新字段，第4步会再读取地址报价。

**成功后：**正常返回且没有 error，做第3步。

## 第3步：设置账单不使用企业税号

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'eid=EID_EXAMPLE' \
  --data-urlencode 'tax_id_collection[purchasing_as_business]=false'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| EID_EXAMPLE | Body → eid | 第1步响应 JSON → eid；没有该字段时固定填 NA |

**响应示例（节选）：**

```json
{
  "config_id": "config_TEAM_BUYER_DEMO"
}
```

**看这里：**本步不需要复制新字段；继续第4步提交账单地址。

**成功后：**正常返回且没有 error，做第4步。此处 purchasing_as_business=false 只是账单不使用企业税号，不改变已经创建的 Team 套餐。

## 第4步：提交完整地址，读取报价【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'eid=EID_EXAMPLE' \
  --data-urlencode 'tax_region[country]=COUNTRY_EXAMPLE' \
  --data-urlencode 'tax_region[state]=STATE_EXAMPLE' \
  --data-urlencode 'tax_region[postal_code]=POSTAL_CODE_EXAMPLE' \
  --data-urlencode 'tax_region[line1]=LINE1_EXAMPLE' \
  --data-urlencode 'tax_region[city]=CITY_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| EID_EXAMPLE | Body → eid | 第1步响应 JSON → eid；没有该字段时固定填 NA |
| COUNTRY_EXAMPLE | Body → tax_region[country] | 准备结果 JSON → billing_country，就是刚才输入的真实卡片账单国家 |
| STATE_EXAMPLE | Body → tax_region[state] | 自己填写卡片账单州/省；当地不适用时留空，美国通常填真实州代码（不在 JSON 里） |
| POSTAL_CODE_EXAMPLE | Body → tax_region[postal_code] | 自己填写卡片账单邮编（不在 JSON 里） |
| LINE1_EXAMPLE | Body → tax_region[line1] | 自己填写卡片账单街道地址（不在 JSON 里） |
| CITY_EXAMPLE | Body → tax_region[city] | 自己填写卡片账单城市（不在 JSON 里） |

**响应示例（节选）：**

```json
{
  "config_id": "config_TEAM_ADDRESS_DEMO",
  "total_summary": {
    "due": 10000
  }
}
```

**看这里：**复制本步 config_id 和 total_summary.due；第5步的金额先用本步 due，后面还会在第6步刷新。

**成功后：**保存响应 JSON 的 config_id、total_summary.due，做第5步；缺少时沿用第1步，实际 0 保留。

## 第5步：初始化 Team 支付组件【准备】

```bash
curl --request GET 'https://api.stripe.com/v1/elements/sessions' --get \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'type=deferred_intent' \
  --data-urlencode 'checkout_session_id=cs_live_TEAMDEMO' \
  --data-urlencode 'hosted_surface=checkout' \
  --data-urlencode 'elements_init_source=checkout' \
  --data-urlencode 'referrer_host=pay.openai.com' \
  --data-urlencode 'stripe_js_id=STRIPE_JS_ID_EXAMPLE' \
  --data-urlencode 'locale=LANGUAGE_EXAMPLE' \
  --data-urlencode 'browser_timezone=TIMEZONE_EXAMPLE' \
  --data-urlencode 'deferred_intent[mode]=subscription' \
  --data-urlencode 'deferred_intent[amount]=AMOUNT_MINOR_EXAMPLE' \
  --data-urlencode 'deferred_intent[currency]=CURRENCY_EXAMPLE' \
  --data-urlencode 'deferred_intent[setup_future_usage]=off_session' \
  --data-urlencode 'deferred_intent[payment_method_types][0]=card' \
  --data-urlencode 'client_betas[0]=google_pay_beta_1' \
  --data-urlencode 'client_betas[1]=disable_deferred_intent_client_validation_beta_1' \
  --data-urlencode 'client_betas[2]=blocked_card_brands_beta_2' \
  --data-urlencode '_stripe_version=2026-03-25.dahlia'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| pk_live_DEMO | Params → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| cs_live_TEAMDEMO | Params → checkout_session_id | 创建结果 JSON → checkout_session_id，复制完整值 |
| STRIPE_JS_ID_EXAMPLE | Params → stripe_js_id | 准备结果 JSON → stripe_js_id，后续保持相同 |
| LANGUAGE_EXAMPLE | Params → locale | 准备结果 JSON → language |
| TIMEZONE_EXAMPLE | Params → browser_timezone | 准备结果 JSON → timezone |
| AMOUNT_MINOR_EXAMPLE | Params → deferred_intent[amount] | 第4步响应 JSON → total_summary.due；没有新金额才用 第1步 due；实际 0 保留，缺失不能当 0 |
| CURRENCY_EXAMPLE | Params → deferred_intent[currency] | 第1步响应 JSON → currency，转小写；缺失可取创建请求 JSON → billing_details.currency，转小写；仍没有就停止 |

**响应示例（节选）：**

```json
{
  "session_id": "es_TEAMDEMO",
  "config_id": "config_TEAM_ELEMENTS_DEMO"
}
```

**看这里：**本步是支付组件的返回示意。不要拿这里的 config_id 直接付款，第6步还要取得最新报价配置。

**成功后：**正常返回且没有 error，做第6步。

## 第6步：重新提交地址，取得最终配置【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'eid=EID_EXAMPLE' \
  --data-urlencode 'tax_region[country]=COUNTRY_EXAMPLE' \
  --data-urlencode 'tax_region[state]=STATE_EXAMPLE' \
  --data-urlencode 'tax_region[postal_code]=POSTAL_CODE_EXAMPLE' \
  --data-urlencode 'tax_region[line1]=LINE1_EXAMPLE' \
  --data-urlencode 'tax_region[city]=CITY_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| EID_EXAMPLE | Body → eid | 第1步响应 JSON → eid；没有该字段时固定填 NA |
| COUNTRY_EXAMPLE | Body → tax_region[country] | 准备结果 JSON → billing_country，就是刚才输入的真实卡片账单国家 |
| STATE_EXAMPLE | Body → tax_region[state] | 自己填写卡片账单州/省；当地不适用时留空，美国通常填真实州代码（不在 JSON 里） |
| POSTAL_CODE_EXAMPLE | Body → tax_region[postal_code] | 自己填写卡片账单邮编（不在 JSON 里） |
| LINE1_EXAMPLE | Body → tax_region[line1] | 自己填写卡片账单街道地址（不在 JSON 里） |
| CITY_EXAMPLE | Body → tax_region[city] | 自己填写卡片账单城市（不在 JSON 里） |

**响应示例（节选）：**

```json
{
  "config_id": "config_TEAM_FINAL_DEMO",
  "currency": "usd",
  "total_summary": {
    "due": 10000
  }
}
```

**看这里：**复制最新 config_id，填第7、8步 CONFIG_ID_EXAMPLE；复制 due，填第8步 AMOUNT_MINOR_EXAMPLE。实际整数原样复制，含 0。

**成功后：**保存本步响应 JSON 最新的 config_id 和 total_summary.due，做第7步；缺少时沿用第4步，再缺少才沿用第1步。实际 0 保留，找不到金额就停。

## 第7步：提交卡片，取得 pm_【准备】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_methods' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --header 'Accept: application/json' \
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
  --data-urlencode 'payment_user_agent=stripe.js/2bae21f786; stripe-js-v3/2bae21f786; checkout' \
  --data-urlencode 'client_attribution_metadata[client_session_id]=CLIENT_SESSION_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[checkout_session_id]=cs_live_TEAMDEMO' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_source]=checkout' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_version]=hosted_checkout' \
  --data-urlencode 'client_attribution_metadata[payment_method_selection_flow]=merchant_specified' \
  --data-urlencode 'client_attribution_metadata[checkout_config_id]=CONFIG_ID_EXAMPLE' \
  --data-urlencode 'guid=GUID_EXAMPLE' \
  --data-urlencode 'muid=MUID_EXAMPLE' \
  --data-urlencode 'sid=SID_EXAMPLE' \
  --data-urlencode '_stripe_version=2020-08-27;custom_checkout_beta=v1'
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
| COUNTRY_EXAMPLE | Body → billing_details[address][country] | 准备结果 JSON → billing_country，填真实卡片账单国家 |
| LINE1_EXAMPLE | Body → billing_details[address][line1] | 自己填写卡片账单街道地址（不在 JSON 里） |
| CITY_EXAMPLE | Body → billing_details[address][city] | 自己填写卡片账单城市（不在 JSON 里） |
| STATE_EXAMPLE | Body → billing_details[address][state] | 自己填写卡片账单州/省；当地不适用时留空，美国通常填真实州代码（不在 JSON 里） |
| POSTAL_CODE_EXAMPLE | Body → billing_details[address][postal_code] | 自己填写卡片账单邮编（不在 JSON 里） |
| CLIENT_SESSION_ID_EXAMPLE | Body → client_attribution_metadata[client_session_id] | 准备结果 JSON → device.client_session_id |
| cs_live_TEAMDEMO | Body → client_attribution_metadata[checkout_session_id] | 创建结果 JSON → checkout_session_id，复制完整值 |
| CONFIG_ID_EXAMPLE | Body → client_attribution_metadata[checkout_config_id] | 优先第6步响应 JSON → config_id；缺失才用 第4步，再缺失才用 第1步；必须是本次最新值 |
| GUID_EXAMPLE | Body → guid | 准备结果 JSON → device.guid |
| MUID_EXAMPLE | Body → muid | 准备结果 JSON → device.muid |
| SID_EXAMPLE | Body → sid | 准备结果 JSON → device.sid；不是代理供应商账号的 SID |

**响应示例（节选）：**

```json
{
  "id": "pm_TEAMDEMO",
  "type": "card"
}
```

**看这里：**复制最外层 id 的完整 pm_ 值，填到第8步 PAYMENT_METHOD_EXAMPLE。

**成功后：**保存响应 JSON 最外层 id（完整 pm_），做第8步。

## 第8步：确认 Team 支付【可能扣款】

```bash
curl --request POST 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO/confirm' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'eid=EID_EXAMPLE' \
  --data-urlencode 'payment_method=PAYMENT_METHOD_EXAMPLE' \
  --data-urlencode 'expected_amount=AMOUNT_MINOR_EXAMPLE' \
  --data-urlencode 'consent[terms_of_service]=accepted' \
  --data-urlencode 'expected_payment_method_type=card' \
  --data-urlencode '_stripe_version=2020-08-27;custom_checkout_beta=v1' \
  --data-urlencode 'guid=GUID_EXAMPLE' \
  --data-urlencode 'muid=MUID_EXAMPLE' \
  --data-urlencode 'sid=SID_EXAMPLE' \
  --data-urlencode 'key=pk_live_DEMO' \
  --data-urlencode 'link_brand=link' \
  --data-urlencode 'client_attribution_metadata[client_session_id]=CLIENT_SESSION_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[checkout_session_id]=cs_live_TEAMDEMO' \
  --data-urlencode 'client_attribution_metadata[checkout_config_id]=CONFIG_ID_EXAMPLE' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_source]=checkout' \
  --data-urlencode 'client_attribution_metadata[merchant_integration_version]=hosted_checkout' \
  --data-urlencode 'client_attribution_metadata[payment_method_selection_flow]=merchant_specified' \
  --data-urlencode 'passive_captcha_ekey=' \
  --data-urlencode 'rv_timestamp=RV_TIMESTAMP_EXAMPLE'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL；Body → client_attribution_metadata[checkout_session_id] | 创建结果 JSON → checkout_session_id，复制完整值 |
| EID_EXAMPLE | Body → eid | 第1步响应 JSON → eid；没有该字段时固定填 NA |
| PAYMENT_METHOD_EXAMPLE | Body → payment_method | 第7步响应 JSON → id，完整 pm_ |
| AMOUNT_MINOR_EXAMPLE | Body → expected_amount | 优先第6步响应 JSON → total_summary.due；缺失才用 第4步，再缺失才用 第1步；整数原样复制，0 保留 |
| GUID_EXAMPLE | Body → guid | 准备结果 JSON → device.guid |
| MUID_EXAMPLE | Body → muid | 准备结果 JSON → device.muid |
| SID_EXAMPLE | Body → sid | 准备结果 JSON → device.sid；不是代理供应商账号的 SID |
| pk_live_DEMO | Body → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |
| CLIENT_SESSION_ID_EXAMPLE | Body → client_attribution_metadata[client_session_id] | 准备结果 JSON → device.client_session_id |
| CONFIG_ID_EXAMPLE | Body → client_attribution_metadata[checkout_config_id] | 优先第6步响应 JSON → config_id；缺失才用 第4步，再缺失才用 第1步；必须是本次最新值 |
| RV_TIMESTAMP_EXAMPLE | Body → rv_timestamp | 准备结果 JSON → rv_timestamp；空字符串时删除整条 rv_timestamp 表单行 |

**响应示例（节选）：**

```json
{
  "payment_intent": {
    "id": "pi_TEAMDEMO",
    "status": "processing"
  }
}
```

**看这里：**processing 只是处理中，还不能说支付成功。接着第9步查，不重新确认。

**成功后：**只发送一次，然后做第9步查询。超时也先查询，不重复本步。

## 第9步：查询 Team 结果【只读】

```bash
curl --request GET 'https://api.stripe.com/v1/payment_pages/cs_live_TEAMDEMO/poll' --get \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://pay.openai.com' \
  --header 'Referer: https://pay.openai.com/' \
  --data-urlencode 'key=pk_live_DEMO'
```

| 标记 | 填到哪里 | 从哪个 JSON、哪个字段复制 |
| --- | --- | --- |
| cs_live_TEAMDEMO | URL | 创建结果 JSON → checkout_session_id，复制完整值 |
| pk_live_DEMO | Params → key | 创建结果 JSON → publishable_key / publishableKey；缺少时先停止 |

**响应示例（节选）：**

```json
{
  "state": "succeeded",
  "payment_object_status": "succeeded"
}
```

**看这里：**示例显示这张支付页付款成功；最后到自己的 ChatGPT 账号核对 Team 订阅。

**成功后：**本次 payment_intent.status 或 payment_object_status/state 明确 succeeded：结束，到 ChatGPT 核对 Team 订阅。处理中只重复本步查询；requires_action、requires_capture 或错误先停，不重新确认付款。

源码：[hosted.py](../packages/core/src/gss_core/hosted.py)。仅离线核对文档，未执行真实支付。
