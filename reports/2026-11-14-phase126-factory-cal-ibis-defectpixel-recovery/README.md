# Phase 126 — Per-Unit Factory Calibration (`nvs` / `cnflasha` / `adj`), `IMX510` Defect-Pixel / Dual-Base ISO ADC Offset & 5-Axis `IBIS` Hall-Zero Cross-Serial Donor Poisoning Firewall, & 14-Pillar Recovery Master Suite

> **Date**: `2026-11-14` · **Phase**: `126`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py) (`40` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `FACTORY_CAL_MUTATION_BYTES = 0`, `PRIVATE_KEY_BYTES_READ = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 126 adds Pillar 14 (`verify-factory-cal-guard` & `verify-all-recovery --with-phase126`) to the `fx3_recovery` suite for Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057` / `CXD90058`), achieving **14/14** green pillars in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Read-Only (`O_RDONLY`) FX3/FX6 Calibration/Backup/Sensor/IBIS Donor Inspection** | [`inspect_factory_cal_and_sensor_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py) | Opens local FX3 `v7.02` (`libbackup.so` `14,232` B `6a3c5f60...`, `backup.ko` `144,976` B `8a8d8c94...`, `appFw.so` `79,015,712` B `545c5053...`, and `cpapp-b.bin` `15,980,568` B `c90d00d8...` when requested) and FX6 `v6.01` (`libbackup.so` `14,232` B `e003e2d8...`, `appFw.so` `50,520,424` B `a1c58b69...`, and `cpapp-b.bin` `17,952,816` B `60de0ab5...`) strictly via `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK`; verifies backup/IMX510/DefectAdj/Hall/KDGyro symbol anchors and cross-SKU separation, falling back deterministically to `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent. |
| **Pillar A — Per-Body Factory Calibration (`nvs` / `adj` / `cnflasha`) Triple-Copy Parity & Cross-Serial Firewall** | [`audit_cnflasha_key_vault_operation`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py), [`verify_factory_cal_triple_parity_and_firewall`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py), [`run_factory_cal_6_scenario_firewall`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py) | Enforces fail-closed: `BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT` on `body_serial_hash` / `board_uid_hash` or SKU mismatch against target Tier-0 identity, `BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY` when fewer than 2 independent matching SHA-256 copies across distinct media locations exist for `nvs` / `adj` / `cnflasha`, and `BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION` on any `cnflasha` modification or raw asymmetric private-key extraction (`6/6` scenarios green, `private_key_bytes_read == 0`, `factory_cal_mutation_bytes == 0`). |
| **Pillar B — `IMX510` Defect-Pixel (`Base ISO 800 / 12800` Column-ADC) & 5-Axis `IBIS` / `IMU` Table Verifier** | [`verify_imx510_and_ibis_cal_tables`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py), [`run_sensor_ibis_cal_6_scenario_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py), [`compute_imx510_cal_crc32`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py), [`compute_ibis_imu_cal_crc32`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py) | Validates clean-room structural invariants and `CRC32`: strictly monotonic row-major defect-pixel coordinates within `4264 x 2408` active `IMX510` array, bounded dual-gain `ISO 800 / 12800` dark-current and column-FPN offsets (`±32 LSB`), complete 5-axis `IBIS` (`pitch`, `yaw`, `roll`, `x`, `y`) Hall-sensor zero-centers & 12-bit ADC stroke headroom, and `-10°C..+60°C` `IMU` gyro temperature-bias polynomials (`6/6` scenarios green). |
| **Pillar C — 14-Pillar Recovery Master Suite & 40 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_factory_cal_ibis_defectpixel_and_nvs_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py) | Registers `verify-factory-cal-guard [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126` (`14/14` green in both modes while preserving default `7/7` behavior), exports all Phase 126 symbols in `__all__`, and passes `40` fast dual-mode tests (`>= 14` pillar assertions). |

---

## 2. 中文摘要 (Chinese Summary)

Phase 126 在严格只读、零持久写入安全红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`FACTORY_CAL_MUTATION_BYTES = 0`、`PRIVATE_KEY_BYTES_READ = 0`）下，为 Sony `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057` / `CXD90058`）交付单机身出厂校准防火墙、`IMX510` 与 5 轴 `IBIS`/`IMU` 校准表校验支柱，并接入 **14 支柱**恢复总检门禁：

1. **供体只读（`os.O_RDONLY`）检查与确定性净室回退**：严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 读取本地 FX3 `v7.02`（`libbackup.so` `14,232 B`、`backup.ko` `144,976 B`、`appFw.so` `79,015,712 B`、按需 `cpapp-b.bin` `15,980,568 B`）与 FX6 `v6.01`（`libbackup.so` `14,232 B`、`appFw.so` `50,520,424 B`、按需 `cpapp-b.bin` `17,952,816 B`）符号锚点与跨机型隔离摘要，零原始固件字节或私钥输出；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时确定性回退 `CLEAN_ROOM_SYNTHETIC`。
2. **支柱 A — 单机身出厂校准分区（`nvs` / `adj` / `cnflasha`）三副本校验与跨机身移植防火墙**：fail-closed 拦截跨机身/跨板移植（`BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT`）、不足 2/3 独立媒体一致 SHA-256 副本（`BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY`）及任何修改 `cnflasha` 或提取非对称私钥的请求（`BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION`，`6/6` 场景全绿，`private_key_bytes_read == 0`）。
3. **支柱 B — `IMX510` 坏点表（`Base ISO 800 / 12800` 双增益列 ADC）与 5 轴 `IBIS` / `IMU` 温漂表校验**：校验 `4264 x 2408` 有效像素阵列内行主序单调坏点坐标、双增益 `ISO 800 / 12800` 暗电流及 `±32 LSB` 列 FPN 偏置、5 轴 `IBIS`（`pitch` / `yaw` / `roll` / `x` / `y`）霍尔零点中心与 12 位 ADC 行程余量、`-10°C..+60°C` `IMU` 陀螺仪温漂多项式与 `CRC32`（`6/6` 场景全绿）。
4. **支柱 C — CLI 与 14 支柱恢复总检集成**：注册 `verify-factory-cal-guard` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126`（双模式下均达成 **14/14** 绿色通过，无标志默认仍保持 `7/7` 向后兼容）。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/factory_cal_ibis_defectpixel_and_nvs_verifier.py) *(NEW)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 126 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-factory-cal-guard` & `verify-all-recovery --with-phase126`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 126 14th pillar documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_factory_cal_ibis_defectpixel_and_nvs_verifier.py) *(NEW — 40 fast dual-mode unit tests)*
6. [`reports/2026-11-14-phase126-factory-cal-ibis-defectpixel-recovery/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 126 Unit Tests (`test_factory_cal_ibis_defectpixel_and_nvs_verifier.py`, 40 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **40 tests** in **2.132s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **40 tests** in **1.410s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **597 tests** in **44.309s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **539 tests** in **12.622s** (`OK`, `skipped=9`).
- **CLI Entrypoint Verification (`verify-factory-cal-guard` & `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126`)**:
  - Local Donor `verify-factory-cal-guard --json`: `exit 0` (`status=VERIFIED_FACTORY_CAL_IBIS_AND_NVS_GUARD`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `firewall=6/6`, `sensor_ibis=6/6`, `factory_cal_mutation_bytes=0`, `private_key_bytes_read=0`, `suite_sha256=276ac152fa4ffc15...`).
  - Clean-Room `verify-factory-cal-guard --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_FACTORY_CAL_IBIS_AND_NVS_GUARD`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `firewall=6/6`, `sensor_ibis=6/6`, `factory_cal_mutation_bytes=0`, `private_key_bytes_read=0`, `suite_sha256=6bfa390530255459...`).
  - Local Donor `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=14/14`, `recovery_master_sha256=0630b15eeaff85be...`).
  - Clean-Room `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=14/14`, `recovery_master_sha256=07b2c16ad97e1ac5...`).
- **Clean-Room Lab Master Gate & JSON Regex Hygiene**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `[hygiene] git status --porcelain binary/pyc audit: CLEAN` (`ALL GREEN in 0.11s`).
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\x27"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
