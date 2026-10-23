# 用你的 JSON，在 Postman 创建结账

和[优惠资格测试文档](优惠资格接口_Postman从零测试.md)一样：**复制本文完整 cURL → 导入 Postman → 按表替换参数 → Send**。直接请求第三方，不调用本地 /api/orders。

本文测试 **Plus**，账单国家由你在脚本里选择；脚本按项目的国家配置自动选币种、语言和时区。只创建结账，不填卡、不付款。

## 先说清楚：创建结账到底走哪条网络？

**通过项目网页创建真实结账时，后端使用你配置并启用的 checkout 代理；停用代理时，才使用后端电脑自身的网络路由。本文的 Postman 直调则使用 Postman 自己的代理设置，不会自动继承项目配置。**

| 你在做什么 | 谁发请求 | 使用哪条网络 |
| --- | --- | --- |
| 在项目网页创建真实结账，或调用本地 /api/orders | 项目后端 | 使用已启用的 checkout 代理；停用代理则使用后端电脑网络路由 |
| 运行本文脚本生成 Sentinel | 本机 Python / Node 脚本，不需要后端运行 | 自动读取保存的 checkout 代理；停用代理则使用运行脚本的电脑网络路由 |
| 导入本文 cURL，在 Postman 点击 Send 创建结账 | Postman，不经过项目建单接口 | 使用 Postman 自己的网络设置；需要你按脚本显示的代理信息手动配置 |

**本文两份 cURL 都没有 --proxy 参数，也没有把代理写进请求头或 Body。复制 cURL 不等于配置好了代理。** Postman 未配置代理时通常使用本机网络，但它启用的系统代理、代理环境变量或系统 VPN / TUN 也可能影响实际出口；不能仅凭请求 URL 判断是不是直连。

项目后端和生成脚本读取 checkout 代理后的连接方式：

| 保存的 checkout 设置 | 连接方式 |
| --- | --- |
| 启用代理，关闭 Clash 中转 | 后端或脚本 → 供应商代理 → ChatGPT |
| 启用代理，开启 Clash 中转 | 后端或脚本 → 本机 Clash → 供应商代理 → ChatGPT |
| 停用代理 | 后端或脚本 → 所在电脑的网络出口；系统 VPN / TUN 仍可能影响路由 |

脚本默认读取 runtime/proxy-gateways.json；设置过 GSS_PROXY_CONFIG 时读取该环境变量指定的文件。**生成脚本不会替 Postman 设置代理**，第五步会告诉你怎么填写。开启 Clash 中转时，脚本会保留一个本机转发端口供 Postman 使用，这只是代理转发，不是调用本地 /api/orders。

另外，项目真实建单会按所选账单国家改写代理账号的地区参数，并为订单生成 SID；本文脚本为便于 Postman 复用，保留保存的地区和 SID。改写代理账号参数不等于已经验证实际出口国家。项目处于 Fake 模式时返回模拟结账，不访问第三方；独立脚本和 Postman 直调不受该 Fake 开关控制。

## 第一步：从你的 session JSON 找到这些值

你的 JSON 很长，本次主要看这些字段：

```json
{
  "accessToken": "ACCESS_TOKEN_EXAMPLE",
  "account": {
    "id": "ACCOUNT_ID_EXAMPLE"
  },
  "sessionToken": "SESSION_TOKEN_EXAMPLE",
  "statsigContext": {
    "deviceId": "DEVICE_ID_EXAMPLE"
  }
}
```

| 在 JSON 中找哪里 | 等一下填在哪里 |
| --- | --- |
| 最外层 accessToken | cURL 的 Authorization：保留 Bearer 和一个空格，只替换后面的 ACCESS_TOKEN_EXAMPLE |
| account.id | cURL 的 ACCOUNT_ID_EXAMPLE；不要取 user.id |
| 最外层 sessionToken | 下一步脚本的第 2 项；用于生成 Cookie |
| statsigContext.deviceId | 脚本的第 3 项，以及 cURL 中两处 DEVICE_ID_EXAMPLE |

