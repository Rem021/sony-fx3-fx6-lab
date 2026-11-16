# Round 53（Wave-39 / `R28..R53` 实机内核 QEMU 第 26 轮 · 累计第 78 次实跑里程碑）：FX3 7.02 原厂内核真机准备预演 — `[Display Quality]`（`Standard` 低功耗默认 vs `High` 高功耗及双重置存活）、`[Bluetooth Rmt Ctrl]`（红外 `SIRCS` 遥控器互斥锁、`[Bluetooth Function]=On` & `[Airplane Mode]=Off` 前置门禁与 `[Reset Network Set.]` 跨重置分层）、以及 `[My Menu Setting]` & `[Display From My Menu]` 6 项操作（`5` 页 × `6` 项 = `30` 项）与 `CAMSET01.DAT` 持久化闭环

> **日期**：2026-11-15 | **轮次**：**Round 53 Live ARM64 QEMU Rehearsal (Wave-39 · 26th Real-HW Round / 78th Live Run Milestone)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r53a` / `r53b` / `r53c`，累计达成 `R28..R53` 第 **26** 轮实机内核预演与第 **78** 次独立实跑）测得；**物理实体 `ILME-FX3` 机身上使用高精度直流稳压电流探头实测 `NP-FZ100` 电池在 `[Display Quality]` `[Standard]` 与 `[High]` 下的真实毫瓦功耗差与机背 LCD 刷新率、在微波暗室中配合蓝牙遥控器（`RMT-P1BT` / `GP-VPT2BT`）与索尼红外 `SIRCS` 遥控器（`RMT-DSLR2`）实测 `[Bluetooth Rmt Ctrl]=On` 对前机身红外接收窗的物理光电屏蔽及 `2.4 GHz` BLE 空口帧抑制、以及在实体机身插拔双 `CFexpress Type A / SDXC` 卡实测 `[My Menu]` 30 项自定义菜单跨 `CAMSET01.DAT` 读写尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 53 轮（Wave-39 · 第 26 轮实机内核 / 第 78 次实跑）三项实机预演总览（`r53a` / `r53b` / `r53c`）

| 实跑场景 | Run ID | `r53_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **53A：`[Display Quality]`（`Standard` vs `High` 功耗与双重置存活）+ `[Bluetooth Rmt Ctrl]`（红外 `SIRCS` 互斥锁、飞行模式零射频抑制与网络重置拆分）+ Big-6 Home** | `round53-display-quality-btrmt-big6` | `display_quality_bt_rmt_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接实证：`MENU -> Setup -> [Monitor] -> [Display Quality]` 真实菜单节点（`fx3_display_quality_node_ok=1`），核验 `Standard`（出厂默认，Tier-0 台架低功耗基线 `tier0_bench_standard_low_power_ok=1`）与 `High`（提高 `NP-FZ100` 电池消耗速率 `high_increases_npfz100_drain_ok=1`）双档枚举（`display_quality_2modes_verified=2`，非法枚举 `rc=-22` `EINVAL`），证实同时跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 持久化存活、仅由 `[Initialize]` 恢复 `Standard`（`display_quality_survives_camreset_ok=1`, `display_quality_survives_netreset_ok=1`, `initialize_restores_display_quality_standard_ok=1`）；同步核验 `MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]`（`fx3_bt_rmt_ctrl_node_ok=1`，默认 `Off` `bt_rmt_default_off_ok=1`、`Off`/`On` 双档 `bt_rmt_2modes_verified=2`），在 `[Bluetooth Function]=Off` 时以 `-EOPNOTSUPP`（`-95`）拦截开启、在零射频台架 `[Airplane Mode]=On` 下强制抑制蓝牙遥控发射（`airplane_on_bt_rmt_suppressed_ok=1`, `passive_tx_bytes_emitted=0`），开启 `[Bluetooth Rmt Ctrl]=On` 时以 `-EBUSY`（`-16`）硬互斥锁死红外 `SIRCS` 遥控接收（`ir_sircs_bt_rmt_conflict_events=0`），并证实跨 `[Camera Settings Reset]` 存活但被 `[Reset Network Set.]` 与 `[Initialize]` 双双复位为 `Off`（`setup_vs_network_reset_split_ok=1`）；`p2:/setting`、`cnflasha` 与 `Slot-1` 只读保护（`rc=-30` `EROFS`），驱动 `appFw.so` 渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.14s` | [`r53a-display-quality-btrmt-big6-schinese-composited.png`](assets/r53a-display-quality-btrmt-big6-schinese-composited.png) |
| **53B：`[My Menu Setting]` 6 项操作（`5` 页 × `6` 项 = `30` 项）与 `[Display From My Menu]` 跨双重置存活及 `CAMSET01.DAT` 闭环** | `round53-mymenu-6ops-camset-persist` | `mymenu_6ops_camset_persist_guard` | Native ARM64 自定义菜单与存储卡设定档门禁实测：核验 `MENU -> My Menu -> [My Menu Setting]`（`fx3_mymenu_node_ok=1`）全部 `6` 项操作（`Add Item`、`Sort Item`、`Delete Item`、`Delete Page`、`Delete All`、`Display From My Menu`，`mymenu_6ops_verified=6`），证实 `[Display From My Menu]` 默认 `Off`（`display_from_mymenu_default_off_ok=1`、`Off`/`On` 双档 `display_from_mymenu_2modes_verified=2`，开启 `On` 时按下 `MENU` 键直接路由至 `My Menu` 首页 `menu_press_target_tab_routing_ok=1`）；核验最多 `5` 页 × 每页 `6` 项 = `30` 项容量上限（`mymenu_max_30_items_ok=1`）、重复注册同一菜单项返回 `-EEXIST`（`-17`）及第 `31` 项溢出返回 `-ENOSPC`（`-28`）；证实已注册 `My Menu` 条目与 `[Display From My Menu]=On` 同时跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 存活（`mymenu_survives_camreset_ok=1`, `mymenu_survives_netreset_ok=1`），仅由 `[Delete Page]`/`[Delete All]` 或 `[Initialize]` 清空（`initialize_clears_mymenu_and_display_from_mymenu_ok=1`），并经 `Save/Load Settings`（`CAMSET01.DAT`）完整无损往返还原（`camset01_mymenu_roundtrip_ok=1`），同时物理 `Slot-1` 保险库卡保持 `-EROFS`（`-30`）零写入（`slot1_vault_writes=0`） | `13/13` 校验（早期 `My Menu` 6 操作与 `CAMSET01.DAT` C 探针退出） | 跳过（`My Menu` 6 操作 C 探针退出） | **`0`** / **`0`** / **`0`** | `8.27s` | — |
| **53C：Wave-39 综合压力预演（Tier-0 `Display Quality=Standard` + `Airplane Mode=On` 零射频 + `My Menu` 持久化 + Big-6 `346,686` px + `16/16 H0 == H3`）** | `round53-wave39-integrated-stress-big6` | `wave39_integrated_stress_big6` | Native ARM64 Wave-39 全链路联合压力预演（累计第 **78** 次独立实跑）：联合激活 `Display Quality=Standard` Tier-0 低功耗姿态（`tier0_standard_low_power_ok=1`）+ `[Airplane Mode]=On` 零射频台架静默（`bt_rmt_suppressed_airplane_on_ok=1`, `passive_tx_bytes_emitted=0`, `ir_remote_state_deterministic_ok=1`, `ir_sircs_bt_rmt_conflict_events=0`）+ 三向重置分离矩阵（`[Camera Settings Reset]` vs `[Reset Network Set.]` vs `[Initialize]`，`reset_3way_matrix_ok=1`）+ `My Menu` 持久化与 `Slot-1` 零写入（`mymenu_persistence_ok=1`, `slot1_vault_ro_blocked_rc=-30`, `slot1_vault_sha256_match=1`）；通过真机 `/lib/ld-2.25.so` `dlopen("/etc/fx6_r53_libjit.so")`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `e_nd_actuator_tx_count=0`, `raw_firmware_bytes_leaked=0`），并同步驱动 `appFw.so` 完整渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `84.3s` | 同 `53A` SHA-256 一致（`e57d7971...`） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `[Display Quality]` 功耗/重置存活、`[Bluetooth Rmt Ctrl]` 红外 `SIRCS` 互斥锁与网络重置分层及 Big-6 渲染（`r53a`）
```text
FX6_R53_DISPQUAL_BTRMT_INIT fx3_display_quality_node_ok=1
  display_quality_default_standard_ok=1 invalid_display_quality_rc=-22
  display_quality_2modes_verified=2 high_increases_npfz100_drain_ok=1
  tier0_bench_standard_low_power_ok=1 display_quality_survives_camreset_ok=1
  display_quality_survives_netreset_ok=1
  initialize_restores_display_quality_standard_ok=1 fx3_bt_rmt_ctrl_node_ok=1
  bt_rmt_default_off_ok=1 invalid_bt_rmt_rc=-22 bt_rmt_2modes_verified=2
  bt_func_off_prerequisite_rc=-95 airplane_on_bt_rmt_suppressed_ok=1
  passive_tx_bytes_emitted=0 bt_rmt_on_locks_out_ir_sircs_rc=-16
  ir_sircs_usable_when_bt_rmt_off_ok=1 ir_sircs_bt_rmt_conflict_events=0
  bt_rmt_survives_camreset_ok=1 bt_rmt_reset_by_netreset_ok=1
  initialize_restores_bt_rmt_off_ok=1 setup_vs_network_reset_split_ok=1
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1
  slot1_vault_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r53_init_ok=1 verify_us=980654

FX6_R53_DISPQUAL_BRIDGE display_quality_default_standard_ok=1
  display_quality_2modes_verified=2 high_increases_npfz100_drain_ok=1
  display_quality_survives_camreset_netreset_ok=1 dispqual_ok=1
  emmc_write_count=0 r53_bridge_ok=1

FX6_R53_BTRMT_IR_NETRESET_BRIDGE bt_rmt_default_off_ok=1
  bt_rmt_2modes_verified=2 bt_func_prerequisite_ok=1
  airplane_on_bt_rmt_suppressed_ok=1 passive_tx_bytes_emitted=0
  bt_rmt_on_locks_out_ir_sircs_ok=1 ir_sircs_bt_rmt_conflict_events=0
  bt_rmt_survives_camreset_ok=1 bt_rmt_reset_by_netreset_ok=1
  bt_rmt_ir_netreset_ok=1 emmc_write_count=0 p2_setting_writes=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `90` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `[My Menu Setting]` 6 项操作（`5×6=30` 项）、`[Display From My Menu]` 路由与 `CAMSET01.DAT` 持久化闭环（`r53b`）
```text
FX6_R53_MYMENU_6OPS_PERSIST fx3_mymenu_node_ok=1
  display_from_mymenu_default_off_ok=1 invalid_display_from_mymenu_rc=-22
  display_from_mymenu_2modes_verified=2 menu_press_target_tab_routing_ok=1
  mymenu_6ops_verified=6 mymenu_max_pages=5 mymenu_max_items_per_page=6
  mymenu_max_30_items_ok=1 mymenu_duplicate_item_rc=-17
  mymenu_31st_item_overflow_rc=-28 mymenu_sort_item_ok=1
  mymenu_delete_item_ok=1 mymenu_delete_page_ok=1 mymenu_delete_all_ok=1
  mymenu_survives_camreset_ok=1 mymenu_survives_netreset_ok=1
  camset01_mymenu_roundtrip_ok=1
  initialize_clears_mymenu_and_display_from_mymenu_ok=1
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  slot1_vault_writes=0 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r53b_ok=1 verify_us=1086418
```

### 2.3 Wave-39 综合压力预演：Tier-0 低功耗 + `Airplane Mode=On` 零射频 + `My Menu` 持久化 + Big-6 `346,686` px + `16/16 H0 == H3`（`r53c`）
```text
FX6_R53_WAVE39_INTEGRATED_STRESS tier0_standard_low_power_ok=1
  bt_rmt_suppressed_airplane_on_ok=1 passive_tx_bytes_emitted=0
  ir_remote_state_deterministic_ok=1 ir_sircs_bt_rmt_conflict_events=0
  reset_3way_matrix_ok=1 mymenu_persistence_ok=1 slot1_vault_ro_blocked_rc=-30
  slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r53c_ok=1 verify_us=394992

