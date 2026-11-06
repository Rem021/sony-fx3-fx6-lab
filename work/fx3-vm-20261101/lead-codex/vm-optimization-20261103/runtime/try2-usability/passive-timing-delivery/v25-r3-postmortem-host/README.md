# v25-r3 故障后 host 诊断候选（未运行）

从冻结 `v25-menu-osd-diagnostic-r3/` 派生的独立 host 候选。`run_trial_v25_diag_r3.py` 明确指向原候选 manifest，SHA256 `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`，其 CPIO/DTB/Backup 均由原 manifest 的哈希门核验；没有构建新 guest，也没有 QEMU 授权或运行。原文件未修改，差异在 `r3-to-postmortem-host.diff`，本目录哈希见 `SHA256.json`。

针对实跑第 16 键的第一项 host 误判，`native_input_deadline_error` 现在区分：原生 down 未见、down 已见但发键线程 up 完成未见、sender 完成而原生接收不全。12 秒有界门、单次发键、100ms、白名单、健康故障停止均未放松。此改动只是错误分类，不能修复 guest 停滞。

针对故障后的证据不足，原有清理 `capture_quiesced_diag` 在 QMP 已确认 `paused/running=false` 后，在保存 16MiB OSD 环之前额外读取 `query-cpus-fast` 和 HMP `info registers -a`；只在有 `early_stop_reason` 时触发。原始响应保存到 `fault-vcpu-paused.json`，`capture_complete` 明示是否实际取得 CPU 列表与非空寄存器文本；不凭 vCPU PC 推断 guest TID、信号或锁。原有 API16 guest ack/原字核验、QEMU quit/reap、双锁和输入哈希门仍在。QMP 命令如不受支持会留下错误响应；此候选尚未做真实 QMP 验证，不能默认快照成功。

定向离线验证：

- `python3 test_input_deadline_classification.py`：边界 12 秒、未见 down、仅见 down、sender up 但原生不全、完整证据；通过。
- `python3 test_quiesced_diag_readback.py`：暂停确认、CPU/寄存器原始回执、全环大小与解析、重复文件拒绝、活态拒绝；通过。
- `python3 -m py_compile run_trial_v25_diag_r3.py quiesced_diag_readback.py` 与 `--help`：通过；没有启动 guest。

下一轮若获得授权，先保持浏览器逐键逐图。首次 ACK 异常时停止按键并读取本候选的 vCPU 原始快照；同时需要可识别的 **当时** guest 线程状态，才能在 KEY96 TID343、FILE100 PID148 与 OSD/原生线程间确定同步点。当前 `restore_seen=0` 仍无法区分未读控制字、Backup 双读阻塞、进入 shutdown shell 后未返回三种情形。不要依据本候选提升默认入口、宣称已修复卡顿或修改 guest 超时。
