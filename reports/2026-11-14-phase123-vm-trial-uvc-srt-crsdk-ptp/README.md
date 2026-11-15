# Phase 123 — Live FX6-on-FX3 交互控制台：USB-C UVC 1.5 / UAC 2.0 洁净推流、有线 P12 SRT/RTMPS（AES-128/256, ARQ）与 CRSDK PTP 遥控及销毁指令防火墙 HUD

> **Phase 123 — Live FX6-on-FX3 Interactive Console: USB-C UVC 1.5 / UAC 2.0 Clean Streaming with USB 2.0 480 Mbps Auto-Stepdown, Wired CDC-NCM P12-Safe SRT / RTMPS TLS 1.3 Live Streaming (AES-128/256, ARQ), & Sony CRSDK PTP / PTP-IP (`0x054C`) Remote Control + Destructive Flash-Opcode (`0x9280..0x92FF`) Firewall HUD (`'UVCS'` `mb[60..63]`)**

- **日期 / Date**: 2026-11-14
- **任务分支 / Branch**: `codex/h128-phase123-vm-trial-uvc-srt-crsdk-ptp-live`
- **隔离验证端口 / Isolated Port**: `http://127.0.0.1:18783/`（`--workdir /private/tmp/fx6_p123_trial_18783 --no-browser`，实测结束后已通过 `POST /api/stop` 停止该隔离 QEMU 会话、终止对应子进程并彻底删除 `/private/tmp/fx6_p123_trial_18783`；实机端口 `8768` 全程零接触、零干扰）

---

## 1. 交付概览 / Executive Summary

本阶段在不触动实时服务端口 `8768` 与既有 `P4/P10/P11/P12/G31` 硬件契约的前提下，完成了面向实时 USB-C 采集流、加密有线直播推流与 Sony CRSDK 远程控制/固件安全防护的全链路闭环与原生 GPE0 HUD 渲染：

1. **USB-C UVC 1.5 / UAC 2.0 洁净输出与 USB 2.0 `480 Mbps` 自动降档 / USB-C UVC 1.5 & UAC 2.0 Clean Feed**
   - 支持 `OFF`、`UVC_4K30P_MJPEG_5G`（`3840x2160@30p MJPEG, 250 Mbps`）、`UVC_1080P60P_YUY2_5G`（`1920x1080@60p YUY2, 400 Mbps`）与 `UVC_720P30P_MJPEG_USB2_FALLBACK`（`1280x720@30p MJPEG, 35 Mbps`），并集成 `UAC 2.0 48kHz 16-bit 2ch PCM` 音频流控制。
   - **非 SuperSpeed USB 2.0 自动降档**：当线缆速率为 `USB2_480M` 且请求 `4K30p` 或 `1080p60` 时，宿主机与客体 `fx6_live_guest.c` 均自动确定性降档至 `UVC_720P30P_MJPEG_USB2_FALLBACK`（`uvc_usb2_stepdown_active = True`），切回 `USB3_5G` 时自动恢复。
   - **洁净无 OSD 烧录硬隔离**：客体硬置位 `mb[60] bit7 (uvc_clean_feed_no_osd = 1)`，`uvc_osd_burnin_px == 0`；一切试图将机内 OSD 烘培入 UVC 输出的请求（`uvc_bake_osd=True` / `uvc_clean_feed_no_osd=False`）均按 Fail-Closed 返回 HTTP `400`（`uvc_osd_burnin_blocked`）。

2. **有线 `CDC-NCM` `SRT` & `RTMPS TLS 1.3` 实时推流（客体硬强制 `P12` Wi-Fi-OFF）/ Wired P12-Safe SRT & RTMPS**
   - 支持 `SRT_CALLER` / `SRT_LISTENER`（密钥长度 `NONE` / `AES-128` 16B / `AES-256` 32B，ARQ 缓冲延迟严格校验 `[20..1000] ms`）及 `RTMPS_TLS13`（码率 `[1..50] Mbps`，Fail-Closed 拒绝明文 RTMP `rtmps_tls13_required`）。
   - **客体与主机双重 `P12` 射频关闭强制**：客体 `fx6_live_guest.c` 硬置位 `mb[61] bit21 (p12_wlan_off = 1)` 与 `bit22 (cdc_ncm_wired_ok = 1)`，锁定 `wf12_00342260_hits == 0`；任何 `use_wifi` / `enable_wlan` / `enable_bt` / `wlan0` 请求均被 Fail-Closed 拦截（HTTP `400` `p12_wlan_off_enforced`）。

