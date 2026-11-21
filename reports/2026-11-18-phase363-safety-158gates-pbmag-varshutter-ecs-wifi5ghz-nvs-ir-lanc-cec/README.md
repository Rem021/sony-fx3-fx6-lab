# Phase 363（`Task H457`，Wave-69，`158/158` 硬件安全门禁里程碑）：Still-Only `Playback -> [Magnification]`（`maginify` 拼写与零视频放大 vs FX6 `Thumbnail`/`Rec Review`/`Focus Magnifier`）+ `[Anti-flicker Shoot.]`（`100/120Hz`）vs 休眠 `[Var. Shutter]`/`[Anti-flicker Tv Scan]`（`EOPNOTSUPP=95`）与 FX6 `ECS`（`G157`），及 `Wi-Fi` `WW728473`/`WW558244` 5GHz SKU 锁 + `[Airplane Mode]` 抗 `[Reset Network Set.]` + `p12/p13` `MS_RDONLY` RF NVS 防火墙与前部 `#5` `[IR Remote Ctrl]`/`[CTRL FOR HDMI]`（`ctrl_for_hmdi` 默认 `On` 41 键 CEC 劫持防线、零 `CEC_REC`）vs FX6 `2.5mm LANC`（`G158`）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H457` · **Phase 363（`158/158` 硬件安全门禁里程碑）**
- **核心结论**：
  1. 已交付门禁 **`G157`**（[`verify_pbmag_varshutter_ecs_guard`](../../outputs/fx3-safety/fx3_safety/realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.py)）与 **`G158`**（[`verify_wifi5ghz_nvs_ir_lanc_cec_guard`](../../outputs/fx3-safety/fx3_safety/realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.py)）及统一预检引擎 **`verify-158-gates`**（[`evaluate_158gate_preflight`](../../outputs/fx3-safety/fx3_safety/realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.py)）。
  2. 离线默认模式实测通过 **`155/158`** 项门禁（`VERIFIED_155_OF_158_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach = False`）；`--simulate-bench-dry-run --force-clean-room` 演练模式通过 **`158/158`** 项（`VERIFIED_ALL_158_GATES_DRY_RUN_SIMULATED_BACKUP`），所有物理写盘/刷机/实时连机红线恒为 `False` 与 `0`。
  3. 4 模式 158 门禁单元测试（`104/104`）、全量 `outputs/fx3-safety/tests`（`81` 个测试文件共 `4,821/4,821` 项测试，正常模式与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模）、[`fx6_closure verify-milestone-349`](../../outputs/fx6-on-fx3-closure/)（正常模式与 `--force-clean-room`）及 `make clean-audit` 全部通过（`ALL GREEN`，`raw_firmware_bytes_leaked == 0`）。
