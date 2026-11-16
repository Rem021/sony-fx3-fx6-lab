# Phase 228 安全护栏报告：Gates G83 / G84 与统一 `verify-84-gates` 预检引擎（`outputs/fx3-safety/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Wave-32 官方 `ILME-FX3 Ver. 7.02` 安全门禁 `G83`、`G84` 与统一 `84-Gate` 主预检引擎（`G01..G84`）闭环交付**：
   - 新增模块 [`realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py)（将 `G01..G82` 直接委托给 [`evaluate_82gate_preflight()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py#L1622-L1844)，`100%` 保留 `verify-58-gates` 至 `verify-82-gates` 向后兼容），并同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/__main__.py) 与 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/README.md)。
2. **双模式全量测试、Milestone 221 与 BYOF 卫生审计 100% 通过（实测事实）**：
   - 新增 [`test_phase228_sq_fixedvar_zebra_peaking_fullformat_84gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/tests/test_phase228_sq_fixedvar_zebra_peaking_fullformat_84gate_guard.py) 共 **62 项**双模式单元测试（要求 `>=56`），在 `LOCAL_DONOR_O_RDONLY`（`4.139s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.176s`）双模式下全部 `OK` 通过；
   - `outputs/fx3-safety/tests` 全量回归：本地只读 Donor 模式 **`1805/1805` 全部通过（`93.890s`）**，Clean-Room 合成模式 **`1804` 项通过、`1` 项按设计跳过（`62.163s`）**；
   - CLI `verify-84-gates`：默认离线模式通过 **`81/84`**（仅物理台架 Tier-0 冷备门禁 `G10..G12` 待接入真机回读凭证），`--simulate-bench-dry-run` 预演模式在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下均通过 **`84/84`**；
   - 跨模块里程碑与 BYOF 卫生审计：`make verify-milestone-221` 双模式 `status=OK`，`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.05s`（零 `.pyc`、零专有固件字节泄漏）。
3. **硬件安全红线硬锁不变（实测事实）**：
   - `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`overall_ready_for_hardware_attach = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. Gate G83 与 Gate G84 技术建模要点（Wave-32 规范映射）

### 2.1 Gate G83：`G83_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD`
- **`Ver. 7.00+ / 7.02` `[Mode Settings] = [Fixed/Variable]` 与旧版 `[S&Q Settings]` 互斥锁**：
  - [`resolve_fx3_mode_settings_and_sq_6locks()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1029-L1098) 与 [`verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1126-L1461) 精确建模 `MENU -> Shooting -> [Shooting Mode] -> [Shoot Mode] -> [S&Q(Slow&Quick Motion)] -> [Mode Settings]`：当启用 `[Fixed/Variable]`（要求固件 `>= 7.00`）时，强制锁定旧版 `MENU -> Shooting -> [Image Quality/Rec] -> [S&Q Settings]` 并切换为直接 `[FPS]`（`Home (FPS)`）帧率控制，任何 `<7.00` 固件宣称或旧菜单篡改均触发 `BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION`。
- **官方 `ILME-FX3` S&Q 6 项硬件级禁用矩阵**：
  1. `0ch` 无音频录制（`sq_audio_channels_recorded == 0` 且 `sound_recorded_in_sq == False`）；
  2. `MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]`（出厂默认 `Live` 零延迟 vs `Lip Sync` 音画同步）在 S&Q 下强制禁用，仅在常规 Movie 模式下可用；
  3. `[Time Code Run]` 与 HDMI `[Time Code Output]` 在 S&Q 下不可用；
  4. `240fps`（NTSC）/ `200fps`（PAL）在全部 4 种 4K 格式（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`、`XAVC S-I DCI 4K`）下禁用（仅限 `XAVC S HD` / `XAVC S-I HD`）；
  5. `120fps`（NTSC）/ `100fps`（PAL）在 `XAVC S-I DCI 4K`（`4096x2160`）下禁用；
  6. `[Proxy Recording]` 在 S&Q 下当 `Rec Frame Rate` 为 `119.88p`/`100p` 或采集 `Frame Rate >= 120fps`/`100fps` 时禁用（违例统一阻断为 `BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION`）。
- **`[Zebra Display]` 与 `[Peaking Display]` 仅限机身本地 LCD 渲染、HDMI Clean-Feed 硬件隔离**：
  - [`resolve_fx3_zebra_peaking_hdmi_cleanfeed()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1101-L1123) 校验斑马纹与峰值对焦（`On/Off`、`High/Mid/Low`、`Red/Yellow/Blue/White`、控制拨轮右键默认 `[Peaking Display Select]`）绝不通过 Type-A HDMI 输出——即便开启 `[HDMI Info. Display] = [On]`（此时机身 LCD 黑屏，外接 HDMI 仅带 OSD 字符而不带斑马纹/峰值轮廓），任何 HDMI 辅助叠加泄漏均触发 `BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK`。
- **有界 `< 0.15s` `O_RDONLY` 本地 Donor 校验与 Clean-Room 兜底**：
  - [`audit_phase228_donor_contracts()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L880-L1020) 以只读描述符校验 `cpapp-b.bin`、`libSaveLoadSettings.so`、`FX3-CX95900_ALLLANG-Backup.bin` 与 `CX95898_NTSC.bin`（`raw_firmware_bytes_leaked == 0`），并支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成模式。

### 2.2 Gate G84：`G84_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD`
- **`[Zebra Display]` 与 `[Zebra Level]` 跨 `[Camera Settings Reset]` 存活非对称性**：
  - [`resolve_fx3_zebra_reset_survival()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1549-L1570) 与 [`verify_zebra_reset_survival_and_fullformat_chord_vault_guard()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1619-L1907) 校验控制拨轮左键默认 `[Zebra Display Select]`、`[Zebra Display]`（`Off`/`On`）及全部 10 档 `[Zebra Level]`（`70..100+`、`Custom 1` `Standard ± Exposure Range` 曝光带、`Custom 2` `Minimum` 过曝下限）在 `[Camera Settings Reset]` 后原样保留，仅在 `[Initialize]` 全量出厂重置时归零为 `Off` / `70`（违例阻断为 `BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION`）。
- **Slot 1 Tier-0 恢复冷备卡（`pnflasha` / `cnflasha` / `CAMSET01.DAT`）三通道格式化硬锁与 Full Format 中途取消语义**：
  - [`resolve_fx3_slot1_format_and_chord_vault_lock()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py#L1573-L1616) 在 Slot 1 存放活跃或尚未完成主机离线 SHA-256 校验并物理拔出/写保护的 Tier-0 恢复镜像期间，同时硬锁阻断：① `[Enter]` **Quick Format**（仅清元数据）、② 确认框按 `(Delete)` 切换的 **Full Format**（擦除全部数据块 + 元数据）、③ 拍摄界面同时长按 **`MENU + (Delete)` 约 `2s` 物理组合键**直接呼出的快速格式化入口（`BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT`）；
  - 同时严格校验 **Full Format 中途取消（`Cancel`）语义**：一旦中途取消，此前存储的数据已被永久擦除（`mid_cancel_prior_data_erased == True`），但存储卡本身保持已格式化可用状态（`mid_cancel_card_usable == True`，不一致阻断为 `BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH`）。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并零错误退出。
- **架构推断（Engineering Inference）**：物理真机 Slot 1 Tier-0 冷备回读（`G10..G12`）仍按设计处于离线待命阻断状态（`81/84`），唯有人工台架提供真机 SHA-256 回读收据后方可在非模拟模式下闭合最后 3 门，且所有硬件自动烧录与 eMMC 持久写红线始终硬锁为 `False`。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 228 双模式定向单测（62 项 × 2） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase228_sq_fixedvar_zebra_peaking_fullformat_84gate_guard.py`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `62/62 OK`（`4.139s`）+ `62/62 OK`（`1.176s`） |
| 全量 `fx3-safety` 测试（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1805 tests in 93.890s — OK` |
| 全量 `fx3-safety` 测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | `Ran 1805 tests in 62.163s — OK (skipped=1)` |
| CLI `verify-84-gates`（离线默认） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-84-gates`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=81/84`（`VERIFIED_81_OF_84_AWAITING_PHYSICAL_TIER0`，`rc=0`） |
| CLI `verify-84-gates --simulate-bench-dry-run` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_safety verify-84-gates --simulate-bench-dry-run`（及 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `verified=84/84`（`VERIFIED_ALL_84_GATES_DRY_RUN_SIMULATED_BACKUP`，`rc=0`） |
| Milestone 221 双模式门禁回归 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221` | `LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 双模式 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s` |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.py)
2. [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/__init__.py)
3. [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/fx3_safety/__main__.py)
4. [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/README.md)
5. [`outputs/fx3-safety/tests/test_phase228_sq_fixedvar_zebra_peaking_fullformat_84gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/outputs/fx3-safety/tests/test_phase228_sq_fixedvar_zebra_peaking_fullformat_84gate_guard.py)
6. [`reports/2026-11-15-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h253-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/reports/2026-11-15-phase228-safety-84gates-sq-fixedvar-zebra-fullformat/README.md)
