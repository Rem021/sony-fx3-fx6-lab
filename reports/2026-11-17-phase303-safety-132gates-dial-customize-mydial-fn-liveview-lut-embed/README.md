# Phase 303（Task H356）工程交付报告：Wave-56 硬件安全闸门 G131 与 G132 暨统一 `132/132` 主预检引擎（`verify-132-gates`）

- **日期**：`2026-11-17`
- **任务标识**：`H356` · Phase `303` · Wave `56`（`outputs/fx3-safety` `132`-Gate Milestone）
- **核心结论（Conclusion First）**：
  1. **Wave-56 硬件安全闸门 `G131` 与 `G132` 暨 `132/132` 统一预检引擎已全部闭环落地并验证通过**：新增守护模块 [`realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py)（schema `realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard_v1`），在 `100%` 向后兼容并委托 `G01..G130` 给 [`evaluate_130gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.py) 的基础上，实现了 `G131`（`768` 状态穷举）、`G132`（`864` 状态穷举）与统一 [`evaluate_132gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py)（CLI `verify-132-gates`），并在 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/__init__.py) 导出最高阶 `evaluate_132gate_preflight` 供 Milestone 295 自动发现。
  2. **离线预检与 Dry-Run 实测结果**：
     - 离线默认模式：`129/132` 通过（`VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0`，仅待物理 Tier-0 备份回执 `G10..G12`），`LOCAL_DONOR_O_RDONLY` 模式下 `11` 份 Wave-56 本地 donor 校验实测耗时 `0.004929s`（`< 0.20s` 预算）、`raw_firmware_bytes_leaked == 0`。
     - `--simulate-bench-dry-run` 预演模式：`132/132` 通过（`VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP`），所有物理写入与热连接红线硬锁为 `False`、`usb_packets_transmitted == 0`。
     - Milestone 295 联动实测：`make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` 均动态发现 `evaluate_132gate_preflight` 并输出 **`gate124=129/132`**、`status=OK`。
  3. **测试与洁净卫生闭环**：[`test_realhw_dial_customize_mydial_fn_liveview_lut_embed_132gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/tests/test_realhw_dial_customize_mydial_fn_liveview_lut_embed_132gate_guard.py) 共 `86` 项单元测试在 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 三模式全部通过；`outputs/fx3-safety` 全量发现共 **`3,579` 项测试全部通过**；`make clean-audit` 与 `--clean-only` 全部绿色无残留。

> 注：下文严格区分**实测事实**（已运行命令输出、UXC/ELF 只读切片与单测计数）与**工程推断**（物理真机未接入前的实机硬件保护行为模型）。

---

## 1. 交付产物与严格文件所有权（6/6 文件）

