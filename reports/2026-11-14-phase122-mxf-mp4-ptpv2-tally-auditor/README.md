# Phase 122 — 24th Unified `fx3-firmware-lab` Auditor: XAVC MXF OP1a (FX6) vs MP4 ISO-BMFF (FX3) Container Essence / SMPTE UMID / KLV RDD-18 Metadata Translator, SMPTE ST 2059-2 PTPv2 Frame-Phase Sync, & Wired P12-Safe TSL UMD v5.0 Tally Bridge
# 第 122 阶段 — 第 24 个统一 `fx3-firmware-lab` 审计器：XAVC MXF OP1a（FX6）与 MP4 ISO-BMFF（FX3）容器精华 / SMPTE UMID / KLV RDD-18 元数据转换器、SMPTE ST 2059-2 PTPv2 帧相位同步与有线 P12 安全 TSL UMD v5.0 Tally 桥接审计器

- **Date / 日期**: 2026-11-14
- **Schema / 架构版本**: `fx3_firmware_lab_phase122_mxf_mp4_ptpv2_tally_v1` (`122.0.0`)
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py)
- **CLI Subcommand / CLI 子命令**: `audit-mxf-mp4-tally` (and 24th auditor inside `audit-all`)
- **Related Wave-14 Research / 关联情报报告**: [`reports/2026-11-14-global-sony-wave14-mxf-ptpv2-tally-unbrick-intel/README.md`](../2026-11-14-global-sony-wave14-mxf-ptpv2-tally-unbrick-intel/README.md)

---

## English Technical Report

### 1. Executive Summary & Clean-Room Compliance

Phase 122 delivers the **24th unified clean-room auditor** (`mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py`) for the Sony `ILME-FX3` (`v7.02`) + `ILME-FX6` (`v6.01`) Cinema Line firmware compatibility lab, grounded in the Wave-14 live global web intelligence sync.

- **Zero Embedded Keys / Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`)**: In Local Donor mode (`LOCAL_DONOR_VERIFIED`), the auditor inspects 12 local FX3 `v7.02` & FX6 `v6.01` donor binaries (`appFw.so`, `libmpr.so`, `libInfraPtpControl.so`, `libNetServiceEther.so`), `global.xdb` (`uxa\x07`) registries, and `.uxc` string packs strictly via `os.O_RDONLY` and section-scoped `.rodata`/`.dynstr` `mmap.ACCESS_READ` scans without creating `.pyc` or mutating any file on disk.
- **Deterministic Clean-Room Fallback (`CLEAN_ROOM_SYNTHETIC`)**: Under `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or missing donor files, `build_clean_room_mxf_mp4_ptpv2_tally_fixtures()` synthesizes self-contained ELF64, `global.xdb`, and `.uxc` fixtures carrying all verified contract markers and runs the identical four-pillar verification pipeline (`0.0015 s` warm, zero proprietary donor files required).

### 2. Verified Observed Metrics & Dual-Mode Digests

| Metric | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) |
| --- | --- | --- |
| Phase 122 `all_checks_passed` | `True` (`errors = ()`) | `True` (`errors = ()`) |
| Phase 122 Standalone Runtime | `0.0993 s` cold / `0.0905 s` warm (`< 0.35 s`) | `0.0016 s` cold / `0.0015 s` warm (`< 0.02 s`) |
| Phase 122 `report_sha256` | `a9eb7646411a9505b14b680d2ae506b90058b764a518779e7791b40e9cd0f93b` | `47407e77114880650a91035ddb9b2ee3e9c8e5cd797c16198d117de72699c3b2` |
| `audit-all --json` Verdict | `24/24` green in `9.333 s` | `24/24` green in `0.514 s` |
| Full Lab `unittest` Suite | `713` tests OK in `23.958 s` | `713` tests OK in `13.118 s` |
| Phase 122 Unit Tests (`test_mxf_mp4_essence_ptpv2_and_tally_umd.py`) | `40` tests OK in `0.710 s` | `40` tests OK in `0.397 s` |
| `scripts/run_all_lab_tests.py --clean-only` | — | `CLEAN / ALL GREEN` in `1.37 s` |

