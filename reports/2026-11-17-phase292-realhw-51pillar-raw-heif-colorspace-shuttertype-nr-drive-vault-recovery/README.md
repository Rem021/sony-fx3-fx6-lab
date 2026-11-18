# Phase 292：Recovery Pillar 51 & 统一 `verify-51pillar-recovery`（`51/51`）恢复总检报告（Wave-49）

## 1. 结论先行（实测 ALL GREEN：`51/51` 全绿闭环）

- **状态与结论**：`VERIFIED_51OF51_PILLAR_RECOVERY_MASTER`（**`51/51` 恢复支柱全绿通过**；`overall_ready_for_hardware_attach = False`、`persistent_emmc_writes_authorized = False`、`raw_firmware_bytes_leaked = 0`、`physical_device_writes = 0`、`slot1_format_hard_locked = True`、`slot1_vault_erofs_ebusy_enforced = True`）。
- **核心交付范围**（严格限定于任务授权的 6 个文件，未触及任何非属目录或在线 QEMU 端口 `8768`）：
  1. [`realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py) — Pillar 51（`51A` + `51B`）与 `51/51` 统一恢复总检聚合器 `evaluate_realhw_51pillar_recovery_master`（并发委托 `evaluate_realhw_50pillar_recovery_master` 与 `run_pillar51_standalone_suite`）。
  2. [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) 与 [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) — 导出 Phase 292 全部不重叠符号（含模块符号共 `257` 项新增导出），并注册 `verify-pillar51-raw-heif-colorspace-shuttertype-vault` 与 `verify-51pillar-recovery` CLI 子命令。
  3. [`test_realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier.py) — **80 项**前向兼容（`assertGreaterEqual(..., 51)`）双模（`LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试，严格使用 `sys.executable`、仓内 `work/_tests/` 临时输出目录及 `try/finally` 清理，支持 `GITHUB_ACTIONS == "true"` 时延余量。
  4. [`README.md`](../../outputs/fx3-recovery-adapter/README.md) — 补充 Phase 292 Pillar 51 与 `verify-51pillar-recovery` CLI 文档。
  5. 本报告：[`reports/2026-11-17-phase292-realhw-51pillar-raw-heif-colorspace-shuttertype-nr-drive-vault-recovery/README.md`](README.md)。

## 2. Wave-49 真机固件核验关键技术事实（Pillar 51A + 51B）

| 子支柱 | 核心域与真机固件锚点 | 关键约束、恢复边界与金库防火墙 | 实测门禁 |
| :--- | :--- | :--- | :--- |
| **51A** | `[Image Quality Settings]`（`BKID_APP_setting_jh_file_type` `_f.uxc` `0x742a`、`BKID_APP_setting_still_file_format` `0xe73d`、`BKID_APP_setting_still_raw_file_type` `0x6ff2`）、`[HLG Still Image]`（`0x76c8` / `BT.2020` `0x79e1`）、`[Color Space]`（`0x68b7`: `sRGB` `0xe07d` / `AdobeRGB` `0xe07e`）、`[Set File Name]`（`0x6993`） | 1. `ILME-FX3 Ver. 7.02`（`12 MP IMX510`）**仅暴露** `Compressed`（默认）与 `Uncompressed` 14-bit `.ARW`；fail-closed 拦截 `appFw.so`/`_f.uxc` `0x6b56`（`0x7897`/`0x6bfd`/`0x7894`）休眠 `Lossless Comp` / `Lossless Comp (L)/(M)/(S)`，并严格区分零 `DCIM`/`.ARW`/`.JPG`/`.HIF` 静态管线的 `ILME-FX6`。<br>2. `JPEG/HEIF Switch` 支持 `JPEG`（`.JPG`）、`HEIF(4:2:0)`、`HEIF(4:2:2)`（10-bit `.HIF`）。`[HLG Still Image] = On` 须同时满足 `HEIF(4:2:0/4:2:2)` + `File Format == HEIF`（非 `RAW`/`RAW & HEIF`）+ `P/A/S/M`（非 `Intelligent Auto` 且未被 `Reg. Custom Shoot Set` 覆盖）；开启后锁定 `Picture Profile`/`Creative Look`/`D-Range Optimizer`/`DRO Bracket`，偏移 ISO 边界并将 `[Color Space]` 覆盖为 `BT.2100`（`BT.2020`）。<br>3. `JPEG` + `AdobeRGB` 触发 DCF 2.0 `_DSC0001` 前缀（`sRGB`/`BT.2100` 为 `DSC00001`）；`[Set File Name]`（默认 `DSC`，跨 `Camera Settings Reset` 留存、仅 `Initialize` 复位）严禁首字符为 `_`。<br>4. `Slot-1` `EROFS`/`EBUSY` 金库防火墙阻断静态拍摄写入、`Sort Recording` 定向 `Slot 1` 及格式化/删格操作，保持 `/tmp/` 易失叠加（`BLKROSET=True`）及 `16/16` `H0 == H3` `Backup.bin`。 | `6/6`（`2` 正 + `4` 负） |
| **51B** | `[Shutter Type]`（`BKID_APP_setting_still_shutter_type` `_f.uxc` `0x7aa9`: `Mechanical Shutter` `0x6ddb` 默认 vs `Electronic Shutter` `0x60a1`）、`[Silent Mode]`（`0x7a53` / `_g.uxc` `0x6079`）、`[e-Front Curtain Shut.]`（`0x64c6`）、`[Long Exposure NR]`（`0x6cd7`）、`[High ISO NR]`（`0x650b`）、`[Drive Mode]`（`0x7228` / `0x68d1` `Hi+` `10 fps`） | 1. `ILME-FX3 Ver. 7.02` 仅暴露 **2 项** `[Shutter Type]`（`Mechanical Shutter` vs `Electronic Shutter`），**不存在 `Auto`**（fail-closed 拦截休眠 `BKID_APP_setting_still_shutter_type_anti_distortion_shutter`），并与 `mechanical_shutter = False` 的 `ILME-FX6` 划界。<br>2. `Electronic Shutter`（仅 `P/A/S/M` 可选）与 `Silent Mode = On`（未设 `Target Function` 覆盖时强切电子快门）触发 **5 锁矩阵**：锁定 ① 闪光灯（全幅机械闪光同步上限精确为 `1/250 s` `0x759b`）、② `Long Exposure NR`、③ `e-Front Curtain Shut.`（默认 `On`，跨 `Camera Settings Reset` 留存，仅 `Initialize` 复位）、④ `BULB`、⑤ `Anti-flicker Shoot.`。<br>3. `[Long Exposure NR]` 在 `>= 1 s` 或 `BULB` 拍摄后执行等时长暗帧减噪（阻塞下一张），并在连拍/`Cont. Bracket` 锁定为 `Off`、`Intelligent Auto` 强制 `On`；`[High ISO NR]`（`Normal`/`Low`/`Off`）在 `RAW` 下不可用且不作用于 `.ARW`。<br>4. `[Drive Mode]` 覆盖全部 8 模式，`Cont. Shooting: Hi+` 在 `Compressed` RAW 下可达 `10 fps`（`Hi=8`、`Mid=6`、`Lo=3`），切至 `Uncompressed` RAW 或闪光时降速 `< 10 fps`；`Hi+` 非实时监看；`F > F11` 下 `Hi+/Hi/Mid` 首张锁定对焦；`HLG Still = On` 禁用 `DRO Bracket`；`Slot-1` 防火墙阻断突发连拍/包围 `DCIM` 与 `AVF_INFO` ImageDB 写入。 | `6/6`（`2` 正 + `4` 负） |

## 3. 有界只读 `O_RDONLY` 供体校验（17 项 Wave-49 供体）

- **约束**：严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 读取本地供体（ELF64 `.so` 仅读头部 `4096 B` `HEADER4K_SHA256`，`.uxc` 与 `Backup.bin` 校验 `FULL_SHA256`，`raw_firmware_bytes_leaked = 0`）；`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动进入 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - `FX3 Ver. 7.02` `lib/appFw.so`：`79,015,712 B`（hdr4k `de3201c6615a5307...`）
  - `FX6 Ver. 6.01` `lib/appFw.so`：`50,520,424 B`（hdr4k `18a5d71362317f3f...`）
  - `FX3-CX95900_ALLLANG-Backup.bin`：`2,229,740 B`（sha256 `bf3a9d851f9853fd...`）
  - 12 项 FX3 UI 语言包（`string_{english,simplifiedchinese,traditionalchinese,japanese}{,_f,_g}.uxc`）与 2 项 FX6 UI 语言包（`string_english.uxc` / `string_english_2.uxc`）全数命中锁定摘要（实测 `17/17` 供体读取耗时 `0.003519s`）。

