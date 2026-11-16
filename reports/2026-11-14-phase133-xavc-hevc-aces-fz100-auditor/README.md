# Phase 133 — 26th Unified `fx3-firmware-lab` Auditor: `BIONZ XR` `XAVC HS` (`HEVC 10-Bit 4:2:2`) vs `XAVC S-I` / `XAVC-I`, `ACES 1.3/2.0` `S-Log3` / `S-Gamut3(.Cine)` `IDT`, & `NP-FZ100` `C-Pin` Handshake
# 第 133 阶段 — 第 26 个统一 `fx3-firmware-lab` 审计器：`BIONZ XR` `XAVC HS`（`HEVC 10-Bit 4:2:2`）与 `XAVC S-I` / `XAVC-I`、`ACES 1.3/2.0` `S-Log3` / `S-Gamut3(.Cine)` `IDT` 及 `NP-FZ100` `C-Pin` 电源握手审计

- **Date / 日期**: 2026-11-14
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/xavc_hevc_intra_aces_idt_and_fz100_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/xavc_hevc_intra_aces_idt_and_fz100_auditor.py)
- **CLI Subcommand / CLI 子命令**: `audit-xavc-aces-fz100` (and integrated as #26 in `audit-all`)
- **Tests / 单元测试**: [`outputs/fx3-firmware-lab/tests/test_xavc_hevc_intra_aces_idt_and_fz100.py`](../../outputs/fx3-firmware-lab/tests/test_xavc_hevc_intra_aces_idt_and_fz100.py) (**40/40** passing in both modes; full suite **793/793** passing in both modes)
- **Web Intelligence Sync / 情报同步**: [`reports/2026-11-14-global-sony-wave16-aces-hevc-fz100-unbrick-intel/README.md`](../2026-11-14-global-sony-wave16-aces-hevc-fz100-unbrick-intel/README.md)

---

## English Technical Summary

### 1. Verification Results & Deterministic Digests

| Verification Gate | Mode / Scope | Result | Runtime | Digest / Count |
| :--- | :--- | :--- | :--- | :--- |
| `analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=False)` | `LOCAL_DONOR_VERIFIED` (12 donor files `os.O_RDONLY`) | `all_checks_passed = True` | `0.1900 s` (`< 0.35 s`) | `report_sha256 = 7a02fa8820f0c8e50a431e4afc09f909349c0c94e65fd83855ca07a1766bc534` |
| `analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)` | `CLEAN_ROOM_SYNTHETIC` | `all_checks_passed = True` | `0.0019 s` (`< 0.02 s`) | `report_sha256 = 9b86361a854c1fcb9e3052b75a1e0bdcba0819c401bc0ae3d6b6f2536a3d235c` |
| `audit-all --json` (Local Donor) | All 26 auditors | `all_checks_passed = True` (`26/26`) | `9.601 s` | `26/26` green |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... audit-all --json` | All 26 auditors (Clean-Room) | `all_checks_passed = True` (`26/26`) | `0.560 s` | `26/26` green |
| `unittest` Phase 133 suite | Local Donor / Forced Clean-Room | `OK` (`40/40` each) | `0.727 s` / `0.391 s` | `40` tests |
| `unittest discover` (full suite) | Local Donor / Forced Clean-Room | `OK` (`793/793` each) | `24.888 s` / `13.603 s` | `793` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Binary / `.pyc` / `git status` hygiene | `CLEAN` | `0.05 s` | `0` forbidden artifacts |

### 2. Verified Donor Artifacts (`os.O_RDONLY` + `mmap.ACCESS_READ`, Zero Mutations)

- **FX3 `v7.02`**: `appFw.so` (`79,015,712 B`), `libmpr.so` (`3,517,008 B`), `cpapp-b.bin` (`15,980,568 B`), `global.xdb` (`11,664 B`), `string_english.uxc` (`165,740 B`, `ns=39`), `string_english_g.uxc` (`69,600 B`, `ns=3`).
- **FX6 `v6.01`**: `appFw.so` (`50,520,424 B`), `libmpr.so` (`28,921,824 B`), `cpapp-b.bin` (`17,952,816 B`), `global.xdb` (`1,792 B`), `string_english.uxc` (`118,208 B`, `ns=1`), `string_english_2.uxc` (`118,676 B`, `ns=2`).
- Verified `.uxc` `STRID`s (100% matched in both donor and clean-room modes):
  - `FX3 ns=39`: `0x0000e02e` (CFexpress VPG200 / Proxy Slot 2 caution), `0x0000e24e` (`"The operation and safety of this battery\ncannot be guaranteed.\nContinue use?"`), `0x0000e704` (`"Battery exhausted."`).
  - `FX3 ns=3`: `0x00006013` (`"Update cannot be executed due to\ninsufficient battery power."`), `0x000060ce` (`XAVC S-I DCI 4K` op restriction).
  - `FX6 ns=1`: `0x0000219f` (`"S-Log3"`), `0x00002b03` (`"XAVC S-I"`), `0x00002693` (`"Battery Error\nPlease Change Battery"`).
  - `FX6 ns=2`: `0x00004005` (`"Voltage Low"`), `0x00004269` (`"DC Voltage Alarm"`), `0x000044fe` (`"S-Gamut → S-Gamut3.Cine"`), `0x00004550` (`"Battery Remain"`).

### 3. Four Audited Pillars

1. **Pillar A — `BIONZ XR` Hardware Codec Matrix (`XAVC HS` vs `XAVC S-I` / `XAVC-I`)**:
   - Proves `FX6 XAVC-I Class 300 (MXF OP1a)` and `FX3 XAVC S-I 4K (MP4 ISO-BMFF)` share identical `AVC_H264_HIGH_422_INTRA` (`AVC480_*_H422IP`) elementary bitstreams (`240..600 Mbps` standard, `1200 Mbps` S&Q `119.88p`), diverging only at `libXavcMxf` vs `libXavcMp4`.
   - Enforces `SDXC V90` (`720 Mbps`) for `600 Mbps` `4K 59.94p`, `CFexpress Type A VPG200/VPG400` (`1600/3200 Mbps`) for `S&Q 120p` (`1200 Mbps`), `SDXC V60` (`480 Mbps`) + hardware decode recommendation for `XAVC HS 4K 4:2:2 10-bit` (`100/200 Mbps`), proxy `+16 Mbps` budget accounting, and hard-blocks FX3 internal `25p / 29.97p` `XAVC HS` gaps (`BLOCKED_XAVC_HS_UNSUPPORTED_FPS`).
2. **Pillar B — `ACES 1.3 / 2.0` `S-Log3` & `S-Gamut3 / S-Gamut3.Cine -> AP0 / AP1` IDT Verifier**:
   - Verifies Sony `S-Log3` landmarks (`0% -> 95.0`, `18% -> 420.0`, `90% -> 597.895257`), piece-wise break continuity at `lin=0.01125 / CV=171.2102946929` (`delta = 3.94e-11 < 1e-6`), and roundtrip precision (`max_roundtrip_error = 7.11e-15 < 1e-11`).
   - Verifies all 6 `3x3` IDT matrices (`S-Gamut3` & `S-Gamut3.Cine` -> `ACES2065-1 AP0` & `ACEScg AP1`, across `BRADFORD` and `CAT02` matching ASWF `OpenColorIO-Config-ACES` `urn:ampas:aces:transformId:v2.0` CLF IDs): determinants `0.7335..1.2868 > 0.50`, inversion roundtrip `< 2.3e-16 < 1e-9`, white-point conservation error `<= 6.66e-16 < 1e-4`, `CAT02` vs `BRADFORD` max entry delta `0.004495237`, while failing closed on singular (`det = 0`) and whitepoint-drifted (`1.01`) matrices.
3. **Pillar C — `NP-FZ100` (`7.2 V`) `C-Pin` Telemetry & Stage-B FX6 `14.4 V` Rail Isolation**:
   - Verifies `OEM NP-FZ100` (`7.2 V`, `16.4 Wh`, `2280 mAh`) and decoded 3P packs under Stage-B FX6 overlay when normalized SoC percentage mapping is enabled, plus `>= 51%` firmware-update gating.
   - Verifies safe degradation (`SAFE_DEGRADED_POWER_NO_PCT`, hidden percentage, `fw_update_allowed = False`) when user confirms **OK** on undecoded 3P packs (`STRID 0x0000e24e`) or regulated `C`-pin-absent dummy couplers, while blocking **Cancel**, over-voltage (`12.0 V`) unregulated dummy packs, thermal excursions (`< 0 C` / `> 60 C`), and unmapped FX6 `14.4 V` (`12.0 V` shutdown) comparisons against FX3's `7.2 V` rail (`BLOCKED_FALSE_FX6_14V4_LOW_BATT_SHUTDOWN`).
4. **Pillar D — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration Mutation**:
   - Validates FX3 & FX6 `global.xdb` (`uxa\x07`) read-only, permits `/tmp/` / `ram://` / `memory://`, hard-blocks `BODYDATA.DAT`, `/dev/nflasha15`, `/dev/cnflasha0`, `/dev/mmcblk0rpmb`, and `p2:/setting/Backup.bin`, and proves `emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.

### 4. Owned Files (Strict 7-File Scope)

1. [`reports/2026-11-14-global-sony-wave16-aces-hevc-fz100-unbrick-intel/README.md`](../2026-11-14-global-sony-wave16-aces-hevc-fz100-unbrick-intel/README.md)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/xavc_hevc_intra_aces_idt_and_fz100_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/xavc_hevc_intra_aces_idt_and_fz100_auditor.py)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md)
6. [`outputs/fx3-firmware-lab/tests/test_xavc_hevc_intra_aces_idt_and_fz100.py`](../../outputs/fx3-firmware-lab/tests/test_xavc_hevc_intra_aces_idt_and_fz100.py)
7. [`reports/2026-11-14-phase133-xavc-hevc-aces-fz100-auditor/README.md`](./README.md)

