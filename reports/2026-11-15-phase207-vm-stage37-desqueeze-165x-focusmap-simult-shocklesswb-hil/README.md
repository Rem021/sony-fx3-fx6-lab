# Phase 207（VM Stage 37 `37/37`）：真机 `ILME-FX3` `[De-Squeeze Display]`（`1.6x=1.65x` 4 锁 & HDMI RAW 旁路）、外置 `M&C Focus Map`（`>=150fps` 截止）与 `[Simult. + Auto Switch]` / `[Shockless WB]` HIL 协同仿真报告

## 1. 结论先行

已在 `outputs/fx3-vm/` 独立完成 **Task H228 — Phase 207（VM Stage 37 `37/37` 里程碑）** 真实硬件主线协同仿真器开发、全板编排接入与双模全量验证：

- **交付物清单（严格受控边界）**：
  1. 新增 Stage 37 核心模块：[realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py)
  2. 更新 37 阶段全板编排器（接入 `stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil` 与 `--skip-phase207`）：[fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)
  3. 新增 48 项双模单测套件（`>= 46` 要求，含 `< 6.0s` 壁钟上限断言）：[test_realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/tests/test_realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py)
  4. 更新虚拟机文档（Stage 37 `37/37` 章节与 CLI 指南）：[outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/README.md)
  5. 参考全球实测情报基线：[Wave-27 Real-Hardware Intel README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/reports/2026-11-15-global-sony-wave27-desqueeze-165x-4locks-external-focusmap-150fps-simult-autoswitch-shocklesswb-intel/README.md)

## 2. 四大核心支柱（`Pillars A–D`）实现与实测证据

### 2.1 双模高速 `os.O_RDONLY` 供体审计（`< 0.10s`）与零字节泄露回退
- [`inspect_phase207_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py#L469-L633) 严格通过 `os.open(..., os.O_RDONLY)` 核验 12 份 FX3 `7.02` 与 FX6 `6.01` 真实供体（对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 采用 `<= 4096 B` 定点 `lseek` 窗口读取并带进程内缓存，实测冷启动 `< 0.01s`）；实证 `string_english_f.uxc`（`373,820 B`）包含全部 19 项 Wave-27 UI 词条且 `fx6_appfw` 偏移 `37,404,672` 处存在精确 `"1.65"` 缩放字面量；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动回退至确定性 `CLEAN_ROOM_SYNTHETIC` 基线，`raw_firmware_bytes_leaked == 0`。

### 2.2 Pillar A — `[De-Squeeze Display]`（`Off/1.3x/2.0x/1.5x/1.6x=1.65x`）4 锁与 5 态旁路 HIL
- [`probe_desqueeze_display_4locks_and_bypass_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py#L640-L824) 精确复刻 `MENU -> Setup -> [Display Option] -> [De-Squeeze Display]`：
  - `[1.6x]` 执行官方 **`1.65x`** 水平拉伸（`16:9 -> 2.39:1` CinemaScope），`1.3x / 1.5x / 2.0x` 对应 `1.30x / 1.50x / 2.00x`。
  - 开启任意非 `Off` 档位时强制锁定 4 项设置：`[Focus Mode]=Manual Focus`、`[Focus Area]=Wide`、`[SteadyShot]=Off`、`[Face Priority in Multi Metering]=Off`（越权覆盖请求返回 `EOPNOTSUPP = 95`）。
  - 在 `[RAW Output]=On`、`[Rec. Media dur HDMI Output]=Off(HDMI Only)`（同步强制 `effective_hdmi_info_display="Off"`）、`[Log Shooting]=Off`、`[Remote Shooting]` 与 `Photo` 拍照模式下自动旁路抑制显示反挤压，且 `desqueeze_baked_into_raw_or_xavc_frames == 0`。

### 2.3 Pillar B — 外置专属 `Monitor & Control` `[Focus Map]`（零机内菜单）与 `>=150fps` 截止 HIL
- [`probe_external_mc_focus_map_and_150fps_cutoff_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py#L890-L1026) 对机内 FX3 `[Focus Map]` 菜单切换与 Stage-B 本地叠加层注入一律返回 `EOPNOTSUPP`（`95`）；在通过 CPAPP 16 位原厂 E-Mount PDAF 谓词 `((id >> 14) == 3) && ((id & 0x0FFF) != 0x0FFF)` 校验后，允许 `< 150fps`（含 FX3 支持但 FX6 封锁的 **`1..6fps` S&Q 低帧率**及 `24p..120fps`）向外置 `M&C` 推流深度图，并对 **`>= 150fps`**（`150 / 200 / 240fps`）、转接环/手动非 PDAF 镜、UVC 推流及机内回放执行硬拦截。

### 2.4 Pillar C & D — 双卡 `[Simult. + Auto Switch]`、`[Shockless WB]` 0 帧旁路与硬安全红线
- [`probe_simult_recording_auto_switch_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py#L1090-L1208) 仿真 `[Simult. Recording]` 下 `[Auto Switch Media]=On` 单卡满容后无缝单卡续录及热插换空卡恢复双卡同录，对比 `Off` 严格双备份一致性停机（`0` 丢帧、`0` 孤立 `.RSV`）。
- [`probe_shockless_wb_and_kelvin_bypass_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py#L1211-L1294) 仿真 `[Shockless WB]`（`Off / 1 / 2 / 3`）跨 `1..240fps` 全帧率预设切换平滑渐变，以及直接编辑 `[C.Temp./Filter]` 色温开尔文值与 `A–B / G–M` 微调网格时的 **`0` 帧即时生效旁路**。
- [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h228-phase207-vm-stage37-desqueeze-165x-focusmap-simult-shocklesswb-hil/outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py#L1297-L1354) 硬锁 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`。

## 3. 实测验证摘要（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 结果与实测指标 |
|---|---|---|
| Stage 37 独立自检 CLI | `LOCAL_DONOR_RDONLY` / `CLEAN_ROOM_SYNTHETIC` | `PASS`（`digest=5e31a0f5c1ed` / `986695bf0dc5`） |
| `fx3_vm_coemulation_suite.py`（Stage `1..37`） | 本地只读供体 / 洁净室合成 | `PASS`（进程内 `1.82s < 2.1s` / `0.43s < 1.0s`；`digest=6c8e4723f3ca` / `ec5242849656`） |
| Stage 37 专项双模单测（48 项） | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `48/48 OK`（`5.15s` / `3.18s < 6.0s`） |
| `outputs/fx3-vm/tests` 全量单测发现 | 默认 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `1420/1420 OK`（`113.74s` / `110.40s`） |
| `scripts/run_all_lab_tests.py --clean-only` | 全仓洁净室门禁 | `ALL GREEN in 2.21s` |
