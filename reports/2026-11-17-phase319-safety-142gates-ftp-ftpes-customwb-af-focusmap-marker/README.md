# Phase 319（`142/142` Safety Gates）：Wave-61 实机硬件安全门禁 `G141` & `G142`、统一 `142/142` 预检引擎与 Donorless `work_root=None` CI 修复交付报告

- **日期**：`2026-11-17`
- **任务**：Task H381 — Phase 319（`142/142` Safety Gates）：Implement Wave-61 Hardware Safety Gates `G141` & `G142` and Unified `142/142` Preflight (`verify-142-gates`) + CI Donorless `work_root=None` `TypeError` 修复
- **分支**：`codex/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker`
- **交付范围（严格单写域 6 个主体文件 + 授权 7 个 CI 修复文件，共 13 个文件）**：
  1. 新增核心守卫模块：[`realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py)
  2. 更新包导出与自动发现入口：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/__init__.py)
  3. 注册 CLI 子命令（`verify-ftp-ftpes-avf-vault-customwb-guard` / `verify-g141-ftp-ftpes-customwb` / `verify-movie-af-focusmap-marker-peaking-guard` / `verify-g142-movie-af-focusmap-marker` / `verify-142-gates`，含 `--json`、`--summary`、`--clean-room` 与 `--simulate-bench-dry-run`）：[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/__main__.py)
  4. 新增文档第 71 节：[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/README.md)
  5. 新增 92 项双模式/三环境变量单元测试（满足 `>= 86` 要求）：[`test_realhw_ftp_ftpes_customwb_af_focusmap_marker_142gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/tests/test_realhw_ftp_ftpes_customwb_af_focusmap_marker_142gate_guard.py)
  6. 本工程交付报告：`reports/2026-11-17-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/README.md`
  7–13. **授权 CI `work_root=None` 防护修复（7 个既有文件）**：[`122gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.py)、[`124gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py)、[`126gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)、[`128gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py)、[`130gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py)、[`test_138gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/tests/test_realhw_big6_home_framing_interval_tc_ssh_fan_138gate_guard.py)、[`test_140gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/tests/test_realhw_rec_media_autoswitch_proxy_cloud_mymenu_140gate_guard.py)。

---

## 核心结论（Executive Summary）

1. **已达成 `142/142` 实机硬件安全门禁演进（Phase 319）**：
   - 离线默认模式（[`evaluate_142gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py) / `verify-142-gates`，`schema_version = "realhw_142gate_preflight_v1"`）：**`139/142` 门禁通过**（`VERIFIED_139_OF_142_AWAITING_PHYSICAL_TIER0`，仅物理 Tier-0 备份回执 `G10..G12` 待人工台架接入），在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1` 及无 donor `work_root=None` 模拟）下均实测通过。
   - 模拟演练模式（`--simulate-bench-dry-run`）：**`142/142` 门禁全绿通过**（`VERIFIED_ALL_142_GATES_DRY_RUN_SIMULATED_BACKUP`）。
   - **Milestone 311 & 295 动态自动发现实测确认**：`make verify-milestone-311` 与 `make verify-milestone-295`（各含正常与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式）均自动发现最高入口 `evaluate_142gate_preflight`，实测输出 `gate134=139/142` / `gate124=139/142`、`pillars=6/6`、`recovery=55/55`、`auditors=45/45`、`vm_stages=65/65`、`rf_pkts=0`、`usb_tx=0`、`leaked=0`。
2. **修复 Donorless Ubuntu CI `work_root=None` `TypeError` 并完成模拟回归**：
   - 修复了 5 个守卫模块（`122`/`124`/`126`/`128`/`130`-gate）及新的 `142`-gate 守卫在 `resolved_work is None` 时执行 `resolved_work / rel` 触发 `TypeError` 的隐患，改为 `missing_paths.append(rel); continue` 回退到 `CLEAN_ROOM_SYNTHETIC`；同时在 `138`/`140`/`142` 测试辅助函数 `_donors_available_here` 增设 `if work_root is None: return False`。
   - 并在 `evaluate_142gate_preflight` 内部对 `resolved_work_root is None` 场景兜底透传 `force_clean_room=True` 至下层 `evaluate_140gate_preflight`（避免绕开权限边界修改 `132..140` 既有守卫文件）。
   - 模拟 GitHub Actions Ubuntu 无 donor 环境（`FX3_FX6_FORCE_CLEAN_ROOM=1` + `_iter_work_roots()` 返回 `()`）实测全量 **`4,023 / 4,023 OK (skipped=5)`**（`59.526s`，`0` 失败、`0` 错误）；本地 `LOCAL_DONOR_O_RDONLY` 模式全量 **`4,023 / 4,023 OK`**（`164.526s`）。
3. **所有硬核安全红线保持永久锁死**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`agent_auto_flash_blocked = True`、`human_hardware_attach_token = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`physical_flash_auto_exec_authorized = False`、`cross_model_flash_authorized = False`、`usb_packets_transmitted = 0`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 一、实测事实 vs 推断边界（Strict Fact / Inference Separation）

