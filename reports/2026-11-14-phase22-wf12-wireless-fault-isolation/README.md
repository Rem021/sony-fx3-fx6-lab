# Phase 22 (`P12`)：无线模块（`WF-12` Wi-Fi/BT / 蓝牙 `BSA` / `InfraPericon` / `SeqQueueNetwork`）非阻塞故障隔离与 Sony Notice `00342260` Bootloop 免疫验证报告

**Phase 22 (`P12`) Wireless (`WF-12` Wi-Fi/BT / Bluetooth `BSA` / `InfraPericon` / `SeqQueueNetwork`) Non-Blocking Fault Isolation & Notice `00342260` Bootloop Immunity Closure Report**

> [!NOTE]
> - **Schema**: `stage_a_phase22_wf12_wireless_guard_v1` (`v22.0.0`)
> - **执行状态 / Status**: **PASS**（本地真实 Donor 模式 `LOCAL_DONOR_VERIFIED` & 干净室合成模式 `CLEAN_ROOM_SYNTHETIC_VERIFIED` 双模式全绿，共 22 项单测 + Unicorn AArch64 指令级验证全部通过）
> - **核心实现 / Implementation**:
>   - [wireless_fault_isolation_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h10-phase22-wf12-wireless-guard/outputs/fx6-on-fx3-closure/fx6_closure/wireless_fault_isolation_verifier.py)
>   - [test_phase22_wireless_fault_isolation.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h10-phase22-wf12-wireless-guard/outputs/fx6-on-fx3-closure/tests/test_phase22_wireless_fault_isolation.py)

---

## 1. 背景与威胁模型（Context & Notice `00342260` / QEMU `a7c2` 根因）

1. **Sony 官方通告 `00342260`（2026-01-20 更新）与 `WF-12` 硬件退化故障**：
   FX3 机身的 `WF-12` Wi-Fi/蓝牙模组存在已知冷焊/热老化/SDIO 通信退化问题；当无线前端探针返回硬件错误（`WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR` / `MODEL_WIFI_FATAL_ERROR_OCCURRED`）或用户态 UI 弹出 `"The Wi-Fi/Bluetooth unit has malfunctioned."` 时，若初始化路径同步死锁、触发看门狗超时或未提供可忽略的降级态，机器会陷入 `"System Error"` 或 **5–10 秒无限 Bootloop**。
2. **QEMU 虚拟化与裸机未初始化 `BSA` 控制器（`a7c2-qemu` `virtual-rom-v1` 发现）**：
   在 QEMU/Stage-A 环境中（无物理 `WF-12` 无线芯片、无 `/dev/ttyAMA3` 蓝牙 HCI UART、无 `sdio_lib.ko`），以及 `BK4\0` 未经飞行模式屏蔽时，FX6 `v6.01` 用户态无线与网络初始化链路如果将无线异常视作致命错误，将阻塞 `Application_System_Init` 或把工作线程卡死在无限循环中。
3. **本阶段目标（`P12` + `P3` 协同闭环）**：
   对 FX6 `v6.01` 与 FX3 `v7.02` 真实只读 Donor 二进制完成字节级反汇编定位 + Unicorn AArch64 指令级故障注入 + 确定性状态机验证，严格证明 5 类故障均实现**非阻塞降级隔离**，且严格遵守 Stage-A/B 红线。

---

## 2. 真实只读 Donor 审计清单（`O_RDONLY` Zero-Mutation Donor Audit）

> [!IMPORTANT]
> 所有 Donor 镜像与脚本均通过 `os.O_RDONLY` 打开读取；未向任何 Donor 目录或运行中 QEMU 实例（`PID 31304` / port `8768`）执行任何写操作或进程干预。

