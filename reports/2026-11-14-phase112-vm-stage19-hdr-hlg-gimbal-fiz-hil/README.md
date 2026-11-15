# Phase 112 — Stage 19 Virtual Camera Co-Emulation Report / 虚拟相机第 19 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 19 (`outputs/fx3-vm/`) — ITU-R BT.2100 / ARIB STD-B67 HLG (`HLG1/2/3` & `FX6 HLG Live/Natural` + `BT.2020 <-> BT.709` Gamut Matrix) Pipeline, CTA-861.3 HDMI HDR `0x87` InfoFrame Synthesizer, EVF/LCD Gamma Display Assist Zero-Leak Isolation, & G33/G34 Salt-Spray/Haze Duct + Wireless FIZ Hard-Stop / Gimbal CoG HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 112 lands **Stage 19** ([`hdr_hlg_assist_fiz_gimbal_emulator.py`](../../outputs/fx3-vm/hdr_hlg_assist_fiz_gimbal_emulator.py)) and integrates it into the unified 19-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase112_hdr_hlg_fiz_gimbal: bool = True`, `--skip-phase112` backward-compatible flag). All 19 stages pass end-to-end well within the **`< 1.8s` (Local Donor `O_RDONLY`)** and **`< 0.65s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)** runtime budgets, backed by **36** new fast dual-mode unit tests (**604** total tests across `outputs/fx3-vm/tests`). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `DISPLAY_ASSIST_BURN_IN_FRAMES = 0`, `XAVC_CLEAN_FEED_LEAKAGE_EVENTS = 0`, `FIZ_GEAR_STRIP_EVENTS = 0`, `IBIS_COIL_SATURATION_EVENTS = 0`, `DUCT_SALT_HAZE_INGESTION_DAMAGE_EVENTS = 0`).
- **中文**: Phase 112 将 **Stage 19**（[`hdr_hlg_assist_fiz_gimbal_emulator.py`](../../outputs/fx3-vm/hdr_hlg_assist_fiz_gimbal_emulator.py)）接入统一 19 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase112_hdr_hlg_fiz_gimbal: bool = True`，支持 `--skip-phase112` 向后兼容）。全板 19 阶段闭环运行耗时严格满足 **`< 1.8s`**（本地只读供体模式）与 **`< 0.65s`**（洁净室合成模式），新增 **36** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **604** 项全绿），并全程锁定零写入与零损毁红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`DISPLAY_ASSIST_BURN_IN_FRAMES = 0`、`XAVC_CLEAN_FEED_LEAKAGE_EVENTS = 0`、`FIZ_GEAR_STRIP_EVENTS = 0`、`IBIS_COIL_SATURATION_EVENTS = 0`、`DUCT_SALT_HAZE_INGESTION_DAMAGE_EVENTS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Subsystem / 子系统 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 10 compact FX3 `v7.02` & FX6 `v6.01` artifacts (`string_english_f.uxc`, `string_english_g.uxc`, `string_english.uxc`, `string_english_2.uxc`, `dataflowInfraFramework.so`, `libGetLog.so`, `libInfraCCPFStatic.so`, FX3 & FX6 `libfan.so`, `libInfraLensCommunicator.so`) SHA-256 & 30 byte markers verified strictly via `os.O_RDONLY`; deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent. | **PASS** |
| **ARIB STD-B67 HLG1/2/3 & `BT.2020 <-> BT.709` Pipeline** | Exact piecewise ARIB STD-B67 HLG OETF/EOTF across `HLG1` (87% knee -> `826`), `HLG2` (95% knee -> `896`), `HLG3` (100% knee -> `940`), `FX6_HLG_LIVE`, and `FX6_HLG_NATURAL`; exact CIE-1931 `BT.2020 <-> BT.709` 3x3 linear gamut matrices (`D65` row-sum `1.0`, inversion residual `< 1e-12`), `0` LSB 10-bit code-value round-trip error across `[64, 940]` & `[0, 1023]`, and fail-closed rejection of `BT.2020`-in-`BT.709` mismatches (`BLOCKED_MISMATCHED_BT2020_IN_BT709_CONTAINER`). | **PASS** |
| **CTA-861.3 `0x87` InfoFrame & EVF/LCD Assist Isolation** | Synthesizes & validates 30-byte CTA-861.3 HDMI HDR Dynamic Range & Mastering InfoFrames (`type=0x87`, `version=0x01`, `length=26`, `(0x100 - sum) & 0xFF == 0`, `EOTF=0x03` HLG BT.2100 vs `0x00` SDR), rejecting bad checksum/length/header/reserved EOTF frames. `GPE0` EVF/LCD Gamma Display Assist (`S-Log3->709(800%)` and `HLG(BT.2020)->709`) remains isolated to local display pipes with **`0` burn-in frames** and **`0` Clean-HDMI / XAVC leakage events**. | **PASS** |
| **G33 Salt-Spray / Haze / Dust Duct HIL** | Sealed coastal marine & filtered haze paths run safely at nominal `55%` / `2,200 RPM` cooling; unsealed coastal salt-spray, heavy glycol haze (`42 mg/m^3` / `65 min` unpurged), and fine alkali dust (`850 ug/m^3`) engage `GPE0` graceful duct protection alerts (`18%` / `950 RPM` protective throttle, `wdt_resets = 0`, `duct_salt_haze_ingestion_damage_events = 0`). | **PASS** |
| **G34 Wireless FIZ Hard-Stop & 22mm Gimbal CoG HIL** | Calibrated & autotuned setup clears safely (`0` faults); uncalibrated `3.2 N*m` (`> 2.5 N*m`) FIZ hard-stop slam engages `0.85 ms` soft-limit clamp (`1.15 N*m < 1.2 N*m`, `fiz_gear_strip_events = 0`); `22 mm` telescoping-zoom gimbal CoG shift (`64.2 Hz` in `40..90 Hz` resonance band) triggers Stock-CP `0x0400` IBIS voice-coil anti-saturation damping (`210.0 mA <= 450.0 mA`, `ibis_coil_saturation_events = 0`, `cp_mutation_bytes = 0`). | **PASS** |

---

## 3. Verification Commands / 复现校验命令

```sh
# 1. Stage 1..19 full-board co-emulation (Local Donor & Clean-Room)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json

# 2. All outputs/fx3-vm unit tests (604 tests, both modes)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
PYTHONPATH=outputs/fx3-vm FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
