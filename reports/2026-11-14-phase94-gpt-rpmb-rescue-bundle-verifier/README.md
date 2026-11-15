# Phase 94 — `CXD90057` eMMC Primary/Backup GPT & Sony Sub-Partition Header Healer, RPMB HMAC-SHA256 Monotonic Write-Counter Replay Guard & Offline SD-Rescue Bundle Verifier

> **Date**: `2026-11-14` · **Phase**: `94`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_gpt_rpmb_and_rescue_bundle_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_gpt_rpmb_and_rescue_bundle_verifier.py) (`36` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `RPMB_WRITES_EMITTED = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 94 delivers a read-only, RAM-only pre-rehearsal verification and self-healing suite for `ILME-FX3` (`0x91030080` / `ALCIN_UUD`) `CXD90057` eMMC partition integrity, JEDEC eMMC 5.1 RPMB replay protection, and air-gapped SD rescue kits across both `LOCAL_DONOR_O_RDONLY` (`os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`) and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) modes:

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Donor Read-Only Inspection & Clean-Room Fallback** | [`inspect_donor_partition_metadata_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py) | Opens local FX3 `2.05/nflasha1`, FX3 `nflasha5.img` (`1399` WBI2 sections), FX6 `nflasha5` (`1197` WBI2 sections), and `cxd90057.dtb` strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`; deterministically falls back to `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent. |
| **1. Primary/Backup GPT (`LBA 1` vs `Last LBA`) CRC32 & 15-Partition Geometry Healer (RAM-Only)** | [`build_gpt_pair_bytes`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`verify_gpt_copy`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`heal_gpt_pair_ram_only`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py) | Models the 15-partition `CXD90057` FX3 eMMC layout (`p1_vfat_boot` through `p15_cnflasha_lens_cal`, `FX3_LENS_CAL_START_LBA = 0x0031C000`) with IEEE 802.3 CRC32 (`zlib.crc32`) over the 92-byte `EFI PART` header and 128-entry (`16,384`-byte) partition array, plus Sony Sector 0 (`8246` `2.00`) cross-check. Deterministically reconstructs Primary ← Backup and Backup ← Primary purely in RAM while fail-closed blocking LBA overlaps (`ERR_GPT_PARTITION_OVERLAP`), non-4 KiB alignment (`ERR_GPT_MISALIGNED_4K`), dual corruption (`ERR_GPT_BOTH_COPIES_CORRUPTED`), and cross-SKU FX6 geometry transplants (`ERR_CROSS_SKU_FX6_GPT_TRANSPLANT`, `0x00312000`). |
| **2. JEDEC eMMC 5.1 512-Byte RPMB Monotonic Write-Counter & Replay Sandbox** | [`build_rpmb_frame`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`parse_rpmb_frame`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`RpmbSandboxController`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`prove_stage_b_zero_rpmb_writes`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py) | Models 512-byte JEDEC eMMC 5.1 RPMB frames (`196B` stuff + `32B` HMAC-SHA256 MAC + `284B` signed payload, `16B` nonce, `4B` big-endian `write_counter`, `2B` `address`/`block_count`/`result`/`req_resp`) using public synthetic test key `SYNTHETIC_RPMB_TEST_KEY` only (zero proprietary keys). Enforces fail-closed rejection of stale `write_counter` replay (`RPMB_RESULT_COUNTER_FAILURE = 0x0003`), nonce mismatch (`ERR_RPMB_NONCE_MISMATCH`), MAC forgery (`RPMB_RESULT_AUTH_FAILURE = 0x0002`), and counter exhaustion near `0xFFFFFFFF` (`RPMB_RESULT_COUNTER_EXPIRED = 0x0080`), while proving Stage-B RAM/SD overlay requires zero physical RPMB writes (`rpmb_writes_emitted == 0`). |
| **3. Offline Air-Gapped SD-Rescue Kit Manifest & Two-Man Verifier** | [`build_synthetic_sd_rescue_bundle`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`verify_sd_rescue_bundle`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py), [`TwoManAttestation`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py) | Verifies `FX3_SAFE_STOCK.FLG` sentinel presence, all 15 `p1..p15` SHA-256 manifests (rejecting missing, partial, truncated, or all-`0x00`/`0xFF` artifacts), `GF(256)` P+Q RAID-6 parity & 1-shard erasure healing via [`tier0_backup_parity_and_manifest_guard.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/tier0_backup_parity_and_manifest_guard.py), body hardware serial binding via `build_body_hardware_identity`, air-gapped isolation flags, and independent two-operator digest attestation before Stage-B rehearsal is permitted. |
| **4. CLI & 36 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_gpt_rpmb_and_rescue_bundle_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_gpt_rpmb_and_rescue_bundle_verifier.py) | Registers `verify-gpt-rpmb-bundle [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94` (Pillar 8, preserving default `7/7` compatibility for all existing 331 tests), exports all Phase 94 symbols in `__init__.py`, and validates 36 fast dual-mode unit tests (`< 0.4s`). |

---

## 2. 中文摘要 (Chinese Summary)

Phase 94 在严格只读、纯内存（RAM-only）安全红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`RPMB_WRITES_EMITTED = 0`）下，为 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`）`CXD90057` eMMC 恢复链路补齐三大核心门禁：

1. **供体只读检查与净室回退**：通过 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 只读核验本地 FX3 `2.05/nflasha1`、FX3 `nflasha5.img`（`1399` 节）、FX6 `nflasha5`（`1197` 节）及 `cxd90057.dtb` 元数据；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换至确定性合成净室夹具（`CLEAN_ROOM_SYNTHETIC`）。
2. **支柱 1 — Primary/Backup GPT（LBA 1 vs Last LBA）CRC32 与 15 分区几何重建器**：完整建模 `CXD90057` FX3 15 分区布局（`p1..p15`、`FX3_LENS_CAL_START_LBA = 0x0031C000`），核验 92 字节 `EFI PART` 头与 128 项（16,384 字节）分区数组 IEEE 802.3 CRC32 及 Sony Sector 0（`'8246' '2.00'`）。在纯 RAM 中实现 Primary ← Backup 与 Backup ← Primary 确定性自愈重建，并对 LBA 重叠（`ERR_GPT_PARTITION_OVERLAP`）、非 4 KiB 对齐（`ERR_GPT_MISALIGNED_4K`）、双副本同毁（`ERR_GPT_BOTH_COPIES_CORRUPTED`）与跨机型 FX6 分区移植（`ERR_CROSS_SKU_FX6_GPT_TRANSPLANT`，`0x00312000`）严格 fail-closed 拦截。
3. **支柱 2 — JEDEC eMMC 5.1 512 字节 RPMB 单调写计数器与防重放沙箱**：仅使用公开合成测试密钥（`SYNTHETIC_RPMB_TEST_KEY`，严禁嵌入专有密钥）建模 512 字节 RPMB 帧（196B 填充 + 32B HMAC-SHA256 + 284B 载荷），fail-closed 拦截过期写计数器重放（`0x0003`）、nonce 不匹配、MAC 伪造（`0x0002`）与 `0xFFFFFFFF` 耗尽边缘写溢出（`0x0080`），并证明 Stage-B RAM/SD 覆盖方案零物理 RPMB 写入（`rpmb_writes_emitted == 0`）。
4. **支柱 3 — 离线气隙 SD-Rescue 急救包清单与双人复核门禁**：在允许任何 Stage-B 演练前，核验 `FX3_SAFE_STOCK.FLG` 哨兵、`p1..p15` 全量 SHA-256 清单、`GF(256)` P+Q RAID-6 校验分片与单分片擦除自愈演练、机身硬件绑定摘要及两位不同操作员独立签名摘要（`TwoManAttestation`）。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/gpt_rpmb_and_rescue_bundle_verifier.py) *(NEW)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 94 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-gpt-rpmb-bundle` & `verify-all-recovery --with-phase94`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 94 documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_gpt_rpmb_and_rescue_bundle_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_gpt_rpmb_and_rescue_bundle_verifier.py) *(NEW — 36 fast dual-mode unit tests)*
6. [`reports/2026-11-14-phase94-gpt-rpmb-rescue-bundle-verifier/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 94 Unit Tests (`test_gpt_rpmb_and_rescue_bundle_verifier.py`, 36 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **36 tests** in **0.356s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **36 tests** in **0.315s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **367 tests** (`331` existing + `36` Phase 94) in **32.783s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **309 tests** (`273` existing + `36` Phase 94) in **3.252s** (`OK`, `skipped=8`).
- **CLI Entrypoint Verification (`verify-gpt-rpmb-bundle` & `verify-all-recovery --with-phase94`)**:
  - Local Donor `verify-gpt-rpmb-bundle --json`: `exit 0` (`status=VERIFIED_GPT_RPMB_RESCUE_BUNDLE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `gpt_partitions=15`, `rpmb_writes_emitted=0`, `stage_b_rehearsal_permitted=True`, `suite_sha256=c0ea1a2d48af76a77349dce3acb15a3df83d7ee586859221b28f2f14dcfd07ac`, `bundle_sha256=ecd25d3c6ecdc659cb4d367eb8e0477797e55127a0e7022b940842ecc237b887`).
  - Clean-Room `verify-gpt-rpmb-bundle --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_GPT_RPMB_RESCUE_BUNDLE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `suite_sha256=95ddc68279c89127927cddd41db4e4969b7d064af9e22c0c93e16a8c3de936b8`).
  - Local Donor `verify-all-recovery --with-phase94`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=8/8`, `recovery_master_sha256=0630b15eeaff85be`).
  - Clean-Room `verify-all-recovery --with-phase94 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `recovery_master_sha256=07b2c16ad97e1ac5b4adbda8b3373b32405a2c01f4af7d257afe7937f3e88cde`).
- **Clean-Room Hygiene & Regex Audit**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `ALL GREEN in 0.05s` (`git status --porcelain binary/pyc audit: CLEAN`).
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\x27"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