- **Wave-69 实证基线**：[Wave-69 调研报告](../2026-11-17-global-sony-wave69-pb-magnify-varshutter-ecs-wifi-5ghz-nvs-ir-lanc-cec-intel/README.md) 与 [`realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulator.py`](../../outputs/fx3-vm/realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulator.py)
- **硬件安全姿态**：对 15 个本地 donor 构件严格采用只读 `os.O_RDONLY` + 有界 `os.pread`（`< 0.20s` 预算）并内置无盘 clean-room 回退（`raw_firmware_bytes_leaked == 0`、`emmc_writes_authorized == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`usb_packets_transmitted == 0`）。

---

## 1. 交付物清单（严格 6 个受控文件）

- 门禁与 158 门禁统一预检模块：[`realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.py`](../../outputs/fx3-safety/fx3_safety/realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.py)
- 包导出与 CLI 注册（`verify-pbmag-varshutter-ecs-guard` / `verify-g157`、`verify-wifi5ghz-nvs-ir-lanc-cec-guard` / `verify-g158`、`verify-158-gates`）：[`fx3_safety/__init__.py`](../../outputs/fx3-safety/fx3_safety/__init__.py)、[`fx3_safety/__main__.py`](../../outputs/fx3-safety/fx3_safety/__main__.py)、[`outputs/fx3-safety/README.md`](../../outputs/fx3-safety/README.md)
- 4 模式单元测试套件（`104` 项测试）：[`test_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_158gate_guard.py`](../../outputs/fx3-safety/tests/test_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_158gate_guard.py)
- 工程收尾报告（本文件）：[`reports/2026-11-18-phase363-safety-158gates-pbmag-varshutter-ecs-wifi5ghz-nvs-ir-lanc-cec/README.md`](./README.md)

---

## 2. 新增安全门禁与技术约束

### 2.1 门禁 `G157`：`PBMAG_ZERO_MOVIE_ZOOM_AND_ANTI_FLICKER_VS_DORMANT_VAR_SHUTTER_ECS_FIREWALL`
- **`Playback -> [Magnification]`（精确 3 个活跃条目）**：
  - 覆盖 `[Enlarge Image]`（`base 0xe8cb`）、`[Enlarge Initial Mag.]`（`_f 0x6b6e`，默认 `Standard. Mag.` / `Previous Mag.`）与 `[Enlarge Initial Position]`（`_f 0x781f`，默认 `Focused Position` 并在无对焦点时回退至 `Center` / `Center`）。
  - 锁定 `W/T` 变焦杆、捏合放大（Sony ELF 拼写 `playback_zoom_maginify_by_pinch`）与双击放大（要求 `[Touch Operation] = On`，否则返回 `EINVAL=22`）、拨盘切图保留倍率及 `MENU`/中央退出行为。
  - **Reset 免疫**：`[Magnification]` 全项对 `[Camera Settings Reset]` 免疫（`Not available`），仅 `[Initialize]` 清零。
  - **视频回放放大硬禁令**：`playback_zoom::is_inhibition()` 对任意视频回放放大操作拒绝并返回 `base 0xe572` `"Unable to magnify."`（`EOPNOTSUPP=95`）。
  - **FX6 Ver. 6.01 对照**：零静态拍照、零回放放大（`Enlarge Screen` `ns1 0x2b0e` 休眠 -> `EOPNOTSUPP=95`），采用 `THUMBNAIL`（`ns1 0x2088`）+ `Rec Review`（`3s/10s/full`）+ 拍摄态 `Focus Magnifier` `x3/x6`。
- **`Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]` vs 休眠 `[Var. Shutter]` / `[Anti-flicker Tv Scan]` / FX6 `ECS`（`384` 状态组合矩阵）**：
  - `[Anti-flicker Shoot.]`（`_f 0x623d`，默认 `Off` / `On`，**可被 `[Camera Settings Reset]` 重置**）：仅限静态 `100Hz/120Hz` 机械快门；在 `Movie`、`S&Q`、`Electronic Shutter`、`[Silent Mode] = On` 及 `BULB` 下禁用（`EINVAL=22`）。
  - 共享 Alpha 高像素符号 `[Anti-flicker Set.]`（`_f 0x68e7`）、`[Var. Shutter]`（`_f 0x64cf`/`0x6831`，`BKID_APP_setting_high_res_ss`）、`[Var. Shutter Set.]`（`_f 0x6f9e`/`0x7af8`）与 `[Anti-flicker Tv Scan]`（`_f 0x63c0` / `_g 0x60a8` 空串 `""`，`sequence_flicker_scan.cpp`）在 FX3 上 **100% 休眠/未暴露**，任何启用请求均被拦截为 `EOPNOTSUPP=95`。
  - **FX6 Ver. 6.01 对照**：`Shooting > Shutter > ECS`（`ECS Frequency` `23.99..8000 Hz` 连续范围校验与 6 档帧率预设 `59.94P->60.00`、`50P->50.00`、`29.97P->30.00`、`25P->25.02`、`24P->24.02`、`23.98P->23.99`）+ `Flicker Reduce`（`Off/Auto/On`，`50Hz/60Hz`）。

### 2.2 门禁 `G158`：`WIFI_5GHZ_SKU_P12_P13_MS_RDONLY_NVS_AND_IR_CTRL_FOR_HDMI_CEC_ZERO_LANC_FIREWALL`
- **`Network -> [Wi-Fi]` SKU 锁、安全基线、`[Airplane Mode]` 与 `p12/p13` 只读 NVS 防火墙**：
  - 校验 `lib::backup_get_wi_fi_frequency_band_dst` 硬件 SKU 门控：`WW728473`（`2.4GHz+5GHz`，户外强制 `2.4GHz`）vs `WW558244`（仅 `2.4GHz`，请求 `5GHz` 阻断 `EOPNOTSUPP=95`）。
  - Ver. 7.00+ 仅允许 `WPA2-PSK`/`WPA3-SAE`（淘汰 `WEP`/`WPA-PSK`/`IPsec`/`Open` -> `EOPNOTSUPP=95`）且强制 `[Access Authen. Settings] = On`；`[SSID/PW Reset]` 仅重置 Wi-Fi Direct。
  - **`[Airplane Mode] = On` 在 `[Reset Network Set.]`（`FUNC_reset_network_settings`）与 `[Camera Settings Reset]` 后保持不变**，仅 `[Initialize]` 恢复 `Off`（且强制 `rf_tx_packets == 0`）。
  - eMMC `p12`（`/dev/nflasha12`，`40 MiB` `/cert`）与 `p13`（`/dev/nflasha13`，`4 MiB` RF/MAC NVS）强制 **`MS_RDONLY`**，任何写入尝试均以 **`EROFS=30`** 拦截（`rf_nvs_mutation_bytes == 0`、`emmc_nflasha_write_count == 0`）。
  - **FX6 Ver. 6.01 对照**：`Wireless LAN`（`Access Point Mode` `Auto(5GHz)` vs `Station Mode`，`ILME-FX6V` `5GHz` vs `ILME-FX6T` `2.4GHz`，移除 NFC -> `EOPNOTSUPP=95`，与 `Wired LAN` 及 `Simul Rec` 互斥 -> `EBUSY=16`）。
- **`[IR Remote Ctrl]`、`[CTRL FOR HDMI]` CEC 劫持防线与零 `LANC`（`384` 状态组合矩阵）**：
  - `Setup -> [Setup Option] -> [IR Remote Ctrl]`（`_f 0x61a6`，默认 `Off`，**Reset 免疫**，仅 `[Initialize]` 重置）：对应前部 `#5` 红外接收窗（区别于 `#8` AF 辅助照明灯），**2025 `ILME-FX3A` 物理移除该传感器**（开启即阻断 `EOPNOTSUPP=95`），开启时绕过 `[Power Save Start Time]`，且与 `[Bluetooth Rmt Ctrl] = On` 互斥（`EBUSY=16`）。
  - `Setup -> [External Output] -> [CTRL FOR HDMI]`（`base 0xe41f`，Sony ELF 拼写 `BKID_APP_setting_ctrl_for_hmdi`，**出厂默认 `On` 且对 `[Camera Settings Reset]` 免疫**）：暴露精确 **41** 个 `EVENT_INPUT_KEY_CEC_*` 注入向量（含 `STANDBY_ON`/`OFF`、`ROOT_MENU`，且**零 `CEC_REC`**）；台架安全防火墙强制要求连接外接 HDMI 设备前必须确认 `[CTRL FOR HDMI] = Off`（`[Initialize]` 重置会将其恢复为 `On` 亦会被拦截）。
  - FX3 物理无 `2.5mm LANC` 与 `3.5mm Grip` 接口（`0` 个活跃 `BKID_APP_*_lanc*` 命中 -> `EOPNOTSUPP=95`），对照 FX6 `#24` `2.5mm` 3 极 `REMOTE (LANC)` 与 `3.5mm` 4 极手柄遥控（零用户 `IR Remote` / `CTRL FOR HDMI` 菜单）。

