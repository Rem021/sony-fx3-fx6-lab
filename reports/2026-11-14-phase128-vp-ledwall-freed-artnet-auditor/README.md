# Phase 128 — 25th Unified `fx3-firmware-lab` Auditor: Virtual Production LED-Volume Brompton/Megapixel PWM Anti-Banding Fractional ECS Solver, Wired FreeD (`0xD1` 29-Byte) Lens/Camera Tracking Telemetry -> Unreal `LiveLink`, & `P12`-Safe `Art-Net 4` / `sACN` Lighting-Cue Frame-Boundary Shutter-Sync Auditor
# 第 128 阶段 — 第 25 个统一 `fx3-firmware-lab` 审计器：虚拟制片 LED 墙 Brompton/Megapixel PWM 抗扫描条纹分数 ECS 求解器、有线 FreeD（`0xD1` 29 字节）镜头/相机追踪 -> Unreal `LiveLink` 遥测及 `P12` 安全 `Art-Net 4` / `sACN` 灯光帧边界同步审计器

- **Date / 日期**: 2026-11-14
- **Schema / 架构版本**: `fx3_firmware_lab_phase128_vp_ledwall_freed_artnet_v1` (`128.0.0`)
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/vp_ledwall_ecs_freed_and_artnet_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/vp_ledwall_ecs_freed_and_artnet_auditor.py)
- **CLI Subcommand / CLI 子命令**: `audit-vp-ledwall-freed` (and 25th auditor inside `audit-all`)
- **Related Wave-15 Research / 关联情报报告**: [`reports/2026-11-14-global-sony-wave15-vp-ledwall-freed-unbrick-intel/README.md`](../2026-11-14-global-sony-wave15-vp-ledwall-freed-unbrick-intel/README.md)

---

## English Technical Report

### 1. Executive Summary & Clean-Room Compliance

