# Phase 274 — VM Stage 54 (`54/54`) 真实硬件 `ILME-FX3` Wave-44 `[File Settings]` vs `[File/Folder Settings]`、`[Gamma Display Assist]` vs `[Display LUT]`、以及 `[Auto Review]` & `[TC/UB]` HIL 协同仿真工程报告

- **日期**: `2026-11-17`
- **任务 / 分支**: `H310` / `codex/h310-phase274-vm-stage54-file-settings-gamma-assist-tcub-hil`
- **目标 Schema 与 Stage**: `realhw_file_settings_gamma_assist_tcub_coemulator_v1`（`version = 274.0.0`，`phase_number = 274`，`stage = stage54_realhw_file_settings_gamma_assist_tcub_hil`，将 `outputs/fx3-vm/` 全板协同仿真从 `53/53` 推进至 **`54/54`**）
- **Wave-44 权威规格参考**: [`reports/2026-11-15-global-sony-wave44-file-settings-camid-reel-37char-gamma-disp-assist-log-lockout-auto-review-tcub-intel/README.md`](../2026-11-15-global-sony-wave44-file-settings-camid-reel-37char-gamma-disp-assist-log-lockout-auto-review-tcub-intel/README.md)

---

## 1. 核心结论（结论先行）

1. **完成 Phase 274 Stage 54（`54/54`）Wave-44 HIL 协同仿真器交付**：新增 [`outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py`](../../outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py)，并在 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 中接入 `stage54_realhw_file_settings_gamma_assist_tcub_hil`（支持 `--include-stage54` / `--skip-stage54` / `--no-include-stage54` / `--skip-phase274` 与 `stage54_ok`），将全板 `FX3-VM` 阶段计数从 `53/53` 推进至 **`54/54`（`vm_stages=54/54`）**。
2. **双模 18 供体 `os.O_RDONLY` 校验与 `CLEAN_ROOM_SYNTHETIC` 对等（实测事实）**：严格以 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（`10` 份全量 SHA-256 + `8` 份 `<= 4096 B` 有界窗口 + 头部 4 KiB SHA-256，`raw_firmware_bytes_leaked == 0`），并在 `FX3_CLEAN_ROOM_TEST=1` 或 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下切换确定性洁净室基线（全套三大核心子模型输出完全一致）：
   - `LOCAL_DONOR_O_RDONLY` 摘要：`c348f9c71be4`（`fx3_vm_coemulation_suite` 54 阶段摘要 `4a96f6c18218`；`verify-milestone-264` SHA-256 `36b9a33b6e57f009...`；`verify-milestone-254` SHA-256 `0ee783804c128a69...`）
   - `CLEAN_ROOM_SYNTHETIC` 摘要：`e24b4e1855c8`（`fx3_vm_coemulation_suite` 54 阶段摘要 `754cdd3f91fe`；`verify-milestone-264` SHA-256 `8597efe2511cd6e1...`；`verify-milestone-254` SHA-256 `7b7afede2a1d5eb4...`）
