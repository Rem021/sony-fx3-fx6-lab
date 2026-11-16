# Phase 232（VM Stage 42 `42/42` 里程碑）：真机 `ILME-FX3` `Ver. 7.00+/7.02` `[Mode Settings]`（`[Fixed/Variable]`）S&Q 6 项功能禁用、`[Zebra]`/`[Peaking]` 本地 LCD 专属与 HDMI 洁净隔离 + `[Full Format]` / `MENU+(Delete)` 2s 组合键保险库防火墙 HIL 协同仿真报告

## 1. 结论先行

已在独立工作树 `outputs/fx3-vm/` 闭环完成 **Task H258 — Phase 232（VM Stage 42 `42/42` 里程碑）** 真实硬件主线协同仿真器开发、全板 42 阶段编排接入、Milestone 221 主门禁兼容验证与双模全量回归验证：

- **交付物清单（严格受控 5 文件所有权边界）**：
  1. 新增 Stage 42 核心协同仿真模块：[realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py)
  2. 更新 42 阶段全板编排器（接入 `stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil` 与 `--skip-phase232`，升级里程碑至 `42/42`）：[fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
  3. 新增 58 项双模单元测试套件（满足 `>= 52` 要求，含前向兼容 `>= 42` 阶段断言、壁钟时延上限与源码 `os.O_RDONLY`/端口卫生断言）：[test_realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/tests/test_realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py)
  4. 更新虚拟机模块文档（Stage 42 `42/42` 里程碑章节与 CLI 指南）：[outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/README.md)
  5. 本里程碑验收报告（参考官方 `ILME-FX3 Ver. 7.02` 实测基线 [Wave-32 Real-Hardware Intel README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/reports/2026-11-15-global-sony-wave32-sq-fixed-variable-fps-zebra-peaking-hdmi-isolation-full-format-chord-intel/README.md)）。

## 2. 核心子模型（`Pillar A–C` + 硬安全红线）实现与实测证据

### 2.1 双模高速 `os.O_RDONLY` 12 供体有界审计（实测冷启动 `4.09 ms < 0.02s`）与零字节泄露回退
- [`inspect_phase232_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L918-L1044) 严格通过 `os.open(..., os.O_RDONLY)` 核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 采用 `<= 4096 B` 4KB 对齐定点 `lseek` 窗口读取并带进程级签名缓存，实测冷启动仅 **`0.00409s`**）；实证 `string_english_f.uxc`（`373,820 B`）、`fx3_appfw`、`fx3_cpapp`、`fx3_libmpr` 与 `fx6_appfw` 包含全部 Wave-32 菜单词条与内部符号（`Mode Settings`、`Fixed/Variable`、`S&Q Settings`、`Rec Frame Rate`、`Audio Out Timing`、`Lip Sync`、`Time Code Run`、`Time Code Output`、`Proxy Recording`、`Zebra Display`、`Zebra Level`、`Zebra Display Select`、`Custom 1`、`Custom 2`、`Std+Range`、`Lower Limit`、`Camera Settings Reset`、`Initialize`、`Peaking Display`、`Peaking Level`、`Peaking Color`、`HDMI Info. Display`、`Full Format`、`Quick Format`、`Switch Full Format`、`ZEBRA`、`PEAKING`、`FULL_FORMAT`、`TIME_CODE`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，`raw_firmware_bytes_leaked == 0`。

### 2.2 Pillar A — `Ver. 7.00+/7.02` `[Mode Settings]` = `[Fixed/Variable]` 直调 `[FPS]` 与 S&Q 6 项硬功能禁用 HIL
- [`probe_sq_mode_settings_fixedvar_and_6locks_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L1074-L1314) 与 [`evaluate_pillar_a_sq_fixedvar_and_6locks_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L1317-L1450) 精确建模 `MENU -> Shooting -> [Shooting Mode] -> [Shoot Mode] -> [Mode Settings]`：
  - 当 `[Mode Settings] = [Fixed/Variable]`（`Ver. 7.00+/7.02`）时，`MENU -> Shooting -> [Image Quality/Rec] -> [S&Q Settings]` 被系统灰显锁定（访问返回 `EOPNOTSUPP = 95`，提示 `Cannot select when [Mode Settings] is set to [Fixed/Variable]. Adjust via [Home (FPS)] on the Main Menu.`），改为通过拍摄主菜单 `Home` 页 `[FPS]` 直调传感器采样帧率并实时显示倍速倍率（如 `24p` 工程帧率下 `60fps -> 2.5x Slow`、`1fps -> 24x Quick`）。
  - 确定性建模并拦截全部 **6 项 S&Q 硬功能禁用与组合限制**：
    1. **无音频录制（`0ch`）**：S&Q 激活时 `audio_recorded_channels == 0`，显式开启音轨录制请求以 `EOPNOTSUPP = 95` 拦截；
    2. **`[Audio Out Timing]` 禁用**：`MENU -> Setup -> [Sound Option] -> [Audio Out Timing]`（`[Live]` / `[Lip Sync]`）在 S&Q 下锁定灰显（显式切换以 `EOPNOTSUPP = 95` 拦截）；
    3. **`[Time Code Run]` 与 `[Time Code Output]` 不可用**：S&Q 下时间码步进模式切换与 HDMI 时间码嵌入输出双双灰显禁用（显式请求以 `EOPNOTSUPP = 95` 拦截）；
    4. **`240fps`（NTSC）/ `200fps`（PAL）4K 全编码拦截**：在 `XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`、`XAVC S-I DCI 4K` 下选择 `240/200fps` 立即以 `EOPNOTSUPP = 95` 拦截，仅允许 `XAVC S HD` / `XAVC S-I HD`（`1080p`）；
    5. **`120fps`（NTSC）/ `100fps`（PAL）DCI 4K 拦截**：在 `XAVC S-I DCI 4K`（`4096x2160`）下选择 `120/100fps` 以 `EOPNOTSUPP = 95` 拦截（UHD 4K 编码允许）；
    6. **`[Proxy Recording]` 双重帧率拦截**：当记录帧率为 `119.88p`（NTSC）/ `100p`（PAL）**或** S&Q 采样帧率 `>= 120fps`（NTSC）/ `>= 100fps`（PAL）时，代理录制强制关闭并以 `EOPNOTSUPP = 95` 拒绝开启（`< 120/100fps` 且记录帧率 `<= 59.94p/50p` 时正常支持代理双录）。

### 2.3 Pillar B — `[Zebra Display]` / `[Zebra Level]` 跨 `[Camera Settings Reset]` 持久化与 `[Zebra]`/`[Peaking]` 本地 LCD 专属 + HDMI 洁净隔离 HIL
- [`probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L1458-L1645) 与 [`simulate_zebra_reset_vs_initialize_lifecycle`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L1648-L1698) 协同仿真斑马纹持久化与 HDMI 输出合成管线：
  - 支持 `[Zebra Display]`（`Off`/`On` 及控制拨轮左键快捷切换 `[Zebra Display Select]`）与 `[Zebra Level]` 标准档位（`70`、`75`、`80`、`85`、`90`、`95`、`100`、`100+`）及双自定义档位：`[Custom 1]`（`[Std+Range]`，如 S-Log3 肤色/灰卡基准 `52 ±2`）与 `[Custom 2]`（`[Lower Limit]`，如高光裁切下限 `94+`，越界参数返回 `EINVAL = 22`）。
  - **跨 `[Camera Settings Reset]` 存活生命周期**：执行 `MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset] -> [Camera Settings Reset]` 时，`[Zebra Display]` 与 `[Zebra Level]`（含 `Custom 1` / `Custom 2` 寄存器）完整保留（`zebra_preserved_across_camera_settings_reset == True`）；仅当执行全机出厂初始化 **`[Initialize]`** 时才恢复默认（`Zebra Display = Off`、`Zebra Level = 70`）。
  - **HDMI 硬件零像素洁净隔离**：`[Zebra Display]` 与 `[Peaking Display]`（`On/Off`、`High`/`Mid`/`Low`、`Red`/`Yellow`/`Blue`/`White`）严格仅在机身本地 LCD 叠加层渲染；无论 `MENU -> Setup -> [External Output] -> [HDMI Info. Display]` 设为 `Off` 还是 **`On`**，HDMI 外部视频流始终保持 `hdmi_zebra_overlay_pixels == 0`、`hdmi_peaking_overlay_pixels == 0`（`hdmi_clean_of_zebra_and_peaking == True`，`hdmi_zebra_or_peaking_leak_events == 0`）。

### 2.4 Pillar C & Redlines — Slot 1 `[Quick Format]` vs `(Delete)` `[Full Format]`、中途取消不可逆风险与 `MENU + (Delete)`（`~2s`）组合键 Tier-0 保险库防火墙 HIL
- [`probe_slot_format_and_menu_delete_chord_vault_firewall_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L1754-L2081) 建模 `MENU -> Shooting -> [Media] -> [Format]` 与机身实体组合键通路：
  - 区分默认 `[Enter]` **`[Quick Format]`**（仅重建文件系统分配表/目录元数据）与按 `(Delete)`（垃圾桶键，`Switch Full Format`）切换的 **`[Full Format]`**（底层块级全擦除数据区 + 元数据）；并精确复现真机 **`[Full Format]` 中途 `Cancel` 风险语义**：中途取消后已擦除的数据块无法恢复（`erased_data_unrecoverable == True`），但文件系统元数据已完成收尾，存储卡立即可正常继续录制使用（`card_usable_as_is_after_cancel == True`）。
  - **拍摄界面 `MENU + (Delete)` 约 `2s` 双键长按直达格式化快捷键**：`< 2.0s` 短按不误触发格式化弹窗（`shortcut_triggered == False`）；`>= 2.0s` 持续同时按住直达存储卡 `[Format]` 确认界面。
  - **Slot 1 Tier-0 恢复保险库三通道零死角防火墙**：只要 Slot 1 驻留未核验冷备或活跃 Tier-0 恢复保险库（`pnflasha` / `cnflasha` / `CAMSET01.DAT`），无论通过菜单 `[Enter]` 快速格式化、`(Delete)` 完全格式化还是拍摄界面 `MENU + (Delete)` `>= 2.0s` 组合键，一律以 `EBUSY = 16` 硬拦截（`vault_intact == True`）；若 SDXC 卡物理写保护拨片处于 `LOCKED`，额外以 `EROFS = 30` 双重硬件阻断；仅当保险库完成异地 SHA-256 归档核验（`VERIFIED_OFFCARD_ARCHIVED`）或操作非保险库槽位（如空置的 Slot 2）且写保护解除时才放行。
- [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h258-phase232-vm-stage42-sq-fixedvar-zebra-peaking-fullformat-hil/outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py#L2084-L2138) fail-closed 锁死全部 9 项禁止动作（`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`overall_ready_for_hardware_attach = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`cnflasha_userspace_write_blocked = True`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`sq_fixedvar_or_6lock_bypass_events = 0`、`hdmi_zebra_or_peaking_leak_events = 0`、`tier0_vault_format_or_chord_erase_events = 0`）。

## 3. 实测验证摘要（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 结果与实测指标 |
|---|---|---|
| Stage 42 独立自检 CLI（`42/42` 里程碑） | `LOCAL_DONOR_O_RDONLY` / `CLEAN_ROOM_SYNTHETIC` | `PASS`（12 供体冷读取 `4.09 ms < 0.02s`；`digest=f69ec596a630` / `eab2f900cf14`） |
| `fx3_vm_coemulation_suite.py`（Stage `1..42`） | 本地只读供体 / 洁净室合成 | `PASS`（`42/42` 里程碑全阶段通过，进程内本地 **`2.025s`**、洁净室 **`0.505s`**；`digest=32abc192f124` / `626ba66e71a5`） |
| `make verify-milestone-221` 主门禁 | 本地只读供体 + `--force-clean-room` | `status=OK`（`pillars=6/6`、`vm_stages=42/42`、`leaked=0`；`sha256=7a24f49261c602b3...` / `147c6d6a60648f46...`） |
| Stage 42 专项双模单测（58 项） | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `58/58 OK`（`3.163s` / `1.587s`） |
| `outputs/fx3-vm/tests` 全量单测发现 | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `1678/1678 OK`（`134.352s` / `112.251s`，洁净室按预期 `skipped=3`） |
| `scripts/run_all_lab_tests.py --clean-only` | 全仓洁净室与字节码门禁 | `ALL GREEN` |
