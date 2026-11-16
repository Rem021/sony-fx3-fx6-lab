# Phase 161 — 实体 FX3 硬件安全护栏 `G51`（双槽 `CFexpress Type A / SDXC V90` 码率门禁、卡门 GPIO 清空与 `BODYDATA.DAT` `\x89UFU` 升级前 `H0 == H3` 校验）、`G52`（5 级不可变砖恢复梯度、`ILME-FX3` `0x91030080` 机型锁与 `CXD90057` EL3 只读守卫）与统一 52-Gate 主预检报告

> **任务 ID**: `H174` · **目标硬件**: Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`)
> **核心结论**: 在严格保持 `G01..G50` 历史模块 100% 未修改的前提下，已完成安全门 **`G51`**、**`G52`** 与统一 **52-Gate 主预检引擎 (`evaluate_52gate_preflight` / `verify-52-gates`)** 的双模式实现与验证。离线默认模式 `49/52` 通过（`G10..G12` 实体 Tier-0 门维持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`），`--dry-run-simulated-backup` 模式 `52/52` 演练通过；全部核心写入/发射/挂机红线（`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`overall_ready_for_hardware_attach = False`）均保持硬锁定。

---

## 1. 严格区分：已实测事实 vs 未执行的实体台架操作

### 1.1 本次已实测事实（`os.O_RDONLY` 固件契约审计 + 离线安全门单元测试 + CLI + 净室卫生审计）
1. **双模式只读 (`os.O_RDONLY`) Donor 审计 ([`audit_phase161_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/realhw_cfexpress_ufu_el3_and_52gate_guard.py#L625-L760))**：
   - 实测经 `os.open(..., os.O_RDONLY)` 读取并校验 FX3 `7.02` 本地供体 `libsencore.so`（`377,328 B`）、`libmpr.so`（`3,517,008 B`）、`im.elf`（`40,920 B`）、`cpapp-b.bin`（`15,980,568 B`）、`FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`）及有界 `4096 B` `fx3-7.02-BODYDATA.DAT` 头部（`\x89UFU\r\n\x1a\n`、`DATV`、`PROV`、`UDID`，总长 `811,876,768 B`），全量 SHA-256 与关键标记均通过；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失 donor 目录时确定性回退至 `CLEAN_ROOM_SYNTHETIC`，JSON 输出零原始索尼固件字节泄露。
2. **Gate `G51` (`CFexpress Type A / SDXC V90` 双槽码率门禁、卡门 GPIO FIFO 清空与官方 `BODYDATA.DAT` `\x89UFU` 升级前护栏)**：
   - 强制 `XAVC S-I 4K 120p 600 Mbps`（需 `93.75 MB/s` 含余量，且硬件锁定 `CFexpress Type A` `VPG200/VPG400`）对 `< V90` 或非 `CFexpress Type A` 介质一律拒绝（`BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT`）。
   - 强制卡门开启 GPIO 中断在卸载前将写缓存 FIFO 刷空（`unflushed_fifo_bytes_on_door_open == 0`、`fifo_flushed_before_umount == True`，否则 `BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO`）。
   - 强制双启动切换期间保持用户素材目录 `PRIVATE/M4ROOT` 与 `XDROOT` 零改动（`m4root_mutation_bytes == 0`、`xdroot_mutation_bytes == 0`，否则 `BLOCKED_G51_USER_CLIP_DIR_MUTATION`）。
   - 强制当 Slot A/B 存在 `/mnt/sd/BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`）时在 `< 100 µs`（标称 `47.0 µs`）触发 Stage-A 原厂直通，并在 `p15:/usr` `.orig` 干净卸载校验 `H0 == H3` 完成前阻断官方固件升级启动（`BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD`）。
3. **Gate `G52` (5 级不可变砖恢复梯度、`ILME-FX3` `0x91030080` `BODYDATA.DAT` 机型锁与 `CXD90057` EL3 `0xfe020000` 只读守卫)**：
   - 校验全部 5 个非破坏性恢复层级顺序与就绪状态：`Tier-1 SD 47 µs` $\to$ `Tier-2 p15 .orig` $\to$ `Tier-3 同机型 BODYDATA.DAT` $\to$ `Tier-4 Multi-USB 1.8V UART EL3 只读` $\to$ `Tier-5 CID 匹配 eMMC ISP`（`BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE`）。
   - 硬阻断跨机型 `BODYDATA.DAT`（`target_model_id != 0x91030080` 或 `target_model_name != "ILME-FX3"`，`BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH`）。
   - 硬锁定 `CXD90057` EL3（`0xfe020000`）仅允许 `READ_ONLY` 被动监听（`el3_uart_tx_bytes == 0`、`el3_payload_transmit_authorized == False`、`spi_nor_write_authorized == False`、`persistent_emmc_writes_authorized == False`）。
