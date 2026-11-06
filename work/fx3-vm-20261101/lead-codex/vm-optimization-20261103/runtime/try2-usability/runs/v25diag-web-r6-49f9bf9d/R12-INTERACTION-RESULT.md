# r12 原 FX3 单轮交互验收：第2键目标未达，整体 failed

本轮唯一运行只完成 **2 个接受的固件键**。第1键 MENU 后亲看完整 Setup > Area/Date 菜单并确认；第2键 UP 有202和原生 down/up/STEP_DONE，但焦点仍停在 Area/Date/Time Setting，未出现预期 Language。没有把无变化画面确认为通过，没有补发已接受UP，已网页End并回收；C4、OK、取消/关闭/重开及关键第7→8门本轮均 **unknown/未执行**。整体8步验收 **failed**。

另有明确执行偏差：UP请求至End记录间隔 **43.821s**，超过30秒要求。第二张无变化图保存后还有 **22.338s** 才发起End，期间没有显式工具等待；判读、决策和操作发起延迟未被及时收住，不能全部归咎工具耗时。该项单独failed，不因健康/清理通过抵消。

## 运行身份与范围

- run=`v25diag-web-r6-49f9bf9d`；runner PID30266、QEMU PID30626；真实Chrome/agent-browser独立会话 `fx3r12-b83358633d9e`，URL `http://127.0.0.1:51239`。
- 唯一命令 `PYTHONDONTWRITEBYTECODE=1 python3 .../v25-r12-confirmation-progress/run_trial_v25_diag_r3.py --port 0 --max-minutes 10 --max-steps 32`。runner duration **159.803815167s**，未重启/开第二轮；实际2接受键、小于16，仍在8分钟总观察预算内，但局部30秒停止合同失败。
- Start `2026-11-04T18:17:49.891Z`、MENU请求 `18:19:17.384Z`、第1次宿主确认 `18:19:40.187Z`、UP请求 `18:19:40.898Z`、End `18:20:24.719Z`、finalACK `18:20:30.048Z`；均为浏览器记录的宿主wall时间。runner创建UTC `18:17:25.548248+00:00`，不与重置后的运行monotonic计时直接相减。
- SOURCE-FREEZE SHA256 `eca2c47accbae27f1a1d2ab1a8e78d6c8d33feade4b580c7b3b3149cf85827e2`；web `cfd4239effb34c8be3381eff9c1de3ebf0f6ca4d10af16c86c167e3d76ee82bb`；runner `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0`。
- 原A/r3 CPIO `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`，candidate `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`；QEMU/kernel/DTB/Backup、4核MTTCG/noicount保持，实际 [command.json](command.json) 和14项输入SHA可复核。
- 没有internal-hoststep、procdiag、自动Stop observer、脚本POST、自动confirm、keepalive、新guest、时限或省电修改；未进入/提交任何设置值、播放删除、格式化或重置，没有FX6、实机、相机/USB/SD操作。只写新run，未改旧failed材料、冻结源码、入口、README/ledger或部署候选。

## 分项结果

| 项目 | 结果 | 证据与边界 |
|---|---|---|
| 待机可见 | passed | [待机图](R12-standby-ready.png)已亲看，有原生待机图标 |
| MENU完整菜单 | passed | [第1键图](R12-01-MENU.png)为Setup > Area/Date 45/59完整菜单，Area/Date/Time Setting焦点 |
| 第1次宿主看图确认 | passed | HTTP200/confirmed=true；之后UP得到202；不是第7→8新frame场景验证 |
| UP送达原生输入队列 | passed | HTTP202、down/up receive返回0、send返回0、STEP_DONE |
| UP后Language焦点 | **failed** | 两次亲看仍Area/Date/Time Setting；runner no_change_observed，未确认此步骤 |
| C4帮助、MENU返回 | unknown/未执行 | 尚未到Language，未发送C4或后续MENU |
| OK语言列表、MENU取消不改English | unknown/未执行 | 未发送OK，不沿用r11通过项作为本轮通过 |
| MENU关闭、确认后新frame/ready、第8键重开 | unknown/未执行 | 第7→8必须缺口没有运行到 |
| 明确409提示/人工重看再点 | unknown/未触发 | 2个key请求均202，confirm仅1个200；409数0、使用机会0 |
| 30秒目标/停止合同 | **failed** | UP→End43.821s，具体动作时间见下表 |
| health/protocol/render/lifecycle/diagnostic | passed | 仅代表相应健康和读回合同，不能认证焦点或画面持续更新 |
| 恢复、退出回收、锁、finalACK、输入与限定存储 | passed | 原始文件与独立核验如下 |
| **总体8步交互验收** | **failed** | 第2键语义目标未达，后续目标缺失 |

## HTTP、原生接收、图像与确认

