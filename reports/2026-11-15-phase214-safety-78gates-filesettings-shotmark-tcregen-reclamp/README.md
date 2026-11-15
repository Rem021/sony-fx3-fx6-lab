# Phase 214 安全护栏报告：Gates G77 / G78 与统一 `verify-78-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-29 官方 `ILME-FX3 Ver. 7.02` 双硬件安全门禁 `G77`、`G78` 及统一 `78-Gate` 主预检引擎（`G01..G78`）闭环交付**：
   - 新增模块 [`realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py)（将 `G01..G76` 直接委托给 [`evaluate_76gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard.py#L750-L934)，`100%` 保留 `verify-58-gates` 至 `verify-76-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/README.md)。
2. **双模式全量测试与 CLI 实测 100% 通过（实测事实）**：
   - 新增 [`test_phase214_filesettings_shotmark_tcregen_reclamp_78gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/tests/test_phase214_filesettings_shotmark_tcregen_reclamp_78gate_guard.py) 共 **60 项**双模式单元测试（要求 `>=50`），在 `LOCAL_DONOR_O_RDONLY`（`5.794s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.227s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1623/1623` 通过（`92.727s`）**，Clean-Room 合成模式 **`1623` 项通过、`1` 项按设计跳过（`59.830s`）**；
   - CLI `verify-78-gates`：默认离线模式通过 **`75/78`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`78/78`**；
   - BYOF 与字节码卫生审计：`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.06s`（零 `.pyc`、零固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G77 与 Gate G78 技术建模要点

### 2.1 Gate G77：`G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD`
- **`[File Settings]` 5 档 `[File Name Format]` 双卡一致性与 `[File Number]` 计数器规则**：
  - [`verify_file_settings_sdhc_37char_and_shotmark_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L816-L1028) 精确校验 Slot 1 & Slot 2 全局统一的 5 种动态影像文件命名格式（`Standard`、`Cam ID + Reel#`、`Title`、`Date + Title`、`Title + Date`），拒绝任何 Slot 1 / Slot 2 异构命名声明（`BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID`）；
  - 校验 `[File Number]`（`Series` 跨卡递增及 `9999 -> 0001` 回绕、`Reset` 换空卡归 `0001`、以及 `[Series Counter Reset]` 强制重置下一条片段至 `0001`）与 `Cam ID`（`A..Z`）/ `Reel#`（`001..999`）边界。
- **`[Title Name Settings]` 37 字符上限、精确 ASCII 符号白名单与仅向后生效语义**：
  - [`validate_fx3_title_name()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L755-L761) 强校验长度 `1..37` 字符与精确允许字符集（`A-Za-z0-9` + `.-_@!#$%+=^~(),;[]` 共 18 个半角符号），拦截空格、斜杠 `/`、引号、Unicode 字符及任何“追溯重命名卡内既有片段”的伪声明（`BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID`）。
- **SDHC 卡（`<=32GB` FAT32）强制锁定 `[Standard]` 与自定义视频文件夹禁止**：
  - [`resolve_effective_fx3_file_name_format()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L764-L793) 检测到任一卡槽插入 SDHC（或 `<=32GB` `FAT32`）存储卡时强制将 `[File Name Format]` 锁定为 `[Standard]`，拦截一切非 `Standard` 命名请求及自定义视频目录请求（强制 `M4ROOT/CLIP/`，`BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN`）。
- **`[Shot Mark]` `M4ROOT/CLIP/*M01.XML` 旁路持久化、`[Image Jump Setting]` 与 FTP/手机传输过滤**：
  - 校验录制期（`Add Shot Mark1/2`）与回放期（`Add/Delete Shot Mark1/2`）仅写入非实时元数据 `M4ROOT/CLIP/*M01.XML`（零 MP4 视频流篡改，且在 Still 静态照片模式下禁用 -> `BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION`）；
  - [`evaluate_shotmark_jump_and_transfer_match()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L796-L813) 校验回放转盘 `[Image Jump Setting]` 四档（`Shot Mark Only`、`Shot Mark1 Only`、`Shot Mark2 Only`、`No Shot Mark`）以及 FTP `[Target Movie] = [Only Shot Mark Mov.]` 与 Creators' App `[Only Shot Mark]` 过滤条件（`BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION`）。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase214_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L596-L748) 通过 `os.open(..., os.O_RDONLY)` 校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成兜底。

### 2.2 Gate G78：`G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD`
- **`[Time Code Make] = [Regenerate]` 强制 `[Rec Run]` 推进与双卡同录独占读取 **Slot 1** 规则**：
  - [`resolve_tc_regenerate_slot_and_extlk()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L1035-L1066) 与 [`verify_tc_regenerate_extlk_and_reclamp_tally_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L1090-L1281) 强制校验：当 `[Time Code Make] = [Regenerate]` 时，无论 `[Time Code Run]` 菜单停留在 `Free Run` 还是 `Rec Run`，时间码一律按 `[Rec Run]` 推进；且在 `[Simult. Recording]` 双卡同录下独占从 **Slot 1** 读取上一段末尾时间码（拒绝任何引用 Slot 2 末尾时间码的声明 -> `BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION`）。
- **`VMC-BNCM1` 外部时间码 `EXT-LK` 前置三要素与切换即时失锁 + `S&Q` 双重禁用**：
  - `EXT-LK` 严格要求 `Movie` 模式 + `[Time Code Make] = [Preset]` + `[Time Code Run] = [Free Run]`，且一旦切换 `[Time Code Make]`（如切至 `Regenerate`）或切换 `[Time Code Run]` 立即释放 `EXT-LK`（`BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION`）；
  - `S&Q` 模式下同时禁用 `[Time Code Run]` 选择与 HDMI `[Time Code Output]`（`BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT`）。
- **FX3 物理 `[REC Lamp]` 三态后灯 + 顶部 `REC` 键硬件耦合与独立 HDMI 红框 + `[Silent Mode]` 静音硬锁**：
  - [`resolve_fx3_rec_lamp_coupled_tally()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py#L1069-L1087) 严格建模 FX3 三态指示灯：`All On`（前+后+顶全亮）、`Only Front Off`（仅灭前灯，**后置灯与顶部 `REC` 键指示灯保持同步常亮**）、`All Off`（全部物理灯熄灭），拦截任何后灯与顶部 `REC` 键指示灯解耦或伪造四分区的声明；同时独立校验 `[Emphasized REC Display]` 仅在 `[HDMI Info. Display] = [On]` 时向 HDMI 输出红框（`BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION`）；
  - 开启 `[Silent Mode] = [On]` 时硬锁 `[Audio signals] = [Off]`，拦截对焦/自拍蜂鸣器发声或菜单可编辑伪声明（`BLOCKED_G78_SILENT_MODE_AUDIO_SIGNALS_LOCK_VIOLATION`）。

---

## 3. 实测验证矩阵（Measured Facts）

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 214 双模式定向单测（60 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p 'test_phase214_*.py'`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `60/60 OK`（`5.794s`）+ `60/60 OK`（`1.227s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 1623 tests in 92.727s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests` | `Ran 1623 tests in 59.830s — OK (skipped=1)` |
| CLI `verify-78-gates`（离线默认） | `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-78-gates` | `verified=75/78`（`VERIFIED_75_OF_78_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-78-gates --simulate-bench-dry-run` | `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-78-gates --simulate-bench-dry-run`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=78/78`（`VERIFIED_ALL_78_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| 仓库 BYOF 与字节码卫生检查 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.06s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase214_filesettings_shotmark_tcregen_reclamp_78gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/outputs/fx3-safety/tests/test_phase214_filesettings_shotmark_tcregen_reclamp_78gate_guard.py)
6. [`reports/2026-11-15-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h236-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/reports/2026-11-15-phase214-safety-78gates-filesettings-shotmark-tcregen-reclamp/README.md)
