# Phase 166（Pillar 22 / `22/22` 统一恢复总检里程碑）：双介质独立 Tier-0 冷备份 Bit-Rot 清洗 / `GF(256)` 恢复前预演与 `verify-22pillar-recovery`

## 1. 核心结论

- **交付闭环**：在 [`outputs/fx3-recovery-adapter/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter) 完成第 22 根恢复支柱（Pillar 22 / **`22/22`**），落地**双物理存储介质独立 Tier-0 冷备份门禁**（Pillar 22A）、**RAID-6 `GF(256)`（`0x11d`）静默 Bit-Rot 自愈与 `16/16` RAM 恢复前预演**（Pillar 22B），以及亚 `2.0s` 并发 **`verify-22pillar-recovery`** 统一恢复总检 CLI。
- **硬锁定安全底线**：全程强制锁定 `otp_fuse_touches = 0`、`otp_fuse_writes = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`、`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`。
- **事实与未执行动作边界**：本轮全部校验均为本地受管只读检查（`os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)`）与洁净室确定性回退（`FX3_FX6_FORCE_CLEAN_ROOM=1`），**未对任何真实物理 `ILME-FX3` 机身执行通电、USB/UART 发包、Stage-A/B 写入、`BODYDATA.DAT` 刷写、eMMC ISP 或 SPI NOR 烧录**。

## 2. 交付文件清单（严格仅 6 项归属文件）

| 类型 | 交付文件 | 说明 |
|---|---|---|
| 新增核心模块 | [`realhw_22pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py) | `O_RDONLY` 供体只读审计 + Pillar 22A（双介质 + `FX3RCPT1`）+ Pillar 22B（`GF(256)` 清洗与 `16/16` 预演）+ 22/22 并发总检聚合器 [`evaluate_22pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py#L1658-L1859) |
| 更新包导出 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出全部 93 项无冲突 Pillar 22 公开常量/数据结构/函数及 [`verify_22pillar_recovery_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py#L1862-L1869)（零覆盖既有符号） |
| 更新 CLI | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 新增子命令 `verify-22pillar-recovery`（摘要/`--json`/`--out`，`< 2.0s`），并在 `verify-all-recovery` 增加 `--with-phase166`（`22/22` 汇总，默认无标志仍保持 `7/7`） |
| 更新文档 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/README.md) | 补充 Phase 166 Pillar 22 与 `verify-22pillar-recovery` CLI 使用说明 |
| 新增单元测试 | [`test_realhw_22pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/tests/test_realhw_22pillar_master_recovery_verifier.py) | 50 项双模式（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）快速单元测试 |
| 阶段报告 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/reports/2026-11-15-phase166-realhw-22pillar-recovery-master-verifier/README.md) | 本报告 |

## 3. 已验证事实与未执行物理台架动作严格区分

### 3.1 已完成实证：`O_RDONLY` 本地供体与洁净室离线核验

1. **FX3 `7.02` 供体严格只读核验（零原始固件字节泄露）**：
   - 经 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 核验 7 项 FX3 `7.02` 供体：`partinf.conf`（`3,999 B`，SHA-256 `3d96228d...`，30 分区含 `p18 LensData @ 0x0031C000`）、`mount.conf`（`1,248 B`，SHA-256 `ea013209...`，`/setting`・`/lens`・`/usr`）、`loader_nor.bin`（`101,888 B`，SHA-256 `4358c839...`，AArch64 `VBAR_EL3` `0xD51EC001`）、`nflasha1` 2.05（`19,377,152 B`，SHA-256 `ab2cd537...`，FAT12 `0x55AA`）、`FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，SHA-256 `bf3a9d85...`，`0xAAAAAAAA` + `BK4\x00` + `819` 子系统 + `ILME-FX3`），以及有界 `4 KiB` 头部的 `cpapp-b.bin`（`15,980,568 B`，前 4K SHA-256 `452c9e4e...`）与 `nflasha15.img`（`479,846,400 B`，`ext2` `0xEF53`，前 4K SHA-256 `6d05ebbd...`）。
   - `FX3_FX6_FORCE_CLEAN_ROOM=1` 下确定性回退至 `CLEAN_ROOM_SYNTHETIC` / `SYNTHETIC_METADATA_ONLY`（`donor_files_inspected=0`，7 项合成元数据条目，JSON 输出不含任何原始字节）。
2. **Pillar 22A — 双物理介质独立 Tier-0 16 表面冷备份与 `528 B FX3RCPT1` 门禁（`6/6`）**：
   - 通过 [`verify_dual_media_cold_backup_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py#L975-L1107) 强制要求 `media_a.device_id != media_b.device_id`、`hardware_uuid` 与 `mount_point` 均独立（如 Host NVMe + 外置 SSD/SDXC）、16 表面清单完整、`p2:/setting/{psd.bin,defdet.bin,Backup.bin}` 与 `p18:/lens/LENSFILE.BIN` 齐全、`528 B FX3RCPT1` CRC32 收据合法且双介质 SHA-256 完全一致，方允许 Stage-A 暂存准备（单介质、同盘双路径、缺表面/校准文件、篡改收据、跨机身、双介质漂移全部 fail-closed 阻断）。
3. **Pillar 22B — RAID-6 `GF(256)`（`0x11d`）静默 Bit-Rot 清洗与 `16/16` RAM 预演（`6/6`）**：
   - 通过 [`encode_16_surface_gf256_archive`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py#L1115-L1150) 与 [`scrub_and_rehearse_dual_media_bitrot_recovery`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h180-phase166-22pillar-recovery-master-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py#L1218-L1382) 验证 `0` 块、`1` 块纯 `GF(256)` 伴随式定位及 `2` 块（双数据分片或数据 + P/Q 校验块）静默 bit-rot 100% 无损恢复与 `16/16` 恢复前 RAM 魔数/域隔离/SHA-256 核验（`physical_device_writes = 0`）；`>= 3` 块并发损坏、跨域混刷与写解锁请求 100% fail-closed 阻断。
4. **22/22 统一总检并发聚合（`< 2.0s`）**：
   - 3 通道平衡并发（Lane 1 独跑 Pillars 1–7，Lane 2 与 Lane 3 并行评估 Pillars 8–22）实测均在 **`< 1.0s`** 内收敛全部 22 根恢复支柱（`LOCAL_DONOR_O_RDONLY`: `0.994s`，`CLEAN_ROOM_SYNTHETIC`: `0.775s`），并聚合验证 Pillars 18/19/20/21/22 的零写/零发包/零熔丝不变式。

### 3.2 未执行项：物理 FX3 相机实机台架操作

以下动作在本任务中**完全未执行**（且代码中所有对应写/发包权限均硬锁定为 `False`/`0`）：
- 未对真实物理 `ILME-FX3` 机身连接 USB、Multi-USB `1.8V UART`、`XRESET_REQ` 或硬件 ISP 飞线。
- 未向真机写入任何 `Stage-A`/`Stage-B` 文件、`/dev/nflasha1`、`/dev/nflasha15`、`BODYDATA.DAT`、`EL3` SRAM 或 SPI NOR 分区，也未对真机外接 SSD/SD 卡介质执行真实块设备写入。

## 4. 实测验证结果

| 验证命令 | 模式 | 实测结果 |
|---|---|---|
| `test_realhw_22pillar_master_recovery_verifier.py`（50 项新单测） | 默认（`LOCAL_DONOR_O_RDONLY`） | **`Ran 50 tests in 10.485s — OK`** |
| `test_realhw_22pillar_master_recovery_verifier.py`（50 项新单测） | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`Ran 50 tests in 11.135s — OK`** |
| `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 默认（`LOCAL_DONOR_O_RDONLY`） | **`Ran 967 tests in 133.860s — OK (skipped=1)`** |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 洁净室模式 | **`Ran 909 tests in 100.367s — OK (skipped=10)`** |
| `fx3_recovery verify-22pillar-recovery` | 默认（`LOCAL_DONOR_O_RDONLY`） | **`pillars=22/22 all_passed=True elapsed_seconds=0.994 under_2s_budget=True pillar22_a=6/6 pillar22_b=6/6 master_22pillar_sha256=bea33ce0adbb7bd0`** |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... fx3_recovery verify-22pillar-recovery` | 洁净室模式 | **`pillars=22/22 all_passed=True elapsed_seconds=0.775 under_2s_budget=True pillar22_a=6/6 pillar22_b=6/6 master_22pillar_sha256=e181d3c96ea4c247`** |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净度审计 | **`ALL GREEN in 0.11s`**（零 `.pyc` / 零未跟踪二进制污染） |
