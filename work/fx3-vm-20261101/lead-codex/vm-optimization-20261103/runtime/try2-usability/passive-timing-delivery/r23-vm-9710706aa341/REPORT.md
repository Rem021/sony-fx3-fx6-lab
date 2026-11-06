# FX3 r23 唯一真实八步导航验收：failed（部分完成）

本轮仅一次 Start，7 次显式 attempt／7 次原生队列 down+up+done，步骤 1–6 完成真实看图及独立确认；步骤 7 已看见待机，但原 confirm helper 拒绝，第 8 步未执行。没有重发、恢复或第二次启动，原 r21c 失败不改判。

- 任务：task_9710706aa341；dispatch：ctx_bbaad9d77bcf。
- 准备目录：本目录；原始 runner：../../runs/v25gate-n64-r17-e2699e9d/。
- 固定原 r21 runtime/PAGE/server、原 kernel/DTB/N64 CPIO；实际 QEMU bf4d46481998b8fb…c70d，4×cortex-a35／5120MiB／MTTCG／noicount。实际 argv 见 ACTUAL-RUNNING-ARGV.json 与 RUNNER-LAUNCH.json。
- scripted_navigation=true、visual_review_at_click=false；计划 SHA 4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f。每一步由代理显式调用，原 PAGE DOM 按钮一次，每张 PNG 在该调用工具结果中实际返回并查看；确认是下一次独立调用。
- 首张合格待机图在 Start 后 44.282 秒取得（180秒限）；本轮运行 165.466 秒（480秒限）。固定运行参数：--port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2；输入上限仍8 accepted／10 attempts／2有归因未入队恢复，每步至多1恢复。

| 步 | 实际新图语义 | 原生down/up/done | 独立confirm |
|---|---|---|---|
| 1 MENU | Setup > Area/Date 45/59，橙色Area/Date/Time Setting | 全部result=0 | 成功 |
| 2 UP | 橙色Language，English | 同上 | 成功 |
| 3 C4 | Language帮助，Selects the display language. | 同上 | 成功 |
| 4 MENU | 返回Language English | 同上 | 成功 |
| 5 OK | 语言列表，English选中；只查看 | 同上 | 成功 |
| 6 MENU | 取消列表，值仍English | 同上 | 成功 |
| 7 MENU | 关闭菜单，返回NO CARD等待机图标 | 同上 | 拒绝，立即End |
| 8 MENU | 未执行 | 无 | 无 |

## 第7步精确失败边界

截图后校验 UTC 2026-11-05T00:57:25.902Z，browser performance_ms=172110，sequence=1373、generation=33、PNG SHA=2914275c…182e；当时记录的 image/review/phase/同内容等检查均为true。确认 helper 在 00:57:35.208Z、performance_ms=181416.6 调用，相隔 **9306.6ms**；00:57:35.209Z 返回 refused：current_review_or_loaded_image_not_ready，click_invoked=false、expected=null，未调用原确认按钮或发送第7次confirm POST。

确认调用距 arm 11065.9ms，仍余8934.1ms；原20秒timer没有延长。00:57:35.251952Z开始原End工具调用，00:57:35.259911Z返回End_invoked=true。完整时间、原件指针及未知项见 [FAILURE-BOUNDARY.json](FAILURE-BOUNDARY.json)。模型实际收图／看图完成时间均unknown，工具返回边界不冒充模型收图时刻。

原 confirm.js 的精确 OR 联合条件（来源路径及SHA见FAILURE-BOUNDARY；其前置PAGE身份、fingerprint、alarm检查未抛错）：

~~~javascript
if (s.phase !== 'ready' || s.error || s.busy || !s.render_valid || !s.frame ||
        !s.review_required || !s.input_received || s.review_step !== c.step || s.steps !== c.step ||
        s.frame.PNG_sha256 !== c.png_sha || shownSHA !== c.png_sha || displayed <= 0 ||
        displayedGeneration !== s.frame.content_generation || img !== image ||
        !img.complete || img.naturalWidth <= 0 || b !== confirmButton || b.disabled || b.hidden ||
        typeof b.onclick !== 'function' || busy || ending || finished || renderFault ||
        awaitingStep !== null || deliveryUnknown || reviewAwaiting || reviewUnknown ||
        pendingConfirm !== null || launchUnknown) fail('current_review_or_loaded_image_not_ready');
~~~

HAR最后一个拒绝前status请求在00:57:35.130130944Z，返回ready、steps=7、review_required=true、review_step=7、input_received=true、busy=false、error=null、render_valid=true；该条server frame为sequence1483／generation46／PNG=e0140ea1…6ec4，和已审图不同，此前也有2914275c…182e与e0140ea1…6ec4交替记录。**这只能证明附近server响应与变化，不能证明confirm执行瞬间的lastStatus、shownSHA、loaded generation、img状态、按钮或其它PAGE局部变量；究竟哪个OR项触发保持unknown。**没有新eval瞬时快照，不确定单项根因，不扩大测试。

## 收尾与冻结核对

原End后 API16在原20秒预算内1.315秒取得guest ACK并读回000b00b4fd7bbba9fd030091f35301a9；原始16字节和header保存在runner目录。QMP quit id=685有return={} ACK，QEMU exit=0且已reap；独立核runner47314／QEMU47449 absent、60889端口closed、双锁free。网页final ACK=true，自有browser active=false；残留armed timer未强制cancel/dispose，随自有文档关闭，原End先行。专用Orca持久终端在确认所有运行进程消失后关闭，详情见EXECUTION-CONTEXT与OWNED-TERMINAL-CLOSE。

r23冻结218项启动前与收尾后均匹配，冻结源码未改。r21源码40项与固定输入14项before/after一致；冻结wrapper的组名delivery145实际遍历DELIVERY-MANIFEST中的144项，145行SHA256SUMS多出的唯一文件是DELIVERY-MANIFEST.json自身，原pins也未单独核它。本轮封存前已只读逐项复核全部145唯一路径，全部匹配，见 [DELIVERY-145-COVERAGE-AUDIT.json](DELIVERY-145-COVERAGE-AUDIT.json)；该文件启动前单独原字节/hash未记录，不声称补出before观测。未改冻结清单或wrapper。

三个授权自然输出的before/after原字节及hash均已留存：preflight文件不变；STATE-v24.json.tmp两端均不存在；STATE-v25-r3.json发生自然更新。仅本次准备目录及runner新run产生其它输出，协调ledger、部署r10和旧实验未改。

原始HTTP在traffic.har，POST索引为1 Start／7 key／6 confirm／1 stop／1 final-ack；7 key HTTP202本身不充菜单通过。web-key-rejections.json原字节304B、total=0，SHA256=5eb4f00bd1d18961cb8587c7ee006f8c7a8f085554b17f6b0442badd632e595f；它是原key拒绝导出，不能抹去本轮confirm helper拒绝。每步原生原行、完整截图和语义判断见NATIVE-VISUAL-SUMMARY，原完整serial及下发证据均保留。tail仍是valid_nontransactional_tail_checkpoint，snapshot_is_end_state=false，后续事件计数unknown。

本报告只裁定本轮八步菜单failed及收尾通过，不升级为4096键／60分钟／全菜单／录像／设备行为或FX6完成。[RESULT.json](RESULT.json)为机器结果，[SHA256SUMS](SHA256SUMS)封存本目录及runner原件。公开协议仅参照[QEMU官方QMP规范](https://www.qemu.org/docs/master/interop/qmp-spec.html)，运行结论取自本轮原始证据。
