# FX3 宿主离线优化候选（2026-11-03）

## 结论与边界

本目录只提供一个待集成的宿主帧扫描补丁；未启动 QEMU、未取得运行锁、未请求本地网页或 guest、未改运行链及历史 run。`nonuniform.patch` 可从 Mac 项目根用 `patch --dry-run -p1 < .../host/nonuniform.patch` 预检；总协调审阅后再应用到 TRY2 的新源码副本，不要直接覆盖冻结候选。当前运行、UI、语言/日期保存和退出均**未验收**。

AP104 性能分解见 `runtime/ap104-light1200-performance-v3.md`：失败序 1207 的“领取到释放” 5.286s、释放到首零完成投递 44.712s；这些是含调度、QMP 暂停、绘图、复制、哈希和日志的端点窗口，不能分配为单一后端耗时。此补丁不修改原厂 5000ms 接收预算，也不声称解决该失败。QEMU 官方 [Monitor 文档](https://www.qemu.org/docs/master/system/monitor) 确认 `pmemsave` 是物理内存转储；[QMP 参考](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html) 定义 stop/resume 事件。由此仅可推断频繁转储或暂停值得单独计时，不能从命令次数推定 guest 延迟。沿用主协调已核对的结论：`icount` 不作为多线程性能基线。

## 可应用改动与回执

- 基线源码 SHA256：`osd_ring93_v4.py` `a57101ea4631ed281b8be34c67826f8844112e8bda1dc7ac342a1517de46c0fc`；`trial_ring_v1.py` `31393143a1fecb5eecb6e5d4f0c169f19c8b47b600c6fe2b22120908bed1c230`。
- `nonuniform_candidate.py` 是独立原型。补丁在 `osd_ring93_v4.py` 增加同一函数，并替换该文件与 `trial_ring_v1.py` 的逐像素 Python 切片扫描。扫描只决定 `nonuniform_pixels` 和保留首个非纯色证据；不触碰 `validate_slot`、全帧 FNV、epoch/目标身份、raw/PNG SHA、不可变快照、源 SHA 和 API16 恢复。
- `test_nonuniform.py` 对旧表达式和候选做 3300 组短随机输入逐项行为比较；包括不满 4 字节的尾片段。640×480 RGBA 样本输入 SHA 前后相同，结果见 `measurement.json`。纯色 33.52→0.087ms、末像素变化 31.54→0.079ms（9 次中位数）；首部变化 0.0004→0.0417ms，是已记录的反向案例。候选会短暂分配约一帧大小的比较缓冲；真实 frame 分布、QMP 时间及 guest 增益未知。
- `patch --dry-run -p1` 通过；Python 语法检查通过。测量是宿主合成 RGBA，未验证实机、guest、网页或退出。

## 其余检查与优先级

1. **P0 CPU/日志增长**：`run_candidate105_v1.py:303` 每约 250ms 全量 `read_text` serial，`303-448` 每轮重复全历史正则；`450-453` 每轮启 `ps`。日志越大，宿主开销越高，且没有 `run_trial_v3.py:314-316` 的 480MiB 限额。TRY2 应把检查改为增量且保留跨块匹配、完整失败 marker 与逐步回执；需用固定日志分块回放对比，当前不作未经证明的行为改写。`trial_log_v2.py:27-47` 已增量读原日志，但 `selected` 无界增长并每次 join，不可原样当常量成本替代品。
2. **P1 全帧/QMP**：`osd_ring93_v4.py:28-38` 新序列时读 `TOTAL=0xc10000`（约 12MiB）再拆 8 槽；`run_candidate105_v1.py:458-465` 周期和终态调用。`trial_ring_v1.py:44-61` 已采用 256B 头 + 单个 1.5MiB 槽和 FNV，但语义仅“最新提交帧”，不能直接替代需要所有可见槽的候选105记录。先采 QMP 转储耗时与漏帧率，再决定接口。
3. **P1 暂停/退出**：`run_trial_v3.py:324-328` 每 60s stop/转储/cont；`run_candidate105_v1.py:317-318` 每 20s 也做一次。原厂 5000ms 窗口附近的暂停可能影响端点时间，需同一时钟量出每次 stop→cont。`run_trial_v3.py:436-499` 覆盖正常、Ctrl-C 与异常的恢复/退出，但 `486-492` 的 poll→killpg 有退出竞态；`run_candidate105_v1.py:508-526` 同样。不可为省时跳过 `restore_api103_v2.py:16-42` 的 ack、原 16B 和停机检查。
4. **P2 网页与输入**：`trial_web_v2.py:116-124` 400ms 状态轮询，帧变化才下载 PNG；`run_trial_v3.py:321-323` 400ms ring 轮询。网页最坏额外等待由两个轮询和编码构成，需实测请求/帧时戳；单纯降低间隔会增加 CPU/QMP。`trial_web_v2.py:57-78` 的 `busy/pending` 限单键，`run_trial_v3.py:398-419` 发键前再次检查 stop 与日志；`/api/stop` 在 `trial_web_v2.py:190-192` 设置 stop 但不清 pending，收尾只在主循环处理，可考虑显式清队列并记录取消状态。`run_trial_v3.py:234-295,354-370` 网页先起、phaseA 和原始读回满足后才 ready，顺序合理；不要提前显示 ready。浏览器对象 URL 在 `trial_web_v2.py:120` 正常换帧时释放，结束时最后一个 URL 待页面关闭释放。

## TRY2 接口

运行链工人只需接收 `nonuniform.patch` 与 `measurement.json`；总协调决定是否把两处替换加入全新 TRY2 runner 源副本。应用前核对上列两个源码 SHA，应用后重算 observer-source SHA 清单并做 host 对照；若使用 `run_trial_v3.py`，其 `observer_sources` 已包含两文件（第 147-149 行），不得沿用旧 SHA。运行验收仍须独立记录帧/输入、原生完成时间、保存回读、API16 与退出锁；宿主测试不能填写这些栏位。
