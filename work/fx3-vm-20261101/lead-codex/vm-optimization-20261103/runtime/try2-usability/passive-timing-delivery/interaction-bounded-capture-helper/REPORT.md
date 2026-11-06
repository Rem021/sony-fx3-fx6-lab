# 原 FX3 第 1 键 MENU 有界只读取图：离线候选

**结果：仅完成 host 候选。** 在固定 r17 PAGE/TrialState、原 20,000ms 闹钟、独立 Chrome 单标签的离线 fixture 中，5 个定向场景通过；未启动 QEMU、未按真实固件键、未部署或修改既有 helper/PAGE。取图结果不作菜单语义判定。

## 设计与边界

`bounded_capture_cli.py` 要求自有唯一 tab、精确 loopback URL、launch UUID、当前 alarm nonce，以及独占的新证据目录。`bounded_capture.js` 验原 PAGE canonical SHA、document/timeOrigin、alarm version/identity/armed/原 due、step 1 review、已加载 PNG SHA+generation；只在已知完整 MENU 固件 PNG SHA 出现时取图。浏览器等待上限 8s，同时为原闹钟保留至少 8s；截图后 `capture_after.js` 再核原 identity、同 SHA/gen、可前进的同内容 seq 和剩余余量。浏览器截图只捕一次；任何竞争、过期或错误均不返回合格截图，保留原闹钟。

第一次真实 fixture 揭示 `due_ms` 以 JSON number 经 JS→Python→JS 返回时可能相差一个 ULP，使严格同一 due 校验误拒绝；失败原始回执留在 `evidence/run-4c3eff27`。最终候选改用原 JS 数值的 `toPrecision(17)` 字符串 token 做**精确同一性**比较，不使用 epsilon，也不延长 due。PAGE/document timeOrigin 同样采用该精确 token。`capture_after.js` 的逐项 `failed_checks` 让身份竞争可复核。

最终 fixture 回执：`evidence/run-301d75e2/RESULT.json`，5 场景 `passed=true`。中间图→参考图约 917ms 取得合格网页截图；未匹配参考图约 8033ms 明确失败且不截图；错 nonce 约 16ms 拒绝；原生产 20s 闹钟到期后约 56ms 拒绝；截图后 fixture 发布新图使后身份失败，保留不合格截图。所有场景 helper 发客体键 0 次、调用确认 0 次；原 alarm 在非到期案例保持 armed。最终成功截图已人工查看，fixture 页面显示 English、橙色焦点和完整 Setup/Area/Date 菜单；该页面由历史完整固件 PNG 与离线 TrialState 组成，**不是新 VM 运行画面**。浏览器 cleanup 回执是 `active=false,pid=null`。

`timeline` 记录 tab 预检、前 eval、截图、后 eval、回执写入的 UTC 与 host monotonic；网页前 eval 另含 `performance.now()`。8s 仅限制页内等待，CLI/截图仍可能拖到 alarm 余量不足，后验会拒绝。这一候选减少固定睡眠造成的已知空窗，却不能证明真实 20s 人工完成。下一门按 `OPERATION.md` 实际演练操作员看图→原显式确认一次→同 nonce 取消，并逐段打点；不把 fixture 的自动发布参考图当自动语义确认。

源码与输入哈希在 `SOURCE-FREEZE.json`、`DEPENDENCIES.json`；本目录交付哈希在 `SHA256SUMS`。所有历史 run/冻结件不变。
