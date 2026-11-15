# Phase 187：真机主线安全门 `G63` & `G64`（`ILME-FX3` vs `ILME-FX3A` 硬件分支防火墙与 `XLR-H1` MI 热靴 4ch/24bit 物理抢占护栏）与 64 门总预检

## 1. 结论先行

基于已合入的 Phase 181（`62` 门预检）与 [Wave-23 索尼真机情报](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/reports/2026-11-15-global-sony-wave23-fx3a-vs-fx3-hardware-split-and-xlrh1-4ch-mishoe-intel/README.md)，本阶段在保持 [`evaluate_58gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py)、[`evaluate_60gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard.py) 与 [`evaluate_62gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/realhw_emount_info3d_hdmi_braw_and_62gate_guard.py) 100% 完整兼容的前提下，新增实现 **Gate `G63`**、**Gate `G64`** 及 **64 门主安全预检 [`evaluate_64gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py)**（CLI：`verify-64-gates`）。

- **Gate `G63`（`GATE_G63_FX3_VS_FX3A_LCD_NFC_IR_FIRMWARE_BRANCH_FIREWALL`）**：严格校验原版 `ILME-FX3`（`0x91030080`、`Ver. 7.02`、`1,440,000` 点 LCD、具备 NFC 与 IR 接收硬件），以 `< 50 µs` Fail-Closed 门限拦截 `ILME-FX3A`（2025 改款、`Ver. 2.02`、`2,359,296` 点 XGA LCD、物理移除 NFC 与 IR）、`ILME-FX30`（`0x91030084`）、`FX3A` `Ver. 1.xx/2.xx` `BODYDATA.DAT` 刷机包及跨分支 `CAMSET` 设置导入。
- **Gate `G64`（`GATE_G64_XLRH1_MISHOE_4CH_24BIT_VS_BODY_35MM_OVERRIDE_GUARD`）**：校验 `XLR-H1` MI 数字热靴音频安全与路由（`48kHz/24bit 4ch` / `48kHz/24bit 2ch` / `48kHz/16bit 2ch`、`HANDLE AUDIO = ON`、`IN1/IN2 -> CH1_CH2`、`IN3 -> CH3_CH4`、耳机监听矩阵 `CH1_2` / `CH3_4` / `CH1+3_CH2+4`、升级后 `16bit/2ch` 重置核对），拦截机身 `3.5mm` 麦克风插孔物理抢占锁死 `[MI Shoe Audio Set.]`、`S&Q` 静音状态不一致、Stage-A -> Stage-B 切换期间 `+48V` 幻象供电毛刺及伪造独立 `XLR-H1` USB 固件包。
- **安全红线硬锁**：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. 交付清单（严格限定 6 个受控文件）

1. 核心模块：[realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py)
2. 包导出：[fx3_safety/__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/__init__.py)
3. CLI 入口：[fx3_safety/__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/fx3_safety/__main__.py)（新增 `verify-g63-fx3a-branch-firewall`、`verify-g64-xlrh1-mishoe-guard`、`verify-64-gates`）
4. 模块文档：[outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/README.md)（第 32 节）
5. 双模单元测试：[test_phase187_fx3a_firewall_xlrh1_mishoe_64gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h203-phase187-safety-64gates-fx3a-firewall-xlrh1/outputs/fx3-safety/tests/test_phase187_fx3a_firewall_xlrh1_mishoe_64gate_guard.py)（50 项测试）
6. 交付报告：本文件

---

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 命令摘要 | 实测结果 |
|---|---|---|
| 64 门模拟演练 CLI | `verify-64-gates --dry-run-simulated` | `64/64` 通过，`LOCAL_DONOR_O_RDONLY`，全红线 `False / 0` |
| 64 门默认离线 CLI | `verify-64-gates` | `61/64` 通过（`G10..G12` 保持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`） |
| `G63` / `G64` 单门 CLI | `verify-g63-fx3a-branch-firewall` & `verify-g64-xlrh1-mishoe-guard` | 均返回 `exit 0` 与 `valid=True` |
| Phase 187 专项单测（本地 donor） | `test_phase187_fx3a_firewall_xlrh1_mishoe_64gate_guard.py` | **50/50 通过**（6.217s；单次 `evaluate_64gate_preflight < 6.0s`） |
| Phase 187 专项单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... test_phase187_...py` | **50/50 通过**（4.248s） |
| `fx3-safety` 全量单测（本地 donor） | `unittest discover -s outputs/fx3-safety/tests` | **1233/1233 通过**（38.758s） |
| `fx3-safety` 全量单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... discover` | **1233 测试全部通过**（skipped=1，32.874s） |
| Clean-Room 卫生审计 | `scripts/run_all_lab_tests.py --clean-only` | `CLEAN`（0.04s，零 `.pyc` / 二进制污染） |

---

## 4. 实测事实与未执行物理动作边界

- **已实测离线事实**：本地只读（`os.O_RDONLY`）校验 `fx3/cpapp-b.bin`（`15,980,568 B`）、`fx3/appFw.so`（`79,015,712 B`）与 `fx6/libInfraHotshoe.so`（`47,808 B`）SHA-256 与字符标记全部匹配，`FX3_FX6_FORCE_CLEAN_ROOM=1` 双模一致，`G63` / `G64` 异常拦截分支与 `58/60/62` 门向后兼容性均通过单测实证。
- **未执行物理动作**：未连接任何真实 `ILME-FX3`、`ILME-FX3A`、`ILME-FX30` 机身或 `XLR-H1` 手柄，未发送任何 USB 数据包，亦未执行任何 eMMC/SPI-NOR 持久化写入。
