# r18/N64 唯一8步复测：failed；首MENU截图合格，确认未赶上deadline

本轮实际1个MENU被接受，原生down/up/done齐全；r18新PAGE与同包辅助取得完整目标菜单合格截图。**原20s闹钟到期调用原End，正常退出后才发生显式确认CLI尝试；CLI在点击前安全拒绝，0 confirm HTTP、0 cancel。八步链failed，步骤2–8未执行。** 正常cleanup与合格PNG不代替逐步人工确认完成。

## 身份、冻结与前提

run v25gate-n64-r17-90781f3e仅沿用遗留r17标签，**实际执行r18**：passive-timing-delivery/v25-r18-frame-admission/run_trial_v25_diag_r3.py，SHA c429f375d57a288370fefda0aedb62270fce96220d5b885d12f5ff27f69e789b。SOURCE-FREEZE8cdc1e0c22d4b72c0a5b163d45b998187092ced5a767fd83d682ad382ffffab4，SHA256SUMS05115115c4d91ca0698c252a86853dff9bc58fb2e13fb038bd827b55fb5b3cb6，PAGE3159c196055fcaba3399c26cad2b97dfb8bde9e02d9c543325d559133d1fe444，canonical d224a8f10786dc815520a8c11320f8625c1e969f9508bac39541c971ecfb9822。

35源、14固定输入和67行SHA清单逐项前后核验通过。计数经协调msg_98144d4d3bd2澄清：DELIVERY-FREEZE.files66项，加DELIVERY-FREEZE本身为67行SHA；初次本地误把66用于SHA行数的断言在启动前纠正，没有修改冻结件或跳过记录。ROOT实为menu-repair-01/runtime，OUT为try2-usability；实际导入PAGE/rejection/snapshot/classifier均来自r18目录（R18-PREFLIGHT），没有误用旧模块。

卷UUID F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B，启动前无现有runner/QEMU，两个锁free。固定kernel/DTB/Backup、N64 candidate96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672、CPIOaaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9、cortex-a35/4核/5120MiB/MTTCG/noicount不变。仅一次VM，无FX6/设备/刷写/部署/设置写入。

命令仅--port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2。URL http://127.0.0.1:56139/，自有单标签fx3-deadline-v25gate-n64-r17-90781f3e、1280×1200，runner14490/QEMU14768。网页launch_request_id12b0abbb-8fbc-4fc2-ab5c-c94f15f87272；host launch_uuid74d84930-fa57-4c25-83eb-f5a45744a010。所有操作源码在本run、Start前冻结，三辅助均取r18/operator-helpers；步骤2–8的已审只读脚本未执行。固定源/输入/交付/本轮操作源码结束后不变。

## 步骤与图像

|步|实际请求/原生|图像与确认|
|---|---|---|
|1 MENU|一次POST202；down/up/done通过|完整Setup > Area/Date及Area/Date/Time Setting整条橙色焦点、右箭头、Language English可读；PNG捕取合格，但未在20s内完成确认，因此本步整体failed|
|2 UP Language|未发送|unknown/unexecuted；step2前快照未触发|
|3 C4帮助|未发送|unknown/unexecuted|
|4 MENU返回|未发送|unknown/unexecuted|
|5 OK语言列表只看English|未发送|unknown/unexecuted|
|6 MENU取消|未发送|unknown/unexecuted|
|7 MENU关闭待机|未发送|unknown/unexecuted|
|8 MENU重开|未发送|unknown/unexecuted；跨7→8分支未测|

首个host导出帧Popen后38.514157–38.514344s；180s首帧门满足。亲看初始待机的较晚截图UTC22:32:42.139，seq172/gen23/PNGe0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4，前后SHA/gen一致；最早浏览器显示首帧时间unknown，不用截图时间冒充。

首MENU合格图operator-step-01/capture/menu-reference-page.png：整页文件SHA f402d9cf2a8e0eb59ec7a6d721ee6f04386aa5d4b72439cd407f430d476c6c58；固件shownSHA60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292，前后seq269/gen39、当前frame身份一致且render_valid，after.failed_checks=[]，after尚余13140.5ms。三门returncode0/qualified/本轮新独占路径存在及PNG hash均通过，同一工具结果直接展示该图。agent确实看到了上述完整目标内容，但**实际接图/看完语义的时钟不可测，不能证明发生在alarm到期前**。

