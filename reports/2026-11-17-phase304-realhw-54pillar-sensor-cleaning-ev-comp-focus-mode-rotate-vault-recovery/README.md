# Phase 304 工程交付报告：Recovery Pillar 54（Wave-52）与 54/54 统一恢复总检（`verify-54pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`54/54` 全绿闭环，`VERIFIED_54OF54_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：围绕 Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`ilc/2210`，`PRODUCT_MODEL_ALCIN_UUD`）与无 IBIS 的 `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）**Wave-52** 实证机制，完成 **Phase 304 Recovery Pillar 54**（Sub-Pillar **54A** & **54B**）与并发式 **54/54 统一恢复总检聚合器** `evaluate_realhw_54pillar_recovery_master`（`verify-54pillar-recovery`），并经 Milestone 295 自动发现接管至 **`recovery=54/54`**。
- **关键实测结果（本地 `O_RDONLY` 供体模式 & 洁净室模式双轨全过）**：
  - `verify-54pillar-recovery`（`LOCAL_DONOR_O_RDONLY`）：`pillars=54/54`，`all_passed=True`，耗时 **`0.916s`**（`< 1.5s` 快速 CLI 预算），`raw_firmware_bytes_leaked=0`，`slot1_data_sector_writes=0`，`slot1_rotate_exif_mutation_bytes=0`，`slot1_vault_mutation_bytes=0`，`master_54pillar_sha256=67824c4e92d6948709e4de0fa6955c4a800a0cfcb7e5f07a0e1643e70446a75b`。
  - `verify-54pillar-recovery --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`pillars=54/54`，`all_passed=True`，耗时 **`0.630s`**（`< 1.5s`），`raw_firmware_bytes_leaked=0`，`master_54pillar_sha256=e81dd9aa9fc86ff1bd6b2a98164392b93ee5dab968530fb04e74ba952d558fb9`。
  - `verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault`：Pillar `54A=6/6`、`54B=6/6`；`LOCAL_DONOR_O_RDONLY` 耗时 **`0.003s`**（`suite_sha256=2f0be5f6f06c5a2ea811ec219732e01ebefde9d158e0c2940f58e259e9853c9a`），`CLEAN_ROOM_SYNTHETIC` 耗时 **`0.0003s`**（`suite_sha256=e3d0b9b4e436ae13712247cdf9f7964d4a827c5e76b1fd9355ad8a067a95854a`）。
  - **硬件安全护栏硬锁**：`overall_ready_for_hardware_attach == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`physical_device_writes == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 2. Wave-52 实证恢复契约与校验范围

### 2.1 Sub-Pillar 54A：`[Sensor Cleaning]`（`>= 51%` 电量门槛与强制开关断电 vs FX6 `e-ND + APR`）与 `[Exposure Comp.]`（`±5.0 / ±2.0 EV` & `Cine EI` 锁死）

1. **`ILME-FX3` `[Sensor Cleaning]`（`_f.uxc` `0x67d6` / 旧版 `.uxc` `0xe7d7` `Cleaning Mode` / `FUNC_set_cleaning_mode`）**：
   - **Ver. 2.00+..7.02 电量硬门槛**：强制校验 `NP-FZ100 >= 51%`（`< 51%` 触发 `BATTERY_CHECK_FOR_CLEANING_MODE_LOWER` -> `.uxc` `0xe574` `"Power insufficient."` 拒绝进入）；对比 Pre-Ver. 2.00（`1.00`/`1.01`）仅检 `>= 3` 格电量图标。
   - **IBIS 震动归位后强制断电**：完成 5 轴 IBIS 传感器超声除尘/锁止归位（`MODEL_CLEANING_MODE_COMP`）后，提示 `_g.uxc` `0x6221` 并强制物理拨动电源开关 `OFF` 方可拆下镜头（禁用压缩空气），未断电即拆镜场景 fail-closed 拦截（`P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION`）。
   - **与无 IBIS 的 `ILME-FX6 Ver. 6.01` 物理边界隔离**：`FX6` 传感器前方为电子可变 ND 光学模组（`CLEAR`、`1/4`..`1/128`，`PID_SET_VARIABLE_ND_VALUE`）并采用 `Technical > APR`（`MODEL_APR_EXECUTE_COMP`），`CrCommandId_SensorCleaning`（`320`）不受支持；在 `FX6` 路径强行声称 IBIS 超声震动或 `CR 320` 即刻被 `P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION` 拦截。
2. **`[Exposure Comp.]`（`BKID_APP_setting_exposure_compensation` / `_f.uxc` `0x76de` / `.uxc` `0xe956`）**：
   - **跨域量程与模式门控**：静态 Still 支持 **`±5.0 EV`**，Movie / `S&Q` 限制 **`±2.0 EV`**（实时测光尺标 `-3.0..+3.0 EV`）；在 `Intelligent Auto` 下禁用；在手动曝光 `M` 下 **仅当 `[ISO] = ISO AUTO` 时生效**，固定手动 ISO 必须锁定禁用。
   - **`[Cine EI]` / `[Cine EI Quick]` 100% 锁死**：在 `[Log Shooting] = Cine EI` 或 `Cine EI Quick` 时曝光模式锁定 `EXPOSURE_MODE_MOVIE_M` 且录制增益锁定 `Base ISO 800 / 12800`（由 `[Exposure Index]` `±2.0 EV` 与 `Display LUT` 接管监看），`Exposure Comp.` 必须 100% 锁闭；`Flexible ISO` 下保留 `Exposure Comp.` + `ISO AUTO`。
   - **复位层级与休眠项屏蔽**：`Camera Settings Reset` 将 `Exposure Comp.` 复位为 `0.0 EV`，而 `[Exposure step]`（`0.3EV` 默认 / `0.5EV`）与 `[Exposure Std. Adjust]` 跨 `Camera Settings Reset` 留存、仅随 `Initialize` 重置；严禁暴露无物理 EV 拨盘 `ilc/2210` 所省略的休眠 `[Reset EV Comp.]`（`0x7853`）与 Ver. 1 `[Dial Ev Comp]`（`0xe4d9`）。

### 2.2 Sub-Pillar 54B：`[Focus Mode]`（5-Still vs 2-Movie `AF-C/MF` 钳位）与回放 `[View Mode]` / `9-25` `[Image Index]` / `[Rotate]` Slot-1 Tier-0 金库防火墙

1. **`[Focus Mode]`（`BKID_APP_setting_focus_mode_menu_dial` / `_g.uxc` `0x625e`/`0x6412`）**：
   - **Still 5 模式 vs Movie/`S&Q` 2 模式硬钳位**：Still 暴露 `AF-S`、`AF-A`（出厂默认，随 `Camera Settings Reset` 复位）、`AF-C`、`DMF`、`MF`；而 Movie 与 `S&Q` 严格钳位为 **`AF-C`**（`appFw.so` 内部编码 `MOVIE_AUTO` `0x66ea`）与 **`MF`**，凡在 Movie/`S&Q` 请求 `AF-S`/`AF-A`/`DMF` 或任何模式暴露休眠 `PF`/`SEMI_MANUAL`，fail-closed 拦截（`EOPNOTSUPP=95` / `EINVAL=22`，`P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT`）。
   - **关联 AF 子菜单门控**：`[Priority Set in AF-S/AF-C]`（`AF` / `Release` / `Balanced Emphasis` 默认）跨 `Camera Settings Reset` 留存、仅随 `Initialize` 清除；`[AF Illuminator]`（`Auto`/`Off`，随 `Camera Settings Reset` 复位）严格仅限 Still 非 `AF-C` 启用，在 Movie/`S&Q`/`AF-C` 下强制锁死。
2. **`[Playback]` 浏览矩阵与 `[Rotate]` Slot-1 Tier-0 金库关键防火墙**：
   - **浏览设置（`Initialize` 专属重置）**：`[View Mode]`（`Date View`、`Folder View(Still)`、`Movie View`、`AVCHD View`、`XAVC S View`）、精确 `[Image Index]` **`9 Images / 25 Images`**（拒绝休眠 `12 Images` / `30 Images`）、`[Display as Group]`（`Off`/`On`）、`[Display Rotation]`（`Auto`/`Manual`/`Off`）均跨 `Camera Settings Reset` 留存。
   - **Slot-1 Tier-0 金库防火墙**：回放 `[Rotate]`（`FUNC_rotate_content`、`_f.uxc` `0x795a`、`.uxc` `0xe5ae`）会直接篡改存储卡上的文件 EXIF 方向与 `AVF_INFO` 数据库；当 `Slot 1` 持有 Tier-0 只读恢复金库（或后台传输激活时）**必须 fail-closed 拦截**（`EROFS=30` / `EBUSY=16`，强制 `slot1_data_sector_writes == 0`、`slot1_rotate_exif_mutation_bytes == 0`、`slot1_vault_mutation_bytes == 0`），同时允许向安全从卡 `Slot 2`（无后台传输冲突时）执行旋转。
   - **Stage-B 与 Tier-0 完整性**：Stage-B 叠加严格限定于易失性 `/tmp/` 或 `/run/` tmpfs（拦截 `/setting`、`p2:/setting`、`/dev/nflasha` 等逃逸），且 `Backup.bin` `H0 == H3`（`16/16` Tier-0 表校验）。

---

## 3. 严格 6 文件交付清单（File Ownership Inventory）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py) | Pillar 54A/54B 状态机与评估器、17 项 `O_RDONLY` 供体有界核验（`< 0.2s`）+ 洁净室合成回退、`6/6 + 6/6` 场景套件及 `54/54` 并发主控 `evaluate_realhw_54pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 无重叠导出 Pillar 54 与 `evaluate_realhw_54pillar_recovery_master` / `P304_*` / `PHASE304_*` / `MASTER_54_*` / `CROSS_MODEL_FLASH_AUTHORIZED` 符号（供 Milestone 295 自动发现 `54` 支柱） |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault` 与 `verify-54pillar-recovery` CLI 子命令（`--json`、`--out`、`--force-clean-room` / `--clean-room`，兼容 Python 3.14 `%%` 转义） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 304 Pillar 54 与 `54/54` 总检规范说明及运行命令 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py) | **84 项**双模单元测试（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`sys.executable`、Milestone 295 负向布尔审计与 CLI） |
| 6 | NEW | [`reports/2026-11-17-phase304-realhw-54pillar-sensor-cleaning-ev-comp-focus-mode-rotate-vault-recovery/README.md`](README.md) | 本 Phase 304 结论先行中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 54 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier.py -v` | **`84/84 OK`**（`7.935s`） |
| Pillar 54 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m unittest ...` | **`84/84 OK`**（`7.453s`） |
| Pillar 54 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter python3 -B -m unittest ...` | **`84/84 OK`**（`7.268s`） |
| Pillar 54 单测（`/usr/bin/python3` + `unicorn`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest ...` | **`84/84 OK`**（`9.070s`） |
| `54/54` CLI（本地供体 / 强制洁净室） | `verify-54pillar-recovery --json` & `--force-clean-room --json` | **`54/54 PASS`**（`0.916s` / `0.630s` `< 1.5s`，`leaked=0`） |
| `make verify-milestone-295`（双模式） | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **`status=OK pillars=6/6 recovery=54/54`**（`leaked=0`，`otp=0`，`rpmb=0`） |
| 清洁审计与缓存卫生 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | **`ALL GREEN in 0.04s`** |
| `fx3-recovery-adapter` 全套 `unittest discover`（`/usr/bin/python3` + `unicorn`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3042 tests OK` (`skipped=1`，`344.619s`)** *(含全部 Pillar 1..54 与 4 项 Unicorn AArch64 测试；`python3` 3.14 下 `3029` 项通过，Pillar 54 `84/84` 双解释器全绿)* |
