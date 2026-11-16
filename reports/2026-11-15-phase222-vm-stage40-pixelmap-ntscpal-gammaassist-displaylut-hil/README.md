# Phase 222（VM Stage 40 `40/40` 里程碑）：真机 `ILME-FX3` `[Pixel Mapping]` 自动重启清零 `/tmp` & `cnflasha` 只读防火墙、`[NTSC/PAL Selector]` 跨 `[Camera Settings Reset]` 持久化与 `[Gamma Display Assist]` 4 档 vs `[Display LUT]` 锁定分离 HIL 协同仿真报告

## 1. 结论先行

已在独立工作树 `outputs/fx3-vm/` 闭环完成 **Task H246 — Phase 222（VM Stage 40 `40/40` 里程碑）** 真实硬件主线协同仿真器开发、全板 40 阶段编排接入与双模全量回归验证：

- **交付物清单（严格受控 5 文件所有权边界）**：
  1. 新增 Stage 40 核心协同仿真模块：[realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py)
  2. 更新 40 阶段全板编排器（接入 `stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil` 与 `--skip-phase222`）：[fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
  3. 新增 48 项双模单元测试套件（满足 `>= 45` 要求，含 40 阶段里程碑完整性、壁钟时延上限与源码 `os.O_RDONLY`/端口卫生断言）：[test_realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/tests/test_realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py)
  4. 更新虚拟机模块文档（Stage 40 `40/40` 里程碑章节与 CLI 指南）：[outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/README.md)
  5. 本里程碑验收报告（参考官方 `ILME-FX3 Ver. 7.02` 实测基线 [Wave-30 Real-Hardware Intel README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/reports/2026-11-15-global-sony-wave30-pixel-mapping-reboot-ntsc-pal-reset-persistence-gamma-assist-displaylut-intel/README.md)）。

## 2. 核心子模型（`Sub-models A–C` + 硬安全红线）实现与实测证据

### 2.1 双模高速 `os.O_RDONLY` 12 供体有界审计（实测冷启动 `2.84 ms < 0.02s`）与零字节泄露回退
- [`inspect_phase222_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py#L723-L822) 严格通过 `os.open(..., os.O_RDONLY)` 核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 采用 `<= 4096 B` 定点 `lseek` 窗口读取并带进程级签名缓存，实测冷启动仅 **`0.00284s`**）；实证 `string_english_f.uxc`（`373,820 B`）、`fx3_appfw`、`fx3_cpapp`、`fx3_libmpr` 与 `fx6_appfw` 包含全部 Wave-30 菜单词条与内部符号（`Auto Pixel Mapping`、`Pixel Mapping`、`Silent Mode`、`NTSC/PAL Selector`、`Camera Settings Reset`、`Initialize`、`TC Format`、`23.98p`、`25p`、`Gamma Display Assist`、`Gamma Disp. Assist Typ.`、`S-Log3→709(800%)`、`HLG(BT.2020)`、`HLG(709)`、`HLG Still Image`、`Log Shooting`、`Cine EI`、`Cine EI Quick`、`Flexible ISO`、`Display LUT`、`Display LUT Switch`、`AUTO_PIXEL_MAPPING`、`PIXEL_MAPPING`、`NTSC_PAL`、`AVCHD`、`GAMMA_DISP`、`LOG_SHOOTING`、`APR`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，`raw_firmware_bytes_leaked == 0`。

### 2.2 Sub-model A — `[Auto Pixel Mapping]` / 手动 `[Pixel Mapping]` 自动重启清零 `/tmp` & `cnflasha` 只读防火墙 HIL
- [`probe_pixel_mapping_reboot_and_cnflasha_firewall_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py#L830-L1020) 精确建模 `MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]` 与手动 `[Pixel Mapping]`：
  - `[Auto Pixel Mapping]` 默认开启为 `On`；当到期执行关机暗场采样时，即使 `[Silent Mode] = On`，机械快门仍按索尼官方规格正常闭合发声（`power_off_shutter_dark_frame_sound_emitted == True`）；若设为 `Off` 且距离上次校准 `>= 3` 天，发出推荐每 `3` 天手动执行校准告警（`three_day_manual_cadence_warning == True`）。
  - 手动 `[Pixel Mapping]` 在电池电量 `< 20%` 时以 `EOPNOTSUPP = 95` 拒绝执行（`low_battery_rejected == True`）；校准执行期间全锁定操作员控制输入（并发按键请求以 `EBUSY = 16` 拦截）；校准完成后**强制触发整机自动重启（Automatic Camera Restart）**，将易失性 `/tmp` Stage-B 绑定挂载 100% 清零并回到原厂 `ILME-FX3 Ver. 7.02 (Stock)`（`post_reboot_tmp_stage_b_mounts == ()`，`h0_equals_h2_verified == True`，`stage_b_tmp_mount_residuals_after_pixelmap_reboot == 0`）。
  - 严锁 `cnflasha` 出厂校准分区只读防火墙（`cnflasha_userspace_write_blocked == True`，用户态写入尝试返回 `EROFS = 30`，`cnflasha_mutation_bytes == 0`）。

### 2.3 Sub-model B — `[NTSC/PAL Selector]` 独占帧率 / `DF-NDF` 矩阵、开机横幅与 `[Camera Settings Reset]` 持久化 HIL
- [`probe_ntsc_pal_selector_reset_persistence_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py#L1075-L1229) 建模 `MENU -> Setup -> [Area/Date] -> [NTSC/PAL Selector]` 与 `[Setting Reset]`：
  - `NTSC` 开放 `23.98p`（NTSC 独占）、`29.97p`、`59.94p`、`119.88p`（及可选 DCI `24.00p`）与 `[TC Format]` `DF`/`NDF`（`23.98p`/`24.00p` 自动锁定 `NDF`）；`PAL` 仅开放 `25p`、`50p`、`100p`，对请求 `23.98p` 或切换 `DF`/`NDF` 一律返回 `EOPNOTSUPP = 95`。
  - 当有效制式与机身区域出厂默认制式不同时，开机显示 `"Running on NTSC."` 或 `"Running on PAL."` 提示横幅。
  - 严格区分复位语义：**`[Camera Settings Reset]` 保留当前 `[NTSC/PAL Selector]` 制式不变**（`preserved_across_camera_settings_reset == True`），唯有全量 **`[Initialize]`** 才恢复区域出厂默认制式并清除非默认开机横幅（`restored_to_factory_by_initialize == True`）。
  - 严格隔离双卡槽 `NTSC` 与 `PAL` 媒体管理数据库：未确认重初始化（`allow_media_db_reinit=False`）时拒绝跨制式混写（`EOPNOTSUPP = 95`，`ntsc_pal_cross_region_db_contamination_events == 0`）。

### 2.4 Sub-model C & Redlines — `[Gamma Display Assist]` 4 档精确表 vs `[Log Shooting]` `[Display LUT]` 硬锁定分离与仅限机内 LCD 作用域 HIL
- [`probe_gamma_display_assist_vs_display_lut_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py#L1299-L1474) 协同仿真色彩监看辅助管线：
  - 精确锁定 `ILME-FX3 Ver. 7.02` 官方 `[Gamma Disp. Assist Typ.]` **4 档表**：`Auto`、`S-Log3->709(800%)`、`HLG(BT.2020)`、`HLG(709)`；请求已移除的 `S-Log2` 选项立即返回 `EINVAL = 22`（`slog2_assist_rejected == True`）。
  - 一旦激活 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`），**硬锁定灰显 `[Gamma Display Assist] = Off`**（`gamma_display_assist_locked_off == True`，强行开启尝试返回 `EOPNOTSUPP = 95`），并将机内与 1080p 预览监看移交 `[Display LUT]` `On`/`Off`（支持 `[Display LUT Switch]` 翻转）。
  - 严格锁死内置 LCD 独占作用域：`[Gamma Display Assist]` **绝不作用于外接 HDMI 输出信号**（`external_hdmi_gamma_assist_applied == False`，强行注入外接 HDMI 返回 `EOPNOTSUPP = 95`）。
- [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h246-phase222-vm-stage40-pixelmap-ntscpal-gammaassist-displaylut-hil/outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py#L1477-L1522) fail-closed 锁死全部 9 项禁止动作（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`cnflasha_userspace_write_blocked = True`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`stage_b_tmp_mount_residuals_after_pixelmap_reboot = 0`、`ntsc_pal_cross_region_db_contamination_events = 0`、`log_shooting_gamma_assist_or_hdmi_leakage_events = 0`）。

## 3. 实测验证摘要（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 结果与实测指标 |
|---|---|---|
| Stage 40 独立自检 CLI（`40/40` 里程碑） | `LOCAL_DONOR_RDONLY` / `CLEAN_ROOM_SYNTHETIC` | `PASS`（12 供体冷读取 `2.84 ms < 0.02s`；`digest=0bd2dcac46a8` / `5ca1c13255ab`） |
| `fx3_vm_coemulation_suite.py`（Stage `1..40`） | 本地只读供体 / 洁净室合成 | `PASS`（`40/40` 里程碑全阶段通过，进程内本地 **`2.021s < 2.2s`**、洁净室 **`0.445s < 0.6s`**；`digest=5496062dc0c0` / `9f530131f4b8`） |
| Stage 40 专项双模单测（48 项） | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `48/48 OK`（`6.68s` / `4.36s`） |
| `outputs/fx3-vm/tests` 全量单测发现 | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `1564/1564 OK`（`121.25s` / `111.81s`，洁净室按预期 `skipped=3`） |
| `scripts/run_all_lab_tests.py --clean-only` | 全仓洁净室与字节码门禁 | `ALL GREEN in 0.04s` |
