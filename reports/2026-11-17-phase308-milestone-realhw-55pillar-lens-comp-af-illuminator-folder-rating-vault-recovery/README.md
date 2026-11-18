# Phase 308 里程碑工程交付报告：Recovery Pillar 55（Wave-53）与 55/55 统一恢复总检（`verify-55pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`55/55` 恢复支柱里程碑全绿闭环，`VERIFIED_55OF55_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：围绕 Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，`PRODUCT_MODEL_ALCIN_UUD`）与 `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）**Wave-53** 实证机制，完成 **Phase 308 Recovery Pillar 55**（Sub-Pillar **55A** & **55B**）与并发式 **55/55 统一恢复总检聚合器** `evaluate_realhw_55pillar_recovery_master`（`verify-55pillar-recovery`），并由 Milestone 295 自动发现接管至 **`recovery=55/55`**。
- **关键实测结果（本地 `O_RDONLY` 供体模式 & 洁净室模式双轨全过）**：
  - `verify-55pillar-recovery`（`LOCAL_DONOR_O_RDONLY`）：`pillars=55/55`，`all_passed=True`，耗时 **`1.054s`–`1.097s`**（`< 1.5s` 快速 CLI 预算），`raw_firmware_bytes_leaked=0`，`slot1_data_sector_writes=0`，`slot1_folder_dir_mutation_bytes=0`，`slot1_rating_avf_info_mutation_bytes=0`，`slot1_vault_mutation_bytes=0`，`master_55pillar_sha256=5774cedce5655746b1bf644ffbeb1d2d76afa48ef84f811285109de99c42efa6`。
  - `verify-55pillar-recovery --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`pillars=55/55`，`all_passed=True`，耗时 **`0.718s`–`0.738s`**（`< 1.5s`），`raw_firmware_bytes_leaked=0`，`master_55pillar_sha256=c4fff9ded87857fba9e1e3c7e6a52f614ae134c8be3eadca23b36798c8a86223`。
  - `verify-pillar55-lens-comp-af-illuminator-folder-rating-vault`：Pillar `55A=6/6`、`55B=6/6`，核验 **18 项** Wave-53 只读供体；`LOCAL_DONOR_O_RDONLY` 耗时 **`0.0034s`–`0.0040s`**（`suite_sha256=d8ea3553426607fcef0a2b6257c23055a09627d708e3616d180181344c028105`），`CLEAN_ROOM_SYNTHETIC` 耗时 **`0.0004s`**（`suite_sha256=4a3e165984449cf2d626f318aed622b11a6c96fe4c37fa8160804127c6945a33`）。
  - Milestone 295（`make verify-milestone-295` 双轨）：`LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 均返回 `status=OK pillars=6/6 gate124=131/134 recovery=55/55 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 ready_attach=False cross_model_flash_auth=False leaked=0`。
  - **硬件安全护栏硬锁**：`overall_ready_for_hardware_attach == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`physical_device_writes == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 2. Wave-53 实证恢复契约与校验范围

### 2.1 Sub-Pillar 55A：`[Lens Compensation]`（`Shading` `Auto`/`Off` vs 休眠 `Auto: Low`）与内置前置 `[AF Illuminator]` LED `#8` vs 零发光器 `ILME-FX6`

1. **`[Lens Compensation]`（`[Shooting] -> [Image Quality/Rec] -> [Lens Compensation]`，`_f.uxc` `0x75c8` / `.uxc` `0x631f`）**：
   - **`[Shading Comp.]`（`BKID_APP_setting_lens_comp_shading`，`_f.uxc` `0x64e1`，默认 `Auto`，`Initialize`-only）**：严格校验 `ILME-FX3 Ver. 7.02` 仅暴露 `Auto` 与 `Off` 两档；对跨机族 BIONZ XR 遗留的休眠枚举 `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW` / `_f.uxc` `0x6c9c`（`Auto: Low`）fail-closed 拒绝并返回 `EOPNOTSUPP=95`（`P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT`）。同时记录 `Auto` 会在部分索尼机身对 `.ARW` 施加原始暗角增益。
   - **`[Chromatic Aberration Comp.]`（`Auto`/`Off`，默认 `Auto`）与 `[Distortion Comp.]`（`Auto`/`Off`，默认 `Off`）**：二者均跨越 `[Camera Settings Reset]` 留存、仅随 `[Initialize]` 重置；针对需要几何校正的 E 卡口镜头（`VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED`，如 `SELP1650`、`FE 28-70mm`）或视频 `[SteadyShot] = Active` 强制锁定 `Distortion Comp. = Auto`，且证明畸变校正绝不烘焙至 `.ARW` 原始像素；针对无触点纯手动镜头（`VAL_launch_lens_comp_LENS_COMP_VALUE_NOT_EXIST`）全项置灰禁用。
   - **`[Breathing Comp.]`（`Ver. 3.00+`，`On`/`Off`，默认 `Off`，`Camera Settings Reset`-resettable）与 `ILME-FX6` 边界**：仅限 `Movie`，在 HDMI 外录 RAW 或不兼容镜头下禁用；严格隔离 `ILME-FX6 Ver. 6.01` 位于 `Technical > Lens`（非 `Project/Paint/Lens`）、保存于 `All File`（`s/SONY/PRO/CAMERA/`）且在 `Distortion Comp. = Off` / `S&Q = On` / `RAW` 编解码下强制锁 `Off` 的差异。
   - **Movie AF 动力学（`[AF Transition Speed]` `1..7` 默认 `5`、`[AF Subj. Shift Sensitivity]` `1..5` 默认 `5(Responsive)`、`[AF Assist]` 默认 `Off` 仅 `Movie`/`S&Q` `AF-C` 兼容镜头生效）**：全部受 `[Camera Settings Reset]` cleanly 复位。
