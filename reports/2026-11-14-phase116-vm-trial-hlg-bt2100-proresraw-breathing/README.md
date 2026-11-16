# Phase 116 — Live FX6-on-FX3 交互控制台：HLG1/HLG2/HLG3 BT.2100 管线、Display Assist 洁净隔离、CTA-861.3 (0x87) InfoFrame 与外部 ProRes RAW / BRAW + 呼吸效应补偿 HUD

> **Phase 116 — Live FX6-on-FX3 Interactive Console: HLG1/HLG2/HLG3 BT.2100/ARIB STD-B67 Pipeline, Gamma Display Assist VF/LCD vs Clean HDMI/SDI Isolation, CTA-861.3 (0x87) HDR InfoFrame, & External ProRes RAW / BRAW 16-Bit->12-Bit Log + Focus Breathing Compensation HUD (`'HLGA'` `mb[56..59]`)**

- **日期 / Date**: 2026-11-14
- **分支 / Branch**: `codex/h119-phase116-vm-trial-hlg-bt2100-assist-proresraw`
- **隔离验证端口 / Isolated Port**: `http://127.0.0.1:18782/`（`--workdir /private/tmp/fx6_p116_trial_18782 --no-browser`，实测结束后已精准终止自启动子进程 `PID 40509` 并彻底删除临时工作目录；生产端口 `8768` 全程零接触、零干扰）

---

## 1. 交付概览 / Executive Summary

本阶段在不触动实时服务端口 `8768` 与既有 `P4/P10/P11/P12/G31` 硬件契约的前提下，完成了面向专业 HDR 制作与外部 RAW 监录链路的控制与原生 GPE0 HUD 渲染闭环：

1. **HLG1 / HLG2 / HLG3 ITU-R BT.2100 (ARIB STD-B67) 管线 & CTA-861.3 (`0x87`) HDR 静态元数据 InfoFrame**
   - 支持 `OFF`、`HLG1`（`87%` / `~925 nit` 低噪点）、`HLG2`（`95%` / `~1000 nit` 均衡）、`HLG3`（`100%` / `~1090 nit` 宽动态范围）及 `FX6_HLG_LIVE` / `FX6_HLG_NATURAL`，支持 `BT.2020 / BT.709 / S-Gamut3.Cine` 色域、Knee（`Auto / 87% / 95% / 100%`）与 Detail（`-7..+7`）。
   - 实时合成符合 HDMI 2.0b / CTA-861.3 规范的 **30 字节 `0x87` HDR Static Metadata InfoFrame**（`EOTF = 3` `HLG_ITU_R_BT2100`，`BT.2020` / `BT.709` 原色与 D65 白点坐标，严格满足 8-bit 模 256 校验和 `(sum(packet) & 0xFF) == 0`，如 HLG3 BT.2020 1090nit -> `CS=0xDA`）。
   - Fail-Closed 拦截将 `BT.2020` 广色域信号封装进 `BT.709` 容器标签的错配请求（HTTP `400` `bt2020_in_bt709_container_blocked`）。

2. **Gamma Display Assist VF/LCD 隔离 vs 洁净 HDMI/SDI 输出护盾 / Display Assist Clean-Feed Isolation**
   - 支持 `OFF / AUTO / S-Log3->709(800%) / HLG->709(BT.2020) / HLG->709(709)`；当选择 `AUTO` 时自动追随当前 `HLG` 色域或 `S-Log3` Look。
   - **客体与宿主机双重硬隔离**：`fx6_live_guest.c` 在每次接收 `mb[57]` 时硬性置位 `bit7 (clean_hdmi_sdi_unassisted=1)` 与 `bit8 (xavc_internal_unassisted=1)`，确保机内 Display Assist LUT **绝对不会**烘焙进入外部 HDMI/SDI 洁净输出或内部 XAVC 录制文件（`external_output_assist_leak_px == 0`）。
   - 任何试图通过 API 强制向 HDMI/SDI/XAVC 注入 Display Assist 的请求均被 Fail-Closed 拦截（HTTP `400` `display_assist_clean_feed_leak_blocked`）并递升审计计数 `assist_leak_blocked_count`。

