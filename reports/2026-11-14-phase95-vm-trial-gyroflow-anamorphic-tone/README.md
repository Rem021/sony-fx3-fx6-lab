# Phase 95 — Live FX6-on-FX3 交互控制台：变形镜头（`1.33x/1.5x/1.8x/2.0x`）IBIS 非对称/居中锁仲裁、Gyroflow `2000Hz` RTMD 就绪遥测与 `1kHz -20dBFS` 基准音 / 4-Ch 限幅器

> **Phase 95 — Live FX6-on-FX3 Interactive Console: Anamorphic (`1.33x/1.5x/1.8x/2.0x`) IBIS Asymmetric Yaw-Gain / Center-Lock Arbitrator, Gyroflow `2000Hz` RTMD Readiness HUD, & `1kHz -20dBFS` Reference Tone / 4-Ch Limiter**

- **日期 / Date**: 2026-11-14
- **分支 / Branch**: `codex/h94-phase95-vm-trial-gyroflow-anamorphic-tone`
- **隔离验证端口 / Isolated Port**: `http://127.0.0.1:18779/` (`--workdir /private/tmp/fx6-phase95-18779`，实测后已终止子进程并删除工作目录；生产端口 `8768` 全程零接触、零干扰)

---

## 1. 交付概览 / Executive Summary

本次 Phase 95 在不触动 `8768` 在线会话与 `P4/P10/P11/P12` 硬件契约的前提下，完成了面向变形宽银幕摄影与后期 Gyroflow 工作流的四大能力闭环：

1. **变形镜头反挤压与 FX3 5 轴 IBIS 自动仲裁器（Anamorphic IBIS Arbitrator）**
   - 支持 `squeeze_factor` ∈ `{1.0, 1.3, 1.33, 1.5, 1.8, 2.0}` 与 `ibis_mode` ∈ `{Off, Standard, Active, Anamorphic_Asymmetric, Center_Lock_Gyroflow}`。
   - 当 `squeeze_factor > 1.0` 且用户请求未做横向补偿的球面 `Active` 防抖时，仲裁器自动将其钳位/路由至 `Anamorphic_Asymmetric`（水平偏航增益 `horizontal_yaw_gain = 1 / squeeze_factor`，如 `2.0x -> 0.5000`，垂直俯仰保持 `1.0`）或 `Center_Lock_Gyroflow`（`0x0400` 居中锁定以便 Gyroflow 后期增稳），彻底消除变形镜头边缘果冻晃动（`anamorphic_edge_wobble_prevented: True`）。
   - 与 Phase 81 Touch-AF 坐标体系联动：支持 `desqueezed_touch_x`（`coordinate_space="desqueezed"`）按 `1 / squeeze_factor` 精确反算回 `960x540` 传感器坐标（如 `2.0x` 下 `desqueezed_touch_x=1200 -> touch_x=600`），并兼容 `1.3x / 1.5x / 1.8x` 遮幅盲区拦截。

2. **Gyroflow / Sony Catalyst `2000 Hz` 6 轴 IMU RTMD 就绪遥测与 IMX510 卷帘果冻延迟**
   - 实时计算 `imu_samples_per_frame`（`83.4 @ 23.98p`、`33.4 @ 59.94p`、`16.7 @ 119.88p`）与 IMX510 读出卷帘延迟（FF 4K `8.7 ms` / 4K120 `4.3 ms`）。
   - 当 Phase 64 `S&Q` VFR 激活时，自动切换为 `RTMD_SUSPENDED_BY_SQ`（与 Sony FX3/FX6 实体固件一致）。
   - 在 `GET /api/xml_sidecar`（`NonRealTimeMeta v2.20`）中自动注入 `<Lenses><Lens anamorphicSqueezeFactor="..." desqueezeDisplay="..." desqueezedAspectRatio="..." irisFstop="..." /></Lenses>` 以及 `<AcquisitionRecord>` 的 `AnamorphicGyroflowRtmd` 与 `AudioReferenceAndLimiter` 元数据组。

3. **Cinema Line `1 kHz -20.0 dBFS` 基准校准测试音 / SMPTE 彩条 & 4 通道 `24-bit` `-3.0 dBFS` 软拐点限幅器**
   - 待机（`STBY`）下可随时开关 `1 kHz -20.0 dBFS` 参考测试音与 7 色 SMPTE 彩条；一旦切换至 `REC` 录制态，测试音与彩条自动被抑制（`ref_tone_inhibited_by_rec: True`），并在客体 `GPE0` 显存直接高亮显示 `[1kHz INHIBITED:REC]`，杜绝误覆盖现场同期声；退回 `STBY` 后自动恢复。
   - 4 通道 `24-bit` `-3.0 dBFS` 峰值限幅器对超出 `-3.0 dBFS` 的通道实时执行软拐点钳位并反馈 `ch_clamped` 掩码与 `effective_ch_db`。

4. **客体 `GPE0`（`0x41e001000`）`mb[44..47]` `'GYRO'` 零堆分配 HUD、四语控制台与 `CAMSET` 持久化**
   - 在 [fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) 新增 `mb[44..47]`（Magic `0x4759524F` `'GYRO'`）及 `fx6_render_phase95_gyroflow_anamorphic_tone_overlay()`，直接在物理显存绘制变形安全框线、偏航增益进度条、Gyroflow IMU/Skew 状态与 `1kHz`/SMPTE 彩条徽章（`0` `malloc/calloc/printf`）。
   - 在 [run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py) 新增 `GET/POST /api/gyroflow_anamorphic`，集成至 `/api/status`、`/api/xml_sidecar`、`/api/camset_export` / `/api/camset_import`（含旧版向后兼容与畸形字段 fail-closed 拦截）以及 `#phase95-gyroflow-anamorphic-card` 四语（`EN / 简体中文 / 繁體中文 / 日本語`）交互面板。

