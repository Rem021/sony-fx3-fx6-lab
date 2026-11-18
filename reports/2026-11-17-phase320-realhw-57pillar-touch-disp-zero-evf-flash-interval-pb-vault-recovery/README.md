# Phase 320 工程交付报告：Recovery Pillar 57（Wave-55）与 `57/57` 统一恢复总检（`verify-57pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`57/57` 恢复支柱闭环，`VERIFIED_57OF57_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：围绕 Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，`PRODUCT_MODEL_ALCIN_UUD`）与 `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）**Wave-55** 实证机制，完成 **Phase 320 Recovery Pillar 57**（Sub-Pillar **57A** & **57B**）及并发式 **57/57 统一恢复总检聚合器** `evaluate_realhw_57pillar_recovery_master`（`schema_version = "realhw_57pillar_recovery_master_v1"`，`verify-57pillar-recovery`），并由 Milestone 311 与 Milestone 295 自动发现接管至 **`recovery=57/57`**。
- **关键实测结果（本地 `O_RDONLY` 供体模式 & 洁净室模式双轨全过）**：
  - `verify-57pillar-recovery`（`LOCAL_DONOR_O_RDONLY`）：`pillars=57/57`，`all_passed=True`，耗时 **`1.087s`–`1.175s`**（`< 1.5s` 快速 CLI 预算），`raw_firmware_bytes_leaked=0`，`slot1_data_sector_writes=0`，`slot1_edit_avf_info_mutation_bytes=0`，`slot1_avf_info_mutated=False`，`slot1_vault_mutation_bytes=0`，`master_57pillar_sha256=9579fd48cc652907ae744a7ab5b5cd8a222cdda654c601b7d5602a3e98415222`。
  - `verify-57pillar-recovery --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`pillars=57/57`，`all_passed=True`，耗时 **`0.502s`–`0.775s`**（`< 1.5s`），`raw_firmware_bytes_leaked=0`，`master_57pillar_sha256=744ca17e73722e5d9b7431c98321ad545a52f1cf9834d56ab80e2eeb6a9e3b87`。
  - `verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault`：Pillar `57A=6/6`、`57B=6/6`，有界只读核验 **17 项** Wave-55 供体（`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`）；`LOCAL_DONOR_O_RDONLY` 耗时 **`0.0037s`**（`suite_sha256=0dc38b458b2bd745ddab577c26c3f1d0e6d57470a1e57d579090225cc179385f`），`CLEAN_ROOM_SYNTHETIC` 耗时 **`0.0003s`**（`suite_sha256=3dcc69edf089cf8bfa7575b149bda001a9d256e026a56a7a1c613d40e4d002ad`）。
  - Milestone 311 & Milestone 295（`make verify-milestone-311` / `make verify-milestone-295` 双轨）：`LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 均返回 **`status=OK pillars=6/6 recovery=57/57 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 ready_attach=False cross_model_flash_auth=False leaked=0`**。
  - **硬件安全护栏硬锁**：`overall_ready_for_hardware_attach == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`physical_device_writes == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 2. Wave-55 实测事实 vs 工程推断边界

> 下表严格区分来自 Sony `ILME-FX3`（`ilc/2210` + `Ver. 7.02 appFw.so` / UXC / `Backup.bin`）与 `ILME-FX6`（`5-024-458-18` + `Ver. 6.01 appFw.so` / UXC）的 **实测事实**，以及恢复子系统所施加的 **工程推断 / 安全护栏**。

### 2.1 Sub-Pillar 57A：Wave-55 `[Touch Operation]` 4 项树 vs 休眠触控陷阱 & 4-Shoot/3-PB `[DISP Set]` 零 EVF 黑屏守卫

1. **实测事实 — `MENU -> (Setup) -> [Touch Operation]`（`_g 0x6345`, `base 0xe8e3`）精确 4 项且全数 `Initialize`-only**：
   - **`[Touch Operation]`**（`BKID_APP_setting_touch_operation`）：`On`（默认）/ `On: Playback Only`（`_f 0x6cde`）/ `Off`。
   - **`[Touch Sensitivity]`**（`_f 0x739f`，`BKID_APP_setting_touch_sensitivity`）：`Standard`（默认）/ **`Sensitive`**（`_f 0x7205`，非 `Responsive`）。
   - **`[Touch Func. in Shooting]`**（`_f 0x7575`，`BKID_APP_setting_shooting_touch_function`）：`Still`、`Movie`、`S&Q` 三域完全一致，仅 **`Touch Focus`**（`_f 0x6e79`/`0x7427`）/ **`Touch Tracking`**（默认，`_f 0x68f4`/`0x69ee`）/ **`Off`**。
   - **`[Swipe Up]`**（`_f 0x7518`，`BKID_APP_setting_swipe_up`）：`Open the Fn Menu`（默认，`_f 0x7281`）/ `Off`（仅当 `Touch Operation == On` 时激活）。
   - 以上 4 项全部抵抗 `[Camera Settings Reset]` 与 `[Reset Network Set.]`，仅随 `[Initialize]` 归位默认值。
