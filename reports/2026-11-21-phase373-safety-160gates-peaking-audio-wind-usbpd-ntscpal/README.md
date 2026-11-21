# Phase 373（`Task H473`，Wave-70 Milestone，`160/160` 硬件安全门禁里程碑）：`[Peaking Display]` Clean-HDMI 隔离 / 零 FX6 `Type/Freq` + Ver. 2.00..7.02 `[Audio Level Display]` 废除 / 精确 5 项音频与 `[Wind Noise Reduct.]` 仅内置立体声麦（`G159`），及 `[USB Power Supply]` 强制 `NP-FZ100` / `DC-C1` 供电铁律 + `[NTSC/PAL Selector]` `J1/CE/E33/U2` SKU 锁 / 纯 XAVC 免格式重启与 `AVF_INFO` `Slot 1` `EROFS=30` 防火墙（`G160`）

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H473` · **Phase 373（`160/160` 硬件安全门禁里程碑）**
- **核心结论（`实测事实`）**：
  1. 已交付门禁 **`G159`**（[`verify_peaking_audio_wind_guard`](../../outputs/fx3-safety/fx3_safety/realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.py)）与 **`G160`**（[`verify_usbpd_ntscpal_avfinfo_guard`](../../outputs/fx3-safety/fx3_safety/realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.py)）及统一预检引擎 **`verify-160-gates`**（[`evaluate_160gate_preflight`](../../outputs/fx3-safety/fx3_safety/realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.py)）。
  2. 离线默认模式实测通过 **`157/160`** 项门禁（`VERIFIED_157_OF_160_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach = False`）；`--simulate-bench-dry-run --force-clean-room` 演练模式通过 **`160/160`** 项（`VERIFIED_ALL_160_GATES_DRY_RUN_SIMULATED_BACKUP`），所有物理写盘/刷机/实时连机红线恒锁 `False` 与 `0`。
  3. 4 模式 160 门禁单元测试（`108/108` × 4）、全量 `outputs/fx3-safety/tests`（`82` 个测试文件共 `4,929/4,929` 项测试，正常模式与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模）、双模 `make verify-milestone-364`（自动发现 `gate156=157/160`、`leaked=0`）及 `make clean-audit` 全部通过（`ALL GREEN`，零 `.pyc`）。
- **Wave-70 实证基线**：[Wave-70 Milestone 调研报告](../2026-11-17-global-sony-wave70-milestone-peaking-audio-level-wind-usb-pd-ntsc-pal-intel/README.md)
- **硬件安全姿态**：对 16 个本地 donor 构件严格采用只读 `os.O_RDONLY` + 有界 `os.pread`（`< 0.20s` 预算）并内置无盘 clean-room 回退（`raw_firmware_bytes_leaked == 0`、`emmc_writes_authorized == False`、`persistent_emmc_writes_authorized == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`usb_packets_transmitted == 0`）。

---

## 1. 交付物清单（严格 6 个受控文件）