#### Verified Donor File Sizes (`os.O_RDONLY`)
- `fx3_appfw`: `79,015,712` B | `fx6_appfw`: `50,520,424` B
- `fx3_libmpr`: `3,517,008` B | `fx6_libmpr`: `28,921,824` B
- `fx6_libinfra_ptp`: `152,520` B | `fx6_libnet_ether`: `175,376` B
- `fx3_global_xdb`: `11,664` B | `fx6_global_xdb`: `1,792` B
- `fx3_str_en`: `165,740` B | `fx3_str_en_g`: `69,600` B | `fx6_str_en_1`: `118,208` B | `fx6_str_en_2`: `118,676` B

### 3. Four-Pillar Technical Architecture

1. **Pillar A — `FX6 MXF OP1a` (`libXavcMxf`) <-> `FX3 MP4 ISO-BMFF` (`rtmd` / `SPVC`) Lossless Essence, SMPTE `UMID`, & KLV `RDD-18` Bridge**:
   - Verified ELF64 donor markers across FX6 `libmpr.so` (`_ZN10libXavcMxf11SetClipNameEjRA4_KN3mpr13ClipNameParamE`, `MuxMxfFnlzPrm_GetVideoCompression`, `GetCubeFilePathForMXF`, `setMetaData_ExposureIndexRDD18`, `setMetaData_CaptureGammaRDD18`, `_ZN3mpr4UMID15CreateBasicUMIDEv`), FX3 `libmpr.so` (`GetCubeFilePath`, `SPVC`, `PrepareInitialVectorAndSPVCBoxData`, `defStruct2sidb_CaptureGammaEquation`, `SetRealTimeMetaSampleInfo`, `CreateBasicUMID`), and FX6 `appFw.so` (`VAL_setting_codec_category_CODEC_CATEGORY_XAVC_MXF`, `get_pair_UMID_unique_id_of_opposite_slot_with_current_unique_id`).
   - Preserves 32-byte SMPTE ST 330 Basic `UMID` across lossless `XAVC-I` (`AVC480_*_H422IP`) <-> `XAVC S-I` (`MP4`) rewraps while deterministically regenerating UMIDs on transcode (`XAVC_HS_HEVC`).
   - Encodes and CRC32-verifies SMPTE RDD-18 / MP4 `rtmd` KLV packets (`ExposureIndex`, Base ISO `800/12800`, `CaptureGammaEquation` UL for `S-LOG3` / `REC709` / `REC2100-HLG`, `CaptureColorPrimaries`, FPS, F-number, Shutter Angle, WB Kelvin, and `.cube` LUT path).
   - Blocks `SPVC` (`sony.private_cert.v1`) signature spoofing (`BLOCKED_SPVC_CERT_SPOOFING`), blocks un-translated raw `MXF_OP1A` writes onto FX3 `MP4` `M4ROOT/CLIP` slots (`BLOCKED_RAW_MXF_OP1A_ON_MP4_SLOT`), and rejects cross-codec lossless rewraps and CRC mismatches.

2. **Pillar B — `SMPTE ST 2059-2` (`IEEE 1588-2008 PTPv2`) Frame-Phase Sync vs Multi-Terminal `LTC` (`SMPTE 12M`) over Wired `USB-LAN` (`P12`)**:
   - Strictly separates `SMPTE ST 2059-2` `PTPv2` synchronization from Sony `PTP-IP` (`TCP/15740`) camera control (`BLOCKED_PTPIP_NOT_IEEE1588_PTPV2`).
   - Converts `PTPv2` TAI epoch nanoseconds (subtracting the `37 s` TAI-UTC offset) into rational frame indices and drop-frame/non-drop-frame `SMPTE 12M` `HH:MM:SS:FF` / `HH:MM:SS;FF` timecodes across `23.976`..`59.94 fps` (`29.97 DF` / `59.94 DF` `;02` minute boundary rule enforced).
   - Enforces `<= 1.0 us` HW timestamping / `<= 250.0 us` SW timestamping jitter ceilings and `<= 500.0 us` Multi-Terminal `LTC` (`VMC-BNCM1`) phase alignment drift bounds.
   - Binds exclusively to wired `USB-LAN` (`CDC_NCM_RTL8153`, `CDC_NCM_AX88179`, `USB_RNDIS_WIRED`) under strict `P12` Wi-Fi-OFF (`wf12_00342260_risk == 0`), failing closed on `WIFI_WLAN0` / `BT_PAN` and blocking `VMC-BNCM1` attachment during `H0` / `uart_boot` (`BLOCKED_VMC_BNCM1_DURING_UART_BOOT`).

