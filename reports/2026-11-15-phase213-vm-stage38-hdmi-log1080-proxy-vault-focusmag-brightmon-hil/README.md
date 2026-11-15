# Phase 213（VM Stage 38 `38/38`）：真机 `ILME-FX3` HDMI Log `1080p` 强制降档 vs `[Off(HDMI Only)]` `4K 10-bit` 黑屏联动、`Px` 代理双编码耦合保险库与 `[Focus Magnifier]` × `[Bright Monitoring]` 互斥 HIL 协同仿真报告

## 1. 结论先行

已在 `outputs/fx3-vm/` 独立完成 **Task H235 — Phase 213（VM Stage 38 `38/38` 里程碑）** 真实硬件主线协同仿真器开发、全板编排接入与双模全量验证：

- **交付物清单（严格受控 5 文件边界）**：
  1. 新增 Stage 38 核心模块：[realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py)
  2. 更新 38 阶段全板编排器（接入 `stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil` 与 `--skip-phase213`）：[fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
  3. 新增 48 项双模单测套件（满足 `>= 45` 要求，含 `< 6.0s` 壁钟上限与源码只读/端口卫生断言）：[test_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/tests/test_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py)
  4. 更新虚拟机模块文档（Stage 38 `38/38` 章节与 CLI 指南）：[outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/README.md)
  5. 参考索尼官方 `ILME-FX3 Ver. 7.02` 实测情报基线：[Wave-28 Real-Hardware Intel README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/reports/2026-11-15-global-sony-wave28-hdmi-log-1080p-hdmionly-4k-proxy-coupled-vault-focusmag-brightmon-intel/README.md)

## 2. 核心子模型（`Sub-models A–C` + 硬安全红线）实现与实测证据

### 2.1 双模高速 `os.O_RDONLY` 12 供体有界审计（实测冷启动 `5.25 ms < 0.02s`）与零字节泄露回退
- [`inspect_phase213_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py#L731-L820) 严格通过 `os.open(..., os.O_RDONLY)` 核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 采用 `<= 4096 B` 定点 `lseek` 窗口读取并带进程内缓存，实测冷启动仅 **`0.00525s`**）；实证 `string_english_f.uxc`（`373,820 B`）、`libInfraAdjMedia.so`（`318,152 B`）与 `fx3_appfw` 包含全部 Wave-28 菜单词条与内部符号（`HDMI Output Settings`、`Off(HDMI Only)`、`4K Output Set.(HDMI Only)`、`PPLUT`、`LOG_SHOOTING`、`Proxy Settings`、`XAVC HS HD`、`XAVC S HD`、`M4ROOT`、`CLIP`、`SUB`、`Initial Focus Mag.`、`Auto Magnifier in MF`、`Bright Monitoring`、`Setting Effect OFF`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动回退至确定性 `CLEAN_ROOM_SYNTHETIC` 基线，`raw_firmware_bytes_leaked == 0`。

### 2.2 Sub-model A — HDMI Log `1080p` 强制降档 vs `[Off(HDMI Only)]` `4K 10-bit` & 机身 LCD 黑屏联动 HIL
- [`probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py#L827-L947) 精确复刻 `MENU -> Setup -> [External Output] -> [HDMI Output Settings]`：
  - 当 `[Rec. Media dur HDMI Output]=On`、`[RAW Output]=Off` 且激活 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）或 `PPLUT1..PPLUT4` 时，即便请求 `2160p`/`Auto`，HDMI 输出强制降档至 **`1920x1080`（`1080p`）**，同时保持机内存储卡录制开启（`internal_card_recording_active == True`）。
  - 当切换 `[Off(HDMI Only)]` + `[4K Output Set.(HDMI Only)]`（`59.94p / 50p / 29.97p / 25p / 23.98p / 24.00p 10bit` 全 6 档）时输出原生 **`3840x2160` `4K 10-bit`**，以 `EOPNOTSUPP`（`95`）硬封锁机内卡录（`internal_card_recording_active == False`），自动强制 `effective_hdmi_info_display == "Off"` 并抑制 HDMI 反挤压（`hdmi_desqueeze_active == False`）。
  - 当 `[Rec. Media dur HDMI Output]=On` 且 `[HDMI Info. Display]=On` 时自动熄灭机身内置 LCD 屏幕（`camera_lcd_blanked == True`），并同步透传 `[Emphasized REC Display]` 红框录制 Tally；`[RAW Output]=On`（`4264x2408` 16-bit Linear RAW）旁路 `1080p` 降档并保持纯净无叠加输出。

### 2.3 Sub-model B — `[Proxy Settings]` 双编码矩阵、高帧率截止、零机内代理回放与 `CLIP/`+`SUB/` 原子耦合保险库 HIL
- [`probe_proxy_dual_codec_and_coupled_vault_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py#L1026-L1178) 建模 `MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings]`：
  - 协同仿真 `XAVC HS HD`（`1920x1080` 10-bit HEVC `4:2:0`：`16M` 与子默认 `9M`，最高 `59.94p/50p`）与全局默认 `XAVC S HD`（`1280x720` 8-bit AVC `4:2:0`：`6M`，最高 `59.94p/50p`），在常规 `119.88p/100p`、S&Q 录制帧率 `119.88p/100p`、S&Q 采样帧率 `>= 100fps/120fps` 及 `[Off(HDMI Only)]` 下以 `EOPNOTSUPP`（`95`）阻断代理生成。
  - 严格锁定零机内代理独立回放（`on_camera_proxy_playback_supported == False`、`on_camera_proxy_playback_frames == 0`，仅在主片索引缩略图显示 `(Px)` 徽标），并保证机内 Delete / Protect 对 `/PRIVATE/M4ROOT/CLIP/<Clip>.MP4` 与 `/PRIVATE/M4ROOT/SUB/<Clip>S03.MP4` 100% 原子耦合执行（受保护片段删除返回 `EACCES = 13`，单边机内修改返回 `EOPNOTSUPP = 95`，外部读卡器孤儿文件返回 `EINVAL = 22`）。

### 2.4 Sub-model C & Redlines — `[Focus Magnifier]` 动态/静态倍率分野 × `[Bright Monitoring]` 互锁与硬安全红线 HIL
- [`probe_focus_mag_and_bright_monitoring_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py#L1255-L1390) 协同仿真 `[Initial Focus Mag.]` 视频（`Movie`/`S&Q`：`x1.0` / `x4.0`）与照片（全画幅 `x1.0` / `x2.1`、APS-C/S35 `x1.0` / `x1.5`）倍率矩阵、视频模式下禁用 `[Auto Magnifier in MF]` 对焦环自动放大（`EOPNOTSUPP = 95`）、放大激活期间自动隐藏 `[Marker Display]`，以及放大激活期间锁定 `[Bright Monitoring]` 自定义键（`EOPNOTSUPP = 95`）、`P/A/S/M` + `MF` 激活强制 `[Live View Display] -> [Setting Effect OFF]` 与跨模式/AF/关机自动取消。
- [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h235-phase213-vm-stage38-hdmi-log1080-proxy-vault-focusmag-brightmon-hil/outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py#L1393-L1433) 硬锁 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`single_sided_proxy_or_main_orphan_mutations = 0`、`on_camera_proxy_playback_frames = 0`。

## 3. 实测验证摘要（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 结果与实测指标 |
|---|---|---|
| Stage 38 独立自检 CLI | `LOCAL_DONOR_RDONLY` / `CLEAN_ROOM_SYNTHETIC` | `PASS`（冷读取 `5.25 ms < 0.02s`；`digest=ad55f5e61e5a` / `5f3872548cac`） |
| `fx3_vm_coemulation_suite.py`（Stage `1..38`） | 本地只读供体 / 洁净室合成 | `PASS`（`38/38` 全阶段通过，洁净室 `0.464s < 0.6s`；`digest=3031d8ef68e4` / `ba7ed9c4fcfe`） |
| Stage 38 专项双模单测（48 项） | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `48/48 OK`（`5.36s` / `3.53s`） |
| `outputs/fx3-vm/tests` 全量单测发现 | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `1468/1468 OK`（`121.95s` / `106.62s`） |
| `scripts/run_all_lab_tests.py --clean-only` | 全仓洁净室门禁 | `ALL GREEN in 2.64s` |
