# Phase 107 — Stage 18 Virtual Camera Co-Emulation Report / 虚拟相机第 18 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 18 (`outputs/fx3-vm/`) — C2PA 2.1 `cnflasha` Key-Vault Zero-Touch Attestation Firewall, E-Mount 12-Pin Lens Shading/CA/Distortion vs Unchipped PL-Mount Identity Arbitrator, Monitor & Control 4-Cam Wired Gigabit USB-LAN (`CDC-NCM`/`RTL8153`) PTP-IP Fleet Sync, & G31/G32 Dummy-Battery OVP Crowbar + PL Cantilever HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 107 lands **Stage 18** ([`c2pa_shading_mcfleet_ovp_emulator.py`](../../outputs/fx3-vm/c2pa_shading_mcfleet_ovp_emulator.py)) and integrates it into the unified 18-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase107_c2pa_shading_mcfleet_ovp: bool = True`, `--skip-phase107` backward-compatible flag). All 18 stages pass end-to-end well within the **`< 1.7s` (Local Donor `O_RDONLY`)** and **`< 0.6s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)** runtime budgets, backed by **36** new fast dual-mode unit tests (**568** total tests across `outputs/fx3-vm/tests`). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `CNFLASHA_MUTATION_BYTES = 0`, `PRIVATE_KEY_READS = 0`, `PRIVATE_KEY_EXPORTS = 0`, `WF12_00342260_HITS = 0`, `CXD90057_PMIC_DAMAGE_EVENTS = 0`, `EMOUNT_FLANGE_DAMAGE_EVENTS = 0`).
- **中文**: Phase 107 将 **Stage 18**（[`c2pa_shading_mcfleet_ovp_emulator.py`](../../outputs/fx3-vm/c2pa_shading_mcfleet_ovp_emulator.py)）接入统一 18 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase107_c2pa_shading_mcfleet_ovp: bool = True`，支持 `--skip-phase107` 向后兼容）。全板 18 阶段闭环运行耗时严格满足 **`< 1.7s`**（本地只读供体模式）与 **`< 0.6s`**（洁净室合成模式），新增 **36** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **568** 项全绿），并全程锁定零写入与零损毁红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`CNFLASHA_MUTATION_BYTES = 0`、`PRIVATE_KEY_READS = 0`、`PRIVATE_KEY_EXPORTS = 0`、`WF12_00342260_HITS = 0`、`CXD90057_PMIC_DAMAGE_EVENTS = 0`、`EMOUNT_FLANGE_DAMAGE_EVENTS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Subsystem / 子系统 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 10 compact FX3 `v7.02` & FX6 `v6.01` artifacts (`libCertificateManager.so` x2, `libInfraCertificate.so`, `libspaccdev.so`, `libInfraLensCommunicator.so` x2, `libNetServiceEther.so` x2, `cdc_ncm.ko`, `libBusPower.so`) SHA-256 & symbol marker verified strictly via `os.O_RDONLY`; deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent. | **PASS** |
| **C2PA 2.1 / `cnflasha` Key-Vault Firewall** | Stage-B clip finalization emits honest `NonRealTimeMeta` XML (`CLEAN_ROOM_RESEARCH_UNATTESTED`, `<HardwareAttestationClaimed>false</HardwareAttestationClaimed>`) with `private_key_reads = 0`, `private_key_exports = 0`, `cnflasha_mutations = 0`. Fail-closed blocks `READ_KEY`/`EXPORT_KEY` (`BLOCKED_C2PA_PRIVATE_KEY_ACCESS`), `cnflasha`/`RPMB`/`SPAcc`/`RQ_LIC.DAT` writes or `rw` mounts (`BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION`), cross-body FX6/forged cert spoofing (`BLOCKED_CROSS_BODY_CERT_SPOOFING`), and attestation forgery (`BLOCKED_C2PA_PROVENANCE_FORGERY`). | **PASS** |
| **E-Mount 12-Pin Shading/CA vs Unchipped PL Arbitrator** | Electronic `SEL2470GM2` (`12` pins) applies radial `cos^4` vignetting (`1.305891x @ r=0.85`), lateral CA, distortion, and breathing polynomials; live hot-swap to unchipped PL-to-E anamorphic prime (`0` pins) resets all tables to `1.0x` identity in **`0.42 ms < 16.6833 ms` (`< 1 frame`)** with `0` stale frames leaked. Corrupt 12-pin UART EEPROM & stale coefficient faults fail closed to `1.0x` identity. | **PASS** |
| **Monitor & Control 4-Cam Wired PTP-IP Fleet Sync** | 4-camera wired Ethernet fleet (`A-Cam` FX6 + `B/C/D-Cam` FX6-on-FX3) over `CDC_NCM_RTL8153` (`1000 Mbps`, `PTP-IP 15740`) streams synchronized `FALSE_COLOR` / `WAVEFORM` / `FOCUS_MAP` packets (`240` packets/tick) and executes Gang REC start/stop (`0.204 ms` start skew / `0.224 ms` stop skew, `<= 64.0 us` PTP skew) with `P12` Wi-Fi/BT RF 100% fenced (`wf12_00342260_hits = 0`); blocks Wi-Fi/BT RF breach and unsupported `RNDIS`/sub-gigabit NICs. | **PASS** |
| **G31/G32 OVP Crowbar & PL Cantilever HIL** | `16.8V` (`G31`) and `26.0V` (`G32`) unregulated dummy-battery surges trip pre-boot OVP crowbar isolation in **`21.59 us`** and **`12.85 us`** (`< 50.0 us`), clamping `CXD90057` PMIC rail peak `<= 8.825V < 9.6V` (`cxd90057_pmic_damage_events = 0`). Unsupported `> 1.8 N*m` (`2.6 N*m`) PL cantilever triggers mount-stress + IBIS interlock (`emount_flange_damage_events = 0`), while 15mm rod support (`0.728 N*m <= 1.8 N*m`) clears safely. | **PASS** |

---

## 3. Verification Commands / 复现校验命令

```sh
# 1. Stage 1..18 full-board co-emulation (Local Donor & Clean-Room)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json

# 2. All outputs/fx3-vm unit tests (568 tests, both modes)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
PYTHONPATH=outputs/fx3-vm FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
