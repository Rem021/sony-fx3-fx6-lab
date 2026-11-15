# Phase 91 — Stage 14 Co-Emulation: Gyroflow / Sony Catalyst `2000 Hz` 6-Axis IMU `RTMD` (`0xE4xx`), Anamorphic (`1.33x/1.5x/1.8x/2.0x`) IBIS Arbitrator & `IMX510` Rolling-Shutter Skew HIL

# Phase 91 — Stage 14 协同仿真：Gyroflow / Sony Catalyst `2000 Hz` 6 轴 IMU `RTMD`（`0xE4xx`）、变形宽银幕（`1.33x/1.5x/1.8x/2.0x`）非对称 IBIS 仲裁与 `IMX510` 卷帘快门偏斜 HIL

**Date / 日期**: 2026-11-14  
**Scope / 范围**: `outputs/fx3-vm/` (Stage 14 Co-Emulation Module wired into the 14-Stage Heterogeneous Co-Emulation Suite, 36 Dual-Mode Unit Tests, Zero Hardware / Zero Flash Mutation)  
**Primary Implementation / 核心实现**: [`outputs/fx3-vm/gyroflow_rtmd_anamorphic_emulator.py`](../../outputs/fx3-vm/gyroflow_rtmd_anamorphic_emulator.py)  
**Co-Emulation Suite / 统一编排器**: [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)  
**Unit Tests / 单元测试**: [`outputs/fx3-vm/tests/test_gyroflow_rtmd_anamorphic_emulator.py`](../../outputs/fx3-vm/tests/test_gyroflow_rtmd_anamorphic_emulator.py)

---

## 1. Executive Summary / 核心摘要

**English**:  
Phase 91 delivers **Stage 14** (`stage14_phase91_gyroflow_rtmd_anamorphic`), extending [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) to **14 co-emulated stages** (`--skip-phase91` backward compatibility preserved; full 14-stage runtime `1.12s < 1.5s` local / `0.35s < 0.5s` clean-room) under strict `os.O_RDONLY` donor auditing and deterministic `CLEAN_ROOM_SYNTHETIC` synthesis (`FX3_FX6_FORCE_CLEAN_ROOM=1`):

1. **2000 Hz 6-Axis IMU Ring-Buffer -> Per-Frame SMPTE RDD 18 `RTMD` (`0xE4xx`) Packetizer**:
   - Models the `CXD90057`/`CXD90058` SPI `2000 Hz` 6-axis gyro/accel FIFO across `23.98p` (`~83.4` samples/frame), `24.00p` (`83, 83, 84` alternating), `25.00p` (exact `80`), `29.97p` (`~66.7`), `59.94p` (`~33.4`), and `119.88p` (`~16.7`).
   - Compensates `+250 ppm` SPI crystal skew down to `<= 2.0 us` residual, trips fail-closed on FIFO high-watermark/overflow (`> 512` samples), and enforces `S&Q / VFR` `RTMD` auto-disable (`VFR_SQ_TIMEBASE_DECOUPLED`) so invalid gyro tracks are suppressed cleanly.
   - Verifies Sony E-mount Cinema Line `+X/+Y/+Z` `SO(3)` mounting matrix (`det == +1.0`) and KLV `0xE400..0xE438` round-trip Gyroflow midpoint quaternion integration with **`0.000013 deg < 0.02 deg`** drift.
2. **Anamorphic (`1.33x/1.5x/1.8x/2.0x`) Asymmetric IBIS Gain & FX6-on-FX3 Center-Lock Arbitrator**:
   - Models FX6 (no physical IBIS) vs FX3 `CXD90058` 5-axis IBIS (`0x0400` Off/Standard/Active) across `Off (1.0x)`, `1.3x`/`1.33x`, `1.5x`, `1.8x`, and `2.0x` de-squeeze.
   - Supports safe **`ANAMORPHIC_ASYMMETRIC_YAW_SCALING`** (`yaw_gain = 1 / squeeze_factor`, eliminating horizontal anamorphic wobble) and **`POST_GYROFLOW_IBIS_CENTER_LOCK`** (`0x0400 = Off` center-lock energized, raw 2000 Hz gyro `RTMD` only).
   - Blocks fail-closed any uncompensated spherical `Active` crop warp under anamorphic squeeze (`BLOCKED_ANAMORPHIC_SPHERICAL_ACTIVE_WARP`) or attempt to embed IBIS shift offsets (`0xE438`) during Gyroflow post-stabilization (`BLOCKED_GYROFLOW_DOUBLE_STABILIZATION_SHIFT_HAZARD`).
