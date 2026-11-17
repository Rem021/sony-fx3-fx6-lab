# Phase 279 实机拍摄前第 8 级物理台架准备度预检器报告（`preflight-usb-mode-hdmi-info-protect-and-network-reset` / Wave 47）

## 1. 核心结论（Conclusion-First）

1. **Wave 47 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`）物理台架检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增第 8 级宿主侧只读物理台架预检器 [`realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py)（Schema `realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier_v1`，版本 `279.0.0`，CLI 子命令 `preflight-usb-mode-hdmi-info-protect-and-network-reset`），将操作员实拍前预检链路推进至 `preflight-card-insert`（Ph186）→ `preflight-bench-cable-fan-slot1`（Ph204）→ `preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）→ `preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）→ `preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）→ `preflight-diffset-customkey-autoslow-and-apsc`（Ph261）→ `preflight-file-settings-gamma-assist-focus-mag-and-videolight`（Ph275）→ **`preflight-usb-mode-hdmi-info-protect-and-network-reset`（Ph279）**，导出符号全部采用无阴影 `P279_*` 前缀。
2. **三模式 70 项单元测试、全包 1,623 项发现测试与 Milestone 264 门禁全绿通过**：新增 [`test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py) 共 **70** 项确定性单测，在 `LOCAL_DONOR_O_RDONLY`（`2.591s`）、`FX3_CLEAN_ROOM_TEST=1`（`2.517s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`2.614s`）三种模式下 **70/70 全绿**，有界 `O_RDONLY` 供体校验耗时仅 **`0.52 ms`（`< 0.15s` 预算）**；全包 `outputs/fx6-on-fx3-closure/tests` 在 `/usr/bin/python3 -B` 本地供体模式下 **1,623/1,623 全部通过（`261.002s`）**、在 `FX3_FX6_FORCE_CLEAN_ROOM=1 python3 -B` 洁净室模式下 **1,623/1,623 通过（`165.475s`，`skipped=51`）**；`make verify-milestone-264` 双模式 `status=OK`（`2dfcb7ee3befe6f9...` / `c19365de83679c8d...`）；`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` 洁净无残留（`0.05s`）。*(注：实测中仅 `python3`（uv CPython 3.14.10）在本地供体多核负载下运行既有非本次修改文件 `test_phase52_stage_b_candidate_integrator.py::test_02_fast_execution_and_candidate_ready` 时耗时 `5.06–5.16s` 触发其 `< 5.0s` 断言，而在 `/usr/bin/python3 -B`（`3.813s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`3.310s`）下均通过。)*
3. **离线默认阻断与硬件安全红线 100% 锁死**：离线无回执时严格返回 `overall_status = READY_OFFLINE_AWAITING_BENCH_RECEIPTS` 与 `go_no_go = BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（CLI 退出码 `2`），`--simulate-bench-dry-run` 返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（CLI 退出码 `0`，`16/16 H0 == H3`），双物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` 验证通过返回 `GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_READONLY_PREFLIGHT_VERIFIED`，任意检查失败返回 `BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_CHECK_FAILURE`（CLI 退出码 `2`）；无条件锁死 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`usb_streaming_exposed_in_fx3_ui = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 与 `passive_tx_bytes_emitted = 0`。

---

## 2. 四大物理台架与官方帮助指南（`ilc/2210`）检查组（`Check Group A .. D`）

| 检查组 ID | 预检域（Wave 47） | 关键校验规则、边界与报错码 |
| :--- | :--- | :--- |
| **`GROUP_A_USB_CONNECTION_MODE_NOUVC_AND_DATA_ISOLATED_USB_PD`** | `[USB Connection Mode]` 4 模式 reality vs `NOUVC` 休眠 `[USB Streaming]` 与数据隔离 `USB PD` 规则（Wave 47 §1） | ① 校验原厂 `ILME-FX3 Ver. 7.02` `(Setup) -> [USB] -> [USB Connection Mode]`（`BKID_APP_setting_usb_connection_method`，`_f.uxc` `0x69a2`）仅暴露 **4** 种模式（`Sel. When Connect` `0x7738` 默认、`MassStorage(MSC)` `0x6c54` `054C:0DA1`、`MTP` `0xe24b`、`Remote Shoot (PC Remote)` `0x60aa`）；严格拒绝对 `ILME-FX3` 伪造 `[USB Streaming]`（UVC/UAC）暴露，尽管固件内编译了休眠态 `usb_f_uvc.ko`（`78,840 B`）与 `0x7399` 词条（`NOUVC` 屏蔽，`P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF`）；<br>② 气隙 Tier-0 台架强阻断 `MassStorage(MSC)`、`MTP`、`Remote Shoot` 与 `USB-LAN` 宿主数据枚举（`P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES`），仅在 USB `D+/D-` 与 SuperSpeed 数据线物理隔离时放行 `[USB Power Supply] = [On]`（`0x721e`，必须经 `USB Type-C` 且已插 `NP-FZ100`，禁止 Multi/Micro USB；`[USB LUN Setting]` `Multi` `0xe631` / `Single` `0x776d`）；<br>③ 校验 `(Setup)->[USB]` 跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 保留、仅在 `[Initialize]` 复位（`P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE`）。 |
| **`GROUP_B_HDMI_INFO_DISPLAY_CLEAN_FEED_AND_LOG_1080_VS_4K_OVERRIDE`** | `[HDMI Info. Display]` 黑屏/OSD 锁与洁净信号 vs `Log`/`PPLUT` `1080` 钳位与 `RAW`/`HDMI Only` `4K` 覆盖（Wave 47 §2） | ① 校验 `[HDMI Info. Display]`（`On` 默认 `0xe07c` 会熄灭内置 LCD 并禁用触控对焦 `CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`，HDMI 为含黑边字符叠加；`Off` `0xe297` 输出无叠加洁净信号并保持内置屏与触控可用，`P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT`）；<br>② 校验机内录制（`Rec. Media dur HDMI Output = On`）配合 `Log Shooting != Off` 或 `PPLUT1..4` 时将 HDMI 输出钳位至 `1080`（拒绝 `2160P`）；而 `Off(HDMI Only)`（`0x6573`）或 `RAW Output = On`（`0x6e97`）输出 `4K` 并自动强制 `[HDMI Info. Display] = [Off]`（`S&Q` 锁定禁止 `Off(HDMI Only)` 与 `RAW`，`P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE`）；<br>③ 校验 `(Setup)` 下外接输出设置跨 `[Camera Settings Reset]` 保留及 `[Framing Settings (HDMI)]` 复位例外（`P279_GB_ERR_SETUP_RESET_SURVIVAL_OR_FRAMING_HDMI_EXCEPTION`）。 |
| **`GROUP_C_PROTECT_4SCOPES_VS_FORMAT_OVERRIDE_AND_DUAL_LAYER_SLOT1_WP`** | `[Protect]` 4 范围防删锁 vs `[Format]` 覆盖擦除与 Slot-1 双层物理写保护 + 防火墙（Wave 47 §3） | ① 校验 `ILME-FX3` 全部 **4** 个 `[Protect]` 范围（`Single`/`Multiple Img.` `0xe2ca`、`All in this Folder` `0x6848`、`All with this date` `0x69f7`、`All Images in This Group` `0xe826`）阻断 `[Delete]` / `[Delete pressing twice]`，且拷贝到另一张卡会剥离保护属性（`P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID`）；<br>② 验证 **`[Format]`（`0xe449` / `0xe414`，Quick `0xe792` / Full `0xe8f5`）会强行抹除受保护文件与 `M1..M4` 卡内设置** — 因此 `Slot 1` 恢复金库介质必须同时具备 **物理 SD `WP` 开关锁定（`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`）** 与 **软件硬锁 `slot1_format_hard_locked == True`**，并阻断任何 `Slot 1` 删除/格式化请求（`P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL`）。 |
| **`GROUP_D_RESET_NETWORK_AUTOREBOOT_AIRPLANE_ZERO_RF_AND_TIER0`** | `[Reset Network Set.]` 自动重启（`BKID_APP_is_shutdown_factor_network_reset`）、3 向复位边界、重启后 `[Airplane Mode]=On` 与 Tier-0 双盘回执（Wave 47 §4 + Tier-0） | ① 校验 3 向复位边界：`[Reset Network Set.]` 清空 Wi-Fi/BT/FTP/Cloud/Streaming/证书，保留 Shooting/Setup/Playback/`CAMSET`（`M1..M4`），触发强制自动重启（`0x65d3`）并将 `[Airplane Mode]` 重置为 `Off`（`P279_GD_ERR_RESET_NETWORK_AUTOREBOOT_OR_3WAY_BOUNDARY_VIOLATION`）；<br>② 强制重启后重新开启 `[Airplane Mode] = [On]`（`0x6df9`）且 `passive_tx_bytes_emitted == 0` 才授权零射频台架（`P279_GD_ERR_POST_REBOOT_AIRPLANE_ON_OR_ZERO_RF_VIOLATION`）；<br>③ 核验 `16/16 H0 == H3`（`P279_GD_ERR_H0_H3_IMMUTABILITY_DRIFT`）与异构双盘 `528 B FX3RCPT1` Tier-0 冷备份回执（`P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID`）。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 SHA-256 指纹

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `414d3b158c89cf87d7147ab7274b01e14b21aa1bd839fa69693bb4e56e31dcc3` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `6e53db0b12b79866fb3b4c4d36f17a418463a5cc8a81454de2d08cd979136a18` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `fda065f7d56bf9c10c904e6ca711ac3d540eb416c7ad29173ed450d49b97f4bd` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0dc70e3196fbd687ba6227bb7f5b19e10fe6f2eda003cb1058212b276235a529` |

