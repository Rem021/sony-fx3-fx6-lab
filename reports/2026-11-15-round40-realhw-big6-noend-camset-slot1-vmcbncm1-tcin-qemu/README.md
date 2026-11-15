# Round 40（第 40 轮里程碑实跑）：FX3 7.02 原厂内核真机准备预演 — `BIG6` `[Home (Lower Left)]` 零 e-ND 驱动护栏、Slot-1 专属 `CAMSET` 双介质目录分裂与 `VMC-BNCM1` 机身专属 `TC IN` / HDMI `TC OUT` 规则

> **日期**：2026-11-15 | **里程碑**：**40th Milestone QEMU Rehearsal** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r40a` / `r40b` / `r40c`）测得；**物理实体 `ILME-FX3` 机身上电切换 `[BIG6]` 与 E 卡口电动光圈电机、实体 `SDXC` / `CFexpress Type A` 存储卡 `CAMSET01..10.DAT` 读写与模式转盘 `MR` 联锁、以及实体 `VMC-BNCM1`（`A-5051-506-A`）连接外部 SMPTE LTC 发生器与外部 HDMI 录机采集测试尚未在物理相机上电执行**（未测物理边界见 §4）。

---

## 1. 第 40 轮里程碑三项实机预演总览（`r40a` / `r40b` / `r40c`）

| 实跑场景 | Run ID | `r40_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **40A：`BIG6`（`[Mode Settings] = [Fixed/Variable]`）六宫格拓扑 + `[Home (Lower Left)]`（`Aperture` vs `ND Filter`）零 e-ND 驱动防火墙 + Big-6 Home** | `r40a-big6-noend-schinese` | `big6_home_noend_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接验证完整 `BIG6` 6 宫格参数（`FPS`、`ISO/Base ISO`、`Shutter Speed/Angle`、`Aperture/ND Filter`、`Picture Profile/Select LUT`、`White Balance`）及底部状态栏（`big6_tile_count=6`, `tiles_verified=6`），拦截非 `Fixed/Variable` 或未绑定 `[Home]` 键进入（`rc=-22` `EINVAL`）；放行 `[Home (Lower Left)]` 在 E 卡口 `Aperture`（`F2.8`, `rc=0`）与虚拟元数据 `ND Filter`（`1/4..1/128`, `rc=0`）间双向切换，同时**硬拦截全部 6 档 `FX6` 电动可变 e-ND（`1/4..1/128`）CP 驱动指令**（`rc=-95` `EOPNOTSUPP`, `end_stops_blocked=6`, **`e_nd_actuator_tx_count=0`**），并渲染简体中文 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.50s` | [`r40a-big6-noend-schinese-composited.png`](assets/r40a-big6-noend-schinese-composited.png) |
| **40B：Slot-1 专属 `CAMSET01.DAT .. CAMSET10.DAT` 双介质路径分裂（`SD` vs `CFexpress-A`）、`MR` 锁死与跨机型 `.DAT` 防火墙** | `r40b-camset-slot1-split` | `camset_slot1_dualmedia_split` | Native ARM64 `CAMSET` 校验器证实仅 **Slot 1** 允许读写最多 `10` 组设定档，且精确路由双介质非对称目录（`SD`: `/PRIVATE/SONY/SETTING/FX3/CAMSET/` `10/10` vs `CFexpress Type A`: `/SONY/SETTING/FX3/CAMSET/` `10/10`）；硬拒 **Slot 2**（`rc=-22` `EINVAL`）、硬拒混用错位根目录（`rc=-22`）、硬拒第 `11` 组 `Save New`（`rc=-28` `ENOSPC`，但允许覆盖已有 `1..10` 槽 `rc=0`）、在 `MR`（`Recall Camera Setting`）模式下硬锁死 `Save/Load Settings`（`rc=-16` `EBUSY`）、硬拒 `ILME-FX3A` / `ILME-FX6` 跨机型 `.DAT` 魔数头（`rc=-79` `ELIBBAD`），并将 Stage-B 配置完全隔离于 `/tmp/fx6_camset_overlay`（`p2_write_blocked_rc=-30`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期 `CAMSET` 校验退出） | 跳过（`CAMSET` C 探针退出） | **`0`** / **`0`** / **`0`** | `5.97s` | — |
| **40C：`VMC-BNCM1`（`A-5051-506-A`）机身专属 `TC IN`（`EXT-LK` `>=10s` 保持）、`XLR-H1` 手柄阻断、BNC `TC OUT` 阻断与 HDMI 数字 `TC OUT` + `16/16 H0 == H3`** | `r40c-vmcbncm1-tcin-hdmi` | `vmcbncm1_tcin_hdmi_tcout` | Native ARM64 时间码探针证实 `VMC-BNCM1`（`A-5051-506-A`, `20cm`）仅在机身 `Multi/Micro USB` + `Movie` + `TC Make=Preset` + `TC Run=Free Run` 连续输入 `>=10,000 ms` 后锁定 `EXT-LK` 并激活拔线保持（`9,999 ms` 返回 `rc=-11` `EAGAIN`；`10,000 ms` 返回 `rc=0`, `ext_lk_locked=1`, `holdover_active=1`），切入 `S&Q` 或改动 `TC Make`/`TC Run`/`TC Preset` 立即释放外锁（`locked=0`）；硬拒 `XLR-H1` 手柄 Micro-USB 挂载 `VMC-BNCM1`（`rc=-19` `ENODEV`）与 BNC 反向驱动 `TC OUT`（`rc=-95` `EOPNOTSUPP`, `bnc_tcout_tx_count=0`）；验证全尺寸 Type-A HDMI 数字 `TC OUT`（`Movie` 放行 `rc=0` vs `S&Q` 禁用 `rc=-95`），通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期 `VMC-BNCM1` 校验退出） | 跳过（`VMC-BNCM1` C 探针退出） | **`0`** / **`0`** / **`0`** | `4.91s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `BIG6` 六宫格拓扑、`[Home (Lower Left)]`（`Aperture` / `ND Filter`）切换与零 e-ND 驱动防火墙（`r40a`）
```text
FX6_R40_BIG6_NOEND_INIT mode_settings=Fixed_Variable home_key_bound=1
  not_fixed_var_reject_rc=-22 no_home_key_reject_rc=-22 home_enter_rc=0
  big6_tile_count=6 status_bar_zone=1 tiles_verified=6
  default_lower_left=Aperture toggle_nd_filter_rc=0 toggle_aperture_rc=0 invalid_ll_reject_rc=-22
  emount_aperture_rc=0 virtual_nd_display_rc=0 virtual_nd_range_reject_rc=-34
  end_1_4_reject_rc=-95 end_1_128_reject_rc=-95 end_stops_blocked=6 e_nd_actuator_tx_count=0
  appfw_present=1 shim_present=1 emmc_write_count=0 r40_init_ok=1 verify_us=586254