3. **安全与 BYOF 硬件红线全部零容忍锁死（实测事实）**：`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`overall_ready_for_hardware_attach = False`、`isp_write_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`cnflasha_userspace_write_blocked = True`、`cnflasha_mutation_bytes = 0`、`physical_device_writes = 0`、`emmc_corruptions = 0`、`nop_count = 0`、`guest_code_modification_bytes = 0`、`slot1_vault_folder_mutation_events = 0`、`title_name_37char_overflow_events = 0`、`still_prefix_leading_underscore_bypass_events = 0`、`gamma_assist_log_lockout_bypass_events = 0`、`hdmi_gamma_assist_baked_frames = 0`、`tcub_camera_settings_reset_wipe_events = 0`、`tc_24p_or_pal_df_violation_events = 0`、`raw_firmware_bytes_leaked = 0`，且仓库零 `.pyc` / `__pycache__` 残留。
4. **前向兼容阶段数断言修复**：经 Coordinator 授权将 Stage 53 测试文件 [`test_realhw_release_wo_card_audio_meter_copyright_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py) 第 992 行由 `assertEqual(len(stage_keys), 53)` 改为 `assertGreaterEqual(len(stage_keys), 53)`，同时在 Stage 54 测试中使用 `assertGreaterEqual(len(stage_keys), 54)`，保障后续阶段持续接入前向兼容。

---

## 2. 本次变更文件清单（严格限定 6 个授权文件）

| # | 文件 | 说明 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py`](../../outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py) | **NEW** — Phase 274 Stage 54 (`54/54`) Wave-44 HIL 协同仿真器 |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 注册 `stage54_realhw_file_settings_gamma_assist_tcub_hil`、`--include-stage54` / `--skip-stage54` / `--no-include-stage54` / `--skip-phase274`、`stage54_ok` 与 `--summary` 摘要行（`54/54`） |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 274 Stage 54 (`54/54`) 架构、子模型契约与双模 CLI 命令说明 |
| 4 | [`outputs/fx3-vm/tests/test_realhw_file_settings_gamma_assist_tcub_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_file_settings_gamma_assist_tcub_coemulator.py) | **NEW** — `70` 项三模式单元测试（使用 `sys.executable`、CI 耗时裕量与 `assertGreaterEqual(..., 54)`） |
| 5 | [`outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py#L992) | 按 Coordinator 授权将第 992 行更新为 `assertGreaterEqual(len(stage_keys), 53)` |
| 6 | [`reports/2026-11-17-phase274-vm-stage54-file-settings-gamma-assist-tcub-hil/README.md`](README.md) | **NEW** — 本阶段中文结论先行工程交付报告 |

---

## 3. 核心架构与 Wave-44 硬件契约建模

### 3.1 `O_RDONLY` 18 供体核验（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`）
- 只读核验 `libInfraMediaCommon.so`（`402,624 B`）、`libInfraMediaMount.so`（`65,392 B`）、`libInfraMediaDetect.so`（`98,224 B`）、`libInfraMetaSupplier.so`（`23,048 B`）、`libInfraIPTC.so`（`68,712 B`）、`libSaveLoadSettings.so`（`18,760 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`）、FX3 `string_english_f.uxc`（`373,820 B`）、FX6 `string_english.uxc`（`118,208 B`），以及 `appFw.so`、`cpapp-b.bin`、`libmpr.so`、`BK4` 各 `<= 4096 B` 有界窗口偏移令牌与 4 KiB 头部 SHA-256。
- 通过进程级缓存实现冷/热路径 `< 0.1s` 内完成校验，缺失供体或开启 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动安全回退至 `CLEAN_ROOM_SYNTHETIC`。

### 3.2 Sub-Model 54A — 视频 `[File Settings]` vs 照片 `[File/Folder Settings]` 与 `Slot-1` 保险箱防火墙
- **Movie `[File Settings]`**（`MENU -> Shooting -> [File] -> [File Settings]`）：覆盖 `[File Number]`（`Series` 默认 / `Reset` + `Series Counter Reset`）、`5` 种 `[File Name Format]`（`Standard` `C0001.MP4`、`Cam ID + Reel#` 含 `Camera ID` `A..Z` / `Reel Number` `001..999` / `Camera Position` `C`/`L`/`R`、`Title`、`Date + Title`、`Title + Date`）、`[Title Name Settings]` `1..37` 字符（`"C"` 默认，`>= 38` 字符与非法字符返回 `EINVAL = 22`），并强制锁定不可变 `PRIVATE/M4ROOT/CLIP` 路径（篡改返回 `EOPNOTSUPP = 95`）。
- **Still `[File/Folder Settings]`**（`MENU -> Shooting -> [File] -> [File/Folder Settings]`）：覆盖 `[File Number]`（`Series` 默认 / `Reset` + `Forced File Number Reset`）、`[Set File Name]` 精确 `3` 字符（`A-Z`/`0-9`/`_`，`"DSC"` 默认，首字符 `_` 以 `EINVAL = 22` 硬拒绝）、`[Folder Name]`（`Standard Form` `100MSDCF` vs `Date Form` `100YMMDD`）。
- **重置持久化 & `Slot-1` 防火墙**：两套菜单全部项跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存，仅 `[Initialize]` 恢复默认；当 `Slot 1` 持有 `CAMSET`/`BODYDATA.DAT` 只读恢复保险箱时，针对 `Slot 1` 的 `[Forced File Number Reset]` 与 `[Create New Folder]` 均以 `EROFS = 30` 硬阻断（`slot1_vault_folder_mutation_events == 0`），而 `Slot 2` 零写入仿真正常通过。

### 3.3 Sub-Model 54B — `[Gamma Display Assist]`（`[Log Shooting]` 互锁 & 机内 LCD 专用）vs `[Display LUT]` / `[Select LUT]`
- 建模 `MENU -> Setup -> [Display Option] -> [Gamma Display Assist]`（`Off` 默认 / `On`）与 `[Gamma Disp. Assist Typ.]`（`Auto` 默认 / `S-Log3->709(800%)` / `HLG(BT.2020)` / `HLG(709)`）：一旦 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）!= `Off`，立即硬锁 `[Gamma Display Assist] = Off`（越权绕过返回 `EOPNOTSUPP = 95`）。
- 严格限定 `[Gamma Display Assist]` 仅作用于机内 `LCD_LIVE_VIEW` 与 `INTERNAL_PLAYBACK`，绝不污染外接纯净 HDMI 输出（`external_hdmi_gamma_assist_applied == False`、`hdmi_gamma_assist_baked_frames == 0`，强行烘焙返回 `EOPNOTSUPP = 95`）。
- 当 `[Log Shooting] != Off` 时，监看色彩由 `[Display LUT]`（`On` 默认 / `Off`）与 `[Select LUT]`（`3` 个内置预设 `S-Log3` / `s709` / `709(800%)` + `User1..User16` 共 `19` 项）接管，且 `[Setup]` 下三项配置跨 `[Camera Settings Reset]` 保留，仅 `[Initialize]` 复原。

### 3.4 Sub-Model 54C & 红线 — `[Auto Review]`（`Off` 电影默认）与 `[TC/UB]`（`6` 项防重置参数）
- 建模 `[Auto Review]`（`ILME-FX3` 出厂默认 `Off` / `2 Sec` / `5 Sec` / `10 Sec`，仅静止照片生效、视频/S&Q 保持 `0s`），跨 `[Camera Settings Reset]` 保留。
- 精确锁定 `[TC/UB]` 全部 **6** 项（`Time Code Preset` `00:00:00.00`、`User Bit Preset` `00 00 00 00`、`Time Code Format` `DF` 默认 vs `24.00p`/PAL `25p`/`50p` 强制 `NDF`、`Time Code Run` `Rec Run`/`Free Run`、`Time Code Make` `Preset`/`Regenerate`、`User Bit Time Rec` `Off`/`On`）与 `[TC/UB Disp. Setting]`（`TC` 默认 / `U-Bit`）：全部 `6` 项均免疫 `[Camera Settings Reset]`（即便位于 `Shooting` 菜单下，强制抹除返回 `EOPNOTSUPP = 95`），仅通过 `[Initialize]` 恢复默认；另覆盖全套 `16` 项硬件安全红线探针。

---

## 4. 实测验证矩阵与工程推断边界

- **实测事实（Measured Facts）**：以下全部验证命令均在分支 `codex/h310-phase274-vm-stage54-file-settings-gamma-assist-tcub-hil` 下通过 `PYTHONDONTWRITEBYTECODE=1` 与 `/usr/bin/python3 -B` 执行，全部退出码为 `0`：

| 验证门禁 | 运行模式 | 实测结果 |
|---|---|---|
| `test_realhw_file_settings_gamma_assist_tcub_coemulator.py` | `LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`70 / 70` PASS**（`2.524s` 本地供体 / `0.647s` `FX3_CLEAN_ROOM_TEST=1` / `0.670s` `FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 全量 `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2465 / 2465` PASS**（`173.844s`，`0` 失败） |
| 全量 `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2465` 运行（`2462` PASS，`3` 项供体专属跳过）**（`160.594s`，`0` 失败） |
| `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=54/54 leaked=0`**（双模通过） |
| `make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=54/54 leaked=0`**（双模通过） |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Hygiene & BYOF Audit | **`ALL GREEN`**（`0.77s`，`0` `.pyc` 文件，工作区干净） |

- **工程推断（Engineering Inference）**：在离线 HIL 协同仿真中显式隔离 Movie `[File Settings]` 与 Still `[File/Folder Settings]` 命名规则、对 `Slot-1` 只读恢复保险箱执行 `EROFS` 目录级防护、强制锁定 `[Log Shooting]` 期间 `[Gamma Display Assist]` 禁用且确保纯净外录 HDMI 零烘焙、并保护 `[TC/UB]` 6 项核心同步参数免受 `[Camera Settings Reset]` 误擦除，可有效避免实拍片场错码、LUT 叠加错乱与保险箱误写；所有真实物理写盘及带机连接仍严格锁定禁用（`overall_ready_for_hardware_attach == False`）。
