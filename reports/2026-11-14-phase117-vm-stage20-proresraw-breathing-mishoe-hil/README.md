# Phase 117 — Stage 20 Virtual Camera Co-Emulation Report / 虚拟相机第 20 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 20 (`outputs/fx3-vm/`) — External Atomos/Blackmagic ProRes RAW / BRAW 16→12-Bit Log Metadata Handshake, E-Mount 12-Pin Focus Breathing FOV Crop (`1.00x..1.08x`) vs Unchipped PL / HDMI RAW `< 0.5 ms` Identity Bypass, MI-Shoe 4-Ch 24-Bit / 48 kHz I2S Master-Clock Fractional-N PLL Lock + Hot-Unplug Holdover, & G35/G36 AOC HDMI Pin-18 `+5V` / CFexpress NVMe Thermal, VPG Write-Floor & Card-Door Emergency FAT Journal HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 117 introduces **Stage 20** ([`hdmi_raw_prores_breathing_mishoe_aoc_emulator.py`](../../outputs/fx3-vm/hdmi_raw_prores_breathing_mishoe_aoc_emulator.py)) and integrates it into the unified 20-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase117_proresraw_breathing_mishoe_hil: bool = True`, `--skip-phase117` backward-compatible flag). All 20 stages complete in **`~1.17s < 1.8s` (Local Donor `O_RDONLY`)** and **`~0.29s < 0.7s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**, backed by **40** new fast dual-mode unit tests (**644** total tests passing across `outputs/fx3-vm/tests`). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `RAW_LUT_BURN_IN_FRAMES = 0`, `PL_BREATHING_STALE_CROP_FRAMES = 0`, `AUDIO_POP_CLICK_FRAMES = 0`, `SY1129_HDMI_FUSE_DAMAGE_EVENTS = 0`, `CFEXPRESS_FAT_CORRUPTION_EVENTS = 0`).
- **中文**: Phase 117 交付 **Stage 20**（[`hdmi_raw_prores_breathing_mishoe_aoc_emulator.py`](../../outputs/fx3-vm/hdmi_raw_prores_breathing_mishoe_aoc_emulator.py)）并接入统一 20 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase117_proresraw_breathing_mishoe_hil: bool = True`，支持 `--skip-phase117` 向后兼容）。全板 20 阶段运行耗时严格优于性能预算：**`~1.17s < 1.8s`**（本地只读供体模式 `LOCAL_DONOR_RDONLY`）与 **`~0.29s < 0.7s`**（洁净室合成模式 `CLEAN_ROOM_SYNTHETIC`），新增 **40** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **644** 项全绿），全程锁定零写入与零损坏红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`RAW_LUT_BURN_IN_FRAMES = 0`、`PL_BREATHING_STALE_CROP_FRAMES = 0`、`AUDIO_POP_CLICK_FRAMES = 0`、`SY1129_HDMI_FUSE_DAMAGE_EVENTS = 0`、`CFEXPRESS_FAT_CORRUPTION_EVENTS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Pillar / 支柱 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 10 compact FX3 `v7.02` & FX6 `v6.01` binaries (`string_english.uxc`, `string_english_g.uxc`, FX6 `string_english.uxc`, `string_english_2.uxc`, `libInfraLensCommunicator.so`, `libInfraHotshoe.so`, `libInfraAdjMedia.so`, `libInfraMediaConfig.so`, `libInfraMediaDetect.so`, `libInfraMediaCommon.so`) SHA-256 & 31 markers verified strictly via `os.O_RDONLY`; deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent. | **PASS** |
| **Pillar A — HDMI 16→12-Bit Log RAW Handshake (`ProRes RAW` / `BRAW`)** | $C^1$-smooth shadow-toe 16→12-bit log compander (`15.0 stops >= 14.5 stops` DR, `2048 ADU` OB-clamp exact round-trip with `0` drift, `[0..512]` shadow injective), 31-byte CTA-861 VSIF (`0x81`, mod-256 checksum `0`), 56-byte `SONYRAW1` metadata (`Base ISO 800 / 12800`, Kelvin/Tint, lens focal/T-stop, `S-Gamut3.Cine` Q13 matrix, CRC-32), unbaked clean stream (`raw_lut_burn_in_frames = 0`) with local `GPE0` display-assist isolation & fail-closed guards. | **PASS** |
| **Pillar B — E-Mount 12-Pin Focus Breathing vs PL/RAW Bypass** | Smooth interpolated FOV crop (`1.00x..1.08x`) across 6 E-Mount 12-pin lens profiles; deterministic `< 0.5 ms` (`0.18–0.22 ms`, `< 1` frame) `1.000x` identity bypass when an unchipped PL adapter, HDMI RAW output, or S&Q 120p is active (`pl_breathing_stale_crop_frames = 0`); fail-closed rejection on forced sensor crop or stale PL coefficient faults. | **PASS** |
| **Pillar C — MI-Shoe 4-Ch 24-Bit / 48 kHz I2S Master-Clock PLL Lock** | Fractional-N PLL lock (`4,608,000 bps`) over `12h` (`43,200 s`) across `23.976p..59.94p` including exact `29.97p` `(1602,1601,1602,1601,1602)` & `59.94p` `(801,801,801,801,800)` 5-frame cadences with **`0.0 < 0.20` samples/hour drift**; `P11` (`0x91db059b -> 0x88000002`) zero-cross ramp to `INTERNAL_CRYSTAL_HOLDOVER` on hot-unplug (`audio_pop_click_frames = 0`, `ivshmem_tx_leaks = 0`). | **PASS** |
| **Pillar D — G35 AOC HDMI +5V & G36 CFexpress NVMe/Door HIL** | `G35`: HDMI Pin-18 `+5V` `> 55 mA` load-switch clamp (`125 mA -> 55.0 mA`) and `> 5.35V` (`5.85V`) reverse-backfeed isolation in **`16.4 us < 40 us`** (`sy1129_hdmi_fuse_damage_events = 0`). `G36`: `CFexpress Type-A` `> 82°C` (`84.5°C`) triggers `PS1_THROTTLED` pre-warning; `4K120p XAVC S-I 600 Mbps` (`93.75 MB/s` guard floor) enforces `VPG200/VPG400` and blocks `V30`; card-door open-during-flush commits emergency FAT journal in `2.8 ms` (`exfat_volume_dirty_bit = 0`, `cfexpress_fat_corruption_events = 0`). | **PASS** |

---

## 3. Observed Metrics & Digests / 实测指标与审计摘要

- **20-Stage Suite Runtime (Measured)**:
  - `LOCAL_DONOR_RDONLY`: `~1.17s` (budget `< 1.8s`), Stage 20 digest `deccba6d5bb6...`, Suite digest `1a6f78f0ede9...`
  - `CLEAN_ROOM_SYNTHETIC`: `~0.29s` (budget `< 0.7s`), Stage 20 digest `fa815b258aa3...`, Suite digest `7cce94d2b843...`
- **Unit Tests**: `40` new Phase 117 tests (`outputs/fx3-vm/tests/test_hdmi_raw_prores_breathing_mishoe_aoc_emulator.py`), **`644`** total tests in `outputs/fx3-vm/tests` passing in both `LOCAL_DONOR_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1`.

---

## 4. Verification Commands / 复现校验命令

```sh
# 1. Unit test discovery across all 644 tests (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 2. Stage 1..20 full-board co-emulation (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
