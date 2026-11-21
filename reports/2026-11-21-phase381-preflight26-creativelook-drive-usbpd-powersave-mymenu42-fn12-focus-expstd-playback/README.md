# Phase 381 工程闭合报告：第 26 级物理台架准备度预检器（`26/26`，`preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback` / `preflight-phase381`，Global Sony Waves 83–84）

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H486` · **Phase 381（`26/26` Physical Bench Readiness Verifiers）**
- **上游实证情报基线**：
  - [Global Sony Wave 83 实证情报报告](../2026-11-21-global-sony-wave83-creativelook-softskin-contshoot-bracket-usbpower-pd-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` & 2025 `ILME-FX3A` `ilc/2510` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`：`[Creative Look]` 10+6 / `354` 条 NVRAM 键与 3 轨 `look`/`look_still`/`look_movie`、非对称 `0..9` `Fade`/`Sharpness`/`Clarity`、4 项硬互锁与 100% 休眠 `[Soft Skin Effect]`；Still `[Drive Mode]` 8 模式 `Hi+ 10 fps` 无实时取景、`> F11` 首帧锁焦（非 `F8`）、`CEA-G160T` `~1,000+` 缓冲、精确 `16` 组 EV 包围、100% 休眠 `[Focus Bracket]`（`129` FX3 / `98` FX6，Wave 83 `G151` 勘误 `56` vs `98`）、Ver. 7.02 `[Shutter Type in Interval]` 与 FX6 零 `Frame Rec`；`libUsbBusPower.so` `48,232 B` `11` 个 PMIC 驱动、强制 `NP-FZ100` 握手、USB-PD `9V/3A` `HIGH` / `5V/1.5A` `LOW` / `Sony DC-C1` `>= 65W+5A`、热拔电池绕过 `SequenceAsync_PowerOff`/`mcmn_drv_writeandflush`/`fsync` 掉电红线 vs FX6 `19.5V` EIAJ `DC IN`；以及精确 2 项抗 Reset `[Power Setting Option]`、FX3 `9` 项 vs `ILME-FX3A` `8` 项旁路与 IR/NFC 物理删减、100% 休眠 `[Power Save by Monitor]`、FX3 IR/BLE 互斥、Ver. 7.00+ `[USB-LAN Cnct. Launch]` vs FX6 `2.5 mm` LANC + `3.5 mm` 手柄远控）
  - [Global Sony Wave 84 实证情报报告](../2026-11-21-global-sony-wave84-mymenu-fn12-focusmode-expstd-playback-rating-intel/README.md)（`[My Menu]` 精确 `6 × 7 = 42` 槽位与 Wave 84 `G98` 勘误、Playback 黑名单、6 项抗 Reset 管理与 Slot 1 `CAMSET01..10.DAT` `EROFS=30`；`12+12` `[Fn Menu Settings]` 零 `Follow Custom`、全 `Not set` `_f 0x6220` 拦截、`XLR-H1` 零 `Fn`/`MENU`/REC 键 vs FX6 `20` 项 `User Menu`；`[Focus Mode]` Still `5` 态 vs Movie/`S&Q` 硬锁 `2` 态、抗 Reset `[AF w/ Shutter]`/`[Pre-AF]`、Movie `[AF Subj. Shift Sensitivity]` 出厂默认 `5(Responsive)` 非 `3`（ELF `MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE`）、`14` 项 `[Focus Area Limit]` 与正交 `[Circ. of Focus Point]`；`[Exposure Comp.]`/`[Exposure step]`/全 5 模式 `[Exposure Std. Adjust]`（`-6..+6` 六分之一档 13 级抗 Reset）/Still `[AEL w/ Shutter]`/`[Spot Metering Point]` 精确 `8` 联动 vs `6` 锁心（Wave 84 `G116` 勘误）vs FX6 `Auto Exposure Level` 25 档零 `AE Shift` 与 `AGC Limit`；以及精确 3 态 `[View Mode]`、`[Display Rotation]` 默认 `Auto`（ELF `BKID_APP_setting_display_rotatiton`）、`[Protect]` 精确 7 菜单项零 `"Single"`（Wave 84 `G114` 勘误，同步 `M4ROOT/SUB/*S03.MP4`）与 `[Rating]` `0..5` 的 Slot 1 `EROFS=30` 防火墙、`[Select on Cam & Send]` 零射频 `[Airplane Mode]=On` 拦截 vs FX6 `Thumbnail`/`OK-NG-KEEP`/`Shot Mark 1-2`/`Lock-Unlock Clip`）
- **前序模板基线**：
  - [Phase 374 工程闭合报告](../2026-11-21-phase374-preflight25-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-format/README.md)（第 25 级预检器模板）

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 26 级物理台架预检器严格在 6 文件所有权范围内落地，将 `fx6_closure` 只读物理台架预检体系推进至 `26/26`**
   - 新增 [`realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py)（`3,519` 行，Schema `realhw_preflight26_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_playback_v1`，版本 `phase381_v1`），完成 Check Groups A–D 与强制 `16/16 H0 == H3` 双介质 `528 B FX3RCPT1` Tier-0 回执闸门。
   - 全部 `216` 项公共符号已以非遮蔽方式接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) 与 `__all__`（AST 查重 `DUP_IMP: []`、`DUP_ALL: []`，全包导入 `4,596` 项 / `__all__` `4,594` 项零回归）。
   - CLI 主命令 `preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback` 与短别名 `preflight-phase381` 已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（所有 `help=` 中 `%` 均已转义为 `%%`，`--help` 实测 `rc=0`），长命令与短别名在干跑模式下生成 **字节级一致的 `report_sha256`**；并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) 追加 Section `# 71.`。
2. **`实测事实`：120 项 4 模式单元测试、CLI 门控、双模 `make verify-milestone-375` 与 `make clean-audit` 全部通过**
   - [`test_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py)（`1,853` 行，`120` 项测试，`>= 116` 要求）在全部 4 种模式下均实测 `Ran 120 tests -> OK`（`0` 失败、`0` 跳过、`0` `.pyc`）：① 常规模式、② `FX3_CLEAN_ROOM_TEST=1`、③ `FX3_FX6_FORCE_CLEAN_ROOM=1`、④ 无供体 `FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase381_missing`。
   - 供体巡检采用 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 有界 64 B 头读取（`<= 2.0s`），带 `work_root is None` 保护与自动 `CLEAN_ROOM_SYNTHETIC` 回退，全程 `raw_firmware_bytes_leaked == 0`。
   - 双模 `make verify-milestone-375`（常规与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）均实测 `status=OK`、`pillars=6/6`、`leaked=0`；`PYTHONDONTWRITEBYTECODE=1 make clean-audit` 实测 `ALL GREEN`、`0` 个 `.pyc`。
3. **`实测事实` + `工程推断`：离线硬件与写入红线全程 Fail-Closed**
   - 离线默认返回 `rc=2`（`GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`），`--simulate-bench-dry-run` 返回 `rc=0`（`GO_NO_GO_DRY_RUN_SIMULATED_READY`）；两种模式下 `overall_ready_for_hardware_attach`、`live_attach_authorized`、`emmc_writes_authorized`、`cross_model_flash_authorized` 均硬锁 `False`，全部遥测写入计数（`slot1_sector_writes`、`slot1_data_sector_writes`、`emmc_write_count`、`rf_tx_packets`、`raw_firmware_bytes_leaked`）硬锁 `0`。

---

## 2. Check Groups A–D 实证覆盖与 CLI 回执账本

### 2.1 四组检查矩阵

| Check Group | 组 ID | 核心实证校验范围（Waves 83–84） |
| :---: | :--- | :--- |
| **A** | `p381_ga_creativelook_354nvram_softskin_drive_f11_focusbracket_interval` | `[Creative Look]` `10+6` / `354` NVRAM 键（`2` + `352` 含 `look`/`look_still`/`look_movie`）、`0..9` 非对称 `Fade`/`Sharpness`/`Clarity`、`1..5` `Sharpness Range`（Movie/S&Q 锁）、`BW`/`SE` `Saturation` 锁、4 硬锁（`PP11`/`Log`/`HLG`/`iAuto`）、休眠 `[Soft Skin Effect]` (`EOPNOTSUPP=95`) vs FX6 `Base Look + User 1..16`；Still `[Drive Mode]` 8 模式 `Hi+ 10 fps` 无实时取景、`> F11` 首帧锁焦（非 `F8`）、`CEA-G160T` `>= 1000` 缓冲、精确 `16` 组 EV 包围、休眠 `[Focus Bracket]`（`129`/`98` `G151` 勘误）、7 项全 `Can be reset` `[Interval Shoot Func.]` & Ver. 7.02 `[Shutter Type in Interval]` vs FX6 零 `Frame Rec` |
| **B** | `p381_gb_usbpd_11pmic_npfz100_dcc1_powersave_fx3_9_vs_fx3a_8_ir_lanc` | `libUsbBusPower.so`（`48,232 B`、`11` PMIC `.ko`）、强制在位 `NP-FZ100` (`7.2 V`)、USB-PD `9V/3A` `HIGH`（开机零充电、关机 `10–30°C` `>= 18 W`）、`5V/1.5A` `LOW` 掉电、`Sony DC-C1`（`>= 65 W + 5A`）、热拔电池绕过 `SequenceAsync_PowerOff`/`mcmn_drv_writeandflush`/`fsync` 掉电红线 vs FX6 `19.5V` EIAJ `DC IN`；精确 2 项抗 Reset `[Power Setting Option]`、FX3 `9` 项 vs `ILME-FX3A` `8` 项旁路、休眠 `[Power Save by Monitor]` (`EOPNOTSUPP=95`)、`ILME-FX3A`（`ilc/2510`）IR/NFC 物理移除、FX3 IR/BLE 互斥、Ver. 7.00+ `[USB-LAN Cnct. Launch]` vs FX6 `2.5 mm` LANC + `3.5 mm` 手柄 |
| **C** | `p381_gc_mymenu42_fn12_focusmode_5vs2_subjshift5_focuslimit14_circ` | `[My Menu]` 精确 `6 × 7 = 42` 槽位（Wave 84 `G98` 勘误辟谣 `30`/`36`）、Playback 黑名单、6 项抗 Reset 操作、Slot 1 `CAMSET01..10.DAT` Save/Delete `EROFS=30`；`12+12` `[Fn Menu Settings]` 零 `Follow Custom`、全 `Not set` `_f 0x6220` 阻断、`XLR-H1` 零 `Fn`/`MENU`/REC 键 vs FX6 `20` 项 `User Menu`；`[Focus Mode]` Still `5` vs Movie/`S&Q` 硬锁 `2`、抗 Reset `[AF w/ Shutter]`/`[Pre-AF]`、Movie `[AF Subj. Shift Sensitivity]` 默认 `5(Responsive)` 非 `3`（`MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE`）、`14` 项 `[Focus Area Limit]`（最少 2 项）、正交 `[Circ. of Focus Point]` vs FX6 `Face/Eye Detection AF` |
| **D** | `p381_gd_expcomp_expstd5_spot8vs6_playback_slot1_erofs30_zerorf_tier0` | `[Exposure Comp.]`（Still `±5.0`/Movie `±2.0 EV`）、抗 Reset `[Exposure step]`（独立于 `Shutter Angle`）、全 5 测光模式 `[Exposure Std. Adjust]`（`±1 EV @ 1/6 EV` 13 级抗 Reset）、Still 抗 Reset `[AEL w/ Shutter]`、`[Spot Metering Point]` 精确 `8` 联动（追踪仅初点）vs `6` 锁心（Wave 84 `G116` 勘误）vs FX6 `Auto Exposure Level` 25 档零 `AE Shift` + `AGC Limit`；`[View Mode]` 精确 3 态、`[Display Rotation]` 默认 `Auto`（`BKID_APP_setting_display_rotatiton`）、`[Image Index]` `9/25`、`[Display as Group]`、`[Enlarge]` 抗 Reset、`[Protect]` 7 菜单项零 `"Single"`（Wave 84 `G114` 勘误，同步 `M4ROOT/SUB/*S03.MP4`）& `[Rating]` `0..5` Slot 1 `EROFS=30`、`[Select on Cam & Send]` 零射频 `[Airplane Mode]=On` 拦截 vs FX6 `Thumbnail`/`OK-NG-KEEP` + 双介质 `528 B FX3RCPT1` `16/16 H0 == H3` Tier-0 闸门 |

### 2.2 四态 CLI 确定性回执（`实测事实`）

| 验证模式 | Dry-Run | `overall_status` | `go_no_go` | CLI `rc` | 供体读取（`O_RDONLY\|O_NOFOLLOW\|O_NONBLOCK`） | `raw_firmware_bytes_leaked` | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1/12`（`64 B`） | `0` | `9d4669d0643a2ce3e35641f0011334513cc68968a0e656fc24bf0f7928dc6c12` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `1/12`（`64 B`） | `0` | `24432e038ed07640c6b27d5c0d9efc289b55d699653ff1e9e7b6e5344788ace8` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/12`（`0 B`） | `0` | `2d914b06be95d1a67c1bb3b7172a875d6ebe4638466d19f81074990176902db4` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/12`（`0 B`） | `0` | `6d63151365a810bb3c43860320db4fb245516e33d698fb52b5a532082ec476d3` |

### 2.3 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py)（新增，`3,519` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（新增 Phase 381 `216` 项非遮蔽导入与 `__all__` 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（新增主命令 `preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback` 与短别名 `preflight-phase381`、全量参数与分派）
4. [`outputs/fx6-on-fx3-closure/tests/test_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py)（新增，`120` 项 4 模式单元测试，`1,853` 行）
5. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（追加 Section `# 71.`）
6. [`reports/2026-11-21-phase381-preflight26-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-playback/README.md`](./README.md)（本工程闭合报告）

---

## 3. 可复现验证命令与实测结果（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_verifier.py"
CMD="preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback"

# 1. 四模式 120 项单元测试（均已实测 Ran 120 tests -> OK）
env -u FX3_CLEAN_ROOM_TEST -u FX3_FX6_FORCE_CLEAN_ROOM -u FX3_FX6_MAC_WORK_ROOT PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase381_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"

# 2. CLI 门控与别名一致性实测（--help rc=0, 离线 rc=2, 干跑 rc=0, 长短命令 SHA-256 字节一致, leaked=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase381 --simulate-bench-dry-run --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase381 --force-clean-room --simulate-bench-dry-run --json

# 3. Milestone 375 双模总闸门与洁净度审计（均已实测 status=OK, pillars=6/6, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-375
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 make verify-milestone-375
PYTHONDONTWRITEBYTECODE=1 make clean-audit
```
