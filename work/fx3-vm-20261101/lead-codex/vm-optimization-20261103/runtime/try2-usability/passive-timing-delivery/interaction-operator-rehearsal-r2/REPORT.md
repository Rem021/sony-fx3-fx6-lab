# r2 单次操作员模拟演练：passed

本次真实完成一次“原20秒arm → 真实页面模拟MENU → r2有界捕图并在同工具返回图像 → agent亲看完整目标 → 下一工具明确调用原explicit_confirm_cli一次 → 同nonce取消”。结果为 **confirmed_and_cancelled**，arm至cancel **11,452.5ms**，原due未变、还余8,547.5ms。随后原End HTTP202和finalACK HTTP200，全部自有资源关闭。**只证明这一轮模拟操作链可行，不构成产品菜单、VM或guest验收，也不证明可重复性/硬实时期限。**

## 授权、依赖和唯一轮

协调端放行消息msg_ca67cbbf15df明确批准已准备的唯一离线计时演练，引用新helper完成消息msg_fb43ed9af674。此前只有准备和5项本地假CLI校验，未创建fixture/browser、未arm或点击timed MENU；PREPARATION-STATE和PREPARATION-RECEIPT保留当时状态。放行原文的固定SHA写入COORDINATOR-RELEASE.json，真实启动和arm之前dependency_gate逐项核验：

| 冻结包 | 已核范围 | SOURCE-FREEZE / SHA256SUMS |
|---|---|---|
| interaction-bounded-capture-helper-r2 |5源、8依赖、30交付|067d37467a01b9950c8ce7b7eba8334d3a331803baedcdf2b6248bab04afd4fe / c54bac33e5271ac0a6c00b2ccf2f3e87754ab435825d270c82074ecd975bdd2e|
| interaction-explicit-confirm-helper 原版 |4源、3依赖、45交付|8c751f05ab82a94ee06c7c0154ba48967bc7909a6100fd1a77cc9f022c23285a / b0f7d8e107ec5758227792bfb76d91ac33f8acfc640f83c044f8772fe6d4a49f|

r2 REPORT固定SHA792615f76e6e1d131c90598af6739e6cf19115eba21af36450a35965e82c0c9a。前后核验一致，含原PAGE、deadline、explicit JS、两份历史PNG和旧失败报告/receipt依赖；没有修改任何冻结目录或旧failed结论。外盘UUID F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B再次核对一致。本任务仅写本新目录，没有QEMU/guest/平台/部署/入口/ledger变更，没有其他worker。

本轮身份：自有唯一session `fx3-deadline-operator-rehearsal-r2-0b081725`，1280×1200，http://127.0.0.1:64311/ `http://127.0.0.1:64311/`，PAGE launch_request_id `e49ce6f6-289a-49d2-bd0d-4e1775c909eb`，fixturePID98821。Start/模拟MENU/confirm/End均由原PAGE按钮click触发原HTTP handler，没有脚本直接POST。原TrialState.submit只接收一次假MENU；fixture后端同步消耗假队列、设step1 review，用线程timer在指定7秒后publish历史完整图。该后端不调用任何原生代码，不提供down/up/done/原生耗时证据。

## 返回失败传播修复及本地检查

旧capture_once失败仍exit0的问题在本目录派生脚本修正，原文件不动。capture_validation.py同时要求bounded CLI returncode=0、JSON status精确qualified、绝对screenshot_path位于**此次新建的独占menu-capture-01目录**、文件存在且非symlink/普通PNG/hash相符；失败返回非0及原因，不输出可展示路径。capture_once在调用前拒绝已存在的capture目录，并以独占once-only-arm-marker阻止重复演练。外层实际functions工具再检查exit0/合格status/validated=true/本轮精确路径，才view_image并在该同一工具结果展示图像。没有取旧图或不存在图。

WRAPPER-LOCAL-RESULT保存5项最小假CLI子进程检查：nonzero但伪称qualified、未qualified、缺失图片、目录外旧图均wrapper exit2且无screenshot_path；本轮目录合格文件对照exit0。测试不启动浏览器、timer或PAGE；这不是重复演练或重跑helper的大量fixture。

## 实际看图与确认身份

在返回图像中，agent实际看见完整Setup > Area/Date（45/59），Area/Date/Time Setting整条橙色焦点及右箭头，Language/English清晰可读，End按钮完整可见。参考SHA只负责触发取图；不是由SHA自动批准目标。亲看之后下一次工具调用才运行confirm_once.py，它调用原冻结explicit_confirm_cli一次，没有与arm/key/capture脚本合并自动确认。

| 身份 | 本轮值 |
|---|---|
| 参考/已加载固件PNG shownSHA |60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292|
| 网页整张截图文件SHA（不可代替shownSHA） |e83511faf4a389e8ba124a7a1b5ca39d80c3f2b602ded896a5ae61232e7063f9|
| 截图前 / 后sequence |213 / 213|
| 截图前 / 后content_generation |2 / 2|
| 同nonce |ea8300c8-4cc3-4af7-8d9a-6fa6d51354c5|
| 原due performance_ms / precision17 token |34655.59999996424 / 34655.599999964237|
| confirm request_id |45215a54-a82b-4dca-968e-6bee50a60961|

