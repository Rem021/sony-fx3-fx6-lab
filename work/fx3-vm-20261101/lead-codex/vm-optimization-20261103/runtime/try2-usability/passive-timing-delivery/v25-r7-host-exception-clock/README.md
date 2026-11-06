# FX3 r7 宿主首异常双时钟补丁

2026-11-04：**12 项离线测试通过；固定 r6 源可零 fuzz、零 offset 精确应用补丁。未集成、未部署、未启动或验证 QEMU/VM。**

任务依据：[宿主异常时钟审查](../../host-storage-20261104/host-exception-clock-review.json)。所有新增文件仅在本 r7 目录；r6、默认入口、guest、FX3 平台参数和其他代理文件未修改。外盘 UUID 已核验为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；Mac 项目根不在 Git 仓库内。

## 交付入口

| 文件 | 内容 |
| --- | --- |
| [r6-to-r7-host-exception-clock.patch](r6-to-r7-host-exception-clock.patch) | 仅修改 runner 的小补丁，供下一冻结候选审阅集成 |
| [host_exception_clock.py](host_exception_clock.py) | 首异常与现有 `qmp.json` 的专用 helper |
| [test_host_exception_clock.py](test_host_exception_clock.py) | 真实宿主文件故障及 patched handler/execute_runner 有界测试 |
| [verify_patch.py](verify_patch.py) | 固定源哈希、补丁 dry-run/应用、编译及 AST 对照；不导入完整 runner |
| [PATCH-TARGET.json](PATCH-TARGET.json) | 固定源、差异和预期补丁后源哈希 |
| [PATCH-APPLY-RECEIPT.json](PATCH-APPLY-RECEIPT.json) | 实际 patch 命令、退出码、源前后哈希和 AST 回执 |
| [OFFLINE-TEST-RECEIPT.json](OFFLINE-TEST-RECEIPT.json) | 最终 12/12、0 failures、0 errors，含内存 journal 快照和测试输出 |
| [OFFLINE-TEST-INITIAL-FAILURE.json](OFFLINE-TEST-INITIAL-FAILURE.json) | 保留首轮 11/12 的测试提取器故障；见下文 |
| [SHA256SUMS](SHA256SUMS) | 交付文件与最终补丁应用副本的 SHA-256 清单 |

`apply-checks/` 仅保存约 64 KB 的 runner 文本验证副本，`offline-cases/` 是本任务创建的微型文件故障夹具；没有复制镜像或构成可启动运行包。

## 行为和持久化边界

1. `write_host_first_exception` 在同一次采集步骤中相邻读取 `time.monotonic()` 与 UTC 时钟，保存 `host_monotonic` 和带 `+00:00` 的 ISO 8601 `host_utc`。二者不是原子采样，也不从 monotonic 推算 UTC。
2. traceback 显式来自传入异常的 `exc.__traceback__`，不依赖调用位置的活动异常；保留异常链。`transport=None` 时两个 QMP 字段为 `null`；存在 transport 时只快照既有状态，不发 QMP 命令。
3. 首异常在写文件**之前**加入 journal 的 `host_first_exception` 项，成功写文件也保留内存项。后续调用直接返回同一首异常对象，不改其类型、错误、traceback、时钟和 QMP 快照，也不重试覆盖首异常文件。
4. 持久化状态作为同一 journal 项的 `host_first_exception_persistence` 保存，与原异常字段分开。失败为 `status=failed`、`write_completed=false`，另有实际写入异常类型/内容；stderr 尽力提示，stderr 故障也不会替换原异常。
5. `status=write_completed` 只表示 Python `write_text` 返回成功；`durability=not_verified` 明确未做 fsync 或掉电耐久证明。首异常文件保持原记录结构并新增 UTC；持久化状态在内存 journal 中，之后 `qmp.json` 成功写入时带入。
6. `write_host_journal` 只写原有 `qmp.json`。它自己的写入结果在尝试后加入内存的 `host_journal_persistence`，因此不会在该次文件内容中虚报自己的完成状态。写失败仍抛出原写入异常；若此前尚无首异常，则采集此异常，若已有则保持不变。
7. runner 在 `trial.fail` 前先采集；`ACTIVE_HOST_JOURNAL` 保留同一 journal 引用，使 `main` 栈展开后仍能检查首异常。外层 `execute_runner` 捕获的异常及 guard 异常也经过同一首异常门，不覆盖已有记录。

helper 不创建父目录、不重试、不选择回退路径、不写其他卷或 iCloud。外盘不可写且 journal 文件也失败时，剩余证据只有进程内存和尽力输出的 stderr；进程退出后的持久留存不作保证。内存 journal 由 runner 单一宿主控制线程持有，本补丁不扩展为通用或并发日志系统。

## 已执行验证

