# Phase 296：Recovery Pillar 52 & 统一 `verify-52pillar-recovery`（`52/52`）恢复总检报告（Wave-50）

## 1. 结论先行（实测 ALL GREEN：`52/52` 全绿闭环）

- **状态与结论**：`VERIFIED_52OF52_PILLAR_RECOVERY_MASTER`（**`52/52` 恢复支柱全绿通过**；`overall_ready_for_hardware_attach = False`、`persistent_emmc_writes_authorized = False`、`raw_firmware_bytes_leaked = 0`、`physical_device_writes = 0`、`slot1_format_hard_locked = True`、`slot1_vault_erofs_ebusy_enforced = True`）。
- **核心交付范围**（严格限定于任务授权的 6 个文件，未触及任何非属目录或在线 QEMU 端口 `8768`）：
  1. [`realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py) — Pillar 52（`52A` + `52B`）与 `52/52` 统一恢复总检聚合器 `evaluate_realhw_52pillar_recovery_master`（并发委托 `evaluate_realhw_51pillar_recovery_master` 与 `run_pillar52_standalone_suite`）。
  2. [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) 与 [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) — 导出 Phase 296 全部不重叠符号（含模块符号共 `243` 项新增 `__all__` 导出），并注册 `verify-pillar52-focus-area-zoom-iso-flash-vault` 与 `verify-52pillar-recovery` CLI 子命令。
  3. [`test_realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier.py) — **80 项**前向兼容（`assertGreaterEqual(..., 52)`）双模（`LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试，严格使用 `sys.executable`、仓内 `work/_tests/` 临时输出目录及 `try/finally` 清理，支持 `GITHUB_ACTIONS == "true"` 时延余量（`15.0s`）。
  4. [`README.md`](../../outputs/fx3-recovery-adapter/README.md) — 补充 Phase 296 Pillar 52 与 `verify-52pillar-recovery` CLI 文档。
  5. 本报告：[`reports/2026-11-17-phase296-realhw-52pillar-focus-area-zoom-lever-iso-minss-flash-vault-recovery/README.md`](README.md)。

## 2. Wave-50 真机固件核验关键技术事实（Pillar 52A + 52B）

| 子支柱 | 核心域与真机固件锚点 | 关键约束、恢复边界与金库防火墙 | 实测门禁 |
| :--- | :--- | :--- | :--- |
| **52A** | `[Focus Area]`（`BKID_APP_setting_autofocus_area_contrast_detect_af`，`_f.uxc` `0x70ac`/`0x6334`，`_g.uxc` `0x61f1`）、`[Focus Area Limit]`（`.uxc` `0xe227`）、`[AF Area Registration]`（`BKID_APP_setting_register_the_af_frame`，`_f.uxc` `0x6b64`/`0x6b65`）、机身 `W/T` `[Zoom Lever Speed]`（`1st=3 / 2nd=8` STBY/REC）、`[Custom Key Z. Speed]`（`3`）、`[Remote Zoom Speed]`（`Variable / Fixed 1..8`） | 1. `ILME-FX3 Ver. 7.02` 暴露 **7 项通用**对焦区域（`Wide`、`Zone`、`Center Fix`、`Spot: S/M/L`、`Expand Spot`）与 **7 项静态专属 `Tracking:`** 区域（Movie/`S&Q` 硬锁定禁用，动态追踪改由 `[Touch Tracking]` 在 `AF-S/A/C/DMF` 下触发）；`[Focus Area Limit]` 至少保留 **`>= 2` / 14 项**；`[AF Area Registration]` 跨 `Camera Settings Reset` 留存（仅 `[Initialize]`/`[Del. Regist. AF Area]` 清除），Movie/`S&Q`/`iAuto` 禁用且强制 **`[Lock Operation Parts] = Off`**；与仅含 `Wide / Zone / Flexible Spot` 且无 `Tracking:`/`Focus Area Limit`/`AF Area Registration` 的 `ILME-FX6` 严格划界。<br>2. **XLR-H1 硬件证伪**：`ILME-FX3` `XLR-H1` 手柄为纯音频手柄，**零变焦拨杆（`xlrh1_has_zoom_lever = False`）、零录制按键（`xlrh1_has_rec_button = False`）、零 `ZOOM HOLD` 开关（`xlrh1_has_zoom_hold_switch = False`）**；仅机身顶前 `W/T` 变焦拨杆、`Custom Key Z. Speed` 与遥控变焦存在，严格区隔于 `ILME-FX6` Smart Handle（`Handle Zoom` `Off/Low/High/Variable 1..8` + `Handle HOLD Switch` `Normal`/`Rec Button Only`，且 `0..99` 为 `Zoom Position Display` 而非速度挡位）。<br>3. `Slot-1` `EROFS`/`EBUSY` 防火墙阻断对焦/变焦 `CAMSET`/格式化/删除写入，保持 `/tmp/` 易失叠加（`BLKROSET=True`）及 `16/16` `H0 == H3` `Backup.bin`。 | `6/6`（`2` 正 + `4` 负） |
| **52B** | `[ISO Range Limit]`（`BKID_APP_setting_iso_range_limit_{min,max}`）、`[ISO AUTO Min. SS]`（`BKID_APP_setting_iso_auto_min_s_s`，`_f.uxc` `0x778b`/`0x6717`）、`[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）、`[Flash Mode]`（`BKID_APP_setting_flash_mode`，`VAL_HAITA_setting_flash_mode_exposure_mode_*`）、`[Video Light Mode]`（MI-Shoe `PMIC 5V <= 900 mA`） | 1. `[ISO Range Limit]`（`Min/Max` 限幅，跨 `Camera Settings Reset` 留存）与 **静态专属** `[ISO AUTO Min. SS]`（`Slower/Slow/Standard/Fast/Faster` 或 `1/8000..30"`，仅在 Still `P/A` 或 `M + ISO AUTO` 生效，可随 `Camera Settings Reset` 复位）在 Movie `Cine EI` / `Cine EI Quick` 下均被 **Base ISO `800` / `12800` 硬锁定**（且锁定 `[Auto Slow Shutter]`）；与使用 `AGC` 且无 `[ISO AUTO Min. SS]` 的 `ILME-FX6` 严格区隔。<br>2. `[Flash Mode]`（`Flash Off` / `Autoflash` / `Fill-flash` / `Slow Sync.` / `Rear Sync.`，Pillar 52 基线默认 `Fill-flash`，全幅机械快门同步上限 `1/250 s`）**严格门控于机械快门 `EXPOSURE_MODE_STILL`**（Movie/`S&Q`、`Electronic Shutter`、`Silent Mode = On` 与无机械快门 `ILME-FX6` 全数拦截）。<br>3. `[Video Light Mode]`（默认 `Power Link` / `REC Link` / `REC Link & STBY` / `Auto`）覆盖 `Still + Movie + S&Q`，受 **MI-Shoe `PMIC 5V <= 900 mA` 电流护栏**（超限如 `1150 mA` fail-closed 拦截）与非索尼 `<250 V` 触发电压护栏约束；`Slot-1` 防火墙阻断闪光/常亮灯/`DCIM`/`AVF_INFO` ImageDB 写入（`0` 字节持久化写入）。 | `6/6`（`2` 正 + `4` 负） |

## 3. 有界只读 `O_RDONLY` 供体校验（17 项 Wave-50 供体）

- **约束**：严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 读取本地供体（ELF64 `.so` 仅读头部 `4096 B` `HEADER4K_SHA256`，`.uxc` 与 `Backup.bin` 校验 `FULL_SHA256`，`raw_firmware_bytes_leaked = 0`）；`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动进入 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - `FX3 Ver. 7.02` `lib/appFw.so`：`79,015,712 B`（hdr4k `de3201c6615a5307...`）
  - `FX6 Ver. 6.01` `lib/appFw.so`：`50,520,424 B`（hdr4k `18a5d71362317f3f...`）
  - `FX3-CX95900_ALLLANG-Backup.bin`：`2,229,740 B`（sha256 `bf3a9d851f9853fd...`）
  - 12 项 FX3 UI 语言包（`string_{english,simplifiedchinese,traditionalchinese,japanese}{,_f,_g}.uxc`）与 2 项 FX6 UI 语言包（`string_english.uxc` / `string_english_2.uxc`）全数命中锁定摘要（实测 `17/17` 供体读取耗时 `0.00275s`）。

## 4. 实测验证结果（全部实测通过，无推断）

| 检查项目 | 运行模式 / 解释器 | 实测结果 | 实测耗时 / 摘要 |
| :--- | :--- | :--- | :--- |
| `verify-pillar52-focus-area-zoom-iso-flash-vault --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS** (`52A 6/6` + `52B 6/6`, 17 donors OK) | `0.003135s`（供体读取 `0.00275s`），`suite_sha256=ed415353a2348ab0...` |
| `verify-pillar52-focus-area-zoom-iso-flash-vault --clean-room --json` | `CLEAN_ROOM_SYNTHETIC` (`python3.14 -B`) | **PASS** (`52A 6/6` + `52B 6/6`, 17 donors synthetic) | `0.000451s`，`suite_sha256=58620d4aa5360f60...` |
| `verify-52pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS（`52/52` 支柱全绿）** | **`0.958696s`**（`< 1.2s` fast CLI budget；P52 `0.043834s`），`master_52pillar_sha256=91b47746c968ade1...` |
| `verify-52pillar-recovery --clean-room --json`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `CLEAN_ROOM_SYNTHETIC` (`python3.14 -B`) | **PASS（`52/52` 支柱全绿）** | **`0.660281s`**（`< 1.2s` fast CLI budget；P52 `0.000471s`），`master_52pillar_sha256=6c9e96783234264c...` |
| Pillar 52 单元测试（`test_realhw_52pillar_...py`） | 默认 `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS `80/80`** | `8.929s` |
| Pillar 52 单元测试（`test_realhw_52pillar_...py`） | `FX3_CLEAN_ROOM_TEST=1` (`python3.14 -B`) | **PASS `80/80`** | `8.919s` |
| Pillar 52 单元测试（`test_realhw_52pillar_...py`） | `FX3_FX6_FORCE_CLEAN_ROOM=1` (`python3.14 -B`) | **PASS `80/80`** | `9.080s` |
| Pillar 52 单元测试（`test_realhw_52pillar_...py`） | `/usr/bin/python3 -B` (`3.9.6 + unicorn`) | **PASS `80/80`** | `10.954s` |
| 全量 `outputs/fx3-recovery-adapter/tests` 发现 | `/usr/bin/python3 -B` (`3.9.6 + unicorn`) | **PASS `2,876` tests**（1 skipped，0 failures） | `293.967s` |
| `make verify-milestone-264` | `/usr/bin/python3 -B`（本地供体 + `--force-clean-room`） | **PASS ALL GREEN**（`6/6`，`gate102=99/102`，`recovery=44/44`，`auditors=45/45`，`vm_stages=58/58`，`qemu=31/31(93/93)`） | `milestone264_sha256=8b92b3c03ebf3326...` / `61be8816b7d69828...` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `python3.14 -B` | **ALL GREEN**（无 `.pyc`/`__pycache__`/未豁免二进制污染） | `0.05s` |
| `make clean-audit` | `/usr/bin/python3 -B` | **ALL GREEN** | `0.03s` |

## 5. 安全护栏不变式（硬锁定）

- `CNFLASHA_USERSPACE_WRITE_BLOCKED = True` · `READ_ONLY_DONOR_ACCESS = True` · `P296_SLOT1_FORMAT_HARD_LOCKED = True` · `P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`
- `OVERALL_READY_FOR_HARDWARE_ATTACH = False` · `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `SPI_NOR_WRITE_AUTHORIZED = False` · `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False` · `ISP_WRITE_AUTHORIZED = False` · `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `OTP_FUSE_TOUCHES = 0` · `RPMB_COUNTER_INCREMENTS = 0` · `PASSIVE_TX_BYTES_EMITTED = 0` · `PHYSICAL_USB_PACKETS_EMITTED = 0` · `PHYSICAL_DEVICE_WRITES = 0` · `RAW_FIRMWARE_BYTES_LEAKED = 0`
