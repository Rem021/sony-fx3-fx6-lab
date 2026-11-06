# FX3 r26 唯一真实轮：failed

2026-11-04 PT（原始时间为2026-11-05 UTC）；task_49f0c1c3663b / ctx_5b588c78070c。正式spec SHA：22f4a800c2d3732c644bd6e9c39541f0484830dacd494b8d738024f6bf5fbf62。

**1 VM / 1 Start；1 accepted / 1显式attempt / 2张未固定观察 / 0实际pin / 0 confirm / 0恢复**。第1步原20秒alarm在pin前到期自动End，八步整体 **failed**，完整正常资源回收 **passed**。这是本轮操作链超时，不能据此判定固件菜单失败；第2张真实观察图已显示完整预期菜单，但未经固定图重新看图和确认，不计第1步通过。步骤2—8未执行，未补键、未重复pin、未追加Start。

[RESULT](RESULT.json) · [逐步图像与身份](STEP-EVIDENCE.json) · [精确时序](STEP1-TIMELINE.json) · [实际工具调用证据](OPERATOR-TOOL-CALL-EVIDENCE.json) · [SHA清单](SHA256SUMS)

首个合格待机约 **44.174秒**（上限180秒），runner运行 **82.255秒**（预算480秒）。初始[真实待机PNG](initial-standby/current.png)实际查看后另行standby_review。scripted_navigation=true、visual_review_at_click=false；模型实际收图/审阅完成时刻unknown，以下只报告宿主工具边界和浏览器alarm日志。

| 实际步骤 | 观察 / 固定 | 亲看判断 | 独立后续动作 |
|---|---|---|---|
| 1 MENU | [观察1](step-01-attempt-01/observation-1/observation.png) | Setup Area/Date过渡布局；橙色目标尚未完整 | observe |
| 1 MENU，同一attempt | [观察2](step-01-attempt-01/observation-2/observation.png) | 完整Setup > Area/Date 45/59；橙色Area/Date/Time Setting、Language English、NTSC/PAL Selector | 明确pin，但其入口前已到期，守卫失败 |
| 1固定图 | 未创建 | 无固定图可审阅 | 未confirm，不计语义通过 |
| 2—8 | 未执行 | 未验 | 终止后未继续 |

两张观察均为真实agent-browser screenshot完整浏览器PNG，并各保留独立reservation、receipt、before/after端点与精确run/launch/document/step/attempt/nonce。观察1截图SHA 0c3025aa19b4846922eece1d17634666b5fa217bed6e1744178c7ad00174cc44；观察2截图SHA 705bcfb378236933ca5a962ae69b638561375653ca81ed91e58b69dc82244dd0。before/after显示帧分别为gen31/seq227/abc20e…与gen33/seq355/60e9ac…；这些端点不为截图赋予精确固件generation，firmware_generation=null、input_permission=false、snapshot_pinned=false、postkey_confirmation=false。snapshot_id和confirm请求身份均不存在，未虚构。

| 原始时序 | UTC | 证据 |
|---|---|---|
| arm | 02:38:11.930Z | 同nonce，deadline_ms=20000 |
| click返回准备完成 | 02:38:15.311783Z | 观察1已合格导出 |
| observe入口 | 02:38:27.662477Z | 与click返回相隔12.350843208秒（宿主单调时钟） |
| observe返回准备完成 | 02:38:27.830991Z | 观察2导出，随后实际看图 |
| alarm自动End | 02:38:31.932Z | elapsed_ms=20002.5，sealed=true、expired |
| /api/stop | 02:38:31.933128192Z | 唯一一次stop POST |
| pin入口 | 02:38:33.543777Z | arm后约21.613777秒；与observe返回相隔5.712990959秒 |
| wrapper失败 | 02:38:33.553034Z | owned browser operation failed；flow进入terminal |
| wrapper原End清理 | 02:38:33.587250Z | 页面已ending，End_invoked=false；未再发stop |

两个间隔是**工具调用间隔，不是精确模型看图耗时**。本次首次functions.exec内exec_command设置max_output_tokens=1200，返回过长导致截断，随后JSON.parse(r.output)报Unexpected token W / Warning: t，未在该调用显示PNG；下一独立只读调用从本task current-return.json读短结构并实际显示观察1，随后才observe。工具调用及报错按实际聊天调用留在[证据JSON](OPERATOR-TOOL-CALL-EVIDENCE.json)，完整被截断stdout未保留，写unknown；原wrapper观察结果及tool-timeline仍完整保留。输出上限选择过小是操作执行失误，额外读图调用与后续调用间隔消耗原20秒，不能把这些时间都归给固件或模型审阅。没有扩时、重武装或到期复活；pin命令原evaluate只保存generic失败，具体守卫子条件未留下，独立确定事实是alarm已先到期。

正常清理：API16原字节 **000b00b4fd7bbba9fd030091f35301a9**，guest restore_seen=1，**1.320601秒 / 原20秒预算**；最终原始16字节、各原始header/API16读取均留在原生run。QMP quit id317返回{}，QEMU exit0/reaped；runner69364、QEMU69453、自有browser daemon69371均absent；双锁独立free探测，61254端口closed/无监听，网页finalACK确认，自有浏览器close成功且session inactive。证据：[CLEANUP](CLEANUP.json)、[独立回收](INDEPENDENT-CLEANUP.json)、FAILURE-CLEANUP-DISPATCH及原生run下restore103-receipt、qmp、resource-guard、receipt、trial-web-final-receipt。alarm保留原20秒并自动End，之后依原cleanup处置expired alarm。

全部 419 条HTTP请求保存在[traffic.har](traffic.har)，[POST原body](HTTP-POST-ORIGINAL-BODIES.json)为Start1、key1、stop1、final-ack1；review-snapshot/confirm POST均0。拒绝导出保留原字节，total=0、truncated=0，大小304字节、SHA 1acbda7b05bb083905a4e8f630d0f3a8a91bdd567d8f78a53e1578570ceab3bd。原生serial.log完整保留，[5条原始按键行](NATIVE-KEY-ORIGINAL-LINES.bin)含down/up发送、native down/up接收及done，[原字节偏移](NATIVE-KEY-ORIGINAL-OFFSETS.json)对应原serial；键0x1ab，一down一up、result/native_result0、requested_hold_ms100。ACK/HTTP202/health_pass不计菜单验收。

前后核验相同：r26交付1277项与33生产源，r25清单594项、r24清单151项、r21清单145项与清单自身pin、source40、fixed14及实际QEMU。五个实际import路径和SHA一致，解析优先级候选→冻结r21→旧兼容目录；PAGE canonical 852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b。固定4×cortex-a35 / 5120MiB / MTTCG / noicount、kernel da4a66fa… / DTB 5aa2beac… / N64 CPIO aaf00661… /实际QEMU bf4d4648…，完整hash与真实argv分别保存在INPUTS-BEFORE/AFTER、SEALED-DELIVERY-BEFORE/AFTER、ACTUAL-IMPORT-BEFORE/AFTER、ACTUAL-RUNNING-ARGV。未重跑离线矩阵，未写旧runtime自然输出，未改源码/部署/协调ledger，r10部署及r25失败保留。

v5 tail仍为非事务checkpoint，snapshot_is_end_state=false、post_snapshot_event_counts=unknown。真实postkey pin/confirm完整链及8步、真实恢复链均未验收，不泛化60分钟/4096键/所有菜单/录像/实机/FX6。本dispatch不含额外VM权限；后续操作工具包装验证与新派发由协调端安排，本轮只封存。

原生run：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-740bafa8。任务目录入口：[README](README.md)。