---

## 简体中文技术报告

### 一、 双模式验证实测结果

- **本地 Donor 模式**（`os.O_RDONLY` + `mmap.ACCESS_READ`，共扫描 FX3 `v7.02` 与 FX6 `v6.01` 12 份只读固件资产）：单项审计耗时 **`0.1900 s`**（远低于 `0.35 s` 阈值），`all_checks_passed = True`，`report_sha256 = 7a02fa8820f0c8e50a431e4afc09f909349c0c94e65fd83855ca07a1766bc534`。
- **Clean-Room 合成模式**（`FX3_FX6_FORCE_CLEAN_ROOM=1`）：单项审计耗时 **`0.0019 s`**，`all_checks_passed = True`，`report_sha256 = 9b86361a854c1fcb9e3052b75a1e0bdcba0819c401bc0ae3d6b6f2536a3d235c`。
- **`audit-all --json` 全局集成**：本地 Donor 模式 **`26/26` 全绿**（`9.601 s`）；Clean-Room 模式 **`26/26` 全绿**（`0.560 s`）。
- **单元测试**：第 133 阶段专项 **`40/40`** 通过（Donor `0.727 s` / Clean-Room `0.391 s`）；全套回归 **`793/793`** 双模式全绿（Donor `24.888 s` / Clean-Room `13.603 s`）。
- **仓库卫生门禁**：`scripts/run_all_lab_tests.py --clean-only` 检查 **`ALL GREEN in 0.05s`**（零 `.pyc`、零二进制污染）。

