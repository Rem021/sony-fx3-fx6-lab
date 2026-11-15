# Phase 248 实机拍摄前物理台架、媒体金库、数字音频与锁键准备度预检器报告（`preflight-imagedb-touch-shoeaudio-and-lockop` / Waves 34–39）

## 1. 核心结论（Conclusion-First）

1. **Waves 34–39 四大物理台架与实拍前准备度检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增第 5 级只读物理台架预检器 [`realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py)（Schema `realhw_imagedb_touch_shoeaudio_and_lockop_verifier_v1`，版本 `248.0.0`，CLI 子命令 `preflight-imagedb-touch-shoeaudio-and-lockop`），将 `ILME-FX3`（`Ver. 7.02`）操作员物理台架预检链路推进至 `preflight-card-insert`（Ph186）→ `preflight-bench-cable-fan-slot1`（Ph204）→ `preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）→ `preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）→ `preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）。
2. **双模式 64 项单元测试与里程碑门禁 100% 通过**：新增 [`test_realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py) 共 **64** 项双模式确定性单测（高于 `>= 58` 要求），在本地有界只读 donor 模式（`LOCAL_DONOR_O_RDONLY`，耗时 **`0.086s`**）与无固件洁净室合成模式（`FX3_FX6_FORCE_CLEAN_ROOM=1` / `CLEAN_ROOM_SYNTHETIC`，耗时 **`0.067s`**）下均 `100%` 全绿（远低于 `< 4.0s` 预算，且有界 `O_RDONLY` 头部核验 `< 0.15s`）；同时 `make verify-milestone-233`、`make verify-milestone-221`（双模式 `6/6` 支柱、`16/16 H0 == H3`）与 `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 全绿。
3. **离线默认阻断与硬件安全红线 100% 锁死**：严格对齐 Phase 227 双态契约——离线默认返回 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（`rc=1`），`--simulate-bench-dry-run` 模拟演练返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（`rc=0`），任意违规即闭锁返回 `BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_CHECK_FAILURE`（`rc=1`）；全程无条件锁死 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 及 `16/16` 存储面 `SHA256(H0) == SHA256(H3)`。

---

## 2. 四大物理台架、媒体金库、音频与锁键检查组（`Check Group A .. D`）

| 检查组 ID | 预检域（Waves 34–39） | 关键校验规则、边界与报错码 |
| :--- | :--- | :--- |
| **`GROUP_A_RECOVER_IMAGEDB_BATTERY_SLOT1_VAULT_AND_MONITOR_FLIP`** | `[Recover Image DB]` 电量 / Slot-1 Tier-0 金库护栏、`[Monitor Flip Direction]` 回放非反转与对焦/间隔静态拍摄边界（Wave 34） | ① 在 `NP-FZ100` 低电量（`< 20.0%` SOC 或低电告警，`P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY`）或针对未完成冷备校验 / 未拨至物理 `LOCK`（`WP`）的 Slot 1 Tier-0 转储卡（含 `pnflasha` / `cnflasha` / `CAMSET01.DAT`）执行 `[Recover Image DB]` 时硬阻断（`P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD`），并核验仅重建 `AVF_INFO` 不删素材且一次性动作菜单不受重置影响（`P248_GA_ERR_RECOVER_IMAGEDB_SEMANTICS_INVALID`）；<br>② 校验 `[Monitor Flip Direction]`（`Auto` / `Horizontal Flip` / `Vertical Flip` / `Off`）在 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 后保留、仅被 `[Initialize]` 恢复为 `[Auto]`，且即使开启 `[Horizontal Flip]`，**回放画面仍保持正向不左右镜像**（`P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION`）；<br>③ 强制核验 `[AF Transition Speed]`（`1..7`）、精确拼写 `"AF Subj. Shift Sensitivity"`（`1..5`）及 `[Interval Shoot Func.]` 仅限静态照片间隔拍摄（非原生视频缩时）（`P248_GA_ERR_AF_KINEMATICS_OR_INTERVAL_STILL_ONLY`）。 |
| **`GROUP_B_TOUCH_OP_4ITEM_GUARD_HDMI_CLEAN_FEED_AND_INDOOR_DISPLAY_POWER`** | `[Touch Operation]` 4 项防误触与重置持久性、HDMI `Off(HDMI Only)` / `RAW` 洁净流及室内 `Sunny Weather` / `Display Quality=High` 节电护栏（Waves 35 & 39） | ① 无人值守 Tier-0 冷备转储期间强制要求 `[Touch Operation]` 处于 `[Off]` 或 `[On: Playback Only]`（拦截 `[On]` 导致触屏误触发 `Touch Focus` / `Swipe Up`），并核验 Setup 全部 **4 项触控设置**（`Touch Operation`、`Touch Sensitivity`、`Swipe Up`、`Touch Func. in Shooting`）在 `[Camera Settings Reset]` 后保留（`P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE`）；<br>② 当 `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]` 或开启 HDMI `RAW` 输出时，强制钳位 `[HDMI Info. Display] = [Off]` 输出无 OSD 洁净流；仅当 `[HDMI Info. Display] = [On]` 时允许 `[Emphasized REC Display]` 与 `[Grid Line Display]` 随 OSD 叠加至外接 HDMI，且任何时候严禁外接 HDMI 期待 `Marker` / `Zebra` / `Peaking` 叠加（`P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION`）；<br>③ 室内台架转储时强制钳位 `[Monitor Brightness] = [Manual]`（`-2..+2`，拦截 `[Sunny Weather]` 背光功耗飙升）与 `[Display Quality] = [Standard]`（拦截 `[High]` 高刷功耗），保护 `NP-FZ100` 余量（`P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH`），同时校验 `[Bluetooth Rmt Ctrl] = [On]` 对红外遥控的硬件互斥与三态重置分离（`P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET`）。 |
| **`GROUP_C_SHOE_AUDIO_4CH_WIND_BUILTIN_ONLY_AND_SAVELOAD_FIREWALL`** | `[Shoe Audio Set.]` `48kHz/24bit 4ch` 三重硬件锁定、`[Wind Noise Reduct.]` 仅内置麦生效及 `[Save/Load Settings]` 4 类排除项 / Slot-1 写入防火墙（Wave 36） | ① 校验 MI 热靴数字音频 `[Shoe Audio Set.]`（`48kHz/16bit 2ch`、`48kHz/24bit 2ch`、`48kHz/24bit 4ch` 联动 `CH1..CH4` 四通道电平表）及全部 **3 项硬件不可用锁定**：`S&Q` 或 `[Audio Recording] = [Off]`、机身 `3.5mm` `MIC` 插孔插入抢占、`XLR-H1` 手柄拨至 `[ANALOG]` 档（`P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING`）；<br>② 强制核验 `[Wind Noise Reduct.]` 高通滤波**仅作用于机身内置麦克风**，拦截外接 `3.5mm` 麦或 MI 热靴 `XLR-H1` 误期待降风噪生效及室内台架误开 `[On]` 削弱低频（`P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON`）；<br>③ 校验 `[Save/Load Settings]`（卡内 `CAMSET01..10.DAT` 最多 10 组与 `C3 Portal` / `Creators' Cloud`）严格限定 `ILME-FX3` 同机型导入，锁死 **4 大不保存/不迁移排除类**（`IPTC/Copyright`、`Custom WB 1..3` 传感器色温寄存器、`Face Memory` 人脸生物特征、`FTP/Streaming/Wi-Fi/TLS` 网络凭据密钥）（`P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION`），并在 Slot 1 Tier-0 金库卡未完成双盘回执核验或已拨 `WP` 时硬阻断向 Slot 1 执行 `[Save]`（`P248_GC_ERR_SAVELOAD_SLOT1_TIER0_SAVE_BLOCKED`）。 |
| **`GROUP_D_LOCK_OP_PARTS_5S_CHORD_USB_POWER_BATTERY_AND_SHUTTER_ANGLE_TABLE`** | `[Lock Operation Parts]` `MENU + Fn` 5s 锁键（防误触毁灭性 `MENU + Delete` 2s）、`[USB Power Supply]` 强制机内 `NP-FZ100` 与 `[Shutter Angle]` 恒定角度表（Waves 37 & 38） | ① 校验 `[Lock Operation Parts]`（`Off`、`Multi-Selector Only`、`Dial + Wheel`、`All`）在 `[Camera Settings Reset]` 后保留，强制区分 **`MENU + Fn` 长按 `5.0s` 全机身防误触锁键**（锁死快门键以外全部按键拨轮，支持 `My Dial` 临时解锁）与**硬阻断毁灭性的 `MENU + Delete` 长按 `2.0s` 卡槽完全格式化组合键**（`P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION`）；<br>② 校验 `[USB Power Supply]` 在未使用 `DC-C1` 假电池耦合器时**必须在机内插入已充电的 `NP-FZ100` 电池**（纯插 `USB Type-C` 无电池无法开机供电），并锁死仅 `USB Type-C` 支持供电/充电（拦截 `Multi/Micro USB` 误接）、`[USB LUN Setting]`（`Multi` / `Single`）重置持久性，以及 `ILME-FX3` 无原生 `[Var. Shutter]` 且 `[Anti-flicker Shoot.]` 仅对机械快门静态照片生效（`P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT`）；<br>③ 证明 `[Exposure step]`（`0.3EV` / `0.5EV`）**完全不改变 `[Shutter Angle]` 恒定电影快门角刻度表**（`5.6°..360°`），核验 `[Audio Out Timing]`（`Live` / `Lip Sync`）在 `S&Q` 下锁定不可调、`[Silent Mode]=On -> [Audio signals]=Off` 联动（`P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION`），以及 `16/16 H0 == H3`（`P248_GD_ERR_H0_H3_IMMUTABILITY_DRIFT`）与异构物理盘（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` Tier-0 双回执门控。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 SHA-256 指纹
| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | Go/No-Go 裁决（`go_no_go`） | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `f38c89553ab9886b5900924732ffdc6e287b64ea44645668c4b861292d47fdfd` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `7e964220617917a305af330618bf56dbc6cfbaeb237b1dc933ba8c1ad7d2a916` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `3662dee82a5bcee0e7dc1c35115f53be5781b70cbd3a9e8d782d2761638c51f7` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `eeacda446444218e3f9fc111e602357c33a89bb749edceeae47fc2530b69579f` |

### 3.2 严格归属的 6 个交付文件
1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py)（新增 Phase 248 第 5 级物理台架准备度预检器主模块）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（无阴影导出 Phase 248 全部 77 个公共常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-imagedb-touch-shoeaudio-and-lockop` CLI 子命令）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 42` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_imagedb_touch_shoeaudio_and_lockop_verifier.py)（新增 **64** 项双模式单测）
6. [`reports/2026-11-15-phase248-realhw-imagedb-touch-shoeaudio-lockop-preflight/README.md`](./README.md)（本实测报告）

### 3.3 实测命令与结果摘要
- **Phase 248 双模式单元测试**：
  - `LOCAL_DONOR_O_RDONLY`：**64/64 通过**（`0.086s < 4.0s`），有界 `O_RDONLY` donor 头部核验 `< 0.15s`，`raw_firmware_bytes_leaked = 0`。
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**64/64 通过**（`0.067s < 4.0s`）。
- **`outputs/fx6-on-fx3-closure/tests` 全量套件回归**：32 个测试套件共 **1,293** 项测试在洁净室双模式下 **1,293/1,293 全部通过**（`skipped=51`）。
- **五级物理台架预检 CLI 链路联调**：`preflight-card-insert`（Ph186）、`preflight-bench-cable-fan-slot1`（Ph204）、`preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）、`preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）、`preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）离线阻断（`rc=1`）与模拟演练（`rc=0`）在双模式下全部符合预期。
- **里程碑与仓库洁净门禁**：
  - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233`：`LOCAL_DONOR_O_RDONLY`（`0f01a844b8d35cd2...`）与 `CLEAN_ROOM_SYNTHETIC`（`3d73a3639c5040d2...`）双模式 **`status=OK`（6/6 支柱全绿）**。
  - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221`：`LOCAL_DONOR_O_RDONLY`（`616458029cf6180c...`）与 `CLEAN_ROOM_SYNTHETIC`（`ee1515d05c724131...`）双模式 **`status=OK`（6/6 支柱全绿）**。
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：**100% 洁净通过**（零 `.pyc`、零未跟踪二进制产物、严格仅改动授权的 6 个文件）。
