# Phase 29：无硬件依赖软件 GPE 光栅/精灵合成引擎与 `virtual-rom-v1` 蓝牙 HCI UART 仿真报告

> **日期**：`2026-11-14` · **工作流任务**：`Hydrogen-20 (task_8e1dac0289c1)` · **目标分支**：`codex/h20-phase29-soft-gpe-bt-rom`  
> **红线声明**：全程严格遵循 `os.O_RDONLY` 只读供体访问、零二进制/字节码缓存提交、`WBI_MUTATION_BYTES = 0`、`CP_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`，未触碰 `8768` 端口及任何后台 QEMU/Python 进程。

---

## 1. 背景与工程目标

依据 [`2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md`](../2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md) 第 2.1、2.2 节与第 4 部分第 4 行升级行动项，本阶段在 [`outputs/fx3-vm/`](../../outputs/fx3-vm/README.md) 中独立实现并验证两套完全脱离物理 `/dev/ldec`、`/dev/mem` 及物理 `WF-12` 无线芯片的软件参考仿真组件：

1. **Part A — 软件 GPE（`GRM_gpermFillrect` / `GRM_gpermRectblit` / `HOSDAP02` / `ramfb`）光栅合成引擎**：对齐 FX3/FX6 `1024×540` `GPE0`（`0x41E001000`）与 `ramfb`（`[0x41E100000, 0x41E600000)`）扫描输出管线，结合纯 CPU Sony LDEC/LZ77 解码与比特精确的 `fx6_px` 通道校验。
2. **Part B — `virtual-rom-v1` 蓝牙 HCI H4 UART（`/dev/ttyAMA3`）状态机仿真器**：核验 FX6 `libbt-vendor.so` 与 `libInfraBluetoothCore.so` 的 `/dev/ttyAMA3` 初始化标记，同时支撑健康 `BSA` 建链与 `P12` / Sony `00342260` 退化防砖分支测试。

---

## 2. Part A：软件 GPE 光栅与精灵合成引擎实现

核心实现位于 [`soft_gpe_and_bt_rom_emulator.py`](../../outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py)：

| 子模块 / 能力 | 关键参数与对齐依据 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- |
| **GPE0 / `ramfb` 内存布局** | `1024×540`（`552,960 px`, `2,211,840 B`）· `GPE0 = 0x41E001000` · `GPE1 = 0x41E221000` · `ramfb ∈ [0x41E100000, 0x41E600000)` | 越界 `ramfb` 地址严格抛出 `SoftGpeError`；`HOSDAP02` 64B 头与 `XRGB8888` 扫描输出长度与 `GPE0` 100% 对齐 |
| **像素格式与 `fx6_px` 校验** | `fx6_px(r,g,b,a) = (a<<24)\|(r<<16)\|(g<<8)\|b`（小端 `[B,G,R,A]`），对齐 [`libgrm-fbinit25-542.c`](../../outputs/fx3-vm-trial/src/libgrm-fbinit25-542.c) 与 [`fx6_next_stage_assist_log.c`](../../outputs/fx3-vm-trial/src/fx6_next_stage_assist_log.c) | 支持 `RGBA4444`、`ARGB4444`、`RGBA8888`、`A8`（`0x0E` 着色）；Cinema Line 琥珀色条 `0xFFF08018` 无 R/B 反转 |
| **混合与图元管线** | `GRM_gpermFillrect`（含 `const_alpha` 门控）、`GRM_gpermRectblit`（最近邻缩放、剪裁 `clip_rect`、Porter-Duff `SRC_OVER` / `SRC_COPY` / 双 `const_alpha`） | 整帧 `552,960` 非零像素、`59` 种唯一 ARGB 色彩（Donor 模式），`gpe0` 与 `gpe1` 刷新 SHA-256 完全一致 |
| **9-Patch 与纯 CPU LDEC 解码** | 直接解析 `image_00_169.uxc` 9-patch 描述符 `off+12` `u16[5..8]` (`left, top, right, bottom` 边距)，实现四角保真+四边单向拉伸+中心双向拉伸 | 只读解析 FX6 `image_00_169.uxc`（`3,941,000 B`）：`1,610` 精灵含 `22` 项 9-patch；洁净室模式合成 `5` 精灵（含 4 格式 + 9-patch） |

---

## 3. Part B：`virtual-rom-v1` 蓝牙 HCI H4 UART (`/dev/ttyAMA3`) 仿真器

