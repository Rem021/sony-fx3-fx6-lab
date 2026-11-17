# Phase 276 安全护栏报告（Task H315，`114/114` Safety Gates）：Wave-47 Safety Gates `G113` / `G114` 与统一 `verify-114-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 276（Task H315，`114/114` Safety Gates）闭环交付，将 Wave-47 官方 `ILME-FX3 Ver. 7.02`（Help Guide `ilc/2210`）、`ILME-FX6 Ver. 6.01` 与共享 `BIONZ XR` `appFw.so` / `.uxc` / `usb_f_uvc.ko` 实机情报转化为确定性安全门禁 `G113`、`G114` 及统一 `114` 门主预检引擎（`G01..G114`）**：
   - 新增模块 [`realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)（Schema `realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard_v1` `1.0.0`），将 `G01..G112` 零重复委托给 [`evaluate_112gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/realhw_power_save_monitor_language_volume_delete_and_112gate_guard.py)（Phase 276 增量 `O_RDONLY` 审计与 `G113`/`G114` 仅新增 **`0.0049s`（4.9 ms）**）；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/__init__.py)（零遮蔽导出全部 Phase 276 专属符号与子模块）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/__main__.py)（注册 `verify-usb-mode-hdmi-info-guard` / `verify-g113-usb-mode-hdmi-info`、`verify-protect-and-network-reset-guard` / `verify-g114-protect-network-reset` 与 `verify-114-gates`）及 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/README.md) 第 57 节。
2. **三模式 76 项双模单测、`verify-114-gates`、Milestone 264 回归、全量 `2839` 项 `fx3-safety` 测试与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_usb_mode_hdmi_info_protect_network_reset_114gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_114gate_guard.py) 共 **76 项**双模单元测试（满足 `>= 72` 项；全量 subprocess 均使用 `sys.executable`，`argparse` 无未转义 `%`，`GITHUB_ACTIONS=true` 含 `15.0s` 充裕时间窗），在 `LOCAL_DONOR_O_RDONLY`（`3.243s`）、`FX3_CLEAN_ROOM_TEST=1`（`3.179s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`3.203s`）下均 **`76/76 OK`**；
   - CLI `verify-114-gates`：默认离线模式通过 **`111/114`**（`VERIFIED_111_OF_114_AWAITING_PHYSICAL_TIER0`，物理 Tier-0 `G10..G12` 按安全规则 fail-closed 待命），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `--force-clean-room` 下均通过 **`114/114`**（`VERIFIED_ALL_114_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_114_gates_verified=True`）；
   - `make verify-milestone-264` 双模均 `status=OK`（`499ed45d275e9f26...` / `a52107a995b54f71...`），`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 1.16s`，且全量 `outputs/fx3-safety/tests` discovery 实测 **`Ran 2839 tests in 84.927s — OK`**。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate `G113` 与 Gate `G114` 技术建模要点（Wave-47 规范映射）

### 2.1 `< 0.20s` 有界 `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底
- [`audit_phase276_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py) 严格使用 `os.open(..., os.O_RDONLY)`，并对 `79,015,712 B` FX3 `appFw.so`（19 个 Wave-47 切片 SHA-256 `ca367416636bb501...`）与 `50,520,424 B` FX6 `appFw.so`（6 个切片 SHA-256 `decff496dabc17a2...`）采用有界定点 `os.pread`，同时对 `string_english_f.uxc`、FX3 `string_english.uxc`、`string_english_g.uxc`、休眠模块 `usb_f_uvc.ko`（`78,840 B`）、`FX3-CX95900_ALLLANG-Backup.bin`、FX6 `string_english.uxc` 及 `string_english_2.uxc` 共 **9 份**产物进行完整校验。
- 实测耗时 **`0.0025s < 0.20s`**，`dormant_usb_f_uvc_ko_bytes == 78_840`，`raw_firmware_bytes_leaked == 0`，并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或 donor 缺失时确定性回落至 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Gate `G113`：`GATE_G113_USB_CONNECTION_MODE_NOUVC_PD_DATA_ISOLATION_AND_HDMI_INFO_DISPLAY_GUARD`
- **`[USB Connection Mode]` 4 模式与休眠 `NOUVC` `[USB Streaming]` 分裂**：
  - 锁定原厂 `ILME-FX3 Ver. 7.02`（`ilc/2210`，`BKID_APP_setting_usb_connection_method`，`_f.uxc` `0x69a2`）**仅暴露 4 种模式**：`Sel. When Connect`（`0x7738` 出厂默认）、`MassStorage(MSC)`（`0x6c54`，`054C:0DA1`，`USB_CONNECTION_METHOD_MASS_STRAGE`）、`MTP`（`0xe24b`）、`Remote Shoot (PC Remote)`（`0x60aa`/`0x7c6f`）。
  - 针对 `appFw.so` + `_f.uxc`（`0x7399`）+ `usb_f_uvc.ko`（`78,840 B`）虽存在但 `ILME-FX3` 上受 `NOUVC` 编译期屏蔽的事实，严格拦截任何声称 FX3 暴露原生 `[USB Streaming]` UVC/UAC UI 的伪造配置（`STATUS_BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION`）。
- **隔空 Tier-0 USB 数据枚举隔离与 `[USB Power Supply]` / `[USB LUN Setting]` 护栏**：
  - 隔空 Tier-0 台架严禁 `MassStorage(MSC)`、`MTP`、`Remote Shoot` 与 `USB-LAN` 主机数据枚举；`[USB Power Supply] = On`（默认 `0x721e`，仅限 `USB Type-C` + 插入 `NP-FZ100`；`[USB LUN Setting]` `Multi` `0xe631` / `Single` `0x776d`）仅在 `USB D+/D-` 与 SuperSpeed 数据线物理隔离时允许放行（`STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD`）。
- **`[HDMI Info. Display]` 息屏联动、`1080` 钳位、`4K` Clean-Feed 强覆盖与 `(Setup)` 复位边界**：
  - 建模 `On`（默认：输出 HDMI OSD 并熄灭机内 LCD `CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`，禁用 LCD 触控对焦）vs `Off`（HDMI Clean Feed 且 LCD 保持点亮）；内录（`On`）叠加 `Log Shooting != Off` 或 `PPLUT1..4` 时强制 `1080` 输出；`Off(HDMI Only)`（`0x6573`）或 `RAW Output = On`（`0x6e97`，`S&Q` 下禁用）输出 `4K` 并强制 `[HDMI Info. Display] = [Off]`；验证 `(Setup)` USB/HDMI 项跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 清零）与 `Framing Settings (HDMI)` 例外复位，经 [`compute_usb_mode_and_hdmi_info_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py) 穷举验证全部 **`256`** 组状态组合。

