# Phase 102 — Live FX6-on-FX3 交互控制台：预录制 Picture Cache（DDR 环缓）、电子快门间隔摄影、`.cube` (`17³/33³/65³ -> 33³` 四面体) 3D-LUT 实时上传与有线 USB-LAN FTPS 后台队列

> **Phase 102 — Live FX6-on-FX3 Interactive Console: Picture Cache (Pre-Rec Circular DDR Ring-Buffer), Interval Recording (Time-Lapse Electronic Shutter), User `.cube` (`17³/33³/65³ -> 33³` Tetrahedral) 3D-LUT Live Uploader, & Wired USB-LAN FTPS Background Queue**

- **日期 / Date**: 2026-11-14
- **分支 / Branch**: `codex/h102-phase102-vm-trial-picturecache-cube3dlut-ftps`
- **隔离验证端口 / Isolated Port**: `http://127.0.0.1:18780/` (`--work-dir /private/tmp/fx6-phase102-18780`，实测结束后已终止子进程 `PID 4621` 并彻底删除工作目录；生产端口 `8768` 全程零接触、零干扰)

---

## 1. 交付概览 / Executive Summary

本阶段在不触动实时服务端口 `8768` 与 `P4/P10/P11/P12` 硬件契约的前提下，完成了面向 Cinema Line 实战拍摄流程的四大核心闭环：

1. **FX6 Picture Cache（Pre-Rec 环形 DDR 缓存 / Circular DDR Ring-Buffer）**
   - 支持 `cache_seconds` ∈ `{0, 2, 4, 8, 16}` 与多码率编码档位（`XAVC_I_4K60`, `XAVC_I_4K24`, `XAVC_L_4K60`, `XAVC_L_4K30`, `XAVC_I_FHD60`, `XAVC_L_FHD60`, `XAVC_HS_4K60`）。
   - 在 FX3 `2048 MiB` DRAM 上将环形缓存确定性钳位至 **`<= 384.0 MiB`**（如 `8s @ XAVC_I_4K60 (75 MiB/s)` 请求 `600.0 MiB` 时自动钳位为 `effective_cache_seconds = 5s`、`375.0 MiB`，`clamped_by_ddr_budget = True`）。
   - 当 `S&Q` VFR、`Interval Recording` 或 `HDMI RAW16` 激活时自动挂起 Picture Cache（`picture_cache_suspended = True`），退出互斥模式后自动恢复。

2. **Interval Recording（时间间隔摄影电子快门保护 / Time-Lapse E-Shutter Protection）**
   - 支持 `interval_rec_enabled`、`interval_sec`（`1..60s`）、`target_shots`（`1..9999`）与 `ae_tracking`（`High` / `Mid` / `Low` / `Lock`）。
   - 严格强制 **Electronic Shutter**（`mechanical_curtain_actuations == 0`），对任何 `mechanical_shutter=True` 或 `shutter_type != "ELECTRONIC"` 篡改执行 fail-closed 拒绝（HTTP `400`），并与 `S&Q` / `Picture Cache` 严格互斥。

3. **Live `.cube` 3D-LUT 清洗器与 `33³` 四面体重采样器（`POST /api/upload_cube_lut`）**
   - 解析真实 Adobe / Iridas `.cube` 文本载荷（支持 `17³`、`33³`、`65³` 网格 + `TITLE` + `DOMAIN_MIN` / `DOMAIN_MAX`），对 `NaN` / `Inf` / 倒置域（`DOMAIN_MIN >= DOMAIN_MAX`）或截断网格执行 fail-closed 拒绝（HTTP `400` + 结构化错误码）。
   - 在易失 RAM 中完成精确四面体插值重采样至 `33³`（`35,937` 三元组，零固件/标定区写入：`persistent_emmc_writes_authorized = False`，`emmc_mutation_bytes = 0`），实时将预览色块与对比度特征同步至示波器 `lut_preview` 与客体 `GPE0` HUD，并在 `GET /api/xml_sidecar`（`NonRealTimeMeta v2.20`）暴露 `MonitoringLutTitle`、`MonitoringLutResampled33Sha256` 与 `<Group name="PictureCacheIntervalCubeFtps">`。

4. **Wired USB-LAN FTPS 后台传输队列（`P12` Wi-Fi/BT 射频关闭强制 / P12 RF-Off Enforced）**
   - 支持 `ftps_mode` ∈ `{Off, Proxy_Only, Original_And_Proxy}`，严格限定经由有线 `CDC-NCM / RTL8153`（或 `AX88179`）USB-LAN 接口入队与传输，并强制保持 `P12` 射频关闭（`wf12_00342260_hits == 0`），对任何开启 Wi-Fi/BT 或非有线网卡请求 fail-closed 拒绝。
   - 严格校验媒体根目录（`/mnt/slot_a`, `/mnt/slot_b`, `/mnt/cfexpress_a`, `/mnt/cfexpress_b`, `/mnt/sd`），对一切 eMMC `p1..p15`、`nflasha`、系统目录或 `..` 路径穿越请求返回 HTTP `400`（`emmc_path_traversal_blocked`）并累计 `ftps_blocked_traversal_count`。