### 3.2 严格归属的 6 个交付文件

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py)（新增 Phase 279 第 8 级物理台架准备度预检器主模块）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（无阴影导出 Phase 279 全部 `P279_*` 公共常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-usb-mode-hdmi-info-protect-and-network-reset` CLI 子命令）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 47` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py)（新增 **70** 项三模式单测）
6. [`reports/2026-11-17-phase279-preflight-usb-mode-hdmi-info-protect-network-reset/README.md`](./README.md)（本实测报告）

### 3.3 实测门禁与洁净回执

- **Phase 279 三模式单元测试（70 项）**：
  - 默认 `LOCAL_DONOR_O_RDONLY`：**70/70 OK**（`2.591s`）
  - `FX3_CLEAN_ROOM_TEST=1`：**70/70 OK**（`2.517s`）
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**70/70 OK**（`2.614s`）
- **全包回归发现测试（`outputs/fx6-on-fx3-closure/tests`）**：
  - `/usr/bin/python3 -B` 本地供体全量发现：**1,623/1,623 OK**（`261.002s`）
  - `FX3_FX6_FORCE_CLEAN_ROOM=1 python3 -B` 洁净室全量发现：**1,623/1,623 OK**（`165.475s`，`skipped=51`）
- **Milestone 264 门禁（`make verify-milestone-264`）**：`LOCAL_DONOR_O_RDONLY`（`milestone264_sha256=2dfcb7ee3befe6f9...`）与 `CLEAN_ROOM_SYNTHETIC`（`milestone264_sha256=c19365de83679c8d...`）均 **`status=OK`（6/6 支柱全绿）**。
- **全库洁净校验（`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only`）**：零 `.pyc`、零未跟踪二进制产物，严格仅修改授权的 6 个文件。

### 3.4 可复现命令

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm python3 -B -m fx6_closure preflight-usb-mode-hdmi-info-protect-and-network-reset --simulate-bench-dry-run --json
```
