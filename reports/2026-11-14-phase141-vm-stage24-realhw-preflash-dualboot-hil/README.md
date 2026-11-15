# Phase 141 — Real-Hardware Main Track Part 7: Stage 24 Full-Board End-to-End Real-Hardware Pre-Flash Lifecycle & Dual-Boot HIL Simulator

## 1. 结论先行

- **交付成果**：在 [`outputs/fx3-vm/`](../../outputs/fx3-vm/) 落地 Stage 24 全板预刷写生命周期与四态双启动 HIL 仿真器 [`realhw_preflash_dualboot_lifecycle_emulator.py`](../../outputs/fx3-vm/realhw_preflash_dualboot_lifecycle_emulator.py)，并将其接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)（全板 `24/24` 阶段全绿，支持 `--skip-phase141` 向后兼容跳过）。
- **硬性硬件安全红线**：全链路保持 **`persistent_emmc_writes_authorized = False`**、**`spi_nor_mutation_bytes = 0`**、**`cp_mutation_bytes = 0`**、**`calibration_mutation_bytes = 0`**、**`sector0_mutation_bytes = 0`**、**`wf12_00342260_hits = 0`**、**`physical_device_writes = 0`** 与 **`rsv_orphan_count = 0`**；所有本地供体仅以 `os.O_RDONLY` + `mmap.ACCESS_READ` 只读扫描，零专有文件/密钥泄漏。
- **双模式与性能门禁**：
  - Stage 24 单模块运行时间：本地供体模式 `~0.10s < 0.15s`，洁净室模式 `~0.001s < 0.15s`。
  - 全板 `24/24` 协同仿真运行时间：本地供体模式 `< 1.80s`，洁净室模式 `< 0.70s`。

## 2. 核心架构与四大仿真支柱

### 2.1 只读供体审计（`os.O_RDONLY` + `FX3_FX6_FORCE_CLEAN_ROOM=1` 回退）

基于 FX3 `7.02` 与 FX6 `6.01` 共 9 份真实解包供体（`partinf.conf` x2、`pformat_config.txt`、`LdrBkupList.txt`、`libJiritsu.so`、`appFw.so` x2、`cpapp-b.bin` x2，共约 `163 MiB`）执行全量 SHA-256 与 28+ 条关键符号/偏移标记核验；当设置 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。

### 2.2 Pillar A — `JIRITSU_SETFILE2_COLD_BACKUP_AND_SPACC_TOPOLOGY`

- 建模 FX3 `7.02` 完整 eMMC UDA（`Sector 0` `"8246"` `"2.00"` 30 项零重叠分区表、`pnflasha1..30`、`crypt-emmc.ko` `cnflasha3/7/8/12/15/23/30` SPACC AES-XTS 边界、`16 MiB` Octal-SPI NOR `infomisc.dat` / `loader_nor.bin` / `ddrtraining.dat @ 0x3e210fc`）。
- 执行 Stage-288 入口自解链 `SET_FILE2` Tier-0/1/2 流式冷备份仿真：验证 `p6_peak_bytes = 4,194,824 B (< 4.5 MiB < 25 MiB)`、`p6_residual_files == 0`、`100%` SHA-256 清单双次校验，并拦截 `/tmp/jbusy (0x10000011)`、非法选择器 `0x02` 与 `J0` 帧 CRC32 篡改。

### 2.3 Pillar B — `CNFLASHA15_CIPHER_SAFE_INSTALL_AND_POWERCUT_ROLLBACK`

- 仿真 A7C-II 风格文件级 Stage-B wrapper 经 `/dev/nflasha15`（`/dev/cnflasha15` `ext2` 加密块设备）原子安装与 `ro` 只读重挂。
- 证明绕过 SPACC 直接向 `/dev/pnflasha15` 写入明文触发硬拦截（`SPACC_CIPHERTEXT_CORRUPTION_BLOCKED`，`ciphertext_corruption_events == 0`）。
- 注入写入中途拔电池断电故障，证明 `.orig` 备份恢复机制可 `100%` 还原原厂 `im.elf` SHA-256 并重新锁回 `ro` 挂载状态。

### 2.4 Pillar C — `FOUR_STATE_DUALBOOT_AND_NATIVE_REC_CLOSED_LOOP`

1. **Path 1（SD 卡拔出 / 物理逃生舱）**：零 Stage-B 挂钩，直接启动 `100%` 原厂 FX3 `7.02`，原生拍摄功能完整保留。
2. **Path 2（插入合法签名 SD 清单）**：激活 Strategy-A（`/dev/nflasha20 -> /dev/nflasha30` + `tmpfs /etc/opelog`，`0` 字节 Sector-0 修改），拉起 FX6 `6.01` `appFw.so` + `libMpr.so` ABI shim 驱动原厂 FX3 `cpapp-b.bin` 完成 XAVC S-I（`.MP4`）录制与封口（`rsv_orphan_count == 0`）。
3. **Path 3（插入篡改 SD 清单）**：在 `< 50 ms`（实测 `8.2 ms`）内 fail-closed 拒绝清单并直接回退原厂 FX3 `7.02`。
4. **Path 4（紧急 `p1` 单次救援启动）**：校验 `p1/p3` 互斥写保护、`cfg.uart=1`（`460800 8N1`）与首行 `rm -f /setting/updater/mode* && sync`，从冷备份恢复 `/usr` 后自动切回原厂 `p3` 启动。

### 2.5 Pillar D — `HARDWARE_SAFETY_REDLINES_AND_ZERO_MUTATION_PROOF`

硬锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_mutation_bytes == 0`、`cp_mutation_bytes == 0`、`calibration_mutation_bytes == 0`、`wf12_00342260_hits == 0`，并对 5 类越界篡改请求实施 fail-closed 拦截。

## 3. 涉及文件（Strict 5-File Ownership）

1. [`outputs/fx3-vm/realhw_preflash_dualboot_lifecycle_emulator.py`](../../outputs/fx3-vm/realhw_preflash_dualboot_lifecycle_emulator.py)
2. [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)
3. [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md)
4. [`outputs/fx3-vm/tests/test_realhw_preflash_dualboot_lifecycle_emulator.py`](../../outputs/fx3-vm/tests/test_realhw_preflash_dualboot_lifecycle_emulator.py)
5. [`reports/2026-11-14-phase141-vm-stage24-realhw-preflash-dualboot-hil/README.md`](README.md)

## 4. 验收命令

```sh
# 1. Stage 24 单元测试（44 项）& 全量 outputs/fx3-vm 测试（808 项），双模式运行
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"

# 2. 全板 24/24 协同仿真（本地与洁净室）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --json

# 3. 全仓洁净室主门禁
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
