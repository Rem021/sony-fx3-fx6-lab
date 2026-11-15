# Phase 203（第 42 号固件审计器 `42/42`）交付报告：`ILME-FX3` (`Ver. 7.02`) `BIG6` `[Home (Lower Left)]` 零物理电子可变 ND 驱动边界、Slot-1 `CAMSET` 双介质路径分叉及 `VMC-BNCM1` 机身直连单向 `TC IN` / HDMI `TC OUT` 审计器

## 1. 核心结论

1. **第 42 号审计器 (`42/42`) 落地闭环**：已在 [`realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor.py) 完成 `PHASE_203_SCHEMA` (`203.0.0`) 实现，完整导出至 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)，并在 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) 注册独立子命令 `audit-realhw-big6-noend-camset-vmcbncm1` 及总控 `audit-all` (`42/42`)，同步更新 [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/README.md)。
2. **有界 `os.O_RDONLY` + `os.pread` 极速扫描与洁净室双模一致性**：本地真机 Donor 冷启动扫描实测耗时 **`0.119s`**（严格满足 `< 0.15s` 预算，进程内 `_DONOR_SCAN_CACHE_P203` 二次命中 `< 1ms`）；`CPAPP-B.BIN` / `cpapp-b.bin` 严格采用头部 `768 KiB` + 尾部 `6 MiB` 有界读取，无任何整镜像 `>50 MiB` 冗余扫描，`raw_firmware_bytes_leaked == 0`，确定性报告哈希 `2ad84faf33f0ad7c10a90134c6c0f5d108063ce8813c86af3a0ee65226466fad`。
3. **全量双模回归 `100%` 通过**：新增 [`test_realhw_big6_noend_camset_slot1_and_vmcbncm1.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/tests/test_realhw_big6_noend_camset_slot1_and_vmcbncm1.py) **56 项**双模单测（Donor 模式 `0.508s`、洁净室模式 `0.389s`）；`outputs/fx3-firmware-lab/tests` 全量 **1,575 项**单测在本地 Donor 模式（`58.045s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式（`29.067s`）均 `100%` 通过。

---

## 2. 四大实证支柱（实测二进制证据 vs 建模边界）

### Pillar 1 — `ILME-FX3` (`Ver. 7.00+/7.02`) `Home` (`BIG6`) 精确 6 宫格拓扑与零物理内置 e-ND 硬件边界
- **实测二进制事实（`O_RDONLY`）**：
  - 原厂 `FX3 Ver. 7.02` (`appFw.so` `79,015,712 B` + `string_english_f.uxc` `373,820 B`) 与 `FX6 Ver. 6.01` (`appFw.so` `50,520,424 B` + `string_english.uxc` `118,208 B`) 均包含 `N5model31setting_movie_home_lower_left_tE`、`set_movie_home_lower_left`、`MOVIE_HOME_LOWER_LEFT_APERTURE`、`MOVIE_HOME_LOWER_LEFT_ND_FILTER`、`GUIDE_BIG6_FPS_SELECT`；`FX3 7.02` 另具 `BKID_APP_setting_movie_home_lower_left`、`26view_tp_button_01_for_big6`、`BKID_APP_setting_nd_filter_manual_set`（`get_fraction_nd_filter_manual_set`）与 `EVENT_FUNC_CUSTOM_FPS_FIXED_VARIABLE_SELECT_ON`。
  - `FX6 Ver. 6.01` 独有的 7 项物理电机/液晶可变 ND 驱动符号（`BKID_APP_VARIABLE_ND_CONT`、`PID_SET_VARIABLE_ND_VALUE`、`PID_SET_VARIABLE_ND_ROTARY_ENCODER`、`PID_GET_VARIABLE_ND_STORED_VALUE`、`INFRA_NOTIFY_VARIABLE_ND_FILTER_VALUE`、`FUNC_set_auto_nd_filter`、`FUNC_set_push_auto_nd_filter`）在 `FX6 6.01` 命中 `>= 1`，而在 `FX3 7.02` `appFw.so` 与 `CPAPP-B.BIN` 中命中数均为 **`0`**。
- **拓扑与 Stage-B 护栏建模**：
  - 精确校验 `[Mode Settings] = [Fixed/Variable]` 与 `[Custom Key/Dial Set.] -> [HOME]` 双前置门禁，以及 6 宫格 + 第 7 状态栏拓扑（`1: FPS`、`2: ISO / Base ISO`、`3: Shutter Speed / Shutter Angle`、`4: Aperture / ND Filter` via `MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]`、`5: Picture Profile / Select LUT`、`6: White Balance`）。
  - 当 `[Home (Lower Left)] = [ND Filter]` 时严格归类为 `MASKED_ABSENT_HW` 手动外置滤镜参考分母元数据（`Clear`, `1/4..1/128`），在 Stage-B 强制拦截一切指向 CP 的 `PID_SET_VARIABLE_ND_VALUE` 电机驱动帧（`e_nd_actuator_tx_count == 0`）。

### Pillar 2 — `[Save/Load Settings]` (`CAMSET01.DAT .. CAMSET10.DAT`) Slot-1 独占锁、双介质路径分叉与跨机型 `.DAT` 防火墙
- **实测二进制事实（`O_RDONLY`）**：
  - 两机 `appFw.so` 均实测检出 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`、`%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT`、`save_load_settings_file0..file9`、`sequence/sequence_save_load_settings_save.cpp` 与 `sequence/sequence_save_load_ftp_settings_save.cpp`；`FX3 7.02` 检出 `CAMSET%02d` 与 `is_recall_camera_setting_screen_push_ok`。