| 类别 | 具体内容 | 证据来源 |
| :--- | :--- | :--- |
| **实测事实（Donor 只读 `os.O_RDONLY` + `os.pread`）** | [`audit_phase319_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py) 在 `0.002529s`（`< 0.20s` 预算）内完成 11 项本地 donor 只读核验（`raw_firmware_bytes_leaked = 0`）：`FX3 appFw.so`（`79,015,712 B`，30 个精准切片联合 SHA-256 `ab7e0fcf0c81666fe90e64034497f574e43e94f5765d928f94d59ed482675559`）、`FX6 appFw.so`（`50,520,424 B`，16 个精准切片联合 SHA-256 `251ed8daff1bafd34ece44804f3e11c6717f40d4ac63033aa717537ef227d4ac`）、FX3 `string_english_f.uxc` / `.uxc` / `_g.uxc` / `_simplifiedchinese_f.uxc` / `_traditionalchinese_f.uxc`（实测精准词条 `對焦變換速度`）/ `_japanese_f.uxc`、`FX3-CX95900_ALLLANG-Backup.bin` 与 FX6 `string_english.uxc` / `_2.uxc` 全数哈希一致。 | [Wave-61 情报报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/reports/2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md) & [`audit_phase319_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py) |
| **实测事实（FX3 Ver. 7.02 vs FX6 Ver. 6.01 ELF/UXC 契约）** | `FX3` `[FTP Transfer Func.]` 精确暴露 9 个服务器槽位（`BKID_APP_ftp_server_settings_*0..8`）、仅支持 `FTP`/`FTPES` 被动模式，ELF 中 `sftp = 0`、`passive_mode = 0`、`_f 0x6aed`/`0x63dd`（`[Transfer JPEG/HEIF Size]`）`0` 命中，且 `save_ftp_transfer_list_to_media` / `.uxc 0x0a13` 写入 `AVF_INFO`；FX3 `[WB]` 含 `Custom 1..3` 与 `preserved_white_balance_adjustment_gm_custom_1..3`（排除出 `CAMSET*.DAT`）；**FX3 与 FX6 均对 `[AF Subj. Shift Sensitivity]` 使用 `1..5`**（FX6 `MOVIE_AF_SUBJ_SHIFT_SENS_1_LOCKED_ON..5_RESPONSICE`），且 **FX3 机身菜单无 `[Focus Map]`（`BKID_APP_USER_MENU_FOCUS_MAP = 0`）**，仅有 Ver. 6.00+ 外接 `Monitor & Control` 支持；FX3 `[Aspect Marker]` 为精确 15 个启用比例（含 `2.39:1`/`1.85:1`/`17:9`/`9:16` 等，不含 `2.40:1`/`21:9`）。 | `FX3 appFw.so` & `FX6 appFw.so` 实测符号与 UXC 切片审计 |
| **推断（工程化安全护栏与 Slot-1 / Zero-RF 防火墙）** | 对物理硬件未接入时的 `Slot-1` Tier-0 恢复保险库实施 `EROFS=30` 写拦截防火墙（禁止 `CONTENT_INFO_FTP_TRANS_STAT_*` / `save_ftp_transfer_list_to_media` / `recover` 改写 `Slot-1 AVF_INFO`，并强制 `cacert.pem` `<= 1 MB` 导入严格 `O_RDONLY`，锁死 `slot1_data_sector_writes == 0`）；因 `[Airplane Mode]=On` **不阻断**有线 `USB-LAN FTP`，台架 Zero-RF 隔离强制同时锁定 `Airplane Mode=On`、`FTP Function=Off` 与 `USB-LAN=Disconnected`（`rf_packets_transmitted=0`、`wired_usblan_ftp_packets=0`）；对休眠/跨机型伪造/越界状态返回确定性 errno（`EOPNOTSUPP=95` / `EINVAL=22` / `EROFS=30`）。 | [`verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py) & [`verify_movie_af_focusmap_marker_peaking_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h381-phase319-safety-142gates-ftp-ftpes-customwb-af-focusmap-marker/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py) |

