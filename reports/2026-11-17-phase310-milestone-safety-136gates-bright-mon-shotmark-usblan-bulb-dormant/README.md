# Phase 310（310th Phase Milestone）：Wave-58 实机硬件安全门禁 `G135` & `G136` 与统一 `136/136` 预检引擎交付报告

- **日期**：`2026-11-17`
- **任务**：Task H366 — Phase 310 (310th Phase Milestone) Wave-58 Hardware Safety Gates `G135` & `G136` + Unified `verify-136-gates` (`136/136`)
- **严格六文件交付范围**：
  1. 新增核心守卫模块：[`realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.py)
  2. 更新包导出与 Milestone 295 自动发现入口：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/__init__.py)
  3. 注册 CLI 子命令（含 `--json` 与 `--simulate-bench-dry-run`）：[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/__main__.py)
  4. 新增文档第 68 节：[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/README.md)
  5. 新增 86 项双模式/三环境变量单元测试：[`test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py)
  6. 本工程报告：`reports/2026-11-17-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/README.md`

---

## 核心结论（Executive Summary）

1. **已将实验室实机安全门禁总账从 `134/134` 推进并收口至 `136/136`（Phase 310 里程碑）**：
   - 离线默认模式（[`evaluate_136gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.py) / `verify-136-gates`）：**`133/136` 门禁通过**（`VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0`，仅物理 Tier-0 备份回执 `G10..G12` 待人工台架接入），在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）下均实测通过。
   - 模拟演练模式（`--simulate-bench-dry-run`）：**`136/136` 门禁全绿通过**（`VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP`）。
   - **Milestone 295 动态自动发现实测确认**：`make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` 自动发现最高入口 `evaluate_136gate_preflight`，输出 `gate124=133/136`、`pillars=6/6`、`recovery=54/54`、`auditors=45/45`、`vm_stages=62/62`、`qemu=34/34(102/102)`。
2. **所有硬核安全红线保持永久锁死**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`agent_auto_flash_blocked = True`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`cross_model_flash_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。
3. **全量实测通过**：
   - Phase 310 新增 **86 项单元测试**（满足 `>= 84` 要求）在 **默认 (`LOCAL_DONOR_O_RDONLY`)**、**`FX3_CLEAN_ROOM_TEST=1`**、**`FX3_FX6_FORCE_CLEAN_ROOM=1`** 三种模式下全部 `86/86 OK`。
   - `outputs/fx3-safety` 全量单元测试发现共 **3,751 项测试**全部 `OK`（`166.287s`）。
   - `make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）审计 **`ALL GREEN`**。

---

## 一、实测事实 vs 推断边界（Strict Fact / Inference Separation）

| 类别 | 具体内容 | 证据来源 |
| :--- | :--- | :--- |
| **实测事实（Donor 只读 `os.O_RDONLY` + `os.pread`）** | `FX3 appFw.so`（`79,015,712 B`，27 组定界切片 `sha256: 2f52e3f1...`）实含 `PRM_setting_bright_monitoring_state`、`EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_{ON,OFF}`、`BKID_APP_setting_lcd_brightness`、`sequence_add_shot_mark`、`execute_clip_flag_by_remote`、`BKID_APP_ext_tc_lock_status`、`BKID_APP_setting_{usb_lan_connect_launch,airplane_mode,bulb_timer}`、`PID_SET_BULB_MODE`、`BKID_APP_extern_menu_hdr_level` 与 `menu_item_id_dro_wrapper`；`tc_link` / `timecode_link` / `UltraSync` 全为 `0` 命中。 | [Wave-58 情报报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/reports/2026-11-17-global-sony-wave58-bright-monitoring-shot-mark-timecode-link-wifi-usblan-intel/README.md) & [`audit_phase310_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.py) |
| **实测事实（FX6 ELF、4 语 UXC 与 USB-LAN 内核栈）** | `FX6 appFw.so`（`50,520,424 B`，13 组定界切片 `sha256: c0f0511a...`）含 `VAL_setting_auto_exposure_mode_MODE_BACKLIGHT`、`BKID_APP_USER_MENU_VF_SETTING0`、`VAL_content_clip_flag_CONTENT_CLIP_FLAG_{OK,NG}` 及休眠 `BKID_APP_SETTING_{BLUETOOTH_FUNCTION,USB_TC_IN_ALT_MODE_SETTING}`；FX3 四语 `_f.uxc` / `.uxc` / `_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`full-v4` 真实驱动模块（`cdc_ncm.ko`、`r8152.ko`、`asix.ko`、`ax88179_178a.ko` 等）与 `lib{WiredLan,Wlan,InfraAirplaneMode}.so` 全数 SHA-256 校验一致。 | 18 项只读 donor 审计 |
| **推断（工程化安全护栏与台架策略）** | `Slot-1` Tier-0 恢复保险库 `EROFS=30` / `EBUSY=16` 写拦截防火墙（阻断会改写 `M4ROOT/CLIP/*M01.XML`、`DCIM/` 或 `AVF_INFO` 的 `Shot Mark 1/2`、`Clip Flag`、`Photo Capture`、`Create Divider Frame` 与 `Edit`）；台架 `[Airplane Mode] = On` 零射频策略（阻断一切 Wi-Fi/BT TX 与 `p12/p13` NVS 写，仅放行已授权有线 `USB-LAN` `eth0`）。 | [`verify_bright_mon_shotmark_vault_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.py) & [`verify_tc_link_wifi_usblan_bulb_dormant_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h366-phase310-milestone-safety-136gates-bright-mon-shotmark-usblan-bulb-dormant/outputs/fx3-safety/fx3_safety/realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.py) |

---

## 二、Gate `G135` & `G136` 核心门禁设计摘要

### 1. Gate `G135`（自定义键独占 `[Bright Monitoring]` + Ver. 7.00+ 放大共存、`[Monitor Brightness]` vs FX6 `VF Setting` / AE `Backlight`，以及 `Shot Mark 1/2` + `Clip Flag` + `Divider Frame` Slot-1 保险库防火墙）
- **`[Bright Monitoring]`（`_f.uxc 0x701f`）**：强制仅允许通过 `Custom Key/Dial Set.` 绑定触发（拒绝拍摄菜单开关或多级增益伪造，`EOPNOTSUPP=95`），开启时自动强制 `[Live View Display] = Setting Effect OFF`，并在关机、离开 `P/A/S/M` 或离开 `MF` 时自动取消；在 `Ver. 7.00+/7.02` 显式放行与 `[Focus Magnifier]` / `[Auto Magnifier in MF]` 共存。
- **`[Monitor Brightness]`（`.uxc 0xe44b`）**：仅暴露 `Manual`（`-2..+2`，默认 `0`）与 `Sunny Weather`（`_f 0x6fd4`），仅由 `[Initialize]` 重置（保留过 `[Camera Settings Reset]`），拒绝休眠 `AUTO/BRIGHT/NORMAL`（`EOPNOTSUPP=95`）及伪造的 FX3 4K 热降亮锁；严格区分 `ILME-FX6` `Monitoring > VF Setting > Brightness`（`1..15`）与 `Shooting > Auto Exposure > Mode > Backlight`（逆光 AE 模式而非屏幕背光！）。
- **`Shot Mark 1/2` + `Clip Flag` + `Create Divider Frame` & Slot-1 写防火墙**：拒绝 FX3 不存在的机内 `[Divide]` / `[Extract]` 与休眠 FTP `15/30/60s` 自动切片（`_f.uxc 0x7005/0x6e38/0x6c2a` -> `EOPNOTSUPP=95`）及 FX6 休眠 `Shot Mark 0..9`；当 `[Add/Delete Shot Mark1/2]`（`_f.uxc 0x628b/0x628a/0x6143/0x6142`）、`[Clip Flag]`（`OK/NG/KEEP`）、`[Photo Capture]`、`[Create Divider Frame]`（`_f.uxc 0x747a` / `_g.uxc 0x6118`）或回放 `[Edit]` 试图向 `Slot-1` Tier-0 只读保险库写入 `M4ROOT/CLIP/*M01.XML`、`DCIM/` 或 `AVF_INFO` 时 fail-closed 拦截返回 `EROFS=30` / `EBUSY=16`（`slot1_data_sector_writes == 0`）；放行 `Slot 1` 只读 `Image Jump` 与 `Slot 2` 合法写操作。
- **全量枚举矩阵 `compute_bright_mon_shotmark_vault_matrix()`**：**384 状态**（`bm_active_effect_off=48`, `bm_autocancel=336`, `cam_reset_mon_persisted=192`, `slot1_vault_blocked=160`）全部不变量成立。

### 2. Gate `G136`（零蓝牙 `Timecode Link` vs 有线 `VMC-BNCM1` `EXT-LK` & FX6 BNC `TC IN/OUT`、Wi-Fi `WPA2/WPA3` 双 SKU + `USB-LAN` 零射频隔离，以及休眠 `[Bulb Timer]` / `[Auto HDR]` vs 机械快门独占 Still `[BULB]` + `DRO` 锁定）
- **时间码通道护栏**：拒绝蓝牙 `[Timecode Link]` / `UltraSync BLUE`（`FX3 Ver. 7.02` 零 `tc_link` 符号 -> `EOPNOTSUPP=95`），仅允许 Movie 下通过 Multi/Micro USB + `VMC-BNCM1`（`Time Code Make = Preset` + `Free Run` -> `EXT-LK`）注入有线 LTC 及 Type-A HDMI `Time Code Output`，并对比 `ILME-FX6` 机身物理 `TC IN/OUT` BNC 开关与零蓝牙硬件。
- **Wi-Fi 安全/SKU & `USB-LAN` 零射频隔离**：校验 `Ver. 7.00+` `WPA2-PSK` / `WPA3-SAE`（拒绝已移除的 `WEP` / `WPA-PSK` / `IPsec`）、`WW728473`（`2.4/5 GHz`）vs `WW558244`（仅 `2.4 GHz`）硬件分版；校验 `USB-LAN` 内核栈（`cdc_ncm.ko`、`cdc_ether.ko`、`r8152.ko`、`asix.ko`、`ax88179_178a.ko`、`usbnet.ko`、`ipheth.ko`、`rndis_host.ko` + `[USB-LAN Cnct. Launch]` `_f.uxc 0x7d2a`）及与 Multi/Micro USB（含 `VMC-BNCM1`）和 Wi-Fi 的总线互斥（`EBUSY=16`）；强制台架 `[Airplane Mode] = On` 零射频锁（跨越 `[Reset Network Set.]` 与 `[Initialize]` 均持久化保留，拦截 Wi-Fi/BT TX 与 `p12/p13` RF NVS 写，仅放行已授权隔离有线 `eth0`）。
- **休眠 `[Bulb Timer]` / `[Auto HDR]` & 机械快门 `BULB` / `DRO` 锁**：拒绝休眠 `[Bulb Timer]`（`BKID_APP_setting_bulb_timer` / `_f.uxc 0x630f` -> `EOPNOTSUPP=95`）与休眠 `[Auto HDR]`（`.uxc 0xe49d` -> `EOPNOTSUPP=95`）；强制 Still `[BULB]` 仅限 `[Mechanical Shutter]` + 单拍/单张自拍（在 `[Electronic Shutter]`、`Cont. Shooting`、`Cont. Bracket`、`Self-timer(Cont)`、`Interval Shooting` 与非 Still 模式下自动夹断至 `30"`，强行开启则 fail-closed 阻断，并禁用 `Anti-flicker Shoot.`）；验证 `[Picture Profile] != Off` 或 `[HLG Still Image] = On` 时 `[D-Range Optimizer]` 与 `[DRO Bracket]` 强制锁定 `Off`（`[Camera Settings Reset]` 重置 DRO 为 `Auto`）。
- **全量枚举矩阵 `compute_tc_link_wifi_usblan_bulb_dormant_matrix()`**：**768 状态**（`zero_rf_blocked=576`, `usb_conflict_blocked=288`, `bulb_clamped=640`, `dro_locked=384`）全部不变量成立。

---

## 三、端到端实测验证日志

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| **Phase 310 单元测试（Donor 只读模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py -v` | **86/86 OK** (`11.121s`) |
| **Phase 310 单元测试（`FX3_CLEAN_ROOM_TEST=1`）** | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py -v` | **86/86 OK** (`3.446s`) |
| **Phase 310 单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_bright_mon_shotmark_usblan_bulb_dormant_136gate_guard.py -v` | **86/86 OK** (`3.454s`) |
| **`verify-136-gates` 离线 & Dry-Run（Donor 模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-136-gates [--simulate-bench-dry-run] --json` | 离线 **`133/136`**（`VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0`）；Dry-Run **`136/136`**（`VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP`） |
| **`verify-136-gates` 离线 & Dry-Run（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-136-gates [--simulate-bench-dry-run] --json` | 离线 **`133/136`**；Dry-Run **`136/136`**，`mode=CLEAN_ROOM_SYNTHETIC` |
| **`outputs/fx3-safety` 全量单元测试发现** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests` | **3,751/3,751 OK** (`166.287s`) |
| **Milestone 295 主控联合门禁（Donor + Clean-Room）** | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **ALL OK**：自动发现 `evaluate_136gate_preflight`，`gate124=133/136`、`pillars=6/6`、`recovery=54/54`、`auditors=45/45`、`vm_stages=62/62`、`qemu=34/34(102/102)`、`leaked=0` |
| **Clean-Room 卫生审计** | `make clean-audit` (`scripts/run_all_lab_tests.py --clean-only`) | **`ALL GREEN`** (`0.04s`) |
