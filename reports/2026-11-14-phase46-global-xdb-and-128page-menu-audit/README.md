# Phase 46 Report: `global.xdb` UX Database Inspector & 128-Page FX6-on-FX3 Multilingual Menu Tree Completeness Audit

- **Task / Agent**: `Hydrogen-38` (`task_cdcc0621aa58`)
- **Target Package**: [`outputs/fx3-firmware-lab/`](../../outputs/fx3-firmware-lab/)
- **Primary Module**: [`global_xdb_and_menu_tree_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/global_xdb_and_menu_tree_auditor.py)
- **CLI Entrypoint**: `python3 -B -m fx3_firmware_lab audit-xdb-menu [--clean-room]` and `audit-all` ([`__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)) — **8 unified auditors**
- **Unit Test Suite**: [`test_global_xdb_and_menu_tree.py`](../../outputs/fx3-firmware-lab/tests/test_global_xdb_and_menu_tree.py) (**28** new tests; **157** total tests in `outputs/fx3-firmware-lab/tests`, passing in both Local Donor `os.O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes)

---

## 1. Executive Summary

| Pillar | Verification Scope | Key Quantitative Result |
| --- | --- | --- |
| **Part 1: `O_RDONLY` `global.xdb` & Companion UX Inspector** | FX6 `v6.01` & FX3 `v7.02` `global.xdb` (`uxa\x07`, `hdr_flag=9`), `lang.uxb` (`uxb\x07`), `fontlist.dat`, disk closure of all `.uxc`/`.uxb` assets, plus SQLite3 `file:...?mode=ro&immutable=1` support (`0` `-wal`/`-shm` sidecars) & clean-room fallback | FX6 `v6.01`: `1,792 B`, `7/7` active slots, `63/63` files present (`0` missing), `lang.uxb` `36` entries, `fontlist.dat` `5` fonts. FX3 `v7.02`: `11,664 B`, `239` slots (`12` active + `227` `__Dummy_NS_ID__*`), `117/117` non-dummy files present (`0` missing), `lang.uxb` `36` entries, `fontlist.dat` `6` fonts |
| **Part 2: 11-Category / 128-Page Multilingual Menu Tree Audit** | All `11` Level-1 categories (`User`, `Edit User Menu`, `Shooting`, `Project`, `Paint/Look`, `TC/Media`, `Monitoring`, `Audio`, `Thumbnail`, `Technical`, `Maintenance`), `Big-6 Home` (`98` rows), `Assignable Buttons Page 110` (`54` rows, `30` pool ResIDs, `P10`), and all `128` descriptor pages in `appFw.so` across `english`, `simplifiedchinese`, `traditionalchinese`, `japanese` | `128/128` pages audited, `2,224` descriptor rows, `4,658` ResID references (`250` unique string ResIDs in donor; `8,896` / `101` in clean-room), `0` missing ResIDs, `0` corrupt UTF-8 strings, `0` null prototype/name hazards |
| **Part 3: FX3 Hardware-Predicate Safety Verification** | Maps FX6-only physical hardware controls (`Optical Variable ND`, `12G-SDI Output`, `Smart Grip/Handle Zoom`, `WLAN/Airplane`) onto deterministic FX3 safe states (`P2`..`P12`) | `4/4` hardware predicates verified (`LOCKED_CLEAR`, `HDMI_FALLBACK`, `INTERNAL_MIC_FALLBACK`, `AIRPLANE_ISOLATED`), `0` null-pointer / missing-widget hazards, `nvram_flash_mutation_bytes = 0` |

---

## 2. Part 1 — `O_RDONLY` `global.xdb` & Companion UX Table Anatomy (`FX6 v6.01` vs `FX3 v7.02`)

Both donor bodies store their UX namespace registry in Sony's binary `uxa\x07` container (`global.xdb`, magic hex `75786107`, `hdr_flag=9`) alongside `lang.uxb` (`uxb\x07`, magic hex `75786207`) and `fontlist.dat` inside `usr/share/app/` (never SQLite3 on disk, though `inspect_sqlite_ux_db_rdonly` additionally supports `file:...?mode=ro&immutable=1` without creating `-wal`/`-shm` sidecar files):

| Metric | FX6 `v6.01` (`LOCAL_DONOR_RDONLY`) | FX3 `v7.02` (`LOCAL_DONOR_RDONLY`) | Clean-Room Synthetic Fixture |
| --- | ---: | ---: | ---: |
| **Container Format / Magic** | `SONY_UXA7` (`75786107`) | `SONY_UXA7` (`75786107`) | `SONY_UXA7` (`75786107`) |
| **`global.xdb` File Size** | `1,792 B` | `11,664 B` | `1,792 B` (FX6) / `1,724 B` (FX3) |
| **`hdr_flag` / Top Namespace Slots** | `9` / `7` (`7` active, `0` dummy) | `9` / `239` (`12` active, `227` `__Dummy_NS_ID__*`) | `9` / `7` (FX6) & `12` (FX3, `5` dummy) |
| **Resource Entries (Total / Non-Dummy)** | `63` / `63` | `344` / `117` | `63` / `63` (FX6) & `51` / `46` (FX3) |
| **Disk Closure (`usr/share/app/`)** | `63 / 63` present (`0` missing) | `117 / 117` present (`0` missing) | `63 / 63` (FX6) & `46 / 46` (FX3) |
| **`lang.uxb` Namespace / Entries** | `uxb\x07`, `ns=4`, `36` entries | `uxb\x07`, `ns=59`, `36` entries | `uxb\x07`, `ns=4`/`59`, `36` entries |
| **`fontlist.dat` Font Mappings** | `5` (`UniversOTS-SJ_wIcon.ltt`, `HeiseiKakuGothW5`, `GB18030`, `Big5HKSCS`, `KSX1001`) | `6` (includes `Sony_DI_Icons.ttf`) | `5` (FX6) / `6` (FX3) |

---

## 3. Part 2 — 11-Category / 128-Page Multilingual Menu Tree Completeness (`EN` / `ZH-CN` / `ZH-TW` / `JA`)

### 3.1 Level-1 Cinema Line Categories (11/11 Complete Across All 4 Languages)

| Cat | Category Key | Title ResID | EN | Simplified Chinese | Traditional Chinese | Japanese | Missing / Corrupt |
| ---: | --- | --- | --- | --- | --- | --- | ---: |
| `0` | `User` | `0x02004208` | `User` | `用户` | `用戶` | `User` | `0 / 0` |
| `1` | `Edit User Menu` | `0x02004d4a` | `Edit User Menu` | `编辑用户菜单` | `編輯用戶功能表` | `User Menu編集` | `0 / 0` |
| `2` | `Shooting` | `0x02002227` | `Shooting` | `拍摄` | `拍攝` | `Shooting` | `0 / 0` |
| `3` | `Project` | `0x02002228` | `Project` | `项目` | `專案` | `Project` | `0 / 0` |
| `4` | `Paint/Look` | `0x02002493` | `Paint/Look` | `绘图/风格` | `繪製/外觀` | `Paint/Look` | `0 / 0` |
| `5` | `TC/Media` | `0x0200222b` | `TC/Media` | `TC/媒体` | `TC/媒體` | `TC/Media` | `0 / 0` |
| `6` | `Monitoring` | `0x02002229` | `Monitoring` | `监看` | `監控` | `Monitoring` | `0 / 0` |
| `7` | `Audio` | `0x020041fb` | `Audio` | `音频` | `音訊` | `Audio` | `0 / 0` |
| `8` | `Thumbnail` | `0x02004209` | `Thumbnail` | `缩略图` | `縮圖` | `Thumbnail` | `0 / 0` |
| `9` | `Technical` | `0x0200222a` | `Technical` | `技术` | `技術` | `Technical` | `0 / 0` |
| `10` | `Maintenance` | `0x02004203` | `Maintenance` | `维护` | `維護` | `Maintenance` | `0 / 0` |

### 3.2 `Big-6 Home`, `Assignable Buttons Page 110` (`P10`), and Full 128-Page Descriptor Sweep

- **`Big-6 Home` (`98` rows)**: All 6 Cinema Line home cells (`FPS`, `ISO`, `Shutter`, `ND Filter`, `Base Look`, `White Balance`) decode cleanly in `EN`, `ZH-CN`, `ZH-TW`, and `JA` (`big6_home_verified = True`).
- **`Assignable Buttons Page 110` (`0x02EB75F0`, `54` rows, `30` assignable pool ResIDs, `P10`)**: `assignable_p10_page110_verified = True`, covering custom FX3 hardware remap targets without null prototypes or unmapped labels.
- **Full 128-Page Sweep (`FX6 v6.01 appFw.so`)**: `128 / 128` widget descriptor tables (`2,224` total rows), `4,658` ResID references (`250` unique string ResIDs across `ns=1` `5,044` and `ns=2` `5,915` entries in all 4 languages in Local Donor; `8,896` references across `101` unique ResIDs in Clean-Room), `0` missing string/common ResIDs, `0` corrupt UTF-8 entries, and `0` null descriptor pointers or names.

---

## 4. Part 3 — FX3 Hardware-Predicate Safety Matrix (`P2`..`P12`)

| Predicate ID | Patch Gate | FX6 Hardware Menu Feature | Deterministic FX3 Safe State | `appFw.so` Symbol Evidence | Null / Widget Hazards | NVRAM Flash Bytes |
| --- | --- | --- | --- | --- | ---: | ---: |
| `VARIABLE_ND` | `P4` | Optical Variable ND (`Auto / Preset / Clear`) | `LOCKED_CLEAR` | `set_nd_filter_mode_i` (`found=True`) | `0` | `0` |
| `SDI_12G_OUTPUT` | `P2+P5` | `12G-SDI Output` (`SDI1` / `SDI2`) | `HDMI_FALLBACK` | `PRM_FEATURE_MANAGER_sdi_output` (`found=True`) | `0` | `0` |
| `SMART_GRIP_HANDLE_ZOOM` | `P3+P10+P11` | Detached `Smart Grip / Handle` Controls & Audio | `INTERNAL_MIC_FALLBACK` | `INFRA_HOTSHOE_UIPC_SHOEINFO_EVT` (`found=True`) | `0` | `0` |
| `WLAN_AIRPLANE_GATE` | `P12` | `Wireless LAN / Wi-Fi` under Airplane Gate | `AIRPLANE_ISOLATED` | `EXTERN_SETTING_AIRPLANE_MODE_ON` (`found=True`) | `0` | `0` |

---

## 5. Verification Summary & Commands

- **Local Donor Mode (`LOCAL_DONOR_VERIFIED`)**: `report_sha256 = b3072135baf3dc50d3ea901b3aa00a1d34ceff828c8a7293812b15479d05d9cc`, `all_checks_passed = True`, `o_rdonly_enforced = True`, `sqlite_wal_shm_forbidden = True`, `zero_null_pointer_hazards = True`.
- **Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC_VERIFIED`)**: `report_sha256 = 08142389b4be0112c5aefd8ebf1193bc58ee6f38d780eba364bfd32ba89b67c6`, `all_checks_passed = True`, `o_rdonly_enforced = True`, `sqlite_wal_shm_forbidden = True`, `zero_null_pointer_hazards = True`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-xdb-menu
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-xdb-menu --clean-room
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest -v outputs/fx3-firmware-lab/tests/test_global_xdb_and_menu_tree.py
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest -v outputs/fx3-firmware-lab/tests/test_global_xdb_and_menu_tree.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-firmware-lab
make verify-firmware-lab
make clean-audit
```