4. **全量自动化验证实测**：
   - 新增 48 项双模式单测（正常 `LOCAL_DONOR_O_RDONLY` 模式 `Ran 48 tests in 2.026s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 48 tests in 1.341s — OK`）。
   - `outputs/fx3-safety/tests` 全套测试：正常模式 `Ran 939 tests in 26.149s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 939 tests in 30.976s — OK (skipped=1)`。
   - CLI `verify-g51-cfexpress-ufu`、`verify-g52-5tier-el3-guard`、`verify-52-gates`（`verified=49/52`）与 `verify-52-gates --dry-run-simulated-backup`（`verified=52/52`，`el3_payload_transmit_authorized=False`、`spi_nor_write_authorized=False`、`persistent_emmc_writes_authorized=False`、`overall_ready_for_hardware_attach=False`）均实测返回退出码 `0`。
   - `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN`。

### 1.2 未执行的实体相机台架操作（仅台架逻辑与护栏就绪，未接触物理机身）
- 尚未向真实物理 **ILME-FX3** 机身插拔物理 CFexpress/SDXC 存储卡测试卡门 GPIO 或触发真实 `BODYDATA.DAT` 更新；实体 Tier-0 门 `G10..G12` 仍未签发，`overall_ready_for_hardware_attach` 硬锁定为 `False`。
- 尚未经由 `Multi-USB 1.8V UART` 向真实 `CXD90057` BootROM EL3（`0xfe020000`）发送任何载荷，也未对 `eMMC` 或 `SPI NOR` 执行任何写入（`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`persistent_emmc_writes_authorized = False`）；跨机型整分区刷写仍为 `BLOCKED / NO-GO`。

---

## 2. 交付清单（严格仅修改/新增 6 个所属文件）

| 序号 | 文件链接 | 变更类型 | 职责摘要 |
| :---: | :--- | :---: | :--- |
| 1 | [realhw_cfexpress_ufu_el3_and_52gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/realhw_cfexpress_ufu_el3_and_52gate_guard.py) | 新增 | 实现 [`audit_phase161_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/realhw_cfexpress_ufu_el3_and_52gate_guard.py#L625-L760)、纯辅助校验器、[`evaluate_g51_cfexpress_ufu`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/realhw_cfexpress_ufu_el3_and_52gate_guard.py#L1570-L1646)、[`evaluate_g52_5tier_el3_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/realhw_cfexpress_ufu_el3_and_52gate_guard.py#L1649-L1735) 及 [`evaluate_52gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/realhw_cfexpress_ufu_el3_and_52gate_guard.py#L1743-L2095) |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/__init__.py) | 更新 | 导出 `G51` / `G52` 与 `evaluate_52gate_preflight` 符号（无历史符号碰撞） |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/fx3_safety/__main__.py) | 更新 | 新增 CLI 子命令 `verify-g51-cfexpress-ufu`、`verify-g52-5tier-el3-guard`、`verify-52-gates` |
| 4 | [outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/README.md) | 更新 | 补充 Section 3.3 导出项与 Section 26（Phase 161 `G51`/`G52`/`verify-52-gates` 说明） |
| 5 | [test_realhw_cfexpress_ufu_el3_and_52gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/outputs/fx3-safety/tests/test_realhw_cfexpress_ufu_el3_and_52gate_guard.py) | 新增 | 48 项双模式单元测试与故障注入用例 |
| 6 | [reports/2026-11-15-phase161-safety-52gates-cfexpress-ufu-el3-guard/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h174-phase161-safety-52gates-cfexpress-ufu-el3/reports/2026-11-15-phase161-safety-52gates-cfexpress-ufu-el3-guard/README.md) | 新增 | 本 Phase 161 验证与交付报告 |
