# Milestone Phase 105: 20th Unified Auditor — C2PA 2.1 Camera Authenticity / `cnflasha` Key-Vault Firewall, E-Mount Lens Shading / Vignetting / Lateral CA / Distortion Polynomials, Sony Monitor & Control Wired USB-LAN PTP-IP Multi-Cam Fleet Isolation, & Per-Body Factory Shading Immutability

# 里程碑 Phase 105：第 20 号统一审计器 — C2PA 2.1 相机真实性 / `cnflasha` 密钥库零触碰防火墙、E 卡口镜头阴影/暗角/横向色差/畸变多项式补偿、Sony Monitor & Control 有线 USB-LAN PTP-IP 四机位舰队隔离与单机原厂校准不可变性证明

- **Date / 日期**: 2026-11-14
- **Phase / Schema**: `105.0.0` / `fx3_firmware_lab_phase105_c2pa_shading_mc_fleet_v1`
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/c2pa_lens_shading_and_mc_fleet_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/c2pa_lens_shading_and_mc_fleet_auditor.py)
- **Test Suite / 测试集**: [`outputs/fx3-firmware-lab/tests/test_c2pa_lens_shading_and_mc_fleet.py`](../../outputs/fx3-firmware-lab/tests/test_c2pa_lens_shading_and_mc_fleet.py) (40 dual-mode unit tests / 40 项双模式单元测试)
- **CLI Entrypoint / 命令行入口**: `python3 -B -m fx3_firmware_lab audit-c2pa-shading-mc [--clean-room] [--json]` (also wired into `audit-all` 20/20)
- **Safety Posture / 安全边界**: Strictly `os.O_RDONLY` + `mmap.ACCESS_READ`, `0` eMMC/NVRAM writes, `0` key extraction, `0` port-8768 modifications, `0` WF-12 RF hits (`P12` Airplane Mode locked ON).

---

## 1. Executive Summary & Dual-Mode Verification Results / 执行摘要与双模式验证结果

Phase 105 adds the **20th unified clean-room auditor** to `fx3_firmware_lab`, closing four critical cinematography, security, and fleet-control domains across **FX3 v7.02** and **FX6 v6.01**, while integrating **Wave-11 live web intelligence** (`reports/2026-11-14-global-sony-wave11-c2pa-mcfleet-unbrick-intel/README.md`).

| Verification Mode / 验证模式 | Cold Runtime / 冷启动耗时 | Warm Runtime / 热启动耗时 | Deterministic `report_sha256` | Result / 结果 |
| --- | ---: | ---: | --- | --- |
| **Local Donor (`LOCAL_DONOR_VERIFIED`)** | **0.2792 s** (`< 0.35s`) | **0.2624 s** | `f607b2a8468edddfdb1b4bd6dc6d3fefa58bd4ed0e7c1aacfdbb3ded93aff5bb` | **ALL CHECKS PASSED** |
| **Clean-Room (`CLEAN_ROOM_SYNTHETIC`)** | **0.0024 s** (`< 0.02s`) | **0.0023 s** | `a2a8f24ba0921bf280b8629540a37098b3bc935d34acc3a30f7162a6609354a7` | **ALL CHECKS PASSED** |
| **Phase 105 Unit Tests (Local Donor)** | — | **0.537 s** (40 tests) | — | **40/40 OK** |
| **Phase 105 Unit Tests (`FX3_FX6_FORCE_CLEAN_ROOM=1`)** | — | **0.248 s** (40 tests) | — | **40/40 OK** |
| **Full Lab Suite (Local Donor)** | **19.611 s** (553 tests) | — | — | **553/553 OK** |
| **Full Lab Suite (`FX3_FX6_FORCE_CLEAN_ROOM=1`)** | **10.175 s** (553 tests) | — | — | **553/553 OK** |
| **`audit-all --json` (Both Modes)** | — | — | — | **20/20 GREEN** |
| **`scripts/run_all_lab_tests.py --clean-only`** | **0.04 s** | — | — | **ALL GREEN** |

### Local Donor Binary & Asset Sizes Inspected Strictly via `os.O_RDONLY` / 只读扫描本地固件尺寸统计

