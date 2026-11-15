# Phase 93 — 18th Unified `fx3-firmware-lab` Auditor: Interval Recording, Picture Cache DDR Ring-Buffer & Wired USB-LAN FTP P12 RF-Off Firewall (`interval_cache_and_ftp_auditor.py`)

- **Date / 日期**: 2026-11-14
- **Schema / 版本**: `fx3_firmware_lab_phase93_interval_cache_ftp_v1` (`93.0.0`)
- **Upstream Wave-10 Intel Report / 上游情报报告**: [`reports/2026-11-14-global-sony-wave10-interval-cache-ftp-intel/README.md`](../2026-11-14-global-sony-wave10-interval-cache-ftp-intel/README.md)
- **Strict Read-Only / 只读零突变约束**: `os.O_RDONLY` + `mmap.ACCESS_READ`, `persistent_emmc_writes_authorized = False`, `calibration_mutation_bytes = 0`, `emmc_mutation_bytes = 0`

---

## 1. Executive Summary / 核心摘要

Phase 93 integrates the **18th unified auditor** ([`interval_cache_and_ftp_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/interval_cache_and_ftp_auditor.py)) into `fx3-firmware-lab`, bringing full dual-mode (`LOCAL_DONOR_VERIFIED` + `CLEAN_ROOM_SYNTHETIC`) verification to three high-risk Cinema Line workflows across FX3 `v7.02` and FX6 `v6.01`:

1. **Pillar 1 — Interval Recording (`1s..60s`, `1..9999` Shots) & Electronic-Shutter Wear Firewall**
2. **Pillar 2 — Picture Cache (`Pre-Rec`) Circular DDR Ring-Buffer Budget on FX3 `2048 MiB` AP DRAM**
3. **Pillar 3 — Wired USB-LAN (`CDC-NCM` / `RTL8153`) FTP/FTPS (`TLS 1.2/1.3`, `PASV`, `REST`) + `P12` `00342260` RF-Off & `p1..p15` Path-Traversal Firewall**
4. **Pillar 4 — Calibration / Internal eMMC Zero-Mutation Proof & `NonRealTimeMeta v2.20` XML Tag Parity**

第 93 阶段向 `fx3-firmware-lab` 集成第 18 个统一审计器 [`interval_cache_and_ftp_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/interval_cache_and_ftp_auditor.py)，在本地只读供体（`LOCAL_DONOR_VERIFIED`）与净室合成（`CLEAN_ROOM_SYNTHETIC`）双模式下全部通过验证，全套 18 个审计器与 **475 项单元测试** 在双模式下 **100% 绿灯**。

---

## 2. Observed Verification Metrics / 实测验证数据

| Metric / 指标 | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) | Gate / 门禁要求 |
| :--- | :--- | :--- | :--- |
| **18th Auditor Status** | `all_checks_passed = True` (`0` errors) | `all_checks_passed = True` (`0` errors) | 100% Pass |
| **18th Auditor Wall Runtime** | **`0.2183 s`** | **`0.0031 s`** | `< 0.35 s` local / `< 0.02 s` clean-room |
| **Report SHA-256 Digest** | `764d645c8f008e58ec240157ab0109de88726dea5c1273cb82514c76ed727a61` | `d790c0dc69875ffa343523b7f8fc92b32f6642bcb97e9fb3fc3bc7efd23f9db0` | Deterministic |
| **`audit-all --json`** | **18 / 18 green** (`all_checks_passed = True`) | **18 / 18 green** (`all_checks_passed = True`) | 18 / 18 Auditors |
| **Phase 93 Unit Tests (`test_interval_cache_and_ftp_auditor.py`)** | **38 / 38 passed** (`1.326 s`) | **38 / 38 passed** | `>= 34` dual-mode tests |
| **Full Lab Unit Suite (`unittest discover`)** | **475 / 475 passed** (`15.820 s`) | **475 / 475 passed** (`7.173 s`) | Zero failures |
| **`scripts/run_all_lab_tests.py --clean-only`** | `CLEAN (0.04s)` — ALL GREEN | `CLEAN (0.04s)` — ALL GREEN | Zero `.pyc` / binaries |
| **Calibration / eMMC Mutation** | `0 B` / `0 B` (`O_RDONLY`) | `0 B` / `0 B` | Strict zero-mutation |

---

## 3. Inspected Local Donor Artifacts (`os.O_RDONLY`) / 只读本地供体清单

