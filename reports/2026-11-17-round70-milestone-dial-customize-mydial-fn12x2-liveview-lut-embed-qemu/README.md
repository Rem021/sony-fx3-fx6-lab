# Round 70 Milestone（Wave-56 · `70th` Round Milestone · `43/43` 实机预演轮次 `R28..R70` · 第 `127..129` 次实跑 -> `129/129` 总实跑 · `86/86` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `Setup -> [Dial Customize]` Ver.2.00+ 5 项树与休眠 `Rear Dial L/R` 拦截、3 物理转盘 `My Dial 1..3`（空组跳过与锁定临时覆盖）+ `12+12` `Fn Menu` 拆分、Still 专用 `[Live View Display Set.]` 3 项非对称复位与 3 种 `[Grid Line]` 清洁 HDMI 隔离，以及 `[Manage User LUTs]` 1..16 只读导入 + 容器 `[Embed LUT File]` vs `[PPLUT1..4]` 像素烘焙 & Slot-1 `EROFS=30` 防火墙

## 结论先行

- **实测结论**：在未修改的 Sony `ILME-FX3 Ver. 7.02` 原厂 ARM64 Linux 内核（`4.9.337-scel+`）与真机动态链接器 `/lib/ld-2.25.so` 上，完成 **Round 70 Milestone** 三路独立 QEMU 实机预演（`r70a` / `r70b` / `r70c`，达成 **`70th` Round Milestone · `43/43` 实机预演轮次 `R28..R70` · `129/129` 次独立实跑 · `86/86` 张 `<= 27,467 B` PNG 视觉凭证**），全部 **`crashes == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`dormant_dial_bypass_events == 0`、`mydial_lock_override_breach == 0`、`fn_empty_bypass_events == 0`、`hdmi_clean_feed_grid_baked_pixels == 0`、`external_cube_sidecar_files == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`、`e_nd_actuator_tx_count == 0`、`raw_firmware_bytes_leaked == 0`**，且 `r70c` 达成 **`16/16 H0 == H3`（`drift_bits=0`）**；`r70a` 驱动 `appFw.so` 渲染简体中文 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`），导出 `26,842 B` Alpha PNG 与 `27,147 B` Composited PNG（均 `<= 27,467 B`）。
- **推断与物理边界**：基于本地 `os.O_RDONLY` 供体审计与 QEMU 内核实跑确认了 Wave 56 四大支柱门禁、休眠符号（`Dial Setup` / `Dial/Wheel Setup` / `Dial / Wheel Lock` / `Rear Dial L/R` / `CUSTOM_GRID_LINE0..3` / `GOLDEN_RATIO_GRID`）的 fail-closed `-95 EOPNOTSUPP` 拦截、`My Dial 1..3` 空组 `--` 跳过与 `[Lock Operation Parts]` 临时解锁覆盖、`12 Still + 12 Movie` `Fn Menu Settings` 隔离、`[Live View Display Set.]` 与 `[Manage User LUTs]`/`[Embed LUT File]`/`[PPLUT1..4]` 非对称复位边界，以及针对 `Slot 1` 录制与写的 Tier-0 保险库 `-30 EROFS` 拦截；**物理实体 `ILME-FX3`（Ver. 7.02）与 `ILME-FX6`（Ver. 6.01）机台台架动作（实体前拨盘/单后拨盘/控制拨轮与镜头功能环手感、`MENU+Fn` 5 秒长按全锁与 `My Dial` 覆盖、`Bright Monitoring` 联动真实 LCD 与外录机清洁 HDMI 信号分析、SDXC/CFexpress 实卡 `.cube` 读取与容器嵌入录像/`PPLUT1..4` 烘焙及物理 `Slot-1` 写保护）尚未上电执行，详见 §4。**

