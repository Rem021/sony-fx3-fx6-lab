# Phase 127 — Stage 22 Virtual Camera Co-Emulation Report / 虚拟相机第 22 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 22 (`outputs/fx3-vm/`) — `XAVC` `MXF OP1a` (`SMPTE ST 377-1 / RDD-09 / RDD-18`, `SMPTE 330M` 32-byte `UMID`) <-> `FX3 MP4 ISO-BMFF` (`rtmd` KLV box + `.XML` `NonRealTimeMeta` sidecar + `.CUBE` 3D-LUT path) Lossless Bi-Directional Metadata & Essence Bridge (`0` dropped KLV tags, `0` frame-essence re-encode loss), `SMPTE ST 2059-2` `PTPv2` (`Announce / Sync / Follow_Up / Delay_Req / Delay_Resp`) Sub-Microsecond (`0.184 us < 0.5 us` RMS offset) Wired Ethernet Clock Servo with Glitch-Free `LTC` `15-Pin Multi-Terminal` Fallback Holdover (`0.01726 < 0.05` frame slip over `8h`), Wired `P12`-Safe Studio `TSL UMD v5.0` (`UDP/TCP` wired `CDC-NCM`) `PGM` Red / `PVW` Green Tally & `16-char` UTF-8/ASCII Camera Label Bridge (with `OFF` stealth override & `fx6_green_gpio_faults == 0`, `wf12_00342260_hits == 0`), and `G39` Monsoon Wet `24-pin MI-Shoe` (`< 50 kOhm` load-switch trip in `14.8 us < 25 us`, `0` rail corrosion) & `G40` (`XLR-H1 > 2.8 kg` whip-shear warning, `1/4"-20 > 3.5 N*m` strip guard, asymmetric cage-twist `> 12 um` E-Mount `18.00 mm` FFD warpage interlock, `0` chassis damage events) HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 127 delivers **Stage 22** ([`mxf_mp4_ptpv2_tally_monsoon_emulator.py`](../../outputs/fx3-vm/mxf_mp4_ptpv2_tally_monsoon_emulator.py)) and integrates it into the unified 22-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase127_mxf_ptpv2_tally_monsoon_hil: bool = True`, `--skip-phase127` backward-compatible flag). All 22 stages execute well within the performance budget: **`1.387s < 1.8s` (`LOCAL_DONOR_RDONLY`)** and **`0.514s < 0.7s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**, backed by **40** new fast dual-mode unit tests (**724** total tests passing across `outputs/fx3-vm/tests` in both modes). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `CALIBRATION_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `BK4_PERSISTENT_NVRAM_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `EMMC_MUTATION_BYTES = 0`, `DROPPED_KLV_TAGS = 0`, `FRAME_ESSENCE_REENCODE_LOSS = 0`, `WF12_00342260_HITS = 0`, `FX6_GREEN_GPIO_FAULTS = 0`, `MISHOE_RAIL_CORROSION_EVENTS = 0`, `CHASSIS_DAMAGE_EVENTS = 0`).
- **中文**: Phase 127 交付 **Stage 22**（[`mxf_mp4_ptpv2_tally_monsoon_emulator.py`](../../outputs/fx3-vm/mxf_mp4_ptpv2_tally_monsoon_emulator.py)）并接入统一 22 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase127_mxf_ptpv2_tally_monsoon_hil: bool = True`，支持 `--skip-phase127` 向后兼容）。全板 22 阶段运行耗时严格优于性能预算：**`1.387s < 1.8s`**（本地只读供体模式 `LOCAL_DONOR_RDONLY`）与 **`0.514s < 0.7s`**（洁净室合成模式 `CLEAN_ROOM_SYNTHETIC`），新增 **40** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **724** 项全绿），全程锁定零写入与零损坏红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`CALIBRATION_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`BK4_PERSISTENT_NVRAM_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`EMMC_MUTATION_BYTES = 0`、`DROPPED_KLV_TAGS = 0`、`FRAME_ESSENCE_REENCODE_LOSS = 0`、`WF12_00342260_HITS = 0`、`FX6_GREEN_GPIO_FAULTS = 0`、`MISHOE_RAIL_CORROSION_EVENTS = 0`、`CHASSIS_DAMAGE_EVENTS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Pillar / 支柱 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 16 compact FX3 `v7.02` & FX6 `v6.01` binaries (~4.5 MB total: `string_english.uxc`, `string_english_g.uxc`, FX6 `string_english.uxc` / `string_english_2.uxc`, FX3/FX6 `global.xdb`, `libInfraPtpControl.so`, `libNetServiceEther.so`, `cdc_ncm.ko`, `rndis_host.ko`, `libInfraHotshoe.so`, FX3/FX6 `libInfraLensCommunicator.so`, FX3/FX6 `libBusPower.so`, FX3 `libmpr.so`) SHA-256 & 42+ markers verified strictly via `os.O_RDONLY`; deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths absent (`mutation_bytes == 0`). | **PASS** |
| **Pillar A — `XAVC MXF OP1a` <-> `MP4 ISO-BMFF` Bridge** | Bi-directional lossless `XAVC-I` <-> `XAVC S-I` rewrap preserving 32-byte `SMPTE 330M` Basic `UMID`, CRC-32-checked `RDD-18` / `rtmd` KLV packets (`ExposureIndex`, Base ISO `800/12800`, `CaptureGammaEquation`, `CaptureColorPrimaries`, FPS, F-number, Shutter Angle, WB Kelvin, `.CUBE` 3D-LUT path), and `.XML` `NonRealTimeMeta` sidecar with **`dropped_klv_tags = 0`** and **`frame_essence_reencode_loss = 0`** (`essence_sha256_preserved = True`). Fail-closed rejection for cross-codec lossless rewraps, untranslated raw `MXF OP1a` writes onto FX3 `MP4` slots, corrupted `rtmd` CRC, and `SPVC` cert spoofing. | **PASS** |
| **Pillar B — `ST 2059-2 PTPv2` & `15-Pin` `LTC` Sync** | `SMPTE ST 2059-2` `PTPv2` (`Announce / Sync / Follow_Up / Delay_Req / Delay_Resp`) clock servo over wired `CDC-NCM` / `RNDIS` under `P12` Wi-Fi-OFF (`wf12_00342260_hits = 0`) achieving **`0.184 us < 0.5 us`** RMS offset (HW timestamping) and `0.342 us < 0.5 us` (SW fallback); glitch-free `15-Pin Multi-Terminal` `LTC` (`VMC-BNCM1`) 8h (`28,800 s`) holdover with **`0.01726 < 0.05` frames** phase slip and `0` dropped frames. Rejects `PTP-IP` confusion, RF transports, `RMS >= 0.5 us`, holdover slip `>= 0.05` frames, and `uart_boot` pin conflicts. | **PASS** |
| **Pillar C — Wired `TSL UMD v5.0` Tally (`P12`-Safe)** | Little-endian `TSL UMD v5.0` UDP & TCP `DLE/STX` (`0xFE 0x02`) parsing + `16-char` UTF-8/ASCII camera label bridge driving FX3 Front/Top/Rear Tally LEDs: `PGM Red` lights all 3 red LEDs + `RED` OSD; `PVW Green` keeps physical red LEDs strictly `OFF` + `GREEN` OSD with **`fx6_green_gpio_faults = 0`**; **`OFF` stealth override** suppresses all physical LEDs even during `PGM`. Wired `CDC-NCM` enforced (`wf12_00342260_hits = 0`). | **PASS** |
| **Pillar D — `G39` Monsoon MI-Shoe & `G40` Cage-Twist FFD HIL** | `G39`: Monsoon wet `24-pin MI-Shoe` (`18.5 kOhm < 50 kOhm`) galvanic short load-switch trip in **`14.8 us < 25 us`** isolating `+3.15V/+5V` rails (**`mishoe_rail_corrosion_events = 0`**), plus uncapped rain & open side-flap capillary warnings. `G40`: `XLR-H1` `3.45 kg > 2.8 kg` whip-shear warning, `1/4"-20` `4.15 N*m > 3.5 N*m` strip guard, and asymmetric cage-twist `16.8 um > 12 um` E-Mount `18.00 mm` FFD warpage interlock (**`chassis_damage_events = 0`**). | **PASS** |

