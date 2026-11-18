# Phase 314 工程交付报告：Recovery Pillar 56（Wave-54）与 `56/56` 统一恢复总检（`verify-56pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`56/56` 恢复支柱闭环，`VERIFIED_56OF56_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：围绕 Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，`PRODUCT_MODEL_ALCIN_UUD`）与 `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）**Wave-54** 实证机制，完成 **Phase 314 Recovery Pillar 56**（Sub-Pillar **56A** & **56B**）与并发式 **56/56 统一恢复总检聚合器** `evaluate_realhw_56pillar_recovery_master`（`schema_version = "realhw_56pillar_recovery_master_v1"`，`verify-56pillar-recovery`），并由 Milestone 311 与 Milestone 295 自动发现接管至 **`recovery=56/56`**。
- **关键实测结果（本地 `O_RDONLY` 供体模式 & 洁净室模式双轨全过）**：
  - `verify-56pillar-recovery`（`LOCAL_DONOR_O_RDONLY`）：`pillars=56/56`，`all_passed=True`，耗时 **`1.069s`–`1.074s`**（`< 1.5s` 快速 CLI 预算），`raw_firmware_bytes_leaked=0`，`slot1_data_sector_writes=0`，`slot1_copy_avf_info_mutation_bytes=0`，`slot1_vault_mutation_bytes=0`，`master_56pillar_sha256=f95ae6aa7c1cde44f941a543689baedb1188e4002fd53f58c5fb5bc887b2c97d`。
  - `verify-56pillar-recovery --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`pillars=56/56`，`all_passed=True`，耗时 **`0.447s`–`0.768s`**（`< 1.5s`），`raw_firmware_bytes_leaked=0`，`master_56pillar_sha256=ae8a6d654765f0f17a62177ab691f2c56bb629d6fb942c69c838d5f99e6f2eb8`。
  - `verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault`：Pillar `56A=6/6`、`56B=6/6`，核验 **17 项** Wave-54 只读供体；`LOCAL_DONOR_O_RDONLY` 耗时 **`0.0037s`**（`suite_sha256=7661381f6c242252f317d8aba8457cce33a2840edbe001213d59e273004de172`），`CLEAN_ROOM_SYNTHETIC` 耗时 **`0.0003s`**（`suite_sha256=46abbfd9cb12bf435b72c201e7e882d96981a083d7eb919496259f6ba404ed25`）。
  - Milestone 311 & Milestone 295（`make verify-milestone-311` / `make verify-milestone-295` 双轨）：`LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 均返回 **`status=OK pillars=6/6 recovery=56/56 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 ready_attach=False cross_model_flash_auth=False leaked=0`**。
  - **硬件安全护栏硬锁**：`overall_ready_for_hardware_attach == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`physical_device_writes == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 2. Wave-54 实证恢复契约与校验范围

### 2.1 Sub-Pillar 56A：Still `AF-C` 专属 `[Switch V/H AF Area]`、14 项 `[Focus Area Limit]` 与 `Initialize`-only `[Focus Area Color]`

1. **`[Switch V/H AF Area]`（`_f.uxc 0x73ae`，`BKID_APP_setting_vertical_horizontal_focus_area_switch`）**：
   - 支持 `Off`（`0x63aa`，出厂默认）、`AF Point Only`（`0x615a`）与 `AF Point + AF Area`（`0x69e8`），仅在 **Still `AF-C`** 生效。
   - 正常跟踪 `0_DEGREES`、`90_DEGREES`、`270_DEGREES` 三向横竖屏旋转；镜头垂直朝上/朝下俯仰返回 `INVALID` 且绝不触发切换；在 Movie、`S&Q`、非 `AF-C`（`AF-S`/`AF-A`/`DMF`/`MF`）、`iAuto`、数码变焦、AF 进行中、连拍、自拍倒计时及 `[Focus Magnifier]` 下严格锁定（`EBUSY=16`）。
   - 变更 `[Switch V/H AF Area]` 模式即清空三向记忆 AF 坐标，且支持 `[Camera Settings Reset]` 与 `[Initialize]` 复位至 `Off`。
