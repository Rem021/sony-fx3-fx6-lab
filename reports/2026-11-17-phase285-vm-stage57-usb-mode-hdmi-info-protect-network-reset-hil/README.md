# Phase 285（Stage 57 / `57/57`）工程报告 — Wave-47 `[USB Connection Mode]` / `NOUVC` 分裂与数据隔离 PD、`[HDMI Info. Display]` 洁净覆写、`[Protect]` vs `[Format]` `Slot-1` 双层防卫及 `[Reset Network Set.]` 协同仿真闭合

> **核心结论（GO / 57/57 ALL GREEN）**：已完成 **Phase 285 Stage 57（`57/57`）** Wave-47 真实硬件协同仿真台架落地与全栈合流。严格依据 [Wave-47 权威分析报告](../2026-11-17-global-sony-wave47-usb-connection-mode-hdmi-info-protect-reset-network-intel/README.md) 与 `13` 份 `ILME-FX3 Ver. 7.02` / `ILME-FX6 Ver. 6.01` `os.O_RDONLY` 实机供体（冷启动 `< 0.2s`，`raw_firmware_bytes_leaked == 0`），将 `[USB Connection Mode]` 4 模式 vs 休眠 `NOUVC` `[USB Streaming]` 分裂与数据隔离 USB PD、`[HDMI Info. Display]` 关屏/干净输出与 `1080` 钳位 vs `4K` 自动清屏覆写、`[Protect]` 4 范围 vs `[Format]` 抹除（`Slot-1` 硬件 SD `WP` + 软件硬锁防火墙）以及 `[Reset Network Set.]` 自动重启后复设 `[Airplane Mode] = [On]` 接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)。全部 `76` 项 Stage 57 双模单测（本地 `O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 三模全绿）、`outputs/fx3-vm/tests` 全量单测、Milestone `264` / `254` 双模门控（`vm_stages=57/57`）以及 `scripts/run_all_lab_tests.py --clean-only` 全仓洁净测试均实测通过，零硬件写入与零越权修改。

---

## 1. 交付文件清单（严格限定自有域 `5` 项）

| # | 交付文件 | 角色与实测状态 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py`](../../outputs/fx3-vm/realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py) | **新增**：Phase 285 Stage 57 (`57/57`) 协同仿真器（13 供体 `O_RDONLY` 有界检查 + Sub-Model 57A/57B/57C + 16 项红线探针 + `CLEAN_ROOM_SYNTHETIC` 确定性回退） |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | **修改**：注册 `stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil`，扩展 `CoEmulationConfig` 与 `--include-stage57` / `--skip-stage57` / `--no-include-stage57` / `--skip-phase285` CLI 开关及 `--summary` 摘要行（`vm_stages=57/57`） |
| 3 | [`outputs/fx3-vm/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py) | **新增**：`76` 项双模单元/CLI/套件回归测试（覆盖 3 种运行模式、全部 `assertGreaterEqual(len(stage_keys), 57)`、`sys.executable` 可移植性与 `15.0s` CI 时限裕量） |
| 4 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | **修改**：补充 Phase 285 Stage 57（`57/57`）架构说明与多模验证命令 |
| 5 | [`reports/2026-11-17-phase285-vm-stage57-usb-mode-hdmi-info-protect-network-reset-hil/README.md`](README.md) | **新增**：本 Phase 285 结论先行工程验收报告 |

---

## 2. 技术实现摘要与三子模型闭环

### 2.1 高速 `O_RDONLY` 13 供体精确锚定与 `CLEAN_ROOM_SYNTHETIC` 对等性
- **FX3 4 语言 `.uxc`（`_f` 主字符串包）**：`string_english_f.uxc`（`373,820 B`）、`string_simplifiedchinese_f.uxc`（`322,652 B`）、`string_traditionalchinese_f.uxc`（`324,148 B`）、`string_japanese_f.uxc`（`447,840 B`）严格按 64 位 SHA-256 核验；并补充 `string_english.uxc`（`165,740 B`）、`string_english_g.uxc`（`69,600 B`）以及 FX6 `string_english.uxc`（`118,208 B`）、`string_english_2.uxc`（`118,676 B`）。
- **内核模块 & 主应用对比供体**：验证 `usb_f_uvc.ko` 在 FX3 `7.02` 与 FX6 `6.01` 中均存在且完全同长（`78,840 B`）；对 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）执行 `<= 4096 B` 有界窗口读数 + 4 KiB 头部 SHA-256 核验，冷启动读取耗时 `< 0.2s`，`raw_firmware_bytes_leaked == 0`。

### 2.2 Sub-Model 57A：`[USB Connection Mode]` 4 模式 vs 休眠 `NOUVC` & 数据隔离 PD HIL
- **Stock `ILME-FX3 Ver. 7.02` 4 模式闭环**：`Sel. When Connect`（`0x7738` 出厂默认）、`MassStorage(MSC)`（`0x6c54` / `054C:0DA1` / `USB_CONNECTION_METHOD_MASS_STRAGE`）、`MTP`（`0xe24b`，Slot 1）、`Remote Shoot (PC Remote)`（`0x60aa`）。
- **休眠 `NOUVC` 防伪造分裂**：虽然 `appFw.so`、`string_*_f.uxc`（`0x7399`）与 `usb_f_uvc.ko` 均随固件存在，但 `ILME-FX3` / `ILME-FX3A` 屏蔽了原生 `[USB Streaming]` UVC/UAC（`fx3_ui_exposes_native_usb_streaming == False`、`usb_f_uvc_insmod_at_fx3_boot == False`），伪造切换请求以 `EOPNOTSUPP = 95` 拦截，并与 `ILME-FX6` `ProCam` UVC（`BKID_APP_SETTING_USB_STREAMING_PROCAM`）及同门 UVC 机型对照验证。
- **`[USB LUN Setting]`、`[USB Power Supply]` 与气隙台架规则**：建模 `Multi`（`2 LUN` 默认）vs `Single`（`1 LUN`）、仅限 USB Type-C 且须装入 `NP-FZ100` 电池的 USB PD 供电、`(Setup)` 跨 `[Camera Settings Reset]` 存活（仅 `[Initialize]` 还原），以及**气隙 Tier-0 台架仅在 `D+/D-` 与 SuperSpeed 数据线物理隔离（`usb_data_lines_physically_isolated == True`）时才放行 USB PD 供电**（否则 `EACCES = 13` 阻断，`tier0_usb_data_enumeration_violations == 0`）。

### 2.3 Sub-Model 57B：`[HDMI Info. Display]` 关屏/干净输出、`1080` 钳位与 `4K` 自动覆写 HIL
- **`On` vs `Off` 液晶与触控行为**：默认 `On`（`0xe07c`）在输出 OSD 叠加与缩框视图的同时黑屏关闭内置 LCD 并禁用触控对焦（`CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`）；`Off`（`0xe297`）输出干净 HDMI 并恢复内置 LCD 与触控对焦激活。
- **`1080` Log/`PPLUT` 钳位与 `4K` 自动清屏覆写**：机内录制（`Rec. Media dur HDMI Output = On`）伴随 `Log Shooting != Off`（`Flexible ISO` / `Cine EI` / `Cine EI Quick`）或 `PPLUT1..4` 时强行钳位外录分辨率为 `1080`（强绕过返回 `EOPNOTSUPP = 95`）；启用 `Off(HDMI Only)`（`0x6573`）或 `RAW Output = On`（`0x6e97`，`4264x2408`）则输出 `4K` 并自动覆写 `[HDMI Info. Display] = [Off]`（`S&Q` 锁定 `Rec. Media = On` 与 `RAW Output = Off`）。同步验证 `(Setup)` 跨 `[Camera Settings Reset]` 存活及 `[Framing Settings (HDMI)]` 例外复位。

### 2.4 Sub-Model 57C：`[Protect]` 4 范围 vs `[Format]` 抹除（`Slot-1` 双层锁定）& `[Reset Network Set.]` 自动重启 HIL
- **`[Protect]` 不防 `[Format]` 与 `Slot-1` 双层保险**：在 `Slot 2` 虚机草稿区验证全部 `4` 项 `[Protect]` 范围（`Multiple Img.` `0xe2ca`、`All in this Folder` `0x6848`、`All with this date` `0x69f7`、`All Images in This Group` `0xe826`）可阻止 `[Delete]` / `[Delete pressing twice]`（`EROFS = 30`），但 `[Format]`（`Quick`/`Full`）会直接清空受保护文件与 `M1..M4` 设置；因此在 `Slot 1` 强制启用**硬件 SD `WP` 物理锁开关（`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`）+ 软件硬锁防火墙（`slot1_format_hard_locked == True`、`EROFS = 30`）**，确保持有恢复保险库的 `Slot 1` 零破坏。
- **`[Reset Network Set.]` 自动重启与复设 `[Airplane Mode] = [On]`**：建模该操作清空 12 域 `(Network)` 凭据、完整保留 `(Shooting)`/`(Setup)`/`(Playback)`/`CAMSET`、触发强制自动重启（`BKID_APP_is_shutdown_factor_network_reset`）并将 `[Airplane Mode]` 复位至 `Off`，要求**重启后立即复设 `[Airplane Mode] = [On]`（`0x6df9`）**以恢复零射频姿态（未复设在零射频台架下返回 `EACCES = 13`，`post_reset_airplane_off_rf_leak_events == 0`、`passive_tx_bytes_emitted == 0`）。
- **16 项红线探针全部闭环**：任意触及 eMMC 写入、硬件实机挂载、ISP/SPI-NOR/EL3、`cnflasha`、CP/WBI、`NOP` 补丁、原生 UVC 伪造、未隔离 USB 枚举、HDMI 清屏违规、`Slot-1` 擦除或网络重置后漏开射频等操作均确定性 fail-closed 拦截。

---

## 3. 实测验证矩阵（实测命令与结果）

| 验证项目 | 运行模式 / 覆盖范围 | 实测结果 |
|---|---|---|
| Stage 57 独立自检 CLI（`--self-test --summary` / `--json`） | `LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | 三模 `PASS`，`donors=13`，`leaked=0` |
| Stage 57 单元/套件测试（`76` 项） | `LOCAL_DONOR_O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **76/76 PASS**（三模全绿） |
| 全板 57 阶段协同套件（`fx3_vm_coemulation_suite.py`） | 默认本地供体 + `--clean-room` | `[PASS]` `vm_stages=57/57` |
| `outputs/fx3-vm/tests` 全量自动发现套件 | 本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 `OK` |
| Milestone `264` & `254` 门控（`make verify-milestone-264` / `verify-milestone-254`） | 本地供体 + 洁净室双模（`vm_stages=57/57`） | **ALL GREEN** |
| 全仓洁净回归（`scripts/run_all_lab_tests.py --clean-only`） | `CLEAN_ROOM` 全仓回归 | **ALL GREEN** |
