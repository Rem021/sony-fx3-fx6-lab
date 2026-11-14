# Phase 48 Report: Stage-B (`P1..P12+Fan`, 13/13) SVR4 `cpio newc` Volatile RAM-Overlay Packager v2 & Atomic `init2` Verify-Before-Mount Guard

- **Task / Agent**: `Hydrogen-41` (`task_2bdfeff2e0be`)
- **Target Package**: [`outputs/fx6-on-fx3-closure/`](../../outputs/fx6-on-fx3-closure/)
- **Primary Module**: [`stage_b_ram_overlay_packager.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/stage_b_ram_overlay_packager.py)
- **Public Exports**: [`__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
- **CLI Entrypoint**: `verify-stage-b-ram-overlay [--clean-room] [--lang en|schinese|tchinese|japanese] [--json] [--output PATH]` ([`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py))
- **Unit Test Suite**: [`test_phase48_stage_b_ram_overlay.py`](../../outputs/fx6-on-fx3-closure/tests/test_phase48_stage_b_ram_overlay.py) (**30/30** tests passing in `<1.4s` under both Local Donor `os.O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1`)

---

## 1. Executive Summary

| Deliverable | Implementation & Scope | Verified Quantitative Result |
| --- | --- | --- |
| **1. Deterministic SVR4 `cpio newc` (`070701`) v2 Archive Builder & Auditor** | Pure-Python in-memory builder (`build_stage_b_cpio_newc_archive`) + strict auditor (`parse_and_audit_stage_b_cpio_newc`) enforcing `mtime=0`, `uid=0`, `gid=0`, sorted relative paths, 4-byte alignment, and `TRAILER!!!` | `8` CPIO entries, `39,508 B`..`39,608 B` (`LOCAL_DONOR`) / `39,480 B`..`39,576 B` (`CLEAN_ROOM`), `100%` bit-identical across runs & shuffled entry inputs, `0` repo binary artifacts |
| **2. `13/13` Stage-B (`P1..P12+Fan`) SHA-256 Lock Table & `tmpfs` DDR Budget** | Manifest `etc/fx6_overlay/stage_b_overlay_manifest.json` + contract descriptors (`P5/P6`, `P7`, `P11`) + `P10` (`appFw.so` `e2bc2619...`) + `P12` (`libWlanResource.so` `0x70d4` -> `47fec188...`) + `verify_stage_b_tmpfs_ddr_budget` | `13/13` lock-table entries verified, `100%` SHA-256 rollback parity, volatile `tmpfs` = `9.2135 MiB` (`< 48.00 MiB` cap, `38.79 MiB` headroom inside FX3 `2048 MiB` DDR; `appFw.so` staged via `ro_sd_loop_bind`) |
| **3. `/tmp/bk4_shadow` (`BK4\0` Airplane-Mode + `BK_LANG` 4-Lang Shadow)** | `synthesize_stage_b_bk4_shadow` & `audit_stage_b_bk4_shadow`: `BK4\0` header (`active_byte8=0x00`), Airplane-Mode `0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00`, CRC-16/CCITT-FALSE + 32-bit checksum, `BK_LANG` `0x02cf019c` | All `4` languages verified (`en=0x00`, `japanese=0x01`, `tchinese=0x18`, `schinese=0x19`), distinct reproducible SHA-256 digests, tamper fails closed |
| **4. POSIX `/bin/sh` Stage-B `init2` Atomic Guard & 9-Scenario Sandbox Drill** | `generate_stage_b_init2_guard_script` + `run_stage_b_init2_sandbox_drill`: one-shot `boot_attempts` latch + `/tmp/mod_arm_once` unlink before mount, zero `/etc/ld.so.preload` mutation, `PRODUCT_MODEL == 0x91030080`, `13/13` SHA-256 gate | **9/9** real `/bin/sh` scenarios PASS (`1` clean `8`-mount boot + `8` fail-closed fallbacks with `0` mounts), passes both `verify_failsafe_hook_script` and `audit_ld_so_preload_and_overlay`, `0` eMMC/CP/WBI mutations |

---

## 2. Deliverable 1 — Deterministic `cpio newc`, `13/13` Lock Table & `tmpfs` Budget

### 2.1 SVR4 `cpio newc` (`070701`) Layout & Determinism

`build_stage_b_cpio_newc_archive(...)` normalizes every entry (`mtime=0`, `uid=0`, `gid=0`, sequential `ino`, sorted lexicographically by relative path, 4-byte padded headers & payloads, ending with `TRAILER!!!`) strictly in memory, while `parse_and_audit_stage_b_cpio_newc(...)` rejects bad magic, truncated trailers, unsorted entries, or any non-zero `mtime`/`uid`/`gid`.

Included Stage-B CPIO entries (`8` entries, all verified present):
1. `etc` (dir `0755`)
2. `etc/fx6_overlay` (dir `0755`)
3. `etc/fx6_overlay/bk4_shadow_meta.json`
4. `etc/fx6_overlay/p11_uipc_cp_shim.json`
5. `etc/fx6_overlay/stage_b_init2_guard.sh` (`0755`)
6. `etc/fx6_overlay/stage_b_overlay_manifest.json`
7. `tmp` (dir `0755`)
8. `tmp/bk4_shadow` (`BK4\0` shadow binary payload)

### 2.2 `13/13` Stage-B (`P1..P12+Fan`) SHA-256 Lock Table (`LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED`)

| # | Matrix ID | Stage Relative Path | Size (Bytes) | Staging Tier | Observed SHA-256 Prefix |
| ---: | --- | --- | ---: | --- | --- |
| 1 | `P1_libInfraSetupFile` | `lib/libInfraSetupFile.so` | `202,664` | `tmpfs_overlay` | `69bf006e4efb7bbb...` |
| 2 | `P1_libInfraMediaCommon` | `lib/libInfraMediaCommon.so` | `402,624` | `tmpfs_overlay` | `d9466fa9211dd311...` |
| 3 | `P1_libInfraMediaConfig` | `lib/libInfraMediaConfig.so` | `52,312` | `tmpfs_overlay` | `295a34e274bbb2e6...` |
| 4 | `P3_libInfraAppRemoteBoard` | `lib/libInfraAppRemoteBoard.so` | `10,448` | `tmpfs_overlay` | `2426911919397ab5...` |
| 5 | `Fan_libfan` | `lib/libfan.so` | `31,176` | `tmpfs_overlay` | `456c3da53257c026...` |
| 6 | `P1_P4_P8_P10_appFw` | `lib/appFw.so` | `50,520,424` | `ro_sd_loop_bind` | `e2bc2619845e9614...` |
| 7 | `P9_upm_ko` | `modules/upm.ko` | `453,896` | `tmpfs_overlay` | `5be2aa0b6d6c0a31...` |
| 8 | `P12_libWlanResource` | `lib/libWlanResource.so` | `56,464` | `tmpfs_overlay` | `47fec188cc174faa...` |
| 9 | `P2_opelog_vfat` | `images/opelog.vfat` | `8,388,608` | `tmpfs_overlay` | `48c2123efbfb93da...` |
| 10 | `P5_P6_uipc_rules` | `contracts/p5_p6_uipc_rules.json` | `1,811` | `tmpfs_overlay` | `b4bf5a6616736633...` |
| 11 | `P7_pcidma_bridge` | `contracts/p7_pcidma_bridge.json` | `255` | `tmpfs_overlay` | `bc8b56a984b34be9...` |
| 12 | `P11_uipc_cp_shim` | `contracts/p11_uipc_cp_shim.json` | `354` | `tmpfs_overlay` | `a1f2f884549257d8...` |
| 13 | `P12_bk4_shadow` (`lang=schinese`) | `tmp/bk4_shadow` | `20,824` | `tmpfs_overlay` | `b24bf0bae9e83ff4...` |

### 2.3 Selectable `BK_LANG` (`0x02cf019c`) + Airplane-Mode `/tmp/bk4_shadow` & `tmpfs` Budget

All 4 languages embed cold-boot Airplane-Mode flags (`0x019e0012 = 0x00`, `0x0051000f = 0x00`, `0x01a20002 = 0x00`), `BK4\0` magic at `+0x0C` (`424b3400`), `active_byte8 = 0x00`, and valid CRC-16 + 32-bit checksum while keeping `flash_write_allowed = False`:

| Mode | `--lang` | `0x02cf019c` Byte | CPIO Size / SHA-256 Prefix | `bk4_shadow` SHA-256 Prefix | Volatile `tmpfs` / Headroom (`<48 MiB`) |
| --- | --- | :---: | --- | --- | --- |
| `LOCAL_DONOR` | `en` | `0x00` | `39,508 B` / `d516aadca1505103...` | `76cd5125409c1f67...` | `9.2134 MiB` / `38.7866 MiB` |
| `LOCAL_DONOR` | `schinese` | `0x19` | `39,604 B` / `eb6e76b66b9d2894...` | `b24bf0bae9e83ff4...` | `9.2135 MiB` / `38.7865 MiB` |
| `LOCAL_DONOR` | `tchinese` | `0x18` | `39,608 B` / `ca52924c48718b01...` | `b9b8771e5fe5a317...` | `9.2135 MiB` / `38.7865 MiB` |
| `LOCAL_DONOR` | `japanese` | `0x01` | `39,540 B` / `3873910d5373764e...` | `57ff1d59e5878243...` | `9.2134 MiB` / `38.7866 MiB` |
| `CLEAN_ROOM` | `en` | `0x00` | `39,480 B` / `9b14cbc2b1d740ef...` | `5bbfc169ca603527...` | `8.1143 MiB` / `39.8857 MiB` |
| `CLEAN_ROOM` | `schinese` | `0x19` | `39,576 B` / `d2c1db7d0830cb7c...` | `c541247ee460fe76...` | `8.1144 MiB` / `39.8856 MiB` |
| `CLEAN_ROOM` | `tchinese` | `0x18` | `39,576 B` / `d30b49832e3b411d...` | `1a1a550bce0df7e1...` | `8.1144 MiB` / `39.8856 MiB` |
| `CLEAN_ROOM` | `japanese` | `0x01` | `39,512 B` / `80ea613a42645553...` | `5f96187ca2cefe25...` | `8.1143 MiB` / `39.8857 MiB` |

---

## 3. Deliverable 2 — POSIX `/bin/sh` `init2` Guard & 9-Scenario Sandbox Drill

`generate_stage_b_init2_guard_script(...)` generates a POSIX `/bin/sh` guard script (`stage_b_init2_guard.sh`) verified against both `verify_failsafe_hook_script` and `audit_ld_so_preload_and_overlay`:
1. Unlinks `/tmp/mod_arm_once` and reads `boot_attempts` **strictly before** any bind-mount; if `boot_attempts >= 1`, calls `busybox sync` and immediately enters `STOCK_FX3_FALLBACK`.
2. Checks absence of `/etc/ld.so.preload` (zero global dynamic preload mutation; `LD_LIBRARY_PATH` and `FX6_P11_SHIM_CFG` are scoped exclusively to the forked `appFw` child subshell).
3. Verifies `PRODUCT_MODEL == 0x91030080`, thermal/battery preflight bounds (`PREFLIGHT_OK=1`, `TEMP_MC <= 65000`, `BATT_MV >= 6800`), `< 48 MiB` `tmpfs` headroom, `tmp/bk4_shadow` magic `'BK4\0'` (`424b3400` at `+0x0C`), and all `13/13` SHA-256 digests in `stage_b_overlay_manifest.json` before executing the 8 read-only bind-mounts (`7` `.so` libraries + `/setting/Backup.bin`).

| Scenario ID | Observed Branch | Observed Diag Code | Mounts | `boot_attempts` (`before -> after`) | eMMC / CP / WBI Mut. | Result |
| --- | --- | --- | ---: | :---: | :---: | :---: |
| `S01_CLEAN_STAGE_B_MOUNT` | `ADAPTED_FX6_STAGE_B` | `OK_STAGE_B_MOUNTED` | `8` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S02_FAULT_P12_SHA_MISMATCH` | `STOCK_FX3_FALLBACK` | `ERR_VERIFY_SHA256_MISMATCH:lib/libWlanResource.so` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S03_FAULT_P10_MISSING_BLOB` | `STOCK_FX3_FALLBACK` | `ERR_VERIFY_MISSING:lib/appFw.so` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S04_FAULT_BOOT_ATTEMPTS_PRELATCHED` | `STOCK_FX3_FALLBACK` | `ERR_BOOT_ATTEMPTS_LATCHED` | `0` | `1 -> 1` | `0 / 0 / 0` | **PASS** |
| `S05_FAULT_BK4_MAGIC_CORRUPTION` | `STOCK_FX3_FALLBACK` | `ERR_BK4_MAGIC_INVALID:42414421` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S06_FAULT_PRODUCT_MODEL_TAMPER` | `STOCK_FX3_FALLBACK` | `ERR_PRODUCT_MODEL_MISMATCH:0x91030099` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S07_FAULT_LD_SO_PRELOAD_HAZARD` | `STOCK_FX3_FALLBACK` | `ERR_LD_SO_PRELOAD_HAZARD` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S08_FAULT_THERMAL_BATTERY_REJECT` | `STOCK_FX3_FALLBACK` | `ERR_THERMAL_OR_BATTERY_PREFLIGHT_REJECT` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |
| `S09_FAULT_MISSING_TMPFS_HEADROOM` | `STOCK_FX3_FALLBACK` | `ERR_TMPFS_HEADROOM_EXHAUSTED` | `0` | `0 -> 1` | `0 / 0 / 0` | **PASS** |

---

## 4. Verification Commands & Timings

- `test_phase48_stage_b_ram_overlay.py` (`30` tests):
  - Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **30/30 OK in `1.364s`** (`<5s`)
  - Local Donor (`FX3_FX6_FORCE_CLEAN_ROOM=0`): **30/30 OK in `1.161s`** (`<5s`)
- Hard-locked redlines verified in both modes: `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`, `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`, `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`, `usb_or_camera_operations = 0`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m fx6_closure verify-stage-b-ram-overlay --lang schinese --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m fx6_closure verify-stage-b-ram-overlay --clean-room --lang schinese --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase48_stage_b_ram_overlay.py
FX3_FX6_FORCE_CLEAN_ROOM=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_phase48_stage_b_ram_overlay.py
make clean-audit
```
