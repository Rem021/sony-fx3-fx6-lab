# 第 153 阶段 — 真机主线 Part 11：`pnflasha/cnflasha` 双层加密配对与 `/dev/mtd0ro` SPI-NOR 守卫（`G47`）、`p12/p13` RF NVS 防火墙 / `Off-in-Rec` `65°C` 风扇强制超驰 / `6100 mV` `EncWfiStop`（`G48`）与 48 门禁主安全预检（`verify-48-gates`）

- **日期**：`2026-11-15`
- **分支 / 工作区**：`h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates`
- **核心模块**：[`realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py)
- **单元测试**：[`test_realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/tests/test_realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py)
- **硬安全红线（不可越界）**：
  - `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
  - `PERSISTENT_WRITE_RELEASE = False`
  - `SPI_NOR_WRITE_AUTHORIZED = False`
  - `overall_ready_for_hardware_attach = False`（默认离线 `45/48` 与 `--dry-run-simulated-backup` `48/48` 模式均锁死）
  - 既有门禁模块（`G01..G46`、`verify-40-gates`、`verify-44-gates`、`verify-46-gates`）保持 100% 向后兼容且零改动。

---

## 1. 已验证事实：只读参考件审计、门禁实现与离线/仿真测试回执

### 1.1 双模 `os.O_RDONLY` 参考件合约审计（[`audit_phase153_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L517-L639)）
严格通过 `os.open(..., os.O_RDONLY)` 读取本地 FX3 `7.02` 只读参考件，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或参考件目录缺失时确定性回退到合成 Clean-Room 元数据，JSON 序列化零原始索尼固件字节泄露：

| 键名 | 制品路径（相对 `work_root`） | 实测字节数 | SHA-256 前缀 | 已校验标记 |
| :--- | :--- | :---: | :--- | :--- |
| `fx3_libsencore` | `sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so` | `377,328` | `a2907111c4a22314...` | `AdjustControlFunc`, `SenserIfStart`, `SenserPacket`, `FAN_SET_SPEED`, `CXS_WRITE_PWM`, `GET_TEMPERATURE`, `USB_BUSPOWER_SUPPLY_CONTROL` |
| `fx3_libmpr` | `fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so` | `3,517,008` | `9aeef3b9edb3d011...` | `DmmMemInfo`, `GetUnitInfo`, `EncWfiStop`, `EncWfiStopReserve`, `ExecEncStart` |
| `fx3_im_elf` | `fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf` | `40,920` | `5171f576d8b76cfb...` | `\x7fELF`, `libIMDB.so`, `libbackup.so`, `libosal_uipc.so` |
| `fx3_cpapp_b` | `sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin` | `15,980,568` | `c90d00d807874a53...` | `SET_FAN_EQ_ID`, `PROC_MSG_SET_FAN_EQ_ID:`, `FAN_R`, `PWM`, `THERM`, `BATT_AUTH_Snd`, `ACV_BATT_Snd`, `LiroSeq` |
| `fx3_backup_bin` | `fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd...` | `BK4\0` |

