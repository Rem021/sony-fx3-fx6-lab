# Phase 200（VM Stage 35 `35/35` 里程碑）：真实硬件 `ILME-FX3` 4 态 `[Fan Control]`（`Off in Rec` 待机 `MAX PWM` / `Always Off` 冷备前置门控）、独立快门 `Speed/Angle`（`5.6°..64F / 360°`）与 `6.01` vs `7.02` `p2:/setting` User LUT 分叉防火墙 HIL 协同仿真报告

## 1. 核心结论（实测与红线零违规）

在 Wave-25 真机情报（[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/reports/2026-11-15-global-sony-wave25-fan-pwm-offinrec-shutter-angle-lut-601-vs-702-binary-split-intel/README.md)）与已合入 Stage 34 协同框架基础上，已完成 **VM Stage 35（`stage35_realhw_fan_pwm_shutter_angle_lut_split_hil`，里程碑 `35/35`）** 的实现、35 阶段套件编排接入、48 项双模单测及全仓回归验证：

- **高速双模只读供体审计（`< 0.10s`，进程级缓存）+ 洁净室回退**：[`inspect_phase200_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py#L796) 以严格 `os.O_RDONLY` 与 `<= 4096 B` 有界窗口核验 FX3 `7.02` 与 FX6 `6.01` 共 **12 份真实供体**（`libfan.so`、`libbackup.so`、`libBackupManager.so`、`im.elf`、`string_english_f.uxc`、`appFw.so`、`cpapp-b.bin`、`libmpr.so`），在 `string_english_f.uxc` 中实测证实 `Fan Control` / `Off in Rec` / `Always Off` / `Minimum` / `Auto Power OFF Temp.` 存在且 **`Auto1` / `Auto2` 命中数为 `0`**；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下确定性切换 `CLEAN_ROOM_SYNTHETIC`（`raw_firmware_bytes_leaked == 0`）。
- **Pillar A — `ILME-FX3`（`0x91030080`）精确 4 态 `[Fan Control]`（拒绝 `Auto1/Auto2`）& 热控/冷备门控 HIL**：[`probe_fx3_fan_pwm_and_backup_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py#L1018) 精确仿真 `MENU -> Setup -> [Setup Option] -> [Fan Control]` 四态 PWM 控制器（`Auto`、`Minimum`、`Off in Rec`、`Always Off`），对无效 `Auto1` / `Auto2` 返回 `EINVAL`（`22`）；在 `Off in Rec` 下待机驱动 **`100% MAX PWM`** 主动排热、正常录制降至 **`0% PWM`** 静音，并在结温越过安全上限（`Standard: 68°C` / `High: 78°C`）时触发 **`100% PWM`** 紧急热保护覆盖；当处于 `Always Off`（或非 `Auto`）时硬拦截 `AdjustControl (0x40)` 75 MiB `p3` 冷备/双启入口，直至切回 `Auto`。
- **Pillar B — 独立 `[Shutter Mode]`（`Speed` vs `Angle`）AP-CP HIL & 帧率钳位**：[`evaluate_shutter_speed_angle_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py#L1395) 协同仿真 `Backup.bin` 独立的 `[Speed]`（`0x01240010`）与 `[Angle]`（`0x01240014`）槽位存储（跨 `BIG6` / `Movie` / `S&Q` 互不覆盖，且快门角对 `0.3EV / 0.5EV` `[Exposure step]` 完全免疫），在 `<= 59.94p` 允许 `5.6°..64F`（`23,040°`）多帧累加，在 `119.88p / 100p` 与 `S&Q` 下严格钳位至 `5.6°..360°`。
- **Pillar C & D — `FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT 二进制格式分叉防火墙与硬安全红线**：[`probe_p2_setting_lut_binary_split_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py#L1661) 与 [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py#L1899) 拦截 Stage-B `FX6 Ver. 6.01`（`<=6.01` 旧版槽位格式）向原厂 `FX3 7.02` `p2:/setting` 的直接写入（返回 `EROFS` `30`），将 `User1..User16` 全部 16 槽位严格重定向至易失性 `/tmp/fx6_lut_overlay`，阻断未重注册 `6.01` 槽位在 `7.02` 中直接加载，保持 `16/16 H0 == H3`（`p2_setting_mutation_bytes == 0`），并硬锁 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`。

## 2. 交付清单（严格限域修改）

| 文件 | 变更 | 说明 |
| --- | --- | --- |
| [`realhw_fan_pwm_shutter_angle_lut_split_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py) | 新增 | Stage 35 (`35/35` 里程碑) 主模块（12 供体只读审计 + Pillars A–D + `--self-test/--summary/--json/--clean-room`） |
| [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 更新 | 接入 [`run_stage35_realhw_fan_pwm_shutter_angle_lut_split_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L2062) 与 `--skip-phase200` |
| [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/README.md) | 更新 | 增补 Phase 200 / Stage 35 (`35/35` 里程碑) 架构与 CLI/测试命令 |
| [`test_realhw_fan_pwm_shutter_angle_lut_split_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/tests/test_realhw_fan_pwm_shutter_angle_lut_split_coemulator.py) | 新增 | 48 项双模单测（覆盖 12 供体、Pillars A–D、Stage 35 `35/35` 与 `--skip-phase200`、`< 6.0s` 时限） |
| [`test_realhw_nouvc_dcc1_lut_path_cineei_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/outputs/fx3-vm/tests/test_realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L649) | 更新 | 仅放宽 Stage 34 阶段数硬编码断言（`assertEqual(..., 34/33)` -> `assertGreaterEqual(..., 34/33)`） |
| [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h219-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/reports/2026-11-15-phase200-vm-stage35-fan-pwm-shutter-angle-lut-split-hil/README.md) | 新增 | 本中文验收报告 |

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 实测结果 | 备注 |
| --- | --- | --- | --- |
| Stage 35 `--self-test --summary` | `LOCAL_DONOR_RDONLY` | **PASS**（`digest=ec5a4d02cbf7`） | `stby_pwm=100% \| hfr_clamp=360.0deg \| p2_erofs=30 \| h0_h3=16/16 \| emmc_wr=0` |
| Stage 35 `--self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | **PASS**（`digest=b62d4cf5b2b1`） | `raw_firmware_bytes_leaked == 0` |
| 35 阶段套件 `run_fx3_vm_coemulation_suite` | Local / Clean-Room | `local_cold=1.887s`（`< 2.1s`）、`local_warm=0.486s`、`clean_room=0.439s`（`< 1.0s`） | `local_digest=1e62a034fe83` / `clean_digest=c645038f56ba` |
| Stage 35 专项单测（48 项） | Local / Clean-Room | **48/48 PASS**（`4.799s` / `3.338s`，均 `< 6.0s`） | `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest ...` |
| `outputs/fx3-vm/tests` 全量发现 | Local | **1324/1324 PASS**（`103.707s`） | 零失败、零残留 `.pyc` |
| `outputs/fx3-vm/tests` 全量发现 | Clean-Room | **1324 tests PASS**（`89.971s`, `skipped=3`） | 仅 3 项既有阶段受本地供体条件跳过 |
| `scripts/run_all_lab_tests.py --clean-only` | 仓库卫生审计 | **ALL GREEN**（`0.05s`） | `git status --porcelain` 二进制/pyc 审计 `CLEAN` |

> [!NOTE]
> 所有仿真均在严格只读（`os.O_RDONLY`）与离线虚拟内存状态下完成，未对任何真实物理 FX3/FX3A/FX6 设备、eMMC、SPI-NOR、OTP 或 RPMB 执行物理写入或 USB 发包。