r18辅助实际采样3种状态：22:32:50.477 accepted_menu_waiting_for_status（steps0/awaiting1）；22:32:50.724 step_one_visual_pending_native_ack（steps1/busytrue/input_receivedtrue/reviewfalse）；22:32:53.570 ready_loaded_review（partial base PNG168a…/gen37）；后续22:32:57.197完整参考图gen39已加载。**input_pending中间态没有采样到**，不把源状态图或离线fixture的四态冒称本轮四态全覆盖。旧r2误拒的ACK等待态这次实际跨过并取得合格PNG。

serial原始字节偏移保存在R18-STEP-RESULT：5854624为down status1 native_result0/clock1 wait_return_ns61539630000；5868104为up status0 native_result0/wait_return_ns61655156992；5866985为发送者FX3_KEY95_STEP_DONE，one_down_one_up1、measured_down_up_ns106938000、wait_result0。保留原serial记录顺序，发送者done与接收者up不强行排序。6685254为frame269 commit clock1 ns67554490992。down→该commit6.014861s是guest clock1域，不能当host工具/人工延迟。

## 原20秒停止与晚到确认

所有UTC为2026-11-04，host monotonic和page performance各自独立，不直接跨原点相减。

|边界|UTC|说明|
|---|---|---|
|真实Start HTTP202|22:31:47.689|一次真实按钮握手|
|arm|22:32:50.399|nonce84992935-64fd-401f-9740-cfa9adb39b89，原20s|
|MENU click入口/返回|22:32:50.406453 /50.416195|单次页面键click|
|MENU HTTP202记录|22:32:50.415|接受1键|
|capture等待入口|22:32:50.470110|同工具内|
|截图入口/返回|22:32:57.200151 /57.251017|一次新合格图|
|capture后验/工具返回准备边界|22:32:57.259984 /57.267898|不是模型收到图像的时刻|
|原alarm自动End|22:33:10.401|elapsed20002.6ms，end_click一次|
|Stop HTTP202|22:33:10.427|原End handler正常提交|
|finalACK HTTP200|22:33:13.425|退出结果已显示并确认送达|
|下一操作工具包装器入口|22:34:33.032718|并非在原due内|
|原explicit CLI入口/返回|22:34:33.074093 /33.087700|refused，0按钮click/0HTTP|
|迟到确认拒绝后核终态|22:35:03.072|End_disabled/ending/finishedtrue，不第二次click|

nonce从未更换，armed_ms82939.5、due_ms102939.5始终相同；到期stateexpired/sealed，0cancel、0重arm。key HTTP→Stop HTTP20.012s；同host键click入口→End后QMPstop上界20.050333s，原30s停止合同本轮通过。timer为观测到的20s后备行为，不承诺系统挂起/浏览器阻塞时硬实时。

**实测空窗**：capture返回准备边界→下一确认包装器入口95.764667s；→原explicit CLI入口95.806046s（各自同host monotonic）。capture函数6796.537ms、页内参考等待6720.600ms；工具返回元数据报告exec执行墙时6.836469s、整体工具约7.0s。没有图像递送ACK、编排队列时间、上下文处理时间或模型接图/语义审完时钟，故是否存在编排/上下文负担以及各段占比均unknown；**不把95.8s称为实测模型思考时间或固件耗时**。R18-TOOL-BOUNDARY-NOTES只保留已知工具元数据与缺测项，不研究或猜测平台内部原因。

下一操作调用确实尝试原explicit CLI一次，使用已审shownSHA和目标文字；回执refused/alarm_identity_or_due、click_invokedfalse、expectednull。它不是“没有CLI文件/没有调用”，也不是成功确认：实际confirm HTTP0。CLI没有改期限、自动重发或取消；原End已完成，故拒绝后只核finished而不补点disabled按钮。没有后续键。

## r18新增拒绝导出：运行验证passed，零记录

receipt.web_key_rejections_export.complete=true，原web-key-rejections.json实际304字节，独立SHA256 **7d5ad65f30a77e1a4cbe2a22baf5217b6e257e3781a9d415cfd56a5cd5024df3**与receipt完全匹配。schema fx3-host-key-rejection-v1、capacity64、total0/stored0/truncated0、records=[]，边界after_qemu_cleanup_before_browser_final_ack。R18-EXPORT-CLEANUP-VERIFY保存原字节核验；零拒绝仍有完整非空JSON导出，不是缺文件。