FX6_R40_BIG6_NOEND_BRIDGE big6_tiles=6 mode_settings=Fixed_Variable
  lower_left_modes=Aperture_NDFilter end_actuator_reject_rc=-95
  e_nd_actuator_tx_count=0 virtual_nd_metadata_only=1
  big6_topology_ok=1 no_end_firewall_ok=1 emmc_write_count=0 r40_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `137` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Slot-1 专属 `CAMSET01..10.DAT` 双介质目录分裂、`MR` 模式锁死与跨机型 `.DAT` 防火墙（`r40b`）
```text
FX6_R40_CAMSET_SLOT1_SPLIT sd_camset_dir=/PRIVATE/SONY/SETTING/FX3/CAMSET/
  cfx_camset_dir=/SONY/SETTING/FX3/CAMSET/
  sd_saved_count=10 sd_loaded_count=10 cfx_saved_count=10 cfx_loaded_count=10
  sd_save_11th_reject_rc=-28 cfx_save_11th_reject_rc=-28 overwrite_existing_slot_rc=0
  slot2_save_reject_rc=-22 slot2_load_reject_rc=-22
  mr_mode_save_reject_rc=-16 mr_mode_load_reject_rc=-16
  wrong_prefix_on_sd_rc=-22 wrong_prefix_on_cfx_rc=-22
  fx3a_dat_reject_rc=-79 fx6_dat_reject_rc=-79 excluded_machine_bound_fields=5
  stageb_overlay_dir=/tmp/fx6_camset_overlay stageb_overlay_saved=10
  p2_write_blocked_rc=-30 p2_setting_sha256_match=1 slot1_fx3_camset_intact=10
  appfw_camset_ok=1 shim_elf_ok=1 emmc_write_count=0 r40b_ok=1 verify_us=599200
```

