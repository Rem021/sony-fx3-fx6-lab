# Phase 53 — Stage 6 `outputs/fx3-vm/` Hardware-in-the-Loop (HIL) Dynamic Fault-Injection & Thermal / `NP-FZ100` / `XLR-H1` / `C2PA` Co-Simulation Harness

# 第 53 阶段 — Stage 6 `outputs/fx3-vm/` 硬件在环（HIL）动态故障注入与热管理 / `NP-FZ100` / `XLR-H1` / `C2PA` 协同仿真台

**Date / 日期**: `2026-11-14`  
**Owner / 负责代理**: Hydrogen-46 (`antigravity`, isolated child worktree)  
**Target Module / 目标模块**: [`outputs/fx3-vm/fx3_vm_hil_fault_harness.py`](../../outputs/fx3-vm/fx3_vm_hil_fault_harness.py)  
**Suite Orchestrator / 联合编排器**: [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`Stage 6`, `--skip-phase53`)  
**Unit Tests / 单元测试**: [`outputs/fx3-vm/tests/test_fx3_vm_hil_fault_harness.py`](../../outputs/fx3-vm/tests/test_fx3_vm_hil_fault_harness.py) (`28` dual-mode tests; `155` total tests in `outputs/fx3-vm/tests/`)  
**Hard Safety Redlines / 硬性安全红线**: `os.O_RDONLY` only, `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `nvram_persistent_writes == 0`, `physical_device_writes == 0`, `persistent_emmc_writes_authorized == False`.

---

## 1. Executive Summary / 阶段总览

**English**:  
Phase 53 completes the **6-stage** `outputs/fx3-vm/` full-board virtual camera co-emulation stack by adding [`fx3_vm_hil_fault_harness.py`](../../outputs/fx3-vm/fx3_vm_hil_fault_harness.py) as **Stage 6** (`stage6_phase53_hil_fault_harness`). The harness drives 8 deterministic Hardware-in-the-Loop (HIL) dynamic fault-injection and telemetry scenarios across the virtual `CXD90057` AP (`AArch64`), unmodified `CXD90058` Stock-CP (`ARM32 Thumb-2`, `cp_mutation_bytes == 0`), `Soft-GPE0` (`1024x540` HUD + `fx6_px` `0xFFF08018`), `MmioWindowBus` (`0xf0000000..0xf8ffffff`), `virtual-rom-v1` (`/dev/ttyAMA3`), and `IMX510/XAVC` Dual-Slot recording pipeline. Stage 6 is wired backward-compatibly into [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) with `--skip-phase53`, executing all 6 stages end-to-end via `make verify-coemulation` in **~1.1s** (Local Donor `O_RDONLY`) and **~0.3s** (`FX3_FX6_FORCE_CLEAN_ROOM=1`).

**中文摘要**:  
第 53 阶段在 [`fx3_vm_hil_fault_harness.py`](../../outputs/fx3-vm/fx3_vm_hil_fault_harness.py) 落地了 **Stage 6** 确定性硬件在环（HIL）动态故障注入与遥测协同仿真台，并向后兼容地接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（支持 `--skip-phase53`），至此完成 `outputs/fx3-vm/` 全板 6 阶段虚拟相机协同一体化仿真架构。在虚拟 `CXD90057` AP + 只读/不可变 `CXD90058` Stock-CP（`cp_mutation_bytes == 0`）+ `Soft-GPE0` + `IMX510/XAVC` 上完整验证了热爬坡优雅封口、热靴热拔出、电池防误切与压降门禁、`C2PA`/`SPACC`/`cnflasha` 陷阱、无 ND 机身光学钳位、`P12`/`WF-12` 降级隔离及双 CFexpress 接力与 `V30` 拒录。`make verify-coemulation` 全 6 阶段端到端耗时约 **1.1s**（本地只读供体模式）与 **0.3s**（`FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式），全套 `155` 项单测双模式 100% 通过。

---

## 2. 8-Scenario HIL Fault & Telemetry Matrix / 8 场景 HIL 故障与遥测验证矩阵

