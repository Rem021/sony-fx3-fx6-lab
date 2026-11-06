# Stage 283: `STOP` 后 `054C:096F`（`USB Bus-powered Device`）返回过渡离线兼容

## 1. 背景与解决的问题
在通信 04（[`stage280-service-access-communication04-execution`](../stage280-service-access-communication04-execution/README.md)）真机运行中，`MSC (054C:0DA1)` 7 轮认证、`SERVICE (054C:0336)` 独占打开与 7 轮认证、`read0` 12B 请求、12B 响应头（`version = 3`，`reason = 1 ok`）、88B 响应体读取（`body_bytes = 88`）、`STOP`（`0336:7`）及 `SERVICE` 对象释放（`0336:8`）全部通过；随后相机退回普通拍摄系统并弹出“选择USB连接模式”菜单（重枚举为同物理端口、同机身串号 HMAC 的 `054C:096F` `USB Bus-powered Device`）。

此前 `iokit_adapter.c`、`transition_identity.c` 与 `flow_receiver.py` 在 `STOP` 后返回窗口（`mode = 1` / `FX3_W_RETURN_ARMED`）仅把 `054C:0336` 视为 `FX3T_BUSY`（`2`），遇到 `054C:096F` 时立即在第 1 个非空轮询样本返回 `FX3T_DENIED`（`1`）并中断等待窗口进入 `HELD`。

## 2. 本阶段离线升级内容
1. **[`iokit_adapter.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/iokit_adapter.c)**：
   - 在 `identity()` 与 `find_at(..., pid=0, ...)`（仅用于过渡轮询快照 `fx3_usb_transition_snapshot`）中允许识别 `054C:096F`（要求非空 `USB Serial Number` 计算出 `FX3_ID_SERIAL` HMAC 标签，且产品名匹配 `"USB Bus-powered Device"`）。
   - 初始 MSC 缓存绑定（`fx3_usb_cached_identity`）与最终驱动归还（`fx3_usb_request_driver_return`）仍严格要求 `054C:0DA1`。
2. **[`transition_identity.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/transition_identity.c)**：
   - 在 `mode == 1`（`FX3_W_RETURN_ARMED`，`STOP` 后返回等待窗口）中，若观测到 `054C:096F` 且满足：同一 `physical_port`、同一 `initial_location`、全新 `registry_id`（`!= source_node && != service_node`）以及与初始 MSC 完全一致的 `origin_serial_tag` HMAC，则返回 **`FX3T_BUSY`（`2`）** 继续轮询等待 `054C:0DA1` 就绪；任何串号不符、位置不符、端口不符、节点复用或在 `mode == 2`（进入 `SERVICE` 窗口）出现的 `054C:096F` 均立即返回 `FX3T_DENIED`（`1`）。
3. **[`flow_receiver.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/flow_receiver.py)**：
   - 在 `state == 4`（`FX3_W_RETURN_ARMED`）下接受通过同机串号 HMAC、同位置、同物理锚点校验的 `054C:096F` `FX3T_BUSY` 轮询帧（以及窗口耗尽时的 `op = 51` `HELD` 终态帧），并拒绝任何将 `054C:096F` 作为 I/O 调用主体（`point in (0, 1)`）或伪造状态的帧。

## 3. 验证结果（0 次管理员/USB 调用，native 入口保持关闭）
- [`component-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/component-check.json)：12 例组件级检查全部通过。
- [`test-receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/test-receipt.json)：8 组人工恢复准入与全流程 IPC 检查通过。
- [`acquisition-integration-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/acquisition-integration-check.json)：5 组获取失败分类检查通过。
- [`shared-access-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/shared-access-check.json)：4 组受限共享控制检查通过。
- [`header-localization-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/header-localization-check.json)：11 组 `read0` 响应头失败定位检查通过。
- [`post-stop-096f-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage283-post-stop-096f-transition-compatibility/post-stop-096f-check.json)：5 组 `054C:096F` 专项检查（C 单元、`096F -> 0DA1` 完整 `COMPLETE` 闭环、错串号 `096F` 拒绝 `HELD`、持续菜单等待 50 样耗尽 `HELD`、6 种帧伪造拒绝）全部通过。