上面都是示意文字，必须换成你自己 JSON 里的完整值，复制值时不带 JSON 外面的双引号。

## 第二步：单独生成 openai-sentinel-token

**它不是 JSON 的字段。项目用本地 Node.js 运行仓库里的 Sentinel SDK，联网生成。** 不需要浏览器抓包，但需要有效 session、已安装的项目依赖和可用代理；不是离线算出来的。

已提供脚本：[scripts/generate_checkout_sentinel.py](../scripts/generate_checkout_sentinel.py)。不需要修改脚本源码，也不需要启动前后端。

打开 PowerShell，复制运行：

```powershell
Set-Location 'G:\aa\kaiyuanxinagmu\gpt-subscribe-studio-1'
.\.venv\Scripts\python.exe .\scripts\generate_checkout_sentinel.py
```

按提示填写：

| 脚本问什么 | 你填什么 |
| --- | --- |
| 1. accessToken | JSON 最外层 accessToken 的完整值 |
| 2. sessionToken | JSON 最外层 sessionToken 的完整值 |
| 3. deviceId | JSON 的 statsigContext.deviceId |
| 4. 优惠活动 ID | 普通结账直接回车；优惠结账填写上一接口查出的真实活动 ID |
| 5. 账单国家代码 | 按脚本列出的选项填写，例如 US、PH、JP；与本次准备创建的结账国家一致 |

前两个值输入时不显示字符，粘贴后直接回车即可。**项目和脚本都不是固定 PH。** 项目网页让你选账单国家，这个独立脚本让你输入国家代码，二者使用同一份国家配置。

例如：PH → PHP、en-PH、Asia/Manila；US → USD、en-US、America/New_York；JP → JPY、ja-JP、Asia/Tokyo。你不需要自己计算，按脚本输出替换 cURL 即可。时区用于生成 Sentinel，不是要新增一个时区请求头。

脚本沿用保存的 checkout 代理地区与 SID，不改写代理配置、不刷新你的 accessToken。**选择账单国家不会自动把代理 IP 切到那个国家**，也不是从 session JSON 的 statsigContext.country 自动取值。若需更换代理出口，请先配置好，再生成 Sentinel。

成功后，终端会显示下面这些名称。**复制等号后面的完整值，不要把名称和等号也复制进去。**

| 终端输出名称 | 替换 cURL 中哪个标记 | 这个值从哪来 |
| --- | --- | --- |
| BILLING_COUNTRY_EXAMPLE | BILLING_COUNTRY_EXAMPLE | 你在脚本第 5 项选择的国家代码 |
| CURRENCY_EXAMPLE | CURRENCY_EXAMPLE | 项目按所选国家匹配的币种 |
| LANGUAGE_EXAMPLE | LANGUAGE_EXAMPLE | 项目按所选国家匹配的语言 |
| ACCEPT_LANGUAGE_EXAMPLE | ACCEPT_LANGUAGE_EXAMPLE | 项目按所选语言拼接的完整 Accept-Language 请求头值 |
| SENTINEL_TOKEN_EXAMPLE | SENTINEL_TOKEN_EXAMPLE | 项目调用 Node SDK 联网生成，完整复制，包括 JSON 花括号 |
| SESSION_ID_EXAMPLE | SESSION_ID_EXAMPLE | 项目按 accessToken 派生会话 ID；读页面成功时也可能用页面中的会话 ID |
| CLIENT_VERSION_EXAMPLE | CLIENT_VERSION_EXAMPLE | 读取页面得到的版本；未取得时沿用源码默认值 |
| CLIENT_BUILD_EXAMPLE | CLIENT_BUILD_EXAMPLE | 读取页面得到的构建号；未取得时沿用源码默认值 |
| COOKIE_EXAMPLE | COOKIE_EXAMPLE | sessionToken、deviceId，以及读取页面后服务器补充的 Cookie |
| PURCHASE_ATTEMPT_ID_EXAMPLE | PURCHASE_ATTEMPT_ID_EXAMPLE | 脚本在本机新生成的 UUID，作为本次结账尝试 ID |