[真实浏览器HTTP回执](R12-web-http-evidence.json)：key尝试2个=202接受2个，confirm1个=200，Start/End各1个202，final-ack1个200；没有409、5xx或未知送达，不使用任何允许再按机会。临时认证header已移除；回读网络记录没有重发POST。

| 步 | 请求/ACK | 原生 down / up / done LF | 图像目标 | 宿主确认 |
|---:|---|---|---|---|
| 1 | MENU 0x1ab /202，next_step=1 | 51814 / 51873 / 51958 | 待机→完整Setup > Area/Date菜单，Area/Date/Time Setting焦点；[R12-01-MENU.png](R12-01-MENU.png) SHA `d28199f74e21a69890f3a6e01945fd454f4a8152548199f7837facadf26fbeba` | 200 |
| 2 | UP 0x3 /202，next_step=2 | 62819 / 63144 / 63151 | 预期Language；实际仍Area/Date/Time Setting焦点；[R12-02-UP-observe.png](R12-02-UP-observe.png) SHA `2c8fe87bd071ae4fb3a9d4455f8c11084db2d5e957e102d0f425da03d5190d38` | 未发送 |

[步骤JSON](R12-STEPS.json) 保存每次HTTP body/ACK、requestId、原生原始行和LF/字节偏移、目标图完整SHA、浏览器shownSHA、runner抓帧SHA与宿主同钟延迟。原串口 [serial.log](serial.log) **6,896,378 B**，SHA256 `1668510a6fc3fe00b921434ec0a7128611c71bfd5f2af926abb86ecced93c71f`，未截断。每步有一次status1和0的原生receive、各一次send return0与one_down_one_up=1；保留原行 `downstream_processing_unproven=1`，不把接收完成当作下游UI处理完成。

第1次确认nonce=`58f96421-3a3c-491d-95d4-a2b84e2be984`，step1、observed_sequence65、generation21、PNG SHA `60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`、guest_input_written=false。第2键请求也引用sequence65，之后runner before/observed_sequence都为65、SHA相同；[第2步页面状态](R12-02-state.json) reviewAwaiting=false、reviewUnknown=false、deliveryUnknown=false、review_required=true/step2。这里是语义目标未出现，没有复现r11第7次确认后锁住的路径，也没有验证r12跨新frame恢复门。

[105笔UP后到End前状态](R12-UP-status-evidence.json) 当前frame均65、generation均21；[首次UP图](R12-02-UP.png)、[后续观察图](R12-02-UP-observe.png)和[最终图](R12-final.png)都可见原焦点。它们证明这些观察没有得到Language目标，不证明任意原绘制调用绝对没发生，也不单独定位生产者/消费者根因。第1键runner最早自动抓到的变化帧仍可能是待机闪烁，所以完整菜单通过仅凭实际菜单图和确认，不凭visual_changed。

## 停止动作与可得时间：未满足30秒

[完整时间线](R12-STOP-TIMELINE.json) 记录如下；文件mtime是采集完成时间，不是精确的人眼识别时刻，HTTP时间是浏览器记录wall时间。与guest CLOCK_MONOTONIC或runner host_monotonic不交叉相减。

| 顺序 | UTC / 可得时间 | 动作与观测 |
|---:|---|---|
| 1 | 18:19:40.187 | 实际点击第1步宿主确认，HTTP200 |
| 2 | 18:19:40.898 | UP请求HTTP202；之后没有其他固件键点击 |
| 3 | 未单独记绝对时刻；已知配置3000ms | 短条件等待review2/错误，返回Wait timed out after3000ms；随后snapshot为处理中/按钮disabled |
| 4 | 18:19:53.082；UP后12.184s | 第1张UP图保存；页面已报原生接收、no_change_observed；焦点未变 |
| 5 | 18:19:53.227 | 保存对应页面状态；没有确认第2步 |
| 6 | 18:20:02.381；UP后21.483s | 第2张观察图保存并亲看，焦点仍未变；此轮没有显式sleep/长wait |
| 7 | 18:20:24.719；UP后43.821s | 下一条实际UI操作才是scroll End + click End，成功返回Done；没有补发UP或其他键 |
| 8 | 18:20:56.094起 | End后才保存停止状态、HTTP补证、最终页面和收尾数据 |

第一张到第二张图间9.299s；第二张到End仍22.338s，后段没有显式工具等待。这段包含assistant判读/决策及工具发起周转，是本次超时的重要执行偏差，应该更早发End。现有工具仅提供各次调用阻塞/yield时间和3秒配置等待，缺完整进程生命周期剖析，不能把43.821s都称为工具执行耗时。未为时间边界再测试、补跑或放宽要求。

## 恢复和诊断

