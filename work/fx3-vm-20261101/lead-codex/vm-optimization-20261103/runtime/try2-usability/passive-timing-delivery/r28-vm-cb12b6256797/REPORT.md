# FX3 r28 唯一真实轮：failed

2026-11-04 PT（原始日志2026-11-05 UTC）；task_cb12b6256797 / ctx_ed4b21dcca7f。正式spec SHA：15e86694c88aa6d32d4c45d3ec3e829b9ab8c14d42fe83131c2db08b2f2b03c5.

**1 VM / 1 Start；0 attempt / 0 accepted / 0 postkey观察 / 0 pin / 0 confirm / 0恢复**。未在原180秒内取得合格待机，启动wrapper按上限End，八步未进入，本轮 **failed**；正常资源回收 **passed**。没有第二次Start或补键。End后可见较晚图标画面，不能追补合格待机或菜单成功。

[RESULT](RESULT.json) · [启动/End精确边界](STARTUP-TIMELINE.json) · [未执行步骤记录](STEP-EVIDENCE.json) · [预绑定/工具通路](OPERATOR-TOOL-CALL-EVIDENCE.json) · [SHA清单](SHA256SUMS)

| 本轮边界 | 证据 |
|---|---|
| 唯一Start POST | 03:48:00.772922880Z |
| 原首帧期限 | Start前宿主单调时钟434166.237438625 + 180秒 |
| 最后首帧poll | 03:51:00.041559Z起；phase=starting、ready=false、loaded=false、error=null、finished=false |
| 超时失败 | 03:51:01.057599Z，约180.322秒；first frame not ready by 180 seconds |
| 原End调用 | 03:51:01.104287Z—03:51:01.124407Z；End_invoked=true |
| 唯一stop POST | 03:51:01.115731968Z |
| HAR首个带frame状态 | 03:51:01.602696960Z请求起点；phase=stopping、ready=false、seq1/gen1/SHA e0140e… |
| 该帧宿主观测 | 434346.781459375；晚于End工具入口约0.175330秒 |
| final ACK | 03:51:04.037437952Z请求起点，200 acknowledged |

HAR没有ready=true状态；没有FIRST-FRAME-PASS或initial-standby合格截图。运行约 **182.921秒**（总预算480秒）。180.322秒是保留原1秒poll节奏后的失败观察点，不是放宽180秒资格期限；End在失败后调用。HAR时刻为HTTP请求起点，宿主frame观测也不是精确compositor/模型收图时刻，不能据此还原所有未观测到的guest瞬变或判定首帧根因。

已实际查看[End后整页PNG](ended-page.png)：显示HD Fixed-59.94fps、F、AF-C、±0.0、AWB等较晚图标，页面明确finished、0键、健康检查未通过；只作为结束图像证据。原生[final PNG](../../runs/v25gate-n64-r17-f7903939/trial-final.png)及原始raw保留，未用作本轮待机/步骤许可。首帧健康未通过的直接证据为standby_ready=false、render_pass=false、health_pass=false；protocol_pass/lifecycle_pass=true、host_observer_error=null、serial_health_failure=null，未将其泛化为已确定固件或宿主根因。

Start前已用真实Node将本r28 short_tool.mjs.bind(本task规范绝对路径)存globalThis.fx3R28One，下一独立工具确认typeof为function，再实际展示明确historical_sample_only=true/current_standby=false的已有PNG，见[PRESTART-NODE-DISPLAY](PRESTART-NODE-DISPLAY.json)。持久shell和正确FX3_NAV_RUN_DIR用于既定runner。因未到合格待机，未调用standby_review或任何生产单动作函数，tool-return-UUID目录为0；实际arm+5秒首次postkey取图、固定图重看/confirm、恢复链全部未验。原20秒alarm已安装但从未armed，清理分类valid_null_never_armed；没有输入attempt/nonce/snapshot/confirm身份可填，不虚构。

正常清理全部通过：API16原字节 **000b00b4fd7bbba9fd030091f35301a9**，guest restore_seen=1，**1.554124秒 / 原20秒预算**；原始header/API16各次读取及最终16字节留存。QMP quit id470返回{}，QEMU exit0/reaped；runner89775、QEMU89913、自有browser daemon89799均absent，双锁独立探测free，55776端口closed且lsof无监听，网页finalACK确认，自有浏览器close成功且session inactive。证据：[CLEANUP](CLEANUP.json)、[独立探测](INDEPENDENT-CLEANUP.json)、STARTUP-FAILURE-CLEANUP及原生run下restore103-receipt、qmp、resource-guard、receipt、trial-web-final-receipt。

全部456条HTTP请求保存在[traffic.har](traffic.har)，[POST原body](HTTP-POST-ORIGINAL-BODIES.json)为Start1、stop1、final-ack1；key/review-snapshot/confirm均0。拒绝导出保留原字节，total=0、truncated=0，304字节、SHA e72f29ede51fcc60be211dc6c53432ad328f21d3bd115ef9c913b97806652a24。serial.log完整保留；[native原行导出](NATIVE-KEY-ORIGINAL-LINES.bin)故意为0字节，[零条记录与serial绑定](NATIVE-KEY-ORIGINAL-OFFSETS.json)说明本轮没有down/up/done，不把空导出当缺件。原ledger仍attempts=[]/recoveries=[]。

冻结前后相同：r28交付562项、生产源38项、core33项，45项既有历史输入；实际preflight覆盖r25清单594项、r24清单151项、r21清单145项及清单自身pin、source40、fixed14、实际QEMU。五个实际模块路径/哈希前后相同，候选→冻结r21→旧兼容目录优先级保持；PAGE canonical 852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b。固定4×cortex-a35 / 5120MiB / MTTCG / noicount，kernel da4a66fa… / DTB 5aa2beac… / N64 CPIO aaf00661… / 实际QEMU bf4d4648…不变，完整hash见INPUTS-BEFORE/AFTER、SEALED-DELIVERY-BEFORE/AFTER、ACTUAL-IMPORT-BEFORE/AFTER。

runner[command记录](../../runs/v25gate-n64-r17-f7903939/command.json)及trial-session QEMU PID保留实际启动argv/平台路径，ACTUAL-ARGV-PREPARED逐项核参数与QEMU哈希；独立live ps argv采集未到达（原start_and_wait只在合格待机后采集），故该额外采样为unknown，不伪造。未写旧runtime自然输出、未改源码/平台/输入门/期限/部署入口/协调ledger；部署仍r10，r26b及全部历史失败保留。未重跑离线矩阵。

scripted_navigation=true、visual_review_at_click=false。模型实际收图/思考/调度无法分离，仍unknown。v5 tail非事务checkpoint，snapshot_is_end_state=false、post_snapshot_event_counts=unknown。本轮合格待机及完整八步、真实arm+5秒观察/精确pin/confirm/恢复均未验收，不泛化60分钟/4096键/所有菜单/录像/实机/FX6；本dispatch无剩余VM/Start权限。

原生run：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-f7903939。任务入口：[README](README.md)。
