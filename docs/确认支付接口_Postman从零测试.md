# 确认支付：先选一份文档

先看创建结账时发送的套餐，再看创建响应里的会话编号。**下面只选一份，不要四份都执行。**

| 你已经创建的结账 | 接下来读哪份 |
| --- | --- |
| 个人 Plus，checkout_session_id 是 oaics_ 开头 | [个人 oaics_ 确认支付](个人oaics_确认支付_Postman.md) |
| 个人 Plus，checkout_session_id 是 cs_ 开头 | [个人 cs_ 确认支付](个人cs_Custom确认支付_Postman.md) |
| Team，返回 cs_ 和托管结账地址 | [Team 确认支付](Team托管结账确认支付_Postman.md) |
| 通过项目 /api/orders 创建，有本地订单 id，想让项目代你付款 | [/pay-protocol](pay-protocol纯协议支付_Postman.md) |

[创建结账文档](创建结账接口_Postman从零测试.md)最后的个人 cs_live_DEMO 例子，接着读上面第二份。

前三份从第三方创建响应的 **checkout_session_id、url、publishable_key** 开始，每步都有完整 cURL、参数来源表、响应 JSON 示例和成功后的下一步。

/pay-protocol 是本项目的接口，需要本地订单 id。第三方返回的 cs_ 不能直接当本地 id；区别只在该文档内说明。

更新后页面会自动区分个人与 Team，个人 oaics_ 也支持自动支付。页面按钮的实际接口顺序请看[页面点击支付流程图](页面点击支付流程图.md)。
