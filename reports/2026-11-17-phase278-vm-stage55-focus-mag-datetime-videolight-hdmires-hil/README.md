# Phase 278 — VM Stage 55（`55/55`）真实硬件 `ILME-FX3` Wave-45 `[Focus Assistant]` / `[Peaking Display]` / `[AF Illuminator]`、`[Area/Date/Time Setting]` 零射频隔断、以及 `[Video Light Mode]` & `[HDMI Resolution]` HIL 协同仿真工程报告

- **日期**: `2026-11-17`
- **任务 / 分支**: `H317` / `codex/h317-phase278-vm-stage55-focus-mag-datetime-videolight-hdmires-hil`
- **目标 Schema 与 Stage**: `realhw_focus_mag_datetime_videolight_hdmires_coemulator_v1`（`version = 278.0.0`，`phase_number = 278`，`stage = stage55_realhw_focus_mag_datetime_videolight_hdmires_hil`，将 `outputs/fx3-vm/` 全板协同仿真从 `54/54` 推进至 **`55/55`**）
- **Wave-45 权威规格参考**: [`reports/2026-11-15-global-sony-wave45-milestone-focus-magnifier-auto-mag-mf-area-datetime-video-light-hdmi-res-intel/README.md`](../2026-11-15-global-sony-wave45-milestone-focus-magnifier-auto-mag-mf-area-datetime-video-light-hdmi-res-intel/README.md)

---

## 1. 核心结论（结论先行）

1. **完成 Phase 278 Stage 55（`55/55`）Wave-45 HIL 协同仿真器交付**：新增 [`outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py`](../../outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py)，并在 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 中接入 `stage55_realhw_focus_mag_datetime_videolight_hdmires_hil`（支持 `--include-stage55` / `--skip-stage55` / `--no-include-stage55` / `--skip-phase278` 与 `stage55_ok`），将全板 `FX3-VM` 阶段计数从 `54/54` 推进至 **`55/55`（`vm_stages=55/55`）**。
2. **双模 18 供体 `os.O_RDONLY` 校验与 `CLEAN_ROOM_SYNTHETIC` 对等（实测事实）**：严格以 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（`10` 份全量 SHA-256 + `8` 份 `<= 4096 B` 有界窗口 + 头部 4 KiB SHA-256，冷/热校验 `< 0.2s`，`raw_firmware_bytes_leaked == 0`），并在 `FX3_CLEAN_ROOM_TEST=1` 或 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下切换确定性洁净室基线（三大核心子模型输出完全一致）：
   - `LOCAL_DONOR_O_RDONLY` 摘要：`19f350d3eb3a`（`fx3_vm_coemulation_suite` 55 阶段摘要 `3eec658cbcac`；`verify-milestone-264` SHA-256 `a2369fd46b8dec92...`；`verify-milestone-254` SHA-256 `498119a42ecd4b67...`）
   - `CLEAN_ROOM_SYNTHETIC` 摘要：`dd1ea9affac9`（`fx3_vm_coemulation_suite` 55 阶段摘要 `3aba7b0f7a65`；`verify-milestone-264` SHA-256 `909bb54f8f21d5e3...`；`verify-milestone-254` SHA-256 `f90d307bcc8a4b76...`）
3. **安全、BYOF 与 Wave-45 硬件红线全部零容忍锁死（实测事实）**：`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`overall_ready_for_hardware_attach = False`、`isp_write_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`cnflasha_userspace_write_blocked = True`、`cnflasha_mutation_bytes = 0`、`physical_device_writes = 0`、`emmc_corruptions = 0`、`nop_count = 0`、`guest_code_modification_bytes = 0`、`legacy_mf_assist_spoof_events = 0`、`hdmi_clean_feed_mag_or_peaking_leaked_pixels = 0`、`af_illuminator_movie_or_sq_fire_events = 0`、`legacy_date_time_setup_spoof_events = 0`、`passive_tx_bytes_emitted = 0`、`creators_app_rtc_sync_jump_events = 0`、`mishoe_5v_900ma_overcurrent_events = 0`、`hdmi_log_1080p_downshift_bypass_events = 0`、`raw_firmware_bytes_leaked = 0`，且仓库零 `.pyc` / `__pycache__` 残留。
4. **前向兼容阶段数断言**：Stage 54 既有单测已全部采用 `assertGreaterEqual(len(stage_keys), 54)`（无需修改旧测试文件），Stage 55 新增 72 项单测采用 `assertGreaterEqual(len(stage_keys), 55)` 并严格遵守 `sys.executable`、CI 耗时裕量与 `argparse` `%%` 转义规范。

---

## 2. 本次变更文件清单（严格限定 5 个授权文件）

