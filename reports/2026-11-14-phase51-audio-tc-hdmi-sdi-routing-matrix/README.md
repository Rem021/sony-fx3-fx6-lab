# Phase 51 Report: 4-Ch `24-bit 48kHz` `XLR-H1` Audio Routing, `SMPTE 12M` Timecode (`VMC-BNCM1` `EXT-LK` & HDMI TC) & `12G-SDI` -> `HDMI Type-A 16-bit RAW` Output Matrix Audit

- **Task / Agent**: `Hydrogen-44` (`task_9c404569ab4e`)
- **Target Package**: [`outputs/fx3-firmware-lab/`](../../outputs/fx3-firmware-lab/)
- **Primary Module**: [`audio_tc_hdmi_sdi_routing_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/audio_tc_hdmi_sdi_routing_auditor.py)
- **CLI Entrypoint**: `python3 -B -m fx3_firmware_lab audit-audio-tc-hdmi [--clean-room]` and `audit-all` ([`__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)) — **9 unified auditors**
- **Unit Test Suite**: [`test_audio_tc_hdmi_sdi_routing.py`](../../outputs/fx3-firmware-lab/tests/test_audio_tc_hdmi_sdi_routing.py) (**28** new tests; **185** total tests in `outputs/fx3-firmware-lab/tests`, passing in both Local Donor `os.O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes)

---

## 1. Executive Summary

| Pillar | Verification Scope | Key Quantitative Result |
| --- | --- | --- |
| **O_RDONLY Donor & Clean-Room Dual Mode** | FX3 `v7.02` (`appFw.so`, `libmpr.so`, `cpapp-b.bin`) + FX6 `v6.01` (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `libInfraHotshoe.so`, `AVBB_SCN_START_AUDIO.so`, `AVBB_SCN_START_PANELEVF.so`) vs deterministic clean-room fixtures | `9 / 9` donor binaries verified strictly `os.O_RDONLY` (`195,902,224 B` total in Local Donor; `4,818 B` synthetic in Clean-Room), `o_rdonly_enforced = True` |
| **Pillar A: 4-Ch `24-bit 48kHz LPCM` Audio & `P11` Hot-Detach** | FX6 Smart Handle `CH1/CH2` + MI-Shoe `CH3/CH4` <-> FX3 `XLR-H1` MI-Shoe (`CH1/CH2 XLR/TRS` + `CH3/CH4 3.5mm/Internal`), 3.5mm body mic jack, 3.5mm headphone monitor bus, and `P11` (`0x91db059b`) hot-detach fallback | `4,608,000 bps` 4-ch 24-bit 48kHz LPCM parity; `13/13` FX3 & `18/18` FX6 `appFw.so` audio markers + `libInfraHotshoe.so` `E_TMO = -50 -> 0x8000`; `P11` hot-detach falls back cleanly to `INTERNAL_STEREO` (`recording_continues = True`, `recording_stalled = False`) |
| **Pillar B: `SMPTE 12M` Timecode & Phase 38 Isolation** | `Preset` / `Regen` / `Free Run` / `Rec Run` / `EXT-LK`, FX6 BNC `TC IN/OUT` vs FX3 Multi-Port `VMC-BNCM1` `LTC IN` (`Pin 3`, `680 kOhm` ID) + `HDMI TC ON` (Atomos trigger) + Phase 38 `H0`/`Tier-3` `uart_boot` rule | `10/10` shared `appFw.so` TC markers + `4/4` FX6 extra `EXT-LK`/RTC markers + `2/2` shared CP TC markers; `SMPTE 12M` NDF/DF BCD validated; `VMC-BNCM1` + `uart_boot` (`Pins 7/8/9`) collision deterministically blocked (`BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION`) |
| **Pillar C: `12G-SDI` + `HDMI` -> FX3 `HDMI Type-A` Routing** | `4264x2408 16-bit Linear RAW` HDMI output, `4K DCI / QFHD 10-bit 4:2:2` clean feed (`HDMI_INFO_DISPLAY_OFF`), independent `MLUT` (`Monitor 3D LUT On/Off`), and `SDI Sub-Output` / `SDI Main` no-op containment | `5/5` shared HDMI RAW markers, `4/4` FX3 HDMI feed markers, `11/11` FX6 MLUT/SDI markers, `7/7` `AVBB_SCN_START_PANELEVF.so` markers, `0` unexpected SDI hardware markers on FX3, `0` missing-transceiver panics, `0` black-screen stalls |

---

## 2. Strictly `os.O_RDONLY` Donor Inventory (`FX3 v7.02` & `FX6 v6.01`)

| Artifact Key | Relative Donor Path | Local Donor Size (Bytes) | Clean-Room Fixture (Bytes) | Role in Phase 51 Audit |
| --- | --- | ---: | ---: | --- |
| `fx3_appfw` | `fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so` | `79,015,712` | `1,555` | FX3 `48kHz 24-bit 4ch`, `XLRMIC`, `HEADPHONE`, `TC_MAKE`/`TC_RUN`/`EXT_TC`/`HDMI_TC`, `HDMI_RAW`/`4K`/`QFHD` markers & zero SDI HW proof |
| `fx6_appfw` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so` | `50,520,424` | `2,258` | FX6 `HOTSHOE_DIGMIC_F48B24C4`, `CONNECT_SHOE_MIC_DIGITAL_XLR`, `BKID_APP_EXTERN_MONITOR_LUT_*`, `TYPE_SDI_OUTPUT_NOT_SUPPORT`, `P11` `chaplin_base` |
| `fx3_libmpr` | `sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so` | `3,517,008` | `103` | Shared `AudioRecStart`, `AudioRecPort`, `AudioFormat` |
| `fx6_libmpr` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so` | `28,921,824` | `191` | Shared `AudioRec*` + `DEMUXCHUNKTYPE_EVENT_LPCM_STREAM_TO_CODEC_1..4` |
| `fx3_cpapp` | `sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin` | `15,980,568` | `142` | Shared `MSG_ID_INFRABB_SYS_SET_TIMECODE_PRESET` / `DFMODE` & zero `MoniFpgaSdi` |
| `fx6_cpapp` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin` | `17,952,816` | `218` | Shared CP TC + `ADJ_CMD_AVBB_TIMECODE_CHANGE_TC_IO` / `TC_GET_TCOUT_VALUE` |
| `fx6_hotshoe` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so` | `47,808` | `207` | `INFRA_HOTSHOE_UIPC_SHOEINFO_EVT`, `SETCTRL_BCK_LRCK`, `WaitRecvCompMsgFromHotshoeRsrc`, `RCMHR_TMO` |
| `fx6_avbb_audio` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/scenario/AVBB_SCN_START_AUDIO.so` | `70,096` | `138` | `AVBB_SCN_START_AUDIO`, `BO_ID_SHOE_MIC`, `BO_ID_MIC`, `LOG_SET_ANTI_CLIP_ADF_START` |
| `fx6_avbb_panelevf` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/scenario/AVBB_SCN_START_PANELEVF.so` | `275,968` | `214` | `AVBB_SCN_START_HDMI`, `AVBB_SCN_START_HDMI_SDI_SUB`, `EXEC_SDI_MAIN_OUTPUT`, `EXEC_SDI_SUB_OUTPUT`, `SET_MONITOR_MLUT`, `_Z12GetOutputSelhPh` |

---

## 3. Three-Pillar Compatibility Matrix Details

### 3.1 Pillar A — 4-Channel `24-bit 48kHz LPCM` Audio & `P11` (`0x91db059b`) Hot-Detach Fallback

| Channel / Bus | FX6 `v6.01` Interface | FX3 `v7.02` `XLR-H1` / Body Interface | Hot-Detach Fallback (`0x91db059b` `0x88000002`) | Verdict |
| --- | --- | --- | --- | --- |
| `CH1` | Smart Handle `XLR1` (`Line/Mic/+48V`) | `XLR-H1` MI-Shoe `INPUT 1` (`XLR/TRS +48V` Digital I2S) | Body 3.5mm Mic Jack L / `Internal Stereo L` | `FULL_PARITY_MI_SHOE_24BIT_48KHZ` |
| `CH2` | Smart Handle `XLR2` (`Line/Mic/+48V`) | `XLR-H1` MI-Shoe `INPUT 2` (`XLR/TRS +48V` Digital I2S) | Body 3.5mm Mic Jack R / `Internal Stereo R` | `FULL_PARITY_MI_SHOE_24BIT_48KHZ` |
| `CH3` | MI-Shoe Digital `CH3` / Internal Mic L | `XLR-H1` `INPUT 3` (`3.5mm Stereo L`) / Internal Mic L | `Internal Stereo L` (non-stalling) | `FULL_PARITY_4CH_EXPANSION` |
| `CH4` | MI-Shoe Digital `CH4` / Internal Mic R | `XLR-H1` `INPUT 3` (`3.5mm Stereo R`) / Internal Mic R | `Internal Stereo R` (non-stalling) | `FULL_PARITY_4CH_EXPANSION` |
| `BODY_3_5MM_MIC_JACK` | Body 3.5mm Mic In (`JACK_MIC_CONNECT_ON`) | Red 3.5mm Stereo Mic Jack (`Plug-in Power`) | `Internal Stereo Mic` | `NATIVE_1_TO_1_PARITY` |
| `HEADPHONE_3_5MM_MONITOR_BUS` | 3.5mm Headphone Out (`BKID_APP_SETTING_HEADPHONE_OUT`) | Black 3.5mm Headphone Jack (`CH1/2`, `CH3/4`, Mix) | Built-in Monitor Speaker | `NATIVE_1_TO_1_PARITY` |

- **Bitrate & Framing**: `48,000 Hz * 24-bit * 4 ch = 4,608,000 bps` (`12 B/sample period`).
- **Non-Stalling Hot-Detach Guard**: `P11` `0x91db059b` emits `0x88000002` (detached) while `libInfraHotshoe.so` `WaitRecvCompMsgFromHotshoeRsrc` returns `0x8000` on `E_TMO = -50`; spoofed `0x88000001` (attached) or blocking waits fail closed.

### 3.2 Pillar B — `SMPTE 12M` Timecode (`VMC-BNCM1` `EXT-LK`, `HDMI TC ON` & Phase 38 `uart_boot` Guard)

| Feature | FX6 `v6.01` | FX3 `v7.02` | Policy / Guard Rule |
| --- | --- | --- | --- |
| `TC Make` (`Preset` / `Regen`) | `VAL_setting_tc_make_TC_MAKE_PRESET` / `_REGENRATE` | Identical `appFw.so` + CP `PRESET`/`DFMODE` | `FULL_PARITY` (`SMPTE 12M` NDF/DF BCD validated) |
| `TC Run` (`Free Run` / `Rec Run`) | `VAL_setting_tc_run_TC_RUN_FREE_RUN` / `_REC_RUN` | Identical + `P11 0x92d2091c` `/dev/rtc0->udate` | `FULL_PARITY` |
| `EXT-LK` LTC Jam-Sync IN | Dedicated Rear BNC `TC IN` (`Lock/PseudoLock/Unlock`) | Multi-Port 15-Pin `VMC-BNCM1` (`Pin 3 LTC+`, `Pin 2 GND`, `Pin 6 680 kOhm ID`) | Normal shooting `EXT-LK` supported; **Phase 38 redline**: `VMC-BNCM1` MUST be disconnected during `H0`/`Tier-3` `uart_boot` (`Pins 7/8/9`) -> `BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION` |
| `BNC TC OUT` vs `HDMI TC ON` | Dedicated BNC `TC OUT` + `HDMI TC Output On/Off` | No BNC `TC OUT`; `EXTERNAL_HDMI_TC_OUTPUT_ON` | Atomos Ninja/Shogun trigger via `HDMI TC ON` verified; FX3 BNC `TC OUT` blocked (`BLOCKED_FX3_NO_BNC_TC_OUT`) |

### 3.3 Pillar C — `12G-SDI` + `HDMI` Monitoring -> FX3 Full-Size `HDMI Type-A` Safe Routing

| Output Route | FX6 `v6.01` Mode | FX3 `v7.02` `HDMI Type-A` Safe Route | Containment / `MLUT` Result |
| --- | --- | --- | --- |
| `HDMI_16BIT_LINEAR_RAW` | `12G-SDI RAW` / `HDMI RAW` (`4096x2160` / `3840x2160` / `4240x2392`) | `4264x2408 16-bit Linear RAW` (up to `60p`) | LCD `MLUT` On allowed; HDMI `MLUT` Off enforced on RAW (`0` panics / `0` stalls) |
| `HDMI_4K_DCI_QFHD_10BIT_422_CLEAN` | `HDMI Out` `4K DCI` / `QFHD` `10-bit 4:2:2` | `HDMI Type-A` `4096x2160` / `3840x2160` `10-bit 4:2:2` Clean Feed | `HDMI_INFO_DISPLAY_OFF` enforced |
| `MLUT_PER_OUTPUT_LCD_HDMI` | Per-output `Monitor 3D LUT On/Off` (`LCD/VF`, `HDMI`, `SDI1/2`) | Independent `LCD` + `HDMI Type-A` `MLUT On/Off` | `SDI1` LUT gated off via `TYPE_SDI_OUTPUT_NOT_SUPPORT` |
| `SDI_MAIN_AND_SUB_OUTPUT_CONTAINMENT` | `EXEC_SDI_MAIN_OUTPUT` / `EXEC_SDI_SUB_OUTPUT` (`AVBB_SCN_START_HDMI_SDI_SUB`) | `NO_OP_CONTAINED` -> Active `HDMI Type-A` Feed | `missing_transceiver_panics = 0`, `black_screen_stalls = 0` |

---

## 4. Verification Summary & Observed Results

- **Local Donor Mode (`LOCAL_DONOR_VERIFIED`)**: `report_sha256 = a9aa3756c92b608ecc9ecf716f178c72e9cd9e277701c4a2f04e7f6748117233`, `all_checks_passed = True`, `o_rdonly_enforced = True`.
- **Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC_VERIFIED`)**: `report_sha256 = 486548dd326b1021344ee13a775986c6b8c830748666eade6c791779ba6e2818`, `all_checks_passed = True`, `o_rdonly_enforced = True`.
- **Unit Tests**:
  - `test_audio_tc_hdmi_sdi_routing.py`: `28/28` passed in `0.694s` (Local Donor) and `0.322s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`).
  - Full `outputs/fx3-firmware-lab/tests` (**185 tests**, **9 unified auditors**): `185/185` passed in `2.505s` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) and `6.996s` (Local Donor).

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-audio-tc-hdmi
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-audio-tc-hdmi --clean-room
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-firmware-lab
make verify-firmware-lab
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
make clean-audit
```
