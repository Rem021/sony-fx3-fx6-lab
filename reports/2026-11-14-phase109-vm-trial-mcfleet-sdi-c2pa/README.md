# Phase 109 — Live FX6-on-FX3 交互控制台：Sony Monitor & Control 4 机位有线 Gang-REC 矩阵、HDMI→12G-SDI AVI InfoFrame / SMPTE RP 188 触发桥接、E-Mount/PL 阴影热插拔与 C2PA 2.1 洁净室溯源护盾

> **Phase 109 — Live FX6-on-FX3 Interactive Console: Sony Monitor & Control 4-Cam Wired Fleet Gang-REC Matrix, HDMI->12G-SDI AVI InfoFrame / RP 188 REC-Trigger Bridge, E-Mount/PL Shading Hot-Swap, & C2PA Clean-Room Provenance HUD**

- **日期 / Date**: 2026-11-14
- **分支 / Branch**: `codex/h110-phase109-vm-trial-mcfleet-sdi-c2pa`
- **隔离验证端口 / Isolated Port**: `http://127.0.0.1:18781/`（`--work-dir /private/tmp/fx6-phase109-18781`，实测结束后已精准终止自启动子进程 `PID 37116` 并彻底删除工作目录；生产端口 `8768` 全程零接触、零干扰）

---

## 1. 交付概览 / Executive Summary

本阶段在不触动实时服务端口 `8768` 与 `P4/P10/P11/P12/G31` 硬件契约的前提下，完成了面向多机位现场制作与外部 SDI/C2PA 溯源闭环的四大核心子系统：

1. **Sony Monitor & Control 4 机位有线千兆 USB-LAN 联机与 Gang-REC 矩阵 / 4-Cam Wired USB-LAN Fleet & Gang-REC Matrix**
   - 支持 `fleet_role` ∈ `{'Solo', 'A_Cam_Master', 'B_Cam_Follower', 'C_Cam_Follower', 'D_Cam_Follower'}`、`fleet_cams_online`（`1..4`）、`fleet_nic_driver` ∈ `{'CDC_NCM_RTL8153', 'CDC_NCM_AX88179'}` 及 `gang_rec_trigger`。
   - 开启 `gang_rec_trigger` 时自动将 Phase 64 `REC` Tally 与四机位 PTP-IP 联机状态（UDP/TCP `15740`，`ptp_max_clock_skew_us <= 18.0`）同步联动；严格强制 `P12` Wi-Fi/BT 射频关闭（`wf12_00342260_hits == 0`、`p12_rf_off_enforced == True`），fail-closed 拒绝一切无线/非零 `wf12_00342260_hits` 请求（HTTP `400` `p12_rf_off_violation`）。

2. **HDMI CEA-861 AVI InfoFrame + HDMI→12G-SDI Active Converter REC 触发桥接 / HDMI->12G-SDI AVI InfoFrame & RP 188 Bridge**
   - 根据当前摄影机 Look 与色彩设置（`S-Log3 / S-Gamut3.Cine`、`S-Cinetone`、`709`、`HDMI_RAW16`）实时合成 17 字节 CEA-861 AVI InfoFrame 载荷及精确校验和（`0x100 - sum == 0`），自动锁定正确的量化范围并拦截外部录机 `FULL_0_1023` 与 `LEGAL_64_940` 混用导致的暗部死黑挤压（`shadow_crush_prevented == True`）。
   - 支持 `sdi_bridge_converter` ∈ `{'BMD_Micro_Converter_12G', 'Teradek_Bolt_HDMI_SDI', 'Atomos_Connect_12G', 'Bypass_HDMI_Direct'}`，随 `REC` Tally / `gang_rec_trigger` 切换实时更新 `SMPTE RP 188`（`DID=0x60` / `SDID=0x60`、`rp188_rec_trigger_bit` `0`/`1`、`rp188_parity_ok == True`），并如实声明 FX3 机身无物理 12G-SDI BNC（`physical_12g_sdi_bnc_present == False`、`ghost_sdi_bnc_hw_faults == 0`）。