---

## 3. 实测验证结果（Observed Facts）

| 检查项 / 命令 | 覆盖范围 | 执行模式 | 实测结果 |
| :--- | :--- | :--- | :--- |
| `test_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_158gate_guard.py` | `104` 项单元测试（4 模式） | 正常 donor 模式 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / 模拟 `work_root=None` | 全部 PASS（`104/104` × 4：`64.14s` / `74.03s` / `62.81s` / `79.09s`，`0` 失败） |
| `python3 -B -m fx3_safety verify-158-gates --summary` | `G01..G158` 统一预检 | 离线默认 NO-GO（`LOCAL_DONOR_O_RDONLY`） | PASS（`155/158`，`VERIFIED_155_OF_158_AWAITING_PHYSICAL_TIER0`，`ready_attach=False`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-158-gates --simulate-bench-dry-run --force-clean-room --summary` | `G01..G158` 统一预检 | 离线模拟干跑（`CLEAN_ROOM_SYNTHETIC`） | PASS（`158/158`，`VERIFIED_ALL_158_GATES_DRY_RUN_SIMULATED_BACKUP`，所有写/连机红线恒 `False`/`0`） |
| `python3 -B -m fx3_safety verify-g157 --summary` & `verify-g158 --summary` | 单门禁 CLI 校验 | `LOCAL_DONOR_O_RDONLY` | PASS（`G157` 与 `G158` 均 `valid=True`，`leaked=0`） |
| 全量 `outputs/fx3-safety/tests`（`81` 个测试文件并行调度） | `4,821` 项安全测试 | 正常模式（3 并发）& `FX3_FX6_FORCE_CLEAN_ROOM=1`（8 并发） | 全部 PASS（正常模式 `4,821/4,821` `failures=0` `330.59s`；clean-room `4,821/4,821` `failures=0` `240.73s`） |
| `python3 -B -m fx6_closure verify-milestone-349` | 上游主闭环门禁 | 正常模式 & `--force-clean-room` | 全部 PASS（`status=OK`，`gate148=155/158`，`leaked=0`） |
| `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | 仓库洁净度与二进制/字节码泄漏审计 | 离线 | `ALL GREEN in 0.05s`（零未跟踪二进制，零 `.pyc`） |

> 注：全量 `81` 个 `fx3-safety` 测试文件若在单进程内串行 `unittest discover` 会超过单命令 600s 超时阈值，且 16 进程高并发下曾触发 4 项历史测试的 200ms donor 盘预算瞬态超时；在 3 并发正常模式及单测隔离复测中 `4,821/4,821` 全部稳定通过。