| Artifact Key | Local Donor Bytes | Clean-Room Fixture Bytes | Verified Targets / Markers |
| --- | ---: | ---: | --- |
| `fx3_appfw` (`appFw.so`) | `79,015,712` | `1,235` | `InfraC2PA` (7), Lens Comp (9), USB-LAN/PTP/P12 (6) |
| `fx6_appfw` (`appFw.so`) | `50,520,424` | `1,293` | `InfraC2PA`/C2PA status (5), BKID/PID Lens Comp (11), PTP-IP/AccessAuth/P12 (7) |
| `fx3_libmpr` (`libmpr.so`) | `3,517,008` | `351` | `CheckDigitalSignature`, `GetDigitalSignatureInfoForMovie`, `(C2PA+SSIG)`, `DistortionCorrection`, `lc2pa.createdlsony.created`, `InfraC2PA.cpp` |
| `fx6_libmpr` (`libmpr.so`) | `28,921,824` | `310` | Shared `libmpr` C2PA/SSIG & `UDAMSetDistortionCorrectionValue` markers |
| `fx3_cpapp` (`cpapp-b.bin`) | `15,980,568` | `224` | `FW: SET_*_CORRECTION`, `fixed_lensfile`, `ExtractFromCombinedLensData`, `/setting/defdet.bin` |
| `fx6_cpapp` (`cpapp-b.bin`) | `17,952,816` | `224` | Shared CP optical compensation & `/setting/defdet.bin` markers |
| `fx6_libcert_mgr` (`libCertificateManager.so`) | `198,880` | `89` | `Certificate`, `ECDSA`, `SHA256` |
| `fx6_libinfra_ptp` (`libInfraPtpControl.so`) | `152,520` | `126` | `PTPT_init_ip`, `_ptpt_close_ip_remote`, `ptp_make_dat_header_packet` |
| `fx6_libnet_ether` (`libNetServiceEther.so`) | `175,376` | `70` | `ETHER` |
| `fx3_global_xdb` / `fx6_global_xdb` | `11,664` / `1,792` | `1,724` / `1,792` | `uxa\x07` menu & node validation |
| `fx3_str_en` / `fx3_str_en_g` | `165,740` / `69,600` | `548` / `2,728` | `.uxc` ns=39 (`Wired LAN`), ns=3 (`Digital Signature`, `Lens Comp.`, `Signature Type: On(C2PA)`) |
| `fx6_str_en_1` / `fx6_str_en_2` | `118,208` / `118,676` | `7,652` / `11,356` | `.uxc` ns=1 (`Access Authentication`, `Wired LAN Cam. Remote Ctrl`, `Certificate for C2PA`), ns=2 (`Distortion Comp.`, `Shading Compensation`) |

---

## 2. Four-Pillar Technical Breakdown / 四大审计支柱技术细节

### Pillar 1 — C2PA 2.1 Camera Authenticity & `cnflasha` Key-Vault Zero-Touch Firewall
**支柱一：C2PA 2.1 相机真实性与 `cnflasha` 密钥库零触碰防火墙**

1. **ISO-BMFF JUMBF Provenance Validation / ISO-BMFF JUMBF 溯源盒解析**：
   - `build_c2pa_jumbf_box()` & `parse_c2pa_jumbf_box()` construct and validate C2PA 2.1 `jumb`/`jumd`/`c2ma`/`c2cl`/`c2as`/`c2cs` boxes with canonical UUID `6332706100110010800000aa00389b71` and 32-byte SHA-256 hard bindings.
2. **Read-Only `cnflasha`/RPMB Firewall / `cnflasha`/RPMB 只读防火墙**：
   - Stock FX3 v7.00–7.02 hardware C2PA video signing is audited under strict `O_RDONLY` key-vault access (`0` writes, `0` key extractions), enforcing FX3 public constraints (`MP4 <= 222 Mbps`, `S&Q` mode excluded, `<= 100` `RQ_LIC.DAT` licenses).
   - Stage-B userland overlays (`STAGE_B_USERLAND_OVERLAY`) are transparently labeled `STAGE_B_CLEAN_ROOM_RESEARCH_OVERLAY_UNVERIFIED_UNSIGNED` with `c2pa_hardware_signature_written = False` (`c2cs` absent).
   - Any `O_RDWR`/write against `/dev/cnflasha*`, `/dev/mmcblk0rpmb`, `p12:/cert`, `RQ_LIC.DAT`, forged Stage-B `c2cs` signature, or cross-body FX3→FX6 cert spoofing is blocked (`BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION`, `BLOCKED_FORGED_C2PA_SIGNATURE_ON_STAGE_B_OVERLAY`, `BLOCKED_CROSS_BODY_CERT_SPOOF`).

