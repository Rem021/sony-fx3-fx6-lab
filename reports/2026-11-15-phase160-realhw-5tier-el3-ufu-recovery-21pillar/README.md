# Phase 160（Pillar 21 / `21/21` 里程碑）：真机 5 级防变砖恢复升级阶梯、`CXD90057` (`Mira`) Multi-USB `1.8V UART` EL3 (`0xfe020000`) 冷启动防护与官方 `BODYDATA.DAT` (`\x89UFU`) 原厂回刷核验

## 1. 核心结论

- **交付闭环**：在 `outputs/fx3-recovery-adapter/` 完成第 21 根恢复支柱（Pillar 21 / **21/21**），实现官方 Sony `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n` `Ver. 7.02`）原厂 `p1` 回刷前置核验、`CXD90057`（*Mira*）15 针 Multi/Micro-USB `1.8V UART` EL3（`0xfe020000`）冷启动只读防护审计，以及确定性 5 级防变砖恢复升级阶梯引擎。
- **硬锁定安全底线**：全模块强制锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`persistent_write_release = False`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`passive_tx_bytes_emitted = 0`、`otp_fuse_touches = 0`、`otp_fuse_writes = 0`、`raw_firmware_bytes_leaked = 0`。
- **事实与未执行动作边界**：本轮全部校验均为本地受管只读文件检查（`os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`）与确定性洁净室合成回归（`FX3_FX6_FORCE_CLEAN_ROOM=1`），**未对任何真实物理 `ILME-FX3` 机身执行通电、USB 发包、Multi-USB 电平接入、EL3 SRAM 载荷发送、`BODYDATA.DAT` 回刷、eMMC ISP 或 SPI NOR 烧录**。

## 2. 交付文件清单（仅 6 项归属文件）

| 类型 | 交付文件 | 说明 |
|---|---|---|
| 新增核心模块 | [`realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py) | Pillar 21 供体有界只读审计 + 支柱 A（UFU 原厂回刷）/ B（EL3 冷启动护栏）/ C（5 级升级阶梯） |
| 更新包导出 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出全部 Pillar 21 公开常量、数据结构与函数至 `__all__`（无覆盖既有 Phase 155 符号） |
| 更新 CLI | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 新增 `verify-realhw-5tier-el3-ufu` 与 `verify-all-recovery --with-phase160`（21/21 支柱） |
| 更新文档 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/outputs/fx3-recovery-adapter/README.md) | 补充 Phase 160（Pillar 21 / `21/21`）模块说明与 CLI 示例 |
| 新增单元测试 | [`test_realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/outputs/fx3-recovery-adapter/tests/test_realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py) | 48 项双模式（本地只读供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1`）快速单元测试 |
| 阶段报告 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/reports/2026-11-15-phase160-realhw-5tier-el3-ufu-recovery-21pillar/README.md) | 本报告 |

## 3. 已验证事实与未执行物理台架动作严格区分

### 3.1 已完成实证：`O_RDONLY` 本地供体与洁净室离线核验

1. **有界只读供体检查（总耗时 `0.017 s`，零专有字节泄露）**：
   - `loader_nor.bin`（`101,888 B`，SHA-256 `4358c839...`）：校验 AArch64 EL3 `VBAR_EL3` 指令序言（`0xD51EC001`）与 `0xFE049000` SRAM 入口特征。
   - `p1` `nflasha1` `/sbin/init`（`1,438 B`，SHA-256 `223f642c...`）与 `7.02 p3` `/sbin/init`（`735 B`，SHA-256 `c83de1ab...`）：经 `FatP1` + `SquashFS` 与 `O_RDONLY` 核对原厂启动链标识。
   - `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，SHA-256 `bf3a9d85...`）：核验 `0xAAAAAAAA`、`BK4\x00`、`subsystems=819` 及 `ILME-FX3` 机种标识。
   - `cpapp-b.bin`（`15,980,568 B`，有界 4 KiB 头部 SHA-256 `452c9e4e...`）与官方 `fx3-7.02-BODYDATA.DAT`（`811,876,768 B`，有界 4 KiB 头部 SHA-256 `fc135914...` + 12 B 尾部 `DEND`）：通过 `os.pread` 仅读取 `<= 64 KiB` 首尾元数据，验证 `\x89UFU\r\n\x1a\n`、`DATV=1`、`PROV=1`、`UDID=10`（含 `054C:0DA1`）、`FDAT`（`811,876,624 B = 272 B + 792,848 * 1024 B` 精确对齐）与 `DEND`。