### 2.3 `VMC-BNCM1`（`A-5051-506-A`）机身专属 `TC IN`（`EXT-LK` `>=10s`）、`XLR-H1` / BNC 阻断与 HDMI 数字 `TC OUT`（`r40c`）
```text
FX6_R40_VMCBNCM1_TCIN_HDMI adapter_model=VMC-BNCM1 part_no=A-5051-506-A cable_len_cm=20
  body_usb_port=Multi_Micro_USB pre_10s_9999ms_rc=-11 body_movie_preset_freerun_10s_rc=0
  ext_lk_locked=1 holdover_active=1
  release_on_sq_locked=0 release_on_tcmake_regen_locked=0
  release_on_tcrun_recrun_locked=0 release_on_tcpreset_edit_locked=0
  xlrh1_handle_usb_reject_rc=-19 bnc_tcout_reject_rc=-95 bnc_tcout_tx_count=0
  hdmi_type_a_movie_tcout_rc=0 hdmi_movie_tcout_active=1
  hdmi_sq_tcout_reject_rc=-95 hdmi_sq_tcout_active=0 hdmi_sq_tcout_disabled=1
  p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16
  drift_bits=0 emmc_write_count=0 r40c_ok=1 verify_us=6296
```

---

## 3. `r40a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r40a` Alpha（`26.21 KiB` / `26,842 B`） | `r40a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r40a Big6 Alpha](assets/r40a-big6-noend-schinese-alpha.png) | ![r40a Big6 Composited](assets/r40a-big6-noend-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）机身进入 `[Shooting] -> [Shooting Mode] -> [BIG6]`（`[Mode Settings] = [Fixed/Variable]`）并切换 `[Menu] -> [Setup] -> [Operation Customize] -> [BIG6 Home Set.] -> [Home (Lower Left)] = [Aperture] / [ND Filter]` 时的 E 卡口镜头光圈电机实测。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）Slot-1 实体 `SDXC`（`/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01..10.DAT`）与 `CFexpress Type A`（`/SONY/SETTING/FX3/CAMSET/CAMSET01..10.DAT`）存储卡 `Save/Load Settings` 实测及模式转盘 `MR` 档位菜单灰显核验。
3. 物理 Sony `VMC-BNCM1`（`A-5051-506-A`）`0.2 m` 转接线连接 `ILME-FX3` 机身 `Multi/Micro USB` 接口接入外部 SMPTE LTC 时码器（`>=10 s` 锁定 `EXT-LK` 与拔线保持精度）及外部录机通过全尺寸 Type-A HDMI 接收数字 `TC OUT` 的台架核验。

---

## 5. 复现命令与洁净室合规

```bash
# Run 40A: BIG6 6-Tile Topology + [Home (Lower Left)] Zero e-ND Actuator Firewall + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 40 --r40-mode big6_home_noend_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r40a-big6-noend-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r40-runs/r40a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r40a-big6-noend-schinese \
  --export-png-dir reports/2026-11-15-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu/assets

# Run 40B: Slot-1-Only CAMSET01..10.DAT Dual-Media Path Split (SD vs CFexpress-A), MR Lockout & Cross-Model .DAT Firewall
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 40 --r40-mode camset_slot1_dualmedia_split --lang en --run-id r40b-camset-slot1-split \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r40-runs/r40b

# Run 40C: VMC-BNCM1 Body-Only TC IN (EXT-LK >=10s), XLR-H1 / BNC Blocks & HDMI Digital TC OUT + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 40 --r40-mode vmcbncm1_tcin_hdmi_tcout --lang en --run-id r40c-vmcbncm1-tcin-hdmi \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r40-runs/r40c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
