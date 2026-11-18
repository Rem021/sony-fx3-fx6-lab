# Phase 300（第 300 期里程碑！）：Recovery Pillar 53 & 统一 `verify-53pillar-recovery`（`53/53`）恢复总检报告（Wave-51）

## 1. 结论先行（实测 ALL GREEN：`53/53` 全绿闭环，Phase 300 第 300 期大里程碑达阵）

- **状态与结论**：`VERIFIED_53OF53_PILLAR_RECOVERY_MASTER`（**`53/53` 恢复支柱全绿通过**；`overall_ready_for_hardware_attach = False`、`persistent_emmc_writes_authorized = False`、`raw_firmware_bytes_leaked = 0`、`physical_device_writes = 0`、`slot1_format_hard_locked = True`、`slot1_vault_erofs_ebusy_enforced = True`）。
- **核心交付范围**（严格限定于任务授权的 6 个文件，未触及任何非属目录或在线 QEMU 端口 `8768`）：
  1. [`realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py) — Pillar 53（`53A` + `53B`）与 `53/53` 统一恢复总检聚合器 `evaluate_realhw_53pillar_recovery_master`（并发委托 `evaluate_realhw_52pillar_recovery_master` 与 `run_pillar53_standalone_suite`）。
  2. [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) 与 [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) — 无遮蔽导出 Phase 300 全部新增符号（含模块符号共 `270` 项新增 `__all__` 导出，总计 `6,542` 项导出），并注册 `verify-pillar53-dci4k-aspect-custom-hold-camset-vault` 与 `verify-53pillar-recovery` CLI 子命令（`argparse` 帮助文本内 `%` 均按 Python 3.14 规范转义为 `%%`）。
  3. [`test_realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier.py) — **82 项**前向兼容（`assertGreaterEqual(..., 53)`）双模（`LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试，严格使用 `sys.executable`、仓内 `work/_tests/` 临时输出目录及 `try/finally` 清理，支持 `GITHUB_ACTIONS == "true"` 时延余量（`15.0s`）。
  4. [`README.md`](../../outputs/fx3-recovery-adapter/README.md) — 补充 Phase 300（`300th` Phase Milestone）Pillar 53 与 `verify-53pillar-recovery` CLI 文档。
  5. 本报告：[`reports/2026-11-17-phase300-milestone-realhw-53pillar-dci4k-aspect-custom-hold-camset-photo-capture-vault-recovery/README.md`](README.md)。

## 2. Wave-51 真机固件核验关键技术事实（Pillar 53A + 53B）

| 子支柱 | 核心域与真机固件锚点 | 关键约束、恢复边界与金库防火墙 | 实测门禁 |
| :--- | :--- | :--- | :--- |
| **53A** | `[XAVC S-I DCI 4K]`（`_f.uxc` `0x7336`/`0x61ce`）、`24.00p` 强制重启与回放隔离（`_f.uxc` `0x75ce`，`_g.uxc` `0x639b`/`0x63b6`/`0x63d7`）、Type-A HDMI RAW（`4264x2408`）、Still `[Aspect Ratio]`（`BKID_APP_setting_aspect_ratio`，`_f.uxc` `0x757c`/`0x78a4`/`0x691f`） | 1. **UHD 与 DCI 4K 实测分界**：`ILME-FX3 Ver. 3.00+/7.02` 确实暴露 `[XAVC S-I DCI 4K]`（`4096x2160` `17:9` All-Intra，`23.98p..59.94p` + `24.00p`，S&Q `1..48fps` 且硬锁定 `100/120fps`，`600M` 需 `CFexpress VPG200+`/`SDXC V90+`）；而 Long-GOP（`XAVC HS 4K` / `XAVC S 4K`）与 `XAVC S-I 4K` 严格保持 `3840x2160` `16:9` UHD（无 `24.00p`），且 fail-closed 拦截休眠字符串 `xavc_hs_8k_24p`。<br>2. **`24.00p` 强制重启与易失 `/tmp/` Stage-B 清空风险**：切入或切出 `24.00p` 触发**强制整机重启**，会将 `/tmp/` 易失性 Stage-B bind-mount 完整清零退回未修改的出厂 `ILME-FX3 7.02`（`H0 == H2`）并触发 `24.00p` 回放隔离，严禁将重启恢复状态误判为持久化写入。<br>3. **`4264x2408` HDMI RAW 与 Still `[Aspect Ratio]`**：FX3 HDMI RAW 为 `4264x2408` `16:9`（需 `[Log Shooting] != Off`，锁 `S-Log3` 且禁用 Active SteadyShot / De-Squeeze），对照 FX6 电影机 native `4096x2160 / 3840x2160` SDI/HDMI RAW；Still `[Aspect Ratio]` 覆盖 `3:2`（默认 `12M`）/ `4:3`（`11M`）/ `16:9`（`10M`）/ `1:1`（`8.0M`），RAW 始终保留全画幅 `4240x2832` + 裁剪元数据，`APS-C S35` 下 `L -> M` 降档，与无静态拍照线的 `ILME-FX6` 严格划界。 | `6/6`（`2` 正 + `4` 负） |
| **53B** | `[Reg. Custom Shoot Set]`（`Recall Custom hold 1..3`，`_f.uxc` `0x7631`/`0x60b4`/`0x7581`/`0x725b`）、`[Camera Set. Memory]`（`BKID_APP_setting_memory_recall`、`%c:%s/SONY/SETTING/%s/`）、`[Playback]` `[Photo Capture]`（`BKID_APP_is_edit_photo_capture`，`_g.uxc` `0x60ce`）与 `[Enlarge Image]`（`Enlarge Initial Mag.` / `Enlarge Initial Position`） | 1. **`[Reg. Custom Shoot Set]` 11 项复选与 HLG 互锁**：严格限定 **Still `P/A/S/M`**（Movie/`S&Q`/`Intelligent Auto`/`MR` 全数封禁），暴露 `appFw.so` 全部 **11 项** `is_checked_recall_custom_hold0..10` 复选键，经 `Camera Settings Reset` 留存（仅 `[Initialize]` 清除），调用 `ISO` 或 `DRO Bracket` 时强制 `[HLG Still Image] = Off`。<br>2. **`[Camera Set. Memory]` 路径隔离与跨机型防火墙**：`ILME-FX3` 机内 `1..3` + 卡槽 `M1..M4`（`CAMPR%02d%c.DAT`）及 `CAMSET01..10.DAT` 均位于 `%c:%s/SONY/SETTING/%s/`（SD 为 `/PRIVATE`，CFexpress Type A 为 `""`）；`FX3 appFw.so` 零 `PRIVATE/SONY/PRO/CAMERA`（该路径仅属 `ILME-FX6` `Scene/User/All File`），跨机型配置导入与往 `Slot 1` Tier-0 金库写入 `CAMPR/CAMSET` 一律 fail-closed 拦截。<br>3. **`[Photo Capture]` DCI 4K 锁死与 `Slot-1` `EROFS`/`EBUSY` 防火墙**：`[Playback] -> [Edit] -> [Photo Capture]` 从 UHD/HD 视频抽帧 `8.3M`（`3840x2160`）/ `2.1M`（`1920x1080`）JPEG 或 HEIF，但在 `XAVC S-I DCI 4K` 片段上硬件禁用（`_g.uxc` `0x60ce`），且当 `[Select Playback Media] = Slot 1` 挂载只读 Tier-0 金库时 fail-closed 阻断（`EROFS`/`EBUSY`）；只读 `[Enlarge Image]`（默认 `Standard. Mag.` / `Focused Position`）安全放行。 | `6/6`（`2` 正 + `4` 负） |

## 3. 有界只读 `O_RDONLY` 供体校验（17 项 Wave-51 供体）

- **约束**：严格经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 读取本地供体（ELF64 `.so` 仅读头部 `4096 B` `HEADER4K_SHA256`，`.uxc` 与 `Backup.bin` 校验 `FULL_SHA256`，`raw_firmware_bytes_leaked = 0`）；`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动进入 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - `FX3 Ver. 7.02` `lib/appFw.so`：`79,015,712 B`（hdr4k `de3201c6615a5307...`）
  - `FX6 Ver. 6.01` `lib/appFw.so`：`50,520,424 B`（hdr4k `18a5d71362317f3f...`）
  - `FX3-CX95900_ALLLANG-Backup.bin`：`2,229,740 B`（sha256 `bf3a9d851f9853fd...`）
  - 12 项 FX3 UI 语言包（`string_{english,simplifiedchinese,traditionalchinese,japanese}{,_f,_g}.uxc`）与 2 项 FX6 UI 语言包（`string_english.uxc` / `string_english_2.uxc`）全数命中锁定摘要（实测 `17/17` 供体单独读取耗时 `0.002747s`）。

