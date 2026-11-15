# Phase 89 — Wave-9 Global `Gyroflow`/`RTMD`/VM/Unbrick Intelligence Sync + 17th Unified Firmware-Lab Auditor (`metadata_gyro_catalyst_and_anamorphic_auditor.py`)

**Date**: `2026-11-14`  
**Worker**: `gemini-4-hydrogen` (`task_3b12d8c488b1`, isolated Orca child worktree based on `codex/fx6-system-port-research`)  
**Status**: **ALL GREEN — 17/17 Unified Firmware-Lab Auditors + 437/437 Dual-Mode Unit Tests Passing**

---

## 1. Deliverables Summary

1. **Wave-9 Live Web Intelligence Report**:  
   [`reports/2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md`](../2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md)  
   Bilingual (English + 简体中文) web-grounded synthesis with primary citations covering:
   - Sony `RTMD` (`0xE304` / `0xE43B` / `0xE44B`) & `Gyroflow` (`telemetry-parser` / `sony.rs`) / `Catalyst Browse` `2000 Hz` IMU sample cadence, `IMX510` rolling-shutter readout durations, IBIS Center-Lock (`0x0400`) vs IBIS-aware stabilization, and `1.3x..2.0x` anamorphic stabilization pitfalls.
   - ARM64 IMU / IIO (`Industrial I/O`) sensor virtualization (`VirtIO SCMI` / `CONFIG_IIO_SCMI`, `vhost-user-i2c`/`spi`/`gpio`, `BMI270` `Sensortime` / `ICM-42688-P` `1 us` `TMST_RES` + `FSYNC` `VSYNC` SOF/EOF tagging).
   - Non-invasive `1.8V` RX-only UART boot-stage tapping (host `TX` disconnected/open so BootROM `uart_boot` at `48000 baud` is never inadvertently latched) and safe SD/CFexpress `BODYDATA.DAT` blind recovery (`nflasha1`).

