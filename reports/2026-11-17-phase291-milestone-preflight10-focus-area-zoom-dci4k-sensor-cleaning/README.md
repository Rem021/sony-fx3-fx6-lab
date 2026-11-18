# Phase 291 第 10 级物理台架准备度预检器里程碑报告（`preflight-focus-area-zoom-dci4k-and-sensor-cleaning` / Waves 50–52）

## 1. 核心结论（Conclusion-First）

1. **Waves 50–52 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`，Model `0x91030080`）物理台架检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增第 10 级（**10th Physical Bench Readiness Verifier Milestone**）宿主侧只读物理台架预检器 [`realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py)（Schema `realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier_v1`，版本 `291.0.0`，CLI 子命令 `preflight-focus-area-zoom-dci4k-and-sensor-cleaning`），将操作员实拍前 10 级预检链路推进至 `preflight-card-insert`（Ph186）→ `preflight-bench-cable-fan-slot1`（Ph204）→ `preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）→ `preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）→ `preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）→ `preflight-diffset-customkey-autoslow-and-apsc`（Ph261）→ `preflight-file-settings-gamma-assist-focus-mag-and-videolight`（Ph275）→ `preflight-usb-mode-hdmi-info-protect-and-network-reset`（Ph279）→ `preflight-pp-scinetone-wb-metering-and-shutter-type`（Ph284）→ **`preflight-focus-area-zoom-dci4k-and-sensor-cleaning`（Ph291）**，全部公共符号采用无阴影 `P291_*` / `PHASE291_*` / `PHASE_291_*` 前缀并在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) 完整导出。
2. **三模式 76 项单元测试、全包 1,771 项洁净室发现、Milestone 264 与全仓洁净度校验全部通过**：新增 [`test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py) 共 **76** 项双模单测（要求 `>= 72` 项），在 `LOCAL_DONOR_O_RDONLY`（`python3 -B` `23.715s`、`/usr/bin/python3 -B` `24.528s`）、`FX3_CLEAN_ROOM_TEST=1`（`24.090s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`24.500s`）下均 **76/76 全绿**，有界 `os.O_RDONLY` 供体校验耗时 **`0.476 ms`（`< 0.15s` 预算）**；全包 `outputs/fx6-on-fx3-closure/tests` 在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下 **1,771/1,771 通过（`196.968s`，`skipped=51`）**；`make verify-milestone-264` 双模式 **`status=OK`（`6/6` 支柱全绿，`684f75069504aceb...` / `a9960a96120317b5...`）**；`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` 与 `make clean-audit` 均 **ALL GREEN**。
3. **离线默认阻断与硬件安全红线 100% 锁死**：离线无物理回执时严格返回 `overall_status = READY_OFFLINE_AWAITING_BENCH_RECEIPTS` 与 `go_no_go = BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（CLI 退出码 `2`）；`--simulate-bench-dry-run` 返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（CLI 退出码 `0`，`16/16 H0 == H3`）；双物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` 验证通过返回 `GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_READONLY_PREFLIGHT_VERIFIED`；任意检查失败返回 `BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_CHECK_FAILURE`（CLI 退出码 `2`）。无条件锁死 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`cross_model_flash_authorized = False`、`xlr_h1_zoom_lever_present = False`、`fx3_private_sony_pro_camera_used = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 与 `passive_tx_bytes_emitted = 0`。

---

## 2. 四大物理台架与官方帮助指南（`ilc/2210`）检查组（`Check Group A .. D`）

