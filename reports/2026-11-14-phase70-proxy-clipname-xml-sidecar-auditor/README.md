# Phase 70 Report — 13th Unified Firmware-Lab Auditor: Dual-Slot Proxy (`XAVC HS/S`), Cinema Line `CamID/Reel` Clip Naming & `NonRealTimeMeta.xml` Sidecar

- **Date**: `2026-11-14`
- **Target Package**: `outputs/fx3-firmware-lab/` ([`proxy_clipname_and_sidecar_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/proxy_clipname_and_sidecar_auditor.py))
- **Milestone**: **13th Unified Auditor** integrated into [`run_audit_all()`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) (`audit-proxy-clipname [--clean-room] [--json]`)
- **Dual-Mode Verification Status**:
  - **Local Donor (`os.O_RDONLY`)**: `LOCAL_DONOR_VERIFIED`, `all_checks_passed = true`, `10 / 10` donor artifacts verified (`0.181s` standalone, well within `< 0.6s`), `report_sha256 = 8d727c5b9d45ce6bc7c6849b3c9de5e369f26de67543f2fe1f8a8967fddeee5f`
  - **Forced Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**: `CLEAN_ROOM_SYNTHETIC_VERIFIED`, `all_checks_passed = true`, `10 / 10` synthetic fixtures verified (`0.002s` standalone), `report_sha256 = 8e22ac3374b076810f542f438f6f40cf2d27e94ee99a5c7cb3f8abb84e2aa07a`
  - **Unit Tests**: `303 / 303` total suite tests pass (`4.037s` Clean-Room, `10.558s` Local Donor across all 11 test files; `32` new Phase 70 tests in [`test_proxy_clipname_and_sidecar.py`](../../outputs/fx3-firmware-lab/tests/test_proxy_clipname_and_sidecar.py) running in `0.503s` Local Donor / `0.326s` Clean-Room)

---

## 1. Strictly `os.O_RDONLY` Donor Artifact Inventory (10 Binaries, `global.xdb` & String Packs)

All local donor reads open files strictly via `os.O_RDONLY` (`mmap.ACCESS_READ` ELF64 `.rodata`/`.dynstr` section-scoped single-pass scanning without copying or mutating proprietary files), and fall back deterministically to synthetic clean-room fixtures when `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or absent donor trees are detected.

| Key | Body / FW | Artifact | Local Donor Size (B) | Role in Phase 70 Audit |
|---|---|---|---:|---|
| `fx3_appfw` | FX3 `v7.02` | `appFw.so` (`icx1295` AP host) | `79,015,712` | `XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_C/L/R`, `CheckCamIdReelNoFile`, `PROXY_RECORD_SETTING_16M/9M_420_10BIT_XAVC_HS_HD`, `PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD`, `SIMULTANEOUS_RECORDING`, `SORT_RECORDING`, `RELAY_REC_ON`, `600MBPS`/`400MBPS` speed cautions, `InfraC2PA` immutability markers |
| `fx6_appfw` | FX6 `v6.01` | `appFw.so` | `50,520,424` | `BKID_APP_CAMID_CURRENT_REEL_NUMBER0`, `BKID_APP_CAMID_CURRENT_CAMERA_POSITION0`, `BKID_APP_SETTING_XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION`, `/XDROOT/`, `/M4ROOT/`, `S03.MP4`, `M01.XML`, `PROXY_RECORD_SETTING_*`, Dual-Slot markers |
| `fx3_libmpr` | FX3 `v7.02` | `libmpr.so` | `3,517,008` | `XavcsNamer::ResetNumberCounter`, `CheckCamIdReelNoFile`, `MovieNamingMode`, `PrepareRelayMedia`, `LOG_ID_VPG_MANAGER`, `NonRealTimeMeta`, `urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20`, `CaptureGammaEquation`, `CaptureColorPrimaries`, `s-log3-cine`, `s-gamut3-cine`, `s-cinetone`, `rec709`, `ul_RecommendedExposureIndex`, `Device` |
| `fx6_libmpr` | FX6 `v6.01` | `libmpr.so` | `28,921,824` | Shared `XavcsNamer`/`NonRealTimeMeta v2.20` markers + `libXavcMxf::SetClipName`, `IsMp4ProxyPath`, `/XDROOT/`, `ExposureIndex`, `MonitoringDescription`, `MonitoringBaseCurve` |
| `fx3_global_xdb` | FX3 `v7.02` | `global.xdb` (`uxa\x07`) | `11,664` | Structural `uxa\x07` + `lang.uxb` + `fontlist.dat` validation |
| `fx6_global_xdb` | FX6 `v6.01` | `global.xdb` (`uxa\x07`) | `1,792` | Structural `uxa\x07` + `lang.uxb` + `fontlist.dat` validation |
| `fx3_str_en` | FX3 `v7.02` | `string_english.uxc` (`ns=39`) | `165,740` | `0x0004E0AE` (`2 memory cards required.\nRecording Mode: Sort`) |
| `fx3_str_en_g` | FX3 `v7.02` | `string_english_g.uxc` (`ns=3`) | `69,600` | `0x0000652B` (`Reel`), `0x00006532` (`Title`) |
| `fx6_str_en_1` | FX6 `v6.01` | `string_english.uxc` (`ns=1`) | `118,208` | `0x00002200` (`Reel`), `0x00002244` (`Clip Name Format`) |
| `fx6_str_en_2` | FX6 `v6.01` | `string_english_2.uxc` (`ns=2`) | `118,676` | `Simul Rec`, `XAVC Proxy Rec Mode`, `Proxy Rec`, `Proxy Format`, `Auto Naming`, `Title Prefix`, `Camera Position`, `Camera ID`, `Cam ID + Reel#` |

---

## 2. Three-Pillar Clip Naming, Dual-Slot Proxy & `NonRealTimeMeta.xml` Verification

### Pillar 1 — Cinema Line `CamID / Reel#` (`A001C001_YYMMDD_XXXX`) vs `Title/Alpha` (`C0001`) Clip Naming & Proxy `S03` Pairing
- **Regex & Token Validation**: Enforces `Cam ID` (`A..Z`), `Reel Number` (`001..999`, with deterministic `999 -> 001` rollover via `advance_reel_number`), `Camera Position` (`C/L/R`), `Clip Number` (`001..999`), calendar-valid `Date` (`YYMMDD`), and 4-char uppercase alphanumeric Camera UID (`[A-Z0-9]{4}`), alongside `Title/Alpha` (`C0001` / custom prefix).
- **Container & `S03.MP4` Proxy Pairing**:
  - `XAVC-I/L` (`MXF`): `XDROOT/Clip/A001C001_261114_R7F3.MXF` <-> `XDROOT/Sub/A001C001_261114_R7F3S03.MP4` + `XDROOT/Clip/A001C001_261114_R7F3M01.XML`
  - `XAVC S / S-I / HS` (`MP4`): `M4ROOT/CLIP/A001C001_261114_R7F3.MP4` <-> `M4ROOT/SUB/A001C001_261114_R7F3S03.MP4` + `M4ROOT/CLIP/A001C001_261114_R7F3M01.XML`
- **Proxy Codec & `S&Q` Auto-Disable Rule**: Verifies `1920x1080 10-bit 4:2:0 XAVC HS` (`16 / 9 Mbps`) and `1280x720 8-bit XAVC S` (`6 Mbps`) proxy profiles, and automatically disables proxy generation (`SQ_OFF_SPEED_PROXY_AUTO_DISABLED`) when off-speed `S&Q` (`1..240fps`) is active (explicitly blocking forced proxy overrides during `S&Q`).

### Pillar 2 — Dual-Slot (`Slot A` + `Slot B` CFexpress Type A / SDXC UHS-II) Recording Modes & Speed-Class Gate
- **All 4 Dual-Slot Modes Verified**:
  - `SIMULTANEOUS`: `Main A + Main B` redundant backup on `SLOT_A` + `SLOT_B`.
  - `RELAY`: Seamless `Slot A -> Slot B` rollover on `Slot A` full (`dropped_frames == 0`).
  - `SORT`: `Main` routed to `SLOT_A` (`CFEXPRESS_VPG400`), `Proxy/Sub` (`S03.MP4`) routed to `SLOT_B` (`SDXC UHS-II`), gracefully skipping `SLOT_B` proxy writes when `S&Q` disables proxy.
  - `OFF`: Single-slot capture on active `SLOT_A` or `SLOT_B`.
- **Speed-Class Gate & Internal eMMC `p1` Isolation**:
  - `XAVC S-I 4K60 600Mbps` accepts `SDXC_V90` / `CFEXPRESS_VPG200` / `CFEXPRESS_VPG400` and cleanly rejects `SDXC_V30` / `SDXC_V60` (`BLOCKED_SPEED_CLASS_REJECT`, `libmpr_crashed == False`).
  - `S&Q 4K120` All-Intra requires `CFEXPRESS_VPG200` / `CFEXPRESS_VPG400` and cleanly rejects `SDXC_V90` / `V60` / `V30` without crashing `libmpr`.
  - Blocks any write targeting `/dev/nflasha*`, `/dev/cnflasha*`, or `p1:` (`internal_emmc_clip_writes == 0`, `persistent_emmc_writes_authorized == False`).

### Pillar 3 — Sony `NonRealTimeMeta` XML Sidecar (`*M01.XML`) Synthesizer & NLE (`Resolve` / `Premiere` / `Catalyst`) LUT/EI Auto-Tag Verifier
- Pure-Python `xml.etree.ElementTree` synthesizer and schema validator for `urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20` sidecar XML (`*M01.XML`):
  - `CaptureGammaEquation`: `s-log3-cine`, `s-log3`, `rec709`, `s-cinetone`
  - `CaptureColorPrimaries`: `s-gamut3-cine`, `s-gamut3`, `rec709`
  - `ExposureIndexOfPhotoMeter`: `200..51200` Cine EI metadata vs Dual Base ISO (`800` / `12800`) stop shift ($\log_2(\text{EI} / \text{BaseISO})$) for non-destructive NLE gain offset
  - `MonitoringDescriptions`: `.cube` 3D LUT reference (`User1.cube..User4.cube`, rejecting path traversal / control characters)
  - `Device`: `manufacturer="Sony"`, `modelName="ILME-FX3"`, `ver="7.02-stageB-ram-overlay"` provenance while enforcing `c2pa_spoof_attempted == False` and `c2pa_rq_lic_preserved == True` (preserving FX3 C2PA `RQ_LIC.DAT` signatures).

---

## 3. Verification Commands & Results

```sh
# 1. Local Donor & Clean-Room Phase 70 CLI audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-proxy-clipname --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-proxy-clipname --clean-room --json

# 2. Full 13-auditor unified CLI check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room

# 3. Full 303-test dual-mode unit suite + hygiene audit
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py" -q
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- Clean-Room full suite: **303 tests in 4.037s** (`OK`)
- Local Donor Phase 70 suite (`test_proxy_clipname_and_sidecar.py`): **32 tests in 0.503s** (`OK`; Clean-Room **32 tests in 0.326s**)
- Local Donor full suite: **303 tests in 10.558s** (`OK`)
- `scripts/run_all_lab_tests.py --clean-only`: verifies zero untracked `.so`/`.elf`/`.ko`/`.cpio`/`.bin`/`.vfat`/`.pyc` or `__pycache__` artifacts
