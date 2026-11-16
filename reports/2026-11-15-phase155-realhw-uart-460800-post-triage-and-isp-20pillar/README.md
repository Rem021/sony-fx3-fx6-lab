# Phase 155 — 真机主线 Part 8（Pillar 20 / `20/20` 里程碑）：`CXD90057` `1.8V ttyAMA0 460800n8` 被动启动阶段分诊、多 USB `1.8V` 电气防火墙与最后手段硬件 ISP 检查单校验器

- **日期**: `2026-11-15`
- **分支**: `codex/h167-phase155-realhw-uart-460800-isp-20pillar`
- **目标包**: `outputs/fx3-recovery-adapter/fx3_recovery/`
- **核心模块**: [`realhw_uart_460800_post_triage_and_isp_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py)
- **强安全红线（硬锁定）**: `PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`RAW_FIRMWARE_BYTES_LEAKED = 0`。

---

## 1. 结论先行与事实边界划分

> [!IMPORTANT]
> **严格区分“`O_RDONLY` 供体/洁净室离线实测事实”与“未执行的物理真机串口/ISP 探针”**：
> 1. **已实测（Host-only / `os.O_RDONLY` / Clean-Room）**：已在双模式（`LOCAL_DONOR_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）闭环验证 FX3 `7.02` 5 项只读供体元数据与 `p1:/boot/kemco.txt` `cfg.uart=1 console=ttyAMA0,460800n8` 配置规则、6 阶段 `ttyAMA0 460800n8` 启动日志分诊引擎（`8/8` 场景）、`1.8V` 逻辑电平与多 USB/`VMC-BNCM1`（`680 kOhm`）竞争防火墙（`6/6` 场景）、以及最后手段脱机 `1.8V VCCQ` eMMC + `1.8V` SPI-NOR ISP 校验清单（`6/6` 场景），接入总检达到 **`20/20`** 支柱里程碑全部通过。
> 2. **未执行（Physical Camera UART/ISP Probe = NOT EXECUTED）**：本任务**未在物理 `Sony ILME-FX3 (7.02)` 主板焊接或连接真实 `1.8V` UART、`VMC-BNCM1`、eMMC ISP 或 SPI-NOR 夹具，未向相机发出任何串口字节（`passive_tx_bytes_emitted == 0`），亦未读取实机 live `ttyAMA0` 串口流、实机 `eMMC CID` / `EXT_CSD` 或物理 `/dev/mtd0ro` 数据**；所有真实相机硬件接驳与任何台架写入仍须经人工确认与双副本 Vault 校验后方可评估。

---

## 2. 双模式供体只读核验（`os.O_RDONLY` vs `FX3_FX6_FORCE_CLEAN_ROOM=1`）

通过 [`inspect_uart_460800_and_isp_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py#L582-L814) 严格使用 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 检查 5 项 FX3 `7.02` 供体（`FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换至确定性洁净室描述符，JSON 中 **0 字节** Sony 专有镜像泄露）：

| 供体文件 | 大小 (B) | SHA-256 前缀 | 实测关键锚点 |
| :--- | :---: | :--- | :--- |
| `kemco.txt` | `1,736` | `555454e8b7db1461...` | `cfg.uart=1`、`console=ttynull0`（出厂静音基线，诊断需 `console=ttyAMA0,460800n8`）、`wdt.timeout=500` |
| `tomco.txt` | `710` | `42f1785422bce152...` | `[TOMCO]`、`uart_baudrate=460800`、`console_enable=N` |
| `/sbin/init` | `735` | `c83de1abeeb779f7...` | `/sbin/initrc` -> `insmod_drv1` -> `setup_nflash` -> `/sbin/init2` 启动序列 |
| `libsencore.so` | `377,328` | `a2907111c4a22314...` | ELF64 AArch64，含 `SET_SEL_UART_LANC`、`SET_GRIP_UART_SEL` 复用符号 |
| `cpapp-b.bin` | `15,980,568` | `452c9e4e05fc1942...` (4K 头) | 有界 4 KiB 头部只读校验（`ARMv7R @ 0x0010800C`） |

---

## 3. 三大核心子系统实现

### 3.1 支柱 A — 被动 `1.8V` 只接收 `460800 8N1` 六阶段启动分诊引擎（`8/8`）

实现于 [`parse_ttyama0_460800_boot_stages`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py#L991-L1035) 与 [`triage_ttyama0_460800_boot_log`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py#L1038-L1233)：

1. **全 6 阶段单调解析**：覆盖 `STAGE_0_BOOTROM_SPI_NOR_IPL` -> `STAGE_1_BLOADER_BL31_ATF` -> `STAGE_2_LINUX_4_9_337_SCEL_KERNEL` -> `STAGE_3_SPACC_CNFLASHA15_EXT2_USR` -> `STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER` -> `STAGE_5_STAGEB_APPFW_BIG6_READY`，显式阶段标签优先于关键字回退，并识别 WDT 复位与串口帧乱码率。
2. **最低影响确定性恢复映射**：按影响由低到高映射至 `EJECT_SD_47US_BYPASS`、`CREATE_STOP_STAGEB_FLAG`、`HOLD_MENU_SHUTTER_POWER`、`P1_LINE1_MODE_CLEAR` 或 `TIER0_VAULT_RESTORE`；遇到乱码/空日志 fail-closed 拒绝盲写。

### 3.2 支柱 B — `1.8V` 逻辑电平与多 USB `VMC-BNCM1` 竞争防火墙（`6/6`）

实现于 [`audit_1v8_uart_and_multi_usb_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py#L822-L899)：

- 硬阻断 `3.3V` / `5.0V` 串口适配器（保护 `CXD90057` `1.8V` IO 引脚）及 `< 1.65V` 欠压探头；
- 强制物理 TX 悬空只接收（`tx_line_connected == False`、`passive_tx_bytes_emitted == 0`）；
- 硬拦截 H0 诊断期间并接 `VMC-BNCM1`（`680 kOhm` LTC 适配器）/ `LANC`（`100 kOhm`）及多 USB 并发端口（`MSC_054C_0DA1`、`SERVICE_054C_0336`、`USB_C_DUAL_HOST`），并校验 `460800 8N1` 帧配置。

### 3.3 支柱 C — 最后手段脱机硬件 ISP（`1.8V VCCQ` eMMC + `1.8V` SPI-NOR）校验清单（`6/6`）

实现于 [`verify_last_resort_isp_checklist`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py#L1415-L1507)：

- 核验 `1.8V VCCQ` eMMC 与 `1.8V` SPI-NOR 供电、`CXD90057` `RESET_N` 拉低隔离 + 主电池/USB 断开、飞线 `<= 10.0 cm`；
- 解析并约束 `EXT_CSD[179]`（`BOOT_PARTITION_ENABLE`、`BOOT_ACK`、`PARTITION_ACCESS == 0`）、`EXT_CSD[177]`（`BOOT_BUS_CONDITIONS`）与 `EXT_CSD[162]`（`RST_n_FUNCTION`，永久阻断 OTP 写入）；
- 校验单机身 `CID` + `body_serial` 绑定的 `pnflasha*` 与 `/dev/mtd0ro` 双遍 SHA-256 配对，同时硬锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`。

---

## 4. 实测验证回执

| 命令 / 测试范围 | 运行模式 | 实测结果 | 耗时 |
| :--- | :--- | :--- | :---: |
| `/usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_uart_460800_post_triage_and_isp_guard.py` | Local Donor (`os.O_RDONLY`) | `48/48` 通过 (`OK`) | `7.597s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_uart_460800_post_triage_and_isp_guard.py` | Clean-Room | `48/48` 通过 (`OK`) | `8.036s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | Recovery 全套 (Local Donor) | `869` run (`OK`, `skipped=1`) | `63.208s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | Recovery 全套 (Clean-Room) | `811` run (`OK`, `skipped=10`) | `32.352s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-uart-460800-isp-triage --json` | CLI 单支柱 (`LOCAL_DONOR_RDONLY`) | `PA=8/8, PB=6/6, PC=6/6, passive_tx_bytes_emitted=0, all_passed=True` | `<0.5s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 ... --with-phase155 --clean-room` | 20 支柱里程碑全开（默认 `7/7`，`--with-phase151` `19/19`） | `pillars=20/20, all_passed=True, passive_tx_bytes_emitted=0` | `<2.5s` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净与二进制/pyc 审计 | `ALL GREEN` (`CLEAN`) | `1.41s` |

---

## 5. 专有修改文件清单（严格 6 个文件）

1. [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/realhw_uart_460800_post_triage_and_isp_guard.py)
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)
4. [`outputs/fx3-recovery-adapter/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/README.md)
5. [`outputs/fx3-recovery-adapter/tests/test_realhw_uart_460800_post_triage_and_isp_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/outputs/fx3-recovery-adapter/tests/test_realhw_uart_460800_post_triage_and_isp_guard.py)
6. [`reports/2026-11-15-phase155-realhw-uart-460800-post-triage-and-isp-20pillar/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h167-phase155-realhw-uart-460800-isp-20pillar/reports/2026-11-15-phase155-realhw-uart-460800-post-triage-and-isp-20pillar/README.md)