Cookie 最初是这样拼的：

```text
__Secure-next-auth.session-token=你的sessionToken; oai-did=你的deviceId
```

页面可能补充 Cookie，所以实际发送时，**直接复制脚本输出的完整 COOKIE_EXAMPLE 值**，不用自己拼。

脚本还可能输出两个附加请求头：

- openai-sentinel-so-token
- oai-web-deployment-attestation

**有值就在 Postman 的 Headers 新增对应行；显示“未生成”就不添加。** 它们不是 session JSON 中的字段，也不要拿其他值冒充。

脚本不创建结账、不付款，也不把输入的凭证保存到文件。依赖未装好时先看[首次安装说明](启动命令文档.md)。如果没有显示“生成成功”，先停在这里，不要拿旧令牌继续。

## 第三步：选一份完整 cURL 导入 Postman

下面两份是供 **Postman Import** 使用的 cURL，不要求你在 PowerShell 执行。

导入后：Authorization 选 **No Auth**，因为请求头中已经有 Authorization；Body 保持 **raw → JSON**。

### A. 没有优惠：普通 Plus 结账

第二步脚本的活动 ID 留空，然后复制这份完整请求：

```bash
curl --request POST 'https://chatgpt.com/backend-api/payments/checkout' \
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
  --header 'openai-sentinel-token: SENTINEL_TOKEN_EXAMPLE' \
  --header 'x-openai-target-path: /backend-api/payments/checkout' \
  --header 'x-openai-target-route: /backend-api/payments/checkout' \
  --header 'originator: Codex Browser' \
  --header 'x-openai-web-frontend: codex_webview' \
  --header 'x-openai-codex-window-type: browser' \
  --header 'x-oai-mcp-form-version: 2' \
  --header 'x-openai-checkout-source: chatgpt_web_merged' \
  --header 'Referer: https://chatgpt.com/' \
  --data-raw '{
  "entry_point": "all_plans_pricing_modal",
  "plan_name": "chatgptplusplan",
  "billing_details": {
    "country": "BILLING_COUNTRY_EXAMPLE",
    "currency": "CURRENCY_EXAMPLE"
  },
  "checkout_source": "chatgpt_web_merged",
  "supports_saved_payment_link": true,
  "checkout_appearance": "light",
  "cancel_url": "https://chatgpt.com/?cta_tab=personal",
  "purchase_attempt_id": "PURCHASE_ATTEMPT_ID_EXAMPLE",
  "checkout_ui_mode": "custom"
}'
```

### B. 有优惠：使用当前账号实际查到的 Plus 活动

活动 ID 从上一接口响应取：

- 直接请求第三方：accounts → 当前账号条目（也可能是 default）→ eligible_promo_campaigns → plus → id。
- 如果之前调用本地优惠接口：campaigns 中 key=plus 那一项的 campaign_id。

**不要从 session JSON 的 marketingEligibility 取，也不要自己猜。** 没有实际活动就用 A 请求。

第二步脚本填写这个活动 ID，再复制以下完整请求：

```bash
curl --request POST 'https://chatgpt.com/backend-api/payments/checkout' \
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
  --header 'openai-sentinel-token: SENTINEL_TOKEN_EXAMPLE' \
  --header 'x-openai-target-path: /backend-api/payments/checkout' \
  --header 'x-openai-target-route: /backend-api/payments/checkout' \
  --header 'originator: Codex Browser' \
  --header 'x-openai-web-frontend: codex_webview' \
  --header 'x-openai-codex-window-type: browser' \
  --header 'x-oai-mcp-form-version: 2' \
  --header 'x-openai-checkout-source: chatgpt_web_merged' \
  --header 'Referer: https://chatgpt.com/?promo_campaign=CAMPAIGN_ID_EXAMPLE' \
  --data-raw '{
  "entry_point": "all_plans_pricing_modal",
  "plan_name": "chatgptplusplan",
  "billing_details": {
    "country": "BILLING_COUNTRY_EXAMPLE",
    "currency": "CURRENCY_EXAMPLE"
  },
  "checkout_source": "chatgpt_web_merged",
  "supports_saved_payment_link": true,
  "checkout_appearance": "light",
  "cancel_url": "https://chatgpt.com/?cta_tab=personal",
  "purchase_attempt_id": "PURCHASE_ATTEMPT_ID_EXAMPLE",
  "checkout_ui_mode": "custom",
  "promo_campaign": {
    "promo_campaign_id": "CAMPAIGN_ID_EXAMPLE",
    "is_coupon_from_query_param": false
  }
}'
```

