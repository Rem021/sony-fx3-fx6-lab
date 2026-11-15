# Phase 99 — Stage 16 Virtual Camera Co-Emulation Report / 虚拟相机第 16 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 16 (`outputs/fx3-vm/`) — `65^3/17^3 -> 33^3` `.cube` Tetrahedral 3D-LUT DMA Engine, CEA-861-G HDMI AVI InfoFrame + HDMI-to-12G-SDI `SMPTE ST 2082` REC-Trigger Bridge, & Sub-Zero (`-20°C`) NP-FZ100 Li-Ion Arrhenius ESR / High-Altitude (`5,200m`) Thermal Derating HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 99 lands **Stage 16** ([`lut3d_tetrahedral_subzero_sdi_emulator.py`](../../outputs/fx3-vm/lut3d_tetrahedral_subzero_sdi_emulator.py)) and wires it into the unified 16-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase99_lut3d_subzero_sdi=True`, `--skip-phase99` backward-compatible flag). All 16 stages run end-to-end in **`~1.38s < 1.5s`** (Local Donor `O_RDONLY`) and **`~0.47s < 0.5s`** (`FX3_FX6_FORCE_CLEAN_ROOM=1`), backed by **36** new fast dual-mode unit tests (**496** total tests across `outputs/fx3-vm/tests`). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `SDI_TRANSCEIVER_FAULTS = 0`, `LITHIUM_PLATING_EVENTS = 0`, `DROPPED_REC_TRIGGERS = 0`).
- **中文**: Phase 99 将 **Stage 16**（[`lut3d_tetrahedral_subzero_sdi_emulator.py`](../../outputs/fx3-vm/lut3d_tetrahedral_subzero_sdi_emulator.py)）接入统一 16 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase99_lut3d_subzero_sdi=True`，支持 `--skip-phase99` 向后兼容）。全板 16 阶段闭环耗时 **`~1.38s < 1.5s`**（本地只读供体模式）与 **`~0.47s < 0.5s`**（洁净室合成模式），新增 **36** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **496** 项全绿），并全程锁定零写入红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SDI_TRANSCEIVER_FAULTS = 0`、`LITHIUM_PLATING_EVENTS = 0`、`DROPPED_REC_TRIGGERS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Subsystem / 子系统 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 10 compact FX3 v7.02 & FX6 v6.01 artifacts (`libmpr.so`, `libInfraAvbbc.so` x2, `AVBB_SCN_START_PANELEVF.so`, `AVBB_SCN_START_VIDEO.so`, `libBusPower.so`, `libUsbBusPower.so` x2, `libfan.so` x2) SHA-256 & marker verified; deterministic `CLEAN_ROOM_SYNTHETIC` fallback. | **PASS** |
| **User `.cube` Sanitizer & `65^3->33^3` Tetrahedral DMA** | Fail-closed blocking on NaN/Inf, `LUT_1D_SIZE`, inverted `DOMAIN_MIN >= DOMAIN_MAX`, voxel mismatches, oversized payloads, and `..`/`/dev/nflasha`/`bk4://` path traversal; exact 6-subtetrahedra (`T1..T6`) barycentric resampling to `33^3` (`35,937` voxels), `U8` (`107,812 B > 0xbb80`) / `U16` (`215,622 B`) volatile `IVSHMEM` (`0x0165`/`0x0166`) staging with `Main-SLog3` clean / `Proxy-MLUT` / `HDMI-Clean` (`RAW16` forced clean) isolation and `nvram_persistent_writes == 0`. | **PASS** |
| **CEA-861-G HDMI AVI + VSIF -> 12G-SDI ST 2082 Bridge** | Exact 17-byte AVI InfoFrame (`(0x100 - sum) & 0xFF == 0`, `YCbCr 4:2:2 10-bit`, Extended Gamut, S-Log3 TRS-safe legal quantization guard blocking `FULL_RANGE` collision with `0x000..0x003`/`0x3FC..0x3FF`), Sony VSIF `RISING_START`/`FALLING_STOP` transitions, `0` dropped REC triggers, `SMPTE RP 188` LTC/VITC zero-frame-offset lock across `ST 2082` `12G-SDI` / `ST 2081` `6G-SDI` / `ST 292` `1.5G-SDI`, and `0` missing-SDI-BNC faults (`fx3_sdi_bnc_present == False`). | **PASS** |
| **Sub-Zero (`-20°C`) ESR & `5,200m` Altitude Derating HIL** | Arrhenius cold-soak `NP-FZ100` (`R_int = 1.0784 Ω` at `-20°C`) under `8.5W` (`4K120 + Active IBIS`) triggers seamless `USB-PD 9V/3A` (`8.88V` bus) hot-handoff before `6.0V` PMIC UVLO (`pmic_uvlo_trips == 0`, graceful `.RSV` salvage when PD absent) with strict `<= 0°C` charge inhibit (`lithium_plating_events == 0`); ISA `5,200m` derating (`~52.6 kPa`, `0.587x` flow) boosts Sigma fan PWM (`55% -> 95.0%`) and sheds background `FTPS` (`1.4W`), holding `CXD90057` peak `79.16°C < T_warn (82.0°C)`. | **PASS** |

---

## 3. Verification Commands / 复现校验命令

```sh
# 1. Stage 1..16 full-board co-emulation (Local Donor & Clean-Room)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json

# 2. All outputs/fx3-vm unit tests (496 tests, both modes)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
PYTHONPATH=outputs/fx3-vm FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