## 4. 实测验证结果（全部实测通过，无推断）

| 检查项目 | 运行模式 / 解释器 | 实测结果 | 实测耗时 / 摘要 |
| :--- | :--- | :--- | :--- |
| `verify-pillar51-raw-heif-colorspace-shuttertype-vault --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS** (`51A 6/6` + `51B 6/6`, 17 donors OK) | `0.004204s`（供体读取 `0.003519s`），`suite_sha256=7d56eae0b9720b55...` |
| `verify-51pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS（`51/51` 支柱全绿）** | **`1.052884s` / `1.046774s`**（`< 1.2s` fast CLI budget），`master_51pillar_sha256=d98134e262513d57...` |
| `verify-51pillar-recovery --json`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `CLEAN_ROOM_SYNTHETIC` (`python3.14 -B`) | **PASS（`51/51` 支柱全绿）** | **`0.742879s`**（CLI） / **`0.327134s`**（API），`master_51pillar_sha256=3c0d0bba6592976d...` |
| Pillar 51 单元测试（`test_realhw_51pillar_...py`） | 默认 `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS `80/80`** | `13.196s` |
| Pillar 51 单元测试（`test_realhw_51pillar_...py`） | `FX3_CLEAN_ROOM_TEST=1` (`python3.14 -B`) | **PASS `80/80`** | `12.804s` |
| Pillar 51 单元测试（`test_realhw_51pillar_...py`） | `FX3_FX6_FORCE_CLEAN_ROOM=1` (`python3.14 -B`) | **PASS `80/80`** | `12.283s` |
| 全量 `outputs/fx3-recovery-adapter/tests` 发现 | `/usr/bin/python3 -B` (`3.9.6 + unicorn`) | **PASS `2,796` tests**（1 skipped，0 failures） | `289.555s` |
| `make verify-milestone-264` | `/usr/bin/python3 -B`（本地供体 + `--force-clean-room`） | **PASS ALL GREEN**（`6/6`，`gate102=99/102`，`recovery=44/44`，`auditors=45/45`，`vm_stages=57/57`，`qemu=31/31(93/93)`） | `milestone264_sha256=4836a7bf0a419d6f...` / `123cca25d5593bc4...` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `python3.14 -B` | **ALL GREEN**（无 `.pyc`/`__pycache__`/未豁免二进制污染） | `2.98s` |
| `make clean-audit` | `/usr/bin/python3 -B` | **ALL GREEN** | `0.04s` |

## 5. 安全护栏不变式（硬锁定）

- `CNFLASHA_USERSPACE_WRITE_BLOCKED = True` · `READ_ONLY_DONOR_ACCESS = True` · `P292_SLOT1_FORMAT_HARD_LOCKED = True` · `P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`
- `OVERALL_READY_FOR_HARDWARE_ATTACH = False` · `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `SPI_NOR_WRITE_AUTHORIZED = False` · `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False` · `ISP_WRITE_AUTHORIZED = False` · `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `OTP_FUSE_TOUCHES = 0` · `RPMB_COUNTER_INCREMENTS = 0` · `PASSIVE_TX_BYTES_EMITTED = 0` · `PHYSICAL_USB_PACKETS_EMITTED = 0` · `PHYSICAL_DEVICE_WRITES = 0` · `RAW_FIRMWARE_BYTES_LEAKED = 0`
