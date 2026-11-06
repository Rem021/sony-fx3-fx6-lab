# FX3 TRY2 v24 宿主启动门候选与本轮失败回执

**结论：v24 宿主启动门验证通过；随后唯一一轮真实 browser+guest 到第 12 键时出现 MENU 弹窗未关闭，完整交互及 31/32 键验收未通过。** 详细逐键证据见 [`try2navreview-web-v24-a215a4af/MANUAL-BROWSER-RESULT.md`](../../../runs/try2navreview-web-v24-a215a4af/MANUAL-BROWSER-RESULT.md)。已授权的 v22 单轮在 0 个按键时观察到原生省电关机；为防止浏览器尚不可控时浪费 guest 空闲时间，独立 v24 候选将 HTTP 网页就绪和显式 Start 放在取得双锁及 QEMU Popen 之前；未改 v22、固件、CPIO、DTB、Backup、定时器或默认入口。

## 原实跑与资源

- 原轮：[`try2navreview-web-v22-c3aed1dd/MANUAL-BROWSER-RESULT.md`](../../../runs/try2navreview-web-v22-c3aed1dd/MANUAL-BROWSER-RESULT.md)，同目录的 `receipt.json`、`serial.log`、待机与终态 PNG。卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，网页显示完整待机；之后尚无按键便发生 `FX3_BOOT_QUEUE_SEND ... source=0x830128` 和 `scr0039_shutdown`。`key_steps=0`、`health_pass=false`，host 总时长 340.857783 秒。协调端提到 Orca 容量错误，精确发生时刻不在 run 时钟里，因此不把它证明为原生关机的唯一原因。
- 原轮 QEMU exit 0/reaped、API16 原字和 20 秒 guest ACK 回执通过、输入 SHA 未变、两锁退出后独立检验 free；这是**故障收尾通过**，不是菜单通过。原浏览器 final ACK true，未点击人工 End。
- v24 验证没有启动 QEMU；本轮不再占运行锁，也没有打开相机、USB 或物理 SD。

## v24 变更与精确边界

- 源从 `host-terminal-v23` 派生，完整改动见 `runner-v23-to-v24.diff` 和 `web-v23-to-v24.diff`；所有最终文件 SHA 在 `FREEZE.json`。runner SHA256 `1f27f7078b3f26752ef1b73053a07607300750e4d2523d8e96e6f615a090d39d`，web SHA256 `3cf9544f08fbdf62dee46420170f5fb85dfae1c656b8a24c062c7b055d64fde1`。
- 固定候选预检完成后先绑定 loopback HTTP；页面状态轮询成功才 POST `/api/browser-ready`。只有操作者在该页点击一次 Start，携带本次 UUID，runner 才尝试原有双锁，之后 Popen。HTTP 线程不碰 QMP/guest。重复的同 ID 请求幂等，不同 ID 被拒；丢失 Start ACK 时网页只读 `/api/status` 精确匹配 ID，**不自动重发**。网页 End、启动前超时、冲突都经原有终态回执及 HTTP 线程收尾。启动成功后才重设会话 deadline，启动前握手独立上限默认 180 秒（参数范围 30..600），实际会话默认 60 分钟/4096 键；`--internal-hoststep` 在 v24 主入口明确拒绝以免绕过此门。
- Start 已接受而 End 若先于 Popen 检查到达，则本轮不 spawn；若 End 在 Popen 临界点之后到达，按既有 guest 退出路径收尾。**不主张任意并发时序都能保证 spawn0。** `restart_requires_new_authorization` 仅属于本轮 Orca 调度回执，不是产品用户每次启动要向我们申请许可。
- 终态页面顶端以中文说明原生关机/健康失败，显示“已结束”与实际秒数，原始错误留在折叠“诊断详情”，无最终帧时占位显示“本轮已结束”。不改变错误门、像素身份门或原生停机判定。
- 追加修正 Start 回执未知且只读状态 ID 持续不匹配时的可见性：红色主提示持续显示并展开可读诊断；仍禁用再次 Start，End 可用。状态最终匹配后清除该暂态提示，终态错误仍优先显示。

## 验证回执

- `launch-protocol-test-receipt.json`：真实本地 HTTP 的 browser-ready、Start 幂等/不同 ID 拒绝、只读状态匹配、取消/超时、同进程 flock 局部检查通过；这是协议局部测试。
- `production-launch-test-receipt.json`：抽取**生产 runner 启动与清理函数体**，仅跳过候选静态预检/命令生成，以真实 loopback HTTP、双锁和 fake Popen 运行。浏览器未就绪 Start→409 后超时、无浏览器超时、启动前取消、已接受 Start 后及时 End、第二把锁冲突均 Popen 计数 0；正常与同 ID 重复只调用一次 fake Popen，然后 fixture 故意抛错。每例最终状态 HTTP ACK、server 线程退出，第一把锁释放；第二锁冲突例明确保留外部测试 owner 的第二锁，随后测试自己释放。真实 guest 未启动。
- `browser-start-v24-start-ack-drop/receipt.json`：在**真实 Chrome 新标签**打开宿主 fixture，先看到 guest 七键禁用、Start 待就绪后启用。人工点击 Start 一次，代理已把后端 HTTP 202 ACK 丢弃，页面依据状态显示“仅宿主握手成功”，Start 保持禁用；随后人工 End，页面显示最终结果。原始请求表恰好一个 `/api/start`、一个 `/api/stop`、一个 `/api/final-ack`，`accepted_count=1`、`guest_started=false`、线程回收、final ACK true。此为追加提示修正前的历史 web SHA。
- `browser-start-v24-terminal-apo/receipt.json`：真实 Chrome 新标签显示“观察到原生关机”、`已结束 · 实际 341 秒`，固件键与 Start/End 都禁用；展开“诊断详情”仍能读到 synthetic `native_model_power_off_observed` 原文。该 fixture 只复现原轮终态字段，不是再次运行 guest；对应追加提示修正前的历史 web SHA。
- `browser-start-v24-start-ack-unmatched/receipt.json` 与同目录三张浏览器 PNG：真实 Chrome 新标签只点击 Start 一次，代理在到达后端前丢包，浏览器 ACK 未知且状态 ID 始终不匹配。初次与多次轮询后红色主提示可见、Start 禁用、End 可用；人工 End 后 final ACK true、线程回收、后端 accepted 0、guest 0、原始 HTTP 路径中只有一个 `/api/start`。前两张 PNG 像素 SHA 均 `fa62abc07173be68c9755d337847493c2dc52e4bdfe60f496c3386378ad4592c`，证明有限轮询间可见状态持续；最终 web SHA 与冻结一致。
- 宿主 fixture 的 Chrome 新标签均已关闭，未动用户原有标签。Orca 内置浏览器访问 host 暂不可用；本轮曾创建的独立 Orca fixture 标签也已单独关闭。早期 ACK-drop/terminal 两份 receipt 对应修改前 web SHA，作为历史保留；最终冻结 SHA 的定向 unmatched fixture 已落盘截图。原 v22 guest 轮的待机/终态 PNG 已落盘。

## 待验与下一轮最小方案

v24 后续唯一一轮已真实验证浏览器握手后 QEMU/双锁/首帧、人工 End 在 Popen 后的 API16 完整路径、前 11 键完整图逐键确认；第 12 键 MENU 已接收却未关闭 Power Save Start Time 弹窗，因此停止且 31/32 边界及持续操作仍未验。原生关键差异与下一轮最小观测点见上面的实跑报告。不得把宿主 fixture 或本轮健康退出当作 guest 可用性通过，也不更新默认 TRY2 入口。