### 二、 四大审计支柱摘要

1. **支柱 A — `BIONZ XR` 硬件编码矩阵（`XAVC HS` vs `XAVC S-I` / `XAVC-I`）**：实证 `FX6 XAVC-I (MXF OP1a)` 与 `FX3 XAVC S-I (MP4)` 在 `libmpr.so` 内共享 `AVC480_*_H422IP` 裸码流内核（`240..600 Mbps` 及 `S&Q 120p 1200 Mbps`），仅封装器在 `libXavcMxf` 与 `libXavcMp4` 分化；强制校验 `SDXC V90`（`600 Mbps`）与 `CFexpress Type A VPG200/VPG400`（`1200 Mbps`）速率门限、`+16 Mbps` Proxy 叠加余量，并精准拦截 FX3 机内 `XAVC HS` 缺失 `25p / 29.97p` 的固件约束。
2. **支柱 B — `ACES 1.3 / 2.0` `S-Log3` 与 `S-Gamut3(.Cine)` `3×3` IDT 矩阵验证**：精算验证 `S-Log3` 关键码值（`95.0 / 420.0 / 597.895257`）、`0.01125 / 171.2102946929` 分段连续性（`3.94e-11`）及往返误差（`7.11e-15`）；同时覆盖 `BRADFORD` 与符合 ASWF `OCIO v2 / CLF` 标准的 `CAT02` 矩阵（`S-Gamut3` / `S-Gamut3.Cine` → `AP0` / `AP1`），全部矩阵满足 `|det| = 0.7335..1.2868 > 0.50`、求逆残差 `< 2.3e-16`、白点 `(1,1,1)` 守恒误差 `<= 6.66e-16 < 1e-4`，并阻断奇异矩阵与白点漂移矩阵。
3. **支柱 C — `NP-FZ100`（`7.2 V`）`C-Pin` 遥测与 Stage-B FX6 `14.4 V` 电源门限隔离**：结合 FX3 `v7.02` 与 FX6 `v6.01` `appFw.so`、`cpapp-b.bin`（`BATT_AUTH_Snd` / `BATT_STATE1_Snd`）及 `.uxc` 告警串（`0x0000e24e` / `0x00006013`），阻断 Stage-B 下未映射的 FX6 `14.4 V`（`12.0 V` 关机门限）误触发 FX3 `7.2 V` 电池 `OFF_BY_BATT_LOW` 关机；对未解码副厂电池/稳压假电池（无 `C-Pin`）在用户确认后允许安全降级供电（隐藏百分比、禁固件升级），对用户取消或 `12 V` 过压非稳压假电池立即硬阻断。
4. **支柱 D — 易失内存暂存与零 `eMMC` / 校准篡改证明**：只读校验双方 `global.xdb`（`uxa\x07`），放行 `/tmp/`、`ram://`、`memory://` 暂存并硬阻断 `BODYDATA.DAT`、`/dev/nflasha15`、`/dev/cnflasha0`、`/dev/mmcblk0rpmb` 与 `Backup.bin`，实证 `emmc_mutation_bytes == 0`、`calibration_mutation_bytes == 0` 且 `persistent_emmc_writes_authorized == False`。
