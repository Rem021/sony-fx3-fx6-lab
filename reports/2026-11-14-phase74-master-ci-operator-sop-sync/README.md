# Phase 74 — Master `Makefile` / Clean-Room CI Gate Upgrade, Bilingual Operator SOP & Master Docs Sync (`Phases 1–70` · `Rounds 1–14` · `Waves 1–6`)

# 第 74 阶段 —— 主 `Makefile` 与无供体洁净室 CI 门禁升级、双语操作/救砖手册新建暨全仓库主文档同步

- **Date / 日期**: `2026-11-14`
- **Task / Agent**: `Phase 74` (`task_2f7b38bf09a6` / `gemini-4-hydrogen` worker in `h69-phase74-master-ci-makefile-operator-sop-sync`)
- **Hard-Locked Safety Redlines**: `persistent_emmc_writes_authorized = False` · `persistent_write_release = False` · `allow_boot_partition_targeting = False` · `allow_destructive_fastboot = False` · `cp_mutation_bytes = 0` · `wbi_mutation_bytes = 0` · `calibration_mutation_bytes = 0`
- **Protected Runtime State**: Live QEMU Console on port `8768` untouched; zero `pkill`/`killall`; Python strictly invoked via `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B`.

---

## 1. Deliverables Summary / 交付成果总览

1. **Root `Makefile` & `.github/workflows/clean-room-ci.yml` Clean-Room Gate Upgrade (`100%` Backward-Compatible)**:
   - Preserved all existing `Makefile` targets (`test`, `test-json`, `clean-audit`, `verify-byof`, `dry-run`, `readiness-packet`, `lifecycle-drill`, `stage-b-lifecycle-drill`, `verify-wireless-guard`, `verify-firmware-lab`, `verify-coemulation`, `verify-stage-b-p10`, `verify-uipc-cp-shim`, etc.).
   - Added 4 non-destructive, dual-mode verification targets:
     - `verify-20-gates`: `PYTHONPATH="outputs/fx3-safety" $(PYTHON) $(PYFLAGS) -m fx3_safety verify-20-gates --dry-run-simulated-backup` (`G01..G20` 20-Gate Master Preflight)
     - `verify-rp2040-fixture`: `PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-rp2040-fixture` (Phase 59 camera-disconnected `RP2040-Zero -DOPEN_DRAIN` bench self-test)
     - `verify-init2-escape`: `PYTHONPATH="outputs/fx3-recovery-adapter" $(PYTHON) $(PYFLAGS) -m fx3_recovery verify-init2-escape` (Phase 66 4-layer `< 1s` `FX3_SAFE_STOCK.FLG` SD escape + `CXD90057` WDT `10,000ms` + `p1` `FAT12/16` swap)
     - `verify-post-trial-audit`: `PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" $(PYTHON) $(PYFLAGS) -m fx6_closure audit-stage-b-post-trial` (Phase 62 `16`-surface `H0 == H2` zero-persistence forensic audit)
   - Wired all 4 new targets into [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml) under `FX3_FX6_FORCE_CLEAN_ROOM=1` (`ubuntu-latest` + `macos-latest`) and updated CI labels for **13 `fx3_firmware_lab` auditors** and **9-Stage `fx3-vm` Co-Emulation**.

2. **Bilingual Field & Bench Operator SOP & Unbrick Runbook ([`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`](../../docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md))**:
   - Authored authoritative side-by-side bilingual (`English` + `简体中文`) field manual covering:
     - **Bench Pre-Plug Checklist (`Camera Disconnected`)**: `RP2040-Zero -DOPEN_DRAIN` `1.8V` `[1.71, 1.89V]` pull-up multimeter checks, `>= 1 MOhm` rail isolation, Raspberry Pi Pico `GP29` ban, `48,000`-baud PIO divider check, and `make verify-rp2040-fixture`.
     - **Cinema Rig Electrical Safety (`Gate G19..G20`)**: D-Tap + copper HDMI Type-A open-negative ground-loop prevention (`CXD90057` ESD array protection), strict `CONNECT_POWER -> CONNECT_HDMI -> CAMERA_ON -> MONITOR_ON` power sequence, HDMI Pin-18 `<= 5.25V/55mA` backfeed guard, E-Mount `LENS_DET` `<= 2.0ms` `V_LENS` crowbar + Stock-CP `0x0400` IBIS park, and `NP-FZ100 >= 15%` (`>= 6.8V`) UPS reserve behind `USB-PD 9V/3A` + read-only `.RSV` salvage.
     - **Media & License Isolation (`Gates G15..G18`)**: Dedicated blank lab CFexpress/SD (`BootChecksum`, `VolumeDirty=0`, zero `XDROOT`/`M4ROOT`/`.RSV` client clips), `P12` Airplane-Mode RF kill coexisting with wired `1 Gbps` `USB-LAN` (`CDC-NCM` `RTL8153`/orig `AX88179` + `PTP-IP 15740`), and `C2PA RQ_LIC.DAT` + `cnflasha` factory calibration zero-write locks.
     - **4-Layer Instant Escape & `Tier-0..Tier-4` Unbrick Decision Tree**: Zero-cable `< 1s` **`FX3_SAFE_STOCK.FLG`** SD/CFexpress escape (`Phase 66`), `REC+MENU` GPIO chord, corrupt CPIO fail-open, volatile `procam_app` crash-loop auto-unmount + `CXD90057` `10,000ms` WDT breaker, `p1` `FAT12/16` atomic swap, and cold-reboot volatile RAM wipe (`H0 == H2`).