before/after均与当前frame一致、render_valid、完整图已加载，after.failed_checks=[]，截图后仍余12,534.3ms。原确认POST请求/HTTP200 body、expected历史receipt与ready当前frame的step/seq/gen/SHA/request_id全部一致，guest_input_written=false；原explicit工具确认原PAGE的七键放行后才cancel相同nonce，状态cancelled，due未变，elapsed11452.5<20000。见explicit-confirm-receipt、HTTP-confirm-visual、capture-result及validated-image-return。这里实际捕获到HTTP200，不以status recovery代替。

本轮capture第一次页内采样已是ready_loaded_review，awaiting_step=null、steps=1；未经过accepted_menu_waiting_for_status。故本次验证完整操作链，但不声称再次触发并证明r2的初始状态等待分支；那一分支的6场景离线证据属于已接受依赖，本轮没有重跑。

## 时钟与空窗

UTC均为2026-11-04。host monotonic与网页performance分别保留，不跨原点相减。OPERATOR-TIMELINE.json保留准备、arm/key、等待、截图、返回准备、下一确认脚本入口、HTTP写出、放行/取消各段原始记录。

| 阶段 | UTC | 同域时钟 |
|---|---|---|
| 准备进入 / 完成 |21:38:32.252168 /37.223874|host411997.798351041 /412002.769900750|
| arm CLI进入 / 返回 |21:38:48.312403 /48.373910|host412013.858381750 /412013.919897958|
| 原PAGE armed |21:38:48.367|performance14655.599999964235|
| 模拟MENU click进入 / 返回 |21:38:48.374035 /48.383201|host412013.920013208 /412013.929182541|
| MENU HTTP202写出 |21:38:48.383170|host412013.929148583|
| bounded CLI进入 / 返回 |21:38:48.383443 /55.842666|host412013.929421541 /412021.388625083|
| fixture完整图publish |21:38:55.392192|host412020.938187458|
| 原PAGE已加载参考 |21:38:55.736|performance22025.099999964237|
| 截图进入 / 返回 |21:38:55.742510 /55.826111|host412021.288462750 /412021.372087250|
| 取图后验通过 |21:38:55.833|performance22121.300000011920|
| 合格图工具返回准备边界 |21:38:55.843531|host412021.389481458|
| **下一工具**人工确认包装器入口 |21:38:59.682381|host412025.228448291|
| 原explicit CLI入口 |21:38:59.722245|host412025.268319583|
| 原confirm click |21:38:59.734|performance26023.099999964237|
| confirm HTTP200写出 |21:38:59.735879|host412025.281813500|
| 匹配receipt和当前ready / cancel |21:38:59.819 /59.820|performance26108.099999964237|
| explicit CLI返回 |21:38:59.822076|host412025.368024208|
| End HTTP202写出 |21:39:05.646651|host412031.192568625|
| finalACK HTTP200写出 |21:39:05.878441|host412031.424380916|

页内等待参考图7,295.600ms；capture函数宿主7,405.937ms，外层bounded CLI调用7,459.204ms；截图83.625ms。fake handler→目标publish实际7.009957s只是指定7s模拟timer加本机调度/日志开销，不是guest/VM延迟。

合格图**返回准备边界→下一人工确认脚本入口**宿主间隔3,838.967ms。该间隔包含工具返回/图像编码传递、模型看图与判断、下一调用调度，不能拆为纯模型思考耗时。模型实际收到图像、看完语义的UTC/monotonic无可测钟，均unknown；没有用截图mtime或工具准备边界冒充。explicit CLI宿主99.705ms；完整人工包装器147.907ms；原页面click→匹配ACK/当前ready/cancel约85ms（同performance域）。arm→cancel页面11,452.5ms，余8,547.5ms；不跨host/performance域计算。

## 计数、停止与清理

实际POST只有browser-ready200、Start202、模拟MENU202、confirm-visual200、Stop202、final-ack200各1次；接受假键1次、实际guest键0、确认1、取消1、重发/自动确认0。历史PNG加载及状态GET不算固件键。MENU202→Stop202宿主17.263420s，confirm成功后没有下一键。原alarm未到期、未自动End、未重新arm，原due始终同一值；主动End没有逆转。

End先于日志/哈希封存。成功dispose后关闭自有browser（active=false,pid=null）；仅SIGTERM本fixture使server.shutdown/server_close/join正常结束，server_thread_alive=false且final_ack_seen=true，进程exit0。CLEANUP.json独立核PID98821不存在、127.0.0.1:64311 connect_ex61/无监听。无守护进程、launchd或后台残留，不触碰用户其他session。

verify_evidence.py只审计本轮已有证据、准备7份操作源未变及固定依赖，全部通过；无新fixture/browser/VM。RESULT.json为分项/派生时差，SOURCE-FREEZE.json绑定本目录源码，SHA256SUMS覆盖新工件。旧failed保留。成功只支持**这一次**完整模拟操作链；不推断原生MENU时序、真实8键链、API16恢复、性能结论或20/30秒硬实时保证；后续真实运行仍需协调端另行安排。
