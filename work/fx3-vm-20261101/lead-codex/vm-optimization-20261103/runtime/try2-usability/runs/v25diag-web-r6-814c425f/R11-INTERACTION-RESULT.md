# r11 原 FX3 交互单轮：C4/OK/返回关闭通过，重开未验，总体未通过

本轮真实网页完成 **7 个接受的固件键**：MENU 开菜单、UP 到 Language、C4 可读帮助、MENU 返回、OK 打开语言列表、MENU 取消、MENU 关闭到待机，均亲看语义目标并点宿主看图确认。**第 7 次确认 HTTP200 后前端未恢复输入**，计划第 8 键 MENU 被 disabled 本地保护拦住，未产生 HTTP 或 guest 键，因此 **MENU 重开 unknown、总体 outcome=failed**。未补发、未重开 VM、未改设置或部署候选。

本轮 health/protocol/render/lifecycle/diagnostic 门和完整恢复回收均 passed。没有 key409，所以 r11“明确拒绝持续可见”与人工重看后再按的运行分支 **未触发/unknown**，使用机会0次；不能把离线验证或前7步通过写成完整交互链通过。上一轮 b6209581 的 failed 结论与材料原样保留。

## 身份和约束

- run=`v25diag-web-r6-814c425f`，runner PID12999、QEMU PID13102，真实 Chrome/agent-browser 独立会话 `fx3r11-b83358633d9e`，URL `http://127.0.0.1:60921`。
- 唯一命令：`PYTHONDONTWRITEBYTECODE=1 python3 .../v25-r11-visible-rejection/run_trial_v25_diag_r3.py --max-minutes 10 --max-steps 32 --port 0`。runner duration **312.497260791 秒**，在8分钟观察预算内主动 End；实际7接受键，小于16。无 internal-hoststep、procdiag、自动Stop observer、重启或第二实例。
- SOURCE-FREEZE SHA256 `8be8343b234d5d579e75fcf86b002ed675376d0de896cb6925fbf6af64454985`，web SHA256 `1425d8f7c29724909fe9a8f29d3e591d73655ae313bf0d8695641fe1de0575eb`，runner仍 `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0`。
- 原A/r3 CPIO `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`，candidate `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`；原 kernel/DTB/Backup、4核MTTCG/noicount、5000ms和API16 20s规则保持，[command.json](command.json) 保存实际命令。
- 未选择其他语言，OK只用于从条目打开列表；English单选焦点保持，MENU取消后条目仍显示English。没有进入播放删除/格式化/重置，不提交设置值、改省电、keepalive、调整时限或输入门；无 FX6、实机、相机/USB/SD操作，没有改冻结22源码、原guest/平台、r10入口、r11启动器、README或ledger。

## 分项结果

| 项目 | 结果 | 依据/限制 |
|---|---|---|
| 待机→MENU开Setup > Area/Date | passed | 第1键接受；完整菜单目标另存图，未把早期NO CARD帧变化算作菜单 |
| UP到Language | passed | 第2键后Language橙色焦点，English |
| C4 Language帮助 | passed | 第3键可读Language说明，未进入播放删除 |
| MENU从帮助返回 | passed | 第4键回Language条目，English |
| OK Language选项列表 | passed | 第5键显示多语言列表，English选中；无其他值选择 |
| MENU取消列表 | passed | 第6键回Language，仍English |
| MENU关闭到待机 | passed | 第7键后实际待机图标可见 |
| 第7次服务器看图确认 | passed | HTTP200、confirmed=true、guest_input_written=false |
| 第7次确认后的前端输入放行 | **failed** | reviewAwaiting持续true；无第8个key HTTP |
| MENU重开原菜单 | **unknown** | 本地disabled拦截，未送达guest，不能判定原生重开功能失败或通过 |
| r11明确409持续可见/允许人工再按 | unknown/本轮未触发 | key请求全202；409数0；再按机会使用0 |
| 目标观察/失败停止时限 | passed（本轮观测） | 各目标首个保存图距请求<16s；未解锁后先End，从第7次确认请求起算17.719s到End |
| health及恢复回收 | passed | 原字+ACK、QMP quit ACK、exit0/reap、PID、锁、finalACK核验 |
| 输入/22冻结源完整性及限定存储查询 | passed | 启动前和结束后核验；存储仅限定predicate/window意义 |
| **总体指定交互链** | **failed** | 重开缺口及宿主前端未解锁未解决 |

## 每步真实网页和原生接收证据

共 **7 个 `/api/key` HTTP尝试=7个202接受键**；7个 `/api/confirm-visual` 均200；Start/End各1个202，final-ack1个200。没有409、5xx、超时或无效key回执，没有自动/手动重发。所有操作来自真实页面按钮，[完整浏览器HTTP回执](R11-web-http-evidence.json) 是回读网络记录，去除了临时认证header，没有脚本POST。

每键原串口各有一次status1/0接收、各一次down/up send return0、STEP_DONE one_down_one_up=1。接收表示固件原生输入队列返回，不等于所有下游处理已完成；本报告另用逐图语义目标判定。如下原始行号均为未截断 [serial.log](serial.log) 的LF行号，完整原行和字节偏移见 [R11-STEPS.json](R11-STEPS.json)。

