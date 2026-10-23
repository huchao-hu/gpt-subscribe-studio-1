# /pay-protocol：让项目代你支付

已按更新后的本地 `6b64475` 核对：当前入口会自动区分个人与 Team，个人支持 oaics_ 和 cs_。页面点击付款时的接口顺序见[页面点击支付流程图](页面点击支付流程图.md)。

本文从**项目 POST /api/orders 创建订单**返回的三个字段开始：

```json
{
  "id": "11111111-2222-4333-8444-555555555555",
  "checkout_url": "https://chatgpt.com/checkout/openai_llc/cs_live_DEMO",
  "publishable_key": "pk_live_DEMO"
}
```

| 这三个字段 | 从哪里复制，后面怎么用 |
| --- | --- |
| id | 本地创建订单响应最外层 id；复制完整值，替换第1步 URL 的 LOCAL_ORDER_ID_EXAMPLE |
| checkout_url | 同一次响应最外层 checkout_url；项目已保存，不用在第1步 Body 再传；个人可含 oaics_ 或 cs_，Team 通常含 cs_ |
| publishable_key | 同一次响应最外层 publishable_key；个人分支会读取它，也可在请求顶层 publishable_key 显式覆盖 |

**如果你拿到的是第三方的 checkout_session_id、url、publishable_key，这三个值不能直接调用本接口。** 第三方创建不会产生项目本地订单；cs_ 不是本地 id。当前没有导入已有会话的接口，这种情况先停，继续使用对应的第三方支付文档。

本文只演示个人 Plus 的本地订单和卡片付款。后端须已按[启动文档](启动命令文档.md)以 GSS_USE_FAKE=0 启动，且创建后没有重启；个人 checkout_url 可含真实 oaics_ 或 cs_live_ / cs_test_；后端按 checkout_kind 自动分流。本地请求绕过 Postman 的远程代理；后端请求 Stripe 使用项目启用的 checkout 代理，按账单国家调整支持的地区参数，开启中转时需要 Clash 运行。

项目不要求你手填 Sentinel、pm_、ctoken_、金额或配置 ID。它会自动执行支持的 Stripe 步骤；/pay-protocol 不受 Fake 保护，可能真实扣款。个人分支按本次请求 publishable_key → 订单保存的公钥 → Vault 保存的公钥依次取值；Team 分支仍使用 STRIPE_PUBLISHABLE_KEY 或源码默认商户公钥。公钥不匹配时停止，不把 accessToken 当公钥。

每一步：Postman Import 整条 cURL → 按表替换 → Send。第1步 Body 使用 raw JSON，Authorization 选 No Auth。DEMO 和 EXAMPLE 都是待替换标记。

下面响应是字段结构示例，不是真实测试结果；只保留本流程用到的字段。DEMO、金额、币种都要以你自己的实际响应为准。

## 第1步：提交给项目确认支付【可能扣款，只发一次】

```bash
curl --request POST 'http://127.0.0.1:8080/api/orders/LOCAL_ORDER_ID_EXAMPLE/pay-protocol' \
  --header 'Content-Type: application/json' \
  --data-raw '{
  "card": {
    "number": "CARD_NUMBER_EXAMPLE",
    "exp_month": "EXP_MONTH_EXAMPLE",
    "exp_year": "EXP_YEAR_EXAMPLE",
    "cvc": "CVC_EXAMPLE"
  },
  "billing": {
    "name": "NAME_EXAMPLE",
    "email": "EMAIL_EXAMPLE",
    "line1": "LINE1_EXAMPLE",
    "city": "CITY_EXAMPLE",
    "state": "STATE_EXAMPLE",
    "postal_code": "POSTAL_CODE_EXAMPLE",
    "country": "COUNTRY_EXAMPLE"
  },
  "steps": {
    "fingerprint": false,
    "dwell": false,
    "elements": false,
    "tax_region": false
  }
}'
```

