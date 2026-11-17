# Phase 272 恢复支柱与统一总控报告（Task H308，`47/47` Recovery Pillars）：Wave-45 Pillar 47（`Focus Magnifier / Auto Magnifier in MF`、`Area/Date/Time Zero-RF`、`Video Light 5V <= 900 mA` & `HDMI Resolution` Vault）与 `verify-47pillar-recovery`（`outputs/fx3-recovery-adapter/`）

## 1. 核心结论（Conclusion-First）

1. **已完成 Phase 272（Task H308）端到端交付：将 Global Sony Real-Hardware Intelligence Wave 45（`ILME-FX3 Ver. 7.02`，`0x91030080`，Help Guide `ilc/2210`）转化为 Recovery Pillar 47（`47A` + `47B`）及统一 `47/47` 恢复主总控（`evaluate_realhw_47pillar_recovery_master` / `verify-47pillar-recovery`）**：
   - 新增模块 [`realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py)（Schema `realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier_v1` `v1.0.0`），通过 `ThreadPoolExecutor(max_workers=2)` 并发将 Pillars `1..46` 直接委托给 [`evaluate_realhw_46pillar_recovery_master()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier.py) 并叠加 Pillar 47 独立套件，保持 100% 向后兼容 `verify-22..46pillar-recovery`；
   - 同步更新 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)（零遮蔽导出全部 Phase 272 常量、数据类、函数与别名，未覆盖 Pillars `1..46` 安全常量）、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)（注册 `verify-focus-mag-datetime-videolight-hdmires-vault` 与 `verify-47pillar-recovery`，支持 `--json` / `--out` / `--force-clean-room`，`argparse` 帮助文本无未转义 `%`）及 [`outputs/fx3-recovery-adapter/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/README.md)。
2. **三模式 75 项双模单测、全套 2,486 项恢复适配器测试、Milestone 264 回归、CLI `< 2.0s` 预算与 BYOF/字节码卫生审计全部通过（实测事实）**：
   - 新增 [`test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/tests/test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py) 共 **75 项**双模单元测试（满足 `>= 70` 项，所有子进程使用 `sys.executable`、`--out` 使用仓内 `work/_tests/` 隔离临时目录、亚秒微时序断言含 `GITHUB_ACTIONS == "true"` 裕量），在 `LOCAL_DONOR_O_RDONLY`（`6.643s`）、`FX3_CLEAN_ROOM_TEST=1`（`6.356s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`6.532s`）下均 `75/75 OK`；
   - CLI `verify-47pillar-recovery` 在 `LOCAL_DONOR_O_RDONLY`（`0.999s < 2.0s`、`master_47pillar_sha256=f458b12769513bd9...`）与 `--force-clean-room`（`0.749s < 2.0s`、`master_47pillar_sha256=7198534f500f68a5...`）下均返回 `VERIFIED_47OF47_PILLAR_RECOVERY_MASTER`（`pillars=47/47`）；
   - `outputs/fx3-recovery-adapter/tests` 全量发现共 **2,486 项**在 `250.454s` 内 `OK (skipped=1)`（Phase 272 全量 75 项零跳过）、`make verify-milestone-264` 双模 `status=OK`、`scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.04s`。
3. **硬件安全红线与只读仓保真度硬锁不变（实测事实）**：
   - `hardware_live_attachment_authorized=False`、`cnflasha_userspace_write_blocked=True`、`persistent_emmc_writes_authorized=False`、`spi_nor_write_authorized=False`、`el3_payload_transmit_authorized=False`、`isp_write_authorized=False`、`otp_fuse_touches=0`、`rpmb_counter_increments=0`、`passive_tx_bytes_emitted=0`、`physical_usb_packets_emitted=0`、`physical_device_writes=0`、`raw_firmware_bytes_leaked=0`、`slot1_vault_mutation_bytes=0`。

---

## 2. Pillar 47A & 47B 与 `47/47` 主总控技术实现要点

### 2.1 有界只读 `O_RDONLY` Donor 校验与 Clean-Room 等价切换
- [`inspect_phase272_donors_readonly()`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py) 使用 `os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK` 边界只读检验 `16` 个 FX3 `Ver. 7.02` & FX6 `Ver. 6.01` Donor 工件（含 4 个大文件 4K header SHA-256 与 12 个 ELF/Backup 全量 SHA-256 及符号校验：`fx3_bodydata_702`、`fx3_appfw_702_so`、`fx3_cpapp_b_bin`、`fx6_appfw_601_so`、`FX3-CX95900_ALLLANG-Backup.bin`、`CX95898_NTSC.bin`、`libbackup.so`、`libBackupManager.so`、`libSaveLoadSettings.so`、`libgpe.so`、`CameraOnDemandSaver.so`、`libInfraAirplaneMode.so`、`libInfraMediaConfig.so`、`libInfraMediaDetect.so`、`libInfraDial.so`、`libInfraHotshoe.so`）。
- 实测耗时 `0.003216s`（远低于本地 `0.15s` 与 CI `0.50s` 预算），`raw_firmware_bytes_leaked == 0`，并在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失 Donor 时确定性切换为 `CLEAN_ROOM_SYNTHETIC`。

### 2.2 Pillar 47A：Focus Assistant 命名防伪、双独立 `Initial Focus Mag.` `x1.0`、干净 HDMI 峰值隔离与纯静态 `AF Illuminator`
- **菜单路径与命名防伪**：锁定 `MENU -> Focus -> [Focus Assistant]`、`[Peaking Display]` 与 `MENU -> Focus -> [AF/MF] -> [AF Illuminator]`。强制 `[Auto Magnifier in MF] = [On]` 默认值，严厉拒止旧机型 `"MF Assist"` 命名伪造（`BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF`，`legacy_mf_assist_spoof_events == 0`）。
- **键位与双独立倍率寄存器**：验证 `[Focus Magnifier]` 默认绑定 `Custom Button 5`、`[Focus Magnif. Time] = [No Limit]` 默认值，且静态照片与视频各自独立维护 `[Initial Focus Mag.] = [x1.0]` 寄存器（`still_movie_initial_mag_couplings == 0`）。
- **纯静态对焦辅助与干净 HDMI 隔离**：验证 `[AF in Focus Mag.] = [On]` 与 `[AF Illuminator] = [Auto]` 仅限 Still 域生效（`Movie` / `S&Q` 中 `movie_af_in_focus_mag_events == 0`、`movie_sq_af_illuminator_fire_events == 0`）；验证 `[Peaking Display]`（`Off` 默认、`Control Wheel Right`、`Mid`、`White`）与对焦放大叠加仅作用于机内 LCD，对 `Info Off` 与 `HDMI RAW` 输出零像素污染（`hdmi_clean_feed_focus_mag_or_peaking_leak_pixels == 0`）。
- **复位域边界与 `144` 状态穷举**：验证 `[Camera Settings Reset]` 重置 Focus 项同时保留 Custom Key 键位、`[Reset Network Set.]` 保留全部项、`[Initialize]` 全量复位，支持 Slot-1 `CAMSET01..10.DAT` 只读 `[Load]` 恢复，并完成 `144` 组状态矩阵穷举与 `6/6` 场景套件。

### 2.3 Pillar 47B：`Area/Date/Time Setting` 零射频时间戳保真、`Video Light Mode` `5V <= 900 mA`、`HDMI Resolution` Log 降档与 Slot-1 只读库锁
- **精确 4 子项命名与 Zero-RF 时钟保护**：锁定 `MENU -> Setup -> [Area/Date] -> [Area/Date/Time Setting]` 精确 4 子项（`Area Setting`、`Daylight Savings = Off`、`Date/Time`、`Date Format = YYYY-MM-DD`），严厉拒止 `"Date/Time Setup"` 伪造（`legacy_datetime_setup_spoof_events == 0`）。在 `[Airplane Mode] = [On]` 零射频台架下强制抑制 Creators' App `[Auto Time Correction]` 与 `[Auto Area Adjustment]`（`unsolicited_rtc_timezone_jump_events == 0`，完整保护 `H0..H3` 取证时间戳）。
- **MI-Shoe 供电预算与 Log HDMI 降档矩阵**：验证 `[Video Light Mode]`（`[Power Link]` 默认）满足 MI-Shoe `PMIC 5V <= 900 mA`（Gate `G24`，`mishoe_5v_overcurrent_events == 0`）；验证 `[HDMI Resolution]`（`[Auto]` 默认）在 `[Log Shooting] != Off` 且内录激活且 `[Rec. Media dur HDMI Output] = On` 时硬件强制 `1080p` 降档覆写（`hdmi_res_log_internal_rec_2160p_bypass_events == 0`），并在 `Off(HDMI Only)` 下放行 `2160p`。完成 `256` 组状态矩阵穷举、`[Setup]` 跨 `[Camera Settings Reset]` 留存验证与 Slot-1 SDXC WP 只读库锁定（`slot1_vault_mutation_bytes == 0`）及 `6/6` 场景套件。

---

## 3. 实测验证矩阵（Measured Facts vs Inferences）

- **实测事实（Measured Facts）**：下表全部命令均在本工作树实测执行并以返回码 `0` 通过。
- **工程推断（Engineering Inference）**：当前全部验证运行于只读 Donor（`LOCAL_DONOR_O_RDONLY`）与 `CLEAN_ROOM_SYNTHETIC` 离线双模沙箱下，与 Phase 271 安全护栏严格一致；真实机端 `Tier-0` 读写解锁仍需物理台架离线只读收据且不授权任何自动化 eMMC/NOR 刷写。

| 验证项 | 执行命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 272 三模式定向单测（75 项 $\times$ 3） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`（及 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `75/75 OK`（Donor `6.643s`）+ `75/75 OK`（`FX3_CLEAN_ROOM_TEST=1` `6.356s`）+ `75/75 OK`（`FX3_FX6_FORCE_CLEAN_ROOM=1` `6.532s`） |
| 恢复适配器全量单测发现 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | `Ran 2486 tests in 250.454s — OK (skipped=1)`（Phase 272 全量 75 项零跳过） |
| CLI `verify-focus-mag-datetime-videolight-hdmires-vault` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-focus-mag-datetime-videolight-hdmires-vault` | `status=VERIFIED_PILLAR47_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_VAULT`，`pillar_47a=6/6`，`pillar_47b=6/6`，`elapsed_seconds=0.004`，`suite_sha256=ba5b373e9e70a822` |
| CLI `verify-47pillar-recovery`（Donor 模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-47pillar-recovery` | `status=VERIFIED_47OF47_PILLAR_RECOVERY_MASTER`，`pillars=47/47`，`elapsed_seconds=0.999`（`< 2.0s`），`master_47pillar_sha256=f458b12769513bd9` |
| CLI `verify-47pillar-recovery`（Clean-Room 模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-47pillar-recovery --force-clean-room` | `status=VERIFIED_47OF47_PILLAR_RECOVERY_MASTER`，`pillars=47/47`，`elapsed_seconds=0.749`（`< 2.0s`），`master_47pillar_sha256=7198534f500f68a5` |
| Milestone 264 双模门禁回归 | `make verify-milestone-264` | `LOCAL_DONOR_O_RDONLY`（`c9b2207f6017c6c7...`）+ `CLEAN_ROOM_SYNTHETIC`（`c2fb728f841a66e5...`）均 `status=OK` |
| 仓库 BYOF 与字节码卫生检查 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.04s`（零 `.pyc`、零专有固件字节泄露） |

---

## 4. 严格归属文件清单（6 Owned Files）

1. [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py)
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)
4. [`outputs/fx3-recovery-adapter/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/README.md)
5. [`outputs/fx3-recovery-adapter/tests/test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/outputs/fx3-recovery-adapter/tests/test_realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier.py)
6. [`reports/2026-11-17-phase272-realhw-47pillar-focus-mag-datetime-videolight-hdmires-vault-recovery/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h308-phase272-pillar47-47pillar-focus-mag-datetime-videolight-hdmires-vault/reports/2026-11-17-phase272-realhw-47pillar-focus-mag-datetime-videolight-hdmires-vault-recovery/README.md)
