# Phase 309（Stage 63 — `63/63` VM 里程碑）：Wave-53 `[Lens Compensation]` Shading Auto/Off vs 休眠 `Auto: Low` & `SteadyShot = Active` 畸变锁、内置前部 AF 辅助照明 LED（`#8`）vs 零照明 `FX6` + 电影 AF 运动学、AF 行为 `Initialize-only` 五项持久化（正交循环聚焦点），以及 `[Create New Folder]` + 回放 `[Rating]`（1..5 星）Slot-1 Tier-0 Vault 防火墙 HIL 协同仿真报告

## 结论先行

1. **Stage 63 (`63/63`) 全闭环通过并接入全板总装门禁**：新增 [`outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py`](../../outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py)（Schema `realhw_lens_comp_af_illuminator_folder_rating_coemulator_v1`），并接线至 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为第 63 阶段（`vm_stages=63/63`），`Stage 1..62` 保持完全向后兼容（支持 `--include-stage63`、`--skip-stage63`、`--no-include-stage63`、`--skip-phase309`）。
2. **12 份真实 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 实机供体双模审计零失真**：通过受界 `os.O_RDONLY`（`<= 4096 B`）校验全部 12 份供体（FX3 `string_*_f.uxc` 4 语全集 + `string_english.uxc` + `string_english_g.uxc` + **`libInfraLensCommunicator.so`** + FX6 `string_english.uxc` / `_2.uxc` + `FX3 appFw.so`、`FX3 BK4`、`FX6 appFw.so`）字节长度、SHA-256 与符号/词条锚点，`LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 三模完全一致，`raw_firmware_bytes_leaked == 0`。
3. **88 项 Stage 63 专项单测 + 全量 `fx3-vm` 单测 + Milestone 295 双模门禁全绿**：全部 42 项硬件安全/模型真值红线硬锁定为 `False`/`0`/`True`（`persistent_emmc_writes_authorized=False`、`hardware_live_attachment_authorized=False`、`overall_ready_for_hardware_attach=False`、`slot1_data_sector_writes=0`、`slot1_avf_info_mutated=False`、`slot1_vault_folder_or_rating_mutation_bytes=0`、`physical_device_writes=0`）。

---

## 一、交付文件清单（严格限定 5 个自有文件）

| 序号 | 类型 | 路径 | 职责摘要 |
| --- | --- | --- | --- |
| 1 | NEW | [`outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py`](../../outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py) | Phase 309 Stage 63 核心模型、12 供体 `O_RDONLY` 审计、63A..63D 仿真器、42 项红线门禁与 CLI |
| 2 | EDIT | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage63_realhw_lens_comp_af_illuminator_folder_rating_hil`（总阶段 `63/63`）与 CLI 开关 |
| 3 | EDIT | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 309 Stage 63 架构契约与三模运行/单测命令 |
| 4 | NEW | [`outputs/fx3-vm/tests/test_realhw_lens_comp_af_illuminator_folder_rating_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_lens_comp_af_illuminator_folder_rating_coemulator.py) | 88 项双模单测（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 5 | NEW | [`reports/2026-11-17-phase309-vm-stage63-lens-comp-af-illuminator-folder-rating-hil/README.md`](README.md) | 本中文结论先行工程报告 |

---

## 二、Wave-53 实机四大硬件契约验证摘要

### 1. Sub-Model 63A：`[Lens Compensation]` Shading Auto/Off vs 休眠 `Auto: Low` & `SteadyShot = Active` 畸变锁

- **FX3 Ver. 7.02 契约**：`(Shooting) -> [Image Quality/Rec] -> [Lens Compensation]`（`_f.uxc 0x75c8`）对 `[Shading Comp.]` **仅暴露 `Auto`（默认）与 `Off`**，严格拒绝跨机族休眠枚举 `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW` 与 `_f.uxc 0x6c9c` `'Auto: Low'`（`ILCE-6700` / `ILCE-7RM5`，返回 `EOPNOTSUPP=95`，`dormant_shading_auto_low_exposed_events=0`）。
- **畸变强制 `Auto` 锁与无触点镜头拦截**：`[Chromatic Aberration Comp.]`（`Auto`/`Off`）与 `[Distortion Comp.]`（`Auto`/`Off`，默认 `Off`）受 `libInfraLensCommunicator.so` 镜头通讯协议管控；特定镜头档案（`SELP1650`、`FE 28-70mm`）或 Movie/S&Q `[SteadyShot] = Active` 时强制将 `[Distortion Comp.]` 锁定为 `Auto`（尝试切 `Off` 立即拒绝 `EOPNOTSUPP=95`）；无触点手动镜头（`Unchipped Manual PL`）返回 `EOPNOTSUPP=95`。
- **生命周期与 RAW 语义**：`Shading / CA / Distortion` 跨 `[Camera Settings Reset]` 保留且仅 via `[Initialize]` 复位；Movie-only `[Breathing Comp.]` 随 `[Camera Settings Reset]` 复位；`Distortion` 永不烘烤进 `.ARW` 像素，仅作为元数据标签随机内 JPEG/HEIF 生效，而 `Shading=Auto` 影响 ARW 增益修正。
- **跨机型差异**：对比 `ILME-FX6 Ver. 6.01` `Technical > Lens`（`All File` 存储作用域，`Distortion=Off` / `S&Q` / `Codec=RAW` 时强制禁用 `Breathing Compensation`）以及传感器白黑均匀度校准 `White/Black Shading`（`PID_SET_{WHITE,BLACK}_SHADING`）的本质隔离。

### 2. Sub-Model 63B：内置前部 AF 辅助照明 LED（`#8`, `0.3..3.0 m`）vs 零照明 `ILME-FX6` & 电影 AF 运动学

- **纠偏硬件事实**：`ILME-FX3` 机身正面确实内置 **AF Illuminator / Self-timer lamp / Visible light & IR sensor LED（`TP1000886886.html` Front `#8`, 有效距离 `0.3..3.0 m`）**，并与 MI 热靴外接闪光灯 AF 辅助照明协同工作（`fx3_has_builtin_af_illuminator=True`）。
- **严格触发与锁定边界**：仅在 **`Still` + `AF-S` + `[AF Illuminator]=Auto` + `Silent Mode=Off` + `Focus Magnifier=Off` + `Mount Adaptor=Off`** 条件下点亮；在 **`Movie`、`S&Q`、`AF-C`、`MF`、`Silent Mode=On`、`Focus Magnifier`、转接环挂载及 `AF-A` 运动被摄体** 场景下 100% 锁定抑制（强制点亮返回 `EOPNOTSUPP=95`，`af_illuminator_non_afs_or_silent_fire_events=0`）。
- **对比零照明 `ILME-FX6` & 电影 AF 运动学**：`ILME-FX6` **无内置 AF 辅助照明 LED**（`fx6_has_builtin_af_illuminator=False` -> 拒绝 `EOPNOTSUPP=95`）；同步建模 Movie/`S&Q` `[AF Transition Speed]`（`1..7`，默认 `5`）、`[AF Subj. Shift Sensitivity]`（`1..5`，默认 `5`）与 `[AF Assist]`（仅 Movie/`S&Q` `AF-C`，排斥 `SELP1650` / `SEL18200LE`），三者均随 `[Camera Settings Reset]` 恢复默认。

### 3. Sub-Model 63C：AF 行为 `Initialize-only` 五项持久化与正交循环聚焦点

- **五项 `Initialize-only` 设定**：
  1. `[Aperture Drive in AF]`（`Focus Priority` / `Standard` [默认] / `Silent Priority`，Still-only，附带光圈声响/实时取景景深/连拍速度下降警告并与 `Silent Mode Settings` 联动）；
  2. `[AF w/ Shutter]`（`On` [默认] / `Off`，Still-only）；
  3. `[Pre-AF]`（`On` / `Off` [默认]，Still-only 且受镜头 `VAL_lens_pre_af_support` 门控）；
  4. `[Circ. of Focus Point]`（`Circulate` / `Does Not Circulate` [默认]，Still/Movie/`S&Q` 通用，仅对 `Zone`/`Spot`/`Expand Spot` 等定点区域生效，**严格只允许水平/垂直正交边界环绕，禁止对角线斜向环绕 -> `EOPNOTSUPP=95`**）；
  5. `[Focus Area Color]`（`White` [默认] / `Red`，Still/Movie/`S&Q` 通用，拒绝旧版 `Focus Frame Color` 伪造标签 -> `EOPNOTSUPP=95`）。
- **复位边界与跨机型对比**：上述 5 项全部跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 留存，**仅在 `[Initialize]` 复位**（`initialize_only_af_reset_wipe_events=0`）；对比 `ILME-FX6` 缺失此 5 项，改由电影 `Iris`（`Auto Iris` / `Manual` / `Push Auto Iris` / `Override -1.0..+1.0` 步进 `0.25`）与 `Focus Area Marker` 接管。

### 4. Sub-Model 63D：`[Create New Folder]` 与回放 `[Rating]`（1..5 星）Slot-1 Tier-0 Vault 防火墙

- **目录与评级契约**：完整建模 `[File/Folder Settings]`（`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` 禁用 `[Select REC Folder]`；`Series`/`Reset`；3 字符 `DSC` 前缀拒绝前导 `_`）、`[Create New Folder]` / `[Forced File Number Reset]`（`max + 1`、`999` 文件夹上限、双卡同录检测）与回放 `[Rating]`（1..5 星 + `[Rating Set(Custom Key)]` 复选框子集约束 + 拍摄画面 `[Add Rating]` 拒绝重复评级 `_g.uxc 0x627d` 及后台 FTP 传输拦截 `EBUSY=16`）。
- **Slot-1 Tier-0 Vault 硬防火墙**：无论直指 `Slot 1` 还是启用 `dual_slot_simultaneous=True` 联动触及 `Slot 1`，一旦 `Slot 1` 承载 Tier-0 Recovery Vault（`slot1_is_tier0_vault=True`），任何 `[Create New Folder]`、`[Forced File Number Reset]`、`[Select REC Folder]` 或 `[Rating]` / `[Add Rating]`（会改写卡上 EXIF 与 `AVF_INFO` 数据库）**100% fail-closed 拦截并返回 `EROFS=30`**（`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == False`、`slot1_vault_folder_or_rating_mutation_bytes == 0`）；仅允许在虚拟 `Slot 2` 执行零物理写入仿真；对比 `FX6` 采用 `XDROOT/Clip` 与 `Clip Flag`（`OK/NG/KEEP`）。

---

## 三、跨平台 CI 合规与安全红线实测项

- **Python 3.14 / CI 兼容**：全模块及单测零硬编码旧系统解释器路径（统一 `sys.executable`）、`argparse` 内全部 `%` 已转义为 `%%`、计时断言包含 `GITHUB_ACTIONS == 'true'` 的 `15.0s` 裕度、总阶段计数校验使用 `assertGreaterEqual(..., 63)`。
- **验证覆盖与实测指标**：
  - Stage 63 独立 CLI 与 **88** 项专项单测在 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`（digest `d05c78a3912f`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（digest `d05c78a3912f`）三模均 **88/88** 全绿通过（实测耗时分别 `3.366s`、`3.328s`、`1.787s`）。
  - `outputs/fx3-vm/tests` 全量单测发现双模全绿：`LOCAL_DONOR_O_RDONLY` 模式 `Ran 3183 tests in 185.782s (OK)`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 3183 tests in 171.033s (OK, skipped=5)`。
  - `make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` 双模全绿通过：`vm_stages=63/63`、`pillars=6/6`、`gate124=131/134`、`recovery=54/54`、`cnflasha_ro=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`auditors=45/45`、`qemu=34/34(102/102)`、`pngs=68/68(max=27467B)`、`leaked=0`、`live_attach_auth=False`、`emmc_writes_auth=False`、`usb_tx=0`（`LOCAL_DONOR_O_RDONLY` `milestone295_sha256=036282c0c7d5d918...`；`CLEAN_ROOM_SYNTHETIC` `milestone295_sha256=aceb126b5b380a81...`）。
  - `make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）：`CLEAN (0.53s)`（`ALL GREEN in 0.53s`），零 `__pycache__`/`.pyc`、零未授权写操作。