3. **Sony `CRSDK` `PTP / PTP-IP` (`0x054C`) 遥控与破坏性 Flash-Opcode 防火墙 (`0x9280..0x92FF`) / CRSDK Remote & Flash Firewall**
   - 支持 `OFF / USB_PTP / WIRED_PTPIP`（VID `0x054C`、PTP-IP TCP `15740`），开放安全 `0xD2xx` 控制白名单：`0xD20D`（快门）、`0xD210`（`Cine EI / Base ISO 800/12800`）、`0xD21C`（白平衡）、`0xD220`（Look/LUT）、`0xD224`（`P4 ND-Clear` 钳位）、`0xD2C1`（Touch AF）、`0xD2C4`（REC 触发）。请求非 Clear ND（如 `1/16`）时强制钳回 `Clear [FX3 P4 Locked]` 并递增 `crsdk_nd_clamp_count`。
   - **破坏性 Flash-Opcode 硬件防火墙**：客体硬置位 `mb[62] bit2 (ptp_flash_opcodes_blocked = 1)`、`bit3 (emmc_mutation_zero = 1)`、`bit4 (p12_wlan_off = 1)`；所有 `0x9280..0x92FF`、`0x9201..0x920F` 操作码及 `firmware_flash` / `emmc_write` / `nvram_tamper` 语义请求均被 Fail-Closed 拦截（HTTP `400` `ptp_flash_opcode_blocked`），严格保证 `emmc_mutation_bytes == 0`、`persistent_emmc_writes_authorized == False`。

4. **`NonRealTimeMeta M01.XML` 边车、`CAMSET` 往返与四语 Web 控制台 / XML, CAMSET & 4-Language UI**
   - `/api/xml_sidecar` 注入 `<Group name="UvcSrtRtmpsAndCrsdkPtpFirewall">`（含 UVC 实际输出、USB2 降档、SRT/RTMPS、P12 状态、CRSDK VID 与防火墙拦截计数）。
   - `/api/camset_export` 与 `/api/camset_import` 完整支持 Phase 123 往返并拒绝 `emmc_mutation_bytes > 0`、`uvc_osd_burnin_px > 0` 或 `p12_wlan_off == False` 篡改预设。
   - Web 控制台新增支持 **EN / 简体中文 / 繁體中文 / 日本語** 的 `#phase123-uvc-srt-crsdk-ptp-card` 交互卡片。

5. **客体 `GPE0` (`0x41e001000`) `mb[60..63]` `'UVCS'` 零堆原生 HUD / Guest GPE0 Overlay**
   - 在 [fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) 中扩展 `mb[60..63]`（物理偏移 `240..255`，魔数 `0x55564353` `'UVCS'`），新增零堆分配、零 `printf` 渲染函数 `fx6_render_phase123_uvc_srt_crsdk_ptp_overlay()`，在 `row1_y = 288`（`h=28`，3 枚并行状态徽章：`UVC/UAC`、`CDC-NCM SRT/RTMPS P12=1`、`CRSDK PTP 0x054C`）及 `row2_y = 320`（`h=24` 全宽防火墙条：`[FIREWALL: PTP_FLASH 0x9280.. BLOCKED=1 | eMMC=0B | P12=1 | UVC_CLEAN=1]`）实时绘制，并随 `FX6_LIVE_FRAME ... UVCS=0x%08x:0x%08x:0x%08x` 串口遥测回传。

---

## 2. 邮箱协议寄存器契约 / Mailbox Register Contract (`mb[60..63]` `'UVCS'`)

| Word | 物理地址偏移 / Physical Offset | 关键字段位域布局 / Bit Layout | 默认引导值 / Boot Default |
|---|---|---|---|
| `mb[60]` | `0x41e000e00 + 0xF0` (`240`) | `[1:0] uvc_req` · `[3:2] uvc_eff` · `[4] usb2_non_ss` · `[5] stepdown` · `[6] uac_en` · `[7] uvc_clean(1)` · `[13:8] fps` · `[23:14] mbps` · `[27:24] uac_ch` · `[28] osd_blk` · `[31] valid` | `0x820000C0` |
| `mb[61]` | `0x41e000e00 + 0xF4` (`244`) | `[1:0] srt_mode` · `[3:2] pbkeylen` · `[13:4] latency_ms` · `[14] rtmps` · `[20:15] bitrate_mbps` · `[21] p12_wlan_off(1)` · `[22] cdc_ncm(1)` · `[29:23] p12_blk_cnt` · `[30] arq_en` · `[31] valid` | `0x80660788` |
| `mb[62]` | `0x41e000e00 + 0xF8` (`248`) | `[1:0] ptp_mode` · `[2] flash_blk(1)` · `[3] emmc_zero(1)` · `[4] p12_ptp(1)` · `[5] p4_nd_clr` · `[13:6] d2xx_low` · `[20:14] flash_blk_cnt` · `[27:21] safe_cnt` · `[30:28] action_kind` · `[31] valid` | `0x8000043C` |
| `mb[63]` | `0x41e000e00 + 0xFC` (`252`) | 协议魔数 / Magic `'UVCS'` | `0x55564353` |