3. **外部 HDMI 16-Bit Linear -> 12-Bit Log RAW（Atomos ProRes RAW & Blackmagic BRAW）与呼吸效应补偿互锁**
   - 支持 `Atomos_ProRes_RAW_16_12L` 与 `Blackmagic_BRAW_16_12L`，实时携带当前 `Base ISO 800/12800`、`Kelvin` 色温、`FPS` 与镜头光圈/卡口元数据，并与 Phase 64 `wired_io_mode == "hdmi_raw16"` 实现双向实时同步。
   - 支持 **Focus Breathing Compensation 呼吸效应补偿**（`OFF / AUTO`）：在 Sony E-Mount 12-Pin 电子镜头下按焦段查询动态裁切系数（`<=20mm: 1.02x`、`21..35mm: 1.04x`、`36..55mm: 1.06x`、`56..85mm: 1.07x`、`>85mm: 1.08x`）；当热插拔为无芯片 PL 卡口（`Manual_PL_Adapter_Unchipped`）或启用外部 HDMI RAW 全传感器读出时，自动降级为 `1.00x` 无裁切旁路（并拦截强制绕过请求，HTTP `400` `focus_breathing_interlock_blocked`）。

4. **`NonRealTimeMeta M01.XML` 边车、`CAMSET` 往返与四语控制台 / XML, CAMSET & 4-Language Console**
   - `GET /api/xml_sidecar` 自动在启用 HLG / BT.2020 时将 `CaptureGammaEquation` 切换为 `rec2100-hlg`、将 `CaptureColorPrimaries` 切换为 `rec2020`，并在 `<AcquisitionRecord>` 中注入 `<Group name="HlgBt2100AssistRawBreathing">`。
   - `/api/camset_export` 与 `/api/camset_import` 完整支持 Phase 116 状态的确定性导出/严格校验导入；Web 控制台新增支持 **EN / 简体中文 / 繁體中文 / 日本語** 的 `#phase116-hlg-raw-breathing-card` 交互卡片。

5. **客体 `GPE0` (`0x41e001000`) `mb[56..59]` `'HLGA'` 零堆原生 HUD / Guest GPE0 Overlay**
   - 在 [fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) 中扩展 `mb[56..59]`（偏移 `0xE0..0xEC`，魔数 `0x484C4741` `'HLGA'`），新增零堆分配、零 `printf` 渲染函数 `fx6_render_phase116_hlg_raw_breathing_overlay()`，实时在 `GPE0` 显存绘制 HLG/峰值尼特/CTA `0x87` 徽章、Display Assist Clean-Out 隔离状态、ProRes RAW / BRAW 16->12L 徽标、呼吸效应补偿裁切比及动态 HDR 波形柱，并随 `FX6_LIVE_FRAME ... HLGA=...` 串口遥测回传。

---

## 2. 邮箱协议寄存器契约 / Mailbox Register Contract (`mb[56..59]` `'HLGA'`)

| Word | 物理地址偏移 / Physical Offset | 关键字段位域布局 / Bit Layout | 默认引导值 / Boot Default |
|---|---|---|---|
| `mb[56]` | `0x41e000e00 + 0xE0` | `[2:0] hlg_idx` · `[4:3] gamut_idx` · `[8:5] detail(+7)` · `[10:9] knee_idx` · `[12:11] cta_eotf` · `[13] cta_ok` · `[21:14] cta_cs` · `[29:22] peak_nits/10` · `[30] bt2020_blk` · `[31] valid` | `0x829A60E0` |
| `mb[57]` | `0x41e000e00 + 0xE4` | `[2:0] assist_req` · `[5:3] assist_res` · `[6] evf_assist_on` · `[7] clean_hdmi_sdi(1)` · `[8] xavc_unassisted(1)` · `[15:9] leak_blk_cnt` · `[23:16] vf_nit/10` · `[30:24] peak_ire` · `[31] valid` | `0xA90A0180` |
| `mb[58]` | `0x41e000e00 + 0xE8` | `[1:0] ext_raw_idx` · `[2] b12800` · `[10:3] kelvin/100` · `[11] lens_meta` · `[12] raw_rec_tc` · `[13] fbc_req` · `[14] fbc_eff` · `[15] byp_pl` · `[16] byp_raw` · `[24:17] crop_x100` · `[30:25] fps_idx` · `[31] valid` | `0x80C809C0` |
| `mb[59]` | `0x41e000e00 + 0xEC` | 协议魔数 / Magic `'HLGA'` | `0x484C4741` |

---

## 3. 隔离端口实机 QEMU 渲染与自动化验证证据 / Verification Receipts

### 3.1 隔离端口 `--port 18782` 实机 QEMU `GPE0` 像素差异实测 / Live QEMU GPE0 Pixel Delta Proof

