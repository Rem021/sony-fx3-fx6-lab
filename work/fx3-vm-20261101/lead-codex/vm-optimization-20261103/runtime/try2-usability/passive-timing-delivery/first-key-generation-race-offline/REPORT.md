# 首键画面代次竞争：离线复现与宿主候选

**结果：两次真实 MENU 请求均被原服务端以 HTTP 409 明确拒绝，固件按键未入队；这不是已证的固件停帧或 bounded capture r3 错误。** 本目录仅有宿主 PAGE 的小候选和真实 Chrome／`TrialState` 离线 fixture，未运行 VM、未部署。候选消除“PAGE 已收到新 status，但新 PNG 尚未加载”时旧按钮仍可点的一个窗口；它不能消除 status 尚未到达时服务端领先的竞争，也不能解释本轮 409 唯一条件。

## 原始回执和可证边界

- 本轮 `runs/v25gate-n64-r17-bdd09f6b` 的一次真实 `MENU` 为 `POST /api/key {key:427, observed_sequence:212}`，HTTP 409 原文“当前画面已变化或不可用，请等待并查看最新画面”；实际 `steps=0`，原生接收／完成为 0，确认请求为 0。拒绝后约 15 ms 的 PAGE 诊断为显示图及 `lastStatus.frame` 均 seq212／generation27／SHA `e0140ea1…`，但它不是 HTTP handler 的锁内快照。`capture-result.json` 仅证明 r3 看到了明确拒绝并以 `no_qualified_screenshot` 停止，未截图或确认。
- 新封存 `MENU8-409-EVIDENCE.json` 中，原生导出 seq212 的 host monotonic 为 `413415.143619833`，不同像素的 seq221 为 `413415.672432791`，浏览器 click 入口为 `413415.692086`；导出 221 早约 **19.653 ms**。导出时间不等于 `TrialState.publish` 时间，且不是 handler 原子状态；它支持帧竞争假设，不能据此指定拒绝时当前 SHA／generation。
- 先前 `runs/v25diag-web-r6-b6209581/INTERACTION-key-http-immediate.json` 亦有 seq196 的 MENU HTTP409、实际 0 键；r11 报告中的 frame196 gen30→frame200 gen31 是相同类型线索，也没有锁内拒绝快照。所有输入文件的路径和 SHA 在 `INPUT-EVIDENCE.json`。
- 原 `TrialState.submit:94-104` 在同一 RLock 下先检查 observed sequence 是否在 64 项缓存；缺失时返回**另一条**提示。本轮提示来自后续复合条件：`render_valid`、`frame`、历史 SHA 对当前 SHA、历史 generation 对当前 generation；现有 raw 无法区分其中具体哪一项。`publish:57-68` 仅在相邻 PNG SHA 改变时增加 generation，同内容 sequence 前进允许旧序号，A→B→A 即使最终 SHA 相同也仍为新 generation。服务端这一严格身份门应保留。

## 最小候选与验证

只复制 r12 的单个宿主模块并修改 PAGE JavaScript；`TrialState`、HTTP handler、`submit/confirm`、键协议、PNG 缓存、健康及清理路径未变，完整差异在 `r12-to-candidate.diff`。`tick` 接收新 status 后，如当前已加载图 SHA/generation 不同，立即只锁固件键与确认，随后照原逻辑加载新图；click 入口再次用**最新已知** status 校验已加载身份，若不符则本地拒绝且不 POST。没有丢弃新服务端帧、绕过 ABA、自动重发／确认，仍由原服务器决定最终接受。原 r11 的 409 持续中文提示保留，新的有效图加载后仍需另一次用户主动操作。

首次实现误用 `disableKeys()`，会连无首帧时的 Start 一起禁用；已修为 `lockVisualControls()` 仅锁固件键和 confirm。最终候选模块 SHA256 `ee135617204a9c724a9e9b8cb5198b2785252de66b07b662105f03b1d130b26c`，规范化 PAGE 内联 script SHA256 `d224a8f10786dc815520a8c11320f8625c1e969f9508bac39541c971ecfb9822`。r12 原模块 SHA256 `cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb`、原 PAGE script `fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478`。