- 门禁与 160 门禁统一预检模块：[`realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.py`](../../outputs/fx3-safety/fx3_safety/realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.py)
- 包导出与 CLI 注册（`verify-peaking-audio-wind-guard` / `verify-g159`、`verify-usbpd-ntscpal-avfinfo-guard` / `verify-g160`、`verify-160-gates`）：[`fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py)、[`fx3_safety/__main__.py`](../../outputs/fx3-safety/fx3_safety/__main__.py)、[`outputs/fx3-safety/README.md`](../../outputs/fx3-safety/README.md)
- 4 模式单元测试套件（`108` 项测试）：[`test_realhw_peaking_audio_wind_usbpd_ntscpal_160gate_guard.py`](../../outputs/fx3-safety/tests/test_realhw_peaking_audio_wind_usbpd_ntscpal_160gate_guard.py)
- 工程收尾报告（本文件）：[`reports/2026-11-21-phase373-safety-160gates-peaking-audio-wind-usbpd-ntscpal/README.md`](./README.md)

---

## 2. 新增安全门禁与实测/推断边界

### 2.1 门禁 `G159`：`PEAKING_CLEAN_HDMI_ZERO_FX6_TYPE_FREQ_AND_AUDIO_5ITEM_WIND_BUILTIN_ONLY_FIREWALL`
- **`实测事实`（Peaking Clean-HDMI 与 FX6 `Type/Freq` 辟谣）**：
  - 精确锁定 FX3 Ver. 7.02 `Shooting -> [Focus] -> [Peaking Display]` 3 项（`Peaking Display` 默认 `Off`/`On`、`Peaking Level` `High`/`Mid` 默认/`Low`、`Peaking Color` `Red`/`Yellow`/`Blue`/`White` 默认），全部 **抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 还原）；强制 **Clean-HDMI 零泄漏**（`peaking_emitted_over_hdmi == False`、`hdmi_peaking_leaked_pixels == 0`），与 `[Focus Magnifier]` 兼容无互斥；机身 `[Focus Map]`（`_f 0x61f9`）及 USB 有线连接 *Monitor & Control* 均返回 **`EOPNOTSUPP=95`**（仅 Ver. 6.00+ 无线 M&C 开放）。
  - 对照 FX6 Ver. 6.01 `Monitoring > Peaking` 精确 3 项（`Setting`、`Peaking Level`、`Color` 采用 `B&W` 而非 `White`），在只读 donor 校验中证伪休眠 UXC 词条 `Peaking Type`/`Peaking Frequency`（`FX6 appFw.so` `0` 符号命中 -> `EOPNOTSUPP=95`）。
- **`实测事实`（Ver. 2.00..7.02 音频 5 项、内置麦独占风噪抑制与 3 级抢占）**：
  - 锁定 Ver. 2.00..7.02 独立 `[Audio Level Display]` 菜单已撤除（由 `DISP`/BIG6 自动渲染，Remote SDK 只读，写操作返 `EOPNOTSUPP=95`）；`Shooting -> [Audio Recording]` 精确 **5 项** 且全部 `Can be reset`：`Audio Recording`、`Audio Rec Level`（`0..31` 默认 `26`，`adj_audio_rec_level_defult` 拼写与永久不可关闭 Limiter）、`Audio Out Timing`（`Live`/`Lip Sync`）、`Wind Noise Reduct.`（**仅 `On`/`Off` 默认 `Off`，绝无 `Auto` -> `EOPNOTSUPP=95`，且仅作用于内置立体声麦**，`3.5mm`/`XLR-H1`/MI 靴/`S&Q` 均自动旁路）及 `Shoe Audio Set.`。
  - 强制 3 级音频抢占序（`3.5mm MIC` > MI 靴 `XLR-H1` DIGITAL > 内置立体声麦；`XLR-H1` `ANALOG` 降级 `16bit 2ch`），并对照 FX6 物理 `CH1/CH2` 旋钮、菜单 `CH1..CH4 Wind Filter`（标准提把无硬件 `LOW CUT` 开关 -> `EOPNOTSUPP=95`）与 6 档 `Limiter Mode`（`384` 状态矩阵）。
- **`推断`**：台架仿真与自动测试脚本若将 FX6 休眠 `Peaking Type/Freq` 或 FX3 `Wind Noise Auto` 误映射为可写菜单项，会导致菜单状态机与真实机身 NVS 漂移，故统一在 `G159` 层以 `EOPNOTSUPP=95` 阻断。

### 2.2 门禁 `G160`：`USB_PD_MANDATORY_FZ100_DCC1_POWER_AND_NTSC_PAL_SKU_AVFINFO_SLOT1_EROFS_FIREWALL`
- **`实测事实`（USB-PD / 强制 `NP-FZ100` / `DC-C1` 与 FX6 `19.5V DC IN`）**：
  - 锁定 FX3 `Setup -> [USB] -> [USB Power Supply]`（默认 `On`，抗 `[Camera Settings Reset]`）仅支持 **USB Type-C**（Multi/Micro USB 返 `EOPNOTSUPP=95`）；推荐 `USB PD 9V/3A`（`27W+`）持续拍摄（`5V/1.5A` 触发低功率掉电告警）；强制**插入具备余电的 `NP-FZ100`** 才可开机运行（`libUsbBusPower.so` `GetCurrentBattState`/`IsSinkReady`，无电池 USB 启动返 `EOPNOTSUPP=95`，拔电池断电无热插拔返 `EINVAL=22`）；严格区分 **ON 态绝不充电**（`CHARGE` LED `OFF`）与 **OFF 态充电**（`10..30°C` 窗内常亮，超窗快闪故障）；`DC-C1` 假电池要求 `>= 65W` PD + `5A` 线缆且监视器亮度锁定最大。
  - 对照 FX6 `19.5V` EIAJ `DC IN`（支持真无电池冷启与拔电热切 `BP-U`，但录影中热重插 `DC IN` 存在重启风险 -> `EBUSY=16`；USB-C 不支持整机供电 -> `EOPNOTSUPP=95`）。
- **`实测事实`（`[NTSC/PAL Selector]` SKU 锁、纯 XAVC 免格式重启与 `Slot 1` `EROFS=30` 防火墙）**：
  - 锁定 `lib::backup_get_ntsc_pal_selector_dst` 区域门控：`J1` 日本机锁死 NTSC-only（切 PAL 返 `EOPNOTSUPP=95`）；`CE`/`E33` PAL 默认机切 NTSC 弹 `Running on NTSC.`；`U2` NTSC 默认机切 PAL 弹 `Running on PAL.`；Ver. 7.02 纯 XAVC 切换触发强制重启但不强制格式化存储卡；异制式影片回放硬拦截（`EOPNOTSUPP=95`）。
  - 强制 Tier-0 **`Slot 1` `EROFS=30` 防火墙**：任意指向 `Slot 1` 的 `AVF_INFO` `Create?` / `Update?` / `Recover Image DB` / `Format` 写操作均硬返 **`EROFS (errno 30)`**（`slot1_data_sector_writes == 0`、`emmc_nflasha_write_count == 0`），并对 `Recover Image DB` 执行低电量保护（`<10%` 或 `<6400 mV` -> `EINVAL=22`）；对照 FX6 `Project > Rec Format > Frequency` 6 档重启与 `Thumbnail` 严格按当前频率过滤（`384` 状态矩阵）。
- **`推断`**：FX3 PMIC 架构以电池母线作为瞬态稳压与鉴权参考，因此在台架复现/验证阶段必须保持合规满电 `NP-FZ100` 或 `>=65W/5A` `DC-C1`，并严格区分 NTSC 与 PAL 测试卡以防止误操作触发 `Slot 1` 写盘。

---

## 3. 实测验证结果（`实测事实`）

| 检查项 / 命令 | 覆盖范围 | 执行模式 | 实测结果 |
| :--- | :--- | :--- | :--- |
| `test_realhw_peaking_audio_wind_usbpd_ntscpal_160gate_guard.py` | `108` 项单元测试（4 模式） | Normal / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / Donorless (`work_root=None`) | 全部 PASS（`108/108` × 4：`69.83s` / `65.87s` / `63.82s` / `65.95s`，`0` 失败） |
| `python3 -B -m fx3_safety verify-g159 --summary` & `verify-g160 --summary` | 单门禁 CLI 校验 | `LOCAL_DONOR_O_RDONLY` | PASS（`G159` 与 `G160` 均 `valid=True`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-160-gates --summary` | `G01..G160` 统一预检 | 离线默认 NO-GO（`LOCAL_DONOR_O_RDONLY`） | PASS（`157/160`，`VERIFIED_157_OF_160_AWAITING_PHYSICAL_TIER0`，`ready_attach=False`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-160-gates --simulate-bench-dry-run --force-clean-room --summary` | `G01..G160` 统一预检 | 离线模拟干跑（`CLEAN_ROOM_SYNTHETIC`） | PASS（`160/160`，`VERIFIED_ALL_160_GATES_DRY_RUN_SIMULATED_BACKUP`，所有写/连机红线恒 `False`/`0`） |
| 全量 `outputs/fx3-safety/tests`（`82` 个测试文件，3 并发） | `4,929` 项安全测试 | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 PASS（Normal `4,929/4,929` `322.76s`；Clean-Room `4,929/4,929` `274.70s`，`0` 失败） |
| `make verify-milestone-364`（双模） | 上游主闭环自动发现 | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 PASS（`status=OK`，`pillars=6/6`，自动发现 `gate156=157/160`，`leaked=0`） |
| `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | 仓库洁净度与字节码审计 | 离线 | `ALL GREEN in 0.10s`（零未跟踪二进制，零 `.pyc`，仅含 6 个受控文件） |
