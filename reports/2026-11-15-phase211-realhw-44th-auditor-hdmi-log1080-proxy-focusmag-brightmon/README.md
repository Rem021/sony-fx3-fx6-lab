# Phase 211（第 44 号固件审计器 `44/44`）交付报告：`ILME-FX3` (`Ver. 7.02`) HDMI Log `1080p` vs `Off(HDMI Only)` `4K 10-bit`、`Px` 代理耦合金库与 `Focus Magnifier` / `Bright Monitoring` 审计器

## 1. 核心结论

1. **第 44 号审计器 (`44/44`) 完整闭环**：已在 [`realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor.py) 完成 `PHASE_211_SCHEMA` (`211.0.0`) 落地，导出至 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)，并在 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) 注册独立子命令 `audit-realhw-hdmi-log1080-proxy-focusmag-brightmon` 与总控 `audit-all` (`44/44`)，同步更新 [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/README.md)。
2. **有界 `os.O_RDONLY` + `os.pread` 极速扫描与洁净室字节级确定性**：本地真机 Donor 六件套（`FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 的 `appFw.so`、`.uxc`、`CPAPP-B.BIN`）冷启动扫描实测耗时 **`0.070s .. 0.084s`**（严格小于 `< 0.15s` 硬预算，进程内 `_DONOR_SCAN_CACHE_P211` 命中 `< 1ms`）；`CPAPP-B.BIN` 严格执行头部 `768 KiB` + 尾部 `6 MiB` 有界读取，`raw_firmware_bytes_leaked == 0`（Donor 报告 SHA-256：`6fc19973e543e4fe6dae697a1e562c989daa18b828f01bb5e7c01d8958fdae87`；洁净室报告 SHA-256：`36a456bade6e192b45778ca7f27819090a1f70086a378b1324b4fdbc41615c15`）。
3. **全量双模回归 `100%` 绿灯**：新增 [`test_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/tests/test_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon.py) **54 项**双模单测（本地 Donor `0.508s`、洁净室 `0.377s`）；`outputs/fx3-firmware-lab/tests` 全量 **1,683 项**单测在本地 Donor 模式（`57.783s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式（`28.612s`，含跨子进程 `audit-all --clean-room --json` 字节级一致性断言）全部 `100%` 通过，`scripts/run_all_lab_tests.py --clean-only` `0.05s` 全绿。

---

## 2. 四大实证支柱（实测二进制证据 vs 建模边界）

### Pillar A — `[HDMI Output Settings]`（`[On]` vs `[Off(HDMI Only)]`）、`Log / PPLUT1..4` 强制 `1080p` 下采样与机身 LCD 黑屏联动
- **实测二进制事实（`O_RDONLY`）**：
  - 原厂 `FX3 Ver. 7.02` (`appFw.so` `79,015,712 B` + `string_english_f.uxc` `373,820 B`) 与 `FX6 Ver. 6.01` (`appFw.so` `50,520,424 B` + `string_english.uxc` `118,208 B`) 均检出 `N5model38setting_rec_media_during_hdmi_output_tE`、`N5model32setting_hdmi_4k_output_setting_tE`、`N5model27setting_hdmi_info_display_tE` 与 `HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_10BIT`。
  - `FX3 Ver. 7.02` 检出独有符号 `BKID_APP_setting_rec_media_during_hdmi_output`、`BKID_APP_setting_hdmi_4k_output_setting`、`BKID_APP_setting_hdmi_info_display`、`BKID_APP_setting_raw_output`、`CAUTION_ID_FACTOR_PICTURE_PROFILE_PPLUT_MSG` 与 `CAUTION_ID_FACTOR_REC_MEDIA_DUR_HDMI_OUTPUT_OFF_MSG`；英文语言包 `string_english_f.uxc` 精确包含 `HDMI Output Settings`、`Rec. Media dur HDMI Output`、`Off(HDMI Only)`、`4K Output Set.(HDMI Only)`、`HDMI Info. Display`、`Emphasized REC Display`、`RAW Output`、`Log Shooting`。
- **精确信号路由建模**：
  - 当 `[Rec. Media dur HDMI Output] = [On]` 且 `[RAW Output] = [Off]` 时，只要启用 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）或 `[Picture Profile] = PPLUT1..PPLUT4`，即便 `[HDMI Resolution]` 设为 `Auto` 或 `2160p`，HDMI 输出仍被强制钳位下采样至 **`1080p` (`1920x1080`)**。
  - 切换 `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]` 解锁全部 6 档 `[4K Output Set.(HDMI Only)]`（`59.94p / 50p / 29.97p / 25p / 23.98p / 24.00p 10bit`，`3840x2160` 或 `4096x2160` DCI），但同步切断机内卡录与代理录制，并强制 `[HDMI Info. Display] = [Off]` 且抑制 HDMI 端变形宽银幕反挤压。
  - `[RAW Output] = [On]` 输出 `4264x2408` 16-bit 线性 RAW，同样强制 `[HDMI Info. Display] = [Off]`；当 `[Rec. Media dur HDMI Output] = [On]` 且 `[HDMI Info. Display] = [On]`（连接 HDMI 线）时，OSD 与 `[Emphasized REC Display]` 红框迁移至外置 HDMI 显示器，**机身内置 LCD 取景画面自动黑屏（Blanked）**。

### Pillar B — `[Proxy Settings]` 精确 2 格式 / 3 码率矩阵、高帧率截止与 `M4ROOT/CLIP/` + `M4ROOT/SUB/` 原子耦合文件库
- **实测二进制事实（`O_RDONLY`）**：
  - `FX3 Ver. 7.02` `appFw.so` 精确命中全部三档代理编码枚举：`PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD`、`PROXY_RECORD_SETTING_9M_420_10BIT_XAVC_HS_HD`、`PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD`（而 `FX6 Ver. 6.01` 为 `BKID_APP_EXTERN_SQ_PROXY_RECORDING_PROCAM` / `BKID_APP_EXTERN_PROXY_REC_BITRATE_PROCAM` 专业机分支）；双方 `CPAPP-B.BIN` 有界切片均检出 `Proxy`、`CLIP`、`SUB`。
- **精确编码与耦合契约建模**：
  - `MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings]` 仅允许 **2 种格式 / 3 档码率**：`[XAVC HS HD]`（`1920x1080` 10-bit 4:2:0 HEVC Long GOP，`16M` / `9M` 格式默认，最高 `59.94p/50p`）与全局默认 `[XAVC S HD]`（`1280x720` 8-bit 4:2:0 AVC Long GOP，`6M`，最高 `59.94p/50p`）；严禁注入 `XAVC S-I`、`ProRes Proxy` 等非法代理格式。
  - 三类硬截止：`[Rec Frame Rate] = 119.88p / 100p`、`S&Q` 传感器帧率 `>= 120fps`（NTSC：`120/240fps`）或 `>= 100fps`（PAL：`100/200fps`），以及 `[Off(HDMI Only)]`。
  - **零机内代理回放**（`on_camera_proxy_playback_supported = False`，仅在主素材缩略图叠加 `(Px)` 徽标）；机内 `Delete` / `Protect` 必须对 `/PRIVATE/M4ROOT/CLIP/<STEM>.MP4` 与 `/PRIVATE/M4ROOT/SUB/<STEM>S03.MP4` **成对原子生效**（拒绝任何机内单边 `CLIP_ONLY` / `SUB_ONLY` 操作，并在恢复校验中精准识别 `ORPHAN_SUB_WITHOUT_CLIP`、`MISSING_SUB_FOR_PX_CLIP` 与 `DESYNCED_CLIP_SUB_PROTECT_FLAGS`）。

### Pillar C — `[Initial Focus Mag.]` 视频/拍照分档、`[Auto Magnifier in MF]` 视频阻断与 `[Bright Monitoring]` 锁链
- **实测二进制事实（`O_RDONLY`）**：
  - `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` `appFw.so` 共享 `N5model37setting_mov_init_ratio_focus_magnif_tE`、`MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0`、`FOCUS_MAGNIFICATION_TIME_NO_LIMIT`、`N5model19setting_mf_assist_tE`、`N5model24setting_marker_display_tE`、`N5model33setting_bright_monitoring_state_tE`；`FX3 Ver. 7.02` 检出 `EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON`（而 `FX6 Ver. 6.01` 检出 `ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3_x6`）。
- **精确取景辅助互斥锁链建模**：
  - `[Initial Focus Mag.]` 在 `Movie / S&Q` 模式下严格限定 `x1.0`（默认）/ `x4.0`（配 `[Focus Magnif. Time]`：`2 Sec` / `5 Sec` / `No Limit` 默认），在 `Still` 全画幅下限定 `x1.0 / x2.1`、APS-C/S35 下限定 `x1.0 / x1.5`；将 `FX6` 的 `x3/x6` 请求安全映射至 `SHIM_TRANSLATED`。
  - `[Auto Magnifier in MF]` 在 `Movie / S&Q` 模式下硬性失效（转动对焦环不触发自动放大）；放大激活期间自动隐藏 `[Marker Display]` 构图线并在退出放大后恢复。
  - `[Bright Monitoring]` 在 `[Focus Magnifier]` 或拍照 `[Auto Magnifier in MF]` 激活期间锁定自定义键不可切换；激活后强制锁定实时取景为 `[Setting Effect OFF]`，且在关机、离开 `P/A/S/M` 曝光模式（如 `Flexible Exp.`）或离开 `MF`（切换至 `AF-C/AF-S/DMF`）时自动取消。

### Pillar D — 硬件零写防火墙与 `P211-01 .. P211-12` 12 触点四分类矩阵
- 完整建立 `P211-01 .. P211-12` 共 **12 个固件/硬件触点**，覆盖 `NATIVE_PASSTHROUGH`（5）、`SHIM_TRANSLATED`（5）、`MASKED_ABSENT_HW`（1）、`HARD_WRITE_PROTECTED`（1）全部四类桥接等级。
- 零写防火墙拦截对 `p2:/setting/Backup.bin`、`BODYDATA.DAT`、`p5:/wbi`、`p8:/cpapp-b.bin`、`p12:/cert`、`p18:/lens`、`/dev/cnflasha*` 与 `spi_nor:` 的全部持久化写入，仅放行易失性 `/tmp/fx6_wave28_hdmi_proxy_focusmag_overlay` 与 `ram://`（对未知非易失路径默认拒绝 fail-closed）。
- **边界声明**：本阶段全部工作均为本地主机侧离线 `O_RDONLY` 二进制取证与洁净室状态机建模，**未触碰端口 `8768`，未连接任何物理相机 USB，未生成或下发任何刷机载荷或闪存写入指令**。

---

## 3. 交付文件清单（严格限定归属范围内 6 个文件）

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor.py)（新增：第 44 号审计器 `44/44` 实现）
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 211 公共常量、数据类与评估入口）
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：注册 `audit-realhw-hdmi-log1080-proxy-focusmag-brightmon` 并接入 `audit-all` `44/44`）
4. [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/README.md)（更新：补充第 44 号审计器 `44/44` 架构说明与 CLI 用法）
5. [`outputs/fx3-firmware-lab/tests/test_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-firmware-lab/tests/test_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon.py)（新增：54 项双模单测）
6. [`reports/2026-11-15-phase211-realhw-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/reports/2026-11-15-phase211-realhw-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/README.md)（新增：本交付报告；上游情报参考 [`Wave-28 README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h232-phase211-44th-auditor-hdmi-log1080-proxy-focusmag-brightmon/reports/2026-11-15-global-sony-wave28-hdmi-log-1080p-hdmionly-4k-proxy-coupled-vault-focusmag-brightmon-intel/README.md)）

---

## 4. 验证命令与实测结果

| 验证项 | 命令（均带 `/usr/bin/python3 -B`） | 实测结果 |
| :--- | :--- | :--- |
| 第 44 号审计器 CLI | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-hdmi-log1080-proxy-focusmag-brightmon --json` | `all_checks_passed: true`, `auditor_index: "44/44"`, 冷扫 `0.070s..0.084s` |
| 总控 `audit-all` (`44/44`) | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room --json` | `all_checks_passed: true`（44 号审计器在线且跨子进程字节级确定性一致） |
| Phase 211 单测（本地 Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon.py` | `Ran 54 tests in 0.508s — OK` |
| Phase 211 单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon.py` | `Ran 54 tests in 0.377s — OK` |
| 固件实验室全量单测（Donor） | `/usr/bin/python3 -B -m unittest discover -s tests -p "test_*.py"` (`Cwd=outputs/fx3-firmware-lab`) | `Ran 1683 tests in 57.783s — OK` |
| 固件实验室全量单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s tests -p "test_*.py"` (`Cwd=outputs/fx3-firmware-lab`) | `Ran 1683 tests in 28.612s — OK (skipped=6)` |
| 全局零字节码/合规门禁 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s`（零 `.pyc` / `__pycache__` / 专有二进制残留） |