2. **三大支柱场景全通（`8/8` + `6/6` + `8/8`）**：
   - **支柱 A（`BODYDATA.DAT` 原厂回刷前置门禁 `8/8`）**：强制只放行 `ILME-FX3`（`0x91030080`），硬拒绝 `ILME-FX30`、`ILCE-7SM3`、`ILCE-7M4`、`ILME-FX6`、`ILME-FX3A` 跨机种载荷；强制更新前完成 `p15:/usr` `.orig` 16/16 净卸载校验；核验 `<HH` `1024 B` `FDAT` 帧校验与 `0x8000` 终止帧；拦截 `<51%` 电量、跨区 `NTSC/PAL` 与降级。
   - **支柱 B（`CXD90057` 15 针 Multi/Micro-USB EL3 `0xfe020000` 冷启动护栏 `6/6`）**：核验 `Pin 2 GND`、`Pin 7 XRESET_REQ`、`Pin 8 UART_TX`、`Pin 9 UART_RX`（`1.65V..1.98V` `1.8V CMOS` 窗口，拦截 `3.3V/5.0V`）、`Pin 10 AD_JACK_IN` 与 `VMC-BNCM1`（`680 kOhm`）/ `LANC`（`100 kOhm`）互斥及 `0xfe020000..0xfe060000` SRAM 边界，并硬锁死 `el3_payload_transmit_authorized = False`。
   - **支柱 C（确定性 5 级防变砖升级阶梯 `8/8`）**：按 `Tier-1 (EH1 47 us SD 旁路)` -> `Tier-2 (p15 .orig EH2 / 16/16 H0==H3 via 054C:0DA1 -> 054C:0336)` -> `Tier-3 (官方 BODYDATA.DAT \x89UFU 原厂回刷；遇脏 p15 自动重定向回 Tier-2)` -> `Tier-4 (CXD90057 EL3 0xfe020000 冷启动只读诊断)` -> `Tier-5 (同机身 CID 绑定 pnflasha* + /dev/mtd0ro loader_nor.bin 离线硬件 ISP 仓库，写授权永久 False)` 自动择最低影响路径。

### 3.2 未执行项：物理 FX3 相机实机台架操作（待后续真机人工授权窗口）

以下动作在本次任务中 **完全未执行**（且代码层面不可写、不可发送）：
- 未将真实 `ILME-FX3` 连接至 Multi/Micro-USB `1.8V UART` / `XRESET_REQ` 治具，未在真机 `0xfe020000` SRAM 发送任何引导载荷。
- 未向真机 USB `054C:0DA1` / `054C:0336` 或 SD 卡执行 `BODYDATA.DAT` 实机回刷。
- 未对真机 eMMC（`pnflasha*`）或 SPI NOR（`loader_nor.bin`）执行焊接飞线、`RESET_N` 拉低或 `8-bit` ISP 编程写入。

## 4. 实测验证结果

| 验证命令 | 模式 | 结果 |
|---|---|---|
| `test_realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py` | 本地只读供体（`LOCAL_DONOR_RDONLY`） | **48/48 全部通过** |
| `test_realhw_bootrom_el3_and_ufu_stock_reflash_verifier.py` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **48/48 全部通过**（3.44s） |
| `fx3_recovery verify-realhw-5tier-el3-ufu` | 双模式（`LOCAL_DONOR_RDONLY` & `CLEAN_ROOM_SYNTHETIC`） | `all_passed=True`，`8/8 + 6/6 + 8/8`，所有写/发包锁均为 `False`/`0` |
| `fx3_recovery verify-all-recovery --with-phase94 ... --with-phase160` | 双模式 | **`pillars=21/21`**，`all_passed=True`（无标志默认仍保持 `7/7` 向后兼容） |
| `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 本地供体 | **916/917 通过（1 skip）**；仅既有用例 [`test_recovery_master_suite_and_uart_decoder.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h173-phase160-5tier-el3-ufu-recovery-21pillar/outputs/fx3-recovery-adapter/tests/test_recovery_master_suite_and_uart_decoder.py#L391) 的 `test_25`（未修改的墙钟 `< 1.0s` 断言）在整套连跑并发负载下录得 `1.174s`（单独运行该文件本地模式 `34/34` `0.847s` 通过） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 洁净室模式 | **858/859 通过（10 skip）**；同上仅既有用例 `test_25` 墙钟 `< 1.0s` 断言在并发负载下录得 `1.488s` |
| `scripts/run_all_lab_tests.py --clean-only` | 仓库洁净度审计 | **ALL GREEN in 0.33s**（零 `.pyc` / 二进制污染） |
| `scripts/verify_byof_manifest.py --json` | BYOF 清单校验 | **`all_checks_passed: true`**（54/54 供体，0.60s） |
