# Phase 132 — Stage 23 Virtual Camera Co-Emulation Report / 虚拟相机第 23 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 23 (`outputs/fx3-vm/`) — Virtual Production LED-Volume (`Brompton Tessera SX40` / `Megapixel HELIOS`, `1/8`, `1/16`, `960..7680 Hz` PWM) + `IMX510` Rolling-Shutter (`8.7 ms` `4K120p` / `13.2 ms` `4K24p`) Fractional `ECS` Safe-Shutter Solver (`< 0.5%` residual when locked vs `> 18%` banding fault when unlocked), Wired `P12`-Safe `FreeD 0xD1` (`29-byte` UDP packet, `0x40 - sum` mod 256 checksum) E-Mount 12-Pin Focus/Zoom/Iris -> Unreal Engine `LiveLink` Bridge (`60/120 Hz`, `< 1.2 ms` glass-to-engine latency, graceful neutral encoder fallback on unchipped PL lenses), `P12`-Safe Wired `Art-Net 4` (`OpDmx 0x5000` UDP `6454`) & `sACN` (`E1.31` UDP `5568`) DMX Lightning/Flash VSYNC Frame-Boundary Synchronizer (`0` half-frame split bands, `wf12_00342260_hits == 0`), and `G41` (`Tri-Level Genlock / 5V TTL Word-Clock` mis-patched into FX3 `LTC-only` `15-pin Multi-Terminal` hardware isolation in `12.4 us < 20 us`, close-range UV-arc/strobe irradiance guard) & `G42` (Helicopter / Chase-Car `> 1.8 g` `20..200 Hz` resonance auto-parking `IBIS` via Stock-CP `0x0400` into `OFF_MECHANICAL_PARK` + `2000 Hz` `RTMD` Gyroflow capture, `0` end-stop slam or coil thermal runaway events) HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 132 delivers **Stage 23** ([`vp_ledwall_freed_artnet_vib_emulator.py`](../../outputs/fx3-vm/vp_ledwall_freed_artnet_vib_emulator.py)) and integrates it into the unified 23-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase132_vp_ledwall_freed_artnet_hil: bool = True`, `--skip-phase132` backward-compatible flag). All 23 stages execute well within the performance budget: **`1.299s < 1.8s` (`LOCAL_DONOR_RDONLY`)** and **`0.495s < 0.7s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**, backed by **40** new fast dual-mode unit tests (**764** total tests passing across `outputs/fx3-vm/tests` in both modes). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `CALIBRATION_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `BK4_PERSISTENT_NVRAM_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `EMMC_MUTATION_BYTES = 0`, `WF12_00342260_HITS = 0`, `FLASH_SPLIT_BAND_FRAMES = 0`, `CXD90057_PIN_DAMAGE_EVENTS = 0`, `IMX510_SENSOR_BURN_EVENTS = 0`, `IBIS_ENDSTOP_SLAM_EVENTS = 0`, `IBIS_COIL_THERMAL_RUNAWAY_EVENTS = 0`).
- **中文**: Phase 132 交付 **Stage 23**（[`vp_ledwall_freed_artnet_vib_emulator.py`](../../outputs/fx3-vm/vp_ledwall_freed_artnet_vib_emulator.py)）并接入统一 23 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase132_vp_ledwall_freed_artnet_hil: bool = True`，支持 `--skip-phase132` 向后兼容）。全板 23 阶段运行耗时严格优于性能预算：**`1.299s < 1.8s`**（本地只读供体模式 `LOCAL_DONOR_RDONLY`）与 **`0.495s < 0.7s`**（洁净室合成模式 `CLEAN_ROOM_SYNTHETIC`），新增 **40** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **764** 项全绿），全程锁定零写入与零损坏红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`CALIBRATION_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`BK4_PERSISTENT_NVRAM_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`EMMC_MUTATION_BYTES = 0`、`WF12_00342260_HITS = 0`、`FLASH_SPLIT_BAND_FRAMES = 0`、`CXD90057_PIN_DAMAGE_EVENTS = 0`、`IMX510_SENSOR_BURN_EVENTS = 0`、`IBIS_ENDSTOP_SLAM_EVENTS = 0`、`IBIS_COIL_THERMAL_RUNAWAY_EVENTS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Pillar / 支柱 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 16 compact FX3 `v7.02` & FX6 `v6.01` binaries (`~1.67 MB` total: FX3/FX6 `string_english*.uxc`, FX3/FX6 `global.xdb`, FX3/FX6 `libInfraLensCommunicator.so`, `libNetServiceEther.so`, `cdc_ncm.ko`, `rndis_host.ko`, `libInfraMultiIF.so`, FX3/FX6 `libInfraPtpControl.so`, `libptp.so`, `libmpr.so`, `cpapp-b.bin`) SHA-256 & 34 markers verified strictly via `os.O_RDONLY`; deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths absent (`mutation_bytes == 0`). | **PASS** |
| **Pillar A — VP LED-Volume Fractional `ECS` Solver** | Models `IMX510` rolling-shutter readout (`8.7 ms` `4K120p`, `13.2 ms` `4K24p`) against `Brompton Tessera SX40` & `Megapixel HELIOS` scan-multiplexing (`1/8`, `1/16`, `960..7680 Hz` PWM). Integer-locked fractional `ECS` shutters achieve **`0.195%` / `0.264% < 0.5%`** luminance banding residual, while unlocked `125 Hz` or genlock-lost states trigger deterministic **`> 18%`** banding fault detection and fail-closed blocking. | **PASS** |
| **Pillar B — Wired `FreeD 0xD1` -> `Unreal LiveLink`** | Bit-exact 29-byte `FreeD 0xD1` UDP packet encoder/decoder with `(0x40 - sum) mod 256` checksum over wired `CDC-NCM` / `RNDIS` under strict `P12` Wi-Fi-OFF (`wf12_00342260_hits = 0`). Delivers `60/120 Hz` E-Mount 12-pin Focus/Zoom/Iris telemetry at **`0.54 ms` / `0.72 ms < 1.2 ms`** glass-to-engine latency and falls back cleanly to neutral encoder baseline (`0x800000` / `0x0000`) on unchipped PL lenses; blocks RF transports, latency `>= 1.2 ms`, and bad checksums. | **PASS** |
| **Pillar C — `P12`-Safe `Art-Net 4` & `sACN` Lighting Sync** | Encodes/decodes real `Art-Net 4` (`OpDmx 0x5000`, UDP `6454`) & `ANSI E1.31 sACN` (UDP `5568`) DMX flash/lightning packets and aligns cues to `IMX510` VSYNC frame boundaries (`aligned_fire_phase_ms = 0.0`), yielding **`flash_split_band_frames = 0`** and **`wf12_00342260_hits = 0`**. Rejects unsynced mid-frame flash cues causing rolling-shutter split bands and blocks all RF transports. | **PASS** |
| **Pillar D — `G41` Genlock/UV & `G42` Helicopter IBIS HIL** | `G41`: Mis-patched `Tri-Level Genlock` or `5V TTL Word-Clock` on FX3 `LTC-only` `15-pin Multi-Terminal` trips hardware over-voltage/HF isolation in **`12.4 us < 20 us`** (`cxd90057_pin_damage_events = 0`), plus close-range UV-arc/strobe irradiance guard (`imx510_sensor_burn_events = 0`). `G42`: Helicopter/chase-car `> 1.8 g` `20..200 Hz` resonance auto-parks 5-axis IBIS voice coils via Stock-CP `0x0400` into **`OFF_MECHANICAL_PARK`** (`vcm_drive_ma = 0.0`, `cp_mutation_bytes = 0`) + **`2000 Hz` `RTMD`** Gyroflow capture (`ibis_endstop_slam_events = 0`, `ibis_coil_thermal_runaway_events = 0`). | **PASS** |

