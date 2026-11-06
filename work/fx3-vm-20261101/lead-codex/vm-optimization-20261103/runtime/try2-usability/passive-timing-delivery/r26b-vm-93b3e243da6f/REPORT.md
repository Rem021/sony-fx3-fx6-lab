# FX3 r26b 唯一真实轮：failed

2026-11-04 PT（原始日志为2026-11-05 UTC）；task_93b3e243da6f / ctx_7a22b7cb527d。正式spec SHA：cdbe1e6e78e716eb0d31497a84cdd9c06faf542c8fa9d0806a1152d7014804c1。

**1 VM / 1 Start；1 accepted / 1显式attempt / 2张未固定观察 / 0实际pin / 0 confirm / 0恢复**。第1步原20秒alarm在pin前到期自动End，八步整体 **failed**，正常资源回收 **passed**。本轮返回适配已实际成功展示两张图，没有截断解析、旧current-return兜底或补回包；但未在期限内完成观察→固定链。第2张观察为完整目标菜单，未经固定PNG重新看图和独立确认，不计该步通过，也不能推断固件菜单失败。

[RESULT](RESULT.json) · [逐步图像与身份](STEP-EVIDENCE.json) · [第1步时序](STEP1-TIMELINE.json) · [Node调用证据](OPERATOR-TOOL-CALL-EVIDENCE.json) · [4个tool-return目录索引](TOOL-RETURN-INDEX.json) · [SHA清单](SHA256SUMS)

首个合格待机 **44.089秒**（上限180秒），runner运行 **100.443秒**（预算480秒）。本轮[待机PNG](initial-standby/current.png)实际查看后另调standby_review。scripted_navigation=true、visual_review_at_click=false；模型实际收图/审阅完成时刻unknown，宿主工具时刻不能冒充模型审阅时刻。

启动前使用真实mcp__node_repl__js导入tool_call/show_result，实际执行Node子进程、filesystem读取及emitImage，亲看封存display-fixed-node历史样本并明确标historical_replay_only=true/current_VM_standby=false，证据[PRESTART-NODE-DISPLAY](PRESTART-NODE-DISPLAY.json)。样本不充本轮待机或菜单成功。

| 步骤 | 本轮真实返回图 | 实际看图判断 | 后续独立动作 |
|---|---|---|---|
| 1 MENU | [观察1](step-01-attempt-01/observation-1/observation.png) | Setup Area/Date过渡布局，橙色目标未完整选中 | observe |
| 同一step/attempt | [观察2](step-01-attempt-01/observation-2/observation.png) | 完整Setup > Area/Date 45/59；橙色Area/Date/Time Setting，Language English与NTSC/PAL Selector | 明确pin，但入口前已到期 |
| 第1步固定图 | 未创建 | 无固定图可审阅 | 未confirm，不计步骤通过 |
| 2—8 | 未执行 | 未验 | terminal/End后未继续 |

两张观察均经固定生产tool_call.mjs executeAndLoad→本次UUID目录完整child.stdout.json/stderr→文件loadResult→nodeRepl.emitImage，在同一顶层工具调用实际显示；未解析exec终端屏幕输出，未读旧current-return兜底。click与pin的functions分别yield为cell11/cell13，只functions.wait取同一cell结果，没有重执行动作。120000ms只是工具等待上限，原alarm仍20000ms。pin非零后Node返回return_failed/无PNG且不读成功summary；原operate失败已自行End并完成cleanup，没有用旧图继续。

每次原动作的完整stdout、stderr、process、invocation、summary均保留在4个tool-return-UUID目录；两次成功图另有原字节运输副本returned.png，SHA与相应原观察PNG一致、未转换。观察PNG SHA分别为 601a879a268fb8ccd76edccdb6c049302cf4375e0bd9ca66f52f3efe3d66baac / fc8231453992f12bc8ea98ba5be9cd7d74112fffdd1f41b0f949d8b27b8c73d7。每张独立receipt保留reservation、run/launch/document/step/attempt/nonce、before/after显示帧与alarm身份；firmware_generation=null、input_permission=false、snapshot_pinned=false、postkey_confirmation=false，PNG截图身份不等同固件帧generation。snapshot_id与confirm请求身份均不存在。