| 构件 / Artifact | 平台版本 | 大小 (Bytes) | SHA-256（前 16 位） | 关键发现 / Disassembly Findings |
| :--- | :--- | ---: | :--- | :--- |
| `appFw.so` | FX6 `v6.01` | `50,520,424` | `a1c58b691c0884e1` | `Application_System_Init` (`0x0c0b044`, QID `0x008f013a`)；`0x13448e0` (`Fatal error on Wi-Fi func`, 投递可忽略事件 `0xbc0`)；`0x0c94dec` (`Invalid Bluetooth Wi-Fi Control`, 返回 `1`)；含全部 `SeqQueueNetwork*` 与 `EXTERN_SETTING_AIRPLANE_MODE_ON` 符号 |
| `libInfraAppRemoteBoard.so` | FX6 `v6.01` | `10,448` | `c7d666093b42713e` | `P3` 锚点 `0x157c` & `0x1700`：未打补丁时读取 `BK4 0x00fa01a3/0x00fa01a4` 后永久阻塞在 `osal_wai_sem_tmo(0x810708dc, -1)`；`P3` 替换为 `mov w0, #0; ret`（`16B` 变更，可完美回滚） |
| `libWlanResource.so` | FX6 `v6.01` | `56,464` | `eb7785e025d11eef` | **新发现 `P12` 死锁根因**：`WlanResourceMainThread` (`0x80f8`) 在 `osal_rcv_msg_tmo` 失败后调用 `_Z16handleFatalErrorv` (`0x70d4`)；该函数在 `0x70e8..0x70f0` 构成 **`while (1) usleep(1_000_000);` 无限死循环**（`0xf4240` us）！`P12_WLAN_FATAL_GUARD_SPEC` 将 `0x70d4` 替换为 `mov w0, #0; ret`（`7B` 差异，零残留回滚）；`loadWlanHostDrivers` (`0x6b5c`) 在 `insmod` 失败时安全返回 `-1/-2` |
| `libWlanControlCommon.so` | FX6 `v6.01` | `18,528` | `4dccfa865720f662` | `initializePort` (`0x1bac`) 在 `/dev/mem` 或 `/dev/gpio` 缺失时非阻塞返回 `-1`；`installWlanDrivers` (`0x28c8`) 在 `sdio_lib.ko`/`sdio_busdriver.ko` 缺失时记录 `0x3006` 错误并返回 `-1` |
| `libInfraBluetooth.so` | FX6 `v6.01` | `154,840` | `3b3c1a411f3e157c` | `Init` (`0x12620`) 首先读取 BK4 `0x019e0012`（1B），若为 `0x00` 则在 `0x126c0` (`cbz w0, 0x126ac`) 提前返回，完全跳过后续 `0x0051000f` 与 BT 核心拉起 |
| `libInfraBluetoothCore.so` | FX6 `v6.01` | `267,576` | `84a9bf33d26914a4` | `wrapper_bt_interface_enable` (`0x1f0f0`) 在 `getHALInterface()==NULL` 或 `hal->init()!=0` 时返回 `0xbb9` (`3001`) 降级错误码，不触发 `abort`；`startProcessOnBoot` (`0x105d8`) 在状态非 `2` 时安全返回 `-1` |
| `libResourceBluetooth.so` | FX6 `v6.01` | `14,464` | `2be9da99a2d45980` | `ResourceBluetooth_init` (`0x1a98`) 读取 BK4 `0x01a20002`（1B），若为 `0x00` 则经 `0x1c14` (`cbz w0, 0x1be0`) 安全退出，不探测物理 BT GPIO |
| `libbt-vendor.so` | FX6 `v6.01` | `47,968` | `3c9a48fedd5bbc82` | 确认 BSA UART 设备节点 `/dev/ttyAMA3` 与 `"HCI device open failed"` / `"PM command failed, power management Disabled"` 降级路径 |
| `libInfraNetInitializer.so` | FX6 `v6.01` | `18,792` | `9628f8d974347347` | `initialize` (`0x2318`) 在 `fopen("/proc/sys/net/core/wmem_max") == NULL` 时仅记录 `errno` 错误日志并继续完成 `lo` / `ResourceManager` 初始化后返回 `0` |
| `appFw.so` | FX3 `v7.02` | `79,015,712` | `545c5053a74e04ff` | `Application_System_Init` (`0x16efb90`)；完整包含 `WIFI_DEVICE_ERROR_TYPE_*`、`MODEL_WIFI_DEVICE_ERROR`、`SeqQueueNetworkUsb`、`extern_BKID_APP_EXTERN_SETTING_AIRPLANE_MODE`、`No40_AirplaneMode` |
| `insmod_drv1` / `insmod_drv2` | FX3 `v7.02` | `152` / `1,298` | `22f29d06` / `19757bdd` | 确认早启脚本加载 **0 个** Wi-Fi / SDIO / BT 内核模块（无线 `.ko` 仅由 `libWlanResource.so` 按需延迟加载） |
| `libInfraPericon.so` 审计 | FX6 `v6.01` | — | 不存在 (`False`) | 实证 FX6 `v6.01` Donor 中外设/远程板/网络初始化职责由 `libInfraAppRemoteBoard.so` (`P3`)、`libInfraNetInitializer.so`、`libWlanResource.so` 与 `appFw.so`（`SeqQueueNetwork*`）共同承担 |