2. **精确 14 项 `[Focus Area Limit]`（`_f.uxc 0x6de2`）**：
   - 精确建模 `ILME-FX3 Ver. 7.02` 暴露的 **14 项** `BKID_APP_focus_area_limit_*` 复选框（`wide`/`zone`/`center_fix`/`spot_s`/`spot_m`/`spot_l`/`expanded_spot` + 7 项仅 Still 生效的 `tracking_*`）；在 Movie/`S&Q` 下自动排除 7 项 `Tracking:*` 区域。
   - 强制最小启用 `>= 2` 项校验（仅剩 1 项或 0 项时触发 `.uxc 0xea28` -> `EINVAL=22`），并对 `appFw.so` 共享 BIONZ XR 代码库中的 5 项休眠符号（`flexible_spot_xl`、`flexible_spot_xs`、`custom_1..3`）严格 fail-closed 拦截并返回 `EOPNOTSUPP=95`。
3. **`Initialize`-only `[Focus Area Color]` vs 零切换 `ILME-FX6`**：
   - `[Focus Area Color]`（`_f.uxc 0x74ad`，`BKID_APP_setting_focus_frame_color`，`White` `.uxc 0xe883` 默认 / `Red` `.uxc 0xe8c6`）跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存，仅经 `[Initialize]` 归位 `White`。
   - 严格对照零 `[Switch V/H AF Area]`、零 `[Focus Area Limit]`、采用移动变橙色框与 `Focus Area Ind.(AF-S)`（`0x2236`）/ `Focus Area Marker`（`0x4d6b`）的 `ILME-FX6` 边界，阻断任何跨机型功能伪造（`P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF`）。

### 2.2 Sub-Pillar 56B：5 模式 `[Exposure Std. Adjust]`、7 项 `TC/UB` 格式锁与关键 `Slot-2 -> Slot-1` 反向 `[Copy]` 金库防火墙

1. **全 5 模式 `[Exposure Std. Adjust]`（`_f.uxc 0x6114`/`0x6f71`，`.uxc 0xe567` 确认提示）与 Still `[Bracket Settings]`**：
   - 明确消除“仅 4 种模式”伪认知，验证 `ILME-FX3` 支持**全部 5 种测光模式**（`Multi` `0x6d79`、`Center` `0x6da8`、`Spot` `0x7a8a`、`Entire Screen Avg.` `0x6f15`、`Highlight` `0x7600`）× 13 档步进（`-1..+1 EV`，`1/6 EV` 步进），经 `PID_SET_STANDARD_EXPOSURE_SETTING` 独立写入 EXIF（绝不篡改 `[Exposure Comp.]`）、同步偏移 `M.M.` 基线、包围曝光中途调整即复位已拍张数，且**跨越 `[Camera Settings Reset]` 留存（`Initialize`-only）**。
   - 对比验证 Still `[Bracket Settings]`（`[Selftimer during Bracket]` `Off/2/5/10 Sec`、`[Bracket order]` `0->-->+` / `-->0->+`）支持 `[Camera Settings Reset]`，并隔离 `ILME-FX6` 零命中 `exposure_standard` 与休眠 `bracket_*`（`ENOENT=2`）。
2. **7 项 `Initialize`-only `[TC/UB]` & `[TC/UB Disp. Setting]` + 制式/帧率锁 vs `ILME-FX6` 物理 BNC**：
   - 全部 6 项 `MENU -> Shooting -> [TC/UB]` 参数 + `MENU -> Setup -> Display Option -> [TC/UB Disp. Setting]`（`Counter`/`TC`/`U-Bit`，`_f.uxc 0x6b0c`，回放仅动态影像可切换 `.uxc 0xe728`）全部跨越 `[Camera Settings Reset]` 留存，仅随 `[Initialize]` 复位。
   - `[Time Code Format]`（`DF`/`NDF`，`_f.uxc 0x6e3d`）仅 NTSC 可用，在 `23.98p` / `24.00p` 下强制锁定为 `NDF`（`[-]`），在 `PAL` 下隐藏；严格区分无物理 BNC 时码口的 `FX3` 与配备实体 BNC `TC IN/OUT` 开关（`EXT-LK`）及 `Users Bit Mode: Fix/Time` 的 `FX6`。
