# FX3 7.02 显示契约（v2）与 UPM/MSS/按键省电活动契约静态取证报告

## 1. 核心结论（Conclusion First）

1. **特殊 20B 消息（`01001500 01000000 05000000 00000000 00000000`，`source = 0x00830128` -> `dst = 0x005503e0`，调用返回点 `0x16f12ec`）的确切身份已由原件指令与 `.rodata` 符号字符串（[`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) `VA 0x2f9e978`）100% 证明［`STATIC_ORIGINAL_CODE`］**：
   - 发送函数 `0x16f11e8..0x16f1354`（`App` vtable `0x41cc480` slot `+0x28 = 0x41cc4a8`）为 **`virtual void App::got_display_update_event(const ds_display_update_event&)`**（对应源文件 `000_main/app.cpp` `VA 0x2f9e8b0`）。
   - 在 `App` 主队列 `0x005503e0` 消费分类器（`0x16f3750..0x16f3900`）中，`0x0015xxxx`（如 `0x00150001`）被归类为类型 `5`（`0x16f38c8: mov w0, #0x5; str w0, [x19, #0x8]`），作为内部 UI 显示更新通知分发，**不直接调用 `0x2eaf294` 或向 UPM MSS 队列 `0x80924220` 发送复位命令**。
2. **[`upm.ko`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko) 的 MSS 队列（`QID = 0x80924220`，消费分发 `.text+0x2180..0x2720`）与 `OFF_BY_APO1`（`k_upm_mss_apo_cb` `.text+0x0730..0x081c`）全状态机已完整反汇编证明［`STATIC_ORIGINAL_CODE`］**：
   - **多级请求级联定时（`k_mss_timer_cb` `.text+0x1670..0x1714`）**：当当前最小 `timeout_sec` 请求到期时，回调将 `mss_state.elapsed_sec`（`[x19+0x48]`）更新为 `active_req->timeout_sec`（`0x16a8..0x16b0`），对所有等于该超时值的请求置 `[req+0x18] = 3`（`EXPIRED`）并广播 `0x00920205`（`k_mss_fire_all_expired_nr` `.text+0x0828`）；随后**立即在 `0x16b8` 调用 `k_mss_find_min_request`（`.text+0x1558`）查找下一个未到期（`[req+0x18] != 3`）的最小请求，并在 `0x16c8` 调用 `k_mss_start_timer_nr`（`.text+0x1008`）按差值 `(next_req->timeout_sec - elapsed_sec) * 1,000,000 us` 启动下一阶段定时器**。
   - **APO1（`req_id = 2`，`5 Min = 300s`）触发条件**：当 `0x00920205` 的 `word1 & 0xfff == 2` 时，`k_upm_mss_apo_cb`（`.text+0x0730`）检查 `[mss_state+0x50] == 0` 且（`word1 == 2` 无 `deco/fakey` 标志，或 `[mss_state+0x54] != 0 && deco_list == NULL`），向 `0x80920021` 发送 16B `[0x00920141, 0x8, 0x1a, 0x21]`（`0x07f0..0x0800`），进而触发 `UPM_CMD_OFF`（`0x00920143`, `Prm1 = 0x08`），经 [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) `upm2model_convert_shutdown_factor`（`VA 0x41172f8` / 文件偏移 `0x41072f8` 第 17 项：`upm=0x08 -> model=0x11` `OFF_BY_APO1`）生成 `52000000 11000000 02000000` 并发送 `ds_event = 0x0003002c` 打开 `scr0039_shutdown`（`0x2af`）。
   - **可启动/停止/复位 MSS 定时器的全部 5 类 `0x80924220` 命令**：
     1. `0x00920204`（`MSS_reload_timer`）：`status == 2` 时调用 `k_mss_reload_timer_nr`（`.text+0x1608`，清零 `elapsed_sec`、重置所有请求状态为 `1` 并按最小请求重开定时器）；`status == 1` 且 `stopper_list == NULL` 时转入 `status = 2` 并启动定时器。
     2. `0x00920206`（`MSS_fakey_start/stop`）：在 `.text+0x23d0..0x2400` 更新 `deco_list` 后，**原位将 `[x19]` 改写为 `0x00920204`（`0x23f0..0x2400: mov w1, #0x920204; str w1, [x19]`）并跳回 `0x21c8` 执行完整 `0x00920204` 重载路径**。
     3. `0x00920203`（`MSS_add_stopper`）：`status == 2` 时调用 `k_mss_stop_timer_nr`（`.text+0x1110`），清零 `elapsed_sec`，置 `status = 1`（`STOPPED`）并挂入 `stopper_list`。
     4. `0x00920202`（`MSS_del_stopper`）：`status == 1` 时从 `stopper_list` 移除节点（`.text+0x1990`）；**若 `stopper_list`（`[x20+0x40]`）变为空，立即跳至 `.text+0x2468` 重置所有请求状态为 `1`、清零 `elapsed_sec`、置 `status = 2`，并在 `.text+0x2490` 调用 `k_mss_start_timer_nr` 重新启动完整 300s 周期并广播 `0x00920204`**。
     5. `0x00920118` / `0x00920119`（`MSS_add_request` / `MSS_del_request`）：`status == 2` 时分别在 `.text+0x2628` 调用 `k_mss_reload_timer_nr` 或在 `.text+0x26bc` 重启定时器。
3. **为什么 `v7` 被动探针（[`fx3-media-observe-v7-mss-safe.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/src/fx3-media-observe-v7-mss-safe.c)）未捕获按键期间的 MSS 活动，以及最小下一步只读观测契约**：
   - 在 [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中，全部 **37 处**向 `0x80924220` 发包的调用点（1 处 `0x00920204`、15 处 `0x00920202`、8 处 `0x00920203`、5 处 `0x00920206`、8 处 `0x00920118`/`0x00920119`）均汇聚于公共发送函数 **`0x2eaf294`**。
   - 但 [`fx3-media-observe-v7-mss-safe.c:23`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/src/fx3-media-observe-v7-mss-safe.c#L23) 写为 `mss_pending=((W)r[0]==0x80924220U&&(W)r[1]==0x00920204U);`，直接丢弃了其余 **36 处**非 `0x00920204` 的 `0x80924220` 调包（如打开/退出菜单或子页面可能触发的 `0x00920203` `add_stopper` / `0x00920202` `del_stopper` / `0x00920206` `fakey` / `0x00920118` `add_request`），且未观测 `upm.ko` 内部 7 处直发 `0x80924220` 的调用点（`.text+0x0f04, 0x614c, 0x69f4, 0x6acc, 0x7164, 0x88c4, 0xa2d0, 0xaa44`）。
   - 同时，在 `0x2eaf294..0x2eaf340` 原件指令中，`0x2eaf2fc..0x2eaf300`（`stp w22, w24, [x8]; stp w21, w20, [x8, #0x8]`）写入的 16B 消息内容在 **`0x2eaf294` 入口寄存器中已完整具备**（`w0 = qid`, `w1 = cmd`, `w6 = src_id`, `w2 = word2`, `w3 = word3`），而 `0x2eaf33c`（`osal_free_msg`）位于 `0x2eaf308`（`cmp w0, #0`）之后。
   - **最小只读观测动作（不注入 `0x00920204`、不改超时或 Backup）**：仅将 `0x2eaf294` 的过滤条件从 `(W)r[0]==0x80924220U && (W)r[1]==0x00920204U` 放宽为 `(W)r[0]==0x80924220U`（直接记录入口寄存器 `[w1, w6, w2, w3]` 构成的 16B 载荷），即可在一次只读运行中完整捕获 `MENU`、`LEFT`、`DOWN` 期间所有 `appFw.so -> 0x80924220` 的 `stopper`/`fakey`/`request`/`reload` 发送事件。
4. **显示契约 v2（[`verify_display_contract_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v2.py)）已完成四级证据分层与边界收窄**：
   - 保留全部 v1 文件（[`README-v1.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/README-v1.md)、[`verify_display_contract.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract.py)、[`display-contract-evidence.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence.json)、[`display-contract-fixture.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture.json)）。
   - 生成 [`display-contract-evidence-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence-v2.json) 与 [`display-contract-fixture-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture-v2.json)，明确区分 `STATIC_ORIGINAL_CODE`、`RUNTIME_LOG_MEASURED`、`BOUNDED_INFERENCE` 与 `MODEL_ASSUMPTION`。

---

## 2. 四级证据分类与 v2 关键修正摘要

| 条目 | 证据等级 | 精确边界说明与原件偏移 |
| :--- | :--- | :--- |
| `libObj.so` `FrameBuffer::swap` (`0xf33d0`) | `STATIC_ORIGINAL_CODE` | `0xf33ec: ldp x0, x1, [x19, #0x60]` + `0xf33f0: stp x1, x0, [x19, #0x60]` 是对 `on_entry`（`fb+0x60`）与 `off_entry`（`fb+0x68`）的**两条指令非原子寄存器交换**，不能表述为单指令原子交换。 |
| `libObj.so` `FrameBuffer::initialize` (`0xf30ac..0xf3198`) vs `token=0x401/0x402` | `STATIC_ORIGINAL_CODE` vs `RUNTIME_LOG_MEASURED` | 原件静态常量仅为 DMM 池类型 `0x403`（`0xf30dc: mov w2, #0x403`）及槽位偏移 `fb+0x18`、`fb+0x38`；具体句柄 `0x401`（`0x43ae96100`）与 `0x402`（`0x43feb5100`）属于运行日志实测值（`RUNTIME_LOG_MEASURED`），非 `libObj.so` 硬编码常量。 |
| `av-cam.bin` `SetCpWidgetInfo` (`0x2ee2dc`) & `SetOutputDeviceInfo` (`0x2ee40c`) | `STATIC_ORIGINAL_CODE` vs `MODEL_ASSUMPTION` | `0x2ee310: ldrh w8, [x19, #0x8]; 0x2ee314: cmp x8, #0x100; 0x2ee318: b.hs 0xffffffc0012ee3b0`（`w < 256`）与 `0x2ee41c: ldr w8, [x1, #0xc]; 0x2ee420: cmp w8, #0x10; 0x2ee428: b.hi 0xffffffc0012ee458`（`hide_count <= 16`）为原件分支检查；而 Python fixture 中对 `attr_count <= 16` 的防御性限制及单状态变量 `pending_sub_op` 建模属于 `MODEL_ASSUMPTION`。 |
| `appFw.so` `0x2eaf294..0x2eaf340` 发送与释放顺序 | `STATIC_ORIGINAL_CODE` | `0x2eaf2fc..0x2eaf300` 写入 16B 消息，`0x2eaf304` 调用 `osal_snd_sync_msg`，`0x2eaf308` 检查返回值，`0x2eaf33c` 才调用 `osal_free_msg`；且入口寄存器 `[w1, w6, w2, w3]` 已完整包含该 16B 消息的 4 个 32 位字。 |

---

## 3. UPM / MSS / 按键输入链路完整静态契约表

### 3.1 `appFw.so` `App` 主事件队列 `QID = 0x005503e0` 的 4 个发送入口（`000_main/app.cpp`）

| 函数 VA | 符号名（`.rodata` 字符串偏移） | 消息大小 | `source` | 作用与下游去向 |
| :--- | :--- | :--- | :--- | :--- |
| `0x16f0fc0` | `void App::input_infra_callback(int, InfraInputEvent*)` (`0x2f9e8f0`) | `32B (0x20)` | `0x00830128` | 将 `libObj.so` `0xc8f50`（`infra_input_res`）回调送来的按键事件封装为 32B 发往 `0x005503e0`（分类为类型 `1`）。 |
| `0x16f11e8` | `virtual void App::got_display_update_event(const ds_display_update_event&)` (`0x2f9e978`) | `20B (0x14)` | `0x00830128` | **即 27 键轮第 2/13 键 `LEFT` 后出现的 `01001500...`（返回点 `0x16f12ec`）**；在 `0x16f38c8` 被归为类型 `5`（内部 UI 显示更新事件），不触发 `0x80924220`。 |
| `0x16f152c` | `virtual void App::got_convert_touch_event(const ds_input_event&)` (`0x2f9e930`) | `20B (0x14)` | `0x00830128` | 触摸转换事件（分类为类型 `6`）。 |
| `0x16f1a50` | `void App::exec_utimer()` (`0x2f9e8c8`) | `28B (0x1c)` | `0x00830128` | UI 定时器事件（分类为类型 `2`）。 |

### 3.2 `QID = 0x80924220`（UPM MSS）发送端全景（`appFw.so` 37 处 + `upm.ko` 内部 7 处）

- **`appFw.so` 侧（全部经由 `0x2eaf294`）**：
  - `0x00920204` (`MSS_reload_timer`, `0x2de0294 -> 0x2eb4f24`)：仅 1 处（`0x2d35168` `sequence_mss_reload::run`，绑定属性 `0x27c` `debug_is_stop_updating_remote_presenter`）。
  - `0x00920202` (`MSS_del_stopper`, `0x2de0254 -> 0x2eb7378`)：15 处（含 `0x2793588` `set_upm_mss_start`、`0x2b669e4` `sequence_boot::run_i`、`0x2d98618` `sequence_set_power_save_start_time` 等；当 `stopper_list` 变空时在 `upm.ko` `.text+0x2468..0x2490` 重新启动完整 300s 定时器）。
  - `0x00920203` (`MSS_add_stopper`, `0x2de02d4 -> 0x2eb7428`)：8 处（含 `0x279344c` `set_upm_mss_stop` 等；在 `upm.ko` `.text+0x26e0` 停止定时器并清零 `elapsed_sec`）。
  - `0x00920206` (`MSS_fakey_start/stop`, `0x2de0314/0x2de0354 -> 0x2eb4f74/0x2eb5084`)：5 处（在 `upm.ko` `.text+0x23f0` 原位改写为 `0x00920204` 并重载定时器）。
  - `0x00920118` / `0x00920119` (`MSS_add_request` / `MSS_del_request`, `0x2de0514/0x2de0554 -> 0x2eb5970/0x2eb5a80`)：8 处（在 `upm.ko` `.text+0x2628` / `0x26bc` 重载/重启定时器）。
- **`upm.ko` 内部直发侧（不经过 `appFw.so` `0x2eaf294`）**：
  - `.text+0x0f04` (`k_upm_init_mss` -> `0x00920118`)、`.text+0x614c` (`k_upm_init_off_factor` -> `0x00920203`)、`.text+0x69f4/0x6acc` (`k_upm_off_factor_handler_active` -> `0x00920203`)、`.text+0x7164` (`k_upm_off_factor_handler_acting_app` -> `0x00920202`)、`.text+0x88c4` (`k_upm_off_factor_handler_res` -> `0x00920202`)、`.text+0xa2d0` (`power_status_factor_cb` 收到 `0x00920131..0x00920138` -> `0x00920204`)、`.text+0xaa44` (`k_upm_init_power_status` -> `0x00920203`)。

---

## 4. 离线复现与校验命令

在 [`display-contract/`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract) 目录下直接执行：

```bash
python3 verify_display_contract_v2.py
```

- [`verify_display_contract_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/verify_display_contract_v2.py) 强校验 5 个原始固件二进制（`appFw.so`、`libObj.so`、`av-cam.bin`、`upm.ko`、`cpapp-b.bin`）与 7 份运行产物/源码的 SHA256，复现 [`display-contract-evidence-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-evidence-v2.json)（SHA256 `790a240c16cca6f52a599f81597265c9b2c56e8220a9f4bd5a8a9d73d946b8ea`）与 [`display-contract-fixture-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/display-contract/display-contract-fixture-v2.json)（SHA256 `d521212cf7da0efa67a4b6564c17f4545df4e3d3c3ed2c942ff0d15e5bf023d0`）。