3. **E-Mount 12-Pin 电子触点 vs 无芯片 PL 卡口热插拔阴影仲裁器 / E-Mount 12-Pin vs Unchipped PL Shading Arbitrator**
   - 支持 `mount_type` ∈ `{'Sony_EMount_12Pin_GM', 'Manual_PL_Adapter_Unchipped'}` 与自定义镜头重量 `lens_kg`、`rod_support_15mm_lws`。
   - 切换至无芯片 PL 卡口时在 `<1` 帧内（`reset_latency_ms = 2.15 ms < frame_period_ms`、`reset_under_one_frame = True`、`stale_gm_frames_leaked = 0`）将径向暗角、色差与呼吸效应补偿强制归位为 `1.000x` 单位矩阵，彻底防止 GM 电子镜头阴影配置文件污染 PL 电影镜头画面。
   - 当 `lens_kg > 1.2` 且未启用 `rod_support_15mm_lws` 时触发 `G31` 15mm LWS 导管支撑安全告警（`g31_15mm_lws_warning == True`），开启 `rod_support_15mm_lws = True` 后自动解除。

4. **C2PA 2.1 / `cnflasha` 零接触洁净室研究溯源护盾 / C2PA 2.1 Zero-Touch Research Provenance Shield**
   - 永久锁定 `c2pa_vault_status == 'CNFLASHA_RDONLY_ZERO_TOUCH'`、`c2pa_provenance_mode == 'CLEAN_ROOM_RESEARCH_UNATTESTED'`、`private_key_reads == 0`、`cnflasha_writes == 0`、`rpmb_writes == 0`、`hardware_attestation_claimed == False`。
   - fail-closed 拦截任何私钥读取、导出、`cnflasha` 写入、真机硬件签章伪造或 `/dev/cnflasha` 路径注入尝试（HTTP `400` `c2pa_cnflasha_zero_touch_blocked`），并在 `GET /api/xml_sidecar`（`NonRealTimeMeta v2.20`）中嵌入诚实的 `<Group name="McFleetSdiAndC2paProvenance">` 溯源记录。

5. **客体 `GPE0` (`0x41e001000`) `mb[52..55]` `'MCFL'` 原生 HUD、`CAMSET` 往返与四语控制台**
   - 在 [fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) 中新增 `mb[52..55]`（Magic `0x4D43464C` `'MCFL'`）及零堆分配/零 `printf` 渲染函数 `fx6_render_phase109_mcfleet_sdi_c2pa_overlay()`，实时渲染 M&C A/B/C/D 联机状态灯、HDMI→SDI RP 188 & AVI 校验和徽章、E-12P / PL-0PIN 阴影归位与 G31 LWS 告警条，以及 C2PA 零接触护盾徽章。
   - 在 [run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py) 中完成 `GET/POST /api/mc_fleet_sdi_c2pa`、`/api/status`、`/api/xml_sidecar`、`CAMSET` 导出/导入往返，以及四语（`EN / 简体中文 / 繁體中文 / 日本語`）Web UI 面板 `#phase109-mcfleet-sdi-c2pa-card` 的完整集成。

---

## 2. 邮箱协议寄存器契约 (`mb[52..55]` `'MCFL'`)

| Word | 物理地址偏移 | 关键字段位域布局 / Bit Layout | 默认引导值 |
|---|---|---|---|
| `mb[52]` | `0x41e000e00 + 0xD0` | `[2:0] fleet_role` · `[5:3] cams_online(1..4)` · `[6] gang_rec` · `[7] sdi_act` · `[9:8] sdi_idx` · `[10] rp188_rec` · `[11] avi_ok` · `[12] quant_idx` · `[20:13] avi_cs` · `[26:21] ptp_skew/2` · `[27] p12_rf_off(1)` · `[28] hdmi_tc` · `[31] valid` | `0x98194888` |
| `mb[53]` | `0x41e000e00 + 0xD4` | `[0] mount_pl` · `[1] shading_ident` · `[9:2] corner_gain_x100` · `[15:10] lens_kg_x10` · `[16] g31_lws_warn` · `[17] rod_lws` · `[21:18] e_pins` · `[28:22] focal_div2` · `[31] valid` | `0x83301E10` |
| `mb[54]` | `0x41e000e00 + 0xD8` | `[1:0] vault_idx(0)` · `[2] clean_room(1)` · `[3] hw_attest(0)` · `[4] cnflasha_ro_zt(1)` · `[5] spoof_blk` · `[13:6] blk_cnt` · `[21:14] pkt_div10` · `[31] valid` | `0x80000014` |
| `mb[55]` | `0x41e000e00 + 0xDC` | 协议魔数 `'MCFL'` | `0x4D43464C` |