---

## 二、Gate `G141` & `G142` 核心门禁设计摘要

### 1. Gate `G141`（`REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD`）
- **9 槽位 `FTP/FTPES` 与休眠项零容忍**：
  - `FX3` 严格限制 `Server 1..9`（`<= 9`），仅允许 `FTP`（端口 `21`）与显式 TLS `FTPES`（`Passive` 模式）；拒绝 `SFTP`（`22`）、隐式 `FTPS`（`990`）、`Active` 模式及休眠菜单 `[Transfer JPEG/HEIF Size]`（均返回 `EOPNOTSUPP=95`）；与 `Cloud Connection` 保持严格互斥；`Specify Directory` 上限 `63` 字符。
  - 对比 `FX6`（UI `1..3` 槽、ELF `16` 槽上限、`Passive Mode On/Off`、`certification.pem` 于 `Slot B`、`Chunk` Proxy 与 `Simul/Relay Rec` 互斥）。
- **CRITICAL `Slot-1 AVF_INFO` 防火墙与 Zero-RF `USB-LAN` 旁路陷阱**：
  - FTP 状态写入或 DB 恢复请求命中 `Slot 1` Tier-0 保险库时立即返回 `EROFS=30`（`slot1_data_sector_writes == 0`），仅允许 `Slot 1` 根目录下 `<= 1 MB` 有效 `cacert.pem` 以 `O_RDONLY` 只读导入。
  - Zero-RF 台架模式强制**三联锁**：`Airplane Mode = On` + `FTP Function = Off` + `USB-LAN/Tethering = Disconnected`（且无 Wi-Fi AP/配对残留），防止开启飞行模式后仍通过有线 USB-LAN 绕过传输数据。
- **White Balance & `Cine EI` / `0x0220` 契约**：
  - `C.Temp./Filter` `2500K..9900K`（步进 `100K`）与 `A-B`（`-7.0..+7.0`，`0.25` 步进）/ `G-M`（`-7.0..+7.0`，`0.5` 步进）；`Custom 1..3` 严禁导出至 `CAMSET*.DAT`，且仅 `[Initialize]` 会清空存储槽位（`[Camera Settings Reset]` 仅把活动模式重置为 `Auto`）；`Log != Off` / `S-Log3` / `PPLUT1..4` 下校准触发 `Custom WB Error 0x0220`（`EINVAL=22`）；`Cine EI` / `Cine EI Quick` 锁定 `Auto` 与 `Underwater Auto`；对比静止模式专属 `[Shutter AWB Lock]`（穿透 `Camera Settings Reset`）与视频 `[Shockless WB]`（`Off/1/2/3`）/ `[Priority Set in AWB]`，以及 `FX6` `PRST/A/B` + `Memory A..H` + `Cine EI` 下锁定 `ATW`。
- **256 状态全量矩阵 `compute_ftp_ftpes_customwb_matrix()`**：`states_checked=256`、`sftp_rejected_count=64`、`slot1_avf_blocked_count=128`、`usblan_bypass_blocked_count=160`、`customwb_0x0220_count=64`，全状态 `slot1_data_sector_writes == 0`。

### 2. Gate `G142`（`REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD`）
- **Movie AF `1..7` / `1..5` 双机型实证与 `[AF Assist]` 镜头白名单**：
  - 纠偏关键事实：`[AF Transition Speed]` 为 `1..7`（默认 `5`），而 **`[AF Subj. Shift Sensitivity]` 在 `FX3` 与 `FX6` 上均严格为 `1..5`**（FX3 默认 `5`，`6`/`7` 在双机型均返回 `EINVAL=22`）；`[AF Assist]` 默认 `Off`（随相机设置重置），且在 `SELP1650`/`SEL18200LE` 上被拒绝（`EINVAL=22`）。
- **CRITICAL `[Focus Map]` 机身菜单纠偏与外接限制**：
  - 严正拦截 FX3 存在机身内置 `[Focus Map]` 菜单（所谓 `Ver. 2.00` 谣言）的伪造请求（`EOPNOTSUPP=95`）；验证 FX3 仅自 `Ver. 6.00` 起通过外接 `Monitor & Control` 提供 Focus Map（`100p/119.88p` **仍支持**，仅 `>= 150fps`、Still 模式、回放、`Auto Framing`、非 PDAF/转接环/无镜头、USB 有线遥控、UVC 推流、HDMI RAW、对焦放大、数字增倍或伪造烧录至 HDMI/录制时拒绝 `EINVAL=22`）；对比 FX6 原生机身 `Focus Map`（`< 7fps` 与 `>= 150fps` 禁用）。
