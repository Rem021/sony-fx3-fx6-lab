# Phase 284 实机拍摄前第 9 级物理台架准备度预检器报告（`preflight-pp-scinetone-wb-metering-and-shutter-type` / Waves 48–49）

## 1. 核心结论（Conclusion-First）

1. **Waves 48–49 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`）物理台架检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增第 9 级宿主机侧只读物理台架预检器 [`realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py)（Schema `realhw_pp_scinetone_wb_metering_and_shutter_type_verifier_v1`，版本 `284.0.0`，CLI 子命令 `preflight-pp-scinetone-wb-metering-and-shutter-type`），将操作员实拍前预检链路推进至 `preflight-card-insert`（Ph186）→ `preflight-bench-cable-fan-slot1`（Ph204）→ `preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）→ `preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）→ `preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）→ `preflight-diffset-customkey-autoslow-and-apsc`（Ph261）→ `preflight-file-settings-gamma-assist-focus-mag-and-videolight`（Ph275）→ `preflight-usb-mode-hdmi-info-protect-and-network-reset`（Ph279）→ **`preflight-pp-scinetone-wb-metering-and-shutter-type`（Ph284）**，全部公共符号采用无阴影 `P284_*` / `PHASE284_*` / `PHASE_284_*` 前缀并在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) 完整导出。
2. **三模式 72 项单元测试、Milestone 264 与全仓洁净度校验全部通过**：新增 [`test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py) 共 **72** 项双模单测（要求 `>= 68` 项），在 `LOCAL_DONOR_O_RDONLY`（`6.581s`）、`FX3_CLEAN_ROOM_TEST=1`（`5.710s`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（`6.224s`）以及 `/usr/bin/python3 -B`（`4.886s`）下均 **72/72 全绿**，有界 `os.O_RDONLY` 供体校验耗时 **`0.56 ms`（`< 0.15s` 预算）**；全包 `outputs/fx6-on-fx3-closure/tests` 在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下 **1,695/1,695 通过（`170.577s`，`skipped=51`）**；`make verify-milestone-264` 双模式 **`status=OK`（`6/6` 支柱全绿，`1a191febe1366fd9...` / `8523c13ac729a47d...`）**；`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` **ALL GREEN（`0.04s`）**。
3. **离线默认阻断与硬件安全红线 100% 锁死**：离线无回执时严格返回 `overall_status = READY_OFFLINE_AWAITING_BENCH_RECEIPTS` 与 `go_no_go = BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（CLI 退出码 `2`）；`--simulate-bench-dry-run` 返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（CLI 退出码 `0`，`16/16 H0 == H3`）；双物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` 验证通过返回 `GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_READONLY_PREFLIGHT_VERIFIED`；任意检查失败返回 `BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_CHECK_FAILURE`（CLI 退出码 `2`）。无条件锁死 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`lossless_comp_exposed_in_fx3_ui = False`、`shutter_type_auto_exposed_in_fx3_ui = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 与 `passive_tx_bytes_emitted = 0`。

---

## 2. 四大物理台架与官方帮助指南（`ilc/2210`）检查组（`Check Group A .. D`）

| 检查组 ID | 预检域（Waves 48–49） | 关键校验规则、边界与报错码 |
| :--- | :--- | :--- |
| **`GROUP_A_PP11_SCINETONE_CREATIVE_LOOK_DRO_LOG_AND_PP_RESET_TRAP`** | 出厂 `PP11` `S-Cinetone` 耦合 vs `[Creative Look]`/`[DRO]` 互斥、`[Log Shooting]` 锁定与 `PP1..11` 内部复位陷阱（Wave 48 §1） | ① 校验原厂 `ILME-FX3 Ver. 7.02` `[Picture Profile]`（`BKID_APP_setting_picture_profile`，`_f.uxc` `0x6830`）出厂默认 **`PP11`（`S-Cinetone`，`0x67ab`/`0x6e61`）**，且在未勾选 `[Different Set for Still/Mv]`（`0x62ee`）时同时作用于 Movie 与 Still（`P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING`）；<br>② 校验只要 `[Picture Profile] != Off` 即锁定 `[Creative Look]`（`BKID_APP_setting_creative_style_plus`，`0x6823`，`10` 种预设 `ST/PT/NT/VV/VV2/FL/IN/SH/BW/SE`）为 `'-'` 且 `[D-Range Optimizer]`（`0xe89c`）为 `Off`；`[Log Shooting]`（`Flexible ISO` / `Cine EI Quick` / `Cine EI`，`0x6020`）同时锁定 `PP = Off`、`Creative Look = '-'`、`DRO = Off` 与电影 `[Gamma Display Assist] = Off`（`P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT`）；<br>③ 校验 `PPLUT1..4` 仅限 Movie（Still 拒绝）且机内录制时 HDMI 输出钳位至 `1080p`（`P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP`）；<br>④ 校验 `PP1..11` 自定义内部参数与 `[Different Set]` 勾选标记跨 `[Camera Settings Reset]` 与 `[Initialize]` 保留，除非逐个执行 `[Picture Profile] -> [PPx] -> [Reset]`（`P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE`）。 |
| **`GROUP_B_WB_CINE_EI_CUSTOM_CAMSET_EXCLUSION_AND_METERING_6MODES`** | `[White Balance]` `Cine EI` 限制、`Custom 1..3` 持久化 / `CAMSET` 排除与 `[Metering Mode]` 6 模式 `M.M.` 边界（Wave 48 §2–3） | ① 校验 `[White Balance]`（`0xe5d4`，`2500K..9900K` `100K` 步进 + `A7..B7`/`G7..M7`、`Priority Set in AWB`、`Shockless WB` `1 (Fast)`、非 `[Camera Settings Reset]` 可复位的 `Shutter AWB Lock = Off`，`Flash WB` 仅限 Still；`P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE`）；<br>② 校验 `Cine EI` / `Cine EI Quick` 禁用 `Auto` 与 `Underwater Auto` WB，且在 `Log Shooting != Off` 或 `S-Log3`（`PP8`/`PP9`）/`PPLUT1..4` 下执行 `[Custom Setup]` 触发采集报错陷阱（`P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP`）；<br>③ 校验 `Custom 1..3` 跨 `[Camera Settings Reset]` 保留且被 `CAMSET`（`Save/Load Settings`）明确排除（`P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION`）；<br>④ 校验 6 种 `[Metering Mode]`（`Multi`、`Center`、`Spot: Standard`、`Spot: Large`、`Entire Screen Avg.`、`Highlight`，`0xe5cf`）、`De-Squeeze != Off` 时强制 `Face Priority in Multi Metering = Off`、`Spot Metering Point`（`Center`/`Focus Point Link`）、非复位 `AEL w/ Shutter = Auto` 与 `Cine EI` Base ISO（`800`/`12800`）仅驱动 `M.M.` 指示器的不变性（`P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO`）。 |
| **`GROUP_C_STILL_RAW_2OPTIONS_NO_LOSSLESS_HLG_HEIF_AND_DCF_ADOBERGB`** | 静态 2 选项 `[RAW File Type]` vs 休眠 `Lossless Comp` 陷阱、`[HLG Still Image]` 与 DCF 2.0 `AdobeRGB` `_DSC` 前缀规则（Wave 49 §1–2） | ① 校验原厂 `ILME-FX3` 静态 `[RAW File Type]`（`0x6ff2`）仅暴露 **`2` 个选项**（`Compressed` 默认与 `Uncompressed` `14-bit .ARW`），严格拒绝伪造暴露固件内休眠词条 `Lossless Comp`（`0x6b56`，`lossless_comp_exposed_in_fx3_ui == False`），并与无机械快门的纯电影机型 `ILME-FX6`（`mechanical_shutter == False`）划清界限（`P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF`）；<br>② 校验 `[HLG Still Image] = [On]`（`0x76c8`）要求 `[JPEG/HEIF Switch] = HEIF(4:2:0/4:2:2)`、`[File Format] = HEIF` 单选与 `P/A/S/M` 曝光模式（`BT.2100`/`BT.2020`），并同时锁定 `Picture Profile`、`Creative Look`、`DRO` 与 `DRO Bracket`（`P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED`）；<br>③ 校验 `[Color Space]`（`Shooting -> [Image Quality/Rec]` `0x68b7`：`sRGB` `DSC00001` vs `AdobeRGB` `_DSC0001` DCF 2.0 规则），验证 `[Set File Name]`（`0x6993`，不随 `Camera Settings Reset` 复位）禁止手工输入前导 `_`（`P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX`）。 |
| **`GROUP_D_SHUTTER_TYPE_2OPTION_NO_AUTO_FLASH_5LOCKOUT_HIP_AND_TIER0`** | `2` 选项 `[Shutter Type]` 无 `Auto`、`1/250 s` 闪光同步、电子快门 5 项锁定与 `Hi+` `10 fps` `> F11` AF 锁定 + Tier-0（Wave 49 §3–4 + Tier-0） | ① 校验原厂 `ILME-FX3` `[Shutter Type]`（`0x7aa9`）仅暴露 **`2` 个选项**（`Mechanical Shutter` 默认与 `Electronic Shutter`，严格拒绝 `Auto` 伪造，`shutter_type_auto_exposed_in_fx3_ui == False`），`Silent Mode = On` 强制切换 `Electronic` + `Audio signals = Off` + 5 项锁定，电子快门仅限 `P/A/S/M`，且 `[e-Front Curtain Shut.] = [On]` 不随 `Camera Settings Reset` 复位（`P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK`）；<br>② 校验 `1/250 s` 机械快门闪光同步上限，以及电子快门 / `Silent Mode` 下 **5 项功能完整锁定**（`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`，`P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT`）；<br>③ 校验 `High ISO NR` 对 RAW 无效、`8` 模式 `[Drive Mode]`（`Cont. Shooting: Hi+` `10 fps` 在 `Uncompressed` RAW 或闪光时降速、`> F11` 时 AF 锁定首张、连拍禁用 `Long Exposure NR`，`P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE`）；<br>④ 核验 `16/16 H0 == H3`（`P284_GD_ERR_H0_H3_IMMUTABILITY_DRIFT`）与异构双盘 `528 B FX3RCPT1` Tier-0 冷备份回执（`P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID`）。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 SHA-256 指纹

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `46147ffb742263c6eb82860971e57a87b8f27753ec1c69cbad95b9a98d43ca47` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `65694bc45d8b71a6139194095a34ab17cbd03d4daad7cde3595f06c8cdf2991e` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `80d48cba476d12af533104d019dca06cdd4ff35b499a6c3f644cda60a65fa81a` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `be30952f7fe1e325d6988825ce7e0e39be223c5603025a5d8a96cae2a8923b15` |

### 3.2 严格归属的 6 个交付文件

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py)（新增 Phase 284 第 9 级物理台架准备度预检器主模块）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（无阴影导出 Phase 284 全部 `P284_*` 公共常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-pp-scinetone-wb-metering-and-shutter-type` CLI 子命令）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 48` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py)（新增 **72** 项三模式单测）
6. [`reports/2026-11-17-phase284-preflight-pp-scinetone-wb-metering-shutter-type/README.md`](./README.md)（本实测报告）

### 3.3 实测门禁与洁净回执

- **Phase 284 三模式单元测试（72 项，`>= 68`）**：
  - 默认 `LOCAL_DONOR_O_RDONLY`（`python3 -B`）：**72/72 OK**（`6.581s`）；`/usr/bin/python3 -B`：**72/72 OK**（`4.886s`）
  - `FX3_CLEAN_ROOM_TEST=1`：**72/72 OK**（`5.710s`）
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**72/72 OK**（`6.224s`）
- **全包回归发现测试（`outputs/fx6-on-fx3-closure/tests`）**：
  - `FX3_FX6_FORCE_CLEAN_ROOM=1 python3 -B` 洁净室全量发现：**1,695/1,695 OK（`170.577s`，`skipped=51`）**
  - 本地供体全量发现说明（实测事实）：`python3 -B` 全量运行 `1,695` 项时，`1,694/1,695` 通过，仅既有非本任务文件 [`test_phase39_stage_b_master_readiness.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase39_stage_b_master_readiness.py) `test_02` 在长跑尾段实测 `5.080s` 略超其 `< 5.0s` 硬编码阈值（单独运行 `test_phase39_stage_b_master_readiness.py` 为 **27/27 OK, `4.124s`**）；`/usr/bin/python3 -B` 全量发现下 `test_phase39` 与 `test_phase52` 均通过，`1,693/1,695` 通过，仅既有非本任务文件 `test_phase110`（`2.596s`）与 `test_phase130`（`2.516s`）因 CPython 3.9 略超 `< 2.5s`（在 `python3 -B` 3.14.10 下二者合并运行 **82/82 OK, `8.530s`**）。严格遵循“仅改 6 个归属文件”红线，未改动既有测试文件阈值。
- **Milestone 264 门禁（`make verify-milestone-264`）**：`LOCAL_DONOR_O_RDONLY`（`milestone264_sha256=1a191febe1366fd9...`）与 `CLEAN_ROOM_SYNTHETIC`（`milestone264_sha256=8523c13ac729a47d...`）均 **`status=OK`（6/6 支柱全绿）**。
- **全库洁净校验（`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only`）**：零 `.pyc`、零未跟踪二进制产物，**ALL GREEN（`0.04s`）**。

### 3.4 可复现命令

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_pp_scinetone_wb_metering_and_shutter_type_verifier.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm python3 -B -m fx6_closure preflight-pp-scinetone-wb-metering-and-shutter-type --simulate-bench-dry-run --json
```
