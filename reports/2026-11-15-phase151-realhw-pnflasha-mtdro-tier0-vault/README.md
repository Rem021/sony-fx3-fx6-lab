# Phase 151 — 真机主线 Part 7（Pillar 19 / `19/19`）：`/dev/pnflasha*` 原始 ISP 密文 + `/dev/cnflasha*` SPACC 逻辑层 + `/dev/mtd*ro` SPI NOR + `Sector 0` 30 分区双层 Tier-0 冷备份仓库校验器

- **日期**: `2026-11-15`
- **分支**: `codex/h162-phase151-realhw-pnflasha-mtdro-tier0-vault`
- **目标包**: `outputs/fx3-recovery-adapter/fx3_recovery/`
- **核心模块**: [`realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py)
- **强安全红线（硬锁定）**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`PHYSICAL_DEVICE_WRITES = 0`、`MTD_RW_OPENS_OR_ERASE_IOCTLS = 0`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 1. 结论先行与事实边界划分

> [!IMPORTANT]
> **严格区分“`O_RDONLY` 供体/洁净室离线实测事实”与“未执行的物理真机导出/刷写动作”**：
> 1. **已实测（Host-only / `os.O_RDONLY` / Clean-Room）**：已在双模式（`LOCAL_DONOR_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）闭环验证 FX3 `7.02` 11 项只读供体元数据、30 分区 `Sector 0`（`"8246"/"2.00"`）LBA 几何、16 表面双层（`RAW_PNFLASHA_ISP` / `SPACC_CNFLASHA_LOGICAL` / `SPI_NOR_MTDRO` / `EMMC_REG_METADATA`）清单与 8 场景跨域还原防火墙（含 GF(256) `P+Q` 位腐败自愈）、以及 `/proc/mtd` -> `/dev/mtd0ro` 只读纪律与 `p12/p13/p18/p23/p30` 单机身出厂校准门禁，接入总检达到 **`19/19`** 支柱全部通过。
> 2. **未执行（Physical Camera Dump = NOT EXECUTED）**：本任务**未连接或打开任何真实物理 ILME-FX3 (`7.02`) 相机 USB/串口/MTD/eMMC 设备、未读取实机 `body_serial` / `eMMC CID` / 物理 `/dev/pnflasha*` / `/dev/cnflasha*` / `/dev/mtd0ro` 转储、未执行任何 eMMC 或 SPI NOR 写入/擦除操作**；任何真机 Stage-B 用户态回读或恢复操作仍须待后续人工显式授权并持实机双副本 Vault 校验通过后方可评审。

---

## 2. 双模式供体只读核验（`os.O_RDONLY` vs `FX3_FX6_FORCE_CLEAN_ROOM=1`）

通过 [`inspect_tier0_dual_layer_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L663-L837) 严格使用 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 检查 11 项 FX3 `7.02` 供体（`FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换至确定性洁净室描述符，JSON 中 **0 字节** Sony 专有镜像泄露）：

| 供体文件 | 大小 (B) | SHA-256 前缀 | 实测关键锚点 |
| :--- | :---: | :--- | :--- |
| `partinf.conf` | `3,999` | `3d96228d4ed2db3c...` | 30 分区表，`p1=(0x80, 0xbf80)`，`p18=(0x31c000, 0xa000)` |
| `mount.conf` | `1,248` | `ea0132091f3bb8d6...` | 30 分区挂载映射含 `/setting`、`/system`、`/rootfs`、`/cp`、`/cert`、`/usr`、`/lens`、`/PMBP` |
| `setup_nflash` | `375` | `055cb3db7a40084a...` | `rename_nflasha()` 先映射 `pnflasha*` 再覆盖映射 `cnflasha*` -> `nflasha*` |
| `insmod_drv1` | `152` | `22f29d06d7776fe5...` | 加载 `crypt-emmc.ko` 与 `emmc.ko` 双层块驱动 |
| `nor_loader_writer.sh` | `9,106` | `78b794fc52c5e104...` | 引用 `loader_nor.bin` / `LdrBkup.bin` / `DGU.bin` / `MIS.bin` / `ddrtraining.dat` |
| `pformat_config.txt` | `1,274` | `21cd5b29dd165c32...` | NOR 扇区布局 `@68` / `@72` / `@512` |
| `loader_nor.bin` | `101,888` | `4358c839cfb1f22d...` | FX3 `v7.02` SPI NOR BLoader 映像 |
| `libsencore.so` | `377,328` | `a2907111c4a22314...` | ELF64 AArch64，含 `AdjustControlFunc` / `TransactionStart` |
| `im.elf` | `40,920` | `5171f576d8b76cfb...` | ELF64 AArch64 (`ET_EXEC`) |
| `cpapp-b.bin` | `15,980,568` | `452c9e4e05fc1942...` (4K 头) | 有界 4 KiB 头部只读校验 (`ARMv7R @ 0x0010800C`) |
| `nflasha15.img` | `479,846,400` | `6d05ebbd28c554d1...` (4K 头) | 有界 4 KiB 超级块校验 (`ext2` `0xEF53`) |

---

## 3. 两大核心支柱实现

### 3.1 支柱 A — 16 表面双层冷备份清单、`Sector 0` 30 分区几何与 8 场景跨域防火墙（`8/8`）

实现于 [`verify_fx3_sector0_30_partition_geometry`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L853-L917)、[`verify_dual_layer_16_surface_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L1216-L1341)、[`evaluate_restore_target_pairing`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L1344-L1494) 与 [`run_pillar_a_8_scenario_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L1497-L1688)：

1. **16 表面全覆盖**：逐一核验 `sector0`、`p1`、`p2`、`p3`、`p5`、`p6`、`p7`、`p8`、`p12`、`p13`、`p15`、`p18`、`p23`、`p30`、`spi_nor_mtd0ro`、与 `emmc_ext_csd` 的 `layer_domain`、FX3 `"8246"/"2.00"` 30 分区 LBA 区间与魔数/熵特征（`ext2 0xEF53`、`SquashFS hsqs`、`BK4\0`、`VX8900`、`WBI2`、`EXT_CSD` 以及 SPACC 密文熵 `>= 7.9 bits/byte`），并拦截 FX6 `p18 @ 0x312000` 偏移或重叠区段。
2. **8 场景跨域防混刷防火墙**：硬拦截 `SPACC_CNFLASHA_LOGICAL` 明文映像写向 `/dev/pnflasha*` 原始扇区、硬拦截 `RAW_PNFLASHA_ISP` 密文映像写向 `/dev/cnflasha*`（或加密 `/dev/nflasha*` 别名）、硬拦截跨机身 `body_serial / cid_sha256` 的 `pnflasha*` SPACC 还原、硬拦截非 `ro` `/dev/mtd*` 或 `MEMERASE`/`MEMWRITEOOB` ioctl，并结合 `SD ExFAT` + `Mac Host Vault` 双副本校验与 GF(256) `P+Q` 纠删码实现分片位腐败自愈。

### 3.2 支柱 B — `/dev/mtd*ro` SPI NOR 与 `p12/p13/p18/p23/p30` 单机身校准完整性门禁（`6/6`）

实现于 [`audit_spi_nor_mtdro_dump`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L1710-L1771)、[`verify_per_camera_factory_cal_vault_gate`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L1774-L1836) 与 [`run_pillar_b_6_scenario_gate`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py#L1839-L1957)：

- 解析 `/proc/mtd` 并强制仅经 `/dev/mtd0ro..mtdNro` (`O_RDONLY`) 读取，校验 `IPL / BLoader / BL31 / BootConfig` 引导包络与擦除块对齐，拒绝全 `0x00`/`0xFF` 擦除态与 `MEMERASE` ioctl。
- 对每台相机唯一的 `p12`、`p13`、`p18`（`/lens` `VX8900`）与 `p23/p30`（`Backup.bin` `BK4\0` 及 FX3 机型 ID 校验）实施双副本 SHA-256 与身份锁检查；全部通过后仅允许进入 Stage-B 人工审阅（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`）。

---

## 4. 实测验证回执

| 命令 / 测试范围 | 运行模式 | 实测结果 | 耗时 |
| :--- | :--- | :--- | :---: |
| `/usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py` | Local Donor (`os.O_RDONLY`) | `46/46` 通过 (`OK`) | `4.646s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py` | Clean-Room | `46` run (`OK`, `skipped=1`) | `4.386s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | Recovery 全套 (Local Donor) | `821` run (`OK`, `skipped=1`) | `64.544s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | Recovery 全套 (Clean-Room) | `763` run (`OK`, `skipped=10`) | `29.858s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-tier0-dual-layer-vault` | CLI 单支柱 (`LOCAL_DONOR_RDONLY`) | `surfaces=16/16, PA=8/8, PB=6/6, mtd_rw_opens_or_erase_ioctls=0, all_passed=True` | `<0.5s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 ... --with-phase151 --clean-room` | 19 支柱全开（默认仍 `7/7`，`--with-phase144` 仍 `18/18`） | `pillars=19/19, all_passed=True, passive_tx_bytes_emitted=0` | `<1.5s` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净与二进制/pyc 审计 | `ALL GREEN` (`CLEAN`) | `0.05s` |

---

## 5. 专有修改文件清单（严格 6 个文件）

1. [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py)
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)
4. [`outputs/fx3-recovery-adapter/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/README.md)
5. [`outputs/fx3-recovery-adapter/tests/test_realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/outputs/fx3-recovery-adapter/tests/test_realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py)
6. [`reports/2026-11-15-phase151-realhw-pnflasha-mtdro-tier0-vault/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h162-phase151-realhw-pnflasha-mtdro-tier0-vault/reports/2026-11-15-phase151-realhw-pnflasha-mtdro-tier0-vault/README.md)
