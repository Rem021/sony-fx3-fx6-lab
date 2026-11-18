# Phase 315（Stage 65 — `65/65` 里程碑）：Wave-55 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 4 项 `[Touch Operation]` & 休眠触摸陷阱防线、`[DISP (Screen Disp) Set]` & 零 EVF 黑屏陷阱拦截、Still-Only `[AEL w/ Shutter]`/`[Flash]` 子菜单，以及 9 档 `[Play Speed for Interval]` & `Slot-1` Tier-0 Vault 防火墙 HIL 协同仿真报告

## 结论先行

1. **Stage 65（`65/65` 里程碑）全闭环通过并接入全板总装门禁**：新增 [`outputs/fx3-vm/realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py`](../../outputs/fx3-vm/realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py)（Schema `realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator_v1`），并接线至 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为第 65 阶段（`vm_stages=65/65`），`Stage 1..64` 保持完全向后兼容（支持 `--include-stage65`、`--skip-stage65`、`--no-include-stage65`、`--skip-phase315`）。
2. **17 份真实 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 实机供体双模审计零失真**：通过受界 `os.O_RDONLY`（`<= 4096 B`）校验全部 17 份供体（FX3 `string_*_f.uxc` 4 语全集 + `string_*.uxc` 4 语全集 + `string_*_g.uxc` 4 语全集 + FX6 `string_english.uxc` / `string_english_2.uxc` + `FX3 appFw.so`、`FX3 BK4`、`FX6 appFw.so`）字节长度、SHA-256 与符号/词条锚点；`LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 三模通过（洁净室双环境变量产生完全一致的确定性摘要 `5d90324815b1`），`raw_firmware_bytes_leaked == 0`。
3. **88 项 Stage 65 专项单测 + 全量 `fx3-vm` 单测（`3,359` 项）+ `Milestone 311` & `Milestone 295` 双模门禁全绿**：全部硬件写安全红线与 Wave-55 实机真值红线锁定（`persistent_emmc_writes_authorized=False`、`hardware_live_attachment_authorized=False`、`overall_ready_for_hardware_attach=False`、`fx3_has_builtin_evf=False`、`fx3_has_eye_sensor=False`、`fx3_has_finder_monitor_button=False`、`fx6_uses_loupe_terminology=False`、`fx6_has_still_flash_stack=False`、`slot1_data_sector_writes=0`、`slot1_avf_info_mutated=False`、`slot1_vault_pb_edit_mutation_bytes=0`、`physical_device_writes=0`）。

---

## 一、交付文件清单（严格限定 5 个自有文件）

| 序号 | 类型 | 路径 | 职责摘要 |
| --- | --- | --- | --- |
| 1 | NEW | [`outputs/fx3-vm/realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py`](../../outputs/fx3-vm/realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py) | Phase 315 Stage 65 核心模型、17 供体 `O_RDONLY` 审计、65A..65D 仿真器、安全/真值红线门禁与 CLI |
| 2 | EDIT | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil`（总阶段 `65/65` Milestone）与 CLI 开关 |
| 3 | EDIT | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 315 Stage 65 架构契约与三模运行/单测命令 |
| 4 | NEW | [`outputs/fx3-vm/tests/test_realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py) | 88 项双模单测（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 5 | NEW | [`reports/2026-11-17-phase315-vm-stage65-touch-shooting-disp-zero-evf-interval-pb-hil/README.md`](README.md) | 本中文结论先行工程报告 |

---

## 二、Wave-55 实机四大硬件契约验证摘要

### 1. Sub-Model 65A：4 项 `[Touch Operation]`（`Initialize`-Only）vs 休眠 `Touch Shutter` / `Touch AE` / `Touch Panel/Pad` / `Footer Icon Touch` 防线

- **`MENU -> Setup -> [Touch Operation]`（`_g.uxc 0x6345`）仅暴露 4 项有效配置**，且**全部跨 `[Camera Settings Reset]` 留存（仅通过 `[Initialize]` 复位）**：
  1. `[Touch Operation]`：`On`（默认）/ `On: Playback Only`（`_f 0x6cde`）/ `Off`；
  2. `[Touch Sensitivity]`（`_f 0x739f`）：`Standard`（默认）/ `Sensitive`（`_f 0x7205`，严格拒绝 `"Responsive"` 返回 `EINVAL=22`）；
  3. `[Touch Func. in Shooting]`（`_f 0x7575`）：`Touch Focus` / `Touch Tracking`（默认）/ `Off`，在 `Still`、`Movie`、`S&Q` 三模下保持一致；
  4. `[Swipe Up]`（`_f 0x7518`）：`Open the Fn Menu`（`_f 0x7281` 默认）/ `Off`，且仅在 `Touch Operation == On` 时激活（`On: Playback Only` 与 `Off` 时禁止手势上滑呼出 Fn 菜单）。
- **休眠 BIONZ XR Alpha 触摸符号 fail-closed 护栏**：对 `Touch Shutter`（`_f 0x6a80`）、`Touch AE`（`_f 0x702a`）、`Touch Focus+AE`（`_f 0x797e`）、`Touch AE Cancel`（`_g 0x6150`）、无 EVF 缺席的 `Touch Panel/Pad` 系列（`_f 0x76ec` / `0x6d1a` / `0x7312`）以及 `Footer Icon Touch` / `Swipe Left` / `Swipe Right`（`_f 0x70da` / `0x6b06` / `0x6c19`）全部拦截并返回 `EOPNOTSUPP=95`（`dormant_touch_shutter_ae_pad_footer_exposed_events == 0`）。
- **对比 `ILME-FX6 Ver. 6.01`**：FX6 仅在可拆卸触摸取景器路径暴露 `Technical > Touch Operation`（`On`/`Off`）与 `Shooting > Focus > Touch Function in MF`（`Spot Focus`/`Tracking AF`，AF 下支持 `Realtime Tracking AF`），不暴露 `On: Playback Only`、`Touch Sensitivity` 或 `Swipe Up`（`EOPNOTSUPP=95`）。

### 2. Sub-Model 65B：`[DISP (Screen Disp) Set]`（`Operation Customize`, 4 Shoot / 3 Play）& 零 EVF `Select Finder/Monitor` 黑屏陷阱拦截

- **精确菜单位置与页面结构**：位于 **`Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]`**（`_g.uxc 0x61da`，拒绝误归入 `Display Option` `EOPNOTSUPP=95`；跨 `[Camera Settings Reset]` 留存，仅 `[Initialize]` 复位）：
  - **4 个拍摄页面**：`Display All Info.`（`0xea0e`）、`No Disp. Info.`（`0xe9f9`）、`Histogram`（`0xe07b`）、`Level`（`0xe8bc`），强制要求 **`>= 1` 页勾选**（0 项勾选返回 `EINVAL=22`）；
  - **3 个回放页面**：锁定为 `Display Info.`、`Histogram`、`No Disp. Info.` 循环（修改页数返回 `EOPNOTSUPP=95`）。
- **`ILME-FX3` 零 EVF 防黑屏假死护栏**：硬件真值严格锁定 **`fx3_has_builtin_evf = False`、`fx3_has_eye_sensor = False`、`fx3_has_finder_monitor_button = False`**；对休眠 `BKID_APP_setting_finder_monitor` / `Select Finder/Monitor`（`_f 0x74f9`）/ `DISP Button:Finder`（`0x6b57`）/ `FINDER/MONITOR` 一律 fail-closed 返回 **`ENODEV=19`**，对 `For viewfinder`（`0x62d3`）/ `Graphic Display`（`0xe07a`）/ `Monitor Off` 返回 **`EOPNOTSUPP=95`**，保证 `lcd_monitor_blacked_out == False` 与 `zero_evf_finder_monitor_blackout_trap_events == 0`。
- **对比 `ILME-FX6 Ver. 6.01`**：FX6 同样无机身内置 EVF（`TYPE_BUILTIN_EVF_NOT_EXIST`），标配可拆卸 3.5" 触摸 **`Viewfinder`** 与 **`Viewfinder Hood`**（严禁误称为 `"Loupe"`，请求 `"Loupe"` 返回 `EINVAL=22`，`fx6_uses_loupe_terminology == False`），使用 `Monitoring > Display On/Off`、`Technical > Menu Settings > Info. Disp. Mode Operation`（`Home Screen Priority` / `Direct Menu Priority`）与 `MIRROR` 翻转。

### 3. Sub-Model 65C：Still-Only `[AEL w/ Shutter]` & `[Flash]` 子菜单（`[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`）vs 无闪光 `FX6`

- **全部 4 项严格限定 Still-Only**：在 `Movie` 与 `S&Q` 模式下访问均返回 **`EBUSY=16`**（`still_only_ael_flash_movie_sq_bypass_events == 0`）。
- **Reset vs Initialize 生命周期精准分化**：
  - `[AEL w/ Shutter]`（`Auto` 默认 / `On` / `Off`）：`Auto` 在 `AF-S`（及静止 `AF-A`）半按锁定曝光、移动 `AF-A` 与 `AF-C` 连拍持续重测光；`[AEL toggle]` 自定义键强制覆盖半按快门策略；**`Initialize`-only**；
  - `[Exp.comp.set]`（位于 `Exposure/Color -> [Flash]` 子菜单下，拒绝错误归属目录 `EOPNOTSUPP=95`）：`Ambient&flash`（默认，EV 补偿同时作用环境光与闪光输出）vs `Ambient only`（`_f 0x7617`，仅偏移环境光）；**`Initialize`-only**；
  - **`[Wireless Flash]`**（`Off` 默认 / `On`，支持 `Wireless Test Flash`）：**本组 4 项中唯一受 `[Camera Settings Reset]` 复位的一项**；
  - `[External Flash Set.]`（`_f 0x6771`）：仅允许 **MI 热靴直插（`MI_SHOE_DIRECT`）**；连接同步线离机（`SYNC_CORD_OFF_CAMERA`）返回 **`EINVAL=22`**（`sync_cord_external_flash_bypass_events == 0`），无热靴连接返回 `ENODEV=19`，拒绝相机菜单端无线配对/复位返回 `EOPNOTSUPP=95`；**`Initialize`-only**。
- **对比 `ILME-FX6 Ver. 6.01`**：电影机无机械焦平面快门与静态 TTL 闪光灯栈（`fx6_has_still_flash_stack == False` -> **`ENOENT=2`**），仅保留消除卷帘快门半帧割裂条纹的 `Flash Band Reduce`（`_2.uxc 0x4215`）。

### 4. Sub-Model 65D & Redlines：回放 `[Viewing]` 9 档 `[Play Speed for Interval]`（`1..9` 默认 `5`）& `[Edit]` vs 休眠 `[Beauty Effect]`/`[Trimming]` + `Slot-1` Tier-0 Vault 防火墙

- **精确 9 档间隔连续播放速率**：位于 **`Playback -> [Viewing]`**（`_g 0x6033`，拒绝误入 `Playback Option` `EOPNOTSUPP=95`），`[Cont. Play for Interval]` & `[Play Speed for Interval]` 精确暴露 **`1..9` 共 9 档**（`CONTINUOUS_PLAYBACK_SPEED_1..9`，**默认 `5`**；`<= 0` 或 `>= 10` 返回 `EINVAL=22`；支持拨轮步进在 `[1, 9]` 钳位；跨 `[Camera Settings Reset]` 留存并仅在 `[Initialize]` 复位至 `5`）。在 `Slot 1` Tier-0 Vault 上纯只读浏览安全放行；机内无间隔照转视频合成功能（`EOPNOTSUPP=95`）。
- **活跃 `[Edit]` vs 休眠陷阱 & `Slot-1` Tier-0 Vault 100% Fail-Closed 防火墙**：
  - 活跃 `Playback -> [Edit]` 仅含 4 项：`Rotate`、`Photo Capture`、`JPEG/HEIF Switch`（`JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)`）与 `Copy`；
  - 任何 `Rotate`、`Photo Capture`、`Copy`（`Slot 2 -> Slot 1`）以及休眠 `Beauty Effect`（`_f 0x7849`）/`Trimming`（`sequence_edit_trimming_*`）只要以挂载 Tier-0 Vault 的 **`Slot 1`** 为目标，**100% fail-closed 拦截返回 `EROFS=30`**，实测锁定 **`slot1_data_sector_writes == 0`**、**`slot1_avf_info_mutated == False`**、**`slot1_vault_pb_edit_mutation_bytes == 0`**；
  - 针对非 Vault 虚拟 `Slot 2` 的休眠 `Beauty Effect` / `Trimming` 返回 **`EOPNOTSUPP=95`**；针对虚拟 `Slot 2` 的 `Rotate`（`270°`）与 `Photo Capture`（`.JPG` / `.HIF`）在 **`physical_device_writes == 0`** 约束下非破坏性完成；`ILME-FX6` 全面拦截消费级回放编辑（`EOPNOTSUPP=95`）。

---

## 三、跨平台 CI 合规与验证实测数据（全量通过）

- **Stage 65 独立 CLI 自检（三模）**：
  - `LOCAL_DONOR_O_RDONLY`：`[PASS] Phase 315 Stage 65 (65/65 Milestone) | mode=LOCAL_DONOR_O_RDONLY donors=17 tch_byp=0 evf_trap=0 fx3_evf=0 ael_byp=0 ivl_byp=0 s1_wr=0 emmc_wr=0 leak=0 digest=4c9028a120cd`
  - `FX3_CLEAN_ROOM_TEST=1` & `FX3_FX6_FORCE_CLEAN_ROOM=1`：双模式输出完全一致的确定性洁净室摘要 `digest=5d90324815b1`
- **全板 65 阶段套件 `fx3_vm_coemulation_suite.py --include-stage65 --summary`**：
  - `LOCAL_DONOR_O_RDONLY`：`m65=65/65`，`digest=11b020358da8`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`m65=65/65`，`digest=8aa693b57dfe`
- **Stage 65 专项 88 项单测（三模全绿）**：
  - `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 全部 `Ran 88 tests (OK)`（无硬件写操作、无固件字节泄漏）。
