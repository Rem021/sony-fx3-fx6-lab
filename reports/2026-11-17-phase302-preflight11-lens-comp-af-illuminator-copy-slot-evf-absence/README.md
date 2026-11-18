# Phase 302 第 11 级物理台架准备度预检器工程报告（`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence` / Waves 53–55）

## 1. 核心结论（Conclusion-First）

1. **实测事实：Waves 53–55 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`，Model `0x91030080`）物理台架检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 新增第 11 级宿主侧只读物理台架与实拍前准备度预检器 [`realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py)（Schema `realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier_v1`，版本 `302.0.0`，CLI 子命令 `preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence`），将 11 级操作员台架预检链路推进至 `preflight-card-insert`（Ph186）→ `preflight-bench-cable-fan-slot1`（Ph204）→ `preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）→ `preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）→ `preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）→ `preflight-diffset-customkey-autoslow-and-apsc`（Ph261）→ `preflight-file-settings-gamma-assist-focus-mag-and-videolight`（Ph275）→ `preflight-usb-mode-hdmi-info-protect-and-network-reset`（Ph279）→ `preflight-pp-scinetone-wb-metering-and-shutter-type`（Ph284）→ `preflight-focus-area-zoom-dci4k-and-sensor-cleaning`（Ph291）→ **`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence`（Ph302）**。全部公共符号采用无阴影 `P302_*` / `PHASE302_*` / `PHASE_302_*` 前缀并在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) 完整导出。
2. **实测事实：两大关键台架防火墙与三项硬件形态纠偏均已 fail-closed 落地**：
   - **关键台架防火墙 1 — Playback `[Copy]` 反向写槽陷阱（Wave 54）**：`FUNC_copy_content`（`_f.uxc` `0x79fc`）的复制方向由 `[Select Playback Media]` 反向决定；当 `[Select Playback Media] == Slot 2` 时，`[Copy]` 会将整批文件与 `AVF_INFO` 写入 **`Slot 1`（`Slot 2 -> Slot 1`）**。[`evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py#L1197) 在 `Slot 1` 挂载 Tier-0 恢复保险库时对其实施 fail-closed 阻断（`EROFS=30` / `EBUSY=16`，`slot1_data_sector_writes == 0`）。
   - **关键台架防火墙 2 — Zero-EVF 黑屏锁死陷阱（Wave 55）**：`ILME-FX3` **零内置 EVF、零眼部传感器、零 `Select Finder/Monitor` 按键、零 `Graphic Display`**（`builtin_evf_present = False`）；[`evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py#L1449) 仅放行 4 档监视器拍摄 `DISP` 与 3 档回放 `DISP`，对任何休眠 EVF/Finder 键位（`BKID_APP_setting_finder_monitor`、`FINDER_MONITOR_SWITCH`、`DISP_MODE_SHOOT_FINDER`、`GRAPHIC_DISPLAY`、`FOR_VIEWFINDER`、`MONITOR_OFF_EVF_MODE`）实施 fail-closed 阻断以防黑屏锁死。
   - **硬件实证纠偏（Waves 53–55）**：`ILME-FX3` 正面具备物理内置 AF 辅助灯/自拍指示灯 LED（*Front side* `#8`，`0.3..3.0 m`，仅 Still `AF-S`），而 `ILME-FX6` **零内置 AF 辅助灯**（`fx6_builtin_af_illuminator_present = False`）；`[Shading Comp.]` 在 FX3 Ver. 7.02 上仅暴露 `Auto / Off`（休眠 `Auto: Low` `LENS_COMP_SHADING_AUTO_LOW` / `0x6c9c` 以 `EOPNOTSUPP=95` 拒绝）；`[Exposure Std. Adjust]` 暴露全部 **5** 种测光模式（`-1.0..+1.0 EV`，`1/6 EV` 步进）；`[Touch Func. in Shooting]` 仅暴露 `Touch Focus / Touch Tracking / Off`（`[Touch Sensitivity]` 为 `Standard / Sensitive`，无 `Responsive`）。
3. **实测事实：三模式 84 项单测、CLI 四态、Milestone 295 双模与全库洁净度审计全部通过**：
   - 新增 [`test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py) 共 **84** 项双模单测（要求 `>= 80`），在 `LOCAL_DONOR_O_RDONLY`（`25.803s`）、`FX3_CLEAN_ROOM_TEST=1`（`26.696s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`26.682s`）下均 **84/84 OK**，有界 `os.O_RDONLY` 供体校验耗时 **`0.555 ms`（`< 0.15s`）**。
   - `make verify-milestone-295` 在 `LOCAL_DONOR_O_RDONLY`（`milestone295_sha256=10ea0a4f49049439...`）与 `CLEAN_ROOM_SYNTHETIC`（`milestone295_sha256=9d1dfced04d3fca2...`）下均返回 **`status=OK`（`6/6` 支柱全绿）**；`make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）返回 **`ALL GREEN in 0.04s`**。
   - 全包 `outputs/fx6-on-fx3-closure/tests` 发现测试（`1,931` 项）：在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下 **1,930/1,931 通过**（`skipped=51`，`271.896s`）；本地模式与洁净室并发运行时 [`test_phase39_stage_b_master_readiness.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase39_stage_b_master_readiness.py) 因 CPU 抢占 `5.170s > 5.0s` 偶发超时，单独串行重跑 **`27/27 OK`（`4.032s`）**；两模式下唯一剩余报错均为基线分支 `1964a0c86` 上与 Phase 302 无关的既有回归 [`test_realhw_milestone295_master_gate.py::test_28_pillar2_fails_when_50a_or_50b_vault_subsuite_fails`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone295_master_gate.py#L698-L709)（`KeyError: 'pillar50_a_pp_scinetone_creativelook_dro_vault'`，严禁越权修改属主范围外文件）。
4. **实测事实：离线默认阻断与硬件安全红线 100% 锁死**：离线无物理回执严格返回 `overall_status = READY_OFFLINE_AWAITING_BENCH_RECEIPTS` 与 `go_no_go = BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（CLI 退出码 `2`）；`--simulate-bench-dry-run` 返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（CLI 退出码 `0`，`16/16 H0 == H3`）；双物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` 验证通过返回 `GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_READONLY_PREFLIGHT_VERIFIED`。无条件锁死 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`cross_model_flash_authorized = False`、`builtin_evf_present = False`、`fx6_builtin_af_illuminator_present = False`、`slot1_tier0_vault_mutated = False`、`usb_packets_transmitted = 0`（`physical_usb_packets_emitted = 0`）、`raw_firmware_bytes_leaked = 0` 与 `passive_tx_bytes_emitted = 0`。

---

## 2. 四大物理台架与官方帮助指南（`ilc/2210`）检查组（`Check Group A .. D`）

| 检查组 ID | 预检域（Waves 53–55） | 核心校验证据与 `实测事实` / `推断` 防线 |
| :--- | :--- | :--- |
| **`GROUP_A_LENS_COMP_BUILTIN_AF_ILLUMINATOR_AF_PERSISTENCE_AND_FOLDER_RATING_VAULT`** | `[Lens Compensation]`、内置 AF LED、5 项 AF 持久化、Slot-1 建夹/评级保护（[Wave 53](../2026-11-17-global-sony-wave53-lens-comp-af-assist-aperture-drive-folder-rating-intel/README.md)） | **实测事实**：① `[Shading Comp.]`（`0x64e1`）仅暴露 `Auto/Off`，休眠 `Auto: Low`（`LENS_COMP_SHADING_AUTO_LOW` / `_f.uxc 0x6c9c`）以 `EOPNOTSUPP=95` 拒绝；`[Chromatic Aberration Comp.]`（`0x68cd`）与 `[Distortion Comp.]`（`0x6200`）受镜头/SteadyShot=Active/无触点手动头约束，`[Breathing Comp.]`（`0x73ea`）仅限 Movie 且可随重置复位；<br>② FX3 具备正面内置 AF 辅助灯 LED `#8`（`0.3..3.0 m`，`0x69c0`/`0xe07f`）且仅限 Still `AF-S`（Movie/`S&Q`/`AF-C`/`MF` 锁定），对比 `ILME-FX6` **零内置 AF 辅助灯**与 Movie/`S&Q` `[AF Transition Speed]`（`1..7`, `0x6e9d`）/`[AF Subj. Shift Sensitivity]`（`1..5`, `0x79d6`）/`[AF Assist]`（`0x64a9`）；<br>③ `[Aperture Drive in AF]`（`0x7879`）、`[AF w/ Shutter]`（`0x771d`）、`[Pre-AF]`（`0x76d8`）、`[Circ. of Focus Point]`（`0x74f6`，仅正交边界循环）与 `[Focus Area Color]`（`0x74ad` `White/Red`）均免疫 `[Camera Settings Reset]`（仅 `[Initialize]` 重置）。<br>**推断（防线）**：`[Create New Folder]`（4,000 张上限）与 `[Rating]`（1..5 星）直接写 DCIM/`AVF_INFO`/EXIF，在只读 `Slot 1` Tier-0 保险库上 fail-closed 拦截（`EROFS=30`/`EBUSY=16`）。 |
| **`GROUP_B_SWITCH_VH_AF_14LIMIT_5MODE_STD_ADJ_TC_FORMAT_AND_COPY_REVERSE_SLOT1_TRAP`** | `[Switch V/H AF Area]`、14 项 `Focus Area Limit`、5 模式 `Exposure Std. Adjust`、TC Format 与 `[Copy]` 反向写槽防火墙（[Wave 54](../2026-11-17-global-sony-wave54-switch-vh-af-focus-limit-bracket-stdadj-copy-slot-intel/README.md)） | **实测事实**：① `[Switch V/H AF Area]`（`0x73ae`：`Off / AF Point Only / AF Point + AF Area`）仅限 Still `AF-C`（`0/90/270 deg` vs `INVALID_VERTICAL_PITCH`）；`[Focus Area Limit]`（`0x6de2`）精确暴露 `14` 项复选框（至少勾 `2` 项 `.uxc 0xea28`，拒绝休眠 `Spot XL/XS/Custom 1..3`）；<br>② `[Exposure Std. Adjust]`（`0x6114`）暴露全部 **5** 种测光模式（`Multi/Center/Spot/Entire Screen Avg./Highlight`，`-1.0..+1.0 EV`、`1/6 EV` 步进、仅 `[Initialize]` 重置）+ Still 专用 `[Bracket Settings]`；<br>③ `[Time Code Format]`（`DF/NDF`）在 `23.98p`/`24.00p` 强制锁 `NDF`、在 `PAL` 隐藏；FX3 无物理 BNC `TC IN/OUT` 切换拨杆。<br>**推断（关键防火墙）**：`[Copy]`（`0x79fc`, `FUNC_copy_content`）在 `[Select Playback Media] == Slot 2` 时将写方向反转为 `Slot 2 -> Slot 1`；当 `Slot 1` 承载 Tier-0 保险库时必须 fail-closed 拦截（`EROFS=30`/`EBUSY=16`），确保 `slot1_data_sector_writes == 0`。 |
| **`GROUP_C_TOUCH_SHOOTING_4MODE_DISP_ZERO_EVF_BLACKOUT_AEL_FLASH_AND_INTERVAL_PLAY`** | `[Touch Func. in Shooting]`、4 模式监视器 `DISP` 与零 EVF 黑屏锁死防火墙、Still 闪光/AEL 与间隔播放（[Wave 55](../2026-11-17-global-sony-wave55-milestone-touch-shooting-disp-btn-evf-absence-ael-wireless-flash-intel/README.md)） | **实测事实**：① `[Touch Func. in Shooting]` 跨 Still/Movie/`S&Q` 仅暴露 `Touch Focus / Touch Tracking / Off`（拒绝休眠 `Touch Shutter / Touch AE / Touch Panel/Pad / Footer Icon Touch`）；`[Touch Sensitivity]` 仅 `Standard / Sensitive`（非 `Responsive`），全部 4 项触控设置仅 `[Initialize]` 重置；<br>② `[Operation Customize] -> [DISP (Screen Disp) Set]` 仅暴露 `4` 种监视器拍摄模式与 `3` 种回放模式，FX3 **零 EVF / 零眼感 / 零 `Select Finder/Monitor` / 零 `Graphic Display`**；<br>③ `[AEL w/ Shutter]`、`[Exp.comp.set]`、`[Wireless Flash]`、`[External Flash Set.]` 均严格限 Still（`FX6` 缺失）；Playback `[Play Speed for Interval]` 为 **`1..9`（默认 `5`）**；`[Beauty Effect]`/`[Trimming]` 为休眠 Edit 陷阱（`EOPNOTSUPP=95`）。<br>**推断（关键防火墙）**：触发任何休眠 EVF/Finder 键位均会引发无 EVF 硬件黑屏锁死，预检器将其作为高危门禁 fail-closed 阻断（`P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP`）。 |
| **`GROUP_D_PHYSICAL_BENCH_READINESS_TIER0_16H0H3_AND_FAIL_CLOSED_REDLINES`** | `16/16 H0 == H3`、双设备 `528 B FX3RCPT1` 与无条件硬件红线 | 核验 `16/16 H0 == H3` 不变性、异构双介质（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` Tier-0 冷备份回执，并强制锁死全部硬件附着、eMMC/SPI-NOR 写入、跨机型刷写及被动字节发射红线。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 `report_sha256` 指纹（实测）

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `4691da38984b8b91cadc91c6ddfd33fdcbd4527cbeb2bc566168ce943c8094b4` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `86e48ba4e19f14f483cbc2cbf8d9230ce5dff9c693bfc498189161bb0a8e16a9` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `f731d4a002c5bb5b4468a81d724e932f51ac44414ac4b6f1cf0d7bb6bdeca32f` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `fc80732f293bc8a796d12f1c948e796f4b84650730381eaa634ce32ae82a7179` |

### 3.2 严格归属的 6 个交付文件

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py)（新增 Phase 302 第 11 级物理台架准备度预检器主模块，含 `inspect_phase302_donors_bounded`、四大检查组、`evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness`、`verify_phase302_report` 与 `render_phase302_markdown`）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（无阴影导出 Phase 302 全部 `P302_*` / `PHASE302_*` / `PHASE_302_*` 公共常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L3682)（接入 `_cmd_preflight_lens_comp_af_illuminator_copy_slot_and_evf_absence` 与 `preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence` CLI 子命令，所有 `argparse` 帮助文本转义 `%%`）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（新增 `# 51.` Phase 302 契约与 CLI 参数文档）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py)（新增 **84** 项三模式单测，统一使用 `sys.executable` 与 `GITHUB_ACTIONS == 'true'` 15.0s 宽裕超时）
6. [`reports/2026-11-17-phase302-preflight11-lens-comp-af-illuminator-copy-slot-evf-absence/README.md`](./README.md)（本实测工程报告）

### 3.3 实测门禁与洁净回执

- **Phase 302 三模式单元测试（84 项，`>= 80`）**：
  - `LOCAL_DONOR_O_RDONLY`（`python3 -B`）：**84/84 OK**（`25.803s`）
  - `FX3_CLEAN_ROOM_TEST=1`：**84/84 OK**（`26.696s`）
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**84/84 OK**（`26.682s`）
- **全包发现测试（`outputs/fx6-on-fx3-closure/tests`，共 `1,931` 项）**：
  - `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室全量发现：**1,930/1,931 通过**（`skipped=51`，`271.896s`）；唯一错误为基线既有测试 [`test_realhw_milestone295_master_gate.py::test_28_pillar2_fails_when_50a_or_50b_vault_subsuite_fails`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone295_master_gate.py#L698-L709)（`KeyError: 'pillar50_a_pp_scinetone_creativelook_dro_vault'`，与 Phase 302 零关联且属于禁止修改文件）。
  - 本地模式并发发现（`363.758s`）：除上述同一既有 `test_28` 错误外，[`test_phase39_stage_b_master_readiness.py::test_02_fast_execution_and_offline_complete`](../../outputs/fx6-on-fx3-closure/tests/test_phase39_stage_b_master_readiness.py#L87) 因双全量并行跑 CPU 竞争录得 `5.170s > 5.0s`；单独串行验证该测试文件 **`27/27 OK`（`4.032s`）**。
- **Milestone 295 门禁（`make verify-milestone-295`）**：`LOCAL_DONOR_O_RDONLY`（`milestone295_sha256=10ea0a4f49049439...`）与 `CLEAN_ROOM_SYNTHETIC`（`milestone295_sha256=9d1dfced04d3fca2...`）均 **`status=OK`（6/6 支柱全绿）**。
- **全库洁净校验（`make clean-audit` / `scripts/run_all_lab_tests.py --clean-only`）**：零 `.pyc`、零未跟踪二进制产物，**ALL GREEN in 0.04s**。

### 3.4 可复现命令

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure python3 -B -m fx6_closure preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence --simulate-bench-dry-run --json
make verify-milestone-295
make clean-audit
```
