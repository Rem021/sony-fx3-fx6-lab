# Phase 312（Stage 64 — `64/64` Power-of-Two $2^6$ VM 阶段里程碑）：Wave-54 `[Switch V/H AF Area]` & 14 项 `[Focus Area Limit]`、5 模式 `[Exposure Std. Adjust]` 1/6 EV + Still `[Bracket Settings]`、`[Time Code Format]` DF/NDF 23.98p-24p-PAL 锁 & `[User Bit Time Rec]`，以及 `[Select Playback Media]=Slot 2` 反向 `[Copy]` (`Slot 2 -> Slot 1`) Tier-0 Vault 防火墙 HIL 协同仿真报告

## 结论先行

1. **Stage 64 (`64/64` Power-of-Two $2^6$ 里程碑) 全闭环通过并接入全板总装门禁**：新增 [`outputs/fx3-vm/realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py`](../../outputs/fx3-vm/realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py)（Schema `realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator_v1`），并接线至 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为第 64 阶段（`vm_stages=64/64`，Power-of-Two $2^6$ 里程碑），`Stage 1..63` 保持完全向后兼容（支持 `--include-stage64`、`--skip-stage64`、`--no-include-stage64`、`--skip-phase312`）。
2. **17 份真实 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 实机供体双模审计零失真**：通过受界 `os.O_RDONLY`（`<= 4096 B`）校验全部 17 份供体（FX3 `string_*_f.uxc` 4 语全集 + `string_*.uxc` 4 语全集 + `string_*_g.uxc` 4 语全集 + FX6 `string_english.uxc` / `string_english_2.uxc` + `FX3 appFw.so`、`FX3 BK4`、`FX6 appFw.so`）字节长度、SHA-256 与符号/词条锚点，`LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 三模完全一致（洁净室双环境变量产生确定性一致摘要 `a73aaefb8cdb`），`raw_firmware_bytes_leaked == 0`。
3. **88 项 Stage 64 专项单测 + 全量 `fx3-vm` 单测（3,271 项）+ Milestone 295 双模门禁全绿**：全部 43 项硬件安全/模型真值红线硬锁定为 `False`/`0`/`True`（`persistent_emmc_writes_authorized=False`、`hardware_live_attachment_authorized=False`、`overall_ready_for_hardware_attach=False`、`slot1_data_sector_writes=0`、`slot1_avf_info_mutated=False`、`slot1_vault_copy_reverse_direction_mutation_bytes=0`、`reverse_copy_slot2_to_slot1_vault_bypass_events=0`、`physical_device_writes=0`、`fx3_has_bnc_tc_in_out_switch=False`、`fx6_has_bnc_tc_in_out_switch=True`）。

---

## 一、交付文件清单（严格限定 5 个自有文件）

| 序号 | 类型 | 路径 | 职责摘要 |
| --- | --- | --- | --- |
| 1 | NEW | [`outputs/fx3-vm/realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py`](../../outputs/fx3-vm/realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py) | Phase 312 Stage 64 核心模型、17 供体 `O_RDONLY` 审计、64A..64D 仿真器、43 项红线门禁与 CLI |
| 2 | EDIT | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil`（总阶段 `64/64` Power-of-Two）与 CLI 开关 |
| 3 | EDIT | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 312 Stage 64 架构契约与三模运行/单测命令 |
| 4 | NEW | [`outputs/fx3-vm/tests/test_realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py) | 88 项双模单测（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 5 | NEW | [`reports/2026-11-17-phase312-milestone-vm-stage64-switch-vh-af-stdadj-tcub-copy-slot-hil/README.md`](README.md) | 本中文结论先行工程报告 |

---

## 二、Wave-54 实机四大硬件契约验证摘要

### 1. Sub-Model 64A：`[Switch V/H AF Area]` & 14 项复选框 `[Focus Area Limit]`

- **`[Switch V/H AF Area]`（`Off` / `AF Point Only` / `AF Point + AF Area`）**：仅在 **`Still` + `AF-C`** 下跨 **`0° / 90° / 270°`** 三向滚动姿态激活（`vh_af_area_orientation_information`）；遇陡直俯仰姿态 `INVALID` 时优雅降级忽略（强行切换返回 `EOPNOTSUPP=95`）；在 `Movie` / `S&Q`、`AF-S` / `AF-A` / `DMF` / `MF`、`iAuto`、`Digital Zoom`、激活追踪、连拍进行中、自拍倒计时及 `Focus Magnifier` 下严格锁定拦截（`switch_vh_af_non_afc_or_invalid_pitch_bypass_events=0`）；修改模式即时清空三向已记忆对焦点/区域坐标。
- **`[Focus Area Limit]` 14 项精确复选框与 `>= 2` 底线**：精确暴露 FX3 Ver. 7.02 全部 **14 项活跃复选框**（`Wide`, `Zone`, `Center Fix`, `Spot: S/M/L`, `Expand Spot` 及 7 项 `Tracking:*`）；强制要求 **至少 2 项勾选**（`.uxc 0xea28`，尝试降至 `< 2` 返回 `EINVAL=22` 确保对焦循环不致空转）；严格拒绝跨机族 Alpha 休眠项 `Spot: XL`、`Spot: XS`、`Custom 1..3`（返回 `EOPNOTSUPP=95`，`focus_area_limit_lt2_or_dormant_alpha_exposed_events=0`）；在 `Movie`/`S&Q` 下自动过滤 7 项 `Tracking:*`；取消勾选自动清除对应已注册 V/H 与 `AF Area Reg.` 坐标。
- **生命周期与跨机型对比**：`[Focus Area Color]`（`White` / `Red`）跨 `[Camera Settings Reset]` 留存并仅在 `[Initialize]` 复位，而 `[Switch V/H AF Area]` 与 `[Focus Area Limit]` 随 `[Camera Settings Reset]` 复位；无上述菜单的 `ILME-FX6 Ver. 6.01` 拒绝 FX3 专属请求（`EOPNOTSUPP=95`）并对比 `Orange` 对焦框语义。

### 2. Sub-Model 64B：5 模式 `[Exposure Std. Adjust]`（1/6 EV）& Still-Only `[Bracket Settings]`

- **全部 5 种测光模式 `-1.0..+1.0 EV` @ `1/6 EV`**：FX3 Ver. 7.02 `[Exposure Std. Adjust]`（`_f.uxc 0x6114`）暴露全部 **5 种测光模式**：`Multi`、`Center`、`Spot`、`Entire Screen Avg.`、`Highlight`，支持精确 **`1/6 EV` 步进**（`-6/6 .. +6/6` 共 13 档；拒绝非 `1/6` 步进如 `0.25 EV` 或越界偏移 -> `EINVAL=22`）。
- **独立偏置与生命周期隔离**：触发警示对话框 `.uxc 0xe567`，通过 `PID_SET_STANDARD_EXPOSURE_SETTING` 下发，独立记入 EXIF 而不修改 `[Exposure Comp.]` 标尺，永久偏移 `M.M.` 与 AE 基准（在 `Spot` 模式下同步偏移 Spot AEL）；若在连续包围曝光中途更改即清零包围计数；**全部 5 项偏移均跨 `[Camera Settings Reset]` 保留，且仅通过 `[Initialize]` 复位**（`exposure_std_adj_reset_wipe_or_missing_5th_mode_events=0`）。
- **Still-Only `[Bracket Settings]`**：覆盖 `[Selftimer during Bracket]`（`Off` / `2 Sec` / `5 Sec` / `10 Sec`）与 `[Bracket order]`（`0->- ->+` vs `- ->0->+` 及 `Focus Bracket` `0->+`），随 `[Camera Settings Reset]` 复位；在 `Movie` / `S&Q` 与无静态拍摄模式的 `ILME-FX6` 下 100% 拒绝（`EOPNOTSUPP=95`，`bracket_movie_sq_or_fx6_bypass_events=0`）。

### 3. Sub-Model 64C：`[Time Code Format]`（DF/NDF）23.98p-24p-PAL 锁 & `[User Bit Time Rec]`

- **制式与帧率硬锁**：
  - `NTSC`（`59.94p` / `29.97p` / `119.88p`）：同时暴露 `DF` / `NDF`；
  - `23.98p` 与真 `24.00p`：**强制硬锁 `NDF`**（请求 `DF` 返回 `EOPNOTSUPP=95`）；
  - `PAL`（`50p` / `25p` / `100p`）：**隐藏菜单并硬锁 `NDF`**（`tc_format_menu_hidden=True`，请求 `DF` 返回 `EOPNOTSUPP=95`，`tc_format_2398p_24p_or_pal_df_violation_events=0`）；跨制式帧率错配同样拒绝。
- **`[User Bit Time Rec]` 与 `Initialize-only` 持久化**：`[User Bit Time Rec]`（`On` / `Off`）开启时以实时 `HH:MM:SS` 覆盖 `[User Bit Preset]`（`00 00 00 00`），`[TC/UB Disp. Setting]`（`Counter` / `TC` / `U-Bit`）在静态照片回放时拦截切换（`.uxc 0xe728`），且全部 6 项 `[TC/UB]` 与显示设置跨 `[Camera Settings Reset]` 保留（仅 `[Initialize]` 复位）。
- **FX3 vs FX6 BNC 硬件差异**：`ILME-FX3` 无物理 BNC `TC IN/OUT` 切换开关（`fx3_has_bnc_tc_in_out_switch=False` -> `EOPNOTSUPP=95`），而 `ILME-FX6` 具备独立物理 BNC `TC IN/OUT` 端子及 `EXT-LK` 状态（`fx6_has_bnc_tc_in_out_switch=True`）并遵守同源 `23.98p`/`24p`/PAL `NDF` 锁定。

### 4. Sub-Model 64D & Redlines：关键反向 Vault 防火墙 — Playback `[Copy]` (`Slot 2 -> Slot 1`) & 安全只读 `[Slide Show]`

- **反向写入方向实机铁律**：`[Select Playback Media]`（`Slot 1` / `Slot 2`）不仅切换回放源卡槽，更**直接反转 Playback `[Copy]` 写入方向**——当 `[Select Playback Media] == Slot 2` 时，执行 Playback `[Copy]` 将 **从 `Slot 2` 反向写入 `Slot 1`**（改写 `DCIM/`、`PRIVATE/M4ROOT/` 与 `AVF_INFO` 数据库）！
- **Slot-1 Tier-0 Vault 100% Fail-Closed 防火墙**：只要 `Slot 1` 挂载 Tier-0 Recovery Vault（`slot1_is_tier0_vault=True`），在 `[Select Playback Media] == Slot 2` 下请求 Playback `[Copy]` 必须 **100% fail-closed 拦截**（返回 `EROFS=30`；写保护卡同步 `EROFS=30`，低电量/录制中/后台传输返回 `EBUSY=16`），实测锁定：
  - `slot1_data_sector_writes == 0`
  - `slot1_avf_info_mutated == False`
  - `slot1_vault_copy_reverse_direction_mutation_bytes == 0`
  - `reverse_copy_slot2_to_slot1_vault_bypass_events == 0`
- **正向虚拟复制 & 只读 `[Slide Show]`**：`Slot 1 -> Slot 2` 虚拟复制维持 `Slot 1` 严格只读（在虚拟目标卡展开组扁平并清除 Protect，慢速 `SDHC Class 4` 目标卡对 Movie 复制返回 `.uxc 0xe80e` / `EOPNOTSUPP=95`）；只读 `[Slide Show]`（`Repeat` `On`/`Off`、`Interval` `1s/3s/5s/10s/30s`，限 `Date View` / `Folder View(Still)`，通过 `DURING_PLAYBACK_SLIDESHOW` 暂挂 `[Power Save Start Time]`）在 `Slot 1` Vault 与 `Slot 2` 均安全放行；对比无消费级 `Copy`/`Slide Show` 的 `ILME-FX6`（`EOPNOTSUPP=95`）。

---

## 三、跨平台 CI 合规与安全红线实测项

- **Python 3.14 / CI 兼容**：全模块与单测零硬编码 `/usr/bin/python3`（统一 `sys.executable`）、`argparse` 帮助文本全部 `%` 已转义为 `%%`、计时断言含 `GITHUB_ACTIONS == 'true'` 下的 `15.0s` 裕度、总阶段计数校验使用 `assertGreaterEqual(..., 64)`，且修复了 `CLEAN_ROOM_SYNTHETIC` 下 `inspection_elapsed_ms` 毫秒抖动导致的 `audit_digest_sha256` 差异（洁净室统一锁定 `0.0`，全量 9 项确定性摘要测试全过）。
- **验证覆盖与实测指标**：
  - **Stage 64 独立 CLI**：`LOCAL_DONOR_O_RDONLY` 与两种洁净室环境变量（`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`）均输出 `[PASS]`，且双洁净室模式摘要完全一致：`digest=a73aaefb8cdb`；全板 64 阶段套件 `--include-stage64 --summary` 输出 `m64=64/64,p2=1`、`digest=b1aecece2952`。
  - **Stage 64 专项 88 项单测（三模全绿）**：
    - `LOCAL_DONOR_O_RDONLY`：`Ran 88 tests in 4.214s (OK)`
    - `FX3_CLEAN_ROOM_TEST=1`：`Ran 88 tests in 4.249s (OK)`
    - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 88 tests in 2.369s (OK)`
  - **`outputs/fx3-vm/tests` 全量单测发现（双模全绿）**：
    - `LOCAL_DONOR_O_RDONLY`：`Ran 3271 tests in 194.062s (OK)`
    - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 3271 tests in 175.075s (OK, skipped=5)`
  - **`make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295`（双模全绿）**：
    `vm_stages=64/64`、`pillars=6/6`、`gate124=131/134`、`recovery=54/54`、`cnflasha_ro=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`auditors=45/45`、`qemu=35/35(105/105)`、`pngs=70/70(max=27467B)`、`leaked=0`、`ready_attach=False`、`live_attach_auth=False`、`emmc_writes_auth=False`、`cross_model_flash_auth=False`、`spi_nor_auth=False`、`el3_tx_auth=False`、`usb_tx=0`（`LOCAL_DONOR_O_RDONLY` `milestone295_sha256=cd76f86c2745ef38...`；`FX3_FX6_FORCE_CLEAN_ROOM=1` `milestone295_sha256=85697baef9c2720c...`）。
  - **`scripts/run_all_lab_tests.py --clean-only` 与 `make clean-audit`**：`CLEAN (1.52s)` / `CLEAN (0.04s)`（`ALL GREEN`），零 `__pycache__`/`.pyc`、零未授权写操作。
