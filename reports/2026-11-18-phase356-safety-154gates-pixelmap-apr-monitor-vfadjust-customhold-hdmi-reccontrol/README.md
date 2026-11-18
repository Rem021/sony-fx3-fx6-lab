# Phase 356（Task H446，Wave 67）：`154/154` 实机硬件安全门控闭环报告（`G153` + `G154` / `verify-154-gates`）

- **日期**：`2026-11-18`
- **任务 / 波次**：`Task H446` · `Phase 356` · `Wave 67`
- **硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `ilc/2210`, `0x0502`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `5-024-458-18`, `PRODUCT_MODEL_CHAPLIN`）
- **硬件安全态势**：严格只读本地 donor 分析与模拟台架预检（`overall_ready_for_hardware_attach = False` · `hardware_live_attachment_authorized = False` · `cross_model_flash_authorized = False` · `persistent_emmc_writes_authorized = False` · `el3_payload_transmit_authorized = False` · `spi_nor_write_authorized = False` · `usb_packets_transmitted = 0` · `raw_firmware_bytes_leaked = 0`）。
- **正文合规声明**：以下严格区分 **`实测事实`**（来自只读 `os.O_RDONLY` / `os.pread` 切片与 SHA-256 校验、Wave-67 官方文档及单元测试实跑输出）与 **`推断`**（Slot-1 Tier-0 只读保险库、`EROFS=30` 运行时拦截边界及台架风险推论）。

---

## 1. 交付产物与模块化设计（`实测事实`）

1. **核心安全护栏与 `154/154` 门控引擎**：
   - [`realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h446-phase356-safety-154gates-pixelmap-apr-monitor-vfadjust-customhold-hdmi-reccontrol/outputs/fx3-safety/fx3_safety/realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.py)
   - 向后兼容复用 `evaluate_152gate_preflight()` 托管 `G01..G152`，新增 `G153` 与 `G154` 升级统一预检器 `evaluate_154gate_preflight()`（同步提供 `evaluate_154_master_safety_gates`、`run_154_gate_preflight`、`verify_real_hardware_154gate_readiness` 别名与 `Master154GateReport` 数据结构），支持 [`realhw_milestone349_master_gate.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h446-phase356-safety-154gates-pixelmap-apr-monitor-vfadjust-customhold-hdmi-reccontrol/outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone349_master_gate.py) P1 自动发现 `N = 154`（离线 `151/154`，干跑 `154/154`）。
2. **包导出与 CLI 注册**：
   - [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h446-phase356-safety-154gates-pixelmap-apr-monitor-vfadjust-customhold-hdmi-reccontrol/outputs/fx3-safety/fx3_safety/__init__.py) 完整导出 Phase 356 符号至 `__all__`（保留 `G01..G152` 全部旧导出）。
   - [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h446-phase356-safety-154gates-pixelmap-apr-monitor-vfadjust-customhold-hdmi-reccontrol/outputs/fx3-safety/fx3_safety/__main__.py) 注册 `verify-pixelmap-apr-monitor-vfadjust-guard`（别名 `verify-g153-pixelmap-apr-monitor` / `verify-g153`）、`verify-recall-custom-hold-hdmi-reccontrol-guard`（别名 `verify-g154-customhold-hdmi-reccontrol` / `verify-g154`）与 `verify-154-gates`（已规避任何 argparse `help=` 未转义 `%` 问题）。
   - [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h446-phase356-safety-154gates-pixelmap-apr-monitor-vfadjust-customhold-hdmi-reccontrol/outputs/fx3-safety/README.md) 新增第 77 节完整文档。
