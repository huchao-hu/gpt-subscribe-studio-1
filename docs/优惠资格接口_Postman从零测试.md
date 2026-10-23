# 用你给的 JSON，在 Postman 查询优惠资格

只做一件事：**从你给的 JSON 取值，填进 Postman，请求 ChatGPT 的优惠资格接口。** 不讲付款、不讲其他接口。

## 先回答：项目里的这个接口走哪条网络？

**真实查询模式下，项目的优惠资格查询会使用你配置并启用的 checkout 代理。** 不是固定直连，也不是固定美国出口。

源码位于 [account/adapter.py 第98行](../services/account/src/gss_account/adapter.py#L98)：

```python
client = ChatGPTClient.from_raw_session(
    session,
    proxy=configured_proxy("checkout")
)
```

你当前默认启动路径对应的 `runtime/proxy-gateways.json` 中，checkout 保存的是 `enabled=true`、`use_clash=true`，Clash 入口为 `http://127.0.0.1:7897`。因此用这份配置启动后，真实查询走：

```text
调用项目本地优惠接口
    → 项目后端
    → 本机Clash（127.0.0.1:7897）
    → 你配置的供应商代理
    → ChatGPT优惠查询接口
```

| 保存的设置 | 项目后端对外出口 |
| --- | --- |
| 启用代理、开启Clash开关 | 后端 → Clash → 供应商代理 → ChatGPT |
| 启用代理、关闭Clash开关 | 后端 → 供应商代理 → ChatGPT |
| 未配置或停用代理 | 使用后端电脑网络路由；系统VPN/TUN仍可能影响出口 |

这次资格查询直接读取保存的代理，不按页面所选国家改region或生成新SID。若后端开启Fake模式，返回模拟资格，本条查询不会访问第三方。

**下面文档演示的“Postman直接请求第三方”不经过项目后端。它走Postman自己的网络设置，不能继承项目里配好的代理。** 如果你希望使用项目已保存的这条串联代理，直接看文末的“调用项目本地接口”示例。

## 第一步：在你的 JSON 中找到这四个字段

你的文件内容很多，本次只需要看下面这部分。为了方便说明，我把真实值替换成了短的示意值：

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

**这是示意数据，不能用它查询真实账号。操作时替换成你文件中的完整值。**

按这个表复制即可：

| 在你的 JSON 中找哪里 | 复制什么 | 等一下填到哪里 |
| --- | --- | --- |
| 最外层的 `accessToken` | 这个字段右边的完整值 | Authorization 请求头 |
| `account` 里面的 `id` | account.id 的完整值 | chatgpt-account-id 请求头 |
| 最外层的 `sessionToken` | 这个字段右边的完整值 | 用来拼 Cookie |
| `statsigContext` 里面的 `deviceId` | statsigContext.deviceId 的完整值 | oai-did、oai-device-id 请求头，也用来拼 Cookie |

不要取 `user.id`。这里需要的是 **account.id**。

## 第二步：把取出的值拼成请求头

### 1. Authorization：前面加 Bearer 和一个空格

拼接规则：

```text
Bearer + 一个空格 + JSON最外层accessToken的值
```

根据上面的示意 JSON，拼接结果是：

```text
Bearer ACCESS_TOKEN_EXAMPLE
```

实际填写时，将 ACCESS_TOKEN_EXAMPLE 替换成你自己的完整 accessToken。

### 2. Cookie：把两个值拼成一行

拼接规则：

```text
__Secure-next-auth.session-token=JSON里的sessionToken; oai-did=JSON里的statsigContext.deviceId
```

根据上面的示意 JSON，拼接结果是：

```text
__Secure-next-auth.session-token=SESSION_TOKEN_EXAMPLE; oai-did=DEVICE_ID_EXAMPLE
```

照着替换这两处值，**保留 Cookie 名称、等号，以及中间的分号和空格**。不要把 JSON 本身粘贴到 Cookie 里。

### 3. 另外三个头：直接复制，不用拼接

根据同一个示意 JSON：

```text
oai-did: DEVICE_ID_EXAMPLE
oai-device-id: DEVICE_ID_EXAMPLE
chatgpt-account-id: ACCOUNT_ID_EXAMPLE
```

两个设备头用同一个 deviceId。这里的 Cookie 是根据你文件中已有的两项数据拼出来的，不表示浏览器其他 Cookie 也被导出了。

## 第三步：准备 JSON 中没有的会话标识

你的文件里**没有** `oai_session_id`。项目会用 accessToken 在本地生成它，不是从 account.id、sessionToken 或 deviceId 复制。

为了与项目的生成方法一致：

1. 打开 PowerShell。
2. 执行下面这一条命令：

```powershell
python -c "import getpass,uuid; print(uuid.uuid5(uuid.NAMESPACE_URL, 'dcp-sid:' + getpass.getpass('accessToken: ')))"
```

3. 提示 `accessToken:` 时，粘贴你 JSON 最外层的 accessToken，然后按回车。输入不会显示在屏幕上。
4. 命令会输出一串 UUID，将它复制到 `oai-session-id` 请求头。

这条命令只在本机生成标识，不访问网络。它不会替你刷新 token。若电脑没有 Python，先使用项目文档中的 Python 环境。

对上面假的 `ACCESS_TOKEN_EXAMPLE`，生成结果是：

```text
d3c395cc-4f86-5996-8940-06aef90ab499
```

这是示意值对应的结果，你自己的 token 会生成你自己的结果。

## 第四步：在 Postman 填写请求

### 1. 请求方法和 URL

方法选 **GET**，URL 填：

```text
https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27?timezone_offset_min=0
```

`timezone_offset_min=0` 是本次请求的固定参数，不用从 JSON 找，也不是国家参数。

### 2. Authorization 页面

选择 **No Auth**。我们已经在下面的 Headers 里手动填写 Authorization，避免重复生成两行。

### 3. Headers 页面

先填这六行。右列是根据示意 JSON 填好后的样子：

| Key | 示意 Value：你要换成自己的值 |
| --- | --- |
| Authorization | `Bearer ACCESS_TOKEN_EXAMPLE` |
| Cookie | `__Secure-next-auth.session-token=SESSION_TOKEN_EXAMPLE; oai-did=DEVICE_ID_EXAMPLE` |
| oai-did | `DEVICE_ID_EXAMPLE` |
| oai-device-id | `DEVICE_ID_EXAMPLE` |
| chatgpt-account-id | `ACCOUNT_ID_EXAMPLE` |
| oai-session-id | `d3c395cc-4f86-5996-8940-06aef90ab499` |

再填下面这些固定头。**这部分不需要从你的 JSON 找，直接照填即可**，它们来自当前项目源码：

| Key | Value |
| --- | --- |
| User-Agent | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36` |
| Accept | `*/*` |
| Accept-Language | `en-US,en;q=0.9,en;q=0.8` |
| Origin | `https://chatgpt.com` |
| Referer | `https://chatgpt.com/` |
| Content-Type | `application/json` |
| oai-language | `en-US` |
| oai-telemetry | `production` |
| oai-client-version | `prod-db390ebea64862bf1899c420a4c736e0cf639747` |
| oai-client-build-number | `7904904` |
| sec-fetch-dest | `empty` |
| sec-fetch-mode | `cors` |
| sec-fetch-site | `same-origin` |
| sec-ch-ua | `"Google Chrome";v="136", "Not.A/Brand";v="8", "Chromium";v="136"` |
| sec-ch-ua-mobile | `?0` |
| sec-ch-ua-platform | `"Windows"` |
| x-openai-target-path | `/backend-api/accounts/check/v4-2023-04-27` |
| x-openai-target-route | `/backend-api/accounts/check/v4-2023-04-27` |

说明：你的 JSON 虽然有 `statsigContext.userAgent`，但项目当前资格查询使用的是源码固定 UA；为了按项目的方式测试，这里直接照上表填写。

### 4. Body 页面

选择 **none**，不填写任何内容。

**这次是 GET 请求，不要把完整 session JSON 放到 Body。**

### 5. 完整请求代码：直接导入 Postman

下面把前面的URL、Query和所有请求头放到了一起。**这是用第一步示意JSON拼好的完整请求**，不是可用账号凭证，也没有双大括号变量需要再配置。

1. 复制整个cURL代码块。
2. 在Postman点击 **Import / 导入**，粘贴这段请求文本并导入。
3. 在导入后的Headers中，按下面替换表换成你自己的值。
4. Authorization选择No Auth，Body选择none，不再重复添加Authorization头。
5. 确认Postman代理链路准备好，再点击Send。

```bash
curl --request GET 'https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27?timezone_offset_min=0' \
  --header 'Authorization: Bearer ACCESS_TOKEN_EXAMPLE' \
  --header 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36' \
  --header 'Accept: */*' \
  --header 'Accept-Language: en-US,en;q=0.9,en;q=0.8' \
  --header 'Origin: https://chatgpt.com' \
  --header 'Referer: https://chatgpt.com/' \
  --header 'Content-Type: application/json' \
  --header 'oai-did: DEVICE_ID_EXAMPLE' \
  --header 'oai-device-id: DEVICE_ID_EXAMPLE' \
  --header 'oai-language: en-US' \
  --header 'oai-telemetry: production' \
  --header 'oai-session-id: d3c395cc-4f86-5996-8940-06aef90ab499' \
  --header 'oai-client-version: prod-db390ebea64862bf1899c420a4c736e0cf639747' \
  --header 'oai-client-build-number: 7904904' \
  --header 'sec-fetch-dest: empty' \
  --header 'sec-fetch-mode: cors' \
  --header 'sec-fetch-site: same-origin' \
  --header 'sec-ch-ua: "Google Chrome";v="136", "Not.A/Brand";v="8", "Chromium";v="136"' \
  --header 'sec-ch-ua-mobile: ?0' \
  --header 'sec-ch-ua-platform: "Windows"' \
  --header 'Cookie: __Secure-next-auth.session-token=SESSION_TOKEN_EXAMPLE; oai-did=DEVICE_ID_EXAMPLE' \
  --header 'chatgpt-account-id: ACCOUNT_ID_EXAMPLE' \
  --header 'x-openai-target-path: /backend-api/accounts/check/v4-2023-04-27' \
  --header 'x-openai-target-route: /backend-api/accounts/check/v4-2023-04-27'
```

**导入后，只替换这些地方：**

| 示例中的内容 | 换成什么 | 出现位置 |
| --- | --- | --- |
| ACCESS_TOKEN_EXAMPLE | JSON根字段accessToken的完整值 | Authorization的Bearer后面 |
| ACCOUNT_ID_EXAMPLE | JSON的account.id | chatgpt-account-id |
| DEVICE_ID_EXAMPLE | JSON的statsigContext.deviceId | oai-did、oai-device-id，以及Cookie里的oai-did，共三处 |
| SESSION_TOKEN_EXAMPLE | JSON根字段sessionToken | Cookie里的__Secure-next-auth.session-token后面 |
| d3c395cc-4f86-5996-8940-06aef90ab499 | 用第三步命令、输入你自己accessToken后得到的UUID | oai-session-id |

其余固定头可按当前源码原样保留。cURL只是Postman导入格式，这里不要求你在PowerShell运行它。

本请求参数汇总：

```text
Method: GET
URL: https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27
Query: timezone_offset_min=0
Body: 无
```

## 第五步：检查代理，然后点击 Send

Postman 直接请求第三方时，**不会自动使用项目网页保存的代理设置**。

你这条供应商代理需要经过 Clash，所以 Postman 也要具备同样的串联链路。只让 Postman 经过 Clash，并不等于又经过了这条供应商代理。如果 Postman 的串联代理还没配置好，即使请求参数正确，也可能请求失败。

代理链路准备好后点击 **Send**。本次仅查询活动，不创建订单、不付款。

## 第六步：响应里看这几个位置

### 1. 响应头：在Postman哪里看

请求发送后，在下方响应区域切换 **Headers** 查看响应头；切换 **Body** 查看响应JSON。上面你填写的是“请求头”，下面是服务器返回的“响应头”，不需要把响应头复制回请求。

响应头格式示意如下，**不是本次真实抓包，不保证上游逐字返回**：

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

实际可能使用HTTP/2，Content-Type也可能带charset等信息，以Postman实际显示为准。

| 查看位置 | 怎么理解 |
| --- | --- |
| 响应状态码200 | 请求得到成功HTTP响应，继续看Body，不代表必然有优惠 |
| 响应状态码401 | 登录凭证无效或过期，重新取得accessToken |
| 响应状态码403 | 请求被拒绝，核对代理链路和上下文，不能只凭状态码认定具体原因 |
| Content-Type包含application/json | Body通常按JSON查看，寻找下面的accounts字段 |
| Content-Type为text/html | 可能是登录页或拦截页，先看实际HTML，不当成活动JSON |
| 响应若有Set-Cookie | 是服务器更新Cookie的指令，不是Plus优惠结果 |

### 2. 响应Body：优惠字段在哪里



结构示意：

```json
{
  "accounts": {
    "ACCOUNT_ID_EXAMPLE": {
      "account": {
        "plan_type": "free"
      },
      "eligible_promo_campaigns": {
        "plus": {
          "id": "实际活动ID",
          "metadata": {
            "discount": {"percentage": 100},
            "duration": {"num_periods": 1, "period": "month"}
          }
        }
      }
    }
  }
}
```

依次打开 `accounts` → 你的账号ID（也可能是 `default`）→ `eligible_promo_campaigns` → `plus`：

- `id`：这个 Plus 活动的ID。
- `metadata.discount.percentage`：优惠比例。
- `metadata.duration.num_periods` 和 `period`：活动周期。

示例不代表你的账号一定有免费活动。没有 plus 活动，不能强行认为有免费月。第三方原始响应也不会直接返回项目整理后的 plus_eligible。

请求失败时：

- **401**：先重新获取自己的有效 accessToken。
- **403**：检查 Postman 实际代理链路和登录上下文；它不自动继承项目代理，参数正确也不能保证第三方放行。
- **返回HTML**：先看是不是登录页或拦截页，不把它当活动JSON解析。

`marketingEligibility`、`user.name`、`statsigContext.country` 等字段不需要放到这次请求里。页面选择的国家也不参与这个优惠查询。

## 可选：想直接使用项目配好的代理，就调用本地接口

这是另一种调用方式，与上面的“Postman直接请求ChatGPT”二选一即可。需要你自己已经启动后端，并设置真实模式 `GSS_USE_FAKE=0`。

这次请求发到本机8080，由项目后端使用保存的checkout代理再请求ChatGPT。按你当前配置，就是经过Clash和供应商代理；Postman不需要自己复制供应商代理凭证。

直接导入：

```bash
curl --request POST 'http://127.0.0.1:8080/api/promo/eligibility' \
  --header 'Content-Type: application/json' \
  --data-raw '{"session":"ACCESS_TOKEN_EXAMPLE"}'
```

只需把ACCESS_TOKEN_EXAMPLE换成JSON根字段accessToken的完整值。这里是最少输入示例；若需要原始设备/Cookie上下文，可将完整session JSON先转义成字符串再填到session字段，不直接传对象。

本地请求不要套到外部代理；Postman应直接访问127.0.0.1，外部出口由后端处理。请求参数为：

```text
Method: POST
URL: http://127.0.0.1:8080/api/promo/eligibility
Header: Content-Type: application/json
Body: {"session":"自己的accessToken完整值"}
```

本地返回的是整理后的摘要，例如：

```json
{
  "account_id": "实际账号ID",
  "current_plan_type": "free",
  "subscription_plan": "chatgptfreeplan",
  "is_free": true,
  "plus_eligible": true,
  "campaigns": [
    {
      "key": "plus",
      "campaign_id": "实际活动ID"
    }
  ]
}
```

这仅展示部分字段位置，不是账号实际结果。与第三方原始accounts响应不同：本地campaigns[].campaign_id对应上游活动对象的id；plus_eligible是项目计算的摘要。如果返回fake-account，说明还在模拟模式；仅修改Postman不能切换后端运行模式。

## 对照源码的位置

- [session字段解析](../packages/core/src/gss_core/session_token.py)：`_from_mapping`。
- [请求头与会话ID生成](../packages/core/src/gss_core/chatgpt.py)：`from_raw_session`、`_identity_headers`。
- [优惠资格查询](../packages/core/src/gss_core/chatgpt.py)：`promo_eligibility`。

本文使用示意值，没有写入你提供的真实 token、Cookie 或账号ID。其他接口的资料见[第三方接口调用文档](第三方接口调用文档.md)。