2. **实测事实 & 工程护栏 — 7 项休眠 Alpha 触控符号 `EOPNOTSUPP=95` 阻断 vs `ILME-FX6` 边界**：
   - 虽 `FX3 appFw.so` / `.uxc` 中残存共享 BIONZ XR 符号，但在真实 `ILME-FX3` 上全数 **0 命中**，因此恢复网关/Stage-B **fail-closed 返回 `EOPNOTSUPP=95`**：`Touch Shutter`（`_f 0x6a80`/`0x62d5`）、`Touch AE`（`_f 0x702a`）、`Touch Panel/Pad`（`BKID_APP_setting_touch_panel_pad`, `_f 0x76ec`）、`Touch Pad Settings`、`Footer Icon Touch`（`_f 0x70da`）及 `Swipe Left`/`Swipe Right`（`_f 0x6b06`/`0x6c19`）。
   - 严格区分 `ILME-FX6 Ver. 6.01`：`Technical > Touch Operation`（`On`/`Off`）+ `Shooting > Focus > Touch Function in MF`（`Spot Focus`/`Tracking AF`），无灵敏度或上滑菜单。
3. **实测事实 & 推断防线 — `[Operation Customize] -> [DISP (Screen Disp) Set]` 与 Zero-EVF Blackout Guard**：
   - **实测事实**：路径为 `MENU -> (Setup) -> [Operation Customize] -> [DISP (Screen Disp) Set]`（`_g 0x61c4 -> 0x61da`，**非** `Display Option`，`Initialize`-only）。拍摄页固定 4 项（`Display All Info.` `0xea0e`、`No Disp. Info.` `0xe9f9`、`Histogram` `0xe07b`、`Level` `0xe8bc`），回放页固定 3 项（`Display Info.`、`Histogram`、`No Disp. Info.`）。
   - **实测事实 + 工程推断（零 EVF 黑屏守卫）**：`ILME-FX3` 机身 **无内置 EVF、无眼部传感器、无 `FINDER/MONITOR` 键**。若恢复/Stage-B 误触发共享符号 `BKID_APP_setting_finder_monitor`（`FINDER_MONITOR_FINDER` / `VIEW_FINDER`）、`BKID_APP_disp_mode_shoot_finder`、`Select Finder/Monitor`（`_f 0x74f9`）、`For viewfinder`（`_f 0x62d3`/`0xe2e5`）、`Graphic Display`（`0xe07a`）或 `Monitor Off`，推断将在无取景器机身上导致 **LCD 切屏黑屏假死**；校验器对上述 12 项休眠取景器/显示陷阱强制 fail-closed `EOPNOTSUPP=95` 并锁定 `evf_scanout_blocked=True`、`lcd_panel_scanout_preserved=True`，并与 `ILME-FX6`（`VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST` + 可拆卸 3.5" LCD `Viewfinder` + `Viewfinder Hood`，绝非 `"Loupe"`）严格隔离。

### 2.2 Sub-Pillar 57B：Still-Only `[AEL w/ Shutter]` & 闪光灯 Reset 分裂 + 9 档 Interval PB & 回放 `[Edit]` `Slot-1` Tier-0 `EROFS=30` 防火墙

1. **实测事实 — 4 项仅 Still 生效（`Movie`/`S&Q` -> `EOPNOTSUPP=95`）测光/闪光灯项与非对称 Reset**：
   - **`[AEL w/ Shutter]`**（`_f 0x669d`，`BKID_APP_setting_still_image_ael_w_shutter`）：`Auto`（默认）/ `On` / `Off`，`Initialize`-only，`[AEL toggle]` 自定义键激活时覆盖半按快门锁定。
   - **`[Exp.comp.set]`**（`_f 0x73c2`，位于 `(Exposure/Color) -> [Flash]` 下，`BKID_APP_setting_exp_comp_set`）：`Ambient&flash`（默认，`_f 0x6efe`）/ `Ambient only`（`_f 0x7617`），`Initialize`-only。
   - **`[Wireless Flash]`**（`_f 0x6201`，`BKID_APP_setting_wireless_flash`）：`Off`（默认）/ `On` —— **以上 4 项中唯一受 `[Camera Settings Reset]` 复位为 `Off` 的菜单项**（`can_be_reset=True`）。
   - **`[External Flash Set.]`**（`_f 0x6771`，`[Ext. Flash Firing Set.]` `0x671d` + `[Ext. Flash Cust. Set.]` `0x705f`）：`Initialize`-only，强制直插 MI 热靴（拒绝有线同步线离机及通过相机菜单配对/复位外闪）；对比无机械快门与 TTL 闪光系统的 `ILME-FX6`（仅含卷帘快门补偿项 `Flash Band Reduce` `FX6_2 0x4215`）。