---

## 3. Observed Metrics & Digests / 实测指标与审计摘要

- **23-Stage Suite Runtime (Measured)**:
  - `LOCAL_DONOR_RDONLY`: **`1.299s`** (budget `< 1.8s`), Stage 23 digest `69cf74a96ca382b7344ceeb283f4682dad8df53fa2e86602e4555441e619920d`, Suite digest `33b0057319f124b7bd53df575e2a5d8fd66079b51f2768159605a58029c7dbf2` (`23` stage keys; `--skip-phase132` emits `22` stage keys cleanly).
  - `CLEAN_ROOM_SYNTHETIC`: **`0.495s`** (budget `< 0.7s`), Stage 23 digest `c471fdab5218fe7029cb78d57ced3c1821f30fe07aa9cecd19adccc539ecdddb`, Suite digest `824014047d0554100c1c73b38c4c147ca15ae73aa71d5c73b158a1aaf4ba9052` (`23` stage keys; `--skip-phase132` emits `22` stage keys cleanly).
- **Unit Tests**: `40` new Phase 132 tests ([`test_vp_ledwall_freed_artnet_vib_emulator.py`](../../outputs/fx3-vm/tests/test_vp_ledwall_freed_artnet_vib_emulator.py), `2.734s` local / `1.770s` clean-room), **`764`** total tests in `outputs/fx3-vm/tests` passing in both `LOCAL_DONOR_RDONLY` (`28.364s`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` (`25.713s`).
- **Clean-Room Hygiene Audit**: `scripts/run_all_lab_tests.py --clean-only` -> `ALL GREEN` (`0.04s`, zero `.pyc` or stray binaries).

---

## 4. Verification Commands / 复现校验命令

```sh
# 1. Unit test discovery across all 764 tests (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 2. Stage 1..23 full-board co-emulation (Local Donor & Clean-Room)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