---

## 2. 邮箱协议寄存器契约 (`mb[44..47]` `'GYRO'`)

| Word | 物理地址偏移 | 关键字段布局 | 默认引导值 |
|---|---|---|---|
| `mb[44]` | `0x41e000e00 + 0xB0` | `[2:0] sq_idx` · `[5:3] eff_ibis_idx` · `[8:6] req_ibis_idx` · `[9] ibis_arbitrated` · `[10] center_lock_0x0400` · `[18:11] yaw_gain_pct` · `[28:19] touch_x` · `[29] touch_af_desqueeze_synced` · `[30] wobble_prevented` · `[31] valid` | `0x8F032048` |
| `mb[45]` | `0x41e000e00 + 0xB4` | `[11:0] imu_samples_x10` · `[19:12] skew_ms_x10` · `[21:20] rtmd_status_idx` · `[22] rtmd_suspended_by_sq` · `[23] gyroflow_ready` · `[24] fallback_center_lock` · `[31:25] squeeze_x50` | `0x64857342` |
| `mb[46]` | `0x41e000e00 + 0xB8` | `[0] tone_req` · `[1] tone_eff` · `[2] tone_inhib_rec` · `[3] bars_eff` · `[4] lim_en` · `[5] lim_eng` · `[9:6] ch_clamped_mask` · `[17:10] ceil_x10(30)` · `[25:18] ref_lvl_abs(20)` · `[31] tone_valid` | `0x80507800` |
| `mb[47]` | `0x41e000e00 + 0xBC` | 协议魔数 `'GYRO'` | `0x4759524F` |

---

## 3. 隔离端口实机 QEMU 渲染与自动化验证证据 / Verification Receipts

### 3.1 隔离端口 `--port 18779` 实机 QEMU `GPE0` 像素差异实测

在严格隔离目录 `/private/tmp/fx6-phase95-18779`（`--port 18779 --no-browser`）启动完整 FX3+FX6 QEMU 虚拟机：

| 验证阶段 / Scenario | 关键状态与遥测结果 | `ack_seq` | `GPE0` 真实像素变化 | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Boot** | `boot_ready_sec=53.33s`, `gpe0_nonzero_px=404,631`, `text_ok=42`, `crashed=false` | `1` | 基线 (`5cb352cffc...`) | `0` (`false`) |
| **Scenario A**: `2.0x` + `Active` -> `Anamorphic_Asymmetric` (`yaw=0.5`) + Touch-AF (`1200->600`) + `1kHz -20dBFS` + SMPTE Bars + Limiter (`Ch1 +5 -> -3.0dB`) | `effective_ibis_mode="Anamorphic_Asymmetric"`, `limiter_engaging=true`, `effective_ch_db=[-3.0,-12.0,-12.0,-12.0]` | `3` | **`76,674` pixels** (`226,870` bytes, `71b380250b...`) | `0` (`false`) |
| **Scenario B**: `1.8x` + `Active` -> `0x0400 Center_Lock_Gyroflow` + `REC` Tally | `center_lock_0x0400=true`, `rtmd_status="RTMD_CENTER_LOCKED"`, `ref_tone_inhibited_by_rec=true` | `5` | **`33,591` pixels** (`100,521` bytes, `1fc48f0630...`) | `0` (`false`) |
| **Scenario C**: `S&Q 120fps` + `STBY` 恢复 + `M01.XML` + `CAMSET` 往返 | `rtmd_status="RTMD_SUSPENDED_BY_SQ"`, `16.7 samples/frame`, `4.3ms` skew, `<Lenses>` & `AnamorphicGyroflowRtmd` 就绪, `camset_roundtrip_ok=true` | `6` | **`46,606` pixels** (`139,204` bytes) | `0` (`false`) |

实测结束后已精准终止子进程（PID `88751`）并彻底删除 `/private/tmp/fx6-phase95-18779`，全程未触碰 `8768` 端口，也未使用 `pkill`/`killall`。

### 3.2 离线双模单元测试与全仓清洁门禁 / Dual-Mode Unit & Clean-Only Gates

- **本地供体模式 / Local Donor Mode** (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py"`): **241 / 241 PASSED**（含新增 30 项 `test_phase95_gyroflow_anamorphic_tone.py`）
- **洁净室模式 / Clean-Room Mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **241 / 241 PASSED**（`skipped=2` 仅限于既有供体二进制校验项，Phase 95 全部 30/30 通过）
- **全仓干净测试门禁 / Lab Clean-Only Gate** (`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`): 全部通过。

---

## 4. 变更文件清单 / Owned Files

1. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c)
2. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py)
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md)
4. [outputs/fx3-vm-trial/tests/test_phase95_gyroflow_anamorphic_tone.py](../../outputs/fx3-vm-trial/tests/test_phase95_gyroflow_anamorphic_tone.py)
5. [reports/2026-11-14-phase95-vm-trial-gyroflow-anamorphic-tone/README.md](README.md)