| Artifact Key | Exact Role | Local Donor Size (Bytes) | Clean-Room Fixture Size (Bytes) | Verified Real Markers / Findings |
| :--- | :--- | ---: | ---: | :--- |
| `fx3_appfw` | FX3 `v7.02` `appFw.so` | `79,015,712` | `849` | `PID_SET_INTERVAL_REC`, `VAL_setting_interval_shooting_INTERVAL_SHOOTING_ON`, `VAL_setting_ftp_connect_method_FTP_CONNECT_METHOD_USB_ETHER`, `VAL_setting_airplane_mode_AIRPLANE_MODE_ON`, `VAL_cloud_function_state_CLOUD_FUNCTION_STATE_STARTED` |
| `fx6_appfw` | FX6 `v6.01` `appFw.so` | `50,520,424` | `1,176` | `VAL_setting_interval_rec_INTERVAL_REC_ON`, `VAL_is_changing_interval_rec_to_picture_cache_rec_IS_CHANGING_INTERVAL_REC_TO_PICTURE_CACHE_REC_TRUE`, `BKID_APP_SETTING_PICTURE_CACHE_REC`, `VAL_setting_cache_rec_size_CACHE_REC_SIZE_SHORT..MAX`, `VAL_setting_auto_upload_proxy_AUTO_UPLOAD_PROXY_CHUNK` |
| `fx3_libmpr` | FX3 `libmpr.so` | `3,517,008` | `139` | `_ZN5MprIf11PreRecStartEPNS_16PreRecStartParamE`, `NonRealTimeMeta`, `intervalRec` |
| `fx6_libmpr` | FX6 `libmpr.so` | `28,921,824` | `139` | `_ZN5MprIf11PreRecStartEPNS_16PreRecStartParamE`, `NonRealTimeMeta`, `intervalRec` |
| `fx3_cpapp` | FX3 `cpapp-b.bin` | `15,980,568` | `172` | `SET_INTERVAL_REC`, `SET_INTERVAL_REC_AE_SMOOTHING_END`, `CheckSetIntervalRecExecState` |
| `fx6_cpapp` | FX6 `cpapp-b.bin` | `17,952,816` | `147` | `SET_INTERVAL_REC`, `GetCaptureIntervalResource`, `InfraBB::Async::ChkSetIntervalRecParam` |
| `fx6_libinfra_ftp` | FX6 `libInfraFtpClient.so` | `231,816` | `1,296` | `InfraFtpClient_Init`, `CT_ERR_PASV_NOT_SUPPORT`, `FT_ERR_FAIL_AUTH_CACERT`, `CT_ID_ASYNC_REQ_RESUME_FTP_TRANSFER`, `TLS_AES_256_GCM_SHA384`, `OPENSSL_3`, `CWD` |
| `fx6_libnet_ether` | FX6 `libNetServiceEther.so` | `175,376` | `1,016` | `EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE`, `WiredLanResource_SendReq_CT_ID_SYNC_REQ_START_USB_ETHER`, `UIBizAPI_SendEvent_CT_ID_EVENT_LINKUP_WIRED_ETHER_NETWORK` |
| `fx3_global_xdb` | FX3 `global.xdb` (`uxa\x07`) | `11,664` | `1,724` | `uxa\x07` container parsed read-only |
| `fx6_global_xdb` | FX6 `global.xdb` (`uxa\x07`) | `1,792` | `1,792` | `uxa\x07` container parsed read-only |
| `fx3_str_en` | FX3 English `ns=39` `.uxc` | `165,740` | `1,904` | `0x0000E100` (`Wired LAN`), `0x0000E39A` (`WireLAN(USB-LAN)`) |
| `fx3_str_en_g` | FX3 English `ns=3` `.uxc` | `69,600` | `2,520` | `0x000061C8` (`Interval shooting...`), `0x0000645F` (`USB-LAN/Tethering`), `0x000064BF` (`FTP Transfer`) |
| `fx6_str_en_1` | FX6 English `ns=1` `.uxc` | `118,208` | `8,036` | `0x00002554` (`Cache Size`), `0x00002E7D` (`Cache Rec`), `0x00002F27` (`Interval Rec Number of Frames`), `0x00002F61` (`File Transfer Auto Upload (Proxy)`) |
| `fx6_str_en_2` | FX6 English `ns=2` `.uxc` | `118,676` | `9,812` | `0x00004247` (`Interval Rec`), `0x0000424C` (`Picture Cache Rec`), `0x000042D3` (`Airplane Mode`), `0x0000457C` (`Cache Rec Time`), `0x000052E9` (`File Transfer Status`) |

---

## 4. Technical Pillar Breakdown / 四大审计支柱详情

### Pillar 1 — Interval Recording (`1s..60s`) & Electronic-Shutter Wear Firewall
- **Boundary Enforcement**: Validates `interval_sec` in `[1, 60]` and `shot_count` in `[1, 9999]`, rejecting out-of-range parameters cleanly (`0` crashes).
- **Zero Mechanical Curtain Wear**: Enforces `ELECTRONIC_SHUTTER` across all interval sequences (`mech_shutter_actuations == 0`), blocking `MECHANICAL_SHUTTER` requests with `BLOCKED_MECH_SHUTTER_WEAR_FIREWALL`.
- **Day-to-Night AE Ramp Stabilization**: Simulates step-by-step exposure tracking (`simulate_day_to_night_ae_step_ev`) across sunset `-6.0 EV` transitions under `LOCK`, `LOW`, `MID`, and `HIGH` sensitivity, verifying monotonic damping (`LOW` max per-step change `< MID < HIGH`).
- **Frame-Packing vs Still Sequence**: Distinguishes FX6 `SINGLE_CLIP_FRAME_PACK` (`in_camera_movie_assembly=True`, `audio_enabled=False`) from FX3 `STILL_SEQUENCE` (`Interval Shoot Func.`, `in_camera_movie_assembly=False`), while explicitly flagging invalid single-clip audio combinations.