- [receipt.json](receipt.json)：health/protocol/render/lifecycle/diagnostic_readback=true，host_observer_error=null；native_shutdown_after_ready=false、native_model_power_off_after_ready=false、serial_health_failure=null，字面`-1018`计数0。menu_verified=false、browser_visual_acceptance=null原样保留；Language列表未进入，不能据此排除历史Language错误。
- QMP stop ACK、query-status paused/running=false后完整读 [osd-ring-final.bin](osd-ring-final.bin) **16,777,216 B**，SHA256 `c58cedd911c57226a7fa922939b5329185ef89fcad33f3141d5657a55277463c`；readback_complete/parse_valid=true，dropped_busy_writer_events=0、invalid_or_torn_slots=[]。诊断内容有效不等于语义目标通过。
- 再证暂停后独立读取 [ui-gate-counters.bin](ui-gate-counters.bin) **65,536 B**，SHA256 `71d5318d2444f491090e736a95463f0d83ed04ee93e83658382f9f377542635d`，optional已声明区complete、errors=[]。按真实双bank布局读header后，从 **0x100 + active_bank×0x1000** 选当前bank；本轮version2、activebank0、publication28282，计数起点0x100，绝非紧跟8Q header的字段。
- 当前bank count4..11=`[3918,3918,3852,66,65,4674,3887,3918]`，gate_hist=`[0,0,66,837,1651,1364]`，peak_gate786、backlog_skip3852、time_skip1、time_pass65、timer_dequeue3887、a12/a13_nonzero0、last_a18=786。它们是全程终态逐字段原子镜像，不是UP瞬间、前端状态或跨字段一致事务；不在本运行报告中推定根因，另由协调端安排离线分析。
- [restore103-receipt.json](restore103-receipt.json)：原20秒合同内 **3.706736s** 完成guest ACK+原API16回读。最后 [raw](restore103-013-api16.bin) 为 `000b00b4fd7bbba9fd030091f35301a9`，SHA256 `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`；[header](restore103-013-header.bin) SHA256 `fc5563e2787ea0ddd29fc3986d24c7d335c5fa23ebceb1ee000b0e060fb82dc9`。独立解包F100FILE、shutdown_control0x100c1ea9、restore_status0、restore_seen1；native_unbind_return0，host未写原代码。
- [qmp.json](qmp.json) quit **id489**、SHUTDOWN reason=host-qmp-quit、同id空对象ACK；QEMU exit0、wait/reap=true、PID_absent=true。[guard回执](resource-guard-receipt.json)与独立 `ps -p 30266,30626` exit1/空输出一致；双锁非阻塞exclusive probe均free，没有强行解锁。
- [网页final receipt](trial-web-final-receipt.json) acknowledged=true/end_reason=browser_ack，真实final-ack HTTP200；[最终图](R12-final.png)与[文本](R12-final-browser.txt)保留健康终态和未变焦点。独立浏览器会话已关闭。

## 卷、输入、限定存储和来源

- [启动前核验](R12-PREFLIGHT.json)：卷UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、无既有QEMU/runner、双锁free，22个r12源和14项固定输入逐SHA通过；运行前固定输入pins由runner再核。[结束后独立核验](R12-VERIFICATION.json) 重新计算14输入和22源，均匹配，含完整路径/SHA、API16/header、QMP、UIbank/ring、PID/锁，没有重跑历史tests。
- [启动前存储](R12-PRE-RUN-STORAGE.json) 2026-11-04 **10:02:15–10:17:15 PST**；[本轮窗口](R12-RUN-STORAGE.json) **10:17:20–10:22:01 PST** 覆盖创建/Start、输入、End和清理。同r10A限定kernel USB/APFS predicate，timeout25s，两次exit0、无timeout、无匹配事件，stdout/stderr/argv/SHA保留。这不是外盘全面可靠性证明。
- 预期操作依据沿用本会话 **2026-11-04** 已读取的Sony **ILME-FX3 Ver.2 or later** 官方说明：[Using the menu](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867589.html) 的方向/中心键/MENU取消退出、[In-Camera Guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867604.html) 的条目Delete说明、[Using the Delete button](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000844148.html) 的播放删除与菜单帮助区别；官方预期不替代VM实测。

[哈希清单](R12-INTERACTION-SHA256SUMS) 封存报告、步骤/HTTP/105状态/时间线、全部图和关键原始串口/QMP/恢复/诊断；[哈希回执](R12-HASH-CHECK.txt)逐项记录。没有创建或写入另派的离线分析目录，未改旧run或任何冻结文件。

未完成：Language焦点、C4帮助、OK列表、MENU返回/取消/关闭/重开及r12第7→8新帧恢复门；409/confirm409人工重看分支本轮未触发。一次159.8秒的失败运行不等于60分钟/4096次稳定性或FX6开机，worker_done按failed提交。
