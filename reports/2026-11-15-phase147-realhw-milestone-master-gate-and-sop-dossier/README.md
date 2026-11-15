# Milestone Phase 147 实机上台架就绪总闸门（`verify-milestone-147`）、根 `Makefile` 同步与双语实机部署总册交付报告

> **任务代号**: H158 (`Milestone Phase 147`) · **日期**: `2026-11-15` · **工作区**: `/Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier`

---

## 一、核心交付结论

已完成 **Milestone Phase 147 六支柱实机上台架就绪总闸门（`realhw_milestone147_master_gate_v1`）**、根目录 [`Makefile`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/Makefile) 同步、权威中文主笔+英文摘要实机部署总册及 46 项双模单元测试，**严格限定在授权的 9 个 Owned Files 内闭环交付**。

### 刚性安全红线与事实/未执行边界声明
1. **已验证的离线、协同仿真与 QEMU 真内核事实（Verified Offline / HIL / QEMU Facts）**：
   - 双模总闸门（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）均返回 `status=OK` (`pillars=6/6`)；
   - 满足前向兼容断言（`>= 44` 门禁、`>= 17` 恢复支柱、`>= 28` 实机审计器、`>= 24` VM 阶段）；
   - 默认全局安全红线恒定锁死：`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`hardware_live_attachment_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`。
2. **尚未执行的真实物理实机上台架会话（Not Yet Executed）**：
   - **真实物理 Sony ILME-FX3 (`Ver. 7.02`) 相机本体的 USB 实包通信与台架 Tier-0 实采写入流程尚未执行**；在真实物理机房通过 `G10..G12` 实机只读快照校验与操作员签收前，禁止解除任何持久化写入锁。

---

## 二、修改与新增文件清单（严格 9/9 Owned Files）

| # | 文件 | 变更类型 | 说明 |
| :---: | :--- | :---: | :--- |
| 1 | [`realhw_milestone147_master_gate.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone147_master_gate.py) | NEW | 6 支柱并行总闸门聚合器、双模支持（`O_RDONLY` / Clean-Room）、前向兼容 `>=` 校验与双语 Markdown 报告渲染器 |
| 2 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) | UPDATE | 导出 Phase 147 全部公共常量、数据类、构建与失效关闭校验函数 |
| 3 | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) | UPDATE | 新增 `verify-milestone-147` CLI 子命令与 `--clean-room` / `--json` / `--markdown-out` / `--output` 参数支持 |
| 4 | [`README.md` (`fx6-on-fx3-closure`)](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/outputs/fx6-on-fx3-closure/README.md) | UPDATE | 补全 Milestone Phase 147 模块结构说明、CLI 入口及 `make verify-milestone-147` 指令 |
| 5 | [`test_phase147_realhw_milestone_master_gate.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/outputs/fx6-on-fx3-closure/tests/test_phase147_realhw_milestone_master_gate.py) | NEW | 46 项双模单元测试（覆盖 P1..P6 故障注入、前向兼容 `>=`、`b'...'` 防护、Round 28/29 审计、CLI 与 `< 20s` 性能门槛） |
| 6 | [`Makefile`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/Makefile) | UPDATE | 新增 `verify-44-gates`、`verify-17pillar-recovery`、`verify-sd-stageb-bundle`、`verify-milestone-147` 并同步至 `verify-fast` |
| 7 | [`REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md) | NEW | 权威中文主笔+英文摘要实机部署总册（`054C:0DA1 -> 054C:0336` `SET_FILE2` + `AdjustControl 0x40`、`/dev/cnflasha15`、`nflasha20 -> nflasha30`、`p1` 首行救援与 `H0 == H3`） |
| 8 | [`STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md) | UPDATE | 互链实机部署总册并同步 Milestone 147 快速门禁命令 |
| 9 | [`README.md` (本报告)](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h158-phase147-realhw-milestone-master-gate-dossier/reports/2026-11-15-phase147-realhw-milestone-master-gate-and-sop-dossier/README.md) | NEW | Milestone Phase 147 交付验收报告 |

---

## 三、实测验证数据与指令回执

| 验证指令 | 运行模式 | 实测结果 |
| :--- | :--- | :--- |
| `PYTHONPATH=... /usr/bin/python3 -B -m unittest test_phase147_... test_phase130_...` | `LOCAL_DONOR_O_RDONLY` | **88 / 88 OK** (`15.976s`, `exit 0`) |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest test_phase147_...` | `CLEAN_ROOM_SYNTHETIC` | **46 / 46 OK** (`9.824s`, `exit 0`) |
| `make verify-44-gates` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_ALL_44_GATES_DRY_RUN_SIMULATED_BACKUP` (`verified=44/44`, `g43_to_g44_all_passed=True`, `persistent_emmc_writes_authorized=False`) |
| `make verify-17pillar-recovery` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_RECOVERY_MASTER_SUITE` (`pillars=17/17`, `uart_scenarios=10/10`, `passive_tx_bytes_emitted=0`, `physical_device_writes=0`) |
| `make verify-sd-stageb-bundle` | `LOCAL_DONOR_O_RDONLY` | `status=OK` (`sd_entries=24`, `tmpfs_mib=9.234`, `eh_scenarios=6/6`, `eh1_us=47`, `h0_eq_h3=16/16`, `power_loss=5/5`, `emmc_writes_auth=False`) |
| `make verify-milestone-147` | `LOCAL_DONOR_O_RDONLY` | `status=OK pillars=6/6 gate44=41/44 recovery=17/17 otp=0 rpmb=0 passive_tx=0 auditors=28/28 vm_stages=24/24 p136_u456=True p143_eh1_us=47 h0_eq_h3=16/16 r28=3/3 r29=3/3 usb_tx=0` (`milestone147_sha256=8cf93889c988d96a...`) |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-147` | `CLEAN_ROOM_SYNTHETIC` | `status=OK pillars=6/6 gate44=41/44 recovery=17/17 otp=0 rpmb=0 passive_tx=0 auditors=28/28 vm_stages=24/24 p136_u456=True p143_eh1_us=47 h0_eq_h3=16/16 r28=3/3 r29=3/3 usb_tx=0` (`milestone147_sha256=52abcebde2669420...`) |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Clean-Room Audit | `git status --porcelain binary/pyc audit: CLEAN` (`ALL GREEN in 0.05s`) |