---

## 3. 隔离端口实机 QEMU 渲染与自动化验证证据 / Verification Receipts

### 3.1 隔离端口 `--port 18781` 实机 QEMU `GPE0` 像素差异实测

在完全隔离目录 `/private/tmp/fx6-phase109-18781`（`--port 18781 --work-dir /private/tmp/fx6-phase109-18781 --no-browser`）启动完整 FX3+FX6 QEMU 虚拟机：

| 验证阶段 / Scenario | 关键状态与遥测结果 | `ack_seq` | `GPE0` 真实像素变化 | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Boot** | `boot_ready_sec=81.5s`, `gpe0_nonzero_px=404,631`, `text_ok=42`, `crashed=false` | `1` | 基线 (`5cb352cffcde4b10`) | `0` (`false`) |
| **Scenario A**: `S-Log3` + `A_Cam_Master 4/4` + Gang-REC + `BMD_Micro_Converter_12G` | `avi_hex=82020DCA2028005D000000000000000000`, `avi_range=SLOG3_EXTENDED_64_1019`, `rp188_rec=1`, `wf12_hits=0` | `3` | **`51,214` pixels** (`161,298` bytes, `0c01fe2313c3a6d7`) | `0` (`false`) |
| **Scenario B**: `Manual_PL_Adapter_Unchipped` (`1.8kg`, `rod_lws=false` -> `true`) + `wf12=1` P12 拦截 | `vignetting_comp_gain=1.0`, `g31_warn_before=true`, `g31_warn_after_lws=false`, `p12_block_http=400` | `4` | **`9,732` pixels** (`29,656` bytes, `aff0e96d67570d8b`) | `0` (`false`) |
| **Scenario C**: Page 6 Viewfinder HUD + C2PA `READ_KEY` 拦截 + XML Sidecar + `CAMSET` 往返 | `page=6`, `c2pa_block_http=400`, `c2pa_blocked_attempts=1`, `private_key_reads=0`, `cnflasha_writes=0`, `xml_has_mcfl_c2pa=true`, `camset_roundtrip_ok=true`, `MCFL=` 串口遥测确认 | `8` | **`367,761` pixels** (`1,371,736` bytes, `b330a24d4b2e51df`) | `0` (`false`) |

实测结束后已精准终止自启动子进程（`PID 37116`，`rc=0`）并彻底删除 `/private/tmp/fx6-phase109-18781`，全程未触碰 `8768` 端口，也未使用 `pkill`/`killall`。

### 3.2 离线双模单元测试与全仓清洁门禁 / Dual-Mode Unit & Clean-Only Gates

- **本地供体模式 / Local Donor Mode** (`PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -v`): **303 / 303 PASSED**（含新增 30 项 `test_phase109_mcfleet_sdi_c2pa.py`）
- **洁净室模式 / Clean-Room Mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **303 / 303 PASSED**（`skipped=2` 仅限于既有供体二进制校验项，Phase 109 全部 30/30 通过）
- **全仓干净测试门禁 / Lab Clean-Only Gate** (`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`): 全部通过。

---

## 4. 变更文件清单 / Owned Files

1. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c)
2. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py)
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md)
4. [outputs/fx3-vm-trial/tests/test_phase109_mcfleet_sdi_c2pa.py](../../outputs/fx3-vm-trial/tests/test_phase109_mcfleet_sdi_c2pa.py)
5. [reports/2026-11-14-phase109-vm-trial-mcfleet-sdi-c2pa/README.md](README.md)