2. **实测事实 — `MENU -> (Playback) -> [Viewing]`（`_g 0x6033`，非 `Playback Option`）9 档 Interval PB**：
   - `[Cont. Play for Interval]`（`_f 0x78fa`，旧别名 `Cont. PB for Interval` `0x72e6`）与 `[Play Speed for Interval]`（`_f 0x639e`，旧别名 `PB Speed for Interval` `0x72bd`，`BKID_APP_setting_continuous_playback`）实机暴露 **`1..9` 档速度刻度**（`CONTINUOUS_PLAYBACK_SPEED_1..9`，默认 `5`，`Initialize`-only，纯只读游标浏览 `safe_read_only=True`，不支持机内合成延时视频）。
3. **实测事实 + 工程推断（`Slot-1` Tier-0 保险库 `EROFS=30` / `EOPNOTSUPP=95` 防火墙）**：
   - `MENU -> (Playback) -> [Edit]`（`_g 0x6418`）实机激活 4 项：`[Rotate]`（`0xe5ae`/`0x795a`）、`[Photo Capture]`（`0x6856`）、`[JPEG/HEIF Switch]`（`0x6938`，`JPEG` 默认 / `HEIF(4:2:0)` / `HEIF(4:2:2)`）与 `[Copy]`（`0x79fc`）。
   - **关键风险与工程护栏**：`[Select Playback Media]` 出厂默认指向 **`Slot 1`**。当 `Slot 1` 挂载只读 Tier-0 恢复保险库时，在 `Slot 2` 允许执行的 `[Rotate]` / `[Photo Capture]` / `[Copy]` 若目标指向 `Slot 1`，**必须 fail-closed 拦截并返回 `EROFS=30`**（`slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`）。
   - 休眠 Alpha 编辑陷阱 `[Beauty Effect]`（`_f 0x7849`, `API_START_BEAUTYEFFECT_DETECTION`）与 `[Trimming]`（`sequence_edit_trimming_*`）全局返回 **`EOPNOTSUPP=95`**，若目标涉及 `Slot 1` 则叠加 **`EROFS=30`**。

---

## 3. 严格 6 文件交付清单（File Ownership Inventory）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py) | Pillar 57A/57B 状态机与评估器、17 项 `O_RDONLY` 供体有界核验（`< 0.2s`）+ 洁净室回退（含 `work_root is None` 防护）、`6/6 + 6/6` 场景套件及并发 `57/57` 主控 `evaluate_realhw_57pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 无重叠导出全部 Phase 320 `P320_*` / `PHASE320_*` / `MASTER_57_*` / `evaluate_realhw_57pillar_recovery_master` 等符号（供 Milestone 311 / 295 自动发现 `57`） |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault` 与 `verify-57pillar-recovery` CLI 子命令（`--json`、`--out`、`--force-clean-room`/`--clean-room`） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 320 `57/57` 恢复支柱与运行命令文档 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py) | **90 项**双模单元测试（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`sys.executable`、前向兼容发现与 CLI） |
| 6 | NEW | [`reports/2026-11-17-phase320-realhw-57pillar-touch-disp-zero-evf-flash-interval-pb-vault-recovery/README.md`](README.md) | 本 Phase 320 中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 57 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_realhw_57pillar_*.py"` | **`90/90 OK`**（`skipped=0`，`14.978s`） |
| Pillar 57 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest discover ... -p "test_realhw_57pillar_*.py"` | **`90/90 OK`**（`skipped=0`，`14.712s`） |
| Pillar 57 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest discover ... -p "test_realhw_57pillar_*.py"` | **`90/90 OK`**（`skipped=0`，`14.021s`） |
| `verify-pillar57-...` CLI（供体 / 洁净室） | `verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault` & `--force-clean-room` | **`57A=6/6, 57B=6/6, donors=17`**（`0.004s` / `0.000s`，`leaked=0`） |
| `verify-57pillar-recovery` CLI（供体 / 洁净室） | `verify-57pillar-recovery` & `--force-clean-room` | **`57/57 PASS`**（`1.087s` / `0.775s` `< 1.5s`，`leaked=0`） |
| `make verify-milestone-311`（双模式） | `make verify-milestone-311` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-311` | **`status=OK pillars=6/6 recovery=57/57 leaked=0`**（`0ef3e601...` / `9b4d3186...`） |
| `make verify-milestone-295`（双模式） | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **`status=OK pillars=6/6 recovery=57/57 leaked=0`**（`eaf16c6c...` / `4c7def26...`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN in 0.06s`** |
| `fx3-recovery-adapter` 全套 `unittest discover`（`/usr/bin/python3 -B`，本地供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,305 tests OK`**（`skipped=1`，`379.322s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`/usr/bin/python3 -B`，强制洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,247 tests OK`**（`skipped=16`，`298.326s`） |
