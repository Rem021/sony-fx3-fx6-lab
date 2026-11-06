# 增量串口读取候选（离线，2026-11-03）

## 结果

`incremental-log.patch` 只把 `run_candidate105_v1.py:303` 的每轮全文磁盘读取换为 `SerialSnapshot.poll()`，并把新模块纳入 `observer-source` SHA 清单。旧 runner 源 SHA256：`fdc48f06b4b653fa3c3f2514c98a080f768eaa473aead0e4789ad5464114daca`；`patch --dry-run -p1` 从 Mac 根通过。补丁尚未应用到 runtime；当前运行进程、锁、guest、网页、原串口文件均未接触。供总协调在全新 TRY2 副本审阅集成。

可证明边界是**每次 poll 返回的完整字符串**与 `Path.read_text(errors='replace')` 一致；因此 `run_candidate105_v1.py:304-448` 原有断言、拒绝、开屏计数、输入、媒体、uptime、退出 marker 的全文正则及事件顺序保持原样。模块按 inode、大小与尾部 64B 锚点发现替换/截断/常见原位重写，并按 UTF-8 增量解码和 universal newline 规则处理跨读取块字符；原 `serial.log` 永远只读。`run_candidate105_v1.py:466,479,534-584` 的结束阶段全文分析保留，免得改动验收回执。没有减少原厂 5000ms 或任何生命周期检查。

## 差分和测量

`test_serial_snapshot.py` 在仅位于本目录的临时文件上做旧/新逐字及五类实际 regex 差分，包括：启动无文件、随机 1–17B 分块、跨字节“菜单”、CR/LF、重复 poll、末行无换行、截断、等长原位重写、重写后增长、inode 替换及删除。两份已结束历史日志完整回放且 SHA 固定：

| 日志 | SHA256 | 大小 | 分块 | 差分 |
|---|---|---:|---:|---|
| `ap104light4save1200-2e5d177c/serial.log` | `546cb84e55fe55b57c820a71334d53d43548ab8001b440e99c33c737ceef9845` | 24,687,256B | 19 | 全部一致，包含 `unfetched` |
| `try1-740a3263/serial.log` | `7ea21fead6e939bcbe4581a26502a14b849c4aca97fbe4bc7ff9779b28677863` | 11,196,092B | 20 | 全部一致 |

完整回执是 `measurement.json`。在 24.7MB 固定日志上重复 30 次不增长 poll：旧 `read_text` CPU 约 469ms、累计从文件读 741MB；候选 CPU 约 0.7ms、只读 1920B 尾锚点。1/4/8/16/24.7MB 的五次重复 poll CPU 曲线见 JSON；候选保留整段文本，稳态堆大小随日志线性增长（24.7MB 文件约 24.5MB 文本），**不是**常量内存。测量不含旧正则运行时间、QEMU、guest、UI、保存或退出。

## `trial_log_v2.selected` 的消费语义和未做的改动

`trial_log_v2.py:23,44-47` 的 `selected` 是命中的完整事件行，`poll()` 每轮把其全部 join 成历史视图；`run_trial_v3.py:330-380` 以该历史视图判断原生加载顺序、媒体分支、屏幕开闭、按键上下行与同代完成，`452-453` 还直接 join `selected` 判断 observer-ready。直接截断列表或只返回尾行会漏掉旧事件及改变 `before_AP` / `up_seen` / phaseA 判断，因此没有提交伪装成等价的限长补丁。实测两份固定日志分别有 82 行/约 15KB、28 行/约 5KB 的 selected 堆对象，远低于 candidate105 的 24.7MB 全文；但没有理论上限，仍是开放项。后续若要去掉它，须先给上述每个消费者建立流式事实状态、跨块 regex 匹配与原样事件顺序回放，再用相同历史日志和反例验证。

## 风险与接口

新模块用 64B 锚点检测常见原位重写；若同一 inode 在两次 poll 间被重写为**更长**内容，且旧末尾 64B 恰好仍相同，无法仅凭增量元数据发现更早的改写。`measurement.json` 的 `known_counterexample` 已实际构造该输入并确认新旧快照不等。真实 QEMU `-serial file:` 是追加写入；TRY2 若可能复用或原位重写路径，应先另开新 run 或增加全量校验，不得以本候选声称覆盖该情形。增量解码仍保留全文，并在增长时产生新字符串；该内存成本与现有全文历史搜索同阶。主协调应用时应核对上述源 SHA、重新记录 observer-source SHA，并单独核对运行线的失败 marker、保存和退出回执。
