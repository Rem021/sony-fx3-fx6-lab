# Phase 226（VM Stage 41 `41/41` 里程碑）：真机 `ILME-FX3` `[SteadyShot]` `[Active]` 3 重切断、`[Clear Image Zoom]` 4 项自动锁定/归位与 `[Power Save Start Time]` 9 条件旁路 + `[Auto Power OFF Temp.]` HIL 协同仿真报告

## 1. 结论先行

已在独立工作树 `outputs/fx3-vm/` 闭环完成 **Task H251 — Phase 226（VM Stage 41 `41/41` 里程碑）** 真实硬件主线协同仿真器开发、全板 41 阶段编排接入、Milestone 221 主门禁兼容验证与双模全量回归验证：

- **交付物清单（严格受控 5 文件所有权边界）**：
  1. 新增 Stage 41 核心协同仿真模块：[realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py)
  2. 更新 41 阶段全板编排器（接入 `stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil` 与 `--skip-phase226`，升级里程碑至 `41/41`）：[fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
  3. 新增 56 项双模单元测试套件（满足 `>= 50` 要求，含前向兼容 `>= 41` 阶段断言、壁钟时延上限与源码 `os.O_RDONLY`/端口卫生断言）：[test_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/tests/test_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py)
  4. 更新虚拟机模块文档（Stage 41 `41/41` 里程碑章节与 CLI 指南）：[outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/README.md)
  5. 本里程碑验收报告（参考官方 `ILME-FX3 Ver. 7.02` 实测基线 [Wave-31 Real-Hardware Intel README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/reports/2026-11-15-global-sony-wave31-steadyshot-active-raw-hfr-ciz-center-af-powersave-9cond-temp-high-intel/README.md)）。

## 2. 核心子模型（`Pillar A–C` + 硬安全红线）实现与实测证据

### 2.1 双模高速 `os.O_RDONLY` 12 供体有界审计（实测冷启动 `2.96 ms < 0.02s`）与零字节泄露回退
- [`inspect_phase226_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py#L881-L1010) 严格通过 `os.open(..., os.O_RDONLY)` 核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 采用 `<= 4096 B` 定点 `lseek` 窗口读取并带进程级签名缓存，实测冷启动仅 **`0.00296s`**）；实证 `string_english_f.uxc`（`373,820 B`）、`fx3_appfw`、`fx3_cpapp`、`fx3_libmpr` 与 `fx6_appfw` 包含全部 Wave-31 菜单词条与内部符号（`SteadyShot`、`Active`、`Standard`、`SteadyShot Adjust.`、`Focal Length`、`RAW Output`、`Zoom Range`、`Optical zoom only`、`Clear Image Zoom`、`Digital Zoom`、`Focus Area`、`Metering Mode`、`Face/Eye Prior. in AF`、`Face Priority in Multi Metering`、`Power Save Start Time`、`Auto Power OFF Temp.`、`Fan Control`、`Minimum`、`Off in Rec`、`Always Off`、`STEADYSHOT`、`CLEAR_IMAGE_ZOOM`、`POWER_SAVE`、`AUTO_POWER_OFF_TEMP`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，`raw_firmware_bytes_leaked == 0`。

### 2.2 Pillar A — `[SteadyShot]`（视频）`[Active]` `~1.1x` 裁切 vs `[Standard]`/`[Off]` 与 3 重切断 HIL
- [`probe_steadyshot_movie_active_cutoffs_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py#L1013-L1191) 精确建模 `MENU -> Shooting -> [Image Stabilization] -> [SteadyShot]`：
  - `[Active]` 在合法帧率（`23.98p` / `24.00p` / `25p` / `29.97p` / `50p` / `59.94p` 且 S&Q `< 100fps`、HDMI `[RAW Output] = Off`）下同时激活 5 轴传感器位移 IBIS 与陀螺仪引导电子裁切（`crop_factor == 1.10`）；`[Standard]` 仅激活 5 轴光学 IBIS（`crop_factor == 1.00`）；`[Off]` 机械驻泊 IBIS 音圈（`ibis_voice_coil_parked == True`）并保留 Catalyst 陀螺仪元数据轨（在非 HFR/非外录 RAW 时）。
  - 严格建模 **3 大 `[Active]` 硬件切断条件**：① 普通视频高帧率 `119.88p`（NTSC）/ `100p`（PAL）；② S&Q 慢快动作传感器采样帧率 `>= 120fps`（NTSC）/ `>= 100fps`（PAL）；③ HDMI 外接 `[RAW Output] = On`。命中任一切断条件时显式请求 `[Active]` 均以 `EOPNOTSUPP = 95` 拦截（或按韧性自动回退至 `[Standard]` `1.00x`），绝不产生越界旁路（`steadyshot_active_cutoff_bypass_events == 0`）；同时支持手动转接镜头 `[SteadyShot Adjust.] = Manual` 与 `[Focal Length]`（`8 mm–1000 mm`）焦点标定校验。

### 2.3 Pillar B — `[Clear Image Zoom]` / `[Digital Zoom]`（`[Zoom Range]`）RAW/HFR 禁用与 4 项自动锁定 + `1.0x` 光学归位 HIL
- [`probe_ciz_digital_zoom_4locks_and_restore_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py#L1296-L1502) 与 [`simulate_ciz_zoom_excursion_and_optical_restore`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py#L1505-L1558) 协同仿真 `MENU -> Shooting -> [Zoom] -> [Zoom Range]`：
  - 精确锁定变焦倍率上限：`[Clear Image Zoom]` 支持 `4K` 下最高 `1.5x`、`HD (1080p)` 与静态照片（JPEG/HEIF）最高 `2.0x`；`[Digital Zoom]` 支持最高 `4.0x`（静态照片 `Size L` 为 `4.0x`、`M` 为 `5.7x`、`S` 为 `8.0x`）。在静态照片 `RAW` / `RAW+JPEG` / `RAW+HEIF`、视频 `119.88p`/`100p`、S&Q `>= 120fps/100fps` 以及 HDMI `[RAW Output] = On` 下硬禁用非光学变焦（返回 `EOPNOTSUPP = 95`）。
  - 一旦实际倍率越过 `1.0x` 进入非光学区间（`> 1.0x`），确定性触发全部 **4 项自动相机状态锁定**：① `[Focus Area]` 菜单锁定并自动降级为中心优先小范围相位检测（`CENTER_PRIORITY_SMALL_PHASE_DETECT`）；② `[Metering Mode]` 强制锁定为 `[Multi]`；③ `[Face/Eye Prior. in AF]` 与 `[Face Priority in Multi Metering]` 变为不可用（`UNAVAILABLE_LOCKED_OFF`）；④ `Real-time Tracking` 实时追踪变为不可用（`UNAVAILABLE_LOCKED_OFF`）。
  - 当变焦倍率退回 **`1.0x` 纯光学区间**时，自动无损恢复此前的对焦区域、测光模式、人脸/眼部优先与实时追踪设置（`restored_matches_initial == True`，`ciz_4lock_unrestored_or_bypass_events == 0`）。

### 2.4 Pillar C & Redlines — `[Power Save Start Time]` 9 条件自动旁路、气隙 Tier-0 `75 MiB` `p3` 防休眠护栏与 `[Auto Power OFF Temp.]` 三脚架互锁 HIL
- [`probe_powersave_9cond_and_autotemp_fan_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py#L1650-L1875) 建模 `MENU -> Setup -> [Power Setting Option]` 与 `[Setup Option] -> [Fan Control]`：
  - 严格使用完整官方菜单名 **`[Power Save Start Time]`**（支持 `Off` / `10 Sec` / `1 Min` / 默认 **`5 Min`** / `30 Min`，对缩写伪名返回 `EINVAL = 22`），完整实现 **9 项自动休眠旁路条件**（① USB PD 外部供电、② 遥控拍摄/网络流推流激活、③ 幻灯片回放、④ 动态视频录制中、⑤ HDMI 外接监看连接、⑥ `[Remote Control] = On`、⑦ `[Bluetooth Rmt Ctrl] = On`、⑧ `[USB Connection Mode] = [Mass Storage]` 或 `[MTP]` 连接主机、⑨ FTP 后台传输进行中）。
  - **气隙纯 `NP-FZ100` 电池 Tier-0 `75 MiB` `p3` 保险库转储防休眠锁**：无外部供电、无 HDMI、无主机 USB 连接的气隙机身不会触发上述 9 项自动旁路；若保持默认 `5 Min`（或 `10 Sec`/`1 Min`）发起 `75 MiB`（`78,643,200 B`）Tier-0 `p3` 保险库备份且电量或超时护栏未满足，立即以 `EOPNOTSUPP = 95` 阻断，强制要求先设 `[Power Save Start Time] = Off` 或 `30 Min` 且电池电量 `>= 50%`（`tier0_sleep_lock_guard_satisfied == True`）。
  - **`[Auto Power OFF Temp.]`（`[Standard]` vs `[High]`）与 `[Fan Control]` 热联动**：`[Auto Power OFF Temp.] = [High]` 严禁手持拍摄（`HANDHELD` 请求以 `EPERM = 1` 拦截防低温接触烫伤，`handheld_contact_burn_blocked == True`），必须配合三脚架/兔笼（`TRIPOD_MOUNTED` / `RIG_CAGE_MOUNTED`）；并联动 `[Fan Control]`（`Auto` / `Minimum` / `Off in Rec` / `Always Off`），当机内温度突破阈值时即使用户设为 `Off in Rec` 或 `Always Off` 亦强制唤醒风扇紧急散热（`thermal_fan_override_engaged == True`）。
- [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h251-phase226-vm-stage41-steadyshot-ciz-powersave-autotemp-hil/outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py#L1878-L1932) fail-closed 锁死全部 9 项禁止动作（`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`cnflasha_userspace_write_blocked = True`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`steadyshot_active_cutoff_bypass_events = 0`、`ciz_4lock_unrestored_or_bypass_events = 0`、`tier0_p3_sleep_abort_or_thermal_burn_events = 0`）。

## 3. 实测验证摘要（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 结果与实测指标 |
|---|---|---|
| Stage 41 独立自检 CLI（`41/41` 里程碑） | `LOCAL_DONOR_O_RDONLY` / `CLEAN_ROOM_SYNTHETIC` | `PASS`（12 供体冷读取 `2.96 ms < 0.02s`；`digest=b20d0189ddfd` / `e4bc52e6b06d`） |
| `fx3_vm_coemulation_suite.py`（Stage `1..41`） | 本地只读供体 / 洁净室合成 | `PASS`（`41/41` 里程碑全阶段通过，进程内本地 **`2.251s`**、洁净室 **`0.539s`**；`digest=ed140505d2e6` / `67d5b0cecf5b`） |
| `make verify-milestone-221` 主门禁 | 本地只读供体 + `--force-clean-room` | `status=OK`（`pillars=6/6`、`vm_stages=41/41`、`leaked=0`；`sha256=dc705960f35d577e...` / `c3e7a9264b8ba647...`） |
| Stage 41 专项双模单测（56 项） | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `56/56 OK`（`3.22s` / `1.59s`） |
| `outputs/fx3-vm/tests` 全量单测发现 | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `1620/1620 OK`（`136.78s` / `130.70s`，洁净室按预期 `skipped=3`） |
| `scripts/run_all_lab_tests.py --clean-only` | 全仓洁净室与字节码门禁 | `ALL GREEN in 0.04s` |