在本目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 test_host_exception_clock.py
shasum -a 256 -c SHA256SUMS
```

第一条先核验外盘 UUID 和固定源 SHA，再把一个 runner 文本复制到本目录内，执行 patch dry-run 和实际应用，并运行离线测试。重新执行会生成新的小型测试目录并刷新两份最终回执；如需复核原交付哈希，应先执行第二条。

| 覆盖 | 结果 |
| --- | --- |
| UTC 偏移、ISO 解析、采样时间范围、monotonic 范围；成功写文件仍保留 journal | 通过 |
| 离开原 except 后、另一个异常的 except 内仍取原 traceback | 通过 |
| transport 状态快照；后续 OSError/KeyboardInterrupt 不改首异常或磁盘记录 | 通过 |
| 实际缺失输出父目录；首异常输出路径实际为目录 | 均记录真实写入失败且不创建缺失目录 |
| 首异常文件与 qmp 文件均失败；qmp 路径为目录；qmp 写入作为首个宿主错误 | 原首异常保留，qmp 写入错误继续抛出，状态明确 |
| qmp 成功写入及 stderr 自身失败 | 状态和错误边界符合上述合同 |
| 从 patched 源提取的 `execute_runner`，假 main 抛异常且输出父目录缺失 | guard 实际调用一次并结束；新增记录失败未阻断收尾 |
| patched 原异常 handler 在 `trial.fail` 真实缺目录故障前记录首异常；随后 guard 首次真实文件故障并重试 | 首异常不变；finalize 共两次，diagnostics 为 true/false，只产生一次假 sleep |

最后两项直接执行补丁后函数/handler 的 AST，配假 main/guard，不导入完整 runner。FakeGuard 越过两次调用会先 `closed=True` 再抛断言，配合精确调用次数断言限制测试有限退出。它们验证新增证据调用不会在这些宿主故障场景中跳过或替代既有 finalizer；未证明真实 child wait/reap、运行锁、API 恢复或 VM 清理通过。

另有 AST 对照确认：main 的全部既有 finally 块不变；QMP、启动握手、原 API 恢复调用及参数不变；移除新增证据调用后，整个 `execute_runner` AST 与原版相同。该静态检查只能证明这些代码未变，不能代替上表的执行验证或真实运行验收。

首轮 11/12 的失败来自测试 AST 提取器选中了另一处 tuple 异常 handler；已改为精确匹配 `(Exception, KeyboardInterrupt)`。修正后 12/12 通过，随后按协调端要求收紧 FakeGuard 防挂边界再测仍为 12/12；初次失败回执与夹具保留，helper/runner 补丁未因该测试问题修改。

## 固定哈希及下一候选集成

| 对象 | SHA-256 |
| --- | --- |
| 原 r6 runner，验证前后均相同 | `2101edb5eb9c7789faa5c753e206fe315df87307df0695d290a95e718fb4846c` |
| 本 runner 补丁 | `66b48b09a53f2135bb0aa9f47b0fd1b2a0116b171d74516102b0d13f5384f532` |
| 精确应用后的 runner 文本 | `902869ee48c1c80dbe770316d0515ac429a5679beb1af73971dfabf7be041126` |
| helper | `5f133dd0c8f6d17b19cab87616b1efe725445829d75447ac0de71ceb99a083dc` |

集成人需在**下一冻结候选**的 runner 源副本上核对原 SHA，并以 `patch --batch --fuzz=0 -p1` 先 dry-run 后应用本差异，核对补丁后 SHA；不得以此覆盖 r6 或默认入口。把 `host_exception_clock.py` 放在新候选 runner 的同级目录，runner 现有首位 `sys.path` 即可导入；补丁的新增 import 位于 `startup_qmp_v1` import 后。补丁已经把 helper 加入运行时 `observer-source` 快照名单，新冻结包自身的源清单/哈希/预检也须纳入该 helper。

本交付不更新既有冻结清单、状态文件、运行标签或默认入口，也不是完整 r7 运行包；新包组装、冻结、审阅和运行验收均未执行。没有启动 QEMU/VM、操作相机/USB/SD、改 guest 或 FX3 参数、改 QMP 预算或恢复 FX6 工作。

## 官方语义依据

2026-11-04 查询 Python 官方文档；以下 API 适用于本次 Python 3.14.6 离线测试所用调用：aware UTC 使用显式时区；monotonic 是独立的递增时钟，不能直接当作墙上时间；`format_exception` 支持显式异常与 traceback。这些是实现依据，测试结论来自本地回执。[datetime](https://docs.python.org/3.13/library/datetime.html#datetime.datetime.now)、[time.monotonic](https://docs.python.org/3.13/library/time.html#time.monotonic)、[traceback.format_exception](https://docs.python.org/3.13/library/traceback.html#traceback.format_exception)。
