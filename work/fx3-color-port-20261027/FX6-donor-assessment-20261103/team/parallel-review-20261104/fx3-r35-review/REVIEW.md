# r35 独立只读审查

结论：发现 1 项首次 publication 摘要覆盖缺口，读取期间已由唯一实现者修复；修复后的源码逻辑与新增宿主回执支持关闭该项。未发现其他已确认代码缺陷；本报告不构成最终构建验收、guest 运行验收或 FX6 开机验收。

审查截止快照：2026-11-04 22:43:40 PST / 2026-11-05 06:43:40 UTC。候选在 ctx_2615e5e41dfd 下持续修改，[snapshot.json](snapshot.json) 记录 38 项有限输入的首次、阶段结束及后续读取 SHA-256；变化文件明确登记，未保存候选副本、未重新封存。只写本目录；未执行候选、候选测试或研究脚本，未启动 QEMU、guest、浏览器、服务或设备。审查者仅运行自己编写的文本/数据公式分析。

## F1：bind 完成后可压住后续 publication 导出（已修复，原 P2）

**发现时版本**：`src/r35-log.inc` SHA-256 `d3ec88635bf5ea1c5b66890bb9c5c81c4205ea150ee0db17ffe0a03aadb07664`。当时第 26 行先判断 bind 状态；bind 完成后类别始终为 5，第 29–30 行只输出尚未见过的类别。

这并非单凭任意 BSS 篡改构造：[src/fx3-osd-r35.c:114](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/src/fx3-osd-r35.c:114) 中的原 observe 分支允许任一合法 publication 首先触发 observer_bind；[src/fx3-osd-r35.c:123](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/src/fx3-osd-r35.c:123) 仅对 CONTROL 的 0x1002 子操作记录 r35 publication。已有 schema 在 [fx3-osd-owner-core-v1.h:6](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-osd-owner-core-v1.h:6) 同时接纳 PIXELS 0x1003/36B 和 META 0x1005/8B，其 SHA-256 为 `8b3ff05b51a3049691e09b9fd5f8832dbc2dc0ac65f25010d768212bff70d26a`。

若合法 PIXELS/META 先使 bind 完成，并在其后有原 UI 日志机会：

| 观测点 | publication phase | bind phase | 旧类别 | 旧摘要 |
|---|---:|---:|---:|---|
| bind 完成，首次 CONTROL 尚未到达 | 0 | 2 | 5 | 输出 |
| 首次 CONTROL 开始 | 1 | 2 | 5 | 被 seen 抑制 |
| 同次 CONTROL 返回 | 2 | 2 | 5 | 被 seen 抑制 |

因此即使尚余 6 条 / 1104B 额度且有原日志机会，也可能不导出后来的首次 publication。影响是诊断覆盖缺失，不是解析器伪造 End 状态。该序列在候选 helper 的入口条件上成立；本次没有证明 Sony guest 会实际采用这种先后顺序。旧公式的可复核数据轨迹见 [phase-key-trace.json](phase-key-trace.json)。

**修复复核**：后续 [src/r35-log.inc:26](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/src/r35-log.inc:26) 的 SHA-256 为 `8b12932497189be9163f2c98ff7273ff097380c62c6142ef0196f4a68669986b`。第 28–36 行改用独立的单调位，分别覆盖 unknown、干净初态、publication entry/return、bind entry/return、loss；完成态也覆盖对应 entry。先 bind 再 publication 会引入新的位，不再被类别 5 遮蔽。

[tests/collector_log_test.c:62](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/tests/collector_log_test.c:62)（SHA-256 `da0dd6e71cc0410002b79e85af4fd221e31385d737a45b20575bf998c9c6812b`）新增全部六种有序两阶段交错，逐步断言输出与条数；[receipts/collector-log.stderr:6](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/receipts/collector-log.stderr:6)（SHA-256 `6456eb995a58433d7a0e21310ff5cec4eb17a6438d332f34686a158cfab0fe33`）记录相应 PASS。后续读取 [HOST-COLLECTOR.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/HOST-COLLECTOR.json) 的 compile_exit/run_exit 均为 0。这是实现者的宿主回执，本审查未重跑其测试。

独立的 [static_phase_review.py](static_phase_review.py) 只读取并核对上述修复源码哈希和公式，再枚举六种交错、五个首次 loss 插入位置及两种早期状态组合；[phase-fix-model.json](phase-fix-model.json) 的 120 组数据模型均保留独立阶段推进，最多 7 条 / 1288B。此证据只补充公式审查，不冒充实际 C 执行、调度或 guest 验收。**F1 在上述修复快照的源码与宿主范围内闭合。**

## 其余审查结果及证据边界

- **进程身份**：[src/r35-collector.inc:10](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/src/r35-collector.inc:10) 的实时 syscall(172) 在 owner 比较之前执行且恢复 errno；pub/bind entry/return 和 snapshot 在相应诊断状态写入前拒绝外来 TGID；[src/r35-log.inc:19](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/src/r35-log.inc:19) 在日志锁、seen 和额度修改前检查实际 TGID。[tests/collector_log_test.c:34](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/tests/collector_log_test.c:34) 的全入口拒绝/状态不变检查、43–55 行的注入共享 BSS、实际宿主 fork 和同 TGID 多线程测试，与 [receipts/collector-log.stderr:1](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/receipts/collector-log.stderr:1) 的标签吻合。它们不等于 AArch64 raw clone/vfork 实测；无需据此添加或宣称此类运行结果。首次读 collector 哈希为 `13f07826cca4b7d92cdaaedcfcdfbd1ccbe6de43a2c98b2f3f153627f1ce9035`，后续读取未变。