- **全量 `outputs/fx3-vm/tests` 单测发现（双模全绿）**：
  - `LOCAL_DONOR_O_RDONLY`：`Ran 3359 tests in 200.396s (OK)`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 3359 tests in 185.121s (OK, skipped=5)`
- **主线总门禁 `make verify-milestone-311` & `make verify-milestone-295`（双模全绿）**：
  - `verify-milestone-311`（`LOCAL_DONOR_O_RDONLY`）：`status=OK`、`vm_stages=65/65`、`pillars=6/6`、`gate134=135/138`、`recovery=55/55`、`auditors=45/45`、`qemu=36/36(108/108)`、`pngs=72/72(max=27467B)`、`leaked=0`、`milestone311_sha256=cbb5389536f0ed8b...`
  - `verify-milestone-311 --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`status=OK`、`vm_stages=65/65`、`leaked=0`、`milestone311_sha256=5f7263da4be67969...`
  - `verify-milestone-295`（`LOCAL_DONOR_O_RDONLY`）：`status=OK`、`vm_stages=65/65`、`gate124=135/138`、`recovery=55/55`、`leaked=0`、`milestone295_sha256=22aa894a16fd92bb...`
  - `verify-milestone-295 --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`status=OK`、`vm_stages=65/65`、`leaked=0`、`milestone295_sha256=adde5ed25cca299a...`
- **洁净室卫生与无泄漏审计 `make clean-audit`**：`[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.03s)`，`ALL GREEN in 0.03s`。

