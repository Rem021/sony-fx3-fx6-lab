# Phase 275 实机拍摄前第 7 级物理台架准备度预检器报告（`preflight-file-settings-gamma-assist-focus-mag-and-videolight` / Waves 44–46）

## 1. 核心结论（Conclusion-First）

1. **Waves 44–46 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`）物理台架检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 中新增第 7 级宿主侧只读物理台架预检器 [`realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py)（Schema `realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier_v1`，版本 `275.0.0`，CLI 子命令 `preflight-file-settings-gamma-assist-focus-mag-and-videolight`），将操作员实拍前预检链路推进至 `preflight-card-insert`（Ph186）→ `preflight-bench-cable-fan-slot1`（Ph204）→ `preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）→ `preflight-pixelmap-ntscpal-powersave-and-autotemp`（Ph227）→ `preflight-imagedb-touch-shoeaudio-and-lockop`（Ph248）→ `preflight-diffset-customkey-autoslow-and-apsc`（Ph261）→ **`preflight-file-settings-gamma-assist-focus-mag-and-videolight`（Ph275）**，导出符号全部采用无阴影 `P275_*` 前缀。
2. **三模式 68 项单元测试、全包 1,553 项测试与 Milestone 264 门禁 100% 通过**：新增 [`test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py) 共 **68** 项确定性单测，在 `LOCAL_DONOR_O_RDONLY`（`2.892s`）、`FX3_CLEAN_ROOM_TEST=1`（`2.853s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`2.910s`）三种模式下 **68/68 全绿**，有界 `O_RDONLY` 供体校验耗时仅 **`0.000687s`（`< 0.15s` 预算）**；全包 `outputs/fx6-on-fx3-closure/tests` **1,553/1,553** 项测试全部通过；`make verify-milestone-264` 双模式 `status=OK`（`606e7686c8587295...` / `95dfd77a4c590bb6...`）；`scripts/run_all_lab_tests.py --clean-only` 洁净无残留。
3. **离线默认阻断与硬件安全红线 100% 锁死**：离线无回执时严格返回 `overall_status = READY_OFFLINE_AWAITING_BENCH_RECEIPTS` 与 `go_no_go = BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`（CLI 退出码 `2`），`--simulate-bench-dry-run` 返回 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`（CLI 退出码 `0`，`16/16 H0 == H3`），双物理设备（`st_dev_a != st_dev_b`）`528 B FX3RCPT1` 验证通过返回 `GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_READONLY_PREFLIGHT_VERIFIED`，任意检查失败返回 `BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_CHECK_FAILURE`（CLI 退出码 `2`）；无条件锁死 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`sd_physical_media_written = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0` 与 `passive_tx_bytes_emitted = 0`。

---

## 2. 四大物理台架与官方帮助指南（`ilc/2210`）检查组（`Check Group A .. D`）