2. **17th Unified Firmware-Lab Auditor (`< 0.5s` Runtime, Dual-Mode)**:  
   [`outputs/fx3-firmware-lab/fx3_firmware_lab/metadata_gyro_catalyst_and_anamorphic_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/metadata_gyro_catalyst_and_anamorphic_auditor.py)
   - **Pillar 1 — `Gyroflow` / `Catalyst Browse` Sony `RTMD` IMU Telemetry Packet Verifier**:
     - Probes `os.O_RDONLY` + `mmap.ACCESS_READ` across FX3 `v7.02` (`libmpr.so` `3,517,008 B`) & FX6 `v6.01` (`libmpr.so` `28,921,824 B`) `mpr::KlvConverter` IMU/readout markers (`_ZN3mpr12KlvConverter11UDAMKeyUnitE`, `UDAMSetGyroscopeValue`, `UDAMSetAccelerometerValue`, `UDAMSetNormalImageControlValue`), plus `.uxc` `SteadyShot` labels.
     - Verifies exact rational `2000 Hz` IMU sample counts per frame (`83/84` at `23.976p`/`24.00p`, `80` at `25.00p`, `66/67` at `29.97p`, `40` at `50.00p`, `33/34` at `59.94p`, `16/17` at `119.88p`), `0` drift over 1,000+ frames (`83,416` samples for 1,000 `23.976p` frames), unit `SO(3)` orientation quaternions & 3x3 rotation matrices (`||q|| = 1.0`, `det(R) = +1.0`), SMPTE RDD 18 KLV packet round-trips (`0x3219`, `0xE43B`, `0xE44B`, `0xE450`, `0xE304`), and deterministic stabilization gating (`IBIS = Off` `0x0400` Center-Lock required for `GYROFLOW_3D_LENS_PROFILE`, blocking `Active` IBIS optical-center shift conflict unless `GYROFLOW_V17_IBIS_METADATA_AWARE` has per-frame offset telemetry).
   - **Pillar 2 — Anamorphic (`1.3x / 1.33x / 1.5x / 1.8x / 2.0x`) 5-Axis IBIS Asymmetric Gain Hazard & Safe Containment**:
     - Audits `appFw.so` (`fx3`: `79,015,712 B`; `fx6`: `50,520,424 B`), `libInfraLensCommunicator.so` (`14,544 B`), and `.uxc` `De-Squeeze` / `Anamorphic` STRIDs (`0x00002504`, `0x000027FE`, `0x000046C7`).
     - Proves FX6 `De-Squeeze` (`1.3x` / `2.0x`) is display-monitoring-only on rigid `IMX510` CMOS (`PRM_is_imager_stabilization_unit_fixed`, `has_physical_ibis == False`), whereas FX3's energized 5-axis IBIS stage suffers $S\times$ horizontal yaw overdrive (`30%..100%` error across `1.3x..2.0x`) if spherical focal length $f$ is applied directly.
     - Enforces `Anamorphic SteadyShot` asymmetric gain ($f_x = f / S$, $f_y = f$, `0.0%` yaw error) OR automatic `IBIS = Off (0x0400 Center-Lock) + 2000 Hz Gyro RTMD` for manual anamorphic lenses.
   - **Pillar 3 — `IMX510` Rolling-Shutter Line-Readout Timing Matrix**:
     - Audits FX6 `libmpr.so` (`MetaConverterImpl::ConvertReadoutDuration`, `muxMxfRtmetaBufferImagerReadoutModeWrite`, `NormalImageControl_EffectivePixelReadoutTime`) and `cpapp-b.bin` (`ImageSensorReadoutMode`, `ReadoutDuration`).
     - Verifies deterministic sensor readout durations (`8.70 ms` full-width `4K 24..60p`, `4.35 ms` `S&Q 4K 120p`, `2.20 ms` `FHD 240p`) and detects skew-shear hazards (`8700 us` erroneously stamped on `4K 120p` -> `BLOCKED_ROLLING_SHUTTER_READOUT_MISMATCH`, `vertical_shear_risk == True`).
   - **Pillar 4 — Stock-CP IMU Factory Bias/Orthogonality Calibration Immutability**:
     - Audits FX3 & FX6 `cpapp-b.bin` (`15,980,568 B` & `17,952,816 B`) and `global.xdb` (`11,664 B` & `1,792 B`) strictly `os.O_RDONLY`, permitting volatile `/tmp`/`ram://`/`memory://` shadow overlays while hard-blocking `/dev/cnflasha*`, `/dev/nflasha*`, `/dev/mmcblk0*`, `p1:`, `p2:/Backup.bin`, `p2:/psd.bin`, and `p6:Jiritsu` (`imu_calibration_mutation_bytes == 0`, `cp_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`).

3. **CLI & Package Integration + 34 Fast Dual-Mode Unit Tests**:
   - Exported public Phase 89 symbols in [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py).
   - Wired `audit-gyroflow-anamorphic [--clean-room] [--json]` and added `metadata_gyro_catalyst_and_anamorphic_audit` as the **17th unified auditor** in `run_audit_all()` inside [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py).
   - Added **34 fast unit tests** in [`outputs/fx3-firmware-lab/tests/test_metadata_gyro_catalyst_and_anamorphic.py`](../../outputs/fx3-firmware-lab/tests/test_metadata_gyro_catalyst_and_anamorphic.py) and updated [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md).

---

## 2. Observed Verification Results (`2026-11-14`)

| Verification Check | Mode | Observed Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=False)` | `LOCAL_DONOR_VERIFIED` (`O_RDONLY`, 14 files) | `all_checks_passed = True`, `0` errors | `0.1979s` (`< 0.5s`) | `sha256: 47fc9ae10e8b70abf0e1f001c0db97cd47fc5d91639c1c961fd50cd9060a86e0` |
| `analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=True)` | `CLEAN_ROOM_SYNTHETIC` (`14` synthetic fixtures) | `all_checks_passed = True`, `0` errors | `0.0028s` (`< 0.5s`) | `sha256: 159f025d037211e8af388baa8101fc0260c9f88d8c8d1ba2bb49a61606c21a23` |
| `test_metadata_gyro_catalyst_and_anamorphic.py` | Local Donor (`os.O_RDONLY`) | `Ran 34 tests ... OK` | `0.942s` | `34/34` passed |
| `test_metadata_gyro_catalyst_and_anamorphic.py` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | `Ran 34 tests ... OK` | `0.542s` | `34/34` passed |
| Full `outputs/fx3-firmware-lab/tests` | Local Donor (`os.O_RDONLY`) | `Ran 437 tests ... OK` | `13.853s` | `437/437` passed |
| Full `outputs/fx3-firmware-lab/tests` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | `Ran 437 tests ... OK` | `6.062s` | `437/437` passed |
| `fx3_firmware_lab audit-all` | Local Donor (`17` auditors) | `all_checks_passed = True` | — | `17/17` passed |
| `fx3_firmware_lab audit-all --clean-room` | Clean-Room (`17` auditors) | `all_checks_passed = True` | — | `17/17` passed |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room / Repo Hygiene | `ALL GREEN` | `0.03s` | `CLEAN` |

### Verified Local Donor Artifact Sizes (`os.O_RDONLY`)
- `fx3_appfw`: `79,015,712 B` | `fx6_appfw`: `50,520,424 B`
- `fx3_libmpr`: `3,517,008 B` | `fx6_libmpr`: `28,921,824 B`
- `fx3_cpapp`: `15,980,568 B` | `fx6_cpapp`: `17,952,816 B`
- `fx3_lens_comm`: `14,544 B` | `fx6_lens_comm`: `14,544 B`
- `fx3_global_xdb`: `11,664 B` | `fx6_global_xdb`: `1,792 B`
- `fx3_str_en`: `165,740 B` | `fx3_str_en_g`: `69,600 B` | `fx6_str_en_1`: `118,208 B` | `fx6_str_en_2`: `118,676 B`

---

## 3. Exclusive File Ownership (7 Files)

1. `outputs/fx3-firmware-lab/fx3_firmware_lab/metadata_gyro_catalyst_and_anamorphic_auditor.py`
2. `outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`
3. `outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`
4. `outputs/fx3-firmware-lab/README.md`
5. `outputs/fx3-firmware-lab/tests/test_metadata_gyro_catalyst_and_anamorphic.py`
6. `reports/2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md`
7. `reports/2026-11-14-phase89-gyroflow-rtmd-anamorphic-ibis-auditor/README.md`
