# FX3 r24 真实八步验收：failed（7/8），回收通过

唯一VM/Start完成7 accepted、7次逐图独立confirm，共8次显式attempt；第8次MENU被原PAGE明确not_posted，未向队列发第8键。恢复cancel成功后，新图身份断言失败，wrapper立即End；没有recovery_review、新nonce、新键或额外Start。部署仍原入口，原r23失败保留，冻结源码未改。

| 步 | 实际亲看固定PNG的判断 | PNG SHA前12位 | gen / seq | arm→confirm秒 | 结果 |
|---|---|---|---|---|---|
| 1 | 已亲看本步固定PNG：完整Setup > Area/Date 45/59，橙色选中Area/Date/Time Setting，Language English及NTSC/PAL Selector完整可见，符合第1步。 | 60e9acccbc46 | 33 / 232 | 11.104 | 通过 |
| 2 | 已亲看本步固定PNG：Setup > Area/Date 45/59，橙色选中Language，右侧English，Area/Date/Time Setting移至下方，符合UP到Language English。 | c5452b85dd06 | 34 / 422 | 5.601 | 通过 |
| 3 | 已亲看本步固定PNG：橙色Language标题，下方Selects the display language.帮助文字和右下OK，符合C4语言帮助。 | 74a59929fafe | 35 / 576 | 6.174 | 通过 |
| 4 | 已亲看本步固定PNG：语言帮助关闭，返回完整Setup > Area/Date菜单，橙色Language与English可见，符合MENU返回Language。 | c5452b85dd06 | 36 / 791 | 5.915 | 通过 |
| 5 | 已亲看本步固定PNG：Language弹出列表打开，English单选项橙色高亮，另见日本語、Français、Deutsch、Italiano、Español；仅查看未选择或修改语言，符合第5步。 | 5aa0cd7e62b6 | 37 / 998 | 9.437 | 通过 |
| 6 | 已亲看本步固定PNG：Language弹出列表已取消，返回Setup > Area/Date，Language仍橙色选中且值English保持，符合MENU取消列表。 | c5452b85dd06 | 38 / 1209 | 6.345 | 通过 |
| 7 | 已亲看本步固定PNG：Setup菜单关闭，恢复NO CARD、HD Fixed-59.94fps、AF-C、AWB、D-R OFF及曝光图标的待机画面，无列表或对话框，符合MENU关闭到待机。 | 2914275caea5 | 39 / 1376 | 6.082 | 通过 |
| 8 | 未发键；恢复图仍NO CARD待机，未得到重开菜单图 | — | — | — | 未验收 |

操作代理实际看过初始待机页面及1–7步的完整指定原PNG，随后各自独立调用standby_review/confirm。scripted_navigation=true、visual_review_at_click=false，不声称实时人工视觉。每步snapshot/run/launch/document/step/attempt、PNG SHA/长度/gen/seq、native观察下界、confirm request UUID与历史回执完整保存在 [STEPS-EVIDENCE.json](STEPS-EVIDENCE.json) 及原各步文件；模型实际收图/完成审阅时刻unknown。

失败位置准确为候选 runtime-wrapper/operate.py:84 调用 untimed_image.snapshot，继而 runtime-wrapper/untimed_image.py:7 的 before/after step、sha、gen、origin一致且sequence不倒退断言。第8次attempt UUID为99f68a04-a042-428a-956d-5f1685573322，原PAGE结果not_posted、mutation_called=false、原因preflight_identity_or_lifecycle_changed；不能再细分该组合门内的具体触发条件。独立cancel成功后，约54ms的新截图观察窗发生：
- before：step7，seq1615，gen65，SHA2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e。
- after：step7，seq1622，gen66，SHAe0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4。
- origin保持1793842568306.2；SHA/gen改变使原断言失败。没有新合格恢复图返回、没有独立recovery_review，立即原End。原before/after stdout、traceback、恢复图、cancel回执均完整保留。

首个合格待机图 44.224 秒/180秒；runner时长 167.449 秒/480秒。实际argv为4×cortex-a35/5120MiB/MTTCG/noicount，原kernel/DTB/N64 CPIO及实际QEMU匹配给定哈希。r21清单自身、145项含manifest、source40、fixed14、实际QEMU及r24最终源码前后匹配；r24清单151项、外部pin3、源码冻结28共182条核验记录。实际导入优先级候选→冻结r21→旧兼容目录。见CANDIDATE-HASH-BEFORE/AFTER、INPUTS-BEFORE/AFTER、ACTUAL-IMPORT-PROBE；未重跑离线矩阵。

7组原生down/up/done与sender结果核回；[NATIVE-ORIGINAL-LINES.bin](NATIVE-ORIGINAL-LINES.bin)保留36条原字节行，完整serial与输入事件在本轮guest目录。ACK不充菜单成功，语义结论来自指定PNG的实际查看。零服务端拒绝也逐字节保留 [WEB-KEY-REJECTIONS-ORIGINAL.json](WEB-KEY-REJECTIONS-ORIGINAL.json)；PAGE未入队和服务端拒绝分开计数。

正常End全项回收通过：API16原字节000b00b4fd7bbba9fd030091f35301a9、guest restore_seen=1，耗时1.320秒/原20秒预算；QMP quit id690匹配ACK、QEMU exit0/reap/PID absent、runner PID absent、双锁free、49966端口closed、网页finalACK、自有browser inactive/PID absent，自有持久shell已关闭。独立复核见 [FINAL-RESOURCE-VERIFICATION.json](FINAL-RESOURCE-VERIFICATION.json)，原restore103二进制、qmp.json、resource guard与最终ACK保留。

[traffic.har](traffic.har)保存628条捕获请求，24POST=Start1+key7+snapshot7+confirm7+End1+finalACK1。原POST请求响应另见HTTP-POST-TRACE.json；没有第8次key POST。候选wrapper在初始网页导航后、Start前开始HAR，因此最初document GET没有HAR原件；默认HAR未嵌入全部binary响应，精确审阅PNG另行保留，不声称HTTP线级无缺口。

v5 tail是非事务检查点：snapshot_is_end_state=false，post_snapshot_event_counts=unknown，不能充最终状态。未扩展到4096键、60分钟、全菜单、录像、实机、FX6或任何设备/部署动作；本授权用完，不再起VM。八步目标仍缺第8步重开及确认。

本task证据根：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r24-vm-a2792c17db55
guest原件：/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v25gate-n64-r17-3c01e985

索引：[README.md](README.md)；结构化结果：[RESULT.json](RESULT.json)；全部文件清单：[SHA256SUMS](SHA256SUMS)。
官方背景只核MTTCG条件：[QEMU Invocation](https://www.qemu.org/docs/master/system/invocation.html)（2026-11-04访问）；运行结论来自本轮原件。
