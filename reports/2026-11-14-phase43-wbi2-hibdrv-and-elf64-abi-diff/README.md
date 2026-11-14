# Phase 43 Report: `WBI2` Hibernation Snapshot Anatomy, `hibdrv` Warm-Boot Mismatch Detector & FX3 `v7.02` vs FX6 `v6.01` ELF64 `.dynsym` ABI Diff

- **Task / Agent**: `Hydrogen-35` (`task_9dc94e3216bd`)
- **Target Package**: [`outputs/fx3-firmware-lab/`](../../outputs/fx3-firmware-lab/)
- **Primary Module**: [`wbi_hibdrv_and_elf_abi_differ.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/wbi_hibdrv_and_elf_abi_differ.py)
- **CLI Entrypoint**: `python3 -B -m fx3_firmware_lab audit-wbi-elf [--clean-room]` and `audit-all` ([`__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py))
- **Unit Test Suite**: [`test_wbi_hibdrv_and_elf_abi.py`](../../outputs/fx3-firmware-lab/tests/test_wbi_hibdrv_and_elf_abi.py) (**27** new tests; **129** total tests in `outputs/fx3-firmware-lab/tests`, passing in both Local Donor `os.O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes)

---

## 1. Executive Summary

| Pillar | Verification Scope | Key Quantitative Result |
| --- | --- | --- |
| **Part 1: `WBI2` Snapshot & `hibdrv` Mismatch Guard** | FX3 `v7.02` (`nflasha5.img`) vs FX6 `v6.01` (`nflasha5`) `88B` `wb_header`, `64B` section descriptors, `0x0F0F0F0F` XOR checksums, `TTBR1_EL1` linear alias, `vmlinux.bin` coupling (`os.O_RDONLY` + `mmap`) | `1,399` FX3 sections (`82` zero-fill, `0x4004a67f0`) vs `1,197` FX6 sections (`54` zero-fill, `0x4004a87f0`); fail-closed `BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH` (`wbi_mutation_bytes = 0` hard-locked) |
| **Part 2: Pure-Python ELF64 `.dynsym` / `DT_NEEDED` Differ** | Direct `mmap`/`struct` parser across FX3 `v7.02` & FX6 `v6.01` core libraries (`appFw.so`, `libuxengine.so`, `libgemini-grm.so`, `libmpr.so`, `libWlanResource.so`, `libInfraBluetoothCore.so`) without subprocesses | `4` shared libraries compared on both bodies + `2` FX6-only libraries gracefully handled on disk (`6/6` in Clean-Room); zero missing closure families |
| **Part 3: `P1..P12+Fan` Closure Cross-Validation** | Maps all 7 divergent Cinema Line feature families (`Big6`, `CineEI`, `Lut3D`, `VariableND`, `SdiOut`, `SmartHandle`, `WlanFatal`) to `P1..P12+Fan` | `7/7` feature families closed (`1,257` `Big6`, `113` `CineEI`, `13` `Lut3D`, `2` `VariableND`, `106` `SdiOut`, `47` `SmartHandle`, `25` `WlanFatal` donor `.dynsym` hits) |

---

## 2. Part 1 — `WBI2` Hibernation Snapshot Anatomy & `hibdrv` Warm-Boot Mismatch Proof

### 2.1 Observed Donor `WBI2` (`p5:/wbi`) & Kernel Build Coupling (`os.O_RDONLY` + `mmap`)

| Metric | FX3 `v7.02` (`nflasha5.img`) | FX6 `v6.01` (`nflasha5`) | Cross-Kernel Delta / Hazard |
| --- | ---: | ---: | ---: |
| **Total Image Size** | `209,112,512 B` | `202,677,056 B` | `-6,435,456 B` |
| **Header Magic / `dVersion`** | `WBI2` / `0x20060224` | `WBI2` / `0x20060224` | Same container ABI, incompatible kernel image |
| **Sections (`64B` each)** | `1,399` (`82` `flag=1` zero-fill) | `1,197` (`54` `flag=1` zero-fill) | `-202` sections |
| **`R_DATA` / `O_DATA` Bytes** | `208,760,832` / `237,330,432` | `202,338,304` / `264,376,320` | `O_DATA` delta `+27,045,888 B` (`+25.79 MiB`) |
| **Section Table SHA-256 prefix** | `7286ddb05a7363c6...` (`100%` XOR ok) | `38d12419b351a09d...` (`100%` XOR ok) | `1,399/1,399` & `1,197/1,197` XOR & `TTBR1_EL1` ok |
| **Physical Address Span** | `[0x400001000, 0x420000000)` (`512 MiB`) | `[0x400001000, 0x424000000)` (`576 MiB`) | `+0x04000000` (`+64 MiB` out-of-bounds on FX3) |
| **`wbimem` Primary Span** | `0x00ba0000` (`12,189,696 B`) | `0x01919000` (`26,316,800 B`) | `+14,127,104 B` (`+13.47 MiB` collision) |
| **`resume_vector` (`vmlinux` match)** | `0x4004a67f0` (`64B` match = `True`) | `0x4004a87f0` (`64B` match = `True`) | `+0x2000 B` misaligned EL1 jump target |
| **Embedded Kernel Banner** | `Sony CE Linux 14.0.1.0` (`dic-build-scm-u20-028`, `Dec 25 2025`) | `Sony CE Linux 14.0.2.0` (`dic-build-scm-u24-002`, `Aug 5 2026`) | Different kernel builds & `swapper_pg_dir` layouts |
| **Trailer (`261,632 B`)** | `RBUF` + `SUBS` present | `RBUF` + `SUBS` present | `p5:/wbi` & `p11:/log` locked (`wbi_mutation_bytes = 0`) |

### 2.2 Fail-Closed `hibdrv` Cross-Kernel Guard (`wbi_mutation_bytes == 0`)

`verify_hibdrv_cross_kernel_rejection()` evaluates cross-kernel `WBI2` warm-boot attempts (`FX6 WBI2` on `FX3` kernel) and returns `BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH` with:
- `rejected_fail_closed = True`
- `wbi_mutation_bytes = 0` (hard-locked)
- `p5_wbi_write_forbidden = True`, `p11_bis_format_forbidden = True`, `warm_mode_2_forbidden = True`
- Explicit EL1 hazards: `KERNEL_BUILD_COUPLED_BANNER_MISMATCH`, `EL1_RESUME_VECTOR_MISMATCH`, `EL1_TTBR1_PAGE_TABLE_DRAM_SPAN_HAZARD`, `O_DATA_RESTORE_FOOTPRINT_MISMATCH`, `SECTION_DESCRIPTOR_COUNT_MISMATCH`, `HIBDRV_WARM_MODE_2_FORBIDDEN_ON_STAGE_A_B`.

---

## 3. Part 2 — Pure-Python ELF64 `.dynsym` / `.dynstr` / `DT_NEEDED` Cross-Body ABI Diff

Parsed directly via `os.O_RDONLY` + `mmap` + `struct` (`~0.012s` across all 10 donor ELF64 shared objects, zero subprocesses):

| Shared Object | On-Disk Status | `DT_NEEDED` Diff (`FX3` vs `FX6`) | Exports (`shared / fx3 / fx6`) | Imports (`shared / fx3 / fx6`) |
| --- | --- | --- | --- | --- |
| `appFw.so` | `BOTH_BODIES_PARSED` | FX3-only: `AdjChkConfig.so`, `libGOConnectionManager.so`, `libInfraSKD.so`, `libNetCommon.so`, `libCertificateManager.so`, `libssl.so.3`; FX6-only: `libSoundTouch.so.1`, `libexpat.so.1`, `libopus.so.0` | `1 / 0 / 0` | `694 / 105 / 215` |
| `libuxengine.so` | `FX6_ONLY_ON_DISK` | FX6 `21` deps (`libandromeda.so`, `libgemini-grm.so`, `libstella.so`, `libux_core.so`, ...) | `0 / 0 / 3,476` | `0 / 0 / 432` |
| `libgemini-grm.so` | `FX6_ONLY_ON_DISK` | FX6 `7` deps (`libpthread.so.0`, `libstdc++.so.6`, ...) | `0 / 0 / 202` | `0 / 0 / 75` |
| `libmpr.so` | `BOTH_BODIES_PARSED` | FX3-only: `libsecvlt.so` (`8` shared deps) | `3,102 / 439 / 1,169` | `281 / 75 / 216` |
| `libWlanResource.so` | `BOTH_BODIES_PARSED` | `9` shared deps (`0` diff) | `92 / 2 / 2` | `90 / 0 / 0` |
| `libInfraBluetoothCore.so` | `BOTH_BODIES_PARSED` | `11` shared deps (`0` diff) | `502 / 7 / 1` | `108 / 0 / 3` |

### `P1..P12+Fan` Closure Cross-Validation Across All 7 Feature Families

| Feature Family | `P1..P12+Fan` Patches | Target Libraries | Donor `.dynsym` Hits | Closure Status |
| --- | --- | --- | ---: | --- |
| `Big6` | `Stage-A`, `Stage-B`, `P10` | `appFw.so`, `libuxengine.so`, `libgemini-grm.so` | `1,257` | `closed=True` |
| `CineEI` | `P8`, `P11`, `BK4-Shadow` | `appFw.so`, `libmpr.so` | `113` | `closed=True` |
| `Lut3D` | `P1`, `P11` | `appFw.so`, `libmpr.so` | `13` | `closed=True` |
| `VariableND` | `P4` | `appFw.so`, `libmpr.so` | `2` | `closed=True` |
| `SdiOut` | `P2`, `P5`, `HDMI-Fallback` | `appFw.so`, `libmpr.so` | `106` | `closed=True` |
| `SmartHandle` | `P3`, `P10`, `P11`, `Fan` | `appFw.so`, `libInfraBluetoothCore.so` | `47` | `closed=True` |
| `WlanFatal` | `P12`, `BK4-Airplane` | `libWlanResource.so`, `libInfraBluetoothCore.so` | `25` | `closed=True` |

---

## 4. Verification Summary

- **Local Donor Mode (`LOCAL_DONOR_VERIFIED`)**: `report_sha256 = e0061c33af0617322c7b166640efccb4dd12ab54e2fca255dd32f105cabbba1d`, `all_checks_passed = True`, `wbi_mutation_bytes = 0`.
- **Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC_VERIFIED`)**: `report_sha256 = abc1b643c084c29b0682e1dc916df1d7450157b995747d5b8545a9d6b62e8b8a`, `all_checks_passed = True`, `wbi_mutation_bytes = 0`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest -v outputs/fx3-firmware-lab/tests/test_wbi_hibdrv_and_elf_abi.py
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest -v outputs/fx3-firmware-lab/tests/test_wbi_hibdrv_and_elf_abi.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-firmware-lab
make verify-firmware-lab
make clean-audit
```