| # | 变更类型 | 文件路径 | 核心职责 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) | Phase 303 Wave-56 只读 Donor 审计（`55` FX3 切片 + `14` FX6 切片 + `11` 份产物）、`G131`（`768` 状态矩阵）、`G132`（`864` 状态矩阵）与 `evaluate_132gate_preflight` |
| 2 | EDIT | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/__init__.py) | 导出 G131/G132、`Master132GateReport` 与 `evaluate_132gate_preflight` 全量公开符号，保持 `G01..G130` 兼容 |
| 3 | EDIT | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/__main__.py) | 注册 `verify-dial-customize-mydial-fn-guard`（别名 `verify-g131-dial-customize-mydial-fn`）、`verify-liveview-grid-lut-embed-guard`（别名 `verify-g132-liveview-grid-lut-embed`）与 `verify-132-gates`；全部 `argparse help=` 字面 `%` 转义为 `%%` |
| 4 | EDIT | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/README.md) | 新增 **Section 66** 文档化 Phase 303 Wave-56 G131/G132 与 `verify-132-gates` 契约 |
| 5 | NEW | [`test_realhw_dial_customize_mydial_fn_liveview_lut_embed_132gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/tests/test_realhw_dial_customize_mydial_fn_liveview_lut_embed_132gate_guard.py) | `86` 项双模单元测试（`>= 84` 要求），使用 `sys.executable` 与 `GITHUB_ACTIONS=='true'` `15.0s` CI 时限余量 |
| 6 | NEW | [`README.md` (本报告)](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/reports/2026-11-17-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/README.md) | 中文结论先行工程交付报告 |

---

## 2. Wave-56 安全闸门实现要点（实测事实 vs 工程推断）

### 2.1 只读本地 Donor 审计（`audit_phase303_donor_contracts`，实测事实）

- 严格通过 `os.open(..., os.O_RDONLY)` + 有界 `os.pread` 审计 `11` 份本地 donor 文件，并在无本地 donor 或 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动进入 `CLEAN_ROOM_SYNTHETIC` 模式：
  - `FX3 appFw.so`（`79,015,712 B`，`55` 个 Wave-56 切片，固定切片 SHA-256 `a4da108c5081286aa7cfe741d86e2c708c8558ac0662a16d4e81899398b25269`）。
  - `FX6 appFw.so`（`50,520,424 B`，`14` 个 Wave-56 切片，固定切片 SHA-256 `656ba14c5ea7dfb6828b71ec1350471b701149d760de8b0a8c6fc2b9103c5fd5`）。
  - 四语言 `_f.uxc` 包（`string_english_f.uxc`、`string_simplifiedchinese_f.uxc`、`string_traditionalchinese_f.uxc`、`string_japanese_f.uxc`）+ `string_english.uxc` + `string_english_g.uxc` + `FX3-CX95900_ALLLANG-Backup.bin` + `FX6 string_english.uxc` / `string_english_2.uxc`。
  - 实测本地耗时 **`0.004929s`**（远低于 `0.20s` 预算），`raw_firmware_bytes_leaked == 0`。

### 2.2 Gate `G131`：`[Dial Customize]` 5 项真值、`3`-Dial 硬件拓扑、`My Dial 1..3` 与 `Fn 12+12` 拆分

1. **`[Dial Customize]` 5 项真值与 `Initialize`-only 策略（实测事实）**：[`verify_dial_customize_mydial_fn_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) 强制 `MENU -> (Setup) -> [Dial Customize]`（`_g.uxc 0x62ed`）在 `FX3 Ver. 7.02` 仅暴露 `5` 项（`Custom Key/Dial Set.`、`My Dial Settings`、`Av/Tv Rotate` [`Normal`/`Reverse`]、`Function Ring(Lens)` [`Power Focus`/`APS-C/Super 35 mm / Full Frame`]、`Lock Operation Parts` [`Off`/`Multi-Selector Only`/`Dial + Wheel`/`All`]），全部在 `[Camera Settings Reset]` 下保留、仅 `[Initialize]` 重置；同时拦截旧版 `Dial Setup`/`Dial/Wheel Setup`/`Dial / Wheel Lock` 及 `VAL_setting_function_ring_FUNCTION_RING_INVALID`。
2. **物理 3 拨盘防越界（实测事实 + 工程推断）**：FX3 仅具备 `Front Dial`、单个 `Rear Dial` 与 `Control Wheel`；针对继承自 4 拨盘 Alpha 机身的休眠 `Rear Dial L` / `Rear Dial R`（`_f 0x6a5c`/`0x680d`、`BKID_APP_mydial_rear_dial_{left,right}_setting_list0..2`、`DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO`）一律 fail-closed 拦截并返回 `EOPNOTSUPP`（`errno = 95`）。
3. **`My Dial 1..3` 与 `Fn Menu 12+12` 隔离 + FX6 对比（实测事实）**：验证 `My Dial 1..3` 共享 NVRAM 库支持 Still/Movie 独立 `Hold`/`Toggle`/`1->2->3` 呼出（自动跳过全 `Not set` 空槽，并在呼出期间临时覆盖解除 `Lock Operation Parts`），`Fn Menu Settings` 严格拆分 `12 Still + 12 Movie` 且全 `Not set` 时阻断呼出（`_f 0x6220`），并与 `ILME-FX6`（`Multi Function Dial`、`Grip Dial`、`Handle Dial`、`IRIS Dial`、`ND Dial`、`Status Screens`、`Direct Menu`）交叉隔离；[`compute_dial_customize_mydial_fn_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) 穷举 **`768`** 状态全部满足不变量。

### 2.3 Gate `G132`：`[Live View Display Set.]` 3 项、`[Grid Line]` HDMI 隔离与 LUT 内嵌 / `PPLUT1..4` + `Slot-1` 防火墙

1. **Still 专属 `[Live View Display Set.]` 3 子项与 `[Bright Monitoring]` 覆写（实测事实）**：[`verify_liveview_grid_lut_embed_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) 限定该菜单（`_f 0x6429`）仅 Still 可用（Movie/`S&Q` 阻断），开启 `[Bright Monitoring]` 时强制 `Live View Display = Setting Effect OFF`；仅 `Frame Rate Low Limit` 会被 `[Camera Settings Reset]` 重置，而 `Live View Display` 与 `Exposure Effect` 保留。
2. **`[Grid Line]` Clean-HDMI 隔离 vs FX6 自定义 PNG（实测事实）**：`Grid Line Display` 与 `Grid Line Type`（`Rule of 3rds Grid` / `Square Grid` / `Diag. + Square Grid`）为 `Initialize`-only，且在 `HDMI Info. Display = Off`（含 RAW 输出/`Off(HDMI Only)`）时完全与 HDMI 清洁输出隔离；同时拦截休眠 FX6 自定义 PNG 网格（`BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`、`GOLDEN_RATIO_GRID`）与 FX6 `Marker`（`80/90/92.5/95%`）串扰。
3. **`[Manage User LUTs]` / `[Embed LUT File]` vs `PPLUT1..4` 与 `Slot-1` Tier-0 保险库防火墙（实测事实 + 工程推断）**：
   - 区分 `[Manage User LUTs]`（`User1..16`，`17pt`/`33pt` `.cube`，SD/SDXC `/Private/Sony/PRO/LUT` vs CFexpress `/Sony/PRO/LUT`，只读 `O_RDONLY` 导入不写 `Slot 1`）、`[Embed LUT File]`（位于 `[Image Quality/Rec] -> [Log Shooting Setting]` 而非 `[Color/Tone]`；`SD/SDHC` 下依 `_g 0x61a0` 硬件锁死为 `Off`；仅在视频容器内嵌 3D LUT 元数据、保留 `S-Log3` 像素且不生成外置 sidecar），以及 `PPLUT1..4`（不可逆像素烘焙，且被 `[Camera Settings Reset]` 与 `[Initialize]` 双重重置）。
   - 当 `Slot 1` 受写保护或挂载 Tier-0 恢复保险库时，任何针对 `Slot 1` 的写操作（`Make Cube Folder`、`Write Cube/Sidecar`、`Record Embed LUT File`、`Record PPLUT`）一律 fail-closed 拦截并返回 **`EROFS` (`30`)** 或 **`EBUSY` (`16`)**，`slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`（而 `Import User LUT` 与 `Slot 2` 写操作可安全放行）；[`compute_liveview_grid_lut_embed_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h356-phase303-safety-132gates-dial-customize-mydial-fn-liveview-lut-embed/outputs/fx3-safety/fx3_safety/realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.py) 穷举 **`864`** 状态全部通过。

---

## 3. 全量实测验证矩阵（Verification Matrix，实测事实）

| 检查项 | 执行命令 / 范围 | 实测结果 |
| :--- | :--- | :--- |
| Phase 303 单测（本地 Donor） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest -v outputs/fx3-safety/tests/test_realhw_dial_customize_mydial_fn_liveview_lut_embed_132gate_guard.py` | **86/86 OK**（`9.740s`） |
| Phase 303 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest ...` | **86/86 OK**（`2.917s`） |
| Phase 303 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest ...` | **86/86 OK**（`2.819s`） |
| `verify-132-gates`（Donor 离线） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-132-gates --summary --json` | **`129/132`** (`VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0`, `G131=STATUS_VERIFIED_G131`, `G132=STATUS_VERIFIED_G132`, `leaked=0`) |
| `verify-132-gates`（Donor Dry-Run） | `... verify-132-gates --simulate-bench-dry-run --summary --json` | **`132/132`** (`VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP`, `ready_attach=False`, `usb_tx=0`) |
| `verify-132-gates`（Clean-Room 离线 & Dry-Run） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... verify-132-gates [--simulate-bench-dry-run] --summary --json` | **`129/132`** 离线 / **`132/132`** Dry-Run（`CLEAN_ROOM_SYNTHETIC`） |
| `outputs/fx3-safety` 全量发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | **3,579/3,579 OK**（`162.387s`） |
| Milestone 295 联动（Donor + Clean-Room） | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **PASS**（动态发现并输出 **`gate124=129/132`**, `status=OK`, `leaked=0`） |
| 仓库洁净与无 `.pyc` 审计 | `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only` & `make clean-audit` | **ALL GREEN**（`CLEAN`, `0.03s` / `0.60s`） |

---

## 4. 安全红线确认（实测锁定状态）

- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False` · `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` · `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False` · `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `HUMAN_HARDWARE_ATTACH_TOKEN = False` · `CROSS_MODEL_FLASH_AUTHORIZED = False`
- `USB_PACKETS_TRANSMITTED = 0` · `PHYSICAL_USB_PACKETS_EMITTED = 0` · `RAW_FIRMWARE_BYTES_LEAKED = 0`
- **硬件禁令遵守确认**：未触碰任何 `outputs/fx3-recovery-adapter`、`outputs/fx3-vm`、`outputs/fx6-*`、`outputs/fx3-firmware-lab`、`Makefile` 或 `8768` 端口，也未对物理 FX3 执行任何烧录或在线写入操作。