---

## 3. 五大故障注入场景与 Unicorn AArch64 执行回执（5 Scenarios）

在 **本地真实 Donor**（`LOCAL_DONOR_VERIFIED`）与 **干净室合成 ELF64**（`CLEAN_ROOM_SYNTHETIC_VERIFIED`）双模式下，Unicorn AArch64 引擎均实测执行全部 5 个故障场景并校对堆栈指针守恒（`SP == 0x7000E000`）：

| # | 场景 ID / Scenario ID | 目标函数 & VMA | 注入故障 / Injected Fault | 返回码 / RC | 耗时预算 | 降级状态 / Degraded State | 结论 |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| 1 | `WF12_SDIO_PROBE_TIMEOUT` | `installWlanDrivers` (`0x28c8`), `loadWlanHostDrivers` (`0x6b5c`), `WlanResourceMainThread` (`0x80f8`), `handleFatalError` (`0x70d4`) | `insmod` 返回 `-1` + `osal_rcv_msg_tmo` 返回 `-50` 超时 | `-1` | `8.4 ms` | `WF12_DEGRADED_RADIO_OFF`（证明未打补丁时进入 `0x70e8` 无限 `usleep`，`P12` 补丁后 `0` WDT 复位） | **PASS** |
| 2 | `BT_BSA_UART_NO_RESPONSE` | `wrapper_bt_interface_enable` (`0x1f0f0`), `startProcessOnBoot` (`0x105d8`) | `getHALInterface()==NULL` 且 `/dev/ttyAMA3` BSA HCI `init()==-1` | `3001` (`0xbb9`) | `6.2 ms` | `BT_DEGRADED_DISABLED`（无 `"System Error"` 中止） | **PASS** |
| 3 | `NOTICE_00342260_MALFUNCTION_CODE` | `appFw.so::FatalErrorOnWifiFunc` (`0x13448e0`) + `InvalidBluetoothWifiControl` (`0x0c94dec`) | `WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR`（Sony Notice `00342260`） | `1` | `11.0 ms` | `NOTICE_00342260_AIRPLANE_LATCHED`（投递可忽略事件 `0xbc0`，拍摄/录制功能 `True` 不受影响） | **PASS** |
| 4 | `SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING` | `appFw.so::Application_System_Init` (`0x0c0b044`) + `libInfraNetInitializer::initialize` (`0x2318`) | 缺失 `/proc/sys/net/core/wmem_max` (`ENOENT`) + 网络异步队列超时 | `0` | `12.5 ms` (`< 50.0 ms`) | `SEQ_QUEUE_NETWORK_NONBLOCKING_DRAINED`（捕获系统初始化队列 `0x008f013a` 正常排空） | **PASS** |
| 5 | `AIRPLANE_MODE_RAM_SHADOW_DEFAULT` | `libInfraBluetooth::Init` (`0x12620`) + `ResourceBluetooth_init` (`0x1a98`) | 首次跨机启动 RAM-Shadow `BK4\0` 飞行模式默认（`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`） | `0` | `2.1 ms` | `AIRPLANE_MODE_RAM_SHADOW_SAFE`（Unicorn 实测 Shadow 下跳过 BT 探测，Stock `0x01` 下进入探测，NVRAM 写入=`0`） | **PASS** |