### 2.3 Gate `G114`：`GATE_G114_PROTECT_VS_FORMAT_SLOT1_WP_FIREWALL_AND_RESET_NETWORK_SET_ZERO_RF_GUARD`
- **`[Protect]` 5 作用域 vs `[Format]` 覆写与 `Slot-1` 双层硬件 WP 防火墙**：
  - 锁定 `MENU -> Playback -> [Selection/Memo] -> [Protect]`（`0xe2c9`）全部 **5 项**作用域（`Single` `0xe2c9`、`Multiple Img.` `0xe2ca`、`All in this Folder` `0x6848`、`All with this date` `0x69f7`、`All Images in This Group` `0xe826`）可阻止 `[Delete]` / `[Delete pressing twice]` 且卡间复制自动剥离保护，但 **`[Format]`（`0xe449` / `0xe414`）会直接抹除已保护文件与卡内 `M1..M4` 设置**。
  - 对 `Slot 1` 恢复保险库强制执行双层防御：严禁仅依赖软件 `[Protect]`，必须同时满足 SD 物理 `WP` 锁定（`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`）与 `slot1_format_hard_locked == True`（`STATUS_BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION`）。
- **`[Reset Network Set.]` 三域复位边界、自动重启与 Zero-RF 恢复序列**：
  - 锁定 `[Reset Network Set.]`（`FUNC_reset_network_settings`，`SETTING_RESET_NW`，`0x60d3`/`0x65d3`）仅清除 `(Network)` 凭证（Wi-Fi SSID/PSK、Bluetooth 配对、FTP `0..8`、`Creators' Cloud`、`Network Streaming`、根证书），保留 `(Shooting)`/`(Exposure/Color)`/`(Focus)`/`(Setup)`/`(Playback)`/`CAMSET`，触发强制自动重启（`BKID_APP_is_shutdown_factor_network_reset`），且**将 `[Airplane Mode]` 复位为 `Off`**。
  - 任何执行 `[Reset Network Set.]` 后未完成自动重启或未重新置位 `[Airplane Mode] = [On]` 的隔空台架流程均拦截为 `STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD`，并经 [`compute_protect_and_network_reset_matrix()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py) 穷举验证全部 **`160`** 组状态组合。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令（含全量 `2839` 项 `fx3-safety` 测试发现）均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：物理真机 Tier-0 收据门禁 `G10..G12` 在离线默认模式下按设计保持 fail-closed 待命（`111/114`），唯有人工台架注入离线只读实机 SHA-256 收据后方可在非模拟模式下闭合最后 3 门，且硬件写与实机自动连接红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 276 双模定向单测（76 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_114gate_guard.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `76/76 OK`（Donor `3.243s`）+ `76/76 OK`（`FX3_CLEAN_ROOM_TEST=1` `3.179s`）+ `76/76 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `3.203s`） |
| CLI `G113` / `G114` 专项门禁检查 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-usb-mode-hdmi-info-guard` / `verify-protect-and-network-reset-guard` | `LOCAL_DONOR_O_RDONLY` 下均 `valid=True`、`rc=0` |
| CLI `verify-114-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-114-gates` | `verified=111/114`（`VERIFIED_111_OF_114_AWAITING_PHYSICAL_TIER0`，`rc=0`，Phase 276 增量耗时 `0.0049s`） |
| CLI `verify-114-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-114-gates --simulate-bench-dry-run`（及 `--force-clean-room`） | `verified=114/114`（`VERIFIED_ALL_114_GATES_DRY_RUN_SIMULATED_BACKUP`，`all_114_gates_verified=True`，`rc=0`） |
| Milestone 264 双模门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`499ed45d275e9f26...`）+ `CLEAN_ROOM_SYNTHETIC`（`a52107a995b54f71...`）均 `status=OK` |
| 全量 `fx3-safety` 测试发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 2839 tests in 84.927s`（`OK`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 1.16s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_114gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/outputs/fx3-safety/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_114gate_guard.py)
6. [`reports/2026-11-17-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h315-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/reports/2026-11-17-phase276-safety-114gates-usb-mode-hdmi-info-protect-reset-network/README.md)