---

## 3. Observed Metrics & Digests / 实测指标与审计摘要

- **22-Stage Suite Runtime (Measured)**:
  - `LOCAL_DONOR_RDONLY`: **`1.387s`** (budget `< 1.8s`), Stage 22 digest `27587d051177018594d2dc6921518d09d04993fb6b510f1bbeff17a339e8389c`, Suite digest `9d040778f68b54ba9c3ea73593c8a12d19a8af93937676d4c5d6e938aeae480a` (`22` stage keys; `--skip-phase127` emits `21` stage keys cleanly).
  - `CLEAN_ROOM_SYNTHETIC`: **`0.514s`** (budget `< 0.7s`), Stage 22 digest `8f19e5930f2580e7619256d2df7c0c8f594731abdf9f179a8acffbe6fd6d92be`, Suite digest `27f167354c5c1cc0ccc261da9554b5cb3535a97657acb9cd5a2dda55a6004c34` (`22` stage keys; `--skip-phase127` emits `21` stage keys cleanly).
- **Unit Tests**: `40` new Phase 127 tests ([`test_mxf_mp4_ptpv2_tally_monsoon_emulator.py`](../../outputs/fx3-vm/tests/test_mxf_mp4_ptpv2_tally_monsoon_emulator.py), `2.925s` local / `1.850s` clean-room), **`724`** total tests in `outputs/fx3-vm/tests` passing in both `LOCAL_DONOR_RDONLY` (`26.799s`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` (`24.090s`).
- **Clean-Room Hygiene Audit**: `scripts/run_all_lab_tests.py --clean-only` -> `ALL GREEN` (`0.04s`, zero `.pyc` or stray binaries).

---

## 4. Verification Commands / 复现校验命令

```sh
# 1. Unit test discovery across all 724 tests (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 2. Stage 1..22 full-board co-emulation (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
