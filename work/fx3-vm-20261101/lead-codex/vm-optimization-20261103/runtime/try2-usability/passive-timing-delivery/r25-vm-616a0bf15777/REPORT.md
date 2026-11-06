# FX3 r25 唯一轮真实菜单验收：failed

2026-11-04（PT；原始日志为 2026-11-05 UTC）。Task: task_616a0bf15777；Dispatch: ctx_dad8bd29ff95。

已执行唯一 **1 VM / 1 Start**，**8 accepted / 8显式attempt / 7独立confirm / 0恢复**。第1—7步固定图实际看图后逐项通过；第8步选定的固定快照仍为待机，语义失败后立即原End，未补键、未重建快照、未再Start。八步整体 **failed**，正常退出和资源回收 **passed**。未修改候选/冻结源码、部署入口或协调ledger，r10部署保持原状。

[机器结果](RESULT.json) · [逐步完整身份与判断](STEP-EVIDENCE.json) · [第8步时序](STEP8-TIMELINE.json) · [所有产物SHA](SHA256SUMS)

首个合格待机截图从Start前宿主单调时钟起 **44.032秒**（上限180秒）；runner运行 **164.075秒**（预算480秒）。
scripted_navigation=true；visual_review_at_click=false：历史固定图用于独立语义审阅，下一次click仍走原实时门。操作代理实际收图/完成审阅时刻不能测得，均为unknown；宿主工具边界另存，不冒充模型时刻或实时人工视觉。

| 步骤 | 实际看图判断 | gen / seq | 语义 | 后续独立动作 |
|---|---|---|---|---|
| 1 | MENU：完整Setup > Area/Date，橙色Area/Date/Time Setting | 52 / 342 | 通过 | 独立confirm；8.640秒 |
| 2 | UP：橙色Language，English | 53 / 484 | 通过 | 独立confirm；7.493秒 |
| 3 | C4：Language帮助说明 | 54 / 626 | 通过 | 独立confirm；4.802秒 |
| 4 | MENU：返回橙色Language English | 55 / 820 | 通过 | 独立confirm；6.076秒 |
| 5 | OK：English语言列表，未改值 | 56 / 1004 | 通过 | 独立confirm；7.446秒 |
| 6 | MENU：取消列表，English保留 | 57 / 1160 | 通过 | 独立confirm；6.458秒 |
| 7 | MENU：关闭菜单到待机 | 58 / 1341 | 通过 | 独立confirm；7.921秒 |
| 8 | MENU：固定图仍待机；预期完整菜单未满足 | 76 / 1484 | 失败 | 立即End；未confirm |

初始待机完整视口为 [initial-standby/current.png](initial-standby/current.png)，已亲看HD Fixed-59.94fps、NO CARD、F、AF-C、±0.0、AWB等图标后，另调standby_review。8张完整固定PNG分别在step-01-attempt-01至step-08-attempt-08/capture/review-snapshot.png；每步JSON保留snapshot_id、run/launch/document/step/attempt/nonce、完整PNG SHA/gen/seq、native接收观察下界、确认请求身份与历史回执。截图身份校验只验证绑定，语义结论来自操作代理实际看图。

第8步的失败边界：

| 时序证据 | UTC / 单调时钟 | 观察 |
|---|---|---|
| native down接收 | guest clock1 156166841008ns | native_result=0；downstream_processing_unproven=1 |
| native up接收 | guest clock1 156297670000ns | native_result=0；仅证明接收 |
| 宿主观察native ACK | host monotonic 428214.025169541 | 下界seq1481；不证明下游处理完成 |
| 首见固定图对应帧 | 02:08:48.759322880Z | gen76 / seq1484 / 291427…待机 |
| 固定pin请求 | 02:08:49.604891904Z | snapshot f3dbad0f-e526-4136-b8cf-55159d80a061；选定gen76待机 |
| 后续状态首见 | 02:08:50.373473024Z | gen77 / seq1485 / 168a27…过渡 |
| 后续状态首见 | 02:08:51.991635968Z | gen78 / seq1488 / c5452b…完整Language菜单 |
| 原End工具调用 | 02:08:52.331858Z—02:08:52.339989Z | End_invoked=true；/api/stop请求02:08:52.338141952Z |