3. **Master Documentation Synchronization (`README.md`, `README.en.md`, `README.zh-CN.md`, `docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**:
   - Updated live test badges & breakdown tables across all 7 unified suites: **`1,601`** Local Donor (`skipped=1`, `212.84s`) and **`1,543`** Clean-Room (`skipped=65`, `97.87s`).
   - Synchronized all architecture tables to **Phases 1–70**, **Rounds 1–14** (`18/18` 4-Language `EN/ZH-CN/ZH-TW/JA` × 3-Surface `Big6 Home` / `3-Layer Menu` / `Status Check` real FX3 `7.02` kernel `nop_count=0` pixel-diff closure), **Global Intel Waves 1–6**, **13 unified `fx3_firmware_lab` auditors**, **9-Stage Heterogeneous Co-Emulation (`fx3-vm`)**, **`G01..G20` 20-Gate Master Preflight**, and **Phase 64 Live Port `8768`** capabilities.

---

## 2. Live Verification Receipts / 实测验收记录

### 2.1 Unified Test Suite (`make test` — Both Modes)

| Suite | Local Donor (`make test`) | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`) |
| :--- | :---: | :---: |
| `outputs/fx3-recovery-adapter/tests` | **231** (`skipped=1`, `28.63s`) | **173** (`skipped=8`, `2.24s`) |
| `outputs/fx3-safety/tests` | **292** (`skipped=0`, `0.68s`) | **292** (`skipped=1`, `0.59s`) |
| `outputs/fx6-on-fx3-closure/tests` | **339** (`skipped=0`, `160.92s`) | **339** (`skipped=50`, `81.45s`) |
| `outputs/fx3-vm-trial/tests` | **129** (`skipped=0`, `6.34s`) | **129** (`skipped=1`, `5.07s`) |
| `outputs/fx6-native-presenter-closure/tests` | **61** (`skipped=0`, `1.39s`) | **61** (`skipped=5`, `1.36s`) |
| `outputs/fx3-vm/tests` | **246** (`skipped=0`, `4.31s`) | **246** (`skipped=0`, `2.99s`) |
| `outputs/fx3-firmware-lab/tests` | **303** (`skipped=0`, `9.67s`) | **303** (`skipped=0`, `3.80s`) |
| **Total (`run_all_lab_tests.py`)** | **`1,601`** (`skipped=1`, `212.84s`, `ALL GREEN`) | **`1,543`** (`skipped=65`, `97.87s`, `ALL GREEN`) |
| **BYOF Manifest (`verify-byof`)** | `LOCAL_DONOR_VERIFIED` (`57+57`, `constants=46`, `live=54`) | `CLEAN_ROOM_SCHEMA_VERIFIED` (`57+57`, `constants=46`, `live=0`) |
| **Hygiene (`clean-audit`)** | `CLEAN` (zero untracked binary/`.pyc`) | `CLEAN` (zero untracked binary/`.pyc`) |

### 2.2 New `Makefile` Targets (Dual-Mode Verification — All Exit `0`)

| `Makefile` Target | Local Donor Result (`exit 0`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` Result (`exit 0`) |
| :--- | :--- | :--- |
| `make verify-20-gates` | `VERIFIED_ALL_20_GATES_DRY_RUN_SIMULATED_BACKUP` (`20/20`, `LOCAL_DONOR_O_RDONLY`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False`) | `VERIFIED_ALL_20_GATES_DRY_RUN_SIMULATED_BACKUP` (`20/20`, `CLEAN_ROOM_SYNTHETIC`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False`) |
| `make verify-rp2040-fixture` | `VERIFIED_BENCH_FIXTURE` (`all_passed=True`, `camera_connected=False`, `persistent_emmc_writes_authorized=False`) | `VERIFIED_BENCH_FIXTURE` (`all_passed=True`, `camera_connected=False`, `persistent_emmc_writes_authorized=False`) |
| `make verify-init2-escape` | `VERIFIED_INIT2_ESCAPE_WDT_FAT` (`escape_drills=7/7`, `wdt_scenarios=5/5`, `physical_writes=0`, `persistent_emmc_writes_authorized=False`) | `VERIFIED_INIT2_ESCAPE_WDT_FAT` (`escape_drills=7/7`, `wdt_scenarios=5/5`, `physical_writes=0`, `persistent_emmc_writes_authorized=False`) |
| `make verify-post-trial-audit` | `status=OK` (`scenarios=10/10`, `items=16/16`, `wbi_mut=0`, `cp_mut=0`, `cal_mut=0`, `c2pa_untouched=True`, `exfat_clean=True`, digest `ecc5751ee8805264...`) | `status=OK` (`scenarios=10/10`, `items=16/16`, `wbi_mut=0`, `cp_mut=0`, `cal_mut=0`, `c2pa_untouched=True`, `exfat_clean=True`, digest `1ad69d75caad0a9f...`) |

### 2.3 Markdown Relative Link & Heading Anchor Audit
- Verified all `6` Phase-74 created/modified Markdown documents (`README.md`, `README.en.md`, `README.zh-CN.md`, `docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`, `docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`, `reports/2026-11-14-phase74-master-ci-operator-sop-sync/README.md`) via Python `-B` relative-path & GitHub-heading-slug checker: **`0` broken file links, `0` missing SVG assets, `0` broken heading anchors**.

---

## 3. Owned Files Modified / Created (`8 / 8`)
1. `Makefile`
2. `.github/workflows/clean-room-ci.yml`
3. `README.md`
4. `README.en.md`
5. `README.zh-CN.md`
6. `docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`
7. `docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`
8. `reports/2026-11-14-phase74-master-ci-operator-sop-sync/README.md`