3. **CRITICAL 关键 `Slot-2 -> Slot-1` 反向 `[Copy]` Tier-0 恢复金库防火墙 + `[Slide Show]` 省电旁路**：
   - `MENU -> Playback -> Edit -> [Copy]`（`FUNC_copy_content`）以 `[Select Playback Media]`（默认 `Slot 1`）为源卡复制到对侧槽位：`Slot 1 -> Slot 2` 仅只读 `Slot 1`、校验 `get_battery_status_for_copy` 与目标卡速率，并在目标卡清除群组与 `Protect` 标志。
   - 一旦操作切换 **`[Select Playback Media] = Slot 2` 并触发 `[Copy]`，写盘目标立即反转为 `Slot 1`**（创建 `DCIM`/`M4ROOT` 与重构 `AVF_INFO` ImageDB）——只要 `Slot 1` 挂载 Tier-0 恢复金库，防火墙 **MUST fail-closed 阻断并返回 `EROFS=30` / `EBUSY=16`**，保证 `slot1_data_sector_writes == 0`、`slot1_copy_avf_info_mutation_bytes == 0`、`slot1_vault_mutation_bytes == 0`。
   - 同时校验 `[Slide Show]`（`Repeat: On/Off` 默认 `Off`，`Interval: 1/3/5/10/30 Sec` 默认 `3 Sec`，仅 `Date View` / `Folder View(Still)` 有效，`Initialize`-only 留存）在播放期间旁路 `[Power Save Start Time]`，及 `ILME-FX6` 休眠 `Copy Clip`（`0x4136`）。

---

## 3. 严格 6 文件交付清单（File Ownership Inventory）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py) | Pillar 56A/56B 状态机与评估器、17 项 `O_RDONLY` 供体有界核验（`< 0.2s`）+ 洁净室回退、`6/6 + 6/6` 场景套件及并发 `56/56` 主控 `evaluate_realhw_56pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 无重叠导出全部 Phase 314 `P314_*` / `PHASE314_*` / `MASTER_56_*` / `evaluate_realhw_56pillar_recovery_master` 等符号（供 Milestone 311 / 295 自动发现 `56`） |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault` 与 `verify-56pillar-recovery` CLI 子命令（`--json`、`--out`、`--force-clean-room`/`--clean-room`） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 314 `56/56` 恢复支柱与运行命令文档 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py) | **88 项**双模单元测试（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`sys.executable`、前向兼容发现与 CLI） |
| 6 | NEW | [`reports/2026-11-17-phase314-realhw-56pillar-switch-vh-af-stdadj-tcub-copy-vault-recovery/README.md`](README.md) | 本 Phase 314 中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 56 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier.py` | **`88/88 OK`**（`13.970s`） |
| Pillar 56 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest ...` | **`88/88 OK`**（`11.993s`） |
| Pillar 56 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest ...` | **`88/88 OK`**（`12.572s`） |
| `verify-pillar56-...` CLI（供体 / 洁净室） | `verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault` & `--force-clean-room` | **`56A=6/6, 56B=6/6, donors=17`**（`0.0037s` / `0.0003s`，`leaked=0`） |
| `verify-56pillar-recovery` CLI（供体 / 洁净室） | `verify-56pillar-recovery` & `--force-clean-room` | **`56/56 PASS`**（`1.069s` / `0.447s` `< 1.5s`，`leaked=0`） |
| `make verify-milestone-311`（双模式） | `make verify-milestone-311` | **`status=OK pillars=6/6 recovery=56/56 leaked=0`**（`6fad58c4...` / `df1fb1cc...`） |
| `make verify-milestone-295`（双模式） | `make verify-milestone-295` | **`status=OK pillars=6/6 recovery=56/56 leaked=0`**（`05eea78d...` / `13cefe1d...`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN in 0.04s`** |
| `fx3-recovery-adapter` 全套 `unittest discover`（`/usr/bin/python3 -B`，本地供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,215 tests OK`（`skipped=1`，`355.724s`）** |
| `fx3-recovery-adapter` 全套 `unittest discover`（`/usr/bin/python3 -B`，强制洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,157 tests OK`（`skipped=16`，`301.627s`）** |