### 负向破坏检测（Negative Guard Corruption Verification）

调用 `run_phase22_wireless_fault_isolation_verification(..., corrupt_wireless_guard=True)` 在本地 Donor 与合成模式下均成功检出回归失败（`passed == False`, `errors=7`）：
- `P3` 返回死锁哨兵 `0xDEAD`（`changed_bytes == 0`）；
- `P12` 返回死循环哨兵 `0xDEAD`（`changed_bytes == 0`，`WlanResourceMainThread` 卡死于 `0x70e8`）；
- 全部 5 个故障场景触发看门狗复位（`wdt_resets > 0`）、`"System Error"` 中止（`system_error_abort == True`）或超时（`120.0 ms >= 50.0 ms`）。

---

## 4. Stage-A/B 硬件红线锁（Hard Redline Locks）

| 红线约束 / Redline Invariant | 锁定值 / Locked Value | 验证结果 |
| :--- | :---: | :---: |
| `p5:/wbi` 改写字节 (`wbi_mutation_bytes`) | `0` | **LOCKED (0)** |
| `p8:/cp` 改写字节 (`cp_mutation_bytes` / `p8_cp_mutation_forbidden`) | `0` / `True` | **LOCKED (0 / True)** |
| FX3 原厂 `.ko` 改写数 (`kmod_mutation_count`) | `0` | **LOCKED (0)** |
| 持久 NVRAM / eMMC 写入 (`nvram_persistent_writes` / `persistent_emmc_writes_authorized` / `persistent_write_release`) | `0` / `False` / `False` | **LOCKED** |
| Donor 文件系统访问标志 (`donor_access_mode`) | `O_RDONLY` | **ENFORCED** |

---

## 5. 双模式验证结果与确定性摘要（Verification Receipts）

### 5.1 实跑命令行与摘要

1. **本地真实 Donor 模式**：
   ```sh
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase22_*.py" -v
   ```
   - 结果：**`Ran 22 tests in 0.635s — OK`**
   - 报告模式：`LOCAL_DONOR_VERIFIED`
   - 确定性 `report_sha256`：`4d91ae13d85e78c0c604960e36d7b66f6712d1f94f7d998c8d4970a3d8254b7d`

2. **干净室合成模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）**：
   ```sh
   PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase22_*.py" -v
   ```
   - 结果：**`Ran 22 tests in 0.196s — OK`**
   - 报告模式：`CLEAN_ROOM_SYNTHETIC_VERIFIED`
   - 确定性 `report_sha256`：`0aa77cd52b1e51cff532ea16a5c1c993f1a9cd4083ec1168c09cdc942553dbcc`

3. **`P3` & `P12` 补丁回滚摘要**：
   - `P3` (`libInfraAppRemoteBoard.so`): `c7d666093b42713e` → `2426911919397ab5` (`changed_bytes=16`, `rollback_sha256_matched=True`, `unpatched_hang_proven=True`, `patched_rc=0`)
   - `P12` (`libWlanResource.so` @ `0x70d4`): `eb7785e025d11eef` → `47fec188cc174faa` (`changed_bytes=7`, `rollback_sha256_matched=True`, `unpatched_hang_proven=True`, `patched_rc=0`)
