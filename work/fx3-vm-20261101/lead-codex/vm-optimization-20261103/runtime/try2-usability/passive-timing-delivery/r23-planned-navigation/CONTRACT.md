# r23 独立测试合同：预定义单步导航＋真实后置视觉确认

本合同仅用于后续另派的独立 FX3 测试；协调员已明确采用此模式。它不改变部署运行政策，不追溯改判 r21/r21c，也不是人工或流式视觉在点击瞬间持续看图。

## 输入依据和证据

- `scripted_navigation=true`、`visual_review_at_click=false`。动作来自冻结 `NAVIGATION-PLAN.json`、本次明确的单步 CLI、前一步真实后置语义审阅和原 explicit_confirm、当前原 PAGE 准入。旧工具静图的 SHA/generation **不是动作许可**，不得拿最新 generation 改写旧图或声称当前已审图。
- 第一次必须先把合格待机截图实际交给操作代理查看，再独立调用 `standby_review`。第 2–8 步必须前一步真实新截图符合计划后置条件、独立调用 `confirm`、原 explicit_confirm 成功；否则不得继续。JSON 不能证明模型实际看了图，这项行为由操作任务执行并记录，不能用脚本默认通过代替。
- 前置依据文件绑定历史截图文件/hash、验证回执/hash、已完成 step、launch、document incarnation、代理明确语义判断；后续步骤再核原确认 request/step/nonce/精确 SHA+generation。新动作记录 plan_sha/step/previous_confirm/nonce/document/launch 和点击时实际 loaded frame，保留原 PAGE attempt 身份。历史审阅与点击帧分开命名。
- 完成 PAGE 摘要 await 后，在同一个无 await 浏览器 job 内捕获当前状态和计划参数，立即决定是否调用一次原按钮。原 PAGE 自己的异步 GET/POST 与 server SHA/generation gate 全部保留；不直接 POST、不排队多键、不自动重试、不等待画面匹配后延迟发键。
- 保留原 ready/有效 loaded frame、busy/review/unknown/error/stop 门、精确单一 tab/document/launch、原 20 秒 alarm 和 nonce。同步 job 一致性不覆盖 server/guest，也不证明原生 input-context 与过去静图相同。

## 八步必须全部验收

| 步 | 固定动作 | 必须实际看见的后置条件 |
|---|---|---|
| 1 | MENU | 完整 Setup > Area/Date，橙色 Area/Date/Time Setting |
| 2 | UP | Language，English |
| 3 | C4 | 语言帮助 |
| 4 | MENU | 返回 Language |
| 5 | OK | 查看 English 语言列表；不选择其它语言 |
| 6 | MENU | 取消列表 |
| 7 | MENU | 关闭菜单到待机 |
| 8 | MENU | 重开完整菜单 |

每 accepted 键后返回与 step/attempt/nonce 对应的合格真实截图；代理实际看图后才另调用原 explicit_confirm，窗口不延长。HTTP202、click、PNG hash、fixture 或原生收键单项均不能代替菜单语义验收。语义不符或原生错误立即原 End，不补键、不换容易路径。

## 预算与失败

后续唯一一轮 8 分钟，8 accepted、10 显式 attempts，最多 2 个有归因未入队恢复且每 step 最多 1 个。helper 本身 `preflight_not_clicked` 默认 End；身份变化、异常、回包丢失、非对象/畸形回包或点击后异常均 unknown，必须 End，不能重发。

只有原 PAGE 的 `not_posted` 或完整 requestID 对应的明确未入队拒绝，才走原恢复 capture→代理看新图→显式 recovery_cancel；cancel 返回的新图还需独立 `recovery_review`，再由新的明确 planned 调用使用新 nonce。恢复不复活旧点击，也不为 helper no-click 增加恢复分支。

End、API16 恢复、QEMU退出/reap、双锁释放、端口关闭、网页 final ACK 和自有 browser 回收仍逐项留证。固定 FX3 平台、原 PAGE/server 字节、20 秒、原生返回值/错误/超时不改；无相机/USB/SD/FX6 动作。