| 键序 | 键/码 | 原生 down / up / done LF | 亲看目标 | 网页图与SHA前12位 |
|---:|---|---|---|---|
| 1 | MENU / 0x1ab | 57634 / 58007 / 58015 | 待机→Setup > Area/Date，Area/Date/Time Setting焦点 | [R11-01-MENU-target.png](R11-01-MENU-target.png) `8701c7ef50e9` |
| 2 | UP / 0x3 | 151229 / 151367 / 151357 | Area/Date/Time Setting→Language，English | [R11-02-UP.png](R11-02-UP.png) `2253014524c9` |
| 3 | C4 / 0x1f8 | 164507 / 164593 / 164601 | Language帮助，Selects the display language. | [R11-03-C4.png](R11-03-C4.png) `ebc06ff07f33` |
| 4 | MENU / 0x1ab | 176912 / 176976 / 176983 | 帮助→Language条目，English | [R11-04-MENU-back.png](R11-04-MENU-back.png) `09b9260f46fd` |
| 5 | OK / 0x1ac | 192254 / 192379 / 192400 | Language选项列表，English保持选中 | [R11-05-OK.png](R11-05-OK.png) `256ca35b40f5` |
| 6 | MENU / 0x1ab | 212126 / 212188 / 212193 | 取消列表→Language条目，仍English | [R11-06-MENU-cancel.png](R11-06-MENU-cancel.png) `43f85c952303` |
| 7 | MENU / 0x1ab | 228951 / 229093 / 229101 | 关闭菜单→待机图标 | [R11-07-MENU-close.png](R11-07-MENU-close.png) `70c814819f72` |

其中C4帮助实际文字是 **“Selects the display language.”**；OK列表可见English、日语、法语、德语、意大利语、西班牙语，English保持选中。没有在列表内按方向键或再次按OK提交值。

[步骤JSON](R11-STEPS.json) 分别保留HTTP请求/202 ACK、原生原行、目标截图完整SHA、浏览器显示SHA、runner首个变化帧PNG、服务器确认200/nonce/generation，以及宿主同钟延迟。第1键runner先抓到待机/NO CARD变化帧，完整菜单目标在后续 `R11-01-MENU-target.png`；所以不把runner自动 `visual_changed` 或首帧当语义完成。目标首次保存图与请求记录的wall间隔为15.698/2.550/1.725/2.954/15.114/9.138/8.113秒，均已亲看；这些是宿主记录/文件采集间隔，不是精确原生语义渲染耗时。guest monotonic不与HTTP wall或host monotonic混减。

## 第7键后停止：可证关系与未知边界

- [关闭图](R11-07-MENU-close.png) 已亲看待机；然后实际点击宿主看图确认。服务器返回200、confirmed=true，step7，nonce=`d39b2219-e14c-4346-a346-8ddf2a8d9b27`，generation69，SHA `e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4`，guest_input_written=false。
- 接下来短等MENU可用3000ms超时；计划的MENU本地点击返回 **disabled，click would not reach it**，没有HTTP请求；再短观察没有step8。下一条动作先滚动并点击页面End，之后才保存补充HTTP/页面/串口证据。没有再次确认、补发已202键或尝试解锁。
- [原始43笔状态](R11-confirm7-status-evidence.json) 位于confirm7请求后、End前：均 phase=ready、steps=7、review_required=false、匹配同一confirmation nonce/generation69；当前frame generation已为70–98，没有一笔与69相同。[停止时页面状态](R11-stop-state.json) 显示reviewAwaiting=true、pendingConfirm仍为上述nonce，reviewUnknown=false、deliveryUnknown=false、renderFault=null。不是key409，也不是固件输入未接收。
- [冻结源码证据](R11-confirmation-source-evidence.json)：web的281–288行 `confirmationMatches` 在匹配确认身份之外，还要求**当前frame generation/SHA继续等于已确认generation/SHA**；376–378行只有该匹配成功才清除reviewAwaiting/pendingConfirm，277行reviewAwaiting会令键disabled。上述43笔状态均不满足generation相等，结合实际未放行状态，支持本轮停在宿主确认匹配门。函数本体与r10逐字一致，不能据本轮称它为r11新增回归。
- 可证的是本轮持续未匹配与门未清除；没有在确认接受瞬间的前端原子状态/调用栈，不能证明所有可能执行路径或把NO CARD闪烁归为唯一根因。没有修改匹配条件、重跑或部署修复。
- [停止时间证据](R11-STOP-EVIDENCE.json)：confirm7请求 `2026-11-04T17:59:05.709Z` → End请求 `17:59:23.428Z` 为 **17.719s**，即使从确认请求保守起算也小于30秒。第7键关闭目标在此之前已经看清，所以不能把第7键请求到End的总间隔误作目标未知等待。Start `17:54:13.426Z`、finalACK `17:59:26.129Z`；全部为浏览器记录的宿主wall时间。