- **路径分叉与沙箱建模**：
  - 严格锁定 **Slot 1 独占**（拒绝 `Slot 2`）、单卡上限 **10 组**（`CAMSET01.DAT .. CAMSET10.DAT`）、`MR`（`Recall Camera Setting`）模式下置灰不可用，并自动剥离机身绑定字段（`Custom WB 1/2/3`、`FTP`、`Network Streaming`、`IP/Cert`、`Date/Time`）。
  - 精确区分 SD / SDHC / SDXC（`/PRIVATE/SONY/SETTING/FX3/CAMSET/`）与 CFexpress Type A（`/SONY/SETTING/FX3/CAMSET/`，无 `/PRIVATE` 前缀）根目录分叉，交叉混用一律拦截。
  - 洁净室 32B 模型头与 CRC32 验证强制阻断 `ILME-FX3` (`0x91030080`, `819` BK4) vs `ILME-FX3A` (`0x91030082`, `823` BK4) vs `ILME-FX6` (`0x91030060`, `840` BK4) 跨机型 `.DAT` 混读；Stage-B 保存操作重定向至易失性 `/tmp/fx6_camset_overlay`，确保 `H0 == H3`（`p2_setting_mutation_bytes == 0`）。

### Pillar 3 — `VMC-BNCM1` (`A-5051-506-A`) 机身直连单向 `TC IN` (`EXT-LK`)、`XLR-H1` 手柄 Micro-USB 禁插令与 HDMI 数字 `TC OUT`
- **实测二进制事实（`O_RDONLY`）**：
  - 两机 `appFw.so` 均包含 `sequence_hdmi_tc_output`、`VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON/OFF`、`TC_RUN_FREE_RUN/REC_RUN`；`FX3 7.02` 包含 `No301_EXTLK` 与 `MSG_ID_TCUB_TC_SYNC`；`FX6 6.01` 独有 `PRM_HAITA_setting_hdmi_tc_output_sdi_output`。两机 `CPAPP-B.BIN` / `cpapp-b.bin` 有界切片均检出 `LTC`、`29:Vitc/LTC/DPACK`、`EXTERNALTC_LOCK`、`HDMI::MSG_PARAM_SET_TC_OUTPUT`。
