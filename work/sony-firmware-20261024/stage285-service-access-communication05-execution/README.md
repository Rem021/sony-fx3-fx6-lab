# Stage 285 — FX3 受限 SERVICE 访问通信 05 真机全闭环完成（`COMPLETE`）

## 结论先行
- **全流程真机闭环打通（`HOST_RETURN_CONTROLLED_PORT_ASSOCIATION` / `COMPLETE`）**：在用户手动推出挂载卷并单次批准 `fx3-702-service-access-communication-20261101-05` 后，Sony ILME-FX3（固件 v7.02，机身 USB 连接模式固定为 Mass Storage）完成了从 **MSC 7 轮认证 $\to$ 物理端口受控关联切换至 `SERVICE`（`054C:0336`） $\to$ 独占设备打开与 7 轮认证 $\to$ 固定 `read0` 12B 请求 $\to$ 12B 响应头（`version = 3, reason = 1 ok`） $\to$ 88B 响应体（`body_hmac = 95254273...`） $\to$ `STOP`（`0336:7`）与对象释放（`0336:8`） $\to$ 同物理端口、同位置、同串号 HMAC 的 `054C:0DA1`（`ILME-FX3` MSC）自动重枚举归还 $\to$ `0da1:9` 驱动释放请求（`status = 0`） $\to$ `FX3_OP_FLOW_COMPLETE`（第 124 帧） $\to$ 全局根日志追加 `CLEAN` $\to$ root helper 与观察器全部正常退出（`native_return = 0, helper_terminal_observed = true`）** 的完整闭环！
- **无需主机收尾**：独立内核 PID 探测确认 root helper（`PID = 97419`）与观察器（`PID = 97367`）均已正常退出（`{"97419": null, "97367": null}`），`global-fx3-owner.journal` 已写入正常 `CLEAN` 终态（`global_guard_result = 0, owner_retained = 0`）。
- **独立 Mac IORegistry 缓存已恢复 MSC 驱动与存储卷**：回读确认同物理端口（`4294968654`、`locationID = 0x01100000`）已恢复唯一 `054C:0DA1`（`ILME-FX3`，`registryID = 4296580734`，内存同机 HMAC 一致），且 `IOUSBMassStorageDriver` / `IOBlockStorageDriver` 驱动链及 `disk10` / `disk10s1` 已自动重新挂载。

---

## 1. 关键里程碑与 124 帧流水（[`actual-runtime-review.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/actual-runtime-review.json)）
1. **恢复准入与身份核验（[`verified-helper.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/verified-helper.json) / [`live-self-image.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/live-self-image.json)）**：
   - `helper PID = 97419`（`uid = 0`，`birth = 1793550788.789715`），自读映像 SHA256 `9fafccf36203a451f39246f83da37806e113078b709fb25156c3bf74e4e9043d` 与 Stage 284 封板一致；
   - `manual_recovery`：`stage = 2`（`before_count = 11`，`prior_tail_hash = a0bc40aa...`，`recovered_hash = 0dc52556...`）。
2. **MSC（`054C:0DA1`，`source_node = 4296570640`）7 轮握手与释放**：
   - 完成 `START` 控制传输、7 轮 Bulk OUT/IN 挑战响应与对象释放，进入 `SERVICE` 过渡轮询窗口。
3. **SERVICE（`054C:0336`，`service_node = 4296580674`）独占打开、7 轮认证与 88B `read0`**：
   - 设备与接口独占打开成功（`device_open_disposition = 1, raw_return = 0, step = 114 pipe_4`）；
   - 完成 `START` 与 7 轮认证；
   - 第 77 帧（`flow-0076.bin`，`op = 4`）：12B `read0` 请求返回 `status = 0`；
   - 第 79 帧（`flow-0078.bin`，`op = 5`）：12B 响应头返回 `status = 0, count = 12, reason = 1 ("ok")`；
   - 第 81 帧（`flow-0080.bin`，`op = 6`）：88B 响应体返回 `status = 0, count = 88`，`body_hmac = 9525427324dae85ee8de0a04ddfbe091a8c66f73d80a6291d822e749c91a439a`；
   - 第 83 帧（`flow-0082.bin`，`op = 7`）：`STOP` 返回 `status = 3`（`0xe000404f` STALL 确认）；
   - 第 85 帧（`flow-0084.bin`，`op = 8`）：`SERVICE` 对象释放返回 `status = 0, raw_return = 0`。
4. **STOP 后同口 MSC 自动归还与驱动释放（第 86–124 帧）**：
   - 第 86 帧（`flow-0085.bin`，`op = 62`）：启动返回窗口（`FX3_W_RETURN_ARMED`）；
   - 第 87–88 帧：2 次 `054C:0336` `BUSY`；第 89–119 帧：31 次 `GONE`；
   - 第 120 帧（`flow-0119.bin`，`op = 63`）：同物理端口（`4294968654`）、同位置（`0x01100000`）、同串号 HMAC 的全新 `054C:0DA1` 节点（`return_node = 4296580719`）重枚举就绪（`status = 0`）；
   - 第 121 帧（`flow-0120.bin`，`op = 41`）：记录 `FX3_OP_ASSOCIATED_MSC_RETURN`；
   - 第 122–123 帧（`flow-0121.bin` / `flow-0122.bin`，`op = 9`）：调用 `0da1:9`（`USBDeviceReEnumerate(kUSBReEnumerateReleaseDeviceMask)`）归还系统驱动，返回 `status = 0, raw_return = 0`；
   - 第 124 帧（`flow-0123.bin`，`op = 50`）：记录 `FX3_OP_FLOW_COMPLETE`。

---

## 2. 私有终态回执与独立缓存核验
- [`private-record.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/private-record.json)：`phase = "COMPLETE"`，`native_return = 0`，`global_guard_result = 0`，`owner_retained = 0`，`cleanup_error = 0`，`clock_invalid = 0`。
- [`live-final-summary.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/live-final-summary.json)：`status = "HOST_RETURN_CONTROLLED_PORT_ASSOCIATION"`，`helper_terminal_observed = true`，`bounded_service_read_observed = true`。
- [`post-return-MSC-cache.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage285-service-access-communication05-execution/post-return-MSC-cache.json)：同口 `054C:0DA1`（`registryID = 4296580734`）与 `IOUSBMassStorageDriver`、`disk10s1` 均已恢复。