在完全隔离工作目录 `/private/tmp/fx6_p116_trial_18782`（`--port 18782 --workdir /private/tmp/fx6_p116_trial_18782 --no-browser`）启动完整 FX3+FX6 QEMU 虚拟机（`boot_sec = 37.73s` 就绪）：

| 验证阶段 / Scenario | 关键状态与遥测结果 / Telemetry | `ack_seq` | `GPE0` 真实像素变化 / Pixel Delta | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Boot** | `gpe0_nonzero_px=404,631`, `text_ok=42`, `crashed=false` | `1` | 基线 (`2882de63bd7b22f5`) | `0` (`false`) |
| **Transition A**: `HLG3` + `BT.2020` (1090nit) + `Display Assist AUTO` | `cta_eotf=3`, `cta_cs=0xDA` (`sum%256=0`), `clean_hdmi_sdi_unassisted=true`, `leak_px=0` | `1 -> 2` | **`36,768` pixels** (`109,545` bytes, `d65d3465ab6606c8`) | `0` (`false`) |
| **Transition B**: `Atomos_ProRes_RAW_16_12L` + `FBC AUTO` (`1.00x` bypass) | `raw=16->12L`, `breathing_bypassed_by_raw=true`, `crop=1.00x` | `2 -> 3` | **`24,199` pixels** (`78,112` bytes, `9642b8d3820b3593`) | `0` (`false`) |
| **Transition C**: `Blackmagic_BRAW_16_12L` + `Base 12800` + `3200K` | `B12800,3200K` 跨模块同步生效 | `3 -> 6` | **`13,062` pixels** (`39,186` bytes, `1bf4b234739c174a`) | `0` (`false`) |
| **Transition D**: `E-Mount 12-Pin` `50mm` + `FBC AUTO` (`ext_raw_mode=OFF`) | `breathing_effective_active=true`, `crop=1.06x` | `6 -> 8` | **`24,145` pixels** (`77,960` bytes, `9a5431bb5405beeb`) | `0` (`false`) |
| **Transition E**: 热插拔 `Manual_PL_Adapter_Unchipped` | 自动归位 `crop=1.00x` (`PL_UNCHIPPED_0PIN_IDENTITY`) | `8 -> 9` | **`37,687` pixels** (`121,639` bytes, `c48f356da077c1e1`) | `0` (`false`) |
| **Transition F**: 切换 `Page 6` Viewfinder HUD | `text_ok=54`, 串口 `HLGA=0xdb76b8eb:0xe40a03d9:0x80d46904` (`seq=14`) | `1 -> 11` | **`381,966` pixels** (`1,385,311` bytes, `87ef8d57aec50b29`) | `0` (`false`) |
| **Fail-Closed & Sidecar**: Clean-Feed Leak / BT.2020-in-709 / PL-FBC / XML / CAMSET | 三类非法请求全返回 HTTP `400`，`leak=0px`；XML 含 `rec2100-hlg`/`rec2020`；`CAMSET` 往返 `ok=true` | `14` (`== cmd_seq`) | 零泄漏 / 零污染 | `0` (`false`) |

实测结束后已精准终止自启动子进程（`PID 40509`）并彻底删除 `/private/tmp/fx6_p116_trial_18782`，全程未触碰 `8768` 端口，未使用 `pkill`/`killall`。

### 3.2 离线双模单元测试与全仓洁净门禁 / Dual-Mode Unit & Clean-Only Gates

- **本地供体模式 / Local Donor Mode** (`PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests`): **335 / 335 PASSED**（含新增 32 项 `test_phase116_hlg_bt2100_proresraw_breathing.py`）
- **洁净室模式 / Clean-Room Mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests`): **335 / 335 PASSED**（`skipped=2` 仅限于既有供体语言包校验项，Phase 116 全部 32/32 通过）
- **全仓干净测试门禁 / Lab Clean-Only Gate** (`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`): 全部通过，仓库内零 `.o`、`.elf`、`.cpio`、`.pyc` 残留。

---

## 4. 变更文件清单 / Owned Files

1. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c)
2. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py)
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md)
4. [outputs/fx3-vm-trial/tests/test_phase116_hlg_bt2100_proresraw_breathing.py](../../outputs/fx3-vm-trial/tests/test_phase116_hlg_bt2100_proresraw_breathing.py)
5. [reports/2026-11-14-phase116-vm-trial-hlg-bt2100-proresraw-breathing/README.md](README.md)