3. **`IMX510` Rolling-Shutter Readout Skew HIL**:
   - Models real `IMX510` readout durations for Full-Frame 4K (`8.7 ms` / `8700 us`), 4K 120p `1.1x` crop (`4.3 ms` / `4300 us`), and HDMI 16-bit Linear RAW (`8.9 ms` / `8900 us` @ `4264x2408`), encoding exact duration into `RTMD` `0xE400`, verifying Gyroflow row-wise de-skew residual `< 0.01 px`, and proving `0` Stock-CP faults.

**中文摘要**：  
Phase 91 交付 **Stage 14**（`stage14_phase91_gyroflow_rtmd_anamorphic`），将 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 扩展至 **14 阶段全板异构协同仿真**（保留 `--skip-phase91` 向后兼容开关；全板 14 阶段本地耗时 `1.12s < 1.5s`，洁净室耗时 `0.35s < 0.5s`）。在严格保持 `os.O_RDONLY` 供体审计与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室确定性回退的同时，闭环验证了：  
1. `CXD90057`/`CXD90058` SPI `2000 Hz` 6 轴 IMU 环形 FIFO（覆盖 `23.98p` / `24.00p` / `25.00p` / `29.97p` / `59.94p` / `119.88p`、晶振漂移微秒补偿、高水位溢出保护、`S&Q/VFR` 自动禁用 `RTMD` 陀螺轨）、E 卡口 `+X/+Y/+Z` 正交 `SO(3)` 安装矩阵及 SMPTE RDD 18 `0xE4xx` 往返四元数积分精度（漂移 `0.000013° < 0.02°`）；  
2. 变形宽银幕（`1.33x`/`1.5x`/`1.8x`/`2.0x` 及 `1.3x` 别名）非对称偏航缩放（`yaw_gain = 1/S`）与后置 Gyroflow `0x0400 Off` 中心锁双安全模式，失败关闭拦截球面 `Active` 电子畸变与 `0xE438` 双重增稳隐患；  
3. `IMX510` 全画幅 4K（`8.7 ms`）、4K 120p `1.1x` 裁切（`4.3 ms`）与 HDMI 16-bit RAW（`8.9 ms`）卷帘快门读出 HIL 与 `0` Stock-CP 故障注入。

---

## 2. Donor Artifacts Audited (`os.O_RDONLY`) & Clean-Room Parity / 只读供体审计清单