| ID | Scenario / 场景 | Injected Telemetry & Faults / 注入遥测与故障 | Verified Outcome / 实测验证结果 |
| :--- | :--- | :--- | :--- |
| **`HIL-01`** | Nominal 4K 60p Cine EI + `XLR-H1` + `EXT-LK` | `SoC 54.0°C`, `CFE 48.0°C`, `NP-FZ100 88% (7980mV)`, `USB-PD 9.0V`, `XLR-H1 24-bit 48kHz`, `VMC-BNCM1 EXT-LK` (`680 kOhm`) | `HIL_NOMINAL_OK`, `0` drops, Dual-ISA `0x0416/0x0169/0x0400` + `P11` OK, `cp_mutation_bytes == 0`, `wdt_resets == 0` |
| **`HIL-02`** | `OFF_IN_REC` Thermal Climb (`48°C -> 64°C -> 83°C -> 91°C`) | `OFF_IN_REC` fan mode across `48/64/83/91°C` SoC (`45/69/78/86°C` CFE) | PWM override at `>=62°C` SoC / `>=68°C` CFE, amber HUD warning (`0xFFF08018`) at `>=82°C`, XAVC trailer flush + clean exFAT unmount (`VolumeDirty == 0`, `0x0000`, `0` `.RSV`) + `tmpfs` teardown at `>=90°C` |
| **`HIL-03`** | Live `XLR-H1` MI-Shoe Hot-Detach | `P11` `0x91db059b -> 0x88000002` detach event mid-standby/rec + `libInfraHotshoe.so @ 0x5d90` `E_TMO -> 0x8000` | Instant fallback to `INTERNAL_STEREO`; `IVSHMEM` TX ring clean (`cp_woken_or_crashed == False`), `0` video frame drops |
| **`HIL-04`** | `NP-FZ100` (`7200 mV`) vs `BP-U` (`11500 mV`) + VBUS Droop | Sub-A: `7200 mV` (`84%` InfoLITHIUM, `140 mV` droop); Sub-B: `520 mV` VBUS droop (`> 450 mV`) | `7200 mV` runs normally without false `BP-U` cutoff (`bpu_false_cutoff_blocked == True`); `> 450 mV` droop blocks `H0`/`H1` (`BLOCKED_BY_USBPD_VBUS_DROOP`) |
| **`HIL-05`** | `C2PA RQ_LIC.DAT` & `SPACC 0xf7fc0000 cnflasha` Trap | Write/mount traps on `/dev/cnflasha12`, `RQ_LIC.DAT`, `sigcert.p12`, `psd.bin`, `defdet.bin`, `jiritsu`, `lensfile.bin`, `RPMB` + userland `SPACC` MMIO R/W | Every target & userland `SPACC` MMIO R/W trapped immediately (`spacc_blocked_userland_ops >= 2`, `calibration_mutation_bytes == 0`, `c2pa_rq_lic_preserved == True`) |
| **`HIL-06`** | `P4` Optical Variable-ND Injection | Injects `Auto ND`, `1/4`, `1/16`, `1/64`, `1/128` into ND-absent FX3 | All commands clamped to `ND=Clear` (`mode=4`, `val=(1, 1)`), `0` actuator timeouts, `RTMD 0xE107` verified (`validate_p4_nd_clear_lock` rejects non-Clear) |
| **`HIL-07`** | `P12` `libWlanResource.so 0x70d4` + `/dev/ttyAMA3` Timeout | `UART_DISCONNECTED_TIMEOUT` (`0x0BB9`) + `PATCHRAM_CORRUPT_NACK` (`00342260` / `WF-12`) + `0x70d4` (`00008052c0035fd6`, `rc=0`) | `ALLOWED_DEGRADED`, infinite hang neutralized (`wdt_resets == 0`), `Soft-GPE0` HUD responsive, shooting unaffected |
| **`HIL-08`** | Dual CFexpress Relay + `V30` Speed Reject | `REC_MODE_RELAY_AUTO_SWITCH` with Slot A filling at frame 5/10 + `4K 120p XAVC-I 600Mbps` onto `V30` | Seamless `Slot A -> Slot B` relay at frame `5` with `0` dropped frames & valid `RTMD`; `V30` cleanly emits `SPEED_CLASS_REJECT` (`appfw_crashed == False`) |

---

## 3. Verification Receipts / 实测验证记录

1. **Standalone Phase 53 HIL Harness CLI**:
   - Local Donor (`O_RDONLY`): `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_hil_fault_harness.py --self-test --summary` -> `[PASS] Phase 53 FX3-VM HIL Fault Harness | mode=LOCAL_DONOR_RDONLY scenarios=8/8 cp_mut=0 cal_mut=0 spacc_traps=2 wdt_resets=0` (`~0.79s`).
   - Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `[PASS] Phase 53 FX3-VM HIL Fault Harness | mode=CLEAN_ROOM_SYNTHETIC scenarios=8/8 cp_mut=0 cal_mut=0 spacc_traps=2 wdt_resets=0` (`~0.11s`).
2. **6-Stage Co-Emulation Suite (`make verify-coemulation`)**:
   - Local Donor (`O_RDONLY`): `make verify-coemulation` -> `rc=0`, `all_checks_passed=True`, `~1.1s` (`< 2.5s` target).
   - Clean-Room: `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation` -> `rc=0`, `all_checks_passed=True`, `~0.3s` (`< 2.5s` target).
3. **Full `outputs/fx3-vm/tests/` Dual-Mode Suite (`155` tests)**:
   - Local Donor (`O_RDONLY`): `155` tests passed in `~3.7s` (`< 4.5s` target).
   - Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `155` tests passed in `~2.3s` (`< 4.5s` target).
4. **Hygiene & Safety Audit (`make clean-audit`)**:
   - Zero `.bin`/`.dtb`/`.so`/`.elf`/`.ko`/`.cpio`/`.vfat`/`.pyc` or `__pycache__` artifacts in tracked/untracked workspace tree.