5. **客体 `GPE0` (`0x41e001000`) `mb[48..51]` `'ICLF'` HUD、`CAMSET` 往返与四语 Web UI**
   - 在 [fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) 中新增 `mb[48..51]`（Magic `0x49434C46` `'ICLF'`）与零堆分配/零 `printf` 渲染函数 `fx6_render_phase102_cache_interval_lut_ftps_overlay()`，实时绘制 Picture Cache DDR 进度条、Interval Rec E-Shutter 计数、Active `.cube` 3D-LUT 槽位与 `33³` 状态、及 USB-LAN FTPS P12-Safe 徽章。
   - 在 [run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py) 中集成 `GET/POST /api/interval_cache_lut_ftp`、`GET/POST /api/upload_cube_lut`、`/api/status`、`/api/xml_sidecar`、`CAMSET` 导出/导入往返，以及四语（`EN / 简体中文 / 繁體中文 / 日本語`）Web UI 面板 `#phase102-cache-lut-ftp-card`。

---

## 2. 邮箱协议寄存器契约 (`mb[48..51]` `'ICLF'`)

| Word | 物理地址偏移 | 关键字段位域布局 / Bit Layout | 默认引导值 |
|---|---|---|---|
| `mb[48]` | `0x41e000e00 + 0xC0` | `[4:0] cache_eff_s` · `[9:5] cache_req_s` · `[18:10] ddr_mib(<=384)` · `[19] cache_act` · `[20] cache_susp` · `[21] clamped` · `[22] intvl_en` · `[28:23] intvl_s` · `[30:29] ae_idx` · `[31] valid` | `0xA2800000` |
| `mb[49]` | `0x41e000e00 + 0xC4` | `[13:0] shots_taken` · `[27:14] target_shots` · `[29:28] ftps_mode_idx` · `[30] p12_safe(1)` · `[31] eshut_enforced(1)` | `0xC01E0000` |
| `mb[50]` | `0x41e000e00 + 0xC8` | `[2:0] lut_slot` · `[3] resamp33` · `[5:4] lut_src_idx(17/33/65)` · `[13:6] contrast_x100` · `[21:14] ftps_q` · `[29:22] ftps_done` · `[30] trav_blk` · `[31] valid` | `0x80001900` |
| `mb[51]` | `0x41e000e00 + 0xCC` | 协议魔数 `'ICLF'` | `0x49434C46` |

---

## 3. 隔离端口实机 QEMU 渲染与自动化验证证据 / Verification Receipts

### 3.1 隔离端口 `--port 18780` 实机 QEMU `GPE0` 像素差异实测

在完全隔离目录 `/private/tmp/fx6-phase102-18780`（`--port 18780 --work-dir /private/tmp/fx6-phase102-18780 --no-browser`）启动完整 FX3+FX6 QEMU 虚拟机：

| 验证阶段 / Scenario | 关键状态与遥测结果 | `ack_seq` | `GPE0` 真实像素变化 | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Boot** | `boot_ready_sec=66.39s`, `gpe0_nonzero_px=404,631`, `text_ok=40`, `crashed=false` | `1` | 基线 (`8d05c298a3a54c94...`) | `0` (`false`) |
| **Scenario A**: Picture Cache `8s @ XAVC_I_4K60` + `17³->33³` `.cube` (`QEMU_Phase102_TealGold`) | `effective_cache_seconds=5`, `allocated_ddr_mib=375.0`, `clamped=true`, `resampled_33_triplets=35937`, `emmc_mutation_bytes=0` | `3` | **`28,212` pixels** (`84,529` bytes, `37c6f6caa0f49792...`) | `0` (`false`) |
| **Scenario B**: Interval Rec `2s/240f` (`shots_taken=3`) + USB-LAN FTPS `Proxy_Only` + `/dev/mmcblk0p1` 穿越拦截 | `picture_cache_suspended=true` (`INTERVAL_REC_ACTIVE`), `mechanical_curtain_actuations=0`, `ftps_queued_count=1`, `ftps_blocked_traversal_count=1`, `wf12_00342260_hits=0` | `5` | **`31,436` pixels** (`94,279` bytes, `aef94359c178064e...`) | `0` (`false`) |
| **Scenario C**: Page 6 Viewfinder HUD + `NonRealTimeMeta` XML + `CAMSET` 导出/导入往返 | `page=6`, `xml_has_lut_sha33=true` (`a84648d13f93432f...`), `camset_roundtrip_ok=true`, `ack_seq == cmd_seq == 6` | `6` | **`352,103` pixels** (`1,040,466` bytes, `f7f31c3df1dc64e9...`) | `0` (`false`) |

实测结束后已精准终止自启动子进程（`PID 4621`）并彻底删除 `/private/tmp/fx6-phase102-18780`，全程未触碰 `8768` 端口，也未使用 `pkill`/`killall`。

### 3.2 离线双模单元测试与全仓清洁门禁 / Dual-Mode Unit & Clean-Only Gates

- **本地供体模式 / Local Donor Mode** (`PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py"`): **273 / 273 PASSED**（含新增 32 项 `test_phase102_picturecache_cube3dlut_ftps.py`）
- **洁净室模式 / Clean-Room Mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **273 / 273 PASSED**（`skipped=2` 仅限于既有供体二进制校验项，Phase 102 全部 32/32 通过）
- **全仓干净测试门禁 / Lab Clean-Only Gate** (`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`): 全部通过。

---

## 4. 变更文件清单 / Owned Files

1. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c)
2. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py)
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md)
4. [outputs/fx3-vm-trial/tests/test_phase102_picturecache_cube3dlut_ftps.py](../../outputs/fx3-vm-trial/tests/test_phase102_picturecache_cube3dlut_ftps.py)
5. [reports/2026-11-14-phase102-vm-trial-picturecache-cube3dlut-ftps/README.md](README.md)