3. **4 模式单元测试集**：
   - [`test_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_154gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h446-phase356-safety-154gates-pixelmap-apr-monitor-vfadjust-customhold-hdmi-reccontrol/outputs/fx3-safety/tests/test_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_154gate_guard.py)（共 `104` 项测试，均在正常、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 及 `mock(work_root=None)` 4 模式下验证通过，且 `test_84` 使用 `assertGreaterEqual(max(nums), 154)` 保持前向兼容）。

---

## 2. Gate `G153` 与 `G154` 核心约束对照

### 2.1 Gate `G153`：`PIXELMAP_APR_MONITOR_ZERO_EVF_VS_FX6_VF_ADJUST_GUARD`

| 维度 | `实测事实`（ELF / UXC / 官方基线） | 门控动作与错误码 |
| :--- | :--- | :--- |
| **`[Auto Pixel Mapping]` 双层 Reset 分裂** | `Setup -> [Setup Option] -> [Auto Pixel Mapping]`（`_f 0x7734`）默认 `On`、**抗 Reset（仅 `[Initialize]` 还原）**；`Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Target Function Settings] -> [Auto Pixel Mapping]`（`_f 0x64e7`）默认 `Off`/`Not Target`、**可 Reset**。后者若保持 `Off`，即便 `[Silent Mode] = On`，关机自动映射仍通过 `vdf_set_shutter_mute_by_pixel_mapping` 发出机械快门声 | 误判“仅开 Silent Mode 即静音关机映射”或误认 Setup 项可被 Reset 均返回 `EINVAL=22`；384 态矩阵全量校验 |
| **手动 `[Pixel Mapping]` & Sony 拼写错字** | `_f 0x61f7` 联动 `INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING` 及镜头盖遮光校验（`_g 0x63f1` / `0x60e7`）并自动重启；`PRM_HAITA_*pixel_map*` 对 USB/流式传输/温度阻断命中 **`0`** 条；ELF 实证拼写错字 `BKID_APP_setting_notification_for_pixel_mappinng` 与 `BKID_APP_pixel_mapping_excuted_status`；`Pixel Map. Notification` / `Shutter When Pwr OFF` 在 FX3 均不暴露 | 未遮光/低电触发手动映射或伪造 `PRM_HAITA` 阻断绑定返回 `EINVAL=22`；伪造 FX3 暴露通知项返回 `EOPNOTSUPP=95` |
| **FX6 `APR` vs 休眠 `ABB`** | FX6 暴露 `Technical > APR`（黑布遮光 `ns1 0x3324` 与 `PIXEL_MAPPING_RESULT_{LIGHT_DETECTED,INVALID_TEMPERATURE}`）；CMOS 机型的 `auto_black_balance`（`ABB`）仅休眠符号未暴露 | 遮光/温控异常返回 `EINVAL=22`；伪造 FX6 `ABB` 菜单暴露返回 `EOPNOTSUPP=95` |
| **`Setup -> [Monitor]` 3 项 vs `[Finder/Monitor]` 辟谣** | FX3 严格使用 **`Setup -> [Monitor]`**（非 `[Finder/Monitor]`），全 3 项均**抗 Reset**：`[Monitor Brightness]`（`Manual -2..+2` / `Sunny Weather`）、`[Display Quality]`（`Standard` / `High`，高温强制锁回 `Standard`）、`[Monitor Flip Direction]`（`Auto` / `Horizontal Flip` / `180 Degree Flip` / `No Flip`）；4 个 EVF 符号（`Finder/Monitor Sel.`、`Viewfinder Bright.`、`Viewfinder Color Temp.`、`Finder Frame Rate`）暴露数为 **`0`** | 伪造 `[Finder/Monitor]` 或 4 个 EVF 菜单返回 `EOPNOTSUPP=95`；高温解锁 `High` 或 Reset 篡改 返回 `EINVAL=22` |
| **FX6 `VF Setting` / `VF Adjust`** | FX6 暴露 `Monitoring > VF Setting`（`Brightness 1..15` def `8`, `Color Mode` `Color`/`B&W`）、`VF Adjust` 按键及物理 `MIRROR` 开关（`Off/B/T/ROT`），无 `Backlight/Contrast/Chroma/Color Temp.` 子菜单 | 伪造 4 级 `VF Adjust` 子菜单返回 `EOPNOTSUPP=95` |

### 2.2 Gate `G154`：`RECALL_CUSTOM_HOLD_11PARAM_STILL_VS_FX6_PUSH_AND_HDMI_SLOT1_REC_CTRL_VAULT_GUARD`

| 维度 | `实测事实` vs `推断` | 门控动作与错误码 |
| :--- | :--- | :--- |
| **仅限静态 `P/A/S/M` `[Recall Custom hold 1..3]`** | **`实测事实`**：`_f 0x60b4/0x7581/0x725b`（抗 Reset 仅 `Initialize` 清除，存 `CAMSET*.DAT`）严格仅限 Still `P/A/S/M`，Movie/`S&Q`/iAuto 不可用；`is_checked_recall_custom_hold0..10` 精确 **11** 项（含排除 Self-timer 的 `drive_mode`），`shoot_set_registration_white_balance` 命中 **`0`**（无独立 White Balance 勾选框） | Movie/`S&Q`/iAuto 下调用或声称存在独立 `White Balance` 勾选框返回 `EOPNOTSUPP=95`；Drive 含 Self-timer 或 Reset 篡改返回 `EINVAL=22` |
| **FX6 `Push AF/AGC/Iris` & 休眠 `High/Low Key`** | **`实测事实`**：FX6 用单维 Push 键替代，其中 `Push AGC` 在 `Cine EI`/`Bokeh Control=On` 禁用，`Push Auto Iris` 在 `MANUAL` 镜头或 `Bokeh Control=On` 禁用；`High/Low Key` 在 FX6 仅休眠字面量未开放 | `High/Low Key` 返回 `EOPNOTSUPP=95`；违反 `Push AGC`/`Push Auto Iris` 互锁返回 `EINVAL=22` |
| **`[External Output]` HDMI 门控与拼写错字** | **`实测事实`**：`Setup -> [External Output]` 全项抗 Reset；`[REC Control] = On` 硬前置 `[Time Code Output] = On` 与兼容外录机；`Log`/`PPLUT1..4` + `Rec. Media = On` + `RAW = Off` 降级 `1080`；`24.00p` 切换需重启与回放隔离；`[HDMI Info. Display] = On` 使机身 LCD 黑屏并在 `Off(HDMI Only)`/`RAW = On` 时强制关；ELF 拼写错字 `BKID_APP_setting_ctrl_for_hmdi` 与 `PRM_HAITA_hdmi_4k_outpute_apsc_restriction`；休眠 `4K/2K Output`/`24p/60p Output` 在 FX3 均 `0` 命中 | 缺 `TC Output = On`、强行在 `Log`/`PPLUT` 输出 4K、`24.00p` 免重启、`S&Q` 解锁 `Off(HDMI Only)`/`TC On` 返回 `EINVAL=22`；休眠 `4K/2K` 或 `24p/60p` 返回 `EOPNOTSUPP=95` |
| **`Rec. Media dur HDMI Output = On` `Slot 1` 防火墙** | **`推断`（基于实测 ELF 联动 `PRM_HAITA_*_slot1_*_rec_media_during_hdmi_output` 推导台架行为）**：`Rec. Media dur HDMI Output` 出厂默认 `On` 且 `S&Q` 锁死 `On`；当录制指向 Tier-0 只读 `Slot 1` 恢复保险库时，若放行写穿 `M4ROOT/CLIP/*.MP4` 与 `AVF_INFO` 将污染恢复盘 | 对指向 `Slot 1` 且生效 `Rec. Media = On`（含 `S&Q` 强锁）的录制写请求及显式写请求强制 fail-closed 返回 **`EROFS (errno 30)`**，实测 `slot1_data_sector_writes = 0`、`emmc_nflasha_write_count = 0` |

---

## 3. 只读 Donor SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

11 份 Wave-67 donor 资产通过 `os.open(..., os.O_RDONLY)` + `os.pread` 切片在 `< 0.20s` 预算内全量验签（`FX3 appFw.so` 31 切片 SHA-256 = `5f5d529a6d4aaca1db2a49f9d4779c89e32a9f77d014d9bb4eed335c169e177f`，`79,015,712 B`；`FX6 appFw.so` 10 切片 SHA-256 = `9ca8e8727fa88fa0a0dae823b9f180cfb1bc9d4c3c23d3c78cbbac6f679e14d1`，`50,520,424 B`；另有 `FX3-CX95900_ALLLANG-Backup.bin`、FX3 4 语 `_f`/英 `.uxc`/`_g.uxc`、FX6 `string_english.uxc`/`string_english_2.uxc`）。

---

## 4. 全量验证收口结果（`实测事实`）

1. **4 模式单元测试**（`test_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_154gate_guard.py`）：
   - 正常模式（`10.435s`）、`FX3_CLEAN_ROOM_TEST=1`（`6.487s`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（`6.421s`）、模拟 `work_root=None` 均 **`104/104`** 全部通过。
2. **全量 `outputs/fx3-safety/tests` 发现**：
   - 正常模式：`4,613` 项全量通过（`Ran 4613 tests in 295.103s`，`OK`）。
   - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`4,613` 项全量通过（`Ran 4613 tests in 155.819s`，`OK (skipped=10)`；新增 `104` 项 Phase 356 测试无一跳过，全数通过）。
3. **双模式 `verify-milestone-349` 自动发现**：
   - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-349`：`LOCAL_DONOR_O_RDONLY`（`milestone349_sha256=9e7f144afb7c4b10...`）与内建 `--force-clean-room`（`20e616305c6a1d1e...`）均实测 `pillars=6/6`、`gate148=151/154`、`leaked=0`、`usb_tx=0`、`ready_attach=False`。
   - `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-349`：实测 `CLEAN_ROOM_SYNTHETIC`（`6df964958111ea29...` / `80d161ded6bcddbb...`）`pillars=6/6`、`gate148=151/154`、`leaked=0`。
4. **工作区洁净审计**：
   - `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 返回 `=== Clean-Room Audit: ALL GREEN in 0.04s ===`。