- **日志预算**：修复后的 [src/r35-log.inc:28](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/src/r35-log.inc:28) 只有 7 个 obligation 位；每次导出必增加至少一个未见位，36 行累计额度，40–42 行形成固定 184B 后缀，最多 7×184＝1288B。35 行使用减法形式检查上限，避免旧加法形式的无符号回绕；这是读取期间实现者一并加入的防御。此证明依赖“唯一活跃安装实例”的既有合同，不能扩展为任意重新加载/清 claim 条件下的全局额度保证。[INSTANCE-CONTRACT.json:162](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/INSTANCE-CONTRACT.json:162) 明列 preload、claim 持续存在及禁止重装等前提；[tests/claim_fixture.c:13](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/tests/claim_fixture.c:13)、24 行只验证实际宿主 O_EXCL 和模拟的 bind_ram 映射，不能证明未来 guest 的完整动态加载生命周期。

- **解析与未知值**：[parse_r35.py:15](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/parse_r35.py:15) 至 36 行分别验证版本/来源/校验、身份、阶段、原返回、映射与 magic，输出区分未绑定、未初始化、争用、身份拒绝和捕获未完成等状态；59–78 行验证 UI/collector 实例、序号及首记录不可替换；81–88 行明确范围仅为完整原日志点，host run ID 来自调用者，不把 PID/初始化时间戳当全局 run ID。未找到新的“缺 token 即证明事件未发生”推断。其读取哈希 `03313c7c83d0951a77500c9b2aeb27e41e85d197a846a00bf72d8d1fc28be393` 在后续读取未变。

- **已知超长行问题已关闭**：[parse_r35.py:39](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/parse_r35.py:39) 至 47、79–83 行使用 discard 状态，不再因超长行调用 End 后继续 feed。协调端 [receipt.json:5](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-coordinator-parser-check/receipt.json:5) 记录同一解析器哈希前后稳定；两例在 22、58 行 exit=0，records 为空且存在结构化 unknown。该回执 SHA-256 为 `136ebc3cd80436281dc5101afa5240907f1e7a7494b47d5e27ac8d2f5007f70d`。后续 [PARSER-TEST.json:4](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/PARSER-TEST.json:4)、10 行已与 CRLF / 超长行新增测试名称一致，未将旧回执作为现状阻塞。

- **宿主原行为等价**：[HOST-WRAPPER.json:35](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/HOST-WRAPPER.json:35) 声明 equivalent_stdout=true，两个 stdout 的 SHA-256 均为 `7430f04a2559459220a94cc3c888b6d274420005a1a93a6278f8ddb830a3f4fe`；八种模式记录相同 rc、errno、send/open/read/map/close/log/thread 次数。[tests/wrapper_fixture.c:1](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/tests/wrapper_fixture.c:1) 明确 native/system facilities 被替身代替，不能把该结果写成 Sony 原函数或物理映射已运行。[HOST-UI.json:33](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/HOST-UI.json:33) 的声明也仅覆盖所选日志块去除后缀后的原字段字节等价；UI 条件修改范围见 [ui-source.diff:15](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/ui-source.diff:15)。

- **成本披露**：后续 [HOST-COST.json:20](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/HOST-COST.json:20)、54 行的首次 claim-failure wrapper 回执记录原 1 次 / 候选 5 次宿主 getpid，符合 pub begin/end + bind begin/end 的最多新增 4 次；同文件的 steady_completed_claim_failure_wrapper 指标另列原 1 次 / 候选 3 次。[HOST-UI.json:31](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate/HOST-UI.json:31) 记录 51 次原日志对应 102 次新增诊断 getpid，及真实宿主 /dev/null vdprintf 成本、预算耗尽时仍执行 2 次检查；没有把额外字节或 getpid 成本隐去。wrapper 的 native/I/O 是替身，UI 只覆盖所选日志块，且 vdprintf 标签明确不推断底层 write 次数；这些纳秒测量均不能保证 guest 时序或串口扰动。仅凭 dprintf 源码调用次数相同，仍不能宣称实际输出 syscall 次数不变。

## 下一验证门

1. 实现者固定最终交付后，协调端核对**同一最终源码、测试输入、宿主回执、AArch64 构建及汇编审查**的哈希链。读取期间 BUILD.json、ASSEMBLY-AUDIT.json、测试及成本回执继续变化；本审查没有逐一复核其最后生成的二进制及指令，不能把较早汇编回执套到较新源码。
2. F1 无需继续改本审查目录的结论为“待修复”；应保留其发现/修复哈希、六种交错测试及额度上限。进一步运行若另获授权，才核对最终映射实例、同一次 host run/End 截止与日志实际机会；本任务不授予或执行该运行。
3. r35 只补 FX3 诊断可观测性。其源码/宿主闭合不解除被拒 FX6 实现的限制，也不替代固定 FX3 平台上的 FX6 上层开机菜单验收。