3. **Pillar C — Studio `TSL UMD v5.0` (UDP `40003`/`8900`, TCP `5727`/`5728`) Red (`PGM`) / Green (`PVW`) Tally & `16-char` UMD Bridge onto FX3 Hardware**:
   - Implements bit-exact little-endian `TSL UMD v5.0` (`VER=0`) wire framing (`PBC`, `FLAGS` ASCII/UTF-16LE, `SCREEN`, `<DMSG>` `INDEX`, `CONTROL` RH/Text/LH tally + brightness, `LENGTH`, `TEXT`), `<= 2048 B` UDP guard, and TCP `DLE/STX` (`0xFE 0x02`) + `0xFE -> 0xFE 0xFE` byte-stuffing (verified even on `screen=0x00FE` / `index=0x00FE`).
   - Strips ANSI/control characters and clamps dynamic UMD camera labels to `16` printable characters (`sanitize_umd_label_16`).
   - Enforces FX3 single-color Red LED hardware truth (`sequence_set_tally_status`): `RED (PGM=1)` turns FX3 physical Front+Rear Red Tally LEDs `ON` + `RED` OSD border; `GREEN (PVW=2)` keeps FX3 physical Red LEDs strictly `OFF` (zero false on-air Red leak!) while rendering a `GREEN` OSD preview border (`fx6_green_gpio_faults == 0` for FX6-only `BKID_APP_SETTING_G_TALLY_LAMP` / `0x000025BE`); `AMBER (3)` renders `AMBER` OSD border with Red LEDs `OFF`; `OFF (0)` clears LEDs and OSD border; all wired-only under `P12` (`wf12_00342260_risk == 0`).

4. **Pillar D — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration Mutation Proof**:
   - Validates FX3 & FX6 `global.xdb` (`uxa\x07`) read-only, allows only `/tmp/`, `ram://`, and `memory://` staging paths, and fail-closed blocks `/mnt/sd/BODYDATA.DAT`, `/dev/nflasha15`, `/dev/cnflasha0`, `/dev/mmcblk0rpmb`, `/dev/mtdblock*`, `p2:/setting/Backup.bin`, `psd.bin`, `defdet.bin`, `jiritsu`, `updater://`, `nvram://`, and `eeprom://` (`emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`).

---

## 中文技术报告

### 一、 摘要与净室只读合规性

