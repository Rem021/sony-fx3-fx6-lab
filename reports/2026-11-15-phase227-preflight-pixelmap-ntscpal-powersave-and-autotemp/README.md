# Phase 227 实机拍摄前物理台架与双卡介质准备度预检器报告（`preflight-pixelmap-ntscpal-powersave-and-autotemp` / Waves 29–31）

## 1. 核心结论（Conclusion-First）

1. **Waves 29–31 三大物理台架与拍摄准备度检查组（`Check Group A..C`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增只读预检器 [`realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py)（Schema `realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier_v1`，版本 `227.0.0`，CLI 子命令 `preflight-pixelmap-ntscpal-powersave-and-autotemp`），将操作员物理台架预检链路推进至 `preflight-card-insert` → `preflight-bench-cable-fan-slot1` → `preflight-hdmi-proxy-desqueeze-and-simult` → `preflight-pixelmap-ntscpal-powersave-and-autotemp`。
2. **双模式 58 项单元测试与里程碑门禁 100% 通过**：新增 [`test_realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py) 共 **58** 项双模式确定性单测（高于 `>= 52` 要求），在本地有界只读 donor 模式（`LOCAL_DONOR_O_RDONLY`，耗时 **`0.050s`**）与无固件洁净室合成模式（`FX3_FX6_FORCE_CLEAN_ROOM=1` / `CLEAN_ROOM_SYNTHETIC`，耗时 **`0.046s`**）下均 `100%` 全绿（远低于 `< 2.0s` 预算，且有界 `O_RDONLY` 头部校验耗时 `< 0.15s`）；同时 `make verify-milestone-221`（双模式 `6/6` 支柱、`16/16 H0 == H3`）与 `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 全绿。
3. **离线默认阻断与硬件安全红线 100% 锁死**：离线默认返回 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（`rc=1`），`--simulate-bench-dry-run` 模拟演练返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（`rc=0`），全程无条件锁死 `hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 及 `16/16` 存储面 `SHA256(H0) == SHA256(H3)`。

---

## 2. 三大物理台架与双卡介质准备度检查组（`Check Group A .. C`）

