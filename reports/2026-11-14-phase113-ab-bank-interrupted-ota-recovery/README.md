# Phase 113 — `CXD90057` / `CXD90058` Dual-Bank A/B Boot-Slot Consistency, Interrupted Official `BODYDATA.DAT` / USB-OTA Power-Loss Forensic Triage & 11-Pillar Recovery Master Suite

> **Date**: `2026-11-14` · **Phase**: `113`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_ab_bank_and_interrupted_ota_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_ab_bank_and_interrupted_ota_verifier.py) (`38` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 113 closes the dual-bank A/B boot-slot consistency and interrupted official Sony firmware-update forensic triage gap for `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, AP `CXD90057` + CP `CXD90058`) and integrates Pillar 11 into the `verify-all-recovery` master readiness suite (`11/11` pillars green in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes):

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Donor Read-Only Inspection & Clean-Room Fallback** | [`inspect_ab_bank_and_ota_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py) | Opens local FX3 `2.05/nflasha1` (`19,377,152` B, `ab2cd537...`, SquashFS `/usr/bin/sdfileinput.elf` `BODYDATA.DAT`, `/usr/bin/UdtrMain.sh` `/setting/updater/uincomp` & `mode*`, `/usr/bin/common.src` `ERROR_UINCOMP=54`, `/usr/kmod/usb_buspwr.ko` `BATTERY_STATE_EXIST`), `udtrbody.squashfs` (`1,253,376` B, `62e86fad...`, `/bin/nor_loader_writer.sh` `cpapp-b.bin`), FX3 `cpapp-b.bin` (`15,980,568` B, `c90d00d8...`), FX6 `cpapp-b.bin` (`17,952,816` B, `60de0ab5...`), and `fx3-7.02-BODYDATA.DAT` bounded `4096`-byte UFU header (`811,876,768` B total, header SHA-256 `fc135914...`, magic `\x89UFU\r\n\x1a\n`) strictly via `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK`; deterministically falls back to `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent. |
| **1. `CXD90057` / `CXD90058` Dual-Bank A/B AP+CP Synchronized Epoch & Torn-Bank Detector** | [`classify_bank_slot_health`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py), [`audit_dual_bank_ap_cp_consistency`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py), [`build_synthetic_dual_bank_snapshot`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py) | Models all 4 deterministic Dual-Bank A/B states (`ACTIVE_VERIFIED`, `PENDING_TRIAL`, `TORN_PARTIAL_WRITE`, `ROLLBACK_FENCED`) across AP (`ap_slot_a`/`ap_slot_b`) and CP (`cpapp-a.bin`/`cpapp-b.bin`) strictly in RAM. Fail-closed rejects split-epoch AP/CP mismatches—specifically AP booting Bank-B `7.02` (epoch `5`) while CP remains torn on half-written Bank-A `2.05` (epoch `1` / corrupt CRC)—which otherwise trigger an AP<->CP IPC protocol deadlock (`ERR_AP_CP_IPC_EPOCH_DEADLOCK`, amber/red LED blink brick), cross-SKU FX6 transplants, and `PENDING_TRIAL` slots lacking an intact fallback bank. |
| **2. Official `BODYDATA.DAT` / Creators'-App OTA Pre-Flight Gate & 6-Scenario Forensic Triage** | [`audit_official_ota_preflight`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py), [`triage_interrupted_ota_brick`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py), [`run_interrupted_ota_6_scenario_triage`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py) | Enforces Sony's firmware-update pre-flight gates (`battery_pct >= 51%`, `0x91030080` FX3 model ID, matching `NTSC`/`PAL` region, UFU magic & CRC, stable transport, consistent dual-bank precheck). Deterministically triages all 6 real-world camera firmware-update & recovery states (`U1_BATTERY_PULLED_DURING_CP_FLASH`, `U2_SD_CARD_READ_CRC_MID_UPDATA`, `U3_USB_CABLE_YANKED_LEGACY_UPDATER`, `U4_CROSS_REGION_NTSC_PAL_MISMATCH`, `U5_STAGE_B_CLEAN_SD_EJECT_ZERO_BRICK`, `U6_INTACT_DUAL_BANK_HEALTHY`), mapping each to exact non-destructive actions (`FX3_SAFE_STOCK.FLG` SD instant boot vs passive `1.8V` UART diagnosis vs Tier-0 read-only dump) and explicitly proving `U5` Stage-B RAM/SD userland overlay has **ZERO flash-interruption brick surface** (`0` eMMC bank transitions, `0` `/setting/updater/*` flags touched). |
| **3. 11-Pillar Recovery Master Suite & 38 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_ab_bank_and_interrupted_ota_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_ab_bank_and_interrupted_ota_verifier.py) | Registers `verify-ab-bank-triage [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113` (`11/11` green in both modes while keeping default `7/7` compatible), exports all Phase 113 symbols (using `AbBankDonorArtifactDigest` to preserve Phase 94 `DonorArtifactDigest`), and passes `38` fast dual-mode tests (`>= 11` pillar assertion for future-phase safety). |

---

## 2. 中文摘要 (Chinese Summary)

Phase 113 在严格只读、纯内存（RAM-only）安全红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`）下，为 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，AP `CXD90057` + CP `CXD90058`）补齐三大恢复取证支柱，并接入 11 支柱总检门禁：

1. **供体只读检查与净室回退**：严格通过 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读校验 FX3 `2.05/nflasha1` SquashFS（`sdfileinput.elf` `BODYDATA.DAT`、`UdtrMain.sh` `/setting/updater/uincomp` 与 `mode*`、`common.src` `ERROR_UINCOMP=54`、`usb_buspwr.ko` `BATTERY_STATE_EXIST`）、`udtrbody.squashfs`（`nor_loader_writer.sh` `cpapp-b.bin`）、FX3/FX6 `cpapp-b.bin` 及 `fx3-7.02-BODYDATA.DAT` 有界 `4096 B` UFU 头；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时确定性回退至 `CLEAN_ROOM_SYNTHETIC`。
2. **支柱 1 — `CXD90057` / `CXD90058` 双槽 A/B（Bank-A / Bank-B）AP+CP 同步 Epoch 与半写入检测器**：在纯 RAM 中精确建模 `ACTIVE_VERIFIED`、`PENDING_TRIAL`、`TORN_PARTIAL_WRITE`、`ROLLBACK_FENCED` 四种双槽状态，fail-closed 拦截 AP 启动 Bank-B `7.02` 而 CP 仍停留在半写入 Bank-A `2.05` / 坏 CRC 引发的 AP<->CP IPC 协议死锁（琥珀/红灯闪烁变砖）、跨 SKU 移植及无完好回退槽的 `PENDING_TRIAL`。
3. **支柱 2 — 官方 `BODYDATA.DAT` / Creators'-App OTA 断电半刷取证分诊**：执行 `>= 51%` 电量门禁与机型/区域/UFU 魔数预检，并对 `U1..U6` 六类典型真实故障状态完成精准无损分诊（SD `FX3_SAFE_STOCK.FLG` 秒级回退、被动 `1.8V` UART 诊断、Tier-0 只读转储），同时显式证明 `U5` Stage-B 易失 RAM/SD 用户态叠加即使在突发拔电池/退卡下也保持**零闪存中断变砖面**（`0` 次 eMMC 槽位切换、`0` 次 `updata` 标志修改）。
4. **支柱 3 — 11 支柱恢复总检集成**：`verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113` 在本地供体与净室双模式下均达到 `11/11` 绿色通过，同时保持无标志默认 `7/7` 行为完全兼容。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/ab_bank_and_interrupted_ota_verifier.py) *(NEW)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 113 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-ab-bank-triage` & `verify-all-recovery --with-phase113`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 113 documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_ab_bank_and_interrupted_ota_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_ab_bank_and_interrupted_ota_verifier.py) *(NEW — 38 fast dual-mode unit tests)*
6. [`reports/2026-11-14-phase113-ab-bank-interrupted-ota-recovery/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 113 Unit Tests (`test_ab_bank_and_interrupted_ota_verifier.py`, 38 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **38 tests** in **1.585s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **38 tests** in **1.121s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **477 tests** in **33.909s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **419 tests** in **6.245s** (`OK`, `skipped=9`).
- **CLI Entrypoint Verification (`verify-ab-bank-triage` & `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113`)**:
  - Local Donor `verify-ab-bank-triage --json`: `exit 0` (`status=VERIFIED_AB_BANK_AND_INTERRUPTED_OTA_GATE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `ota_scenarios=6/6`, `stage_b_u5_zero_brick_verified=True`, `split_deadlock_rejected=True`, `suite_sha256=0b5a548cacca7bee7d051b1c8ae300a42cf69faffcc804c7576c2d389aca8428`).
  - Clean-Room `verify-ab-bank-triage --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_AB_BANK_AND_INTERRUPTED_OTA_GATE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `suite_sha256=90baaa2140edb8c32a877c39657272a002fdd2d53a5b6dda187bbdcf1f1b5f2b`).
  - Local Donor `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=11/11`, `recovery_master_sha256=0630b15eeaff85be`).
  - Clean-Room `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=11/11`, `recovery_master_sha256=07b2c16ad97e1ac5`).
- **Clean-Room Lab Master Gate & JSON Regex Hygiene**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> verified clean-room pass.
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\x27"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