- **精确 15 比例 `[Aspect Marker]` 与 `[Peaking Display]` 永不输出 HDMI**：
  - 验证 FX3 严格拥有 `15` 个启用比例 + `Off` 共 `16` 态（拒绝 `2.40:1`/`Custom` -> `EOPNOTSUPP=95` 与 `21:9`/`1.33:1` -> `EINVAL=22`）；`Safety Zone` 为 `Off/80%/90%`（拒绝 FX6 `92.5%/95%`）；`Peaking Color` FX3 默认 `White`（4 色不含 `B&W`）vs FX6 默认 `B&W`（4 色不含 `White`）；**5 项 Marker + 3 项 Peaking 全部穿透 `[Camera Settings Reset]`（仅 `[Initialize]` 归零）**，且二者永不输出至 HDMI 信号；`Marker` 在对焦放大时自动隐藏；FX3 拒绝 FX6 专属 `User Box` 与 `Aspect Mask`（`EOPNOTSUPP=95`）。
- **512 状态全量矩阵 `compute_movie_af_focusmap_marker_peaking_matrix()`**：`states_checked=512`、`af_range_blocked_count=256`、`onbody_focusmap_blocked_count=128`、`external_focusmap_valid_count=128`、`marker_peaking_reset_survived_count=256`。

---

## 三、端到端实测验证日志

| 验证项 | 命令 / 场景 | 实测结果 |
| :--- | :--- | :--- |
| **Phase 319 单元测试（Donor 只读模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest tests/test_realhw_ftp_ftpes_customwb_af_focusmap_marker_142gate_guard.py` | **92/92 OK** (`14.252s`) |
| **Phase 319 单元测试（`FX3_CLEAN_ROOM_TEST=1`）** | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest tests/test_realhw_ftp_ftpes_customwb_af_focusmap_marker_142gate_guard.py` | **92/92 OK (skipped=2)** (`10.870s`) |
| **Phase 319 单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest tests/test_realhw_ftp_ftpes_customwb_af_focusmap_marker_142gate_guard.py` | **92/92 OK (skipped=2)** (`10.913s`) |
| **Donorless `work_root=None` CI 专项回归** | Mock `resolve_donor_thermal_power_paths` `.work_root=None` + `repo_root=/tmp/nonexistent-donorless-repo` 验证 `audit_phase288/290/294/297/299/319` 与 `124/130/138/140/142` 目标测试；全套 `FX3_FX6_FORCE_CLEAN_ROOM=1` + `_iter_work_roots=()` | 6 项 `audit` 全返回 `CLEAN_ROOM_SYNTHETIC`；CI 模拟全量 **`4,023/4,023 OK (skipped=5)`** (`59.526s`) |
| **`verify-142-gates` 离线 & Dry-Run CLI** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-142-gates [--clean-room --simulate-bench-dry-run] --summary` | 离线 **`139/142`**（`VERIFIED_139_OF_142_AWAITING_PHYSICAL_TIER0`）；Dry-Run **`142/142`**（`VERIFIED_ALL_142_GATES_DRY_RUN_SIMULATED_BACKUP`），`raw_firmware_bytes_leaked=0` |
| **`G141` & `G142` 独立 CLI 子命令** | `verify-ftp-ftpes-avf-vault-customwb-guard --summary` & `verify-movie-af-focusmap-marker-peaking-guard --summary` | 均 **`valid=True`**（`STATUS_VERIFIED_G141` / `STATUS_VERIFIED_G142`，`s1_writes=0`，`zero_rf_usblan=True`，`onbody_fm=False`，`peaking=White`） |
| **`outputs/fx3-safety` 全量单元测试发现（默认 Donor 模式）** | `python3 -m unittest discover -s tests` | **4,023/4,023 OK** (`164.526s`) |
| **Milestone 311 & 295 主控联合门禁（Donor + Clean-Room）** | `make verify-milestone-311` & `make verify-milestone-295` | **ALL OK**：动态自动发现 `evaluate_142gate_preflight`，`gate134=139/142`、`gate124=139/142`、`pillars=6/6`、`recovery=55/55`、`auditors=45/45`、`vm_stages=65/65`、`rf_pkts=0`、`usb_tx=0`、`leaked=0` |
| **Clean-Room 卫生审计** | `make clean-audit` | **`ALL GREEN`** (`0.04s`) |