## 4. 实测验证结果（全部实测通过，无推断）

| 检查项目 | 运行模式 / 解释器 | 实测结果 | 实测耗时 / 摘要 |
| :--- | :--- | :--- | :--- |
| `verify-pillar53-dci4k-aspect-custom-hold-camset-vault --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS**（`53A 6/6` + `53B 6/6`，17 donors OK） | `0.003135s`（供体读取 `0.002747s`），`suite_sha256=81eb44bfab30b4b4...` |
| `verify-pillar53-dci4k-aspect-custom-hold-camset-vault --json`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `CLEAN_ROOM_SYNTHETIC` (`python3.14 -B`) | **PASS**（`53A 6/6` + `53B 6/6`，17 donors synthetic） | `0.000427s`，`suite_sha256=e03735c80a593f41...` |
| `verify-53pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS（`53/53` 支柱全绿）** | **`0.926049s`**（`< 1.2s` fast CLI budget；供体读取 `0.055571s`），`master_53pillar_sha256=2a5c320d912c6b2e...` |
| `verify-53pillar-recovery --json`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `CLEAN_ROOM_SYNTHETIC` (`python3.14 -B`) | **PASS（`53/53` 支柱全绿）** | **`0.627440s`**（`< 1.2s` fast CLI budget），`master_53pillar_sha256=7a6733b9d8597f15...` |
| Pillar 53 单元测试（`test_realhw_53pillar_...py`） | 默认 `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS `82/82`** | `9.431s` |
| Pillar 53 单元测试（`test_realhw_53pillar_...py`） | `FX3_CLEAN_ROOM_TEST=1` (`python3.14 -B`) | **PASS `82/82`** | `9.353s` |
| Pillar 53 单元测试（`test_realhw_53pillar_...py`） | `FX3_FX6_FORCE_CLEAN_ROOM=1` (`python3.14 -B`) | **PASS `82/82`** | `9.499s` |
| Pillar 53 单元测试（`test_realhw_53pillar_...py`） | `/usr/bin/python3 -B` (`3.9.6 + unicorn`) | **PASS `82/82`** | `11.271s` |
| 全量 `outputs/fx3-recovery-adapter/tests` 发现 | `/usr/bin/python3 -B` (`3.9.6 + unicorn`) | **PASS `2,958` tests**（1 skipped，0 failures） | `302.426s` |
| `make verify-milestone-264` | `/usr/bin/python3 -B`（本地供体 + `--force-clean-room`） | **PASS ALL GREEN**（`6/6`，`gate102=99/102`，`recovery=44/44`，`auditors=45/45`，`vm_stages=59/59`，`qemu=32/32(96/96)`） | `milestone264_sha256=1d8b0cd5c399ead8...` / `d63cf13e0df746f6...` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `python3.14 -B` | **ALL GREEN**（无 `.pyc`/`__pycache__`/未豁免二进制污染） | `0.04s` |
| `make clean-audit` | `/usr/bin/python3 -B` | **ALL GREEN** | `0.12s` |

## 5. 安全护栏不变式（硬锁定）

- `CNFLASHA_USERSPACE_WRITE_BLOCKED = True` · `READ_ONLY_DONOR_ACCESS = True` · `P300_SLOT1_FORMAT_HARD_LOCKED = True` · `P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True`
- `OVERALL_READY_FOR_HARDWARE_ATTACH = False` · `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `SPI_NOR_WRITE_AUTHORIZED = False` · `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False` · `ISP_WRITE_AUTHORIZED = False` · `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `OTP_FUSE_TOUCHES = 0` · `RPMB_COUNTER_INCREMENTS = 0` · `PASSIVE_TX_BYTES_EMITTED = 0` · `PHYSICAL_USB_PACKETS_EMITTED = 0` · `PHYSICAL_DEVICE_WRITES = 0` · `RAW_FIRMWARE_BYTES_LEAKED = 0`