| 原始时序 | UTC | 说明 |
|---|---|---|
| arm | 03:00:41.562Z | 同nonce、原deadline20000ms |
| click返回准备完成 | 03:00:44.130582Z | 首图返回；随后同工具显示并亲看 |
| observe入口 | 03:00:53.839841Z | click返回后9.709404125秒 |
| observe返回准备完成 | 03:00:54.002668Z | 第二图同工具显示并亲看 |
| alarm自动End | 03:01:01.565Z | elapsed_ms=20002.5；sealed/expired |
| pin入口 | 03:01:03.034289Z | arm后21.472289秒，observe返回后9.03171625秒 |
| wrapper失败 | 03:01:03.043086Z | owned browser operation failed，flow转terminal并原cleanup |

两个间隔是宿主工具调用间隔，不是精确模型审阅耗时。实际PNG首次送达、模型接收、思考及工具调度的各自贡献unknown；本轮只证实全链未在20秒内到达pin。原evaluate的具体失败子条件未被保留，generic失败和alarm先到期是分别留证的事实。未扩时、重武装、补键、重试pin或追加Start。

正常清理全通过：API16原字节 **000b00b4fd7bbba9fd030091f35301a9**，guest restore_seen=1，**1.834161秒 / 原20秒预算**；最终16字节及各次原始header/API16均留存。QMP quit id407返回{}，QEMU exit0/reaped；runner73163、QEMU73239、自有browser daemon73173均absent，双锁独立探测free，64077端口closed/无监听，网页finalACK已确认，自有浏览器close成功且session inactive。见[CLEANUP](CLEANUP.json)、[独立清理探测](INDEPENDENT-CLEANUP.json)、FAILURE-CLEANUP-DISPATCH及原生run下restore103-receipt、qmp、resource-guard、receipt、trial-web-final-receipt。原alarm先触发End，wrapper清理核页已ending，无额外stop POST。

全部482条HTTP请求保存在[traffic.har](traffic.har)，[原POST body](HTTP-POST-ORIGINAL-BODIES.json)包含Start1、key1、stop1、final-ack1；review-snapshot/confirm POST均0。拒绝导出保留原字节，total=0、truncated=0，304字节、SHA 6fb230c492374ba7136cdb67b84911634fe46e36e0dd3b6409d208d744387801。完整serial.log保留；[5条原按键行](NATIVE-KEY-ORIGINAL-LINES.bin)含down/up发送、native down/up接收及done，[偏移](NATIVE-KEY-ORIGINAL-OFFSETS.json)绑定原字节；键0x1ab、一down一up、result/native_result0、requested_hold_ms100。ACK/HTTP202/health_pass不计菜单成功。

候选/适配前后相同：r26交付1277项与33生产源、返回适配169项与5源；r25清单594项、r24清单151项、r21清单145项及清单自身pin、source40、fixed14、实际QEMU均匹配。五个实际import路径及SHA一致，候选→冻结r21→旧兼容目录的优先级保持；PAGE canonical 852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b。固定4×cortex-a35 / 5120MiB / MTTCG / noicount，kernel da4a66fa… / DTB 5aa2beac… / N64 CPIO aaf00661… / 实际QEMU bf4d4648…；完整hash与真实argv见INPUTS-BEFORE/AFTER、SEALED-DELIVERY-BEFORE/AFTER、ACTUAL-IMPORT-BEFORE/AFTER、ACTUAL-RUNNING-ARGV。未写旧runtime自然输出，未改源码、平台、输入门、期限、部署入口或协调ledger；部署仍r10，r25/r26失败保留，未重跑离线矩阵。

v5 tail仍非事务checkpoint，snapshot_is_end_state=false、post_snapshot_event_counts=unknown。本轮真实postkey pin/confirm、完整8步及恢复链均未验收，不泛化4096键/60分钟/所有菜单/录像/实机/FX6，本dispatch没有剩余VM/Start授权。

原生run：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-45304842。任务入口：[README](README.md)。
