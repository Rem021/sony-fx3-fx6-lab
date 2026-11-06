# 通信04仅主机收尾实际结果（`fx3-host-cleanup-20261101-04-r2`）

- **终态**：`HOST_CLEANUP_COMPLETE_ORIGINAL_COMMUNICATION04_REMAINS_UNKNOWN`
- **原根助手 `PID 37860`**：通过内核 `audit_token_t` 发送一次 `SIGKILL(9)` 后已退出（`helper_absent = 1`，独立探测 `37860 = None`）。
- **原观察器 `PID 36633`**：收尾前已自行退出，复核未发送信号且保持不存在（`observer_signal = 0, observer_absent = 1`，独立探测 `36633 = None`）。
- **全局根日志**：`/private/var/root/fx3-owner-trials/global-fx3-owner.journal` 字节与 SHA256 完全未变（`old_guard_bytes_unchanged = True`）。
- **相机与 USB**：0 次 USB 请求、0 次固件写入，收尾前后 Sony 缓存节点均为 `[]`；原通信 04 的 95 帧私有流与 `HELD`/`UNKNOWN` 状态原样保留。