2. **关键硬件纠偏 — 内置前置 `[AF Illuminator]` LED `#8` vs 零发光器 `ILME-FX6`**：
   - 推翻“FX3 机身无 AF 辅助灯”的错误假设：`ILME-FX3` 机身正面物理配备内置 `AF illuminator / Self-timer lamp / Visible light and IR sensor` LED（官方零件图 `TP1000886886.html` `#8`，有效照射 `0.3..3.0 m`）并联动 MI-Shoe 外接闪光灯 AF 辅助灯（`BKID_APP_setting_still_image_af_illuminator`，`.uxc` `0xe07f`，`_f.uxc` `0x69c0`，默认 `Auto`，随 `Camera Settings Reset` 复位）。
   - **严格模式门控**：内置 LED 与 MI-Shoe 辅助灯 **仅在 Still `AF-S`（及静止 `AF-A`）允许点亮**，在 `Movie`、`S&Q`、`AF-C`、`MF`、`Silent Mode = On`、`Focus Magnifier` 与转接环下均 100% 锁闭；对比 `ILME-FX6` 具备 **0 颗内置 AF 辅助灯 LED**（`appFw.so` 仅 6 条休眠符号），任何 `FX6` 宣称内置 LED 行为均被 `P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF` 拦截。

### 2.2 Sub-Pillar 55B：`[Aperture Drive in AF]` 等 5 项 `Initialize`-only 留存与 `[Create New Folder]` + 回放 `[Rating]` `Slot-1` Tier-0 金库防火墙

1. **5 项 `Initialize`-only 对焦/光圈设置（全部跨越 `[Camera Settings Reset]` 留存、仅随 `[Initialize]` 归位）**：
   - **`[Aperture Drive in AF]`**（Still-only）：`Focus Priority`（需显式确认高速连拍降速与机械音提示 `_g.uxc` `0x631a`/`0x63e2`）/ `Standard`（默认）/ `Silent Priority`。
   - **`[AF w/ Shutter]`**（Still-only，`On` 默认/`Off`）与 **`[Pre-AF]`**（Still-only，`On`/`Off` 默认，受 `LENS_PRE_AF_SUPPORT` 镜头门控）。
   - **`[Circ. of Focus Point]`**（Still/Movie/`S&Q`，`Circulate` / `Does Not Circulate` 默认）：强制验证 **仅限正交水平/垂直环绕**，严禁并硬拒绝 `Diagonal` 对角回绕。
   - **`[Focus Area Color]`**（Still/Movie/`S&Q`，`White` 默认 `.uxc` `0xe883` / `Red` `.uxc` `0xe8c6`）。
   - 严格隔离无此 5 项、改用 `Iris` 系统的 `ILME-FX6`（PXW-FX9 休眠词条 `0x4fc3` 在 `FX6 appFw.so` 呈 `0` 命中）。
