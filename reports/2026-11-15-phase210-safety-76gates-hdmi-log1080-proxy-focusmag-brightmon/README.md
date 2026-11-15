# Phase 210 安全护栏报告：Gates G75 / G76 与统一 `verify-76-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-28 官方 `ILME-FX3 Ver. 7.02` 双硬件安全门禁 `G75`、`G76` 及统一 `76-Gate` 主预检引擎（`G01..G76`）闭环交付**：
   - 新增模块 [`realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py)（将 `G01..G74` 直接委托给 [`evaluate_74gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py#L1943-L2282)，`100%` 保留 `verify-58-gates` 至 `verify-74-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/README.md)。
2. **双模式全量测试与 CLI 实测 100% 通过（实测事实）**：
   - 新增 [`test_phase210_hdmi_log1080_proxy_focusmag_brightmon_76gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/tests/test_phase210_hdmi_log1080_proxy_focusmag_brightmon_76gate_guard.py) 共 **56 项**双模式单元测试，在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模式下合并耗时 **`3.009s` 全绿通过**；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1563/1563` 通过（`90.231s`）**，Clean-Room 合成模式 **`1563` 项通过、`1` 项按设计跳过（`62.963s`）**；
   - CLI `verify-76-gates`：默认离线模式通过 **`73/76`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式通过 **`76/76`**；
   - BYOF 与卫生审计：`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`（零 `.pyc`、零固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G75 与 Gate G76 技术建模要点

### 2.1 Gate G75：`G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD`
- **`[HDMI Output Settings]` 双模式与 `[4K Output Set.(HDMI Only)]` 六档精确枚举**：
  - 校验 `[Rec. Media dur HDMI Output]`（`[On]` vs `[Off(HDMI Only)]`）、`[Output Resolution]`（`Auto / 2160p / 1080p / 1080i`）以及仅在 `[Off(HDMI Only)]` 解锁的 6 档 10-bit 4K 输出（`59.94p 10bit`、`50p 10bit`、`29.97p 10bit`、`25p 10bit`、`23.98p 10bit`、`24.00p 10bit`，其中 `24.00p 10bit` 强校验 `[QFHD 24p]` 系统使能）。
- **`[Log Shooting]` 与 `PPLUT1..PPLUT4` 非 RAW `1080p` HDMI 硬件降档规则**：
  - 当 `[Rec. Media dur HDMI Output] = [On]` 且 `[RAW Output] = [Off]` 时，只要开启 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）或选用 `PPLUT1..PPLUT4`，`ILME-FX3 Ver. 7.02` 硬件管线强制将 HDMI 输出分辨率降为 `1080p`，Fail-Closed 拦截任何“机内录卡同时输出非 RAW 4K Log/PPLUT HDMI”的错误假设（`BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM`）。
- **`[Off(HDMI Only)]` 禁机内录卡、OSD/反挤压抑制与相机内置 LCD 黑屏互锁**：
  - `[Off(HDMI Only)]` 下强制 `internal_card_recording_active == False`；
  - `[Off(HDMI Only)]` 或 `[RAW Output] = [On]` 下自动强制 `[HDMI Info. Display] -> [Off]` 且抑制 HDMI `[De-Squeeze Display]`；
  - 当 `[HDMI Info. Display] = [On]` 时，强制校验机身内置 LCD 黑屏关闭（`camera_lcd_panel_blanked == True`）。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase210_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py#L371-L492) 严格通过 `os.open(..., os.O_RDONLY)` 校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（实测冷读 `< 0.03s < 0.15s`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 无固件确定性回退。

### 2.2 Gate G76：`G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD`
- **`[Proxy Settings]` 精确 2 格式 / 3 档位表与高帧率 / HDMI-Only 硬件截止**：
  - 仅允许 `XAVC HS HD`（`1920x1080` 10-bit HEVC `16M` / `9M`，最高 `59.94p/50p`）与 `XAVC S HD`（`1280x720` 8-bit AVC `6M`，最高 `59.94p/50p`）；
  - 在普通视频 `119.88p / 100p`、`S&Q` `119.88p / 100p` 或传感器帧率 `>= 100fps / 120fps / 200fps / 240fps`、以及 `[Off(HDMI Only)]` 下 Fail-Closed 阻断 `[Proxy Recording] = [On]`。
- **`M4ROOT/CLIP/` + `M4ROOT/SUB/` 原子耦合保险库与机内代理回放禁止**：
  - 严禁机内单侧删除或单侧保护主片/代理（强制 `clip_deleted == sub_proxy_deleted` 且 `clip_protected == sub_proxy_protected`），并阻断任何机内直接回放 `M4ROOT/SUB/` 代理片的伪声明。
- **`[Focus Magnifier]` × `[Auto Magnifier in MF]` × `[Bright Monitoring]` 三重监看互锁**：
  - 视频模式 `[Initial Focus Mag.]` 严格锁定 `x1.0 / x4.0`（拍照 FF `x1.0 / x2.1`、APS-C/S35 `x1.0 / x1.5`），视频拍摄期间硬禁 `[Auto Magnifier in MF]` 对焦环自动放大，放大监看期间抑制 `[Marker Display]` 且保持录制流无裁切；
  - `[Focus Magnifier]` / `[Auto Magnifier in MF]` 激活期间硬锁拒绝切换 `[Bright Monitoring]` 自定义键，且 `[Bright Monitoring]` 在离开 `P/A/S/M`、离开 `MF` 或关机时自动取消，激活时强制 `[Live View Display] = [Setting Effect OFF]`。

---

## 3. 实测验证矩阵（Measured Facts）

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 210 双模式定向单测（56 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_phase210_*.py" -v`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `56/56 OK` × 2（共 `3.009s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1563 tests in 90.231s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1563 tests in 62.963s — OK (skipped=1)` |
| CLI `verify-76-gates`（离线默认） | `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-76-gates` | `verified=73/76`（`VERIFIED_73_OF_76_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-76-gates --simulate-bench-dry-run` | `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-76-gates --simulate-bench-dry-run` | `verified=76/76`（`VERIFIED_ALL_76_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase210_hdmi_log1080_proxy_focusmag_brightmon_76gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/outputs/fx3-safety/tests/test_phase210_hdmi_log1080_proxy_focusmag_brightmon_76gate_guard.py)
6. [`reports/2026-11-15-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h231-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/reports/2026-11-15-phase210-safety-76gates-hdmi-log1080-proxy-focusmag-brightmon/README.md)
