# Phase 96 — Stage 15 Virtual Camera Co-Emulation Report / 虚拟相机第 15 阶段协同仿真报告

**Date / 日期**: `2026-11-14`  
**Scope / 范围**: Stage 15 (`outputs/fx3-vm/`) — Interval Recording (Time-Lapse Electronic-Shutter XAVC Frame Packing & Day-to-Night AE Smoother), Picture Cache (DDR Circular Pre-Rec Ring-Buffer Arbitrator on FX3 2048 MiB DRAM), Wired USB-LAN FTPS Background Transfer (P12 RF-Off Verified), & Sigma Fan Occlusion / Tachometer Stall / Underwater Housing Vacuum HIL.

---

## 1. Executive Summary (EN / 中文摘要)

- **English**: Phase 96 lands **Stage 15** ([`interval_cache_ftp_fan_emulator.py`](../../outputs/fx3-vm/interval_cache_ftp_fan_emulator.py)) and wires it into the unified 15-stage [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) (`include_phase96_interval_cache_ftp_fan=True`, `--skip-phase96` backward-compatible flag). All 15 stages run end-to-end in **`1.28s < 1.5s`** (Local Donor `O_RDONLY`) and **`0.41s < 0.5s`** (`FX3_FX6_FORCE_CLEAN_ROOM=1`), backed by **36** new fast dual-mode unit tests (**460** total tests across `outputs/fx3-vm/tests`). All hard safety redlines remain locked (`CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `NVRAM_PERSISTENT_WRITES = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `WF12_00342260_HITS = 0`, `EMMC_PARTITION_MUTATIONS = 0`).
- **中文**: Phase 96 将 **Stage 15**（[`interval_cache_ftp_fan_emulator.py`](../../outputs/fx3-vm/interval_cache_ftp_fan_emulator.py)）接入统一 15 阶段全板协同仿真编排器 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（默认开启 `include_phase96_interval_cache_ftp_fan=True`，支持 `--skip-phase96` 向后兼容）。全板 15 阶段闭环耗时 **`1.28s < 1.5s`**（本地只读供体模式）与 **`0.41s < 0.5s`**（洁净室合成模式），新增 **36** 项双模式单元测试（`outputs/fx3-vm/tests` 总计 **460** 项全绿），并全程锁定零写入红线（`CP_MUTATION_BYTES = 0`、`WBI_MUTATION_BYTES = 0`、`NVRAM_PERSISTENT_WRITES = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`WF12_00342260_HITS = 0`、`EMMC_PARTITION_MUTATIONS = 0`）。

---

## 2. Subsystems & Verification Results / 子系统与验证结果

| Subsystem / 子系统 | Key Invariants Verified / 核心验证不变量 | Status / 状态 |
|---|---|---|
| **Donor Read-Only Audit (`os.O_RDONLY`)** | 10 compact FX3 v7.02 & FX6 v6.01 artifacts (`libmpr.so`, `cachecontrol.ko`, `libInfraFtpClient.so` x2, `libNetServiceEther.so` x2, `cdc_ncm.ko`, `libWlanResource.so`, `libfan.so` x2) SHA-256 & marker verified; deterministic `CLEAN_ROOM_SYNTHETIC` fallback. | **PASS** |
| **Interval Recording (Time-Lapse)** | Interval `1..60s`, shots `1..9999`, strict Electronic Shutter (`mechanical_curtain_actuations == 0`, zero focal-plane wear), 6-stop sunset damped exponential AE smoothing (`High`/`Mid`/`Low`/`Lock`), single-MXF/MP4 packing + `NonRealTimeMeta` XML `<IntervalRecording>` round-trip. | **PASS** |
| **Picture Cache (DDR Pre-Rec Ring)** | `2s..16s` GOP-aligned circular ring buffer within FX3 safe `384 MiB` volatile pool (`XAVC-I 4K60` 16s clamped to `5.0s` / `357.628 MiB`, `>= 1664 MiB` `appFw`/`GPE0`/kernel headroom), zero dropped GOPs on REC flush, auto-suspension on `S&Q` / `HDMI RAW16` / `Interval Rec`. | **PASS** |
| **Wired USB-LAN FTPS + P12 & eMMC Firewall** | Passive `EPSV`/`PASV` `TLSv1.3` over wired `CDC-NCM` / `RTL8153`, injected link blip + `REST <byte_offset>` resume with SHA-256 parity (`PROXY_ONLY` & `ORIGINAL_AND_PROXY`), `P12` Wi-Fi/BT RF-off (`wf12_00342260_hits == 0`), 100% block on `/dev/mmcblk0p1..p15`, `/dev/nflasha*`, `bk4://`, and `..` path traversal. | **PASS** |
| **Sigma Fan & Underwater Housing HIL** | Hall tachometer rotor stall (`PWM >= 25%`, `RPM == 0`), blocked side exhaust (`< 5 mm`), housing vacuum drop (`> 1.5 mbar/10min`), moisture intrusion, and `>= 90°C` thermal ceiling trigger graceful `.RSV` zero-loss close (`VolumeDirty == 0`) and safe shutdown with `0` eMMC corruptions. | **PASS** |

---

## 3. Verification Commands / 复现校验命令

```sh
# 1. Stage 1..15 full-board co-emulation (Local Donor & Clean-Room)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json

# 2. All outputs/fx3-vm unit tests (460 tests, both modes)
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
PYTHONPATH=outputs/fx3-vm FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests

# 3. Repository clean-room binary/bytecode hygiene check
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
