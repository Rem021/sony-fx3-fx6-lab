# R13 step2预输入诊断：无首帧，关键采集未触发，任务 failed

本轮唯一运行 **216.788099秒、0固件键**，没有有效待机帧。按协调端“仍无首帧即提前End”的明确指示，下一条UI操作就点了真实页面End；未武装闹钟、未补按、未重跑。因此**没有step2前UI/OSD两份raw及postwrite最终门结果，无法做指定区间比较，诊断任务failed**。不是8步功能验收，也不能把缺采集当成Δ=0或“未复现UP故障所以通过”。

已保留完整全零OSD raw及独立有效结束UI bank。API16原字+guest ACK、QMPquit ACK/exit0/reap/PID消失、双锁与网页finalACK通过；health/protocol/render/diagnostic门失败，lifecycle通过。这些结果分别保留，不能互相替代。

## 身份与唯一运行

- run=`v25diag-web-r6-2b63f512`，runner PID50793、QEMU PID51103；专属单标签 `fx3-deadline-r13-2b63f512`、固定1280×1200，URL `http://127.0.0.1:57521/`。
- 唯一命令 `PYTHONDONTWRITEBYTECODE=1 python3 <DEL/v25-r13-preinput-observation>/run_trial_v25_diag_r3.py --port 0 --max-minutes 10 --max-steps 32 --pre-input-snapshot-step 2`，见 [操作者动作记录](R13-OPERATOR-ACTIONS.json)。实际QEMU参数在 [command.json](command.json)。无internal-hoststep/procdiag/新guest/keepalive、时限或恢复合同变化。
- SOURCE-FREEZE `3991aabecd1009c0c266f9290cd2c782623210f6b1c36cfb6c38d251bda209ce`；DELIVERY-FREEZE `e283e887eab32e43adee4a3e8e44f428fc9dab98515447fee398ef669aa2c8e8`。原A/r3 CPIO `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`、固定kernel/DTB/QEMU/Backup/4核MTTCG/noicount保持。
- 辅助SHA256SUMS `8d95b85bf5666ebd0bd898ec95c670e673fe5eb732852766dff3f82d8f53fbdc`及36项已核；真实页面脚本指纹和launch身份匹配后安装固定20,000ms版本。没有发固件键/看图确认/直接POST或设置值，也没有部署、修改候选/helper/旧run/入口/README/ledger，无实机或FX6操作。

## 分项判定

| 项目 | 结果 | 原始依据 |
|---|---|---|
| 真实页面Start | passed | 一次HTTP202，guest_spawned_by_http=false |
| 待机首帧前提 | **failed/未出现** | End前5笔状态均phase starting、ready=false、frame=null；所有键disabled |
| MENU/UP语义 | unknown/未执行 | 0个key HTTP、0个原生输入marker、0个confirm |
| step2前64KiB UI+256B OSD采集 | **failed/未触发** | 没有pre-input-step-*文件，也没有journal pre_input_snapshot记录 |
| postwrite_gate_passed完整结果 | unknown/未执行 | 无最终journal结果；不存在的磁盘receipt也不可能称通过 |
| 指定前后区间差分 | unknown/无法计算 | 没有前样本，结束OSD无效；全部Δ字段为null |
| 原结束独立UI读回 | passed | 65536B、有效magic/version/activebank，optional complete/errors=[] |
| 原结束OSD完整读回 | raw完整性passed；内容解析failed | 16MiB全零，parse_valid=false，不称有效ring |
| 固定20秒辅助行为 | 安装passed；武装/取消/到期未执行 | current=null、events只有installed，之后dispose封存 |
| 按键至End≤30秒 | not exercised | 没有按键请求，不伪报为passed |
| API16/quit/reap/PID/双锁/finalACK | passed | 下述raw/header与实际ACK及独立复核 |
| health/protocol/render/diagnostic | **failed** | 原receipt false；lifecycle_pass=true |
| 总体指定诊断 | **failed** | 缺关键前置采集，虽正确收尾也不具备任务成功条件 |

## HTTP、截止与停止时间

[真实浏览器HTTP回执](R13-web-http-evidence.json) 是回读实际网络记录，已移除临时认证header：Start1个202、End1个202、final-ack1个200；key/confirm各0。启动ID `2f890c37-36c9-40a0-9e0b-9d68924b3b67`。

- runner创建UTC `2026-11-04T18:59:20.383372+00:00`；页面Start请求 `19:00:03.868Z`，End `19:03:37.661Z`，finalACK `19:03:40.753Z`。Start→End记录间隔213.793秒，低于8分钟总观察上限；runner duration含其自身起点/收尾口径，不和创建wall时间混减。
- 收到协调端 `msg_e71b9d43c039` 时，当前快照仍无image、所有键不可用，故先点击End，之后才保存补证。[停止页文字](R13-stop-browser.txt)、[最终图](R13-final.png)/[文本](R13-final-browser.txt)保留没有首帧与失败终态，不把占位区域黑色称原生黑帧。
- [安装回执](R13-deadline-install.json)及[停止时辅助状态](R13-deadline-status.json) current=null，无armed/cancelled/end_click；未达到待机前提，故没有武装任何目标nonce或制造due回执。随后 [dispose](R13-deadline-dispose.json) sealed=true，专属浏览器关闭，[session回执](R13-browser-closed.json) inactive/pid=null。没有借关闭/重装规避活动alarm，因为根本没有活动alarm。
- 因0键，按键至End30秒合同与20秒超时触发均未运行；本轮不提供timer硬实时保证或生产20秒到期验收。