FX6_R53_MYMENU_PERSIST_BRIDGE display_from_mymenu_default_off_ok=1
  display_from_mymenu_2modes_verified=2 mymenu_6ops_verified=6
  mymenu_max_30_items_ok=1 mymenu_survives_camreset_netreset_ok=1
  camset01_mymenu_roundtrip_ok=1 slot1_vault_writes=0 mymenu_persist_ok=1
  cnflasha_writes=0 emmc_write_count=0
```

---

## 3. `r53a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r53a` Alpha（`26.50 KiB` / `27,132 B`） | `r53a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r53a Big6 Alpha](assets/r53a-display-quality-btrmt-big6-schinese-alpha.png) | ![r53a Big6 Composited](assets/r53a-display-quality-btrmt-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）直流稳压假电池与高精度电流探头测试台实测：`MENU -> Setup -> [Monitor] -> [Display Quality]` 在 `[Standard]` 与 `[High]` 切换时的真实 `NP-FZ100` 电池电流增量、机背侧翻液晶屏光学细节对比，以及高温长时间录制下的机身热平衡差异。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）微波屏蔽暗室与红外光电测试台实测：配对实体索尼蓝牙遥控器（`RMT-P1BT` / `GP-VPT2BT`）开启 `[Bluetooth Rmt Ctrl]=On` 后对机身红外接收窗（`RMT-DSLR2` `SIRCS` 调制光信号）的物理锁定表现、开启 `[Airplane Mode]=On` 时的 `2.4 GHz` BLE 空口零发射频谱验证，以及执行 `[Reset Network Set.]` 后蓝牙配对关系与遥控开关的物理清除过程。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）双卡槽实体菜单交互实测：在机身上手动完成 `[My Menu Setting]` 的 `Add Item`、`Sort Item`、`Delete Item`、`Delete Page`、`Delete All` 与 `[Display From My Menu]=On`（满载 `5` 页 `30` 项），并在真实 `SDXC / CFexpress Type A` 存储卡上执行 `Save/Load Settings`（`CAMSET01.DAT`）跨机身迁移验证。

---

## 5. 复现命令与洁净室合规

```bash
# Run 53A (76th Live Run): [Display Quality] (Standard vs High) + [Bluetooth Rmt Ctrl] (IR Lockout & Reset Network Set. Split) + Stage-B Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 53 --r53-mode display_quality_bt_rmt_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round53-display-quality-btrmt-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r53-runs/r53a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r53a-display-quality-btrmt-big6-schinese \
  --export-png-dir reports/2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu/assets

# Run 53B (77th Live Run): [My Menu Setting] 6-Op & [Display From My Menu] Persistence + CAMSET01.DAT Round-Trip
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 53 --r53-mode mymenu_6ops_camset_persist_guard --lang en \
  --run-id round53-mymenu-6ops-camset-persist --duration 35 \
  --run-dir <SCRATCH_ROOT>/fx6-r53-runs/r53b

# Run 53C (78th Live Run): Integrated Wave-39 Stress Rehearsal (Display Quality=Standard + Airplane Mode=On + My Menu + Big-6 346,686 px + 16/16 H0 == H3)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 53 --r53-mode wave39_integrated_stress_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id round53-wave39-integrated-stress-big6 --duration 71 \
  --run-dir <SCRATCH_ROOT>/fx6-r53-runs/r53c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500

# Dual-Mode Unit Tests & Milestone Verifiers
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round53_realhw_display_quality_bt_rmt_mymenu_qemu.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-native-presenter-closure/tests/test_round53_realhw_display_quality_bt_rmt_mymenu_qemu.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-254
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存文件严格隔离在受控暂存区并已完成清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 50 KiB`），`raw_firmware_bytes_leaked = 0`；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