| Artifact Key | Target / Component | Size (B) | Verified Contract Marker | SHA-256 (Prefix) |
|---|---|---|---|---|
| `fx3_dataflow_infra_so` | FX3 `dataflowInfraFramework.so` | `306,496` | `GetData_GyroInfo`, `PIN_YC_PB_RAW_RDD18_INFO` | `5d6a9be3ba35...` |
| `fx6_dataflow_infra_so` | FX6 `dataflowInfraFramework.so` | `306,496` | `GetData_GyroDataTiming`, `PIN_YC_PB_RAW_RDD18_INFO` | `8b8b8a74d2ca...` |
| `fx3_libmpr_so` | FX3 `libmpr.so` | `3,517,008` | `UDAMSetGyroscopeValue`, `ExecuteSerialize_Accelerometer` | `9aeef3b9edb3...` |
| `fx3_libinfraccpf_static_so` | FX3 `libInfraCCPFStatic.so` | `122,160` | `GetRecordInfoVideoRDD18MetaColorPrimaries` | `b991137ce1e8...` |
| `fx3_cam_movie_rec_so` | FX3 `CAMERA_SCN_MOVIE_REC_START.so` | `69,264` | `PID_SET_ANAMO_DESQUEEZE_SCALE`, `PID_SET_FRAME_LOCK_STEADYSHOT` | `a258365bddea...` |
| `fx6_avbb_video_so` | FX6 `AVBB_SCN_START_VIDEO.so` | `268,088` | `MSG_ID_VDF_INPUT_SET_DE_SQUEEZE`, `C_6AXIS_GYRO_STAT_NOISE` | `f3aa48395762...` |
| `fx6_avbb_panelevf_so` | FX6 `AVBB_SCN_START_PANELEVF.so` | `275,968` | `InternalSetDeSqueeze`, `SetDeSqueezeComp`, `C_GYRO_GAIN` | `36d98e83611f...` |
| `fx3_libgetlog_so` | FX3 `libGetLog.so` | `178,832` | `ACC_GYRO_MOVE`, `S_GYRO_REF_GAIN` | `6b977765c055...` |
| `fx6_libgetlog_so` | FX6 `libGetLog.so` | `531,232` | `SteadyShot`, `STEADY_SHOT`, `A_AS_GYRO_CROSSTALK_ADJ` | `2210eef5646d...` |
| `fx3_string_english_f_uxc` | FX3 `string_english_f.uxc` | `373,820` | `De-Squeeze Display`, `1.3x`, `1.5x`, `2.0x`, `SteadyShot` | `7e1f78fc8722...` |

---

## 3. Verification Receipts & Timing / 验证回执与耗时

All verification commands ran with `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B` across both **Local Donor** and **`FX3_FX6_FORCE_CLEAN_ROOM=1`** modes:

| Check | Mode | Result | Runtime | Digest / Count |
|---|---|---|---|---|
| `gyroflow_rtmd_anamorphic_emulator.py --self-test --summary` | `LOCAL_DONOR_RDONLY` | PASS | `< 0.05s` | `c8c950c190cd...` |
| `gyroflow_rtmd_anamorphic_emulator.py --self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | `< 0.05s` | `0631d51d326b...` |
| `fx3_vm_coemulation_suite.py --summary` (All 14 Stages) | `LOCAL_DONOR_RDONLY` | PASS | `1.12s` (`< 1.5s`) | `589b5a5634f7...` |
| `fx3_vm_coemulation_suite.py --summary` (All 14 Stages) | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.35s` (`< 0.5s`) | `9fdac6a9a58d...` |
| `fx3_vm_coemulation_suite.py --skip-phase91 --clean-room --summary` | `CLEAN_ROOM_SYNTHETIC` | PASS | Backward-compat | `b888dbacc221...` |
| `unittest test_gyroflow_rtmd_anamorphic_emulator.py -v` | `LOCAL_DONOR_RDONLY` | PASS | `0.897s` | `36 / 36` tests |
| `unittest test_gyroflow_rtmd_anamorphic_emulator.py -v` | `CLEAN_ROOM_SYNTHETIC` | PASS | `0.899s` | `36 / 36` tests |
| `unittest discover -s outputs/fx3-vm/tests` | `LOCAL_DONOR_RDONLY` | PASS | `8.939s` | `424 / 424` tests |
| `unittest discover -s outputs/fx3-vm/tests` | `CLEAN_ROOM_SYNTHETIC` | PASS | `7.490s` | `424 / 424` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Clean-Room Hygiene | PASS | `0.06s` | Binary/pyc clean |

---

## 4. Safety & Clean-Room Redlines Maintained / 安全与洁净室红线

- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `guest_code_modification_bytes == 0`.
- `nop_count == 0`, `bk4_persistent_nvram_writes == 0`, `nvram_persistent_writes == 0`, `null_gpio_derefs == 0`, `mailbox_stalls == 0`, `physical_device_writes == 0`, `stock_cp_fault_count == 0`.
- `persistent_emmc_writes_authorized == False`, `donor_access_mode == "O_RDONLY"`.
- Live port `8768` untouched; zero `.pyc`, `__pycache__`, `.so`, `.elf`, `.ko`, `.cpio`, or `.bin` files created in workspace.