### 1.2 Gate `G47`：双层 `pnflasha/cnflasha` SPACC 加密域配对、同机身 `CID` OTP 绑定与 `/dev/mtd0ro` SPI-NOR 只读守卫
实现函数：[`verify_pnflasha_cnflasha_cid_and_mtdro_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L779-L995) / [`evaluate_g47_pnflasha_mtdro_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L1298-L1384)
1. **双层 eMMC 加密域隔离（[`validate_dual_layer_cipher_pairing`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L646-L678)）**：严禁将 `SPACC_CNFLASHA_LOGICAL` 逻辑解密流还原至 `RAW_PNFLASHA_ISP` 原始镜像，或反之跨越加密边界写回；跨域即阻断为 `BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH`。
2. **同机身 `eMMC CID` OTP 密钥绑定（[`validate_camera_cid_binding`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L681-L695)）**：校验 `backup_camera_cid_sha256` 与 `target_camera_cid_sha256`（必须为 64 位小写 hex 且严格相等），对 `RAW_PNFLASHA_ISP` 或任一跨机身密文镜像不一致直接阻断为 `BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH`。
3. **`/dev/mtd0ro` SPI-NOR 引导闪存硬只读锁（[`validate_mtd_readonly_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L698-L722)）**：要求设备节点匹配 `/dev/mtd\d+ro`、仅允许 `O_RDONLY` 打开模式、零写字节与零写请求，且严格封堵 `MEMERASE`、`MEMERASE64`、`MEMWRITEOOB`、`MEMWRITEOOB64`、`MEMWRITE`、`MEMLOCK`、`MEMUNLOCK`、`OTPSELECT`、`OTPLOCK` 等 ioctl，恒定锁定 `spi_nor_write_authorized = False`（否则阻断 `BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE`）。

### 1.3 Gate `G48`：`p12/p13` 射频校准 NVS 防火墙、`USB MSC 054C:0DA1` 可达性、`Off-in-Rec` `>=65°C` `100% PWM` 超驰与 `<=6100 mV` `EncWfiStop`
实现函数：[`verify_rfnvs_msc_fan_override_and_power_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L1002-L1290) / [`evaluate_g48_rfnvs_fan_power_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L1391-L1479)
1. **`p12/p13` RF 监管校准 NVS 防火墙**：强制 `/dev/nflasha12` 与 `/dev/nflasha13` 保持 `MS_RDONLY` 挂载、`rf_nvs_mutation_bytes == 0`、`rf_nvs_writes_requested == 0`，禁止修改 Wi-Fi/BLE MAC 或监管域配置（`BLOCKED_G48_RF_NVS_OR_MAC_MUTATION`）。
2. **`USB MSC 054C:0DA1` 恢复链路保全**：校验 USB 控制器/PHY 未被屏蔽、恢复分区未损坏且 `usb_msc_0da1_reachable == True`（`BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE`）。
3. **`Off in Rec` 与 `cpapp-b.bin` `SET_FAN_EQ_ID` 热超驰阶梯（[`compute_cpapp_fan_override_pwm_pct`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L725-L749)）**：严禁禁用风扇的 `ALWAYS_OFF` 策略；在安全模式（`OFF_IN_REC`/`AUTO1`/`AUTO2`/`MINIMUM`）下强制 `>=58°C -> >=45% PWM`、`>=65°C -> 100% PWM`、`>=72°C -> EncWfiStop`（`BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION`）。
4. **`NP-FZ100` `<=6100 mV` (`2%`) 优雅 `EncWfiStop` 守卫（[`evaluate_npfz100_6100mv_encwfistop`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L752-L771)）**：当未接入外部 USB-PD 且电压跌至 `<=6100 mV`（或电量 `<=2%`）时必须触发 `EncWfiStop` 安全收尾落盘，同时严禁误报 FX6 `18.0V`/`19.5V DC-IN` 阈值告警（`BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM`）。

### 1.4 48 门禁主预检（[`evaluate_48gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py#L1487-L1828) / `verify-48-gates`）实测验证回执

| 验证命令（均使用 `/usr/bin/python3 -B`） | 模式 | 实测结果 | 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `46/46` passed (`OK`) | `2.724s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py -v` | Clean-Room | `46/46` passed (`OK`) | `2.597s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | 全量安全套件（Local Donor） | `843/843` passed (`OK`) | `15.624s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | 全量安全套件（Clean-Room） | `843` run, `842` passed, `1` skipped (`OK`) | `15.154s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-g47-pnflasha-mtdro-vault` | CLI Gate `G47` | `valid=True`, `domain=SPACC_CNFLASHA_LOGICAL->SPACC_CNFLASHA_LOGICAL`, `mtd=/dev/mtd0ro(O_RDONLY)`, `spi_nor_write_authorized=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-g48-rfnvs-fan-power-guard` | CLI Gate `G48` | `valid=True`, `p12_flags=MS_RDONLY`, `rf_mut=0B`, `msc=054C:0DA1`, `fan=100%@65C`, `batt=7600mV/NOMINAL`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-48-gates` | CLI 默认离线 | `status=VERIFIED_45_OF_48_AWAITING_PHYSICAL_TIER0`, `verified=45/48`, `g47_to_g48_all_passed=True`, `overall_ready_for_hardware_attach=False`, `spi_nor_write_authorized=False`, `persistent_emmc_writes_authorized=False` | `<0.4s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-48-gates --clean-room --dry-run-simulated-backup` | CLI 仿真备份演练 | `status=VERIFIED_ALL_48_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=48/48`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `spi_nor_write_authorized=False`, `persistent_emmc_writes_authorized=False` | `<0.4s` |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-46-gates` / `verify-44-gates` / `verify-40-gates` | 向后兼容检查 | `verified=43/46` / `41/44` / `37/40`, `persistent_emmc_writes_authorized=False` | `<0.6s` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库 Clean-Room 卫生检查 | `ALL GREEN` (`CLEAN`) | `0.04s` |

---

## 2. 未执行事项：物理真机上机实测边界

以下事项涉及真实物理 **ILME-FX3（`7.02`）** 硬件会话，本阶段仅完成离线策略守卫、只读参考件校验与仿真测试，**尚未在物理真机上执行**：
1. 物理相机真实 `eMMC` 硬件 `CID` 提取、主机端 `Tier-0` 冷备份读出（`G10..G12`），以及 `pnflasha*` 加密备份库与同机身 `OTP` 密钥一致性实机核验（`G47`）。
2. 物理相机运行时 `/dev/mtd0ro` 只读设备节点句柄校验，以及 `/dev/nflasha12`、`nflasha13`（`p12/p13` RF NVS）真实挂载标志核验（`G47`/`G48`）。
3. 物理相机在 `Off in Rec`（`65°C`）工况下的真实 `SET_FAN_EQ_ID` PWM 阶跃曲线与 `NP-FZ100` 低压至 `6100 mV` 时的实机 `EncWfiStop` 掉电保护遥测（`G48`），因此 `overall_ready_for_hardware_attach`、`spi_nor_write_authorized` 与 `persistent_emmc_writes_authorized` 保持 `False`。

---

## 3. 本阶段专有文件清单（仅 6 个文件）

1. [`outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/outputs/fx3-safety/tests/test_realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py)
6. [`reports/2026-11-15-phase153-safety-realhw-pnflasha-mtdro-rfnvs-48gates/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h165-phase153-safety-pnflasha-mtdro-rfnvs-48gates/reports/2026-11-15-phase153-safety-realhw-pnflasha-mtdro-rfnvs-48gates/README.md)
