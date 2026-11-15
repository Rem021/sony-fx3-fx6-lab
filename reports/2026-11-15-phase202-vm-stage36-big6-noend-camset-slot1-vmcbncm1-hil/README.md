# Phase 202（VM Stage 36 `36/36`）：`ILME-FX3` `BIG6` `[Home (Lower Left)]` 零物理 e-ND 执行器防火墙、Slot-1 `CAMSET` 双介质根路径分流与 `VMC-BNCM1` 机身专属 `TC IN` / HDMI `TC OUT` HIL 协同仿真报告

## 1. 结论先行

基于已合入的 **VM Stage 35（`stage35_realhw_fan_pwm_shutter_angle_lut_split_hil`）** 与 [Wave-26 真实硬件情报](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/reports/2026-11-15-global-sony-wave26-big6-home-aperture-nd-camset-slot1-path-vmcbncm1-tcin-only-intel/README.md)，已在 `outputs/fx3-vm/` 完成 **VM Stage 36（`36/36` 里程碑：`stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil`）** 闭环交付：

- **只读供体高速审计（实测事实）**：[`realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py) 以 `os.open(..., os.O_RDONLY)` 有界窗口（`<= 4096 B`）核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（含 `appFw.so` 中 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` 与 `CAMSET%02d`、`string_english_f.uxc` 中 `Home (Lower Left)` / `Save/Load Settings` / `Slot 1` / `Time Code Output` 等精确词条），冷启动耗时仅 **`0.0016s`**（远低于 `< 0.10s` 上限），进程内缓存命中 `< 0.0001s`；开启 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时零接触供体切换至确定性 `CLEAN_ROOM_SYNTHETIC` 基线（`raw_firmware_bytes_leaked == 0`）。
- **全板 36 阶段集成与运行性能（实测事实）**：[`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) 接入 `stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil` 与 `--skip-phase202`，全量 36 阶段（`Stage 1..36`）实测耗时 **`1.839s`（本地供体） / `0.442s`（洁净室）**，严格满足 `< 2.1s` local / `< 1.0s` clean-room 预算。
- **双模单测与全仓回归（实测事实）**：新增 **48 项**双模单元测试 [`test_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/tests/test_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py)，本地只读供体与洁净室双模以及全仓 `scripts/run_all_lab_tests.py --clean-only` 全部 `100%` 通过。

---

## 2. 四大核心支柱（Pillars A–D）实现要点

| 支柱 | 核心入口函数 | 关键硬件契约与安全门控 |
| :--- | :--- | :--- |
| **Donor Audit** | [`inspect_phase202_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py#L469-L607) | 12 份 FX3 `7.02` / FX6 `6.01` 供体 `O_RDONLY` 校验（`< 0.10s`）+ `CLEAN_ROOM_SYNTHETIC` 零泄漏回退（`raw_firmware_bytes_leaked == 0`）。 |
| **Pillar A** | [`probe_big6_home_lower_left_and_end_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py#L614-L746) | `ILME-FX3`（`0x91030080`）`BIG6`（`[Mode Settings] = [Fixed/Variable]` + 绑定自定义 `Home` 键）6 格磁贴（`FPS` / `ISO/Base ISO` / `Shutter Speed/Angle` / `Aperture/ND Filter` / `Picture Profile/Select LUT` / `White Balance`）+ 第 7 状态栏区；支持 `[Home (Lower Left)]` 在 E-Mount `[Aperture]` 与纯虚拟 `[ND Filter]` 显示间切换，并以 `EOPNOTSUPP`（`95`）硬拦截一切 `FX6` `1/4..1/128` 电动可变 e-ND CP 驱动帧（`e_nd_actuator_tx_count == 0`）。 |
| **Pillar B** | [`probe_slot1_camset_dual_media_and_cross_model_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py#L835-L1098) | 严格执行 `Slot 1` 专属（`Slot 2` 返回 `EINVAL` `22`）、最多 `10` 组（`CAMSET01.DAT .. CAMSET10.DAT`）、`MR` 模式灰显禁用（`EOPNOTSUPP` `95`）、`SD/SDHC/SDXC`（`/PRIVATE/SONY/SETTING/FX3/CAMSET/`）vs `CFexpress-A`（`/SONY/SETTING/FX3/CAMSET/`）双介质根路径分流、拦截 `ILME-FX3A` / `ILME-FX6` 跨机型 `.DAT`，并将 Stage-B 重定向至 `/tmp/fx6_camset_overlay`（直接写返回 `EROFS` `30`，`10/10 H0 == H3`）。 |
| **Pillar C & D** | [`probe_vmcbncm1_tcin_and_hdmi_tcout_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py#L1189-L1376) / [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py#L1379-L1443) | `VMC-BNCM1`（`A-5051-506-A`）机身 `Multi/Micro-USB` 单向 `TC IN`（`Movie` + `Preset` + `Free Run` 持续 `>= 10s` 点亮 `EXT-LK`，切 `S&Q` 或改 `TC` 立即释放），拦截 `XLR-H1` 手柄 Micro-USB 误插（`ENODEV` `19`）与反向 BNC `TC OUT`（`EOPNOTSUPP` `95`），建模标准 Type-A HDMI 数字 `TC OUT`（`Movie` 开启、`S&Q` 自动禁用），并硬锁 `persistent_emmc_writes_authorized = False` 等全部红线。 |

---

## 3. 修改文件清单（严格限定自有范围）

1. [outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py)（新增）
2. [outputs/fx3-vm/fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（更新：接入 Stage 36 与 `--skip-phase202`）
3. [outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/README.md)（更新：补充 Phase 202 Stage 36 `36/36` 文档与验证命令）
4. [outputs/fx3-vm/tests/test_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/outputs/fx3-vm/tests/test_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py)（新增：48 项双模单元测试）
5. [reports/2026-11-15-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h222-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/reports/2026-11-15-phase202-vm-stage36-big6-noend-camset-slot1-vmcbncm1-hil/README.md)（新增：本报告）

---

## 4. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

- Stage 36 独立摘要（本地供体 / 洁净室）：
  - `LOCAL_DONOR_RDONLY`：`digest=038b8bc8f22a`（`PASS`）
  - `CLEAN_ROOM_SYNTHETIC`：`digest=424aa78d49f6`（`PASS`）
- 36 阶段全板套件摘要（本地供体 / 洁净室）：
  - `LOCAL_DONOR_RDONLY`：`1.839s`，`digest=52f81f94bee6`（`PASS`）
  - `CLEAN_ROOM_SYNTHETIC`：`0.442s`，`digest=ec4633e28eb8`（`PASS`）
- 48 项 Stage 36 双模单测、全量 `outputs/fx3-vm/tests` 双模回归及 `scripts/run_all_lab_tests.py --clean-only` 全仓洁净室门禁均 `100%` 通过，零 `.pyc` / `__pycache__` 残留。