| # | 文件 | 说明 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py`](../../outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py) | **NEW** — Phase 278 Stage 55 (`55/55`) Wave-45 HIL 协同仿真器 |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 注册 `stage55_realhw_focus_mag_datetime_videolight_hdmires_hil`、`--include-stage55` / `--skip-stage55` / `--no-include-stage55` / `--skip-phase278`、`stage55_ok` 与 `--summary` 摘要行（`55/55`） |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 278 Stage 55（`55/55`）架构、子模型契约与双模 CLI 命令说明 |
| 4 | [`outputs/fx3-vm/tests/test_realhw_focus_mag_datetime_videolight_hdmires_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_focus_mag_datetime_videolight_hdmires_coemulator.py) | **NEW** — `72` 项三模式单元测试（使用 `sys.executable`、CI 耗时裕量与 `assertGreaterEqual(..., 55)`） |
| 5 | [`reports/2026-11-17-phase278-vm-stage55-focus-mag-datetime-videolight-hdmires-hil/README.md`](README.md) | **NEW** — 本阶段中文结论先行工程交付报告 |

---

## 3. 核心架构与 Wave-45 硬件契约建模

### 3.1 `O_RDONLY` 18 供体核验（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`）
- 只读核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 共 `10` 份紧凑构件全量 SHA-256（`libInfraAdjMedia.so` `318,152 B`、`libInfraAirplaneMode.so` `14,488 B`、`libSaveLoadSettings.so` `18,760 B`、`libBusPower.so` `43,968 B`、`libInfraMediaConfig.so` `52,312 B`、`libInfraMediaCommon.so` `402,624 B`、`libInfraBluetoothCore.so` `267,592 B`、`libWlanControlCommon.so` `18,528 B`、FX3 `string_english_f.uxc` `373,820 B`、FX6 `string_english.uxc` `118,208 B`），以及 `8` 份大体积构件（FX3/FX6 `appFw.so`、`cpapp-b.bin`、`libmpr.so`、`BK4`）各 `<= 4096 B` 有界窗口偏移令牌与 4 KiB 头部 SHA-256。
- 在 `string_english_f.uxc` 中精确证实 Wave-45 全量官方 `ilc/2210` 词条，并在 `string_english_f.uxc` 中硬验证 `Date/Time Setup`、`Autoframing Settings`、`Built-In ND`、`ECS` 为 `0` 命中。

### 3.2 Sub-Model 55A — `[Focus Assistant]`、`[Peaking Display]` 与 `[AF Illuminator]`（仅限静态照片）
- **`MENU -> Focus -> [Focus Assistant]`**：
  - `[Auto Magnifier in MF]`（`On` 默认 / `Off`）— 严格绑定官方 `ilc/2210` 标题，对旧款 `"MF Assist"` 伪造以 `EOPNOTSUPP = 95` 硬阻断（`legacy_mf_assist_spoof_events == 0`）。
  - `[Focus Magnifier]`：默认映射至 `Custom Button 5`，并在 `Touch Operation = On` 且处于 `MF`/`DMF` 时支持机背 LCD 双击放大。
  - `[Focus Magnif. Time]`：`No Limit`（默认）/ `2 Sec` / `5 Sec`。
  - 独立 Still 与 Movie `[Initial Focus Mag.]` 寄存器：各自独立保存并默认 `x1.0`（支持 `x1.0` / `x4.0`），切换域互不串扰。
  - Still `[AF in Focus Mag.]`：`On`（默认，半按快门于放大区内重新对焦）/ `Off`（Movie / `S&Q` 禁用此项并返回 `EOPNOTSUPP = 95`）。
  - HDMI 纯净输出退出与 `RAW Output` 互斥：`HDMI RAW Output = On` 时锁定禁用放大倍率输出；且无论 `Focus Magnifier` 还是 `Peaking Display` 均严格限定于机内 LCD 叠加，绝不渗漏至外接 HDMI（`hdmi_clean_feed_mag_or_peaking_leaked_pixels == 0`）。
- **`[Peaking Display]` & `[AF Illuminator]`**：
  - `[Peaking Display]`（`Off` 默认 / `On`）、`[Peaking Level]`（`Mid` 默认：`High`/`Mid`/`Low`）、`[Peaking Color]`（`White` 默认：`Red`/`Yellow`/`Blue`/`White`），仅作用于机内 LCD。
  - `[AF Illuminator]`（`Auto` 默认 / `Off`）：**严格仅限 Still 静态照片 AF**，在 `Movie` 与 `S&Q` 下强制永不触发（`af_illuminator_movie_or_sq_fire_events == 0`）。

### 3.3 Sub-Model 55B — `[Area/Date/Time Setting]`（`Setup > Area/Date`）与零射频 Creators' App 隔离
- 严格强制 `ilc/2210` 官方标题 `[Area/Date/Time Setting]`（硬拒绝旧款 `"Date/Time Setup"` 伪造，`EOPNOTSUPP = 95`，`legacy_date_time_setup_spoof_events == 0`）：覆盖 `[Area Setting]`（初始 `"—"`）、`[Daylight Savings]`（`Off` 默认 / `On`）、`[Date/Time]` 与 `[Date Format]`（`Y-M-D` / `M-D-Y` / `D-M-Y`）。
- 验证其位于 `[Setup]` 菜单下，跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存，仅由 `[Initialize]` 或 RTC 后备电池耗尽触发清零并重新提示设置。
- 在零射频气隙台架（`[Airplane Mode] = [On]`，`passive_tx_bytes_emitted == 0`）下以 `EACCES = 13` 阻断 Creators' App `[Location Information Linkage]`（`[Auto Time Correction]` / `[Auto Area Adjustment]`）蓝牙/Wi-Fi 时间/时区同步，确保 `H0..H3` 取证链路 RTC 时间戳单调无跳变（`creators_app_rtc_sync_jump_events == 0`）。

### 3.4 Sub-Model 55C & 红线 — `[Video Light Mode]`（`Power Link` & MI 热靴 `5V <= 900 mA`）与 `[HDMI Resolution]`（`Auto` & Log `1080p` 下变换）
- **`[Video Light Mode]`**：支持 `Power Link`（默认）/ `REC Link` / `REC Link & STBY` / `Auto`，驻留 `[Setup]` 下跨 `[Camera Settings Reset]` 存活；并与 `Gate G24` 对等建模 MI 热靴 `5V <= 900 mA` 供电轨预算，`> 900 mA` 触发 `EACCES = 13` 过流硬件闭锁（`mishoe_5v_900ma_overcurrent_events == 0`）。
- **`[HDMI Resolution]`**：支持 `Auto`（默认，EDID 协商）/ `2160p` / `1080p` / `1080i`，驻留 `[Setup]` 下跨 `[Camera Settings Reset]` 存活（仅 `[Initialize]` 恢复 `Auto`）；精确建模当 `[Log Shooting] != Off` 且正在机内录制时自动强制下变换至 `1080p`（除非 `[Rec. Media dur HDMI Output] = Off(HDMI Only)`），任何绕过企图返回 `EOPNOTSUPP = 95`（`hdmi_log_1080p_downshift_bypass_events == 0`）。
- 全量覆盖 `16` 项安全红线探针并保持全部 `0` 事件 / `False` 授权状态。

---

## 4. 实测验证矩阵与工程推断边界

- **实测事实（Measured Facts）**：以下全部验证命令均在分支 `codex/h317-phase278-vm-stage55-focus-mag-datetime-videolight-hdmires-hil` 下通过 `PYTHONDONTWRITEBYTECODE=1` 执行，全部退出码为 `0`：

| 验证门禁 | 运行模式 | 实测结果 |
|---|---|---|
| `test_realhw_focus_mag_datetime_videolight_hdmires_coemulator.py` | `LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`72 / 72` PASS**（`2.675s` 本地供体 / `0.746s` `FX3_CLEAN_ROOM_TEST=1` / `0.716s` `FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 全量 `outputs/fx3-vm/tests` (`unittest discover`) | `LOCAL_DONOR_O_RDONLY` | **`2537 / 2537` PASS**（`166.574s`，`0` 失败） |
| 全量 `outputs/fx3-vm/tests` (`unittest discover`) | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2537` 运行（`2534` PASS，`3` 项供体专属跳过）**（`151.372s`，`0` 失败） |
| `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=55/55 leaked=0`**（双模通过） |
| `make verify-milestone-254` | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK pillars=6/6 vm_stages=55/55 leaked=0`**（双模通过） |
| `python3 -B scripts/run_all_lab_tests.py --clean-only` | Clean-Room Hygiene & BYOF Audit | **`ALL GREEN`**（`0.04s`，`0` `.pyc` 文件，工作区干净） |

- **工程推断（Engineering Inference）**：在离线 HIL 协同仿真中同时锚定 `ilc/2210` 官方词条边界（拒止旧款 `"MF Assist"` / `"Date/Time Setup"` 伪造）、HDMI 纯净输出（禁止放大与峰值叠加及 Log 录制期间未授权 `2160p` 旁路）、`Airplane Mode = On` 零射频 RTC 时间戳稳定性，以及 MI 热靴 `5V <= 900 mA` 电流护栏，可在零实体硬件接触的前提下完备覆盖 Wave-45 全套辅助对焦、时区时钟与热靴/HDMI 协同行为；真实物理设备写入及带机连接仍严格锁定禁用（`overall_ready_for_hardware_attach == False`）。