| 标记 / 位置 | 从哪里复制 |
| --- | --- |
| LOCAL_ORDER_ID_EXAMPLE（URL） | 创建结果 JSON 最外层 id，复制完整本地订单 ID，不是 checkout_url 中的 cs_ |
| CARD_NUMBER_EXAMPLE（card.number） | 自己填写实际卡号，只填数字；不是 session JSON 字段 |
| EXP_MONTH_EXAMPLE（card.exp_month） | 卡片到期月份，例如 09 |
| EXP_YEAR_EXAMPLE（card.exp_year） | 卡片到期四位年份 |
| CVC_EXAMPLE（card.cvc） | 卡片安全码 |
| NAME_EXAMPLE（billing.name） | 自己填写真实账单姓名，不在创建结果里 |
| EMAIL_EXAMPLE（billing.email） | 自己填写真实账单邮箱，不在创建结果里 |
| LINE1_EXAMPLE（billing.line1） | 自己填写卡片账单街道 |
| CITY_EXAMPLE（billing.city） | 自己填写卡片账单城市 |
| STATE_EXAMPLE（billing.state） | 自己填写州/省，当地不适用时填空字符串 |
| POSTAL_CODE_EXAMPLE（billing.postal_code） | 自己填写卡片账单邮编 |
| COUNTRY_EXAMPLE（billing.country） | 本地创建请求 JSON → billing_country；创建完整响应也有同名字段，示例 PH。与个人创建国家保持一致 |
| steps 四个 false | 固定按示例保留，不从 JSON 复制 |

**响应示例（节选）：**

```json
{
  "state": "paid",
  "code": null,
  "decline_code": null,
  "message": null,
  "intent_status": "succeeded",
  "charge_id": null,
  "payment_method_id": null
}
```

**看这里：**这是本地后端整理后的响应。看 state 和 intent_status；示例组合表示成功。charge_id、payment_method_id 可能为空，不需要拿它们继续填请求。

**成功后：**看本步响应 JSON 的 state 和 intent_status。state=paid 且 intent_status=succeeded 时，到 ChatGPT 核对订阅；requires_capture 只是待扣款授权，不能算扣款完成。处理中或超时先核对结果：Team 可用第2步查询；个人需要核对本次 Intent 或官方结账页面，不能把 oaics_ 填入第2步；confirm_error、card_declined、challenge_required、captcha_rejected 先停，不重发本步。HTTP 200 不等于支付成功。

## 第2步：仅 Team cs_ 查询，不再提交付款

本步骤只用于 Team 的 Stripe Hosted 结账。个人 oaics_ 不发送这条请求；个人 cs_ 的查询还需本次 Custom 上下文，见[新流程图的个人分支](页面点击支付流程图.md)。

```bash
curl --request GET 'https://api.stripe.com/v1/payment_pages/CS_ID_EXAMPLE/poll' --get \
  --header 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'Origin: https://js.stripe.com' \
  --header 'Referer: https://js.stripe.com/' \
  --data-urlencode 'key=PUBLISHABLE_KEY_EXAMPLE' \
  --data-urlencode '_stripe_version=2025-03-31.basil'
```

| 标记 / 位置 | 从哪里复制 |
| --- | --- |
| CS_ID_EXAMPLE（URL） | 创建结果 JSON → checkout_url。比如 https://chatgpt.com/checkout/openai_llc/cs_live_DEMO，只复制最后的 cs_live_DEMO；实际必须使用完整真实 cs_ 值，不带 URL 和 # 后面的片段 |
| PUBLISHABLE_KEY_EXAMPLE（Params → key） | 同一次创建结果 JSON 最外层 → publishable_key，完整 pk_ 值；必须属于这次结账的商户 |
| _stripe_version | 固定按 cURL 保留 |
| Postman 代理 | 本步请求第三方，按项目支付所使用的 checkout 出口配置 Postman；访问本地后端的设置不会自动用于这个第三方请求 |

**响应示例（节选）：**

```json
{
  "state": "succeeded",
  "payment_object_status": "succeeded"
}
```

**看这里：**这是 Stripe 直接返回的响应，不是本地后端结果。示例显示支付页成功，再核对账号订阅。

**成功后：**本步响应 JSON 的 state / payment_object_status 明确 succeeded 时，到 ChatGPT 核对订阅。processing / pending 只继续本步查询；failed / expired / canceled 或需要验证时停止。结果不明确不要重新发送第1步。

当前入口不会回写本地订单支付状态，所以项目页面“待支付”不能作为再次付款的理由。个人 cs_ 分支现在会按返回状态自动请求 ChatGPT 审批；验证码和 3DS 仍不能自动完成全部验证。需要验证或状态不明时先停止核对，不重复付款。

源码：[本地支付路由](../services/api/src/gss_api/routers/orders.py)、[实际 Stripe 请求](../packages/core/src/gss_core/stripe_protocol.py)。仅离线核对文档，未执行真实支付。