| 检查组 ID | 预检域（Waves 44–46） | 关键校验规则、边界与报错码 |
| :--- | :--- | :--- |
| **`GROUP_A_CINEMA_SLATE_FILE_SETTINGS_AUTO_REVIEW_AND_TCUB_PERSISTENCE`** | 电影 `[File Settings]`（`Cam ID + Reel#` 与 `37` 字符标题）、静态 `[File/Folder Settings]`（`DSC` 前缀与 Slot-1 防火墙）、`[Auto Review]=Off` 及 `6` 项 `[TC/UB]` 重置保留（Wave 44） | ① 校验电影 `[File Settings]`：`File Number`（`Series`/`Reset`）、`File Name Format`（`Cam ID + Reel#`：`A..Z` / `001..999` / `C|L|R`）、`Title Name Settings`（`1..37` 字符 ASCII，默认 `"C"`）与固定 `PRIVATE/M4ROOT/CLIP` 路径（禁止自定义目录，`P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR`）；<br>② 校验静态 `[File/Folder Settings]` `3` 字符前缀（默认 `DSC`，严格拦截前导 `_` 如 `_SC`），并在 Slot 1 持有 Tier-0 只读恢复金库时硬阻断 `Forced File Number Reset` 与 `Create New Folder`（Slot 2 仍放行，`P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION`）；<br>③ 强制 `[Auto Review] = [Off]`（仅限静态）、`6` 项 `[TC/UB]` 菜单与 `24.00p`/PAL 强迫 `NDF` 规则，且以上项目全部在 `[Camera Settings Reset]` 下保持、仅 `[Initialize]` 恢复默认（`P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE`）。 |
| **`GROUP_B_GAMMA_DISPLAY_ASSIST_VS_DISPLAY_LUT_CLEAN_HDMI`** | `[Gamma Display Assist]` Log 锁定与机内 LCD 隔离 vs `[Display LUT]` / `[Select LUT]` `User1..16`（Wave 44） | ① 只要 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）`!= Off`，`[Gamma Display Assist]` 强制锁定 `Off`（`P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED`）；在 `Log = Off` 时支持 `Auto` / `S-Log3->709(800%)` / `HLG(BT.2020)` / `HLG(709)` 四模式；<br>② 强制 `[Gamma Display Assist]` 仅限机身内屏 LCD，外部 HDMI 必须保持零像素叠加洁净输出（`external_hdmi_gamma_assist_pixels == 0`，`P275_GB_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_BOUNDARY`）；<br>③ 校验 `[Display LUT]`（默认 `On`）与 `[Select LUT]`（`S-Log3` / `s709` / `709(800%)` / `User1..User16` 共 19 项，拒绝 `User17` 等越界槽位）及 `[Setup]` 复位保留（`P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID`）。 |
| **`GROUP_C_FOCUS_MAG_4X_PEAKING_ZERORF_TIME_VIDEOLIGHT_HDMI_RES`** | `4.0x` 对焦放大与 `[Auto Magnifier in MF]`、`[Peaking]` / `[AF Illuminator]`、零射频 `[Area/Date/Time Setting]`、MI 热靴 `5V<=900mA` 视频灯与 `HDMI Resolution` Log `1080p` 降格（Wave 45） | ① 校验 `[Focus Magnifier]` `1.0x`/`4.0x`、默认 `No Limit`、精确标签 `"Auto Magnifier in MF"`（拒绝旧名称 `"MF Assist"`）与 `Custom Button 5`，并在退出放大时保持洁净 HDMI 零叠加及在 `HDMI RAW Output` 下锁定放大器（`P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT`）；<br>② 校验 `[Peaking Display]`（默认 `Off`、`High/Mid/Low`、`Red/Yellow/Blue/White`）与 `[AF Illuminator]`（默认 `Auto`，仅限静态 `AF-S`/`DMF`/`MF`，Movie/`S&Q`/`AF-C` 锁定不触发，`P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT`）；<br>③ 校验 `[Area/Date/Time Setting]` 四子项手调气隙配置，强制 `Airplane Mode = On`、`Bluetooth Function = Off`、关闭 `Creators' App` `[Location Information Linkage]`（`passive_tx_bytes_emitted == 0`，`P275_GC_ERR_AREA_DATE_TIME_OR_ZERO_RF_CREATORS_APP_SYNC`）；<br>④ 校验 `[Video Light Mode]` 4 模式（默认 `Power Link`）与 MI 热靴 `5V <= 900 mA` PMIC 过流预算护栏（`P275_GC_ERR_VIDEO_LIGHT_MODE_OR_MI_SHOE_5V_900MA_OVERCURRENT`），以及 `[HDMI Resolution]` 在 `Log` 机内录制或 `HDMI RAW` 下禁止 `2160P`（`Auto`/`1080P`/`1080I` 通过，`Off(HDMI Only)` 非 RAW 放行 `2160P`，`P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT`）。 |
| **`GROUP_D_POWER_SAVE_MONITOR_SPLIT_BKLANG_VOLUME_DELETE_AND_TIER0`** | `[Power Setting Option]` 官方/固件现实分裂、`BK_LANG` `0x02cf019c`（`34` vs `29`）、`[Volume]`/`[4ch Audio Monitoring]`、`[Delete confirm.]` Slot-1 金库防护与 Tier-0 双盘回执（Wave 46） | ① 校验 `ILME-FX3 Ver. 7.02`（`ilc/2210`）UI 仅暴露 2 项 `[Power Setting Option]`（`Power Save Start Time` / `Auto Power OFF Temp.`），同时审计 `appFw.so` 内编译但未在 FX3 UI 暴露的 4 模式 `[Power Save by Monitor]`（`Both Linked` `0x6db5` / `Open: Return` `0x6db6` / `Close: Power Save` `0x60a8` / `Does Not Link` `0x6b2e`），拒绝无头台架闭合休眠并校验 9 项休眠豁免条件与气隙电池 `Off`/`30 Min` 规则（`P275_GD_ERR_POWER_SETTING_OPTION_REALITY_SPLIT_OR_9COND`）；<br>② 校验 `[Language]` 寄存器 `BK_LANG` `0x02cf019c`（`FX3` `34` 种 vs `FX6` `29` 种语言；`en=0x00`, `japanese=0x01`, `tchinese=0x18`, `schinese=0x19`）跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 保留（`P275_GD_ERR_BKLANG_34_VS_29_OR_SETUP_RESET_PERSISTENCE`）；<br>③ 校验 `[Volume Settings]`（`0..15`，默认 `7`，接 `XLR-H1` 时 `> 7` 告警、`> 10` 阻断防啸叫）与 `[4ch Audio Monitoring]` 精确 5 路由（`CH1/CH2`, `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2`）及 `3.5mm` `2ch` 上限（`P275_GD_ERR_VOLUME_OR_4CH_MONITORING_5ROUTE_OR_FEEDBACK`）；<br>④ 强制 `[Delete confirm.] = ["Cancel" first]` 并硬阻断 Slot-1 金库卡删除/格式化（`P275_GD_ERR_DELETE_CONFIRM_OR_SLOT1_VAULT_DELETE_FORMAT_BLOCKED`），核验 `16/16 H0 == H3`（`P275_GD_ERR_H0_H3_IMMUTABILITY_DRIFT`）与异构双盘 `528 B FX3RCPT1` 回执（`P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID`）。 |