> **日期**：2026-11-17 | **轮次**：**Round 70 Milestone (`70th` Round · `43/43` Real-HW Rounds · Wave-56 · `127th..129th` Live Runs -> `129/129` Total Live Runs, `86/86` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测事实 vs 推断界定**：§1–§3 与 §5 命令行参数及遥测输出为 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实测记录；Wave-56 原生 UXC/ELF 菜单行为对照源自 [`reports/2026-11-17-global-sony-wave56-dial-wheel-setup-mydial-fn-menu-liveview-lut-embed-intel/README.md`](../2026-11-17-global-sony-wave56-dial-wheel-setup-mydial-fn-menu-liveview-lut-embed-intel/README.md) 实测逆向与官方手册映射，物理相机硬件电气动作属于未执行台架推断范围（见 §4）。

---

## 1. 第 70 轮里程碑（Wave-56 · `70th` Round Milestone / `43/43` 实机轮次 / `127th..129th` -> `129/129` 次实跑 / `86/86` PNG）三项实机预演总览（`r70a` / `r70b` / `r70c`）

| 实跑场景 | Run ID | `r70_mode` | 核心硬件/安全门禁实测结果（`实测事实`） | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **70A（第 127 次实跑）：Wave-56 四大支柱 — 5 项 `[Dial Customize]` 与休眠 `Dial Setup`/`Lock`/`Rear Dial L/R`、3 物理转盘 `My Dial 1..3` 锁定覆盖 + `12+12` `Fn Menu`、Still 3 项 `[Live View Display Set.]` 非对称复位与 3 种 `[Grid Line]` 清洁 HDMI 隔离、`[Manage User LUTs]` 只读导入与 `[Embed LUT File]` vs `[PPLUT1..4]` + Slot-1 `EROFS=30` + Big-6 Home** | `r70a` | `dial_mydial_fn12x2_liveview_lut_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 `Setup -> [Dial Customize]`（`_g 0x62ed`）**Ver.2.00+ 5 项仅 `Initialize` 复位树**：`Custom Key/Dial Set.`（Still `_f 0x6290` / Movie `_f 0x73a0`）、`My Dial Settings`（`_f 0x6538`）、`Av/Tv Rotate`（`_f 0x72e3`: `Normal`/`Reverse`）、`Function Ring(Lens)`（`_f 0x715e`: `Power Focus` / `APS-C/S35 / Full Frame`）、`Lock Operation Parts`（`_f 0x6904`: `Off` / `Multi-Selector Only` / `Dial + Wheel` / `All`，长按 `Fn` 或 `MENU+Fn` 5s 全锁），拒绝旧版/休眠 `Dial Setup`、`Dial/Wheel Setup`（`_f 0x6a89`）、`Dial / Wheel Lock`（`0xe352`）、`Rear Dial L/R`（`_f 0x6a5c`/`0x680d`）（`-95 EOPNOTSUPP`），对比 `ILME-FX6`（`Multi Function Dial` + `Grip/Handle/IRIS/ND Dials` + 物理 `HOLD` 开关）；(2) 核验 **3 物理转盘拓扑**（`Front Dial _f 0x6d2a`、单 `Rear Dial _f 0x6b61`、`Control Wheel _f 0x6178`）、`My Dial 1..3`（`Hold`/`Toggle`/`1->2->3` 自动跳过全 `--` 空组且激活期间自动临时解锁 `[Lock Operation Parts]`）与 `12 Still + 12 Movie` `[Fn Menu Settings]`（`_g 0x614b`，全 `Not set 0xe0ac` 时触发 `_f 0x6220` 无效提示 `-22 EINVAL`），对比 `FX6` `Status Screens` + `Direct Menu`；(3) 核验 Still 专用 **`[Live View Display Set.]`**（`_f 0x6429`）3 项非对称复位：`Live View Display`（`Setting Effect ON`[def]/`OFF`，`Bright Monitoring` 下强制 `OFF`）与 `Exposure Effect`（仅 `Initialize`）vs 可 `[Camera Settings Reset]` 复位的 **`[Frame Rate Low Limit]`**（`On`/`Off`[def]），以及 3 种仅 `Initialize` `[Grid Line Display]` / `[Grid Line Type]`（`Rule of 3rds`/`Square`/`Diag. + Square`）与清洁 HDMI 隔离；(4) 核验 `[Manage User LUTs]`（`User1..16` `.cube` 从 SDXC `/Private/Sony/PRO/LUT` 或 CFexpress `/Sony/PRO/LUT` 只读导入，`slot1_data_sector_writes=0`）+ `[Select LUT]`（`s709`[def]，Resettable）+ `[Log Shooting Setting] -> [Embed LUT File]`（`On`[def]/`Off`，Resettable，非破坏性容器元数据嵌入）vs `[Picture Profile] -> PPLUT1..4`（不可逆像素烘焙，与 PP1..11 不同支持 Reset）+ **`Slot-1` Tier-0 保险库 `-30 EROFS` 防火墙**，并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r70_init_ok=1`, `r70_bridge_ok=1`, `verify_us=961796`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `77.73s` | [`r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-composited.png`](assets/r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-composited.png) |
| **70B（第 128 次实跑）：Fail-Closed Wave-56 防火墙 — 休眠 `Dial Setup/Lock/Rear Dial L/R`、`My Dial` 空组、全空 `Fn`、`S&Q` Live View 与 `Bright Monitoring`、`CUSTOM_GRID_LINE`、64B/65pt/Slot17 LUT、SD/SDHC Embed 锁定与 `Slot-1` LUT 写入 `EROFS=30` 拦截** | `r70b` | `wave56_dial_mydial_fn_liveview_lut_erofs_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截休眠 `Dial Setup` / `Dial/Wheel Setup` / `Dial / Wheel Lock` / `Rear Dial L` / `Rear Dial R`（`-95 EOPNOTSUPP`）、`Function Ring` 无效枚举（`-22 EINVAL`）与 `FX6` 无 `Av/Tv Rotate`/`Lock Operation Parts`（`-2 ENOENT`）vs `FX6` `Multi Function Dial` 成功（`0`）；(2) 拦截 `My Dial Hold` 空 `--` 槽（`-22 EINVAL`）、Movie 12 槽全 `Not set`（`0x6220` `-22 EINVAL`）、Fn 槽越界（`-22 EINVAL`）与 `FX6` 无 `My Dial`/`Fn Menu`（`-2 ENOENT`）vs `FX6` `Direct Menu` 成功（`0`）；(3) 拦截 `S&Q` 下 `[Live View Display Set.]` 全 3 项（`-16 EBUSY`）、`Bright Monitoring` 开启时切回 `Setting Effect ON`（`-16 EBUSY`）、网格越界（`-22 EINVAL`）、休眠 `CUSTOM_GRID_LINE0..3` / `GOLDEN_RATIO_GRID`（`-95 EOPNOTSUPP`）vs `FX6` `Marker` 成功（`0`）；(4) 拦截 `User17` 越界 / `64` 字节超长文件名 / `65pt` `.cube`（`-22 EINVAL`）、错配卡目录（`-2 ENOENT`）、`SD/SDHC` 卡 `[Embed LUT File]` 锁死（`-16 EBUSY`）、未导入 `PPLUT` 绑定（`-2 ENOENT`），以及 **`Slot-1` 创建 LUT 目录 / `[Embed LUT File]` 录制 / `PPLUT` 烘焙录制 + Vault / `AVF_INFO` / `P2` / `cnflasha` 写入（`-30 EROFS`**, `slot1_vault_sha256_match=1`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `emmc_write_count=0`, `r70b_ok=1`, `verify_us=920022`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `9.66s` | — |
| **70C（第 129 次实跑 · `70th` Round Milestone）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-56 非对称复位层级验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r70c` | `clean_unmount_wave56_reset_h0_h3_big6` | Native ARM64 Wave-56 联合预演（**`70th` Round Milestone · `43/43` 实机轮次 · 第 `129/129` 次独立实跑**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` **仅复位 `[Frame Rate Low Limit]->Off`（Live View 3 项中唯一）、`[Select LUT]->s709`、`[Embed LUT File]->On` 与 `[PPLUT1..4]->未链接`**，而**全 5 项 `[Dial Customize]`、`My Dial 1..3`、`12+12` `[Fn Menu Settings]`、`[Live View Display]`、`[Exposure Effect]`、`[Grid Line Display]`/`[Grid Line Type]` 与 `[Manage User LUTs]` `User1..16` 均跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_wave56_survivors_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave56_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `slot1_avf_info_mutated=0`, `slot1_data_sector_writes=0`, `e_nd_actuator_tx_count=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`osd=45`，`verify_us=410294`，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `80.50s` | 同 `70A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel 实测事实）

### 2.1 Wave-56 四大支柱初始化与 Stage-B 四路桥接（`r70a` — 第 127 次实跑）
```text
FX6_R70_WAVE56_INIT fx3_wave56_nodes_ok=1 uxc_tokens_ok=1 dial_tree_ok=1
  mydial_fn12x2_ok=1 liveview_grid_ok=1 lut_embed_erofs_ok=1
  dormant_dial_setup_rc=-95 dormant_dial_wheel_lock_rc=-95 dormant_rear_dial_r_rc=-95
  func_ring_invalid_rc=-22 fn_all_notset_rc=-22 bright_mon_lock_rc=-16 lv_movie_ebusy_rc=-16
  slot1_mkdir_erofs_rc=-30 lut_oob_rc=-22 slot1_embed_erofs_rc=-30 slot1_pplut_erofs_rc=-30
  p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  dormant_dial_bypass_events=0 mydial_lock_override_breach=0 fn_empty_bypass_events=0
  hdmi_clean_feed_grid_baked_pixels=0 external_cube_sidecar_files=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0 passive_tx_bytes_emitted=0
  e_nd_actuator_tx_count=0 cnflasha_writes=0 appfw_present=1 shim_present=1
  emmc_write_count=0 r70_init_ok=1 verify_us=961796

FX6_R70_DIAL_CUSTOMIZE_DORMANT_BRIDGE dial_5item_initonly_vs_fx6_ok=1
  dormant_dial_setup_lock_rear_lr_rejected_ok=1 fx6_mfd_grip_iris_nd_hold_ok=1
  dial_customize_dormant_guard_ok=1 dormant_dial_bypass_events=0 emmc_write_count=0 r70_bridge_ok=1

FX6_R70_MYDIAL3_FN12X2_SPLIT_BRIDGE three_dial_mydial123_skip_lock_override_ok=1
  fn_menu_12still_12movie_0x6220_guard_ok=1 fx6_status_screens_direct_menu_ok=1
  mydial3_fn12x2_split_ok=1 mydial_lock_override_breach=0 fn_empty_bypass_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R70_LIVEVIEW_GRID_HDMI_BRIDGE still_liveview_3item_asymmetric_reset_ok=1
  bright_monitoring_setting_effect_off_lock_ok=1 grid_3pattern_clean_hdmi_isolated_ok=1
  liveview_grid_hdmi_ok=1 hdmi_clean_feed_grid_baked_pixels=0 cnflasha_writes=0 emmc_write_count=0

FX6_R70_LUT_IMPORT_EMBED_EROFS_BRIDGE manage_user_luts_1to16_ro_import_ok=1
  embed_lut_container_vs_pplut14_bake_ok=1 slot1_lut_tier0_erofs30_ok=1
  lut_import_embed_erofs_ok=1 external_cube_sidecar_files=0 slot1_avf_info_mutated=0
  slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `58` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`149` 实时线程零崩溃。

### 2.2 Fail-Closed Wave-56 防火墙拦截明细（`r70b` — 第 128 次实跑）
```text
FX6_R70_WAVE56_GUARD dial_setup_rc=-95 dial_wheel_setup_rc=-95 dial_wheel_lock_rc=-95
  rear_dial_l_rc=-95 rear_dial_r_rc=-95 func_ring_invalid_rc=-22
  fx6_avtv_rc=-2 fx6_lock_rc=-2 fx6_mfd_ok_rc=0
  mydial_empty_hold_rc=-22 fn_movie_all_notset_rc=-22 fn_slot_oob_rc=-22
  fx6_mydial_rc=-2 fx6_fn_rc=-2 fx6_direct_menu_ok_rc=0
  sq_lv_disp_rc=-16 sq_exp_eff_rc=-16 sq_fr_low_rc=-16 bright_mon_on_rc=-16
  grid_oob_rc=-22 custom_grid_dormant_rc=-95 golden_grid_dormant_rc=-95 fx6_marker_ok_rc=0
  lut_slot17_rc=-22 lut_name64_rc=-22 lut_65pt_rc=-22 lut_bad_path_rc=-2
  sdhc_embed_locked_rc=-16 pplut_unimported_rc=-2
  slot1_mkdir_erofs_rc=-30 slot1_embed_erofs_rc=-30 slot1_pplut_erofs_rc=-30
  slot1_wave56_erofs_rc=-30 slot1_avf_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  dormant_dial_bypass_events=0 mydial_lock_override_breach=0 fn_empty_bypass_events=0
  hdmi_clean_feed_grid_baked_pixels=0 external_cube_sidecar_files=0
  slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r70b_ok=1 verify_us=920022
```

### 2.3 洁净卸载还原原厂、Wave-56 复位层级与 `16/16 H0 == H3`（`r70c` — 第 129 次实跑）
```text
FX6_R70_CLEAN_UNMOUNT_WAVE56_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave56_survivors_ok=1 initialize_restores_wave56_defaults_ok=1
  dormant_dial_bypass_events=0 mydial_lock_override_breach=0
  fn_empty_bypass_events=0 hdmi_clean_feed_grid_baked_pixels=0
  external_cube_sidecar_files=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0
  emmc_write_count=0 r70c_ok=1 verify_us=410294
```

---

## 3. `r70a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r70a` Alpha（`26.21 KiB` / `26,842 B`） | `r70a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r70a Big6 Alpha](assets/r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-alpha.png) | ![r70a Big6 Composited](assets/r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界（推断 vs 实测分割）

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX6` 相机上通电实测，**本次未运行**（当前 QEMU 探针基于 ELF/UXC 实测约束与 C 模型验证，属于预演级替代而非物理台架证据）：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）前拨盘、单后拨盘、控制拨轮、兼容镜头 `Function Ring(Lens)` 与 `[Lock Operation Parts]` 台架（验证 Ver. 2.00+ 5 项 `[Dial Customize]` 树、长按 `Fn` 与 `MENU+Fn` 5 秒锁定、`My Dial 1..3` 空组自动跳过及调用期间自动临时解除转盘锁定、`12 Still + 12 Movie` `[Fn Menu Settings]` 与全 `Not set` `0x6220` 阻断提示，对比 `ILME-FX6 Ver. 6.01` `Multi Function Dial`、`Grip/Handle/IRIS/ND Dials`、物理 `HOLD` 开关与 `Status Screens`/`Direct Menu`）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）LCD 与外录机清洁 HDMI 信号分析台架（验证 Still 专用 `[Live View Display Set.]` 3 项非对称复位：`Live View Display` 在 `[Bright Monitoring]` 下自动切至 `Setting Effect OFF`、`Exposure Effect` 与唯一支持 `[Camera Settings Reset]` 的 `[Frame Rate Low Limit]`，以及 3 种 `[Grid Line Type]` 在 `[HDMI Info. Display]=Off` 时仅叠于机身 LCD 而零污染 Clean HDMI 输出）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）双槽 SDXC/CFexpress Type A LUT 导入与录制台架（验证 `[Manage User LUTs]` `User1..16` `.cube` 从 SDXC `/Private/Sony/PRO/LUT` 或 CFexpress `/Sony/PRO/LUT` 只读导入、SD/SDHC 卡锁定 `[Embed LUT File]=Off`、`[Embed LUT File]=On` 非破坏性容器元数据内嵌 vs `[Picture Profile] -> PPLUT1..4` 不可逆像素烘焙与 Reset 清除，以及物理 `Slot-1` 写保护拦截 `AVF_INFO` 与数据扇区写入）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 70A (127th Live Run — 70th Round Milestone): Wave-56 4-Pillar Dial Customize / My Dial 1-3 + Fn 12+12 / Live View 3-Item + Grid Clean HDMI / User LUT Import + Embed vs PPLUT1-4 Slot-1 EROFS=30 + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 70 --r70-mode dial_mydial_fn12x2_liveview_lut_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r70a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round70-qemu/r70a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu/assets

# Run 70B (128th Live Run): Fail-Closed Wave-56 Guard (Dormant Dial Setup/Lock/Rear Dial L/R EOPNOTSUPP, Empty My Dial / All-NotSet Fn EINVAL, S&Q LiveView & BrightMon EBUSY, Dormant Custom Grid EOPNOTSUPP, LUT OOB/SDHC Embed/Slot-1 EROFS=30)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 70 --r70-mode wave56_dial_mydial_fn_liveview_lut_erofs_guard --sd-manifest-mode valid --lang en \
  --run-id r70b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round70-qemu/r70b

# Run 70C (129th Live Run — 70th Round Milestone / 43/43 Real-HW Rounds / 129/129 Live Runs / 86/86 PNGs): Clean Unmount Stock FX3 Restoration, Wave-56 Asymmetric Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 70 --r70-mode clean_unmount_wave56_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r70c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round70-qemu/r70c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`e_nd_actuator_tx_count == 0`、`dormant_dial_bypass_events == 0`、`mydial_lock_override_breach == 0`、`fn_empty_bypass_events == 0`、`hdmi_clean_feed_grid_baked_pixels == 0`、`external_cube_sidecar_files == 0`、`slot1_avf_info_mutated == 0`、`slot1_data_sector_writes == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
