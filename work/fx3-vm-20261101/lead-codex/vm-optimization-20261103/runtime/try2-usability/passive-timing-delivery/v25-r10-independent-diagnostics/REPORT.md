# FX3 r10 独立暂停态诊断候选

2026-11-04。**宿主离线修复和定向测试完成；未启动 VM，未部署默认入口。** 原 r9、guest CPIO、QEMU、kernel、DTB、Backup 与 FX6 均未修改。外盘 UUID 已确认 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。

## 实测缺口与修复

A `v25diag-web-r6-0dfbd0ab` 的暂停态环文件完整 `16,777,216` 字节、SHA-256 `080acf35a507ac9849cfcba47dc2ad83e01b75663a516279c8b9d243b719643e`，内容全零；原 r9 `parse()` 抛 `ValueError('not a v25-r3 diagnostic readback')`，`ui-gate-counters.bin` 未生成。B `v25procdiag-web-r6-d4254d75` 的完整环有有效格式、`diag_snapshot.consistent=true`，同一 64 KiB UI gate 文件生成。r9 runner 原 733–765 行把全部声明的 optional `pmemsave` 放在 `diag_snapshot.consistent` 门后，这足以解释 A 的**诊断缺口**，不解释 A 的原生零帧原因。

r10 只改宿主：`quiesced_diag_readback.py` 分别记 `paused_proven`、`readback_complete`、`parse_valid` 和严格 `consistent`。完成 16 MiB 原始读回后先保存字节数/SHA；坏头或全零保留 `parse_error`，`consistent=false`。有效解析后的 JSON 写失败单列 `parsed_artifact_write_error`，不误记成解析错误；receipt 写失败单列 `receipt_write_error`，返回的内存对象仍在 cleanup 中，健康门仍 false。坏长度单列 `readback_error`，不尝试可选观察区。

runner 在**完整暂停态原始环**条件下调用 `optional_paused_snapshots.py`，不以解析成功作为读取 64 KiB UI gate 的前提；可选采集开始前再次 `query-status` 证明 paused，检查 transport `send_unknown`，以 10 秒共用 monotonic 截止预算逐个读取 DTB 已声明的区域，UI gate 排第一且不会重读 16 MiB 核心环。每项保留地址、预期/实际字节数、SHA、错误与未尝试原因；原路径已有文件不覆盖。QMP 调用使用剩余预算作 timeout；本地文件哈希按 64 KiB 分块在每次读取前查截止时刻，但文件系统单次 open/read/write 的阻塞时间不能被 Python 时钟检查硬中断，**10 秒不是包含不可控存储阻塞的硬实时保证**。可选结果同时进入内存 journal，最终文件落盘失败不伪称保存成功。

若 transport 已 unknown、暂停重证失败或核心读回不完整，不进行可选内存读取。可选 QMP 失败/timeout、文件缺失/坏长度、可选日志轮询或 `final-before-shutdown` 文件快照异常分别记账，不阻断后续原有 API16 恢复尝试；若 send_unknown 已发生，则明确记录 `transport_send_unknown_before_restore`，不强迫恢复写入或伪造 ACK，随后仍走现有 quit/进程回收。原 `restore_native_api(... timeout=20)` 和 guest 5000 ms 逻辑未改。

## 健康门与测试

原 runner `diagnostic_readback_pass = shutdown.get('diag_snapshot', {}).get('consistent') is True` 与 `health_pass = bool(health_pass and diagnostic_readback_pass)` 保持不变。定向测试执行**新 runner 的真实 finally AST**，接假 QMP/进程但调用真实 r10 环读取与可选采集函数，断言全零环虽取得 UI gate，诊断与最终 health 门仍 false；有效 B 环保持格式通过。还覆盖非 paused、读后暂停重证失败、send_unknown、坏长度、核心/可选 QMP 错误、可选 timeout 变 unknown 后不读第二项、原生文件快照落盘异常仍执行恢复与 reap、有效解析但 JSON 写失败、receipt 写失败、共用绝对 QMP 预算；全部 13 项 PASS。`--help` 导入和 `py_compile` PASS。夹具是离线宿主验证，未证明实际 QMP、存储压力、guest 恢复或 VM 健康。

## 冻结与审阅入口

| 文件 | SHA-256 |
| --- | --- |
| 原 r9 runner（未改） | `902869ee48c1c80dbe770316d0515ac429a5679beb1af73971dfabf7be041126` |
| r10 runner | `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0` |
| r10 环读取 helper | `51b2507730a5a7515333c0611022bf4a8c29d9a43663db8dd6e385db007ca6cb` |
| 新可选观察 helper | `15fbc3b50b1871b815b13c05b8275922f561ea2683c64c0d9a2e81c611d451a9` |
| [r9-to-r10.diff](r9-to-r10.diff) | `169039916000353778aa0cdad69df6952ec410d788a6c00dac6eb4c4d530b694` |
| [SOURCE-FREEZE.json](SOURCE-FREEZE.json)（22 个小型宿主 `.py`） | `65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce` |

新目录只有小型宿主源码、测试、差分和回执，没有复制 guest 镜像、Backup 或整个项目。`OFFLINE-TEST-RECEIPT.json` 是测试项目清单；`SHA256SUMS` 固定交付物。下一轮若获授权，仅可用此独立候选做一次有界真实 VM 验证：首故障暂停后核 16 MiB 原始环与 `ui-gate-counters.bin` 的地址/长度/SHA及 paused 再确认，随后原 API16 ACK/原字、QEMU wait/reap、PID 与两锁逐项验收；不得把 UI gate 采集成功当成首帧或健康通过。本任务未获 VM 授权。