- **端口路由与状态机建模**：
  - `VMC-BNCM1`（`A-5051-506-A`, `0.2m`）仅允许插入机身侧 `BODY_MULTI_MICRO_USB` 执行单向 `TC IN`：在 `[Movie]` + `[Time Code Make] = [Preset]` + `[Time Code Run] = [Free Run]` 且锁相驻留 `>= 10.0s` 时进入 `EXT-LK`；切入 `S&Q` 或修改 `TC Make/Run/Preset` 立即释放 `EXT-LK`。
  - 硬性禁止将 `VMC-BNCM1` 误插至 `XLR-H1` 顶部手柄侧面固件升级专用 Micro-USB 口（`HARD_WRITE_PROTECTED`），并阻断 `H0` `uart_boot` 期间 Pin 7/8/9 串口争用。
  - 对机身 Multi/Micro USB 或虚拟 BNC 发起的反向 `TC OUT` 一律返回 `EOPNOTSUPP`（`bnc_tc_out_tx_packets == 0`）；数字 `TC OUT` 唯一合法物理出口为全尺寸 Type-A HDMI（`[Time Code Output] = [On]`，且在 `S&Q` 模式下自动关闭）。

### Pillar 4 — 全局零写防火墙与 12 触点四分类兼容矩阵
- 汇总 `P203-01 .. P203-12` 共 **12 个硬件/固件触点**，完整覆盖 `NATIVE_PASSTHROUGH`、`SHIM_TRANSLATED`、`MASKED_ABSENT_HW`、`HARD_WRITE_PROTECTED` 四类桥接等级。
- 硬安全不变量恒成立：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`e_nd_actuator_tx_count = 0`、`raw_firmware_bytes_leaked = 0`。
- **边界声明**：本阶段全部工作均为本地主机侧纯离线 `O_RDONLY` 二进制取证与洁净室状态机建模，**未连接任何物理相机 USB，未生成或下发任何刷机载荷或 eMMC/SPI-NOR 写入指令**。

---

## 3. 交付文件清单（严格归属范围内 6 个文件）

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor.py)（新增：第 42 号审计器 `42/42` 实现）
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 203 公共常量、数据类与入口函数）
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：注册 `audit-realhw-big6-noend-camset-vmcbncm1` 并接入 `audit-all` `42/42`）
4. [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/README.md)（更新：补充第 42 号审计器说明与 CLI 命令）
5. [`outputs/fx3-firmware-lab/tests/test_realhw_big6_noend_camset_slot1_and_vmcbncm1.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/outputs/fx3-firmware-lab/tests/test_realhw_big6_noend_camset_slot1_and_vmcbncm1.py)（新增：56 项双模单测；注：第 41 号审计器测试已使用 `assertGreaterEqual(..., 41)`，无需改动）
6. [`reports/2026-11-15-phase203-realhw-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h223-phase203-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/reports/2026-11-15-phase203-realhw-42nd-auditor-big6-noend-camset-slot1-vmcbncm1/README.md)（新增：本交付报告）

---

## 4. 验证命令与实测结果

| 验证项 | 命令（均带 `/usr/bin/python3 -B`） | 实测结果 |
| :--- | :--- | :--- |
| 第 42 号审计器 CLI | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-big6-noend-camset-vmcbncm1 --json \| head -n 30` | `all_checks_passed: true`, `auditor_index: "42/42"`, 冷扫 `0.119s` |
| 总控 `audit-all` (`42/42`) | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --json \| head -n 30` | `all_checks_passed: true`（42 项审计器全绿） |
| Phase 203 单测（本地 Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_big6_noend_camset_slot1_and_vmcbncm1.py` | `Ran 56 tests in 0.508s — OK` |
| Phase 203 单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_big6_noend_camset_slot1_and_vmcbncm1.py` | `Ran 56 tests in 0.389s — OK` |
| 固件实验室全量单测（Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1575 tests in 58.045s — OK` |
| 固件实验室全量单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1575 tests in 29.067s — OK (skipped=6)` |
| 全局零字节码/合规门禁 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `PASS`（零 `.pyc` / `__pycache__` / 专有二进制残留） |