第 122 阶段基于第十四波全球实时情报同步，完成并集成了 `fx3-firmware-lab` 的 **第 24 个统一净室审计器**（[`mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py)）。

- **零内置密钥 / 严格只读（`os.O_RDONLY` + `mmap.ACCESS_READ`）**：本地供体模式仅以 `os.O_RDONLY` 与 `mmap.ACCESS_READ` 扫描 FX3 `v7.02` 与 FX6 `v6.01` 的 12 个核心二进制、`.uxc` 语言包与 `global.xdb`（`uxa\x07`），绝不产生任何持久化修改或 `.pyc` 缓存污染。
- **确定性净室回退（`CLEAN_ROOM_SYNTHETIC`）**：当设置 `FX3_FX6_FORCE_CLEAN_ROOM=1`、`--clean-room` 或本地供体缺失时，自动合成完整 ELF64 / `global.xdb` / `.uxc` 夹具并运行完全一致的四支柱验证流水线（热运行仅 `0.0015 秒`）。

### 二、 实测指标与双模式验证结果

- **本地供体全量测试**：`713` 项单元测试全部通过（耗时 `23.958s`），`audit-all --json` **`24/24` 全绿**（耗时 `9.333s`，Phase 122 报告 SHA-256：`a9eb7646411a9505b14b680d2ae506b90058b764a518779e7791b40e9cd0f93b`）。
- **强制净室全量测试**：`713` 项单元测试全部通过（耗时 `13.118s`），`audit-all --json` **`24/24` 全绿**（耗时 `0.514s`，Phase 122 报告 SHA-256：`47407e77114880650a91035ddb9b2ee3e9c8e5cd797c16198d117de72699c3b2`）。
- **Phase 122 专项单元测试**：`40` 项双模式测试在本地模式（`0.710s`）与净室模式（`0.397s`）下均全通过；`scripts/run_all_lab_tests.py --clean-only` 检查 `CLEAN / ALL GREEN`（`1.37s`）。

### 三、 四支柱核心架构与防砖契约

1. **支柱 A — `FX6 MXF OP1a` 与 `FX3 MP4 ISO-BMFF` 无损转封装、SMPTE `UMID` 与 `RDD-18 / rtmd` 转换器**：校验 `libXavcMxf` / `GetCubeFilePathForMXF` / `setMetaData_ExposureIndexRDD18` / `setMetaData_CaptureGammaRDD18` 与 FX3 `SPVC` / `SetRealTimeMetaSampleInfo` 符号契约；在 `XAVC-I` <-> `XAVC S-I` 无损重打包时严格保持 32 字节 SMPTE `UMID`，跨编码转码时确定性重新生成 `UMID`；构建并 CRC32 校验 `RDD-18 / rtmd` 元数据包；禁止伪造 `SPVC` 签名，禁止将未转换的裸 `.MXF` 直接写入 FX3 `MP4` 卡槽。
2. **支柱 B — `SMPTE ST 2059-2 PTPv2` 与多接口 `LTC` 相位对齐（有线 `USB-LAN` / `P12`）**：严格隔离 `ST 2059-2 PTPv2` 与 `PTP-IP (TCP/15740)` 控制协议；完成 TAI 纳秒（扣除 `37s` TAI-UTC 闰秒偏移）向 `23.976..59.94 fps` 丢帧/非丢帧 `SMPTE 12M` 时间码的精确换算；强制硬件时间戳抖动 `<= 1.0 us`、软件时间戳抖动 `<= 250.0 us`、Multi-Terminal `LTC` (`VMC-BNCM1`) 相位漂移 `<= 500.0 us`；严格绑定有线 `CDC-NCM / RNDIS`（`wf12_00342260_risk == 0`），并在 `uart_boot` 期间阻断 `VMC-BNCM1` 接入。
3. **支柱 C — 演播室 `TSL UMD v5.0`（UDP `40003/8900`、TCP `5727/5728`）红/绿 Tally 与 16 字符 UMD 硬件安全桥接**：完整实现小端序 `TSL UMD v5.0` 线协议、UDP `<= 2048 B` 上限保护与 TCP `DLE/STX (0xFE 0x02)` 双 `0xFE` 转义；清洗 ANSI 控制符并截断至 `16` 字符；遵循 FX3 物理单红灯硬件真实性——`Red (PGM)` 点亮前/后红色 Tally LED 与红色 OSD 边框，而 `Green (PVW)` 保持物理红灯**严格熄灭**（杜绝误亮红灯造成播出事故）并仅渲染绿色 OSD 边框（零缺失 FX6 `G Tally Lamp` GPIO 报错）。
4. **支柱 D — 易失性 RAM 暂存与持久 `eMMC` / 校准分区零写入证明**：只读校验双方 `global.xdb`，仅放行 `/tmp/`、`ram://`、`memory://`，硬阻断 `BODYDATA.DAT`、`/dev/nflasha15`、`/dev/cnflasha0`、`Backup.bin`、`psd.bin`、`defdet.bin` 与 `jiritsu`（`emmc_mutation_bytes == 0`、`calibration_mutation_bytes == 0`）。

---

## Owned 7-File Inventory / 本阶段七文件交付清单

1. [`reports/2026-11-14-global-sony-wave14-mxf-ptpv2-tally-unbrick-intel/README.md`](../2026-11-14-global-sony-wave14-mxf-ptpv2-tally-unbrick-intel/README.md) — Wave-14 live global web intelligence report (EN/ZH-CN, cited URLs)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py) — 24th unified `fx3-firmware-lab` auditor
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) — Phase 122 symbol exports and `__all__`
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) — `audit-mxf-mp4-tally` CLI subcommand & 24th auditor in `run_audit_all`
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md) — Phase 122 documentation & CLI usage examples
6. [`outputs/fx3-firmware-lab/tests/test_mxf_mp4_essence_ptpv2_and_tally_umd.py`](../../outputs/fx3-firmware-lab/tests/test_mxf_mp4_essence_ptpv2_and_tally_umd.py) — 40 dual-mode unit tests
7. [`reports/2026-11-14-phase122-mxf-mp4-ptpv2-tally-auditor/README.md`](README.md) — Phase 122 bilingual technical report