## 原始诊断与有限分析

[区间字段表](R13-INTERVAL.json) 保留两bank真实布局解析和缺采集状态。UI header是8Q，计数从 **0x100 + active_bank×0x1000** 读96Q，绝不从header后直接读。

- 结束 [ui-gate-counters.bin](ui-gate-counters.bin) **65536B**，SHA256 `e2b9ebb587c442904a2abb8c39f3ca27ceadcaea4d5d17ff112d68ee6bce1ce1`；magic0x3145544147335846、version2、activebank0、publication43470、pid237。active计数偏移0x100；id5..11=`[5767,5767,0,0,8831,5741,5768]`，gate_hist=`[0,0,0,0,5,5762]`，last_a18=3091、peak3378、backlog_skip5767、time_skip/time_pass=0/0、a12/a13_nonzero=0。
- 这些是**全轮结束态逐字段原子镜像**。全轮记录id7/id8为0是可报告字段，不是指定区间Δ，也不能绝对证明原更新/绘制调用从未发生或证明积压为唯一根因。没有step2前样本，不能应用“Δid5/9/10/11>0且Δid7/8=0”的区间判据。
- 结束QMP stop ACK、query-status paused/running=false后完整读 [osd-ring-final.bin](osd-ring-final.bin) **16777216B**，SHA256 `080acf35a507ac9849cfcba47dc2ad83e01b75663a516279c8b9d243b719643e`，逐字节全零。receipt paused_proven/readback_complete=true，但consistent=false、parse_valid=false、parse_error=`ValueError('not a v25-r3 diagnostic readback')`。不伪造事件数、提交seq或guest时间。
- [结束header派生文件](R13-osd-header-final-from-ring.bin) 只是上述raw的offset0/length256拷贝，也全零；不是另一次QMP读取，更不是step2前header。源文件与派生SHA在区间JSON中。原live header同样保留，不能当有效pre-input样本。
- 原ring解析失败后，r13继承的独立optional路径仍再次证明paused，并在10秒预算内完成所有已声明区，errors=[]，含有效UI bank；这证明本轮该宿主失败分支的独立读取实际完成。
- [serial.log](serial.log) **6143494B**；原生key receive/send/STEP_DONE各0、UI_WIRE63、OSD102_COMMIT marker0、字面-1018为0。缺marker只说明留存观察，不能证明任意原调用绝对未发生；无UP可与最后commit同钟配对，不能从此轮解释r12第二键因果。

没有预输入采集，故也没有该选定2秒读回所增加的输入暂停扰动可评估；正常End暂停读回不是“无扰动前样本”。所有id5..11/gate_hist/last_a18/OSD seq差分在JSON中为null，未混合UI clock7、guest clock1和host monotonic。

## 恢复、QMP与完整性

- [restore103-receipt.json](restore103-receipt.json)：原20秒合同内 **1.544479s** 成功guest ACK+原字回读。最后 [API16 raw](restore103-006-api16.bin) 为 `000b00b4fd7bbba9fd030091f35301a9`，SHA256 `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`；[header](restore103-006-header.bin) SHA256 `fc5563e2787ea0ddd29fc3986d24c7d335c5fa23ebceb1ee000b0e060fb82dc9`。独立解包F100FILE、shutdown_control0x100c1ea9、restore_status0、restore_seen1；native_unbind_return0，host未写原代码或延长期限。
- [qmp.json](qmp.json) quit **id553**、SHUTDOWN reason=host-qmp-quit、同id空对象ACK；QEMU exit0、wait/reap=true、PID_absent=true；独立 `ps -p 50793,51103` exit1/空输出。两把运行锁非阻塞exclusive probe均free，没有强行解锁。原 [guard receipt](resource-guard-receipt.json)保留。
- [final receipt](trial-web-final-receipt.json) acknowledged=true/end_reason=browser_ack。health_pass/protocol_pass/render_pass/diagnostic_readback_pass=false、lifecycle_pass=true原值保留；host_observer_error=null，native_shutdown_after_ready/native_model_power_off_after_ready=false（本轮并未达到ready，不能据这些字段泛化未观察事件）。
- [启动前核验](R13-PREFLIGHT.json)：卷UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、无既有runner/QEMU、双锁空闲，23源/7交付/辅助36哈希/固定14输入均通过。[结束独立核验](R13-VERIFICATION.json)再次核14输入/23源及冻结pin不变，保存原字、QMP、PID/锁和所有分项；没有重复历史tests。
- [启动前存储](R13-PRE-RUN-STORAGE.json) **10:43:21–10:58:21 PST**；[运行窗口](R13-RUN-STORAGE.json) **10:59:15–11:05:59 PST**（2026-11-04）覆盖创建/Start、End和清理。同旧限定kernel USB/APFS predicate、timeout25s，均exit0/no timeout/no matching event；原argv/stdout/stderr/SHA保留。仅排除该谓词窗口记录，不证明外盘全面可靠。

[哈希清单](R13-SHA256SUMS) / [校验回执](R13-HASH-CHECK.txt)封存本新run证据。没有改r13候选、helper或旧材料；本轮无首帧属于未进入指定两键诊断条件，不能声称诊断已采齐、UP语义已验证、根因已定位或单次通过长期使用验收。worker_done按failed。