## 第四步：按这张表替换，不要遗漏

导入 Postman 后，主要在 Headers 和 Body 替换：

| 标记 | 从哪里复制 | 出现位置 |
| --- | --- | --- |
| ACCESS_TOKEN_EXAMPLE | JSON 最外层 accessToken，与脚本输入相同 | Authorization 的 Bearer 后面 |
| ACCOUNT_ID_EXAMPLE | JSON 的 account.id | chatgpt-account-id |
| DEVICE_ID_EXAMPLE | JSON 的 statsigContext.deviceId，与脚本输入相同 | oai-did、oai-device-id，共两处 |
| BILLING_COUNTRY_EXAMPLE | 脚本同名输出的等号后面 | Body 的 billing_details.country |
| CURRENCY_EXAMPLE | 脚本同名输出的等号后面 | Body 的 billing_details.currency |
| LANGUAGE_EXAMPLE | 脚本同名输出的等号后面 | oai-language |
| ACCEPT_LANGUAGE_EXAMPLE | 脚本同名输出的等号后面 | Accept-Language，整格替换 |
| SENTINEL_TOKEN_EXAMPLE | 脚本同名输出的等号后面 | openai-sentinel-token |
| SESSION_ID_EXAMPLE | 脚本同名输出的等号后面 | oai-session-id |
| CLIENT_VERSION_EXAMPLE | 脚本同名输出的等号后面 | oai-client-version |
| CLIENT_BUILD_EXAMPLE | 脚本同名输出的等号后面 | oai-client-build-number |
| COOKIE_EXAMPLE | 脚本同名输出的等号后面 | Cookie，整格替换 |
| PURCHASE_ATTEMPT_ID_EXAMPLE | 脚本同名输出的等号后面 | Body 的 purchase_attempt_id |
| CAMPAIGN_ID_EXAMPLE（仅优惠请求） | 优惠查询返回的实际活动 ID，与脚本输入相同 | Referer 和 Body 的 promo_campaign.promo_campaign_id，共两处 |

其余固定参数按示例保留。活动 ID 在 Referer 中属于 URL 参数，如含特殊字符需要 URL 编码；Body 中仍填写原始活动 ID。

**普通与优惠的区别：优惠请求的 Body 多一个 promo_campaign 对象，Referer 使用对应活动页面。** 不需要添加本地接口使用的 mode、risk_acknowledged，也不要把整个 session JSON 放进 Body。

若脚本输出附加请求头，在这里一并添加。为避免旧 Cookie 混入，清掉 Postman 为 chatgpt.com 保存的旧 Cookie，或对本次请求关闭 Cookie jar。

## 第五步：配置代理，再点击 Send

**Postman 不会自动使用项目网页里的代理。** 脚本会在终端显示本次 Postman 应填的代理协议、主机、端口、用户名、密码。

在 Postman 的 Settings → Proxy 中：

1. 关闭系统代理、读取代理环境变量的选项。
2. 有代理时开启自定义代理，按终端显示的值填写，允许 HTTPS 请求走代理。
3. 有用户名密码时开启代理认证；它与请求头里的 Bearer 是两回事。chatgpt.com 不要放进绕过列表。
4. 没有启用项目代理时，自定义代理也关闭；系统 VPN / TUN 仍可能影响网络。

