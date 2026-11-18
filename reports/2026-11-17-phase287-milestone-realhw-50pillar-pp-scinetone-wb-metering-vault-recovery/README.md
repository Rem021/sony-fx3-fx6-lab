# Phase 287（`50/50` 恢复支柱总里程碑！）：Recovery Pillar 50 & 统一 `verify-50pillar-recovery` 总检报告（Wave-48）

## 1. 结论先行（实测 ALL GREEN：`50/50` 里程碑闭环）

- **状态与里程碑结论**：`VERIFIED_50OF50_PILLAR_RECOVERY_MASTER`（`50/50` 全绿通过，无任何硬件写入、`raw_firmware_bytes_leaked = 0`、`physical_device_writes = 0`、`slot1_format_hard_locked = True`）。
- **核心交付范围**（严格限定于 `outputs/fx3-recovery-adapter/` 与本 Phase 287 报告目录）：
  1. [`realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py) — Pillar 50（`50A` + `50B`）与 `50/50` 统一恢复总检聚合器（并发委托 `evaluate_realhw_49pillar_recovery_master` 与 `run_pillar50_standalone_suite`）。
  2. [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) 与 [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) — 导出 `realhw_50pillar_*` 全量 `234` 项新增符号并注册 `verify-pp-scinetone-wb-metering-vault`、`verify-50pillar-recovery` CLI 子命令。
  3. [`test_realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier.py) — **78 项**前向兼容（`>= 50` 支柱计数）双模（`LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试，符合 CI 跨平台可移植规范（`sys.executable`、仓内 `work/_tests/` 临时输出目录 `try/finally` 清理、无裸 `%` 参数）。
  4. [`README.md`](../../outputs/fx3-recovery-adapter/README.md) — 补充 Phase 287（`50/50` 里程碑）与 CLI 入口文档。

## 2. Wave-48 真机固件核验关键技术事实（Pillar 50A + 50B）

| 子支柱 | 核心域与真机固件锚点 | 关键约束与恢复陷阱 | 实测门禁 |
| :--- | :--- | :--- | :--- |
| **50A** | `[Picture Profile]` (`BKID_APP_setting_picture_profile`, `_f.uxc` `0x6830`)、`PP11` (`S-Cinetone`, `0x67ab`/`0x6e61`)、`[Different Set for Still/Mv]` (`0x62ee`)、`[Creative Look]` (`0x6823`: 10 组预设 + `CREATIVE_BOX_1..6`)、`[DRO]` (`0xe89c`)、`[Log Shooting]` (`0x6020`) | 1. 开箱 Movie & Still 默认均为 `PP11`（除非勾选 `Different Set`）。<br>2. `[Picture Profile] != Off` 锁定 `Creative Look = '-'` 与 `DRO = Off`。<br>3. `[Log Shooting]`（`Flexible ISO`/`Cine EI Quick`/`Cine EI`）同时锁死 `PP=Off`、`CL='-'`、`DRO=Off` 防止双 Log 畸变；`PPLUT1..4` 仅限 Movie 且内录下 HDMI 输出钳位 `1080p`。<br>4. **关键复位陷阱**：`[Camera Settings Reset]` 与 `[Initialize]` **均不会清除 `PP1..11` 内部参数及 `Different Set` 勾选标记**（仅 `Initialize` 复位 `PPLUT1..4`），须显式核验 `[PPx] -> [Reset]`；严禁混淆 `ILME-FX6` `Base Look`（`Custom` 默认 `S-Cinetone`，`Cine EI` 锁 `S-Log3`）。 | `6/6`（`2` 正 + `4` 负） |
| **50B** | `[White Balance]` (`0xe5d4`: `Auto` 默认 / `Priority Set in AWB` `0x67a7` / `C.Temp./Filter` `2500K..9900K` `100K` 步进 / `A7..B7` / `G7..M7` / `Custom 1..3` `0xe79d..0xe79c` / `Shutter AWB Lock` `0x66db` / `Shockless WB` `0x62fe`) 与 `[Metering Mode]` (`0xe5cf`: 6 模式、`Face Priority in Multi Metering` `0x69c7`、`Spot Metering Point` `0x625c`、`AEL w/ Shutter` `0x669d`) | 1. `Cine EI` / `Cine EI Quick` 禁用 `Auto` 与 `Underwater Auto` WB；`Log Shooting != Off` 或 `S-Log3`/`PPLUT1..4` 下触发 `[Custom Setup]` 错误陷阱。<br>2. **`Custom 1..3` 随 `Camera Settings Reset` 保留，却被 `Slot 1` `Save/Load Settings` (`CAMSET`) 排除**：恢复后禁止依赖 `CAMSET` 还原 `Custom 1..3`，必须执行人工重标定验证；`Shutter AWB Lock` 与 `AEL w/ Shutter` 跨 `Camera Settings Reset` 留存。<br>3. `De-Squeeze != Off` 强锁 `Face Priority = Off`；`Wide` 对焦区与动态 Tracking 下 `Spot Metering Point` 回退 `Center`；`Cine EI` Base ISO (`800`/`12800`) 保持不变，测光仅输出被动 `M.M.` 偏差。 | `6/6`（`2` 正 + `4` 负） |
| **Slot-1 金库 & Tier-0** | `Slot 1` `CAMSET`/`Backup.bin` (`16` 表面 `H0==H3`) + Stage-B `/tmp/` 易失挂载 | 双层物理 SD `WP` + `slot1_format_hard_locked = True` 阻断 `FORMAT_QUICK`/`FORMAT_FULL`/`DELETE_SINGLE`；Stage-B 禁止写入 `/setting` 等持久分区。 | `0` 字节变异 |

## 3. 有界只读 `O_RDONLY` 供体校验（11 项 Wave-48 供体，< 0.05s）

- **约束**：仅以 `os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK` 有界读取供体，ELF64 `.so` 仅读前 `4096 B`（`HEADER4K_SHA256`），UI `.uxc` 与 `Backup.bin` 全量校验 `FULL_SHA256`，报告与日志 `raw_firmware_bytes_leaked = 0`；无供体或设置 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动进入确定性 `CLEAN_ROOM_SYNTHETIC` 洁净室模式：
  - `FX3 Ver. 7.02` `lib/appFw.so`：`79,015,712 B`（hdr4k `de3201c6615a5307...`）
  - `FX6 Ver. 6.01` `lib/appFw.so`：`50,520,424 B`（hdr4k `18a5d71362317f3f...`）
  - `FX3-CX95900_ALLLANG-Backup.bin`：`2,229,740 B`（sha256 `bf3a9d851f9853fd...`）
  - 其余 8 项 FX3（`string_*_f.uxc` / `string_english.uxc` / `string_english_g.uxc`）与 FX6（`string_english.uxc` / `string_english_2.uxc`）语言包全部 byte-for-byte 命中锁定摘要。

## 4. 实测验证结果（全部实测通过，无推断）

| 检查项目 | 运行模式 / 解释器 | 实测结果 | 实测耗时 / 摘要 |
| :--- | :--- | :--- | :--- |
| `verify-pp-scinetone-wb-metering-vault --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS** (`50A 6/6` + `50B 6/6`, 11 donors OK) | `0.003s`（供体读取 `0.0023s`），`suite_sha256=2ea098fa564c43f4...` |
| `verify-50pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` (`python3.14 -B`) | **PASS (`50/50` 支柱全绿)** | **`0.951s`**（`< 2.2s` budget），`master_50pillar_sha256=b763ff6aa13267c5...` |
| `verify-50pillar-recovery --clean-room --json` | `CLEAN_ROOM_SYNTHETIC` (`FX3_CLEAN_ROOM_TEST=1`) | **PASS (`50/50` 支柱全绿)** | **`0.674s`**（`< 2.2s` budget），`master_50pillar_sha256=14eac8727fce65a1...` |
| Pillar 50 单元测试（`test_realhw_50pillar_...py`） | 3 模式全测：默认 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **PASS `78/78` × 3 模式** | `13.353s` / `11.910s` / `10.424s` |
| 全量 `outputs/fx3-recovery-adapter/tests` 发现 | `/usr/bin/python3 -B` (`3.9.6 + unicorn`) | **PASS `2,716` tests**（1 skipped，0 failures） | `280.011s` |
| `make verify-milestone-264` | `/usr/bin/python3 -B`（本地供体 + `--force-clean-room`） | **PASS ALL GREEN**（`6/6`, `gate102=99/102`, `recovery=44/44`, `qemu=29/29`） | `milestone264_sha256=1a04841142231665...` / `2f74ab5bf8b20a6c...` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` | `python3 -B` | **ALL GREEN**（无 `.pyc`/`__pycache__`/未豁免二进制污染） | `2.87s` |

## 5. 安全护栏不变式（硬锁定）

- `CNFLASHA_USERSPACE_WRITE_BLOCKED = True` · `READ_ONLY_DONOR_ACCESS = True` · `P287_SLOT1_FORMAT_HARD_LOCKED = True`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `SPI_NOR_WRITE_AUTHORIZED = False` · `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False` · `ISP_WRITE_AUTHORIZED = False` · `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `OTP_FUSE_TOUCHES = 0` · `RPMB_COUNTER_INCREMENTS = 0` · `PASSIVE_TX_BYTES_EMITTED = 0` · `PHYSICAL_USB_PACKETS_EMITTED = 0` · `PHYSICAL_DEVICE_WRITES = 0` · `RAW_FIRMWARE_BYTES_LEAKED = 0`