### Pillar 2 — E-Mount 12-Pin Lens Shading, Lateral CA & Distortion Polynomials
**支柱二：E 卡口 12 针镜头阴影/横向色差/畸变多项式补偿与无触点手动头 1.0x 安全回退**

1. **Radial $\cos^4(\theta)$ Vignetting / 径向暗角补偿**：
   - Models IMX510 full-frame half-diagonal ($21.633\,\text{mm}$, $4096\,\text{px}$ width) illumination falloff and clamps digital gain to $\le 4.0\times$ (`+2.0 EV`). Across `SEL1635GM2_16MM` (`theta_max = 32.5°`), `AUTO` yields `shading_gain_corner = 2.298184` with `corner_uniformity_error = 0.0 < 1e-6` and monotonic $g_{\text{corner}} > g_{\text{mid}} > g_0$.
2. **Lateral Chromatic Aberration & Distortion / 横向色差与径向畸变逆解**：
   - R/B lateral CA micro-scale polynomials achieve **`99.7052%`** (`0.997052 >= 0.95`) fringe reduction with residual $< 0.15\,\text{px}$.
   - Newton-Raphson inversion of $r_d = r(1 + k_1 r^2 + k_2 r^4)$ recovers barrel (`SEL1635GM2_16MM`, `SEL50F12GM`) and pincushion (`SEL70200GM2_200MM`) coordinates to **`0.00e+00`** (`< 1e-8`).
3. **Unchipped PL / Anamorphic Fail-Safe / 无触点 PL 与变形宽银幕镜头 1.0x 严格直通**：
   - For `UNCHIPPED_PL_CINE_PRIME` and `MANUAL_ANAMORPHIC_2X` (`mount_pins_detected = False`), compensation strictly locks to `IDENTITY_1X` (`1.0x` gain, CA/distortion disabled). Attempting `force_stale_coefficients=True` fails closed (`BLOCKED_STALE_ELECTRONIC_LENS_COEFF_ON_UNCHIPPED_LENS`).

### Pillar 3 — Sony Monitor & Control Wired USB-LAN PTP-IP 4-Cam Fleet & `P12` Isolation
**支柱三：Sony Monitor & Control 有线 USB-LAN PTP-IP 四机位矩阵与 `P12` 射频关闭隔离**

- **4-Cam Mixed FX3 + FX6 Matrix / 四机位混合拓扑**：Verifies `WIRED_LAN_SWITCH_OR_ROUTER` topology using verified `CDC_NCM_RTL8153` / `CDC_NCM_UE300C_V2` / `BELKIN_USBC_ETH` USB-LAN adapters, `PTP-IP` (`TCP/15740`, `80`-byte UTF-16LE `Init_Command_Request` packet round-trip), `Access Authentication = ON`, total telemetry bitrate `32.8 Mbps` (`<= 300.0 Mbps`), synchronized `False Color` / `Waveform` / `Focus Map`, and gang `REC` trigger skew `5.3 ms` (`<= 16.7 ms`).
- **Strict `P12` RF Fence / `P12` 射频静默隔离**：Requires `p12_airplane_mode_on = True`, `wifi_rf_enabled = False`, `bt_rf_enabled = False`, `hci_tx_packets = 0`, `wf12_00342260_hits = 0`.
- **Unsupported Topology Guard / 不支持拓扑拦截**：Blocks `DIRECT_ETHERNET_NO_ROUTER` (per Sony M&C wired LAN multi-cam hub requirement), `FX6_USB_TETHER_IPADOS` (unsupported on iPadOS), `> 4` cameras on `FREE_4CAM`, unauthenticated `PTP-IP`, duplicate IPs, and unverified NIC drivers.

### Pillar 4 — Per-Body Factory Shading & Defect-Pixel Map Bit-Exact Preservation Proof
**支柱四：单机原厂阴影图与坏点表逐比特（SHA-256）不可变性证明**

- Validates `fx3_global_xdb` & `fx6_global_xdb` `uxa\x07` integrity and verifies bit-exact SHA-256 equality (`factory_digests_before == factory_digests_after`) across all 6 factory calibration targets: `p2:/setting/psd.bin`, `p2:/setting/defdet.bin`, `p2:/setting/Backup.bin`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin`, and `p12:/cert`.
- Allows volatile `/tmp/` and `ram://` staging while blocking persistent writes and traversal (`calibration_mutation_bytes == 0`, `emmc_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`).
