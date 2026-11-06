# 单次操作员端到端演练：failed

本轮未完成“亲看完整目标→explicit_confirm_cli→同 nonce cancel”。真实浏览器中的一次模拟 MENU 得到 HTTP202，但冻结取图辅助在原页面下一次状态轮询前立即拒绝，未返回合格截图；没有执行确认或取消。失败后先通过原 End 按钮停止，保存失败证据，没有重试。本轮只用原 r17 PAGE/TrialState、历史 PNG 和轻量本地模拟后端，实际 guest 键为0，未运行 QEMU/guest、部署或修改产品/平台/冻结文件。

## 范围和准备

- 自有 session：`fx3-deadline-operator-rehearsal-9240ea35`，唯一 tab，1280×1200，URL `http://127.0.0.1:62277/`，页面 launch_request_id `13cb80fa-2e76-45d3-a862-a0a00c7836d0`。fixture PID94792。
- 先核目标卷 UUID F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B；实际 Git 查询确认 Mac 非 Git 仓库。只新建本目录，未改入口、ledger、原报告或候选。
- 协调端依赖通知 msg_3a294c4021c6 后才 arm；自行核 bounded helper 51交付/5源/5依赖、explicit helper 45交付/4源/3依赖，前后源码与依赖一致，见 DEPENDENCY-VERIFICATION.json 和 RESULT.json。
- 原 PAGE 文件 SHA cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb；安装回执 canonical PAGE SHA fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478。原生产 alarm 固定20000ms，未替换源码常量或门限。
- 原始待机/partial来源 trial-step-01-key-1ab.png，SHA2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e；完整参考 trial-final.png，SHA60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292。均只读自旧 c33f8c46，未复制/修改。此处partial是待机图，不是后来那张局部菜单截图。
- fixture 原 Start HTTP握手后布置 ready；原 submit 接受唯一模拟 MENU 后同步消耗假队列、布置 step1 review，并用 threading.Timer 在7秒后发布完整参考图。**7秒是指定演练参数，不是VM或host实测延迟**。无原生down/up/done含义。
- 参数、独占 nonce、确认目标、两段脚本在 arm 前准备完成。capture_once.py 只有 arm/一次页面键 click/取图，没有confirm；confirm_once.py 仅备妥，实际未调用。

## 分段时钟与失败

所有下表 UTC 均为2026-11-04；host monotonic 为同一本机域。网页 performance_ms 另列，未与host原点相减。完整打点见 prepare-timeline.json、operator-capture-timeline.json、capture-result.json、fixture-events.jsonl 和 RESULT.json。

| 边界 | UTC | host monotonic / 网页 performance_ms |
|---|---|---|
| 准备进入 |21:27:43.762931|411349.310047208|
| 真实 Start click进入/返回 |21:27:47.521802 /47.533917|411353.068791416 /411353.080912833|
| 准备完成 |21:27:47.945438|411353.492410750|
| arm CLI进入 |21:27:57.977493|411363.524419250|
| 网页 armed |21:27:58.028|performance13531；due33531|
| arm返回且核验 |21:27:58.035535|411363.582469416|
| MENU click进入/返回 |21:27:58.035692 /58.044651|411363.582618083 /411363.591587041|
| MENU HTTP202写出 |21:27:58.044962|411363.591886541|
| bounded CLI进入 |21:27:58.044898|411363.591825791|
| 取图 before_eval进入 |21:27:58.094890|411363.641818416|
| 页内拒绝 |21:27:58.100|performance13603.69999998808|
| bounded CLI返回 |21:27:58.108752|411363.655683125|
| 工具返回准备边界 |21:27:58.108988|411363.655913250|
| 原 End HTTP202写出 |21:28:01.647083|411367.193997458|
| 网页finalACK HTTP200写出 |21:28:01.988397|411367.535317750|
| 模拟完整图迟到发布 |21:28:05.060214|411370.607126708|
| alarm到期已结束，仅记录 |21:28:18.031|performance33534，elapsed20003ms|

网页在取图检查前最后一份 status 回复为21:27:57.935557，MENU后第一份 status 回复为21:27:58.340667；取图检查位于两者之间。原 PAGE 仅在 tick 获得 status 后替换 lastStatus（trial_web_v22_navigation_review.py:339），并在372行以后按该status清除 awaitingStep；388行是400ms下一轮轮询。bounded_capture.js:32–37 对 step1/review/input/awaitingStep 等前提立即抛出 phase_or_input_gate_not_ready，67–75行仅在这些前提通过之后才等待参考PNG。