以上HAR时间是HTTP请求起点，并非精确到图像到达或模型审阅时刻；详见JSON中的HTTP耗时与frame.host_monotonic。第8步arm工具起点到End工具返回上界 **4.217秒**，小于原20秒alarm，未延长、未取消armed alarm。End后的[原final PNG](../../runs/v25gate-n64-r17-bd4c1126/trial-final.png)已实际查看为Setup > Area/Date 45/59、橙色Language English，完整SHA为 c5452b85dd066fdad5d96807acc3eafe8a6dfba64b36e7b53ed56367f41b3ce2；这是较晚图像，不能替代已选定的固定待机图，未追溯补confirm或把本轮改为通过。固定快照早于后来完整菜单是观察结论，所有异步绘制/下游处理的精确完成点仍未知。

正常清理逐项通过：API16原字节 **000b00b4fd7bbba9fd030091f35301a9**，guest restore_seen=1，1.571秒/原20秒预算；所有restore103原始header/API16及最终16字节均留存。QMP quit id677返回{}，QEMU exit0且reaped；runner61870、QEMU62048、自有browser daemon61881均absent；双锁独立探测free，55052端口closed且无监听；网页finalACK已确认，自有浏览器close成功且session inactive。第8步alarm保留armed至End后关闭自有文档，未强行cancel/dispose。证据见[CLEANUP.json](CLEANUP.json)、[独立清理探测](INDEPENDENT-CLEANUP.json)及原生run目录的restore103-receipt、qmp、resource-guard、receipt、trial-web-final-receipt。

[traffic.har](traffic.har)保存677条HTTP请求，POST为Start1、key8、review-snapshot8、confirm-visual7、stop1、final-ack1；[POST原请求/响应body](HTTP-POST-ORIGINAL-BODIES.json)另存完整身份。拒绝导出原字节仍在原生run的web-key-rejections.json：304字节，total/stored/truncated均0，SHA b40f2c25aacd2b1581701aa08e2fcb51c810cc9073af49c0241a349b4f19fa7c。原始serial.log完整保留；[40行按键原字节](NATIVE-KEY-ORIGINAL-LINES.bin)含16条down/up发送、16条native接收、8条done，[偏移索引](NATIVE-KEY-ORIGINAL-OFFSETS.json)绑定原serial位置。8键均一down一up、result0、requested_hold_ms100；ACK、HTTP202与健康通过不充菜单成功。

冻结与平台前后相同：r25交付594项、生产源30项，r24清单151项、r21清单145项及清单自身pin、source40、fixed14、实际QEMU。五个实际import按候选→冻结r21→旧兼容目录路径优先级解析，前后路径和SHA一致；PAGE canonical 852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b。固定4×cortex-a35、5120MiB、tcg,thread=multi、无icount；kernel da4a66fa…、DTB 5aa2beac…、N64 CPIO aaf00661…、实际QEMU bf4d4648…，完整hash、真实运行argv见INPUTS-BEFORE/AFTER、SEALED-DELIVERY-BEFORE/AFTER、ACTUAL-IMPORT-BEFORE/AFTER、ACTUAL-RUNNING-ARGV。未重跑离线矩阵。

v5 tail为valid_nontransactional_tail_checkpoint，snapshot_is_end_state=false、post_snapshot_event_counts=unknown，不充最终事务状态。真实恢复链本轮未触发，不能宣称已通过真实VM恢复验收；第8步精确固定图语义确认仍未完成。未推广为4096键、60分钟、全菜单、录像、实机或FX6验收；本dispatch没有剩余VM/Start授权。

原生运行目录：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-bd4c1126

联网准备核对仅用于冻结运行条件的解释，未据此改参数：[QEMU官方Invocation](https://www.qemu.org/docs/master/system/invocation.html)，2026-11-04读取，MTTCG每vCPU线程及icount不兼容条件；实际行为与通过范围以上述本轮原始证据为准。