运行 `python3 tests/browser_race_replay.py` 只启动本地受控 HTTP fixture 与专用 `fx3-generation-race-*` Chrome session；它加载真实 r12／候选 PAGE 与真实 `TrialState`，用测试控制端在原 `submit` 前发布帧，并记录请求、原子入口视图、返回、入队及截图。最终 `evidence/run-1793830208691/RESULT.json` 为 `passed=true`，11 个浏览器场景，结束后浏览器关闭、两个 fixture PID 均退出：

| 离线场景 | 实测结果 |
| --- | --- |
| 同内容 seq1→2，generation1 | PAGE 发送 observed seq1；服务端当前 seq2 同 SHA／generation，HTTP202、入队1。 |
| A→B，在 `submit` 前变化 | HTTP409、入队0，提示跨 status 持续可见；B 加载且按钮 ready 后**fixture 脚本第二次点击**才 HTTP202／入队1。此脚本点击不是实际操作员亲看或 VM 验收。 |
| A→B→A | 同 SHA 但 generation3，旧请求 409、入队0；没有借 SHA 绕过代次。 |
| 新 status B 已到，B 图加载被测试延迟 2.2s | r12 旧按钮仍 enabled，点击旧 A 得 409；候选在同窗口禁用固件键，HTTP key 0 次；B 加载后按钮恢复。截图分别为 `baseline-loading-old-button-enabled.png` 与 `candidate-loading-button-locked.png`。 |
| 503 送达未知 | 按键禁用，跨下一次轮询无补发，HTTP key 1、入队0。 |
| 无首帧的 awaiting-launch | 原 PAGE browser-ready 后 Start 保持可用，真实点击产生 launch request ID；固件 key 0 次。 |

`evidence/RESULT.json` 是修正 Start 回归**之前**的初次离线回放，`evidence/run-1793830188592/` 为修正后的首次运行，因测试按钮在 viewport 外而中止；均保留不作最终通过依据。最终依据仅 `run-1793830208691`，其中包含 DOM、服务端请求／入队数和各 PNG SHA；已实际看过旧／新加载窗口和 409 提示截图，图为合成色块 fixture，不是固件页面。

## 集成边界与下一单次验证

本候选只改善**已收到新 status、旧 PNG 尚在加载**的网页窗口。如果服务端先发布新图而 PAGE 的下一轮 status 尚未到达，按钮仍可能发送旧图并正确收到 409；人眼看图到 HTTP 仍有不可消灭的竞争，不能承诺所有首键不再拒绝。保留现有 409 可见提示，让用户在新图实际加载并亲看后，自主决定是否再点；不能自动重试。若需更窄地减少后者，可另审在手动 click 前做一次短时只读 status 身份预检，但它也有读后至 POST 的竞争且增加交互延时，本目录未实施。

**本候选不能直接替换 r17 运行入口。** 原 `interaction-deadline-helper/deadline.js`、`interaction-bounded-capture-helper-r3/bounded_capture.js`、`interaction-explicit-confirm-helper/explicit_confirm.js` 均钉住旧规范化 PAGE script SHA `fe56b484…` 和原 confirm handler 形态；新 script `d224a8f1…` 会被这些辅助合理拒绝。协调端若选择下一 VM，须先另做独立宿主集成包，审查新 PAGE 与辅助的身份绑定并复测启动、确认及停止；不得现场跳过指纹或偷换哈希。

下一次**最有区分力**的单轮实跑准备是：在 `submit` 同一 RLock 的 409 分支有界记录 observed seq 对应 SHA/generation、当前 seq/SHA/generation、`render_valid` 与具体布尔原因，附浏览器 click 前已加载身份及最近 status；不记录 token，不改接受门。这样才可判本轮是否服务端领先、黑帧状态或代次冲突。该仪表未在本任务实施或运行；所有真实 20s 操作员闹钟、guest 性能、菜单语义、生命周期仍待独立验收。