| 检查组 ID | 预检域（Waves 29–31） | 关键校验规则、边界与报错码 |
| :--- | :--- | :--- |
| **`GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT`** | `[Pixel Mapping]` 自动重启 / `cnflasha` 只读防火墙、`[NTSC/PAL Selector]` 重置持久性与 `Ver. 7.02` `[Gamma Display Assist]` vs `[Display LUT]` 分离 | ① 在低电量（`< 20%` SOC 或低电告警，`GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED`）、Tier-0 冷备进行中（`GA_ERR_PIXEL_MAPPING_DURING_ACTIVE_TIER0_DUMP`）或未受控校准写入企图（`cnflasha` 用户态 `O_RDONLY` 防火墙，`cnflasha_calibration_mutation_bytes == 0`，`GA_ERR_CNFLASHA_USERSPACE_RO_FIREWALL_VIOLATION`）时硬阻断手动 `[Pixel Mapping]`；建模 `[Auto Pixel Mapping]` 关机暗场快门声不被 `[Silent Mode]` 静音、关闭时 `<= 3` 天手动周期（`GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER`），以及校准全按键锁定与强制自动重启卸载 Stage-B `/tmp` RAM Overlay（`H0 == H2`，`GA_ERR_PIXEL_MAPPING_MANDATORY_RESTART_OR_CONTROL_LOCK`）；<br>② 校验 `[NTSC/PAL Selector]` 帧率与 `DF/NDF` 互斥（`PAL` 禁用 `23.98p` 与 `TC Format` `DF/NDF`）、开机 `"Running on NTSC."` / `"Running on PAL."` 提示及卡内媒体库制式一致性，证明其**在 `[Camera Settings Reset]` 后保留、仅被 `[Initialize]` 清除恢复区域默认**（`GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB`）；<br>③ 强制 `Ver. 7.02` 精确 4 档 `[Gamma Disp. Assist Typ.]`（`Auto`、`S-Log3->709(800%)`、`HLG(BT.2020)`、`HLG(709)`，无旧版 `S-Log2`），当 `[Log Shooting]` 处于激活态（`On` / `Cine EI` / `Cine EI Quick` / `Flexible ISO`）时硬锁 `[Gamma Display Assist] = [Off]` 并交由 `[Display LUT]` 独立控制（`GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT`），且严禁外接 HDMI 期待叠加 `[Gamma Display Assist]`（`GA_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_FORBIDDEN`）。 |
| **`GROUP_B_FILE_SETTINGS_SHOTMARK_TC_REGEN_AND_COUPLED_RECLAMP`** | `[File Settings]` `37` 字符 / `SDHC` 不可用、`Shot Mark1/2` MP4/XAVC 专属性、`TC Regenerate` Slot-1 / `EXT-LK` 预警与 `[REC Lamp]` 机身+`XLR-H1` 联动熄灭 | ① 校验 `[File Settings]`（`Series` / `Reset`、`1..37` 位 ASCII `[Title Name Settings]`、`Cam ID` `A..Z`、`Reel#` `001..999`、仅向前生效无追溯改名），以及 `SDHC`（FAT32 `<=32GB`）卡插入时自定义命名与目录名不可用、硬件锁定 `[Standard]`（`GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE`）；<br>② 强制 `Shot Mark1` / `Shot Mark2` **仅支持 MP4 / XAVC 视频片段**（配合 `M4ROOT/CLIP/*M01.XML` `NonRealTimeMeta` 旁路文件与 `[Image Jump Setting]`），拦截 `JPEG` / `HEIF` / `RAW` / `PHOTO` 静态照片误标（`GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION`）；<br>③ 校验 `[Time Code Make] = [Regenerate]` 在 `[Simult. Recording]` 下严格只从 **Slot 1** 读取尾帧时码并强制切换 `[Rec Run]`（`GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION`），当外部 `VMC-BNCM1` `EXT-LK` 锁相激活后切往 `Regenerate` / `Rec Run` / `S&Q` 时发出 `WARN_EXT_LK_RELEASED_BY_TC_REGENERATE_OR_RUN_CHANGE` 并在要求保锁时硬阻断（`GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION`）；<br>④ 校验物理 `[REC Lamp]` 3 态联动（`All On`、`Only Front Off` 保持后灯+顶键 `REC` 灯硬件耦合，以及 **`[Off]` / `All Off` 同时熄灭机身全部 Tally 灯与 `XLR-H1` 手柄 `REC` 红灯**，`GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION`）及 `[Silent Mode] = [On]` → `[Audio signals] = [Off]` 锁定。 |
| **`GROUP_C_POWERSAVE_9COND_AUTOTEMP_TRIPOD_STEADYSHOT_AND_CIZ`** | `[Power Save Start Time]` 9 条件旁路与 `75 MiB` `p3` 冷备防休眠、`[Auto Power OFF Temp.]` 三脚架强制、`SteadyShot Active` 3 截止线与 `CIZ` 4 项锁定 | ① 精确锁定菜单名 `"Power Save Start Time"` 及全部 **9** 项自动旁路条件（`USB Power Supply`、`Slideshow Playback`、`FTP Transfer`、`Movie Recording`、`Computer Connection`、`TV/HDMI Connection`、`IR Remote Ctrl=On`、`Bluetooth Rmt Ctrl=On`、`Streaming/Cloud Upload`）；当仅靠机内 `NP-FZ100` 电池执行 `75 MiB` `p3` 冷备且 9 项旁路全部未激活时，强制 `[Power Save Start Time]` 设为 `Off` 或 `30 Min`（拦截 `5 Min` / `2 Min` / `1 Min` / `10 Sec` 中途断电休眠风险，`GC_ERR_NPFZ100_P3_75MIB_DUMP_SLEEP_HAZARD`）；<br>② 当 `[Auto Power OFF Temp.] = [High]` 时强制验证三脚架固定（`tripod_mounted == True` 且 `handheld_operation_active == False`，防范手持低温烫伤，`GC_ERR_AUTO_POWER_OFF_TEMP_HIGH_REQUIRES_TRIPOD`）并拦截 `[Fan Control] = [Always Off]` 与 `>= 45.0°C` 起测机身温度；<br>③ 校验视频 `[SteadyShot] = [Active]`（`~1.1x` 裁切、`8..1000mm` 手动焦距）全部 **3 条硬件截止线**：`119.88p/100p` 高帧率、`S&Q >= 120/100fps` 及 HDMI `RAW Output`（`GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION`）；<br>④ 校验 `Clear Image Zoom`（`4K <= 1.5x`、`HD <= 2.0x`）与 `Digital Zoom`（`<= 4.0x`）在 RAW / `100p/120fps` 下的禁用边界（`GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN`）与全部 **4 项对焦/测光锁**（`FocusAreaCenterPriority`、`MeteringModeMulti`、`FaceEyePriorityDisabled`、`RealtimeTrackingDisabled`，`GC_ERR_CIZ_FOUR_AF_METERING_LOCK_VIOLATION`），以及 `16/16 H0 == H3` 与异构物理盘（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` Tier-0 双回执门控。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 SHA-256 指纹
| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | Go/No-Go 裁决（`go_no_go`） | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `06ac62d94a384207d8c910de4763b9b86153e192c3203d66fe7c524ed6fa05c1` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `4bbe66242f59073e4e1eab410bec9c1c1fa5d379313bfa008c54c13f1a5820ea` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `be13f69d79d4f3043495b0db007a9dc3675cc002ca004d1acbdc80c7419467f3` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `a876e91019c10b8bcd0ba2edfccd07abb57811bbbf98aff91a5cf6da0b042212` |

### 3.2 严格归属的 6 个交付文件
1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py)（新增 Phase 227 预检器主模块）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（导出 Phase 227 全部常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-pixelmap-ntscpal-powersave-and-autotemp` CLI 子命令）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 41` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier.py)（新增 **58** 项双模式单测）
6. [`reports/2026-11-15-phase227-preflight-pixelmap-ntscpal-powersave-and-autotemp/README.md`](./README.md)（本实测报告）

### 3.3 实测命令与结果摘要
- **Phase 227 双模式单元测试**：
  - `LOCAL_DONOR_O_RDONLY`：**58/58 通过**（`0.050s < 2.0s`），有界 `O_RDONLY` donor 头部核验 `< 0.15s`，`raw_firmware_bytes_leaked = 0`。
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**58/58 通过**（`0.046s < 2.0s`）。
- **四级物理台架预检 CLI 链路联调**：`preflight-card-insert`（Ph186）、`preflight-bench-cable-fan-slot1`（Ph204）、`preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）、`preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）离线阻断与模拟演练全部符合预期。
- **里程碑与仓库洁净门禁**：
  - `make verify-milestone-221`：`LOCAL_DONOR_O_RDONLY`（`4ee2c183b8439e04...`）与 `CLEAN_ROOM_SYNTHETIC`（`878f9f4064caa027...`）双模式 **`status=OK`（6/6 支柱全绿）**。
  - `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：**100% 洁净通过**（零 `.pyc`、零未跟踪二进制产物、未触碰根 `Makefile` / `docs/` 或其他 `outputs/*` 模块）。