**可证事实**：错误为该组合门拒绝；页内只运行0.400000036ms，取图capture函数13.801ms（外层bounded CLI调用打点63.854ms），未尝试截图；before_eval进入在假键handler进入后50.894ms，早于新status。**依据源与时间序列的推断**：原PAGE还没有消费step1 review的新status，因此 capture 提前调用；这不是7秒参考图等待超时。没有在失败瞬间逐项dump所有词法变量，不能把组合门中的唯一失败项声称为直接采样结论。

外层工具还因 capture_once.py 失败时仍exit0、包装器仅按exit_code决定取图，尝试读取不存在的 menu-reference-page.png，返回“unable to locate image”。这是本次操作包装器的错误；没有实际合格图像返回，未因此确认或再次取图。脚本保持原样供审查，没有事后修复或补跑。tool_image_return_preparation_boundary 只是命名的宿主返回准备边界，本轮无目标图像可返回，不能当模型收到图像的时刻。

7秒定时发布在 End 后仍触发，实测 fake MENU handler→publish 为7.016203秒（含本机调度/日志开销）；state保持finished，PAGE已停止轮询，不表示操作员看过完整菜单。这里只留存该模拟后端行为，不把它充作目标完成或guest证据。

## 分项结果

| 项目 | 结果与证据 |
|---|---|
| 原PAGE/真实Chrome/真实模拟MENU HTTP202 |passed；一次，见fixture-events及脱敏browser-HTTP-metadata|
| 7秒模拟完整图发布 |调度已触发；发生在已停止之后，无验收意义|
| 完整目标合格截图/实际agent看图 |failed / not_reached；screenshot_attempted=false|
| explicit_confirm_cli / confirmHTTP |not_invoked；0次，没有独占confirm receipt|
| 同nonce cancel |not_reached；0次，不能声称confirmed_and_cancelled|
| 原nonce和due未改变 |passed；nonce2273f116-c81b-4c40-96d9-c6b2f27a40b7，due33531|
| 失败先End/不重试 |passed；keyHTTP202→StopHTTP202为3.602111s，远小于20s；没有第二键或确认|
| 后备20秒 |到期elapsed20003ms，already_stopping_or_disabled、phasefinished；0自动Endclick，不逆转终态|
| 收尾 |passed；End202、finalACK200，fixturePID absent、端口closed、browser activefalse/pidnull|
| 原helper/PAGE/PNG不变 |passed；前后固定源码/依赖hash见RESULT.json|
| 端到端人工确认链 |failed；没有到达，不作产品菜单/VM通过声明|

模型实际收到图像、语义判定完成的时钟均unknown；本轮本来就没有合格目标图像。下一确认调用入口、确认HTTP和取消打点也不存在，不补造。prepared-page.png供准备布局检查，ended-page.png仅证明结束时页面；都不是已审完整目标。

第一次dispose在alarm仍armed时exit1，deadline-dispose.json为空stdout且未保存该调用stderr，不能从空文件声称成功。未提前cancel；原due到期后 cleanup-status.json证明sealed expired/already_stopping_or_disabled，再显式dispose成功，保留于cleanup-dispose.json。随后关闭唯一自有session、SIGTERM只用于本fixture并正常server.shutdown/join，exec进程exit0；CLEANUP.json独立核PID不存在、端口connect_ex61、浏览器inactive。无守护进程或launchd任务。

## 尚未完成与最小后续

这次演练不能判断原explicit_confirm运行耗时或整个模型工具链是否能在20秒完成，也不能由失败判断firmware反应。本轮到此终止。若协调端后续另行安排，最小需审查一个**同工具内、同nonce/due、总预算内只读等待PAGE消费本步review状态**的前置步骤，再调用现有捕图；或让下一版捕图明确识别安全的“前status尚未追上”暂态。必须保持真实错误/终态立即拒绝，保留原8秒等待和8秒确认余量，不改PAGE、不重发键、不自动确认。本任务未实现该调整、未开展第二次演练或VM。

离线verify_evidence.py只审计本轮文件和冻结依赖，不启动fixture/browser/VM；已通过证据一致性检查，**证据检查通过不改变任务failed**。源码封存在SOURCE-FREEZE.json，全部新文件hash在SHA256SUMS。