| 检查组 ID | 预检域（Waves 50–52） | 关键校验规则、边界与报错码 |
| :--- | :--- | :--- |
| **`GROUP_A_FOCUS_AREA_STILL_TRACKING_BODY_WT_ZOOM_ISO_AND_FLASH_GATE`** | Still-only `Tracking:` 对焦区域、`XLR-H1` 无变焦拨杆纠偏、`ISO Range Limit`/`ISO AUTO Min. SS` vs `Cine EI`、机械静态快门闪光门禁（Wave 50） | ① 校验 `ILME-FX3 Ver. 7.02` `[Focus Area]`（`BKID_APP_setting_autofocus_area_contrast_detect_af`，`_f.uxc` `0x70ac`）全部 `14` 个选项（`7` 个非跟踪 + `7` 个 `Tracking:`）：所有 `7` 个 `Tracking:` 区域严格 **仅限 Still `AF-C`**（Movie/`S&Q` 使用 `[Touch Tracking]`），`[Focus Area Limit]` `>= 2`、Still-only `[Switch V/H AF Area]`、非复位 `[Focus Area Color]`（`White`/`Red`）、`[Circ. of Focus Point]` 与 `ilc/2210` 精确命名 **`AF Area Registration`**（非旧称 `AF Area Regist.`；`P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG`）；<br>② 实证纠偏 **`ILME-FX3` `XLR-H1` 音频手柄无变焦拨杆、无 REC 键、无 `ZOOM HOLD` 开关**（`xlr_h1_zoom_lever_present == False`），仅机身 `W/T` `[Zoom Lever Speed]`（`1..8` `STBY`/`REC`）、`[Custom Key Z. Speed]`（`1..8`）与 `[Remote Zoom Speed]`（`Variable`/`Fixed 1..8`）生效，对比 `FX6` Smart Handle（`Handle Zoom` `Off/Low/High/Variable 1..8` + `Handle HOLD Switch`，且 `0..99` 为 `Zoom Position Display` 指示而非 `Fixed 1..99` 速率；`P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED`）；<br>③ 校验非复位 `[ISO Range Limit]`（`50..409600`）与 Still `P/A`+`ISO AUTO` 限定 `[ISO AUTO Min. SS]` 对比 `Cine EI`/`Cine EI Quick` Base ISO `800`/`12800` 硬锁（`P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK`）；<br>④ 校验 `[Flash Mode]` 及闪光栈严格门控至 `EXPOSURE_MODE_STILL` + `Mechanical Shutter`（`1/250 s`），而 `[Video Light Mode]` 横跨 Still/Movie/`S&Q` 且受 `MI-Shoe 5V <= 900 mA` PMIC 约束（`P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT`）。 |
| **`GROUP_B_XAVC_SI_DCI4K_24P_ASPECT_CUSTOM_HOLD11_CAMSET_AND_PHOTO_CAPTURE`** | `XAVC S-I DCI 4K` `4096x2160` + `24.00p` 重启隔离、Still `Aspect Ratio`、`11` 项 `Recall Custom hold`、`/SONY/SETTING/%s/` 卡路径、`Photo Capture` 封锁（Wave 51） | ① 校验 `ILME-FX3 Ver. 3.00+/7.02` **确有暴露 `[XAVC S-I DCI 4K]`**（`_f.uxc` `0x7336`、`4096x2160` `17:9` All-Intra `4:2:2 10-bit`，`23.98p..59.94p` + `S&Q <= 48fps`，无 `100/120p`）以及强制重启且清空 `/tmp` Stage-B 易失覆盖的 `24.00p`（`0x75ce`），而 Long-GOP（`XAVC HS/S 4K`）与 `XAVC S-I 4K` 保持 `3840x2160` UHD、HDMI RAW 输出 `4264x2408`（`P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY`）；<br>② 校验 Still `4` 档 `[Aspect Ratio]`（`3:2`/`4:3`/`16:9`/`1:1`，`APS-C S35` 下 `L->M` 降档；`P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC`）；<br>③ 校验 Still `P/A/S/M` `[Reg. Custom Shoot Set]` 暴露全部 **`11` 个**保持复选框（`is_checked_recall_custom_hold0..10`）及 ISO/DRO-BKT 保持期间强制 `HLG Still = Off`（`P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK`）；<br>④ 校验 `FX3` 卡上 `M1..M4`（`CAMPR%02d%c.DAT`）与 `CAMSET` 均位于 **`%c:%s/SONY/SETTING/%s/`**（绝对零 `FX6` 专属 `PRIVATE/SONY/PRO/CAMERA`；`P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA`）；<br>⑤ 校验 `[Photo Capture]`（`8.3M` UHD / `2.1M` HD）对 `XAVC S-I DCI 4K` 片段拒绝执行（`_g.uxc` `0x60ce`）并在只读 `Slot 1` Tier-0 防火墙下 fail-closed 阻断，同时验证 Still-only `[Enlarge Image]` / `[Enlarge Initial Mag.]` / `[Enlarge Initial Position]`（`P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL`）。 |
| **`GROUP_C_SENSOR_CLEANING_51PCT_EV_COMP_CINE_EI_FOCUS_5VS2_AND_PLAYBACK`** | `[Sensor Cleaning]` `>= 51%` 电量与强制关机 vs `FX6` `e-ND`、`[Exposure Comp.]` vs `Cine EI`、`[Focus Mode]` 5 vs 2 与回放/旋转防火墙（Wave 52） | ① 校验 `[Sensor Cleaning]`（`_f.uxc` `0x67d6`，旧 `.uxc` `0xe7d7` `Cleaning Mode`）要求 `NP-FZ100 >= 51%` + IBIS 抖动后强制物理关机（`_g.uxc` `0x6221`，无人值守 Tier-0 转储期间阻断），对比无 IBIS 且传感器前覆 `e-ND` 光模块的 `ILME-FX6`（`CrCommandId 320` 不支持，使用 `APR`；`P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END`）；<br>② 校验 `[Exposure Comp.]`（Still `±5.0 EV` / Movie `±2.0 EV`）在 `M` 模式下仅对 `ISO AUTO` 生效、在 `Cine EI`/`Cine EI Quick` 下 **100% 锁死**（改用 `[Exposure Index]`），且 `FX3` 已删略 Alpha 物理拨盘遗产 `[Reset EV Comp.]`（`P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK`）；<br>③ 校验 `[Focus Mode]` Still `5` 模式（`AF-S`/`AF-A`/`AF-C`/`DMF`/`MF`）vs Movie/`S&Q` `2` 模式（`AF-C [MOVIE_AUTO]` / `MF`）分裂及 `[AF Assist]`/`[Priority Set in AF-S/AF-C]`/`[AF Illuminator]`（`P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU`）；<br>④ 校验非复位 3 模式 `[View Mode]`、2 模式 `[Image Index]`（`9`/`25 Images`，封杀休眠 `12`/`30 Images`）、`[Display as Group]`/`[Display Rotation]` 以及 `[Rotate]` 在只读 `Slot 1` Tier-0 金库上的 fail-closed 阻断（`P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL`）。 |
| **`GROUP_D_PHYSICAL_BENCH_READINESS_TIER0_16H0H3_AND_FAIL_CLOSED_REDLINES`** | `16/16 H0 == H3`、双盘 `528 B FX3RCPT1` Tier-0 与无条件硬件红线 | 核验 `16/16 H0 == H3`（`P291_GD_ERR_H0_H3_IMMUTABILITY_DRIFT`）、异构双盘（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` Tier-0 冷备份回执（`P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID`）以及全套物理写入红线锁定（`P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION`）。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 SHA-256 指纹

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `7463da55c3eb09969772335744a426bbcff968ee7e8c9241c25df8fac17fb4a8` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `7024dc94e13610663181ec2595f90dab76bbb4d1d4f9dbfbc5faacf5fdb79d85` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `6a20f72eea90bc18af9a12f4c73e1d6a895edfd30f7fd949ee4efd2c7030e5ac` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `afac44e6db8145a618a89ed96878429dd81778b15226231798a18752b4487758` |

### 3.2 严格归属的 6 个交付文件

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py)（新增 Phase 291 第 10 级物理台架准备度预检器主模块）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（无阴影导出 Phase 291 全部 `P291_*` 公共常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-focus-area-zoom-dci4k-and-sensor-cleaning` CLI 子命令，已转义全部 `argparse` 帮助文本 `%`）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 49` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py)（新增 **76** 项三模式单测，统一采用 `sys.executable` 与 `15.0s` 子进程宽松超时阈值）
6. [`reports/2026-11-17-phase291-milestone-preflight10-focus-area-zoom-dci4k-sensor-cleaning/README.md`](./README.md)（本实测报告）

### 3.3 实测门禁与洁净回执

- **Phase 291 三模式单元测试（76 项，`>= 72`）**：
  - 默认 `LOCAL_DONOR_O_RDONLY`（`python3 -B`）：**76/76 OK**（`23.715s`）；`/usr/bin/python3 -B`：**76/76 OK**（`24.528s`）
  - `FX3_CLEAN_ROOM_TEST=1`：**76/76 OK**（`24.090s`）
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**76/76 OK**（`24.500s`）
- **全包回归发现测试（`outputs/fx6-on-fx3-closure/tests`）**：
  - `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" python3 -B` 洁净室全量发现：**1,771/1,771 OK（`196.968s`，`skipped=51`）**
- **Milestone 264 门禁（`make verify-milestone-264`）**：`LOCAL_DONOR_O_RDONLY`（`milestone264_sha256=684f75069504aceb...`）与 `CLEAN_ROOM_SYNTHETIC`（`milestone264_sha256=a9960a96120317b5...`）均 **`status=OK`（6/6 支柱全绿）**。
- **全库洁净校验（`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit`）**：零 `.pyc`、零未跟踪二进制产物，**ALL GREEN**。

### 3.4 可复现命令

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm python3 -B -m fx6_closure preflight-focus-area-zoom-dci4k-and-sensor-cleaning --simulate-bench-dry-run --json
```