### Pillar 2 — Picture Cache (`Pre-Rec`) Circular DDR Ring-Buffer Budget on FX3 `2048 MiB` DRAM
- **DRAM Budget Partition**:
  - Total AP DRAM: `2048.0 MiB`
  - Fixed Reservations: Kernel/DMA (`384.0 MiB`) + `appFw`/`libmpr`/`ux` (`640.0 MiB`) + `GPE0`/Codec (`384.0 MiB`) + OOM Safety Guard (`256.0 MiB`) = `1664.0 MiB`
  - **Net Ring-Buffer Headroom**: **`384.0 MiB`**
- **Codec Clamp Matrix**:
  - `XAVC-I 4K60` (`600 Mbps = 75.0 MiB/s`): Clamped max `5.0 s` (`375.0 MiB` <= `384.0 MiB`); unclamped `10s..16s` (`750..1200 MiB`) fails closed (`BLOCKED_DDR_OOM_RISK`).
  - `XAVC-I 4K24` (`240 Mbps = 30.0 MiB/s`): Clamped max `12.0 s` (`360.0 MiB`).
  - `XAVC-L 4K30` (`100 Mbps = 12.5 MiB/s`) & `XAVC-L FHD60` (`50 Mbps = 6.25 MiB/s`): Full `16.0 s` (`200.0 MiB` / `100.0 MiB`).
- **Mutual Exclusions**: Auto-disables Picture Cache (`PICTURE_CACHE_AUTO_DISABLED_IN_MODE`) under `S&Q`, `HDMI RAW16`, `Interval Rec`, `Simul Rec`, and `Proxy Rec`.

### Pillar 3 — Wired USB-LAN FTP/FTPS & `P12` `00342260` RF-Off / Path-Traversal Firewall
- **Wired `CDC-NCM / RTL8153` Only**: Enforces `p12_airplane_mode == True`, `wlan_rf_enabled == False`, `bt_rf_enabled == False`, and `hci_tx_packets == 0`, proving `WF-12 00342260` immunity (`wf12_00342260_immune == True`) while blocking `WLAN`, `BT_PAN`, or any active RF leakage.
- **FTPES Security & Resume**: Enforces explicit TLS (`FTPES_TLS12` / `FTPES_TLS13`) with verified CA certificates (`root_cert_verified == True`), passive `PASV` data channel (blocking active `PORT`), byte-exact SHA-256 `REST` resume offset verification, and `OK / KEEP` Clip Flag filtering across `PROXY_ONLY`, `ORIGINAL_ONLY`, and `PROXY_AND_ORIGINAL`.
- **Path-Traversal & `p1..p15` Containment**: Strictly validates normalized paths against removable media roots (`/mnt/sd`, `/mnt/cfexpress_a`, `/mnt/cfexpress_b`, `/mnt/slot_a`, `/mnt/slot_b`), blocking `..`, NUL bytes, and `/dev/mmcblk0p1..p15` or `/dev/nflasha*` / `/dev/cnflasha*`.

### Pillar 4 — Calibration / eMMC Zero-Mutation Proof & `NonRealTimeMeta v2.20` XML Parity
- Hard-blocks persistent write attempts to `p2:/Backup.bin`, `p2:/psd.bin`, `/dev/nflasha*`, `/dev/cnflasha*`, and `/dev/mmcblk0p*` while permitting volatile `/tmp/` / `ram://` shadow configs (`calibration_mutation_bytes == 0`, `emmc_mutation_bytes == 0`).
- Generates and round-trip parses pure-Python `NonRealTimeMeta v2.20` (`urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20`) XML carrying `<IntervalRecording>` and `<PictureCache>` + `<NetworkTransfer>` metadata tags with deterministic SHA-256 verification.

---

## 5. Owned File Inventory (7 Files) / 本阶段交付文件清单

1. [`reports/2026-11-14-global-sony-wave10-interval-cache-ftp-intel/README.md`](../2026-11-14-global-sony-wave10-interval-cache-ftp-intel/README.md)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/interval_cache_and_ftp_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/interval_cache_and_ftp_auditor.py)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md)
6. [`outputs/fx3-firmware-lab/tests/test_interval_cache_and_ftp_auditor.py`](../../outputs/fx3-firmware-lab/tests/test_interval_cache_and_ftp_auditor.py)
7. [`reports/2026-11-14-phase93-interval-cache-ftp-auditor/README.md`](./README.md)
