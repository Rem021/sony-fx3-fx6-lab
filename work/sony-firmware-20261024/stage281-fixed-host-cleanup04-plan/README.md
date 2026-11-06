# 通信04保留主机实例的单次收尾方案（`fx3-host-cleanup-20261101-04`）

本方案只处理 Mac 上的通信04保留根助手 `PID 37860`（出生时间 `1793546568.487337`）与观察器 `PID 36633`（出生时间 `1793546063.372013`，已自行退出）。**已编译并核对，尚未批准、暂存或启动。** 用户已确认拔下 USB 前相机显示“选择USB连接模式”菜单（对应 `STOP` 后重枚举的 `054C:096F` `USB Bus-powered Device`），拔下全部 USB 线后纯电池供电下拍摄界面和菜单一切正常；独立缓存核对当前无任何 Sony USB 节点（`sony_candidates_count = 0`）。整个收尾期间保持 USB 断开，本程序不调用任何 USB/IOKit 接口。

## 固定操作与范围

- **授权标识（Grant ID）**：`fx3-host-cleanup-20261101-04`
- **最大管理员调用次数**：`1`（必要时在 Terminal 完成一次 `sudo` / Touch ID 验证）
- **绑定目标**：
  1. 原根助手：`UID 0`、`PID 37860`、出生时间 `1793546568.487337`、路径 `/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-04/helper`、映像 SHA256 `32ad51d0d111b0318f28d6e92fe0df5d0c018f256683ad35624043a8f476150c`。
  2. 原观察器：`UID 501`、`PID 36633`、出生时间 `1793546063.372013`、Python 路径与映像 SHA256 `104402c76823baa218defcdb2a96c2e3d94302dd12cabf0db3c1f39cd620cb64`（当前已退出，`fx3_host_same_process == 0`，程序仅核对并记录 `observer_absent = 1, observer_signal = 0`，不向已退出或复用的 PID 发送任何信号）。
- **执行动作**：
  1. 只用 `task_name_for_pid` 读取原根助手的内核 `audit_token_t` 并核对 PID 版本与路径。
  2. 只读核对 `/private/var/root/fx3-owner-trials/global-fx3-owner.journal` 尾部确属 `PID 37860`（`1793546568.487337`）。
  3. 仅向匹配的 `PID 37860` audit token 发送一次 `SIGKILL(9)` 并等待其退出（最多约 2 秒）。
  4. 复核 `PID 36633` 已退出（`observer_absent == 1`）且根日志字节与摘要完全未变，写出 `/private/var/root/fx3-host-cleanup-20261101-04/result.json`。
- **实际清理程序 SHA256**：`db39253a9e1edc3a6c759264afd78d55c251d842b4b3fbf4b6f51a18d0fdfb27`
- **固定文件**：[`fixed-plan.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage281-fixed-host-cleanup04-plan/fixed-plan.json) · [`build-and-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage281-fixed-host-cleanup04-plan/build-and-check.json) · [`approval-bundle.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage281-fixed-host-cleanup04-plan/approval-bundle.json)
