# Phase 205（第 43 号固件审计器 `43/43`）交付报告：`ILME-FX3` (`Ver. 7.02`) `[De-Squeeze Display]` (`1.6x=1.65x` 与四项硬件强锁 / HDMI RAW 旁路)、外置 `M&C Focus Map` (`>=150fps` 截止) 及双卡 `[Simult. + Auto Switch]` / `[Shockless WB]` 审计器

## 1. 核心结论

1. **第 43 号审计器 (`43/43`) 落地闭环**：已在 [`realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor.py) 完成 `PHASE_205_SCHEMA` (`205.0.0`) 实现，完整导出至 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)，并在 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) 注册独立子命令 `audit-realhw-desqueeze-focusmap-shocklesswb` 及总控 `audit-all` (`43/43`)，同步更新 [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/README.md)。
2. **有界 `os.O_RDONLY` + `os.pread` 极速扫描与洁净室双模一致性**：本地真机 Donor 冷启动扫描实测耗时 **`0.123s .. 0.134s`**（严格满足 `< 0.15s` 预算，进程内 `_DONOR_SCAN_CACHE_P205` 二次命中 `< 1ms`）；`CPAPP-B.BIN` / `cpapp-b.bin` 严格采用头部 `768 KiB` + 尾部 `6 MiB` 有界读取，零整包冗余扫描，`raw_firmware_bytes_leaked == 0`（Donor 报告 SHA-256：`8e2267a67c2796c8e967c93674d5cc1ff6e819c649cb474685b359acc8f63a99`；洁净室报告 SHA-256：`d702c5b602c2b92e4bb27ed91e183a09a03658e734f684f1816e5a52634da3e9`）。
3. **全量双模回归 `100%` 通过**：新增 [`test_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/tests/test_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb.py) **54 项**双模单测（Donor 模式 `0.594s`、洁净室模式 `0.341s`）；`outputs/fx3-firmware-lab/tests` 全量 **1,629 项**单测在本地 Donor 模式（`57.733s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式（`27.948s`）均 `100%` 通过，且 `scripts/run_all_lab_tests.py --clean-only` 全绿（`2.60s`）。

---

## 2. 四大实证支柱（实测二进制证据 vs 建模边界）

### Pillar 1 — `[De-Squeeze Display]` 五档枚举（`1.6x = 1.65x`）、四项硬件强锁与五类自动抑制旁路
- **实测二进制事实（`O_RDONLY`）**：
  - 原厂 `FX3 Ver. 7.02` (`appFw.so` `79,015,712 B` + `string_english_f.uxc` `373,820 B`) 与 `FX6 Ver. 6.01` (`appFw.so` `50,520,424 B` + `string_english.uxc` `118,208 B`) 均检出 `N5model25setting_de_squeeze_disp_tE`、`set_de_squeeze_disp_i`、`set_param_anamo_desqueeze_scale_msg`、`video_set_de_squeeze_disp`、`FOCUS_MODE_MF` 与 `FACE_DETECTION_IN_MULTI`。
  - `FX3 7.02` 检出完整五档 HAITA 排斥符号：`BKID_APP_setting_de_squeeze_disp`、`DE_SQUEEZE_DISP_1_3X`、**`DE_SQUEEZE_DISP_1_5X`**、**`DE_SQUEEZE_DISP_1_6X`**、`DE_SQUEEZE_DISP_2_0X` 及 `STEADY_SHOT_OFF`；英文语言包 `string_english_f.uxc` 完整命中 `De-Squeeze Display`、`1.3x`、`1.5x`、`1.6x`、`2.0x`、`Manual Focus`、`Wide`、`SteadyShot`、`Face Priority in Multi Metering`、`RAW Output`、`Off(HDMI Only)`、`HDMI Info. Display`、`Log Shooting` 与 `Remote Shooting`。
- **精确几何与锁链建模**：
  - `MENU -> Setup -> [Display Option] -> [De-Squeeze Display]` 支持 `Off`、`1.3x`、`1.5x`（`Ver. 7.00+`）、**`1.6x`（`Ver. 7.00+`，实际施加 `1.65` 倍水平拉伸还原 `2.39:1` CinemaScope 宽银幕）** 与 `2.0x`；低于 `Ver. 7.00` 的固件请求 `1.5x/1.6x` 严格阻断。
  - 非 `Off` 且未处于抑制态时强制校验四项锁定：`[Focus Mode] = Manual Focus`、`[Focus Area] = Wide`、`[SteadyShot] = Off`、`[Face Priority in Multi Metering] = Off`。
  - 五类自动抑制回退至 `1.0x`：`[RAW Output] = On`、`[Rec. Media dur HDMI Output] = Off(HDMI Only)`（同时联动强制 `[HDMI Info. Display] = Off`）、`[Log Shooting] = Off`、`[Remote Shooting]` 激活以及 `Photo` 拍照模式，并拦截 Stage-B 强行覆写。

### Pillar 2 — `ILME-FX3` 零机内 `[Focus Map]` 菜单（对比 `FX30`/`FX6`）与外置 `Monitor & Control` `>=150fps` 截止
- **实测二进制事实（`O_RDONLY`）**：
  - `FX6 Ver. 6.01` `appFw.so` 包含 4 项机内菜单/自定义按键符号（`BKID_APP_USER_MENU_FOCUS_MAP`、`ASSIGNABLE_SWITCH_FOCUS_MAP`、`EVENT_FUNC_FOCUS_MAP_ON`、`EVENT_FUNC_FOCUS_MAP_OFF`），而在 `FX3 Ver. 7.02` `appFw.so` 中该 4 项符号命中数均为 **`0`**，实证 `FX3` 机内无本地 `[Focus Map]` 菜单开关。
  - `FX3 Ver. 7.02` `appFw.so` 检出远程事件桥接 `to_remote_event_focus_map`、`sequence_notify_focus_map`、`view_mp_focus_map`，且 `CPAPP-B.BIN` 有界切片检出 `cpActFocusMap`、`cpActFocusMapWidgetService`、`paramYcFocusMap` 与 `Mount_DividedInfo`。
- **外置遥测与截止边界建模**：
  - 严禁 Stage-B 在 `ILME-FX3` 机内 LCD 强刷不存在的本地硬件 `Focus Map` 叠加层（`in_body_focus_map_overlay_injected == False`，归类 `MASKED_ABSENT_HW`）。
  - 外置 `Monitor & Control` App 焦点图流（需 `FX3 Ver. 6.00+` + 原生索尼 E 卡口 PDAF 镜头）在 **`>= 150 fps`**（含 `200fps / 240fps S&Q`）、无镜头/转接环/非相位检测镜头、UVC 串流与机内回放态下自动截止；同时精确区分 **`FX3` 允许 `1..6 fps`** vs **`FX6` 在 `<= 6 fps` 触发下限截止** 的跨机差异。

### Pillar 3 — 双卡 `[Simult. Recording]` + `[Auto Switch Media]`（`Ver. 2.0+` 单卡续录 vs `Off` 严格双份）与 `[Shockless WB]` 色温/网格 0 帧旁路
- **实测二进制事实（`O_RDONLY`）**：
  - `FX3 Ver. 7.02` `appFw.so` 检出 `VAL_setting_movie_recording_media_MOVIE_RECORDING_MEDIA_SIMULTANEOUS_RECORDING`、`SIMULT_REC`、`setting_relay_rec_movie`、`RELAY_REC_ON`、`CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD`，以及白平衡缓变符号 `BKID_APP_setting_movie_shockless_wb`、`movie_shockless_wb_seq`、`MOVIE_SHOCKLESS_WB_OFF / 1 / 2 / 3`、`BKID_APP_MENU_WB_COLOR_TEMP` 与 `WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_5500K`。
- **双卡容灾与白平衡瞬时旁路建模**：
  - 起录强制双槽在位校验（缺卡触发 `CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD`）；`Ver. 2.0..7.02` 下若 `[Auto Switch Media] = [On]`，单卡耗尽时 **0 丢帧自动降级在剩余单卡续录**，热插拔换入新卡后自动恢复双卡同录；若要求双份冗余严格一致（`1:1` 镜像），设为 `[Auto Switch Media] = [Off]` 即在任一卡满时立即停录。
  - `MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]`（`Off / 1 (Fast) / 2 / 3 (Slow)`）在全帧率（`1fps .. 23.98p .. 120p .. 240fps S&Q`）对预设/记忆档切换与 ATW 收敛执行平滑过渡，但对 **`[C.Temp./Filter]` 直接修改 Kelvin 值（`2500K..9900K`）** 与 **`A–B / G–M` 微调网格偏移（`±7.0`）** 严格执行 **`0` 过渡帧即时生效旁路**。

### Pillar 4 — 全局零写防火墙与 12 触点四分类兼容矩阵
- 汇总 `P205-01 .. P205-12` 共 **12 个硬件/固件触点**，完整覆盖 `NATIVE_PASSTHROUGH`（4）、`SHIM_TRANSLATED`（5）、`MASKED_ABSENT_HW`（1）、`HARD_WRITE_PROTECTED`（2）四类桥接等级。
- 硬安全不变量恒成立：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`in_body_focus_map_overlay_injected = False`、`raw_firmware_bytes_leaked = 0`。
- **边界声明**：本阶段全部工作均为本地主机侧纯离线 `O_RDONLY` 二进制取证与洁净室状态机建模，**未连接任何物理相机 USB，未生成或下发任何刷机载荷或 eMMC/SPI-NOR 写入指令**。

---

## 3. 交付文件清单（严格归属范围内 6 个文件）

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor.py)（新增：第 43 号审计器 `43/43` 实现）
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 205 公共常量、数据类与入口函数）
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：注册 `audit-realhw-desqueeze-focusmap-shocklesswb` 并接入 `audit-all` `43/43`）
4. [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/README.md)（更新：补充第 43 号审计器 `43/43` 说明与 CLI 命令）
5. [`outputs/fx3-firmware-lab/tests/test_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/outputs/fx3-firmware-lab/tests/test_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb.py)（新增：54 项双模单测；注：第 42 号审计器测试已使用 `assertGreaterEqual(..., 42)`，无需改动）
6. [`reports/2026-11-15-phase205-realhw-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/reports/2026-11-15-phase205-realhw-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/README.md)（新增：本交付报告；上游情报参考 [`Wave-27 README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h226-phase205-43rd-auditor-desqueeze-165x-focusmap-simult-shocklesswb/reports/2026-11-15-global-sony-wave27-desqueeze-165x-4locks-external-focusmap-150fps-simult-autoswitch-shocklesswb-intel/README.md)）

---

## 4. 验证命令与实测结果

| 验证项 | 命令（均带 `/usr/bin/python3 -B`） | 实测结果 |
| :--- | :--- | :--- |
| 第 43 号审计器 CLI | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-desqueeze-focusmap-shocklesswb --json \| head -n 30` | `all_checks_passed: true`, `auditor_index: "43/43"`, 冷扫 `0.123s..0.134s` |
| 总控 `audit-all` (`43/43`) | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --json \| head -n 30` | `all_checks_passed: true`（43 项审计器全绿） |
| Phase 205 单测（本地 Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb.py` | `Ran 54 tests in 0.594s — OK` |
| Phase 205 单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb.py` | `Ran 54 tests in 0.341s — OK` |
| 固件实验室全量单测（Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1629 tests in 57.733s — OK` |
| 固件实验室全量单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1629 tests in 27.948s — OK (skipped=6)` |
| 全局零字节码/合规门禁 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 2.60s`（零 `.pyc` / `__pycache__` / 专有二进制残留） |
