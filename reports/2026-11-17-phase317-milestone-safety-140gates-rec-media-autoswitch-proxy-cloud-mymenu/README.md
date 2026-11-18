# Phase 317（`140/140` Safety Gates Grand Milestone!）：Wave-60 实机硬件安全门禁 `G139` & `G140` 与统一 `140/140` 预检引擎交付报告

- **日期**：`2026-11-17`
- **任务**：Task H378 — Phase 317（`140/140` Safety Gates Grand Milestone!）：Implement Wave-60 Hardware Safety Gates `G139` & `G140` and Unified `140/140` Preflight (`verify-140-gates`)
- **分支**：`codex/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu`
- **交付范围（严格单写域 6 文件）**：
  1. 新增核心守卫模块：[`realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py)
  2. 更新包导出与自动发现入口：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/__init__.py)
  3. 注册 CLI 子命令（`verify-rec-media-autoswitch-proxy-vault-guard` / `verify-creators-cloud-zerorf-mymenu42-guard` / `verify-140-gates`，含 `--json`、`--summary`、`--clean-room` 与 `--simulate-bench-dry-run`）：[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/__main__.py)
  4. 新增文档第 70 节：[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/README.md)
  5. 新增 92 项双模式/三环境变量单元测试（满足 `>= 86` 要求）：[`test_realhw_rec_media_autoswitch_proxy_cloud_mymenu_140gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/tests/test_realhw_rec_media_autoswitch_proxy_cloud_mymenu_140gate_guard.py)
  6. 本工程交付报告：`reports/2026-11-17-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/README.md`

---

## 核心结论（Executive Summary）