---

## 3. 隔离端口实机 QEMU 渲染与自动化验证证据 / Verification Receipts

### 3.1 隔离端口 `--port 18783` 实机 QEMU `GPE0` 像素差异实测 / Live QEMU GPE0 Pixel Delta Proof

在完全隔离工作目录 `/private/tmp/fx6_p123_trial_18783`（`--port 18783 --workdir /private/tmp/fx6_p123_trial_18783 --no-browser`）启动完整 FX3+FX6 QEMU 虚拟机（`boot_sec = 47.4s` 就绪）：

| 验证阶段 / Scenario | 关键状态与遥测结果 / Telemetry | `ack_seq` | `GPE0` 真实像素变化 / Pixel Delta | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Boot** | `gpe0_nonzero_px=404,631`, `crashed=false` | `1` | 基线 (`96f34cf7c6a3063d`) | `0` (`false`) |
| **Step 1**: `UVC_4K30P_MJPEG_5G` (`USB3_5G`) + `SRT_CALLER` (`AES-256`, `120ms`) + `WIRED_PTPIP` (`0xD210` EI `12800`) | `guest_synced=true`, `ack_seq == cmd_seq == 2`, `p12_wlan_off=1`, `wf12=0` | `1 -> 2` | **`55,957` pixels** (`167,082` bytes, `8f6c1b263bffbdc7`) | `0` (`false`) |
| **Step 2**: `USB2_480M` 自动降档 + `RTMPS_TLS13@18M` + `0xD224` P4 ND 钳位 + Fail-Closed 拦截 `0x9280` / `use_wifi` / `uvc_bake_osd` | `effective_uvc_mode=UVC_720P30P_MJPEG_USB2_FALLBACK`, `blocked_flash_opcode_count=1`, `p12_blocked_count=1`, `uvc_osd_blocked_count=1`, `emmc_mutation_bytes=0`, `wf12_00342260_hits=0` | `2 -> 6` | **`48,217` pixels** (`143,628` bytes, `70e289a2106398de`) | `0` (`false`) |
| **Step 3**: 切换 `Page 6` Viewfinder HUD | `crashed=false` | `6 -> 7` | **`342,009` pixels** (`1,009,344` bytes, `c95c3e647ea65c5e`) | `0` (`false`) |
| **Step 4**: `/api/xml_sidecar` & `/api/camset_export` -> `/api/camset_import` 往返 | XML `10,020` bytes 含 `UvcSrtRtmpsAndCrsdkPtpFirewall`; `CAMSET` `preset_sha256=0af6cd772777c019`, `guest_synced=true` | 往返同步 | 零泄漏 / 零篡改 (`emmc=0B`) | `0` (`false`) |

实测结束后已通过 `POST /api/stop` 停止该隔离会话并终止对应子进程，同时彻底删除 `/private/tmp/fx6_p123_trial_18783`，全程未触碰 `8768` 端口，未使用 `pkill`/`killall`。

### 3.2 离线双模单元测试与全仓洁净门禁 / Dual-Mode Unit & Clean-Only Gates

- **本地供体模式 / Local Donor Mode** (`PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests`): **367 / 367 PASSED**（含新增 32 项 `test_phase123_uvc_srt_crsdk_ptp.py`）
- **洁净室模式 / Clean-Room Mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests`): **367 / 367 PASSED**（`skipped=2` 仅限于既有供体语言包校验项，Phase 123 全部 32/32 通过）
- **全仓干净测试门禁 / Lab Clean-Only Gate** (`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`): 全部通过，仓库内零 `.o`、`.elf`、`.cpio`、`.pyc` 残留。

---

## 4. 变更文件清单 / Owned Files

1. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c)
2. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py)
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md)
4. [outputs/fx3-vm-trial/tests/test_phase123_uvc_srt_crsdk_ptp.py](../../outputs/fx3-vm-trial/tests/test_phase123_uvc_srt_crsdk_ptp.py)
5. [reports/2026-11-14-phase123-vm-trial-uvc-srt-crsdk-ptp/README.md](README.md)