HTTP 对应 HTTP，SOCKS5 对应 SOCKS5。若显示 https 且 Postman 不支持这种代理入口，不要直接改成 HTTP，先解决入口兼容问题。菜单名称可对照[Postman 官方代理说明](https://learning.postman.com/docs/getting-started/installation/proxy)。

开启项目的 Clash 中转时，终端会显示 **127.0.0.1 和本次随机端口**。这是临时转发入口，请按输出填写，保持脚本窗口和 Clash 运行：

```text
Postman → 脚本保留的本机转发 → Clash → 供应商代理 → ChatGPT
```

不是填本地 API 的 8080，也不要擅自换成 Clash 的 7897。关闭中转时直接使用终端显示的供应商代理入口。

生成后尽快 Send，不要中途换账号、账单国家、活动、代理 SID 或节点。动态代理可能自行换 IP；相同配置也不保证出口一直不变。Postman 与项目的 TLS 指纹还可能不同，生成 Sentinel 不保证第三方一定接受。

## 第六步：看响应

成功时看 Postman 下方 **Body**。为了让下一份支付文档能接着讲，**两份文档共用下面这一份假数据例子**：假设你创建的是个人结账，这次拿到的是 cs_ 会话。DEMO 不是实际可用值，也不代表所有账号都会返回这种会话：

```json
{
  "checkout_session_id": "cs_live_DEMO",
  "url": "https://chatgpt.com/checkout/openai_llc/cs_live_DEMO",
  "publishable_key": "pk_live_DEMO"
}
```

| 这三个字段 | 接下来怎么用 |
| --- | --- |
| checkout_session_id | 结账单编号；下一份文档所有 cs_live_DEMO 都换成你的完整值 |
| publishable_key | 商户公钥；下一份文档所有 key=pk_live_DEMO 都换成你的完整值 |
| url | 可在浏览器打开的结账页面；不是确认支付 API 的地址 |

**创建结账成功不等于已经付款。** 最终金额和卡片的 pm_ 还需要后续接口取得，这份个人 cs_ 示例接着按[个人 cs_ Custom 支付文档](个人cs_Custom确认支付_Postman.md)第0步往下做。实际返回 oaics_ 时，改看[个人 oaics_ 文档](个人oaics_确认支付_Postman.md)；Team 创建成功后的付款见[Team 文档](Team托管结账确认支付_Postman.md)。不要同时执行多份付款流程。

源码也兼容 session_id / id、checkout_url、publishableKey 等字段；不保证每次都同时返回。这里是第三方原始响应，没有项目本地订单 ID。响应头在下方 **Headers** 查看，不用复制回请求。

| 情况 | 先检查 |
| --- | --- |
| 代理连不上 | 协议、端口、认证；Clash 中转时脚本窗口和 Clash 都要运行 |
| 407 | Postman 的代理用户名、密码 |
| 401 | session 是否有效，替换登录信息后重新生成 Sentinel |
| 403 / unusual activity | 代理出口、Cookie 和生成上下文；参数正确也可能被第三方拒绝 |
| Sentinel 无效 | 是否完整复制，账号、活动、出口是否变化；重新生成 |
| 没有预期优惠 | 活动 ID 是否属于当前账号；创建成功不等于优惠一定生效 |

本文到创建结账为止，不确认付款。重复 Send 可能重复创建结账会话。**如果继续按支付文档测试，先保持脚本窗口和 Clash 运行，沿用本次代理端口。** 全部测试结束后再回到终端按回车退出；退出会关闭临时转发端口。

源码：[后端建单选择代理](../services/api/src/gss_api/routers/orders.py)、[真实结账适配器](../services/checkout/src/gss_checkout/adapter.py)、[代理配置及 Clash 入口解析](../packages/core/src/gss_core/proxies.py)、[国家、币种、语言和时区配置](../packages/core/src/gss_core/countries.py)、[请求头、页面准备及结账 Body](../packages/core/src/gss_core/chatgpt.py)、[Sentinel Python 入口](../packages/core/src/gss_core/sentinel.py)、[Node 桥](../packages/core/src/gss_core/sentinel_assets/sentinel_bridge.js)。

本次只核对源码、脚本和文档，未联网生成 Sentinel，未请求真实结账或付款。