### 3.1 只读供体标记核验（`O_RDONLY`）

- **`libbt-vendor.so`**（`47,968 B`, `sha256: 3c9a48fedd5bbc829d3d166feac090d3d5df3f347d9599f864722f885bdbf8bb`）：验证 `/dev/ttyAMA3`、`HCI device open failed`、`bt_hci_init_transport`、`userial_vendor_set_baud`、`rome_hci_reset_req`、`rome_set_baudrate_req`、`hci_send_cmd`、`read_hci_event`（`8/8`）。
- **`libInfraBluetoothCore.so`**（`267,576 B`, `sha256: 84a9bf33d26914a42c46ffc34381041d56006b3fdf76a2f475d954b602292694`）：验证 `/dev/ttyAMA3`、`g_uart_fd`、`g_default_termios_uart`、`libosal_uipc.so`、`_Z27wrapper_bt_interface_enableP13tBSA_MGT_OPEN`、`_ZN12InfraBTCore_14CBTCoreProcess17startQcaBsaCommonEb`、`_ZN12InfraBTCore_7CBTWoLE34HCI_Read_Local_Information_CommandEv`、`hci_update_baud_rate`（`8/8`）。

### 3.2 H4 UART 命令集与 4 种确定性运行模式

[`VirtualRomV1BtController`](../../outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py) 支持逐字节分片与粘包合流两种 H4 UART 流解析，覆盖 `HCI_Reset (0x0C03)`、`HCI_Read_Local_Version_Info (0x1001)`、`HCI_Read_BD_ADDR (0x1009)`、以及 Broadcom/Cypress 厂商指令 `0xFC2E`（Download_Minidriver）、`0xFC4C`（Write_RAM）、`0xFC4E`（Launch_RAM）和 `0xFC18`（Update_Baudrate）：

| 运行模式 (`mode`) | 触发条件 / 注入故障 | 验证结果与关键不变量 |
| :--- | :--- | :--- |
| **`HEALTHY_VIRTUAL_ROM_V1`** | 正常 `/dev/ttyAMA3` + RAM-Shadow 未开启飞行模式 | 完整 `BSA` 建链 `10` 包交互成功、`baud = 3000000`、`patchram = 160 B (3 chunks)`、`BD_ADDR = 58:36:57:00:29:01`、`errors = 0` |
| **`UART_DISCONNECTED_TIMEOUT`** | 串口无响应 / 断开 | 发射 `0` 条 HCI 事件，触发 `P12` `BT_DEGRADED_DISABLED`（`hal_error_code = 0x0BB9 / 3001`），`system_error_abort = False`、`wdt_resets = 0`、拍摄/录制不受影响 |
| **`PATCHRAM_CORRUPT_NACK`** | `0xFC4C` 第 2 分片注入中段 `WF-12` 拒绝（`0x0C` + `HCI_EVT_HARDWARE_ERROR 0x10`） | 立即锁存索尼 `00342260`（`NOTICE_00342260_AIRPLANE_LATCHED`），`wdt_resets = 0`、拍摄/录制正常、无 NVRAM 写入 |
| **`AIRPLANE_SHADOW_GATED`** | Stage-A/B RAM-Shadow `BK4\0`（`0x019e0012=00`、`0x01a20002=00`）激活 | `uart_opened = False`、`tx_packets = 0`、`tx_bytes = 0`；强行写入 UART 直接抛出 `BtRomEmulatorError` 门控异常 |

---

## 4. 验证记录（Local Donor & Clean-Room 双模式）

| 检查命令 | 覆盖范围 | 耗时 | 结果 |
| :--- | :--- | :--- | :--- |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py` | Local Donor (`O_RDONLY`) Part A + Part B 自检 | `< 0.5s` | **PASS**（`sprites=1610, 9patch=22, bt_modes_ok=4/4`） |
| `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py` | Clean-Room 合成模式自检 | `< 0.3s` | **PASS**（`sprites=5, 9patch=1, bt_modes_ok=4/4`） |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v` | Phase 24 (`22`) + Phase 29 (`25`) = **47 项单测**（Local Donor） | `1.547s` | **ALL 47 PASS** |
| `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v` | Phase 24 (`22`) + Phase 29 (`25`) = **47 项单测**（Clean-Room） | `0.851s` | **ALL 47 PASS** |
| `make clean-audit` | 全仓二进制/字节码/路径卫生审计 | `0.04s` | **ALL GREEN** |