---

## 3. 确定性输出摘要与实测验证记录

### 3.1 四态确定性报告 SHA-256 指纹

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `d99e7b31ec7264e4bcdaf7e500a06f0e868852bb6c877d6f7f5c3c65f285ad5f` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `b0f804f6a81ff12b7428c8c0462deb144ee988452d61947165caa4cbfd70aa9d` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1dbde879f8ff1b81570f5729eacf8d4df97d8d83279cfaf31ba36b67bc3d7e52` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `cb6e4839f3c4194629c84c693037e207ae100d10efae55988b1364508f8b89c0` |

### 3.2 严格归属的 6 个交付文件

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py)（新增 Phase 275 第 7 级物理台架准备度预检器主模块）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（无阴影导出 Phase 275 全部 `P275_*` 公共常量、数据类与校验函数）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `preflight-file-settings-gamma-assist-focus-mag-and-videolight` CLI 子命令）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（补充模块结构说明与 CLI `# 46` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py)（新增 **68** 项三模式单测）
6. [`reports/2026-11-17-phase275-preflight-file-settings-gamma-assist-focus-mag-videolight/README.md`](./README.md)（本实测报告）

### 3.3 实测门禁与洁净回执

- **Phase 275 三模式单元测试（68 项）**：
  - 默认 `LOCAL_DONOR_O_RDONLY`：**68/68 OK**（`2.892s`）
  - `FX3_CLEAN_ROOM_TEST=1`：**68/68 OK**（`2.853s`）
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：**68/68 OK**（`2.910s`）
- **全包回归发现测试（`outputs/fx6-on-fx3-closure/tests`）**：**1,553/1,553 OK**（`266.593s`）。
- **Milestone 264 门禁（`make verify-milestone-264`）**：`LOCAL_DONOR_O_RDONLY`（`milestone264_sha256=606e7686c8587295...`）与 `CLEAN_ROOM_SYNTHETIC`（`milestone264_sha256=95dfd77a4c590bb6...`）均 **`status=OK`（6/6 支柱全绿）**。
- **全库洁净校验（`PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only`）**：零 `.pyc`、零未跟踪二进制产物，严格仅修改授权的 6 个文件。

### 3.4 可复现命令

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm python3 -B -m fx6_closure preflight-file-settings-gamma-assist-focus-mag-and-videolight --simulate-bench-dry-run --json
```