## 健康、原字恢复与回收

- [receipt.json](receipt.json) health/protocol/render/lifecycle/diagnostic_readback均true；host_observer_error=null，native_shutdown_after_ready=false、native_model_power_off_after_ready=false。menu_verified=false及browser_visual_acceptance=null保持原值，独立逐图通过项不回写原始receipt。完整串口 **30,132,948 B**，SHA256 `61bd1ed6660ea88e9d99e93dfe57e2ba04393d9f2f3c52b33ce423c4d45804af`，字面`-1018`计数0、serial_health_failure=null；本轮语言列表成功不证明历史-1018根因已消除。
- QMP stop ACK、query-status paused/running=false后，完整读 [osd-ring-final.bin](osd-ring-final.bin) **16,777,216 B**，SHA256 `5924633f7e82b32c073048522ddceaa9ad890d20e342108302c85f33ff481451`；parse_valid/readback_complete=true、invalid_or_torn_slots=[]、dropped_busy_writer_events=0。
- 再证暂停后独立读 [ui-gate-counters.bin](ui-gate-counters.bin) **65,536 B**，SHA256 `d98638a0558a3b289e22c2d48b0560a3315b0f417f26b259afa4101ab478c96d`，optional已声明区complete、errors=[]。magic0x3145544147335846、version2、bank1、publication serial101533；count4..11=`[14009,14009,10087,3922,3506,13964,13959,14000]`，gate_hist=`[118,261,3543,8464,1258,365]`，peak283、backlog_skip10087、time_skip416、time_pass3506、timer_dequeue13959、a12/a13_nonzero0、last_a18=4。是全程结束态逐字段原子镜像，不是确认瞬间的前端状态或跨字段一致事务。
- [restore103-receipt.json](restore103-receipt.json)：API16原20秒合同内 **1.303467s** 完成guest ACK+原字回读。最后 [16B raw](restore103-005-api16.bin) 为`000b00b4fd7bbba9fd030091f35301a9`，SHA256 `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`；[header](restore103-005-header.bin) SHA256 `b518c3c6a7e3769b6f8208bf95738990bacca31f6e51b7a40b998379f01085e5`。独立解包F100FILE、shutdown_control0x100c1ea9、restore_status0、restore_seen1，native_unbind_return0；host未写原代码。
- [qmp.json](qmp.json) 末尾quit id1280、SHUTDOWN reason=host-qmp-quit、同id返回空对象ACK；QEMU exit0、wait/reap=true、PID_absent=true。[guard回执](resource-guard-receipt.json) 与独立 `ps -p 12999,13102` exit1/空输出一致；双锁非阻塞exclusive probe均free，没有强行解锁。
- [网页final receipt](trial-web-final-receipt.json) acknowledged=true/end_reason=browser_ack，真实页面final-ack HTTP200；[最终网页图](R11-final.png) 已亲看健康终态与待机，浏览器独立会话已关闭。

## 卷、输入和限定存储窗口

- [启动前回执](R11-PREFLIGHT.json)：KAFU2T UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，无既有QEMU/runner，双锁free；22个r11冻结源以及固定14项inputs均按SHA逐个通过。原A/r3 CPIO、kernel、DTB、Backup及QEMU命令由runner在启动前再次检验。
- [结束后独立核验](R11-VERIFICATION.json)：全部14项input_checks及22源重新计算SHA，仍匹配；含完整路径/哈希、API16/header、QMP、UIbank/ring、PID和锁。没有重跑历史测试。
- [启动前存储](R11-PRE-RUN-STORAGE.json)：2026-11-04 **09:38:33–09:53:33 PST**；[运行窗口](R11-RUN-STORAGE.json)：**09:53:46–10:01:58 PST** 覆盖创建/Start、按键、End和清理。同r10A精确kernel USB/APFS predicate、timeout25s，两次exit0、无timeout、无匹配；stdout/stderr/argv/SHA保留。这不等于外盘全面可靠性证明。

## 官方预期和交付边界

沿用本会话 **2026-11-04** 已读取的Sony **ILME-FX3 Ver.2 or later** 官方说明：[Using the menu](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867589.html) 给出中心键进入、MENU取消/退出；[In-Camera Guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867604.html) 给出选中菜单条目后Delete显示说明；[Using the Delete button](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000844148.html) 区分播放删除与菜单帮助用途。这些是预期操作依据，本报告仅以实际7步图像/HTTP/原生接收确认通过项，不外推全菜单、其他设置、实机或长时稳定性。

[哈希清单](R11-INTERACTION-SHA256SUMS) 封存报告、每步图/状态/HTTP、原串口/QMP/回执/关键诊断与恢复原始文件；[校验回执](R11-HASH-CHECK.txt) 记逐项结果。所有新写内容限定本run，旧failed记录与冻结候选未改。

仍缺：MENU重开的真实送达与目标画面、宿主确认后放行问题的后续处理、409提示/允许人工重看再按运行分支。没有为补齐再开VM、修改源码或部署；本任务worker_done按failed提交。