Phase 128 delivers the **25th unified clean-room auditor** ([`vp_ledwall_ecs_freed_and_artnet_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/vp_ledwall_ecs_freed_and_artnet_auditor.py)) for the Sony `ILME-FX3` (`v7.02`) + `ILME-FX6` (`v6.01`) Cinema Line firmware compatibility lab, grounded in the Wave-15 live global web intelligence sync.

- **Zero Embedded Keys / Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`)**: In Local Donor mode (`LOCAL_DONOR_VERIFIED`), the auditor inspects 12 local FX3 `v7.02` & FX6 `v6.01` donor binaries (`appFw.so`, `libmpr.so`, `libInfraLensCommunicator.so`, `libNetServiceEther.so`), `global.xdb` (`uxa\x07`) registries, and `.uxc` string packs strictly via `os.O_RDONLY` and section-scoped `.rodata`/`.dynstr`/`.data.rel.ro`/`.strtab` `mmap.ACCESS_READ` scans without creating `.pyc` or mutating any file on disk.
- **Deterministic Clean-Room Fallback (`CLEAN_ROOM_SYNTHETIC`)**: Under `FX3_FX6_FORCE_CLEAN_ROOM=1`, `--clean-room`, or missing donor files, `build_clean_room_vp_ledwall_freed_fixtures()` synthesizes self-contained ELF64, `global.xdb`, and `.uxc` fixtures carrying all verified contract markers and runs the identical four-pillar verification pipeline (`0.0017 s` warm, zero proprietary donor files required).

### 2. Verified Observed Metrics & Dual-Mode Digests

| Metric | Local Donor Mode (`LOCAL_DONOR_VERIFIED`) | Clean-Room Mode (`CLEAN_ROOM_SYNTHETIC`) |
| --- | --- | --- |
| Phase 128 `all_checks_passed` | `True` (`errors = ()`) | `True` (`errors = ()`) |
| Phase 128 Standalone Runtime | `0.1100 s` cold / `0.0852 s` warm (`< 0.35 s`) | `0.0022 s` cold / `0.0017 s` warm (`< 0.02 s`) |
| Phase 128 `report_sha256` | `ce1f00de54fe3bdc1a817d29d257a770ba79019c24a512f95ab4335db692a9e9` | `471e00df6cd2ef0d01e1e78701a06b56a2fc07b842ad89f929afb2945dfd99d5` |
| `audit-all --json` Verdict | `25/25` green in `8.856 s` | `25/25` green in `0.092 s` |
| Full Lab `unittest` Suite | `753` tests OK in `24.571 s` | `753` tests OK in `13.171 s` |
| Phase 128 Unit Tests (`test_vp_ledwall_ecs_freed_and_artnet.py`) | `40` tests OK in `0.598 s` | `40` tests OK in `0.392 s` |
| `scripts/run_all_lab_tests.py --clean-only` | — | `CLEAN / ALL GREEN` in `0.04 s` |

#### Verified Donor File Sizes (`os.O_RDONLY`)
- `fx3_appfw`: `79,015,712` B | `fx6_appfw`: `50,520,424` B
- `fx3_libmpr`: `3,517,008` B | `fx6_libmpr`: `28,921,824` B
- `fx3_lens_comm`: `14,544` B | `fx6_libnet_ether`: `175,376` B
- `fx3_global_xdb`: `11,664` B | `fx6_global_xdb`: `1,792` B
- `fx3_str_en`: `165,740` B | `fx3_str_en_g`: `69,600` B | `fx6_str_en_1`: `118,208` B | `fx6_str_en_2`: `118,676` B

### 3. Four-Pillar Technical Architecture

1. **Pillar A — Virtual Production LED-Volume (`Brompton Tessera SX40` / `Megapixel HELIOS`) `IMX510` Readout-Skew & Fractional `ECS` Safe-Shutter Solver**:
   - Verifies FX6 `appFw.so` (`BKID_APP_SETTING_ECS`, `EVENT_REMOTE_SHUTTER_ECS_FREQUENCY`, `VAL_setting_shutter_mode_SHUTTER_MODE_ECS`) and FX3 `appFw.so` (`ANTI_FLICKER_SET_HIGH_RES_SS_ON`, `HighResolutionShutterSpeedMode`) donor markers plus `.uxc` labels (`0x00002077` `ECS`, `0x000022DB` `ECS Frequency`, `0x0004E116` `Anti-flicker Tv Scan`).
   - Solves and audits fractional `ECS` frequencies across `23.98..7680.0 Hz` against LED carrier PWM (`960..7680 Hz`) and scan-multiplexing ratios (`1/1..1/32`) across `IMX510` readout windows (`8.70 ms` 4K FF, `13.20 ms` oversampled ref, `4.35 ms` 4K 120p, `2.20 ms` FHD 240p).
   - Enforces `harmonic_error_pct <= 0.50%`, effective exposure duration `>= T_mux` to eliminate sub-multiplex dark scanline banding (`BLOCKED_SUB_MULTIPLEX_SCANLINE_BANDING`), and explicit non-genlock beat warnings when `genlock_spg_locked=False`.

2. **Pillar B — Wired `FreeD` (`0xD1` 29-Byte UDP) E-Mount 12-Pin Lens Telemetry -> Unreal Engine `LiveLinkFreeD`**:
   - Verifies FX3 `libInfraLensCommunicator.so` (`0x00003880` / `14,544 B`) and FX3/FX6 `appFw.so` (`EVENT_REMOTE_ABSOLUTE_FOCUS_POSITION`, `EVENT_REMOTE_ZOOM_POSITION_SETTING`, `EVENT_REMOTE_IRIS_POSITION`, `libNetServiceEther.so` UDP/TCP markers).
   - Implements bit-exact 29-byte big-endian `0xD1` encoding/decoding (`Pan/Tilt/Roll` signed 24-bit `* 32768`, `X/Y/Z` signed 24-bit `* 64` mm, `Zoom/Focus` unsigned 24-bit `0..0xFFFFFF`, Sony 16-bit Spare carrying 12-bit Iris + 4-bit frame counter, modulo-256 `(0x40 - sum(pkt[0:28])) & 0xFF` checksum).
   - Rejects corrupted checksums, invalid packet lengths, un-chipped lenses lacking external FIZ encoders (`BLOCKED_NO_FIZ_ENCODER_ON_UNCHIPPED_LENS`), and wireless transports (`WIFI_WLAN0`, `BT_PAN`), binding strictly to wired `USB-LAN` (`CDC_NCM_RTL8153`, `CDC_NCM_AX88179`, `USB_RNDIS_WIRED`) with `wf12_00342260_risk == 0`.

3. **Pillar C — `Art-Net 4` (`UDP 6454`, `OpDmx 0x5000`, `ArtSync 0x5200`) & `sACN` (`ANSI E1.31`, `UDP 5568`) Frame-Boundary Shutter-Sync Guard (`P12`)**:
   - Synthesizes and verifies bit-exact `Art-Net 4 OpDmx` (15-bit Port-Address `Net/SubNet/Universe`, `ProtVer 14`, `ArtSync 0x5200` latch flag) and `ANSI E1.31 sACN` (`ASC-E1.17\0\0\0`, Universe `1..63999`, IPv4 multicast `239.255.H.L`, Priority `0..200`, `E1.31 Sync` lock).
   - Blocks mid-readout lighting flash/strobe tears inside the `8.7 ms` / `13.2 ms` `IMX510` readout interval (`BLOCKED_MID_READOUT_FLASH_TEAR`), multi-universe spatial tearing without `ArtSync`/`E1.31 Sync`, excessive cue jitter, and any wireless DMX transport (`wf12_00342260_risk == 0`).

4. **Pillar D — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration Mutation Proof**:
   - Validates FX3 & FX6 `global.xdb` (`uxa\x07`) read-only, permits only volatile RAM paths (`/tmp/`, `ram://`, `memory://`), and fail-closed blocks `/mnt/sd/BODYDATA.DAT`, `/dev/nflasha15`, `/dev/cnflasha0`, `/dev/mmcblk0rpmb`, `/dev/mtdblock*`, `p2:/setting/Backup.bin`, `psd.bin`, `defdet.bin`, `jiritsu`, `updater://`, `nvram://`, and `eeprom://` (`emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`).

---

## 中文技术报告

### 一、 摘要与净室只读合规性

第 128 阶段基于第十五波全球实时情报同步，完成并集成了 `fx3-firmware-lab` 的 **第 25 个统一净室审计器**（[`vp_ledwall_ecs_freed_and_artnet_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/vp_ledwall_ecs_freed_and_artnet_auditor.py)）。

- **零内置密钥 / 严格只读（`os.O_RDONLY` + `mmap.ACCESS_READ`）**：本地供体模式仅通过 `os.O_RDONLY` 与分节 `mmap.ACCESS_READ` 扫描 FX3 `v7.02` 与 FX6 `v6.01` 的 12 个核心二进制（`appFw.so`、`libmpr.so`、`libInfraLensCommunicator.so`、`libNetServiceEther.so`）、`.uxc` 语言包及 `global.xdb`（`uxa\x07`），绝不产生任何持久化修改或 `.pyc` 缓存污染。
- **确定性净室回退（`CLEAN_ROOM_SYNTHETIC`）**：当设置 `FX3_FX6_FORCE_CLEAN_ROOM=1`、`--clean-room` 或本地供体缺失时，自动合成完整 ELF64 / `global.xdb` / `.uxc` 夹具并运行完全一致的四支柱验证流水线（热运行仅 `0.0017 秒`）。

### 二、 实测指标与双模式验证结果

- **本地供体全量测试**：`753` 项单元测试全部通过（耗时 `24.571s`），`audit-all --json` **`25/25` 全绿**（耗时 `8.856s`，Phase 128 报告 SHA-256：`ce1f00de54fe3bdc1a817d29d257a770ba79019c24a512f95ab4335db692a9e9`）。
- **强制净室全量测试**：`753` 项单元测试全部通过（耗时 `13.171s`），`audit-all --json` **`25/25` 全绿**（耗时 `0.092s`，Phase 128 报告 SHA-256：`471e00df6cd2ef0d01e1e78701a06b56a2fc07b842ad89f929afb2945dfd99d5`）。
- **Phase 128 专项单元测试**：`40` 项双模式测试在本地模式（`0.598s`）与净室模式（`0.392s`）下均全通过；`scripts/run_all_lab_tests.py --clean-only` 检查 `CLEAN / ALL GREEN`（`0.04s`）。

### 三、 四支柱核心架构与防砖契约

1. **支柱 A — 虚拟制片 LED 墙（Brompton SX40 / Megapixel HELIOS）`IMX510` 卷帘读出与分数级 `ECS` 抗扫描条纹求解器**：基于 FX6 `BKID_APP_SETTING_ECS` 与 FX3 `ANTI_FLICKER_SET_HIGH_RES_SS_ON` 契约，在 `23.98..7680.0 Hz` 范围内对齐 LED 扫描复用频率（$f_{\text{mux}} = f_{\text{PWM}} / N_{\text{mux}}$）的整数分频，强拦截次周期条纹与谐波拍频漂移。
2. **支柱 B — 有线 `FreeD`（`0xD1` 29 字节 UDP）与 E 卡口 12 针实时镜头编码器 -> Unreal `LiveLinkFreeD` 桥接**：精准编解码 24-bit 有符号位姿/角度、24-bit Zoom/Focus、Sony 16-bit Spare（12-bit Iris + 4-bit 帧计数）及 `(0x40 - sum) & 0xFF` 校验和；校验 `libInfraLensCommunicator.so` 契约并强制绑定 `P12` 有线 `USB-LAN`（`wf12_00342260_risk == 0`）。
3. **支柱 C — `Art-Net 4`（`UDP 6454`）与 `sACN`（`ANSI E1.31`，`UDP 5568`）灯光帧边界同步防护**：实现并校验 `OpDmx 0x5000`、`ArtSync 0x5200` 与 `ANSI E1.31` 组播/同步域报文，阻断落在 `IMX510` `8.7 ms / 13.2 ms` 读出窗口内的频闪撕裂、未同步多域撕裂与任何无线传输路径。
4. **支柱 D — 易失性 RAM 暂存与持久 `eMMC` / 校准分区零写入证明**：只读校验双方 `global.xdb`，仅放行 `/tmp/`、`ram://`、`memory://`，硬阻断 `BODYDATA.DAT`、`/dev/nflasha15`、`/dev/cnflasha0`、`Backup.bin`、`psd.bin`、`defdet.bin` 与 `jiritsu`（`emmc_mutation_bytes == 0`、`calibration_mutation_bytes == 0`）。

---

## Owned 7-File Inventory / 本阶段七文件交付清单

1. [`reports/2026-11-14-global-sony-wave15-vp-ledwall-freed-unbrick-intel/README.md`](../2026-11-14-global-sony-wave15-vp-ledwall-freed-unbrick-intel/README.md) — Wave-15 live global web intelligence report (EN/ZH-CN, cited URLs)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/vp_ledwall_ecs_freed_and_artnet_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/vp_ledwall_ecs_freed_and_artnet_auditor.py) — 25th unified `fx3-firmware-lab` auditor
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) — Phase 128 symbol exports and `__all__`
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) — `audit-vp-ledwall-freed` CLI subcommand & 25th auditor in `run_audit_all`
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md) — Phase 128 documentation & CLI usage examples
6. [`outputs/fx3-firmware-lab/tests/test_vp_ledwall_ecs_freed_and_artnet.py`](../../outputs/fx3-firmware-lab/tests/test_vp_ledwall_ecs_freed_and_artnet.py) — 40 dual-mode unit tests
7. [`reports/2026-11-14-phase128-vp-ledwall-freed-artnet-auditor/README.md`](README.md) — Phase 128 bilingual technical report
