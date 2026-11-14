# Phase 60 Report — 11th Unified Firmware-Lab Auditor: Cinema Shutter Angle (`5.6°..360.0°`), Extended Clear Scan (`ECS` Anti-LED-Flicker), `S&Q` (`1..240fps`), Tally LEDs & FX3 Mechanical Shutter Curtain Protection

- **Date**: `2026-11-14`
- **Target Package**: `outputs/fx3-firmware-lab/` ([`shutter_ecs_sq_and_tally_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/shutter_ecs_sq_and_tally_auditor.py))
- **Milestone**: **11th Unified Auditor** integrated into [`run_audit_all()`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (`audit-shutter-tally [--clean-room]`)
- **Dual-Mode Verification Status**:
  - **Local Donor (`os.O_RDONLY`)**: `LOCAL_DONOR_VERIFIED`, `all_checks_passed = true`, `10 / 10` donor artifacts verified (`0.322s` standalone), `report_sha256 = 039a891b1f675a786a7ed95ad2fd6e65d12180e4eba56838e6f5a214e101c488`
  - **Forced Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**: `CLEAN_ROOM_SYNTHETIC_VERIFIED`, `all_checks_passed = true`, `10 / 10` synthetic fixtures verified, `report_sha256 = 5d5f835ee07422fc1712027b0447fa80b6a17ebddcfeba27c24014f1300729c4`
  - **Unit Tests**: `241 / 241` total suite tests pass (`3.447s` Clean-Room, `9.562s` Local Donor across all 9 test files; `28` new Phase 60 tests in [`test_shutter_ecs_sq_and_tally.py`](../../outputs/fx3-firmware-lab/tests/test_shutter_ecs_sq_and_tally.py) running in `0.643s`)

---

## 1. Strictly `os.O_RDONLY` Donor Artifact Inventory (10 Binaries & String Packs)

All local donor reads open files strictly via `os.O_RDONLY` (`mmap.ACCESS_READ` ELF64 `.rodata`/`.dynstr` section-scoped single-pass scanning without copying or mutating proprietary files), and fall back deterministically to synthetic clean-room fixtures when `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or absent donor trees are detected.

| Key | Body / FW | Artifact | Local Donor Size (B) | Role in Phase 60 Audit |
|---|---|---|---:|---|
| `fx3_appfw` | FX3 `v7.02` | `appFw.so` | `79,015,712` | Mechanical shutter PIDs (`PID_SET_SHUTTER_TYPE`, Anti-Dust), 19 discrete angles (`5.6°..360.0°` + `2F..64F`), `S&Q` (`120FPS`/`240FPS`), `REC_LAMP_*` |
| `fx6_appfw` | FX6 `v6.01` | `appFw.so` | `50,520,424` | `0` mechanical shutter PIDs, `SHUTTER_ANGLE_CONTINUOUS`, `ECS_FREQUENCY`, `SQ_FRAME_RATE_1FPS..240FPS`, `FRONT/REAR/TALLY_CONTROL/BRIGHTNESS` |
| `fx3_libmpr` | FX3 `v7.02` | `libmpr.so` | `3,517,008` | `AudioRecStart`, `AudioRecStop`, `AudioFormat`, `AVC_Proxy_1920_1080_HP`, `HEVC_Proxy_1920_1080_M10P` |
| `fx6_libmpr` | FX6 `v6.01` | `libmpr.so` | `28,921,824` | Shared audio/proxy + `muxMxfRtmetaBufferShutterSpeedAngleWrite`, `muxMxfRtmetaBufferShutterSpeedTimeWrite`, `muxMxfRtBimConvertSubShutterTime` |
| `fx3_cpapp` | FX3 `v7.02` | `cpapp-b.bin` | `15,980,568` | Stock-CP (`cp_mutation_bytes == 0`), `SET_SHUTTER_TYPE`, `SET_FRONT_ESHUTTER`, `EC_ElecShutter_Main`, `SLOW_AND_QUICK_MODE`, `MSG_ID_INFRABB_SYS_SET_CA_TALLY` |
| `fx6_cpapp` | FX6 `v6.01` | `cpapp-b.bin` | `17,952,816` | `0` mechanical shutter CP handlers, shared `EC_ElecShutter_Main`, `ShutterSpeedAngle`, `ShutterSpeedAngleMeta`, `ShutterSpeedTime`, `MSG_ID_INFRABB_SYS_SET_CA_TALLY` |
| `fx3_str_en` | FX3 `v7.02` | `string_english.uxc` (`ns=39`) | `165,740` | `0x0000e368` (`Slow Shutter`), `0x0000e72e` (`Audio Recording`) |
| `fx3_str_en_g` | FX3 `v7.02` | `string_english_g.uxc` (`ns=3`) | `69,600` | `0x00006099` (`S&Q Motion`), `0x000060c6` (`Movie/S&Q Motion`), `0x00006431` (`Shutter`) |
| `fx6_str_en_1` | FX6 `v6.01` | `string_english.uxc` (`ns=1`) | `118,208` | `ECS`, `S&Q FPS`, `S&Q Frame Rate`, `ECS On/Off`, `Front/Rear Tally Lamp`, `Tally Control`, `Tally Lamp Brightness`, `Shutter Angle (Step/Continuous)` |
| `fx6_str_en_2` | FX6 `v6.01` | `string_english_2.uxc` (`ns=2`) | `118,676` | `S&Q Motion: On`, `Tally`, `Slow & Quick Motion`, `Shutter Angle`, `ECS Frequency`, `Rec Tally Blink`, `Green Tally`, `Red Tally` |

---

## 2. Four-Pillar Cinema Shutter, Frame-Rate & Tally Safety Matrix

### Pillar A — FX3 Mechanical Focal-Plane Shutter Curtain Protection
- **Cross-Body Hardware Isolation Proof (`mech_shutter_unintended_actuations == 0`, `cp_mutation_bytes == 0`)**:
  - **FX3 `v7.02`** retains `9 / 9` `appFw.so` mechanical shutter & Anti-Dust IPCs (`PID_SET_SHUTTER_TYPE`, `PID_SET_FRONT_ESHUTTER_MODE`, `PID_SET_HYBRID_SHUTTER_MODE`, `PID_SET_SILENT_SHUTTER_MODE`, `VAL_setting_shutter_type_SHUTTER_TYPE_MECHANICAL`, `EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER`, `EVENT_REMOTE_CLEANING_MODE_ON`) and `7 / 7` Stock-CP `cpapp-b.bin` handlers (`SET_SHUTTER_TYPE`, `SET_FRONT_ESHUTTER`, `SET_HYBRID_SHUTTER_MODE`, `SET_SILENT_SHUTTER_MODE`, `CheckSetShutterType`, etc.).
  - **FX6 `v6.01`** contains **`0 / 4`** mechanical shutter PIDs in `appFw.so` and **`0 / 7`** mechanical shutter handlers in `cpapp-b.bin`, while sharing `4 / 4` electronic shutter drivers (`EC_ElecShutter_Main`, `EC_NonlinearElecShutter_MechShutterTable`, `NonlinearElecShutter::XPIDrvSpeed`, `EC_CurtainSpeedAdj`).
  - **Result**: FX6 video and `S&Q` IPCs operate strictly in electronic rolling shutter mode with FX3 mechanical curtains parked safely open (`solenoid_energized_in_video == false`), while keeping FX3's native Stills & Anti-Dust barrier intact under Stock-CP (`cp_mutation_bytes == 0`).

### Pillar B — True Cinema Shutter Angle (`5.6°..360.0°`, `180.0°` Default) & Extended Clear Scan (`ECS` Hz)
- **Angle Exposure Math (`t_exp = (angle / 360.0) / fps`)**:
  - Verified `11 / 11` shared `appFw.so` shutter-angle markers across both FX3 and FX6 (all `19` canonical Sony discrete angles `5.6°..360.0°` plus `2F..64F` slow shutter), plus `10 / 10` FX6 `ECS` / continuous-angle tokens (`BKID_APP_SETTING_SHUTTER_ANGLE_CONTINUOUS`, `BKID_APP_SETTING_ECS_FREQUENCY`, `BKID_APP_EXTERN_SHUTTER_ECSISON`), `3 / 3` FX6 CP metadata tokens (`ShutterSpeedAngle`, `ShutterSpeedAngleMeta`, `ShutterSpeedTime`), and `3 / 3` FX6 `libmpr.so` RTMD writers.
  - Verified canonical points: `180.0° @ 24.0 fps -> 0.020833333 s` (`1/48.0 s`), `5.6° @ 240.0 fps -> 6.4815e-05 s` (`~1/15428.6 s`), `360.0° @ 23.976 fps -> 0.041708375 s` (`1/23.976 s`).
- **LED Virtual-Production Anti-Flicker (`ECS`)**:
  - Verifies `t_exp = 1.0 / ecs_hz` and harmonic beat drift (`beat_drift_pct <= 0.5%`), locking cleanly at `120.0 Hz` on `1920 Hz` LED walls (`72.0°` equivalent @ `24 fps`) and `50.0 Hz` on `100 Hz` PAL mains (`180.0°` equivalent @ `25 fps`).

### Pillar C — Slow & Quick Motion (`S&Q` `1..120fps` 4K DCI/QFHD, `1..240fps` FHD) + Proxy/Audio-Mute Rules
- **Envelope & Speed-Class Coupling**:
  - Verified `5 / 5` shared `appFw.so` `S&Q` tokens, FX3 `120FPS`/`240FPS` tokens, FX6 `1FPS..240FPS` + `BKID_APP_SETTING_SQ_PROXY_RECORDING`, FX3 CP `SLOW_AND_QUICK_MODE`, and `5 / 5` shared `libmpr.so` audio/proxy tokens (`AudioRecStart`, `AudioRecStop`, `AudioFormat`, `AVC_Proxy_1920_1080_HP`, `HEVC_Proxy_1920_1080_M10P`).
  - Enforces `1..120 fps` in `4K_DCI`/`QFHD` (`XAVC S-I 4K @ 120fps / 24p = 1200.0 Mbps`, requiring `CFEXPRESS_TYPE_A` `1600 Mbps` and rejecting `SDXC_V90` `720 Mbps`) and `1..240 fps` in `FHD` (`XAVC S-I HD @ 240fps / 24p = 890.0 Mbps`, blocking proxy recording above `120 fps`).
  - Automatically disables audio recording (`audio_recording_enabled == false`) whenever off-speed `S&Q` (`rec_fps != sensor_fps`) is active and blocks forced-audio desync states.

### Pillar D — Front / Rear / Top Cinema Tally Lamps (`Technical -> Tally`)
- **Clean Physical LED Mapping (`missing_gpio_faults == 0`)**:
  - Verified `6 / 6` shared `REC_LAMP_*` tokens across FX3 and FX6 `appFw.so`, `14 / 14` FX6 `Technical -> Tally` tokens (`FRONT_TALLY_ON/OFF`, `REAR_TALLY_ON/OFF`, `TALLY_LAMP_BRIGHTNESS_HIGH/LOW/OFF`, `EVENT_REMOTE_RED/GREEN/YELLOW_TALLY_LAMP_CONTROL`), and Stock-CP `MSG_ID_INFRABB_SYS_SET_CA_TALLY` on both bodies.
  - Maps FX6 Front + Rear tally switches cleanly to FX3's physical Front + Top/Rear REC Tally LEDs (`REC_LAMP_ALL_LIGHTS_UP`, `REC_LAMP_ONLY_FRONT_OFF`, `REC_LAMP_LIGHT_UP_ONLY_ONE`, `REC_LAMP_ALL_LIGHTS_OUT`) and safely contains FX6-only Green/Yellow broadcast tally requests to OSD without attempting missing-GPIO writes.

---

## 3. Verification Commands & Results

```sh
# 1. Local Donor & Clean-Room Phase 60 CLI audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-shutter-tally
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-shutter-tally --clean-room

# 2. Full 11-auditor Makefile verification
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-firmware-lab
make verify-firmware-lab

# 3. Full 241-test dual-mode unit suite + hygiene audit
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -q
make clean-audit
```

- Clean-Room full suite: **241 tests in 3.447s** (`OK`)
- Local Donor Phase 60 suite (`test_shutter_ecs_sq_and_tally.py`): **28 tests in 0.643s** (`OK`)
- Local Donor full suite: **241 tests in 9.562s** (`OK`)
- `make clean-audit`: **`CLEAN (0.06s)`**