本轮没有server submit拒绝，因而没有同锁failed_predicates/observed/current身份样本可展示，不能模拟补填。晚到explicit工具的本地precondition拒绝不属于TrialState.submit记录；文件零记录与这一事实一致。不能由export时间推算server publish时刻。本轮未触发409，R18-409现场脚本未执行，也不宣称持续拒绝提示/按钮恢复分支已实测。

## 原收尾与raw验证

health/protocol/render/diagnostic/lifecycle均true，host error/early_stop null；原API16 20s恢复合同在1.562323s完成，原16字节000b00b4fd7bbba9fd030091f35301a9实读，SHA1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75；F100FILE/control0x100c1ea9/status0/seen1，host未写原代码。QMP quit335同ID ACK/SHUTDOWN、exit0/reaped，PID14490/14768独立ps不存在，两个锁free；finalACK200，专属browser关闭/端口无监听。native_shutdown_after_ready及native_model_power_off_after_ready均false，不声称观测到原生PowerOff。

原暂停16MiB环SHA a788347e0777d4f44cbbcb2859ce3e7a6c2176ce4f9a10ef8ed73a09fbe2b226，停止后原parser独立重解析等于自然JSON；4107事件、0丢失/0坏槽。End UI bank64KiB SHA42a46902499d350333857c67f9988d3688c4b1fbf17162f75753e32b8a93a4d9，真实active bank按0x100+bank*0x1000解98Q，publication_serial308。尾段的非事务镜像不用于唯一根因推断。

v5尾段valid_nontransactional_tail_checkpoint且snapshot_is_end_statefalse；两份976B完全相同、SHAba2bff80beb6521065c91ab8718e7589ec9aa798466bc949ce3e748265f753ad。独立48I ACK/784B98Q/FNV58e4e643通过，host tag0x1be6f9c160e222a9、nonce0x3edd37a88ffe1eaf、PID237/root0x7ed84bfd60、probe9/TID241；selftest/bound1、object_mismatch/root_change0。实际cont/running/stop/paused匹配，attempted/acknowledgedtrue，无旧qmp_cont_sent。capture27.695ms、total30.240ms，guest clock1复制50000ns；尾段不算End瞬间或启动性能。无step2前快照、无UP区间结论。

限定存储预检15分钟与本轮窗口exit0无匹配/无timeout，不是存储可靠性证明。35源/14输入/67交付、原平台及所有本轮操作源前后不变。R18-verify.py、R18-final-check.py、STEP-RESULT、EXPORT-CLEANUP-VERIFY保存独立核验；R18-final-check对齐1次CLI尝试与0次实际confirm。八步失败不以这些诊断/cleanup passed替代。

## 最小后续交接（本任务不执行）

需要新的明确单轮授权后，沿用r18上述原runner和本任务8min/32静态上限/实际8键参数；已部署入口和平台无需修改。三helper统一在r18/operator-helpers，原PAGE指纹d224…9822，使用本run的OPERATOR.py、capture_validation.py、capture_review.js/capture_after.js为参考；后续操作源码只能进将来的新run，提前设定新URL/session/launch_id/每步新nonce并在Start前冻结，**不得在本已完成run重跑**。

逐步最小流程：

1. 一个工具内运行python3 -B <新run>/OPERATOR.py capture <实际step>；检查exit0、JSON qualified、validated_new_screenshot=true、路径为本步新独占capture/menu-reference-page.png且文件/hash匹配，然后同工具直接view_image并返回图。第1步用r18 bounded_r3；2–8用实际step只读review捕图。原due/8s保留不变。
2. 操作者亲看完整语义后，**下一工具**只运行python3 -B <新run>/OPERATOR.py confirm <step> --target '<实际亲见目标>'一次；原CLI精确历史ACK和当前ready后同nonce cancel，必须confirmed_and_cancelled且elapsed<20000才续键。不因任意像素变化自动批准。
3. 拒绝/未知/不合格即原End；明确409才按本任务END409.py样例一次只读snapshot+截图后同工具End，不等待刷新、重试或cancel。成功第8步确认即End。

可复用证据：interaction-operator-rehearsal-r2已实际完成单次人工工具链11.4525s；r18/evidence/rejection-delivery-test、run-1793830854968及helper-run-538ce8a4是已验收13/11/8离线结果，r3原fixture轨迹和本轮实际跨ACK到完整图也保留。它们不消除本轮95.8s未分解空窗，不构成再次运行的自动许可。本任务不重跑fixture或VM、不为迁就延迟改20s或自动确认；后续是否更换操作方式或采编排时钟由协调端另行安排。