2. **`[File/Folder Settings]`、`[Rating]`（`1..5` 星）与关键 `Slot-1` Tier-0 金库防火墙**：
   - 校验 `[Folder Name]`（`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` 禁用 `[Select REC Folder]`）、`[File Number]`（`Series`/`Reset`）、3 字符 `[Set File Name]` 前缀（`DSC` 默认，禁止前导 `_`）、单夹 `4,000` 张上限（`STATUS_OF_MEDIA_SLOT1_FOLDER_MAX`），以及回放 `[Rating]`（`1..5` 星 `FUNC_rating_content` / `VAL_xmp_rating_XMP_RATING_VALID`）、`[Rating Set(Custom Key)]` 与仅 Still 生效且禁覆盖的 `[Add Rating]`（`_g.uxc` `0x627d`），对比 `FX6` `XAVC Root Folder Name` 与 `Clip Flag`（`OK`/`NG`/`KEEP`）。
   - **CRITICAL `Slot-1` Tier-0 恢复金库防火墙**：`[Create New Folder]`（创建 `DCIM/1xxMSDCF`）、`[Forced File Number Reset]`、双卡同时录制 `[Select REC Folder]`、回放 `[Rating]`（篡改卡上 EXIF/XMP 与 `AVF_INFO` ImageDB）及 `[Add Rating]` 一旦指向 `Slot 1`（或双卡同时录制波及 `Slot 1`）或命中后台传输冲突，均 **MUST fail-closed** 拦截并给出 `EROFS=30` / `EBUSY=16`，强制保障 `slot1_data_sector_writes == 0`、`slot1_folder_dir_mutation_bytes == 0`、`slot1_rating_avf_info_mutation_bytes == 0`、`slot1_vault_mutation_bytes == 0`；同时校验 Stage-B 易失 `/tmp` 叠加隔离与 `16/16` Tier-0 `Backup.bin` `H0 == H3` 不变性。

---

## 3. 严格 6 文件交付清单（File Ownership Inventory）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py) | Pillar 55A/55B 状态机与评估器（`3,911` 行）、18 项 `O_RDONLY` 供体有界核验（`< 0.2s`）+ 洁净室合成回退、`6/6 + 6/6` 场景套件及并发 `55/55` 主控 `evaluate_realhw_55pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 无重叠导出 264 项 Pillar 55 与 `evaluate_realhw_55pillar_recovery_master` / `P308_*` / `PHASE308_*` / `MASTER_55_*` 符号（供 Milestone 295 自动发现最高支柱 `55`） |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar55-lens-comp-af-illuminator-folder-rating-vault` 与 `verify-55pillar-recovery` CLI 子命令（`--json`、`--out`、`--force-clean-room`/`--clean-room`） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 308 `55/55` 恢复支柱里程碑与运行命令文档 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py) | **85 项**双模单元测试（`1,893` 行，覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`sys.executable`、Milestone 295 负向布尔审计与 CLI） |
| 6 | NEW | [`reports/2026-11-17-phase308-milestone-realhw-55pillar-lens-comp-af-illuminator-folder-rating-vault-recovery/README.md`](README.md) | 本 Phase 308 结论先行中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 55 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m unittest -v outputs/fx3-recovery-adapter/tests/test_realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier.py` | **`85/85 OK`**（`9.088s`） |
| Pillar 55 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m unittest ...` | **`85/85 OK`**（`9.617s`） |
| Pillar 55 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m unittest ...` | **`85/85 OK`**（`9.016s`） |
| Pillar 55 单测（`/usr/bin/python3 -B` + `unicorn 2.1.4`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest ...` | **`85/85 OK`**（`10.321s`，`unicorn: 2.1.4` `55/55`） |
| `verify-pillar55-...` CLI（本地供体 / 强制洁净室） | `verify-pillar55-lens-comp-af-illuminator-folder-rating-vault --json` & `--force-clean-room --json` | **`55A=6/6, 55B=6/6, donors=18`**（`0.0040s` / `0.0004s`，`leaked=0`） |
| `verify-55pillar-recovery` CLI（本地供体 / 强制洁净室） | `verify-55pillar-recovery --json` & `--force-clean-room --json` | **`55/55 PASS`**（`1.097s` / `0.7377s` `< 1.5s`，`leaked=0`） |
| `make verify-milestone-295`（双模式） | `make verify-milestone-295` | **`status=OK pillars=6/6 recovery=55/55`**（`LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` 双轨通过，`leaked=0`，`otp=0`，`rpmb=0`） |
| 清洁审计与缓存卫生 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | **`ALL GREEN in 0.05s` / `0.04s`** |
| `fx3-recovery-adapter` 全套 `unittest discover`（`/usr/bin/python3 -B` + `unicorn 2.1.4`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,127 tests OK`（`skipped=1`，`338.518s`）** *（含全部 Pillar 1..55 与 4 项 Unicorn AArch64 测试；`python3` 3.14 无 `unicorn` 环境下发现 `3,118` 项，`3,109` 项通过、仅既有 `test_p1_symbol_autolocator.py` `4` 项缺 `unicorn`、`skipped=5`，Pillar 55 `85/85` 双解释器全绿）* |
