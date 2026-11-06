# save1800 宿主性能关联分析（离线，2026-11-03）

## 结论

原始 81,321,567B `serial.log` 的 SHA256 为 `54dd1237d678dfd5aa2cd03d0b087a5a45a438d69ab63c7365c587a6272270ec`。两次 >5000ms 都是 **GPE module=0x82 动态 QID 分配返回至显式完成返回的 user `ns` 上界**，各有成功完成和释放；它们不是原厂 `ReceiveDrawComp` 入口到返回的直接计时。原 kernel 随后在 QID `0x808261c0` 报 `free_dynamic_msgq_id` 错误，再有 OSD allocation deadline 诊断；host 改动不能被宣称修复这两件事。未修改原日志、runner、guest、锁或 QEMU。

| seq / QID | alloc→SendDrawComp 进入 | 函数进入→成功返回 | alloc→成功返回上界 | 完成返回→CMD 返回 |
|---|---:|---:|---:|---:|
| 6329 / `0x808261c1` | 4985.761ms | 36.112ms | **5021.873ms** | 35.473ms |
| 7545 / `0x808261c0` | 5634.021ms | 16.978ms | **5650.999ms** | 5.644ms |

同一 user `ns` 的起止值和 QMP 请求列于 `intervals.json`；脚本 `analyze_intervals.py` 可由固定日志复算。`seq6329` alloc event1379 是原日志行 515395，完成 enter/return 是 517426/517431；`seq7545` alloc event1439 是 607292，完成 enter/return 是 608050/608051。原 kernel 错误在 608068，使用独立 printk `[38320.919593]` 时间域；**不能**拿它减 user `ns` 或 host QMP elapsed。两个窗口内有别的 guest 命令/线程，producer、领取、backend 分段和 life 锁等待没有完整同钟记录，因此余下约 4.99/5.63 秒不能直接归给任一组件。

## 宿主操作的相关性

`vmopt-20261103-run_candidate105-save1800.py:306-453` 每轮全文读取 serial、执行历史 regex，且每轮启动 `ps`；`348-401` 的截图/状态请求会 stop、读 ring、cont；`460-463` 周期 ring 轮询。`ap101-host-input-gate.json` 的 host monotonic 与 `FX3_SYNTH_KEY status=1` 的 user `ns` 按相邻步骤插值，再以 step19 输入前 QMP stop 锚定 host elapsed，估得 seq6329 的 host 窗口约 1013.417–1018.508s，seq7545 约 1246.645–1252.385s。这个映射含 guest/host 输入延迟与虚拟时间漂移，**不是共同硬件时钟或精确因果配对**。

- seq6329 的估计窗口内，QMP `stop` 1017.483→`cont` 1018.110s，期间读 ring 和 date-row-late3 证据，host 停顿上界约 0.627s。它与 5.022s 窗口相邻/重叠，但不足以解释全部时间。
- seq7545 的估计窗口内，QMP `stop` 1247.263→`cont` 1247.266s（输入），随后 1247.570–1247.572s 读 ring 头和全 ring；停止约 3.6ms。原 kernel `free_dynamic_msgq_id` 在完成后出现，不能从这些宿主动作推出起因。
- `receipt.json` 记录 607 个 `ps` 样本，代码实际是每轮执行而非低频定时。离线对自身 PID 做 50 次同式 `ps`，父进程 CPU 39.7ms、wall 125.6ms（约 2.5ms/次）；这是不同负载上的 host 测量，不是运行当时的精确耗时。

## 固定真实日志的隔离基准

`bench_save1800.py` 和 `bench_boundaries.py` 均先校验完整日志 SHA，模拟 runner 的串口谓词，不连接 guest。`bench.json` 是整份 81.3MB 文件的一次完整实际谓词扫描及一次无增长重复读，不是历史 607 次轮询的重放；历史没有每次 poll 的串口偏移与 host CPU 回执，**无法从现有证据计算整轮真实 CPU 总和或实际读取总字节**。若这 607 个 `ps` 样本逐一对应主循环，且日志单调增长，全文读取的数学上界是 607×81,321,567B≈49.36GB；这只是上界，不能当实际 I/O 回执。

| 输入 | 旧全文 `read_text` 重复读取 | 已有增量候选重复 poll | 原实际谓词集 | 仅两条原 `re.I` 拒绝检查 | 新保守预检 + 原 regex 兜底 |
|---|---:|---:|---:|---:|---:|
| 完整 81.3MB | 60.7ms / 81.3MB | 0.15ms / 64B 尾锚点 | 4297ms | 3820ms | 251ms |
| seq6329 末 62.3MB 前缀 | — | — | 3424ms | 2937ms | 192ms |
| seq7545 末 73.2MB 前缀 | — | — | 4010ms | 3454ms | 228ms |

首读增量候选约 216ms，旧读约 63ms；它靠后续重复 poll 才获益，**不削减原 regex**（新旧实际谓词集分别约 4318/4297ms，结果逐项相等）。全文解码约 80,644,240 字符、稳态 Python 字符串约 80.6MB；增量候选仍保留全文，`guarded_rejects` 的 casefold 临时串可能再占约 80.6MB。此处 CPU 数值是离线单进程条件下的 `process_time`，不能直接填入 guest 5 秒预算或推断 QEMU vCPU 的调度行为。

两个先前已验证的 host 候选分别是 `host/nonuniform.patch` 和 `host/incremental-log/incremental-log.patch`。前者在这轮三个真实 raw 帧转 RGBA 后，每 200 次扫描从约 66–101ms 降至 5.6–6.2ms，即**每帧约 0.3–0.48ms**；保留 FNV/SHA/像素内容，收益远小于数秒窗口。后者消除重复串口 I/O，但不消除上述 regex；仍有前次报告的同 inode 保留尾锚点原位重写反例。二者均未集成这次 run。

## 可应用的最小补丁与条件

`guarded-reject.patch` 针对已结束的 save1800 runner SHA `44744a93ba2c8811fd8fe6a986c3d89ec8212cec117ad96051418e2cc1f68365`，仅为两条高成本大小写不敏感拒绝 regex 加快速**否定**预检；任何可能命中的内容仍交给原 regex 判定，检测顺序和原错误理由不变。`guarded_reject.py` 是独立测试原型，补丁内联同一函数进 runner，runner 自身已在 observer-source 快照中。`test_guarded_reject.py` 的 5000 个随机/注入 Unicode 例及本轮/AP104-light 两份固定 SHA 日志的 10%/50%/100% 前缀旧新结果相等；`patch --dry-run -p1` 通过。运行 owner 应只在**新 TRY2 副本**上审阅/应用并更新源码 SHA，保留现有拒绝门、保存与退出回执，先做离线完整谓词和负例对照，再做有界 guest 验收。

即使 host CPU 扫描与两个上界在时间上相关，当前证据仍不能证明它造成原厂 deadline、QID 释放错误或 OSD 诊断。下一步要因果判断，需在新 run 同时记录 host 每轮读取/正则/截图/ps 的起止 host monotonic、guest GPE alloc/complete 同源 `ns`，以及可对齐的 host/guest 锚点；所有原厂 5000ms、生命周期、API16 与失败检测必须保持。