1. **已达成 `140/140` 实机硬件安全门禁总里程碑（Phase 317 Grand Milestone）**：
   - 离线默认模式（[`evaluate_140gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py) / `verify-140-gates`，`schema_version = "realhw_140gate_preflight_v1"`）：**`137/140` 门禁通过**（`VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0`，仅物理 Tier-0 备份回执 `G10..G12` 待人工台架接入），在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）下均实测通过。
   - 模拟演练模式（`--simulate-bench-dry-run`）：**`140/140` 门禁全绿通过**（`VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP`）。
   - **Milestone 311 & 295 动态自动发现实测确认**：`make verify-milestone-311` 与 `make verify-milestone-295`（各自动连续执行正常与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式）均自动发现最高入口 `evaluate_140gate_preflight`，动态输出 `gate134=137/140` / `gate124=137/140`、`pillars=6/6`、`recovery=55/55`、`auditors=45/45`、`vm_stages=64/64`、`rf_pkts=0`、`usb_tx=0`、`leaked=0`。
2. **所有硬核安全红线保持永久锁死**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`agent_auto_flash_blocked = True`、`human_hardware_attach_token = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`physical_flash_auto_exec_authorized = False`、`cross_model_flash_authorized = False`、`usb_packets_transmitted = 0`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。
3. **全量实测通过**：
   - Phase 317 新增 **92 项单元测试**（超过 `>= 86` 要求）在 **默认 (`LOCAL_DONOR_O_RDONLY`)**、**`FX3_CLEAN_ROOM_TEST=1`**、**`FX3_FX6_FORCE_CLEAN_ROOM=1`** 三种模式下全部通过（`92/92 OK` / `92/92 OK (skipped=2)` / `92/92 OK (skipped=2)`，耗时 `4.215s` / `2.130s` / `2.099s`）。
   - `outputs/fx3-safety` 全量单元测试发现在 **正常模式** 与 **`FX3_FX6_FORCE_CLEAN_ROOM=1`** 下均完成 **3,931 项测试**（`0` 失败、`0` 错误；分别耗时 `194.431s` 与 `82.594s`）。
   - `make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）审计 **`ALL GREEN`**（`0.05s`）。

---

## 一、实测事实 vs 推断边界（Strict Fact / Inference Separation）

| 类别 | 具体内容 | 证据来源 |
| :--- | :--- | :--- |
| **实测事实（Donor 只读 `os.O_RDONLY` + `os.pread`）** | [`audit_phase317_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py) 在 `0.004217s`（`< 0.20s` 预算）内完成 11 项本地 donor 只读核验（`raw_firmware_bytes_leaked = 0`）：`FX3 appFw.so`（`79,015,712 B`，24 个精准切片联合 SHA-256 `e30c37ef260d171bd836f36e6bfa1fe8cce93315f46482b5d2184ddb32b7b484`）、`FX6 appFw.so`（`50,520,424 B`，7 个切片联合 SHA-256 `6e4750954dcc9acc5140d6ac88e324e34eb0820e9ef4cff45e7a9bfa234e7beb`）、FX3 `string_english_f.uxc` / `.uxc` / `_g.uxc` / `_simplifiedchinese_f.uxc`（实测精准词条 `摄像媒体设置`）/ `_traditionalchinese_f.uxc` / `_japanese_f.uxc`、`FX3-CX95900_ALLLANG-Backup.bin` 与 FX6 `string_english.uxc` / `_2.uxc` 全数哈希一致。 | [Wave-60 情报报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/reports/2026-11-17-global-sony-wave60-milestone-rec-media-auto-switch-proxy-cloud-mymenu-intel/README.md) & [`audit_phase317_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py) |
| **实测事实（FX3 Ver. 7.02 vs FX6 Ver. 6.01 ELF/UXC 契约）** | `FX3 appFw.so` 实含拆分 `BKID_APP_setting_still_recording_media` / `BKID_APP_setting_movie_recording_media`（仅 Still 含 `SORT_RECORDING`）、`BKID_APP_setting_relay_rec`、`PRM_HAITA_setting_relay_rec_movie_setting_movie_recording_media_media_read_only_state_slot1`、`BKID_APP_setting_sq_proxy_{recording,file_format,record_setting}`、`BKID_APP_setting_cloud_connection`、`CLOUD_CONNECTION_ON_FTP_OFF`、`BKID_APP_extern_menu_cnct_while_power_off`、`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER`、`BLUETOOTH_PAIRING_LAUNCH_FUNCTION_SEND_AT_POWER_OFF`、`BKID_APP_mymenu_group1_setting_list0`..`group6_setting_list6`（`group0` / `group7` / `list7` 均 `0` 命中，精确 42 格）；而 `Prioritize`（`_f 0x719e`）在 FX3 中 `0` 命中、`FX6 appFw.so` 含 `SIMUL_REC` / `CHUNK_PROXY` / `USER_MENU_LOCK` 且无蓝牙 `Cnct. while Power OFF`。 | `FX3 appFw.so` & `FX6 appFw.so` 实测符号与 UXC 切片审计 |
| **推断（工程化安全护栏与 Slot-1 Tier-0 防火墙）** | 对物理硬件未接入时的 `Slot-1` Tier-0 恢复保险库实施 `EROFS=30` 写拦截防火墙（防止 `[Auto Switch Media] = On` 时 `Slot 2` 满/弹出导致回卷写入 `Slot 1` + `AVF_INFO`，以及 `Simult. Recording` / 联动删除保护 / `M4ROOT/SUB` / `CAMSET*.DAT` 导出写入 `Slot 1`，锁死 `slot1_data_sector_writes == 0`）；并在 Zero-RF 台架模式强制要求 `[Airplane Mode] == On` 且 `[Cnct. while Power OFF] == Off`（`rf_packets_transmitted == 0`），对休眠/虚构状态返回确定性 errno（`EOPNOTSUPP=95` / `EINVAL=22` / `ENODEV=19` / `EROFS=30`）。 | [`verify_rec_media_autoswitch_proxy_vault_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py) & [`verify_creators_cloud_zerorf_mymenu42_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h378-phase317-milestone-safety-140gates-rec-media-autoswitch-proxy-cloud-mymenu/outputs/fx3-safety/fx3_safety/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard.py) |

---

## 二、Gate `G139` & `G140` 核心门禁设计摘要

### 1. Gate `G139`（`[Recording Media]` 拆分、`[Auto Switch Media]` `Slot-2->Slot-1` 回卷与 `VPG200/400` 速率门、Proxy `M4ROOT/SUB` Slot-1 保险库防火墙）
- **Ver. 2.00+–7.02 `[Rec. Media Settings]` 拆分与复位层级**：
  - 永久拦截历史休眠菜单 `[Prioritize Rec. Media]`（`_f 0x719e`，在 FX3 `appFw.so` 中 `0` 命中 -> `EOPNOTSUPP=95`）。
  - 校验拆分为仅 `[Initialize]` 重置（穿透 `[Camera Settings Reset]`）的 **`[Recording Media]`**：`Still` 仅开放 `Slot 1` / `Slot 2` / `Simult. Recording` / `Sort Recording`，`Movie`/`S&Q` 仅开放 `Slot 1` / `Slot 2` / `Simult. Recording`（强拒 Movie `Sort Recording` -> `EINVAL=22`）；`Simult. Recording` 严格要求双槽文件系统同为 `exFAT` 或 `FAT32`。
- **CRITICAL `Slot-2 -> Slot-1` 溢出回卷陷阱（Tier-0 保险库防火墙）**：
  - **`[Auto Switch Media]`**（`_f 0x6dd9`、`BKID_APP_setting_relay_rec`）同样穿透 `[Camera Settings Reset]` 保留状态；一旦设定 `[Recording Media] = Slot 2` 且 `[Auto Switch Media] = On`，当 `Slot 2` 写满或拔卡时固件将静默把视频流与 `AVF_INFO` 回卷写入 `Slot 1`。门禁强制执行双保险锁死（`Auto Switch Media == Off` + 物理/逻辑 `Slot 1` `EROFS=30` 防火墙，保证 `slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == False`、`slot1_sub_dir_mutated == False`）。
- **卡速门与 `CFexpress Type B` 拒止**：
  - 覆盖 `XAVC HS/S 4K <=280M`（`SDXC V60+`，`<=200M` `U3/V30`，`<=60M` `Class 10`，`SDHC <=32GB` 标记 4GB 分片）、`XAVC S-I 4K / DCI 4K 600M`（`SDXC V90+`）、`S&Q XAVC S-I 4K 1200M` 与 `S&Q XAVC S-I HD 240/200fps 890M`（强制 `CFexpress Type A VPG200/VPG400`，对应 `base.uxc 0xe228`/`0xe224`；叠加 Proxy 时升格 `VPG400`）；`CFexpress Type B` 返回 `ENODEV=19`。
- **`[Proxy Settings]` 与 FX6 对比互斥**：
  - `_f 0x6e3f`（随 `[Camera Settings Reset]` 重置）：`XAVC S HD`（`1280x720 6M 8bit`）vs `XAVC HS HD`（`1920x1080 9M/16M 10bit`），拦截休眠 `16M 8bit`（`_f 0x6b8f`）/`9M_420_8BIT`；正确在 `119.88p/100p` 与 `S&Q 120/100fps` 禁用 Proxy，同时纠正“DCI 4K 禁用 Proxy”误传（`XAVC S-I DCI 4K <=59.94p` 允许 Proxy，受卡速门制约）；禁止机内回放 Proxy，并按 `SDXC` (`/PRIVATE/M4ROOT/SUB`) vs `CFexpress Type A` (`/M4ROOT/SUB`) 防护 `Slot-1` 保险库联动删改（对比 FX6 `Simul Rec` 与 `Chunk Proxy` 互斥）。
- **256 状态全量矩阵 `compute_rec_media_autoswitch_proxy_matrix()`**：`states_checked=256`、`slot1_vault_blocked_count=96`、`overflow_trap_count=32`、`proxy_fr_blocked_count=128`、`vpg_cfe_required_count=160`，全状态保持 `slot1_data_sector_writes == 0`。

### 2. Gate `G140`（`[Creators' Cloud]`/`[C3 Portal]`、Zero-RF `[Cnct. while Power OFF]` 与精确 42 格 `[My Menu]`）
- **`[Creators' Cloud]` 与 `[C3 Portal]`**：
  - 建模 `Cloud Connection *` / `Cloud Information *` **穿透甚至 `[Initialize]` 仍保留绑定**（必须显式账号登出清除）、`CLOUD_CONNECTION_ON_FTP_OFF` 与 FTP 严格互斥、`C3 Portal`（`Cloud(Private)`/`Cloud(Share)`）与 Ver. 7.00+ `Clip Flag`（`OK`/`NG`/`KEEP`）筛选。
- **CRITICAL Zero-RF 盲区（`[Cnct. while Power OFF]`）**：
  - 当 `[Cnct. while Power OFF] = On`（`_f 0x6ab3`，穿透 `[Camera Settings Reset]` 保留；同步记录 `_g 0x6476` 简繁空串缺陷）且已配对时，即使物理电源开关处于 `OFF`，`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER` 仍保持加电与 BLE 广播。
  - Zero-RF 台架模式强制要求 **同时满足 `[Airplane Mode] == On` 且 `[Cnct. while Power OFF] == Off`**（`rf_packets_transmitted == 0`），并与无蓝牙硬件的 `ILME-FX6` 形成对比。
- **精确 42 格 `[My Menu]` 纠偏与 FX6 `User Menu with Lock` 隔离**：
  - 证实 `ILME-FX3` `[My Menu]`（`_g 0x6232`）严格为 **`6 × 7 = 42` 格**（`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`），严厉拒绝 `30`/`36` 格误传、下标 `>= 42` 及 `(Playback)` 标签页注册（`EINVAL=22`）；穿透 `[Camera Settings Reset]` 保留；拦截向 `Slot 1` Tier-0 保险库导出 `CAMSET*.DAT`（`EROFS=30`）；对比并隔离 `ILME-FX6` **20 项 `User Menu`**、`User Menu Only` 与租赁 **`User Menu with Lock`**（`0000..9999` PIN、`Multi-Function Dial + MENU` 组合键、排除出 `All File` 导出，在 FX3 上返回 `EOPNOTSUPP=95`）。
- **256 状态全量矩阵 `compute_creators_cloud_zerorf_mymenu_matrix()`**：`states_checked=256`、`cloud_survived_init_count=16`、`ble_power_off_hazard_count=32`、`zero_rf_clean_count=96`、`slot1_camset_vault_blocked_count=128`。

---

## 三、端到端实测验证日志

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| **Phase 317 单元测试（Donor 只读模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_rec_media_autoswitch_proxy_cloud_mymenu_140gate_guard.py` | **92/92 OK** (`4.215s`) |
| **Phase 317 单元测试（`FX3_CLEAN_ROOM_TEST=1`）** | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_rec_media_autoswitch_proxy_cloud_mymenu_140gate_guard.py` | **92/92 OK (skipped=2)** (`2.130s`) |
| **Phase 317 单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_rec_media_autoswitch_proxy_cloud_mymenu_140gate_guard.py` | **92/92 OK (skipped=2)** (`2.099s`) |
| **`verify-140-gates` 离线 & Dry-Run（Donor 模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-140-gates [--simulate-bench-dry-run]` | 离线 **`137/140`**（`VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0`）；Dry-Run **`140/140`**（`VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP`），`raw_firmware_bytes_leaked=0` |
| **`verify-140-gates` 离线 & Dry-Run（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-140-gates --clean-room [--simulate-bench-dry-run]` | 离线 **`137/140`**；Dry-Run **`140/140`**，`verification_mode=CLEAN_ROOM_SYNTHETIC`，`raw_firmware_bytes_leaked=0` |
| **`G139` & `G140` 独立 CLI 子命令** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-rec-media-autoswitch-proxy-vault-guard` & `verify-creators-cloud-zerorf-mymenu42-guard` | 均 **`valid=True`**（`STATUS_VERIFIED_G139` / `STATUS_VERIFIED_G140`，`s1_writes=0`，`rf_pkts=0`，`mymenu_slots=42`） |
| **`outputs/fx3-safety` 全量单元测试发现（Donor + Clean-Room 双模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests`（含 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | Donor 模式 **3,931/3,931 OK** (`194.431s`)；Clean-Room 模式 **3,931/3,931 OK (skipped=3)** (`82.594s`) |
| **Milestone 311 & 295 主控联合门禁（Donor + Clean-Room）** | `make verify-milestone-311` & `make verify-milestone-295` | **ALL OK**：动态自动发现 `evaluate_140gate_preflight`，`gate134=137/140`、`gate124=137/140`、`pillars=6/6`、`recovery=55/55`、`auditors=45/45`、`vm_stages=64/64`、`rf_pkts=0`、`usb_tx=0`、`leaked=0` |
| **Clean-Room 卫生审计** | `make clean-audit` (`scripts/run_all_lab_tests.py --clean-only`) | **`ALL GREEN`** (`0.05s`) |
