# r25 恢复观察合同

本候选只修复“原 PAGE 明确证明未入队”后的观察流程。原 r24 真实运行仍为 7 accepted keys / 7 confirm，第8次 not_posted，八步整体失败。此目录不部署、不开真实 QEMU；离线 native 与视觉判断均为 MOCK。

## 身份、采集与失效

恢复观察 fx3-recovery-observation-r25-v1 / qualified_recovery_observation 是 agent-browser screenshot 实际新采集的浏览器视口 PNG。目录以 exclusive mkdir 创建，保存 session、URL、observation UUID、实际路径/SHA/长度、宿主起止时间及截图前后两份原状态。两端记录显示帧 SHA/gen/seq，但不把它们合成为 PNG 的固件身份：firmware_generation=null、input_permission=false、postkey_confirmation=false，不声称像素因果性。

每个端点先验证原 r24 PAGE SHA，读 fresh /api/status，再在无 await 同步片段检查 document 对象/脚本未变、URL、timeOrigin、reviewDocumentId、launch、step、完整 attempt binding、not_posted 且 mutation_called=false 或准确 explicit_rejected_unqueued、同 nonce 和 due/armed alarm 身份、ready、无 error/busy/review/unknown/End、原 frameLoadedFor。fresh status 也必须同 launch/step、ready、render_valid、无 error/busy/review/unknown。前后 document/launch/step/attempt/alarm 身份必须完全相同，seq不得倒退；画面 SHA/gen/seq可前进或变化。

端点是有限观测，fresh HTTP、JS同步片段、截图与 guest 不构成原子事务；不能证明区间中未观察到的瞬变，也不能将服务器回包后的变化视为已知。恢复图只供历史观察，下一键仍使用自己的全部实时门禁，所以不把端点证据提升为输入许可。

armed 模式保留原 RecoveryEligibility 与20秒到期门；cancelled 模式绑定同一原 helper 的精确取消回执，包括 nonce、armed/due/cancelled、文档身份、匹配 cancelled event 与 elapsed。原 helper 在赋值 cancelled_ms 后另取日志时刻，允许 event.performance_ms 后于赋值且不晚于当前时刻；不加 epsilon。浏览器 JSON.stringify 的取消身份字符串保留 JS 双精度往返，避免工具对象重编码后的末位变动；20秒等式在同一个浏览器片段内精确判断并与 deadline_ms=20000 一起返回，宿主不重新对已被工具编码的数字做可能产生 1 ULP 假失败的等式。

## 完整显式流程

1. 单独 operate.py click 仅调用原按钮一次；PAGE归因未入队后采集取消前恢复观察，返回真实PNG，0新按键POST。
2. 操作 agent 实际查看返回图，在另一调用 operate.py recovery_cancel 中显式填写判断。先校验原回执固定SHA与实际PNG，再调用原同nonce取消；无 key/confirm/new alarm。
3. cancel helper 在取消后独立新采集另一恢复观察，绑定同取消回执。返回这张新图，禁止把前图复制为后图。
4. 另一调用 operate.py recovery_review 实际查看后图后显式填写判断。PNG、观察回执、cancel回执、binding、ledger与当前attempt逐项绑定；同时重查fresh/PAGE生命周期、同一cancelled nonce。
5. 下一次单独 operate.py click 再核上述链接及生命周期，单次消费恢复审阅，生成新nonce后走原 planned click。正常 prerequisite 来自初始待机或上一个真实postkey快照的精确确认；恢复图永远不创建 postkey prerequisite。

任何未知/End/身份变化/错误nonce/篡改/未单独审阅/重复恢复/预算耗尽均拒绝并由 wrapper 原失败清理调用 End，不自动重试、延迟点击或重新武装。原计划 SHA 4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f 不变，最多8accepted/10attempts/2attributedrecoveries且每步一次；每个alarm仍20秒。server max_steps32仅保留原r24最后确认就绪行为，脚本只允许8accepted。

## 保持项与证据

r24 PAGE、server、runner、正常 postkey snapshot/confirm、planned click、deadline、initial standby capture等源均按原字节复用；只派生 recovery_tools/read/cancel、operate 和 preflight，新增 recovery_observation/recovery_guard。固定 FX3 QEMU/kernel/DTB/CPU/内存/时钟未改，r24全部151项与r21全部145项由独立预检查再次核验。

同步片段边界参照 [MDN execution model](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)（2026-11-04核查）；Window内时间信息的上下文范围参照 [MDN Window.performance](https://developer.mozilla.org/en-US/docs/Web/API/Window/performance)。
