# Phase 218（第 45 号里程碑固件审计器 `45/45`）交付报告：`ILME-FX3` (`Ver. 7.02`) `File Settings` 37 字符 / SDHC 锁 + `Shot Mark1/2`、`TC Regenerate` Slot-1 主读 & `EXT-LK` 释放与 `REC Lamp` 后+顶联动 Tally 审计器

## 1. 核心结论

1. **第 45 号里程碑审计器 (`45/45`) 完整闭环**：已在 [`realhw_filesettings_shotmark_tcregen_and_reclamp_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_filesettings_shotmark_tcregen_and_reclamp_auditor.py) 完成 `PHASE_218_SCHEMA` (`218.0.0`, `AUDITOR_INDEX_P218 = "45/45"`) 落地，导出至 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)，并在 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) 注册独立 CLI 子命令 `audit-realhw-filesettings-shotmark-tcregen-reclamp` 与总控 `audit-all` (`45/45`)，同步更新 [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/README.md)。
2. **有界 `os.O_RDONLY` + `os.pread` 极速扫描与洁净室字节级确定性**：本地真机 Donor 六件套（`FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 的 `appFw.so`、`.uxc`、`CPAPP-B.BIN`）冷启动扫描实测耗时 **`0.1025s`**（严格小于 `< 0.15s` 硬预算，进程内 `_DONOR_SCAN_CACHE_P218` 命中 `< 1ms`）；`CPAPP-B.BIN` 严格执行头部 `768 KiB` + 尾部 `6 MiB`（合计 `7,077,888 B`）有界读取，`raw_firmware_bytes_leaked == 0`（Donor 报告 SHA-256：`762b9c4e5ef769a06140353632d465a8daa3172e4d5da0e9007c6e984dcf103b`；洁净室报告 SHA-256：`ad21f49a883a64dd9a310d295a95c26a1d46db72c6bf222d68c79b3c75fa1513`）。
3. **全量双模回归 `100%` 绿灯**：新增 [`test_realhw_filesettings_shotmark_tcregen_and_reclamp.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/tests/test_realhw_filesettings_shotmark_tcregen_and_reclamp.py) **55 项**双模单测（`0.333s` 全过）；`outputs/fx3-firmware-lab/tests` 全量 **1,738 项**单测在本地 Donor 模式（`56.093s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式（`26.402s`，含跨子进程 `audit-all --clean-room --json` 45 号审计器字节级一致性断言）全部 `100%` 通过，`scripts/run_all_lab_tests.py --clean-only` `1.16s` 全绿。

---

## 2. 四大实证支柱（实测二进制证据 vs 硬件规则建模）

### Pillar A — `[File Settings]` 5 模式双槽命名、`<= 37` ASCII 字符集、SDHC FAT32 强制锁与 `Shot Mark1/2` XML 侧车
- **实测二进制事实（`O_RDONLY`）**：
  - 原厂 `FX3 Ver. 7.02` (`appFw.so` `79,015,712 B` + `string_english_f.uxc` `373,820 B`) 与 `FX6 Ver. 6.01` (`appFw.so` `50,520,424 B` + `string_english.uxc` `118,208 B`) 共享 `N5model27setting_xavcs_file_number_tE`、`N5model30sequence_set_file_number_resetE`、`set_clip_title_name` 与 `N5model22sequence_add_shot_markE`。
  - `FX3 Ver. 7.02` 检出独有符号 `BKID_APP_setting_xavcs_file_number`、`BKID_APP_setting_xavcs_file_name_reel_number`、`file_settings_title_name_settings`、`EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_1_ON`、`EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_2_ON`、`BKID_APP_setting_image_jump_dial` 与 `AUTO_FTP_TRANSFER_TARGET_MOVIE_MOVIE_SHOT_MARK`；英文语言包 `string_english_f.uxc` 精确包含 `File Settings`、`File Name Format`、`Cam ID + Reel#`、`Date + Title`、`Title + Date`、`Title Name Settings`、`Series Counter Reset`、`Shot Mark1`、`Shot Mark2`、`Image Jump Setting`、`Only Shot Mark Mov.`。
- **精确文件与侧车契约建模**：
  - 完整建模 Slot 1、Slot 2 与 `[Simult. Recording]`（双卡生成完全同名 `.MP4` 与 `*M01.XML`）下的 5 种 `[File Name Format]`：`[Standard]` (`C0001`)、`[Cam ID + Reel#]` (`A001C0001`)、`[Title]`、`[Date + Title]`、`[Title + Date]`，以及 `[File Number]`（`[Series]` 跨换空卡延续、`[Reset]` 空卡回 `0001`、`[Series Counter Reset]` 强制归 `0001`、`9999 -> 0001` 回绕）。
  - `[Title Name Settings]` 严格限制为 **`1 .. 37` 个单字节允许 ASCII 字符**（`A-Za-z0-9` + `.-_@!#$%+=^~(),;[]`），拦截 `38+` 字符、空格、斜杠及多字节 Unicode，且修改标题严格只作用于后续新录素材（`retroactive_rename_existing_clips = False`）。
  - **SDHC (`<= 32 GB` FAT32) 强制锁**：任一活跃录制卡槽插入 `SDHC_FAT32` 卡时，强制将 `[File Name Format]` 钳位至 `[Standard]` 并禁止新建自定义视频目录（锁定 `/PRIVATE/M4ROOT/CLIP`）。
  - **`Shot Mark1/2` 侧车与筛选**：实时录制与回放编辑落盘至 `/PRIVATE/M4ROOT/CLIP/<STEM>M01.XML`，完整覆盖 `[Image Jump Setting]` 四档（`Shot Mark Only`、`Shot Mark1 Only`、`Shot Mark2 Only`、`No Shot Mark`）与 FTP `[Only Shot Mark Mov.]` / `[Only Shot Mark]` 过滤。

### Pillar B — `[TC/UB]` `[Time Code Make: Regenerate]` Slot-1 独占主读、强制 `[Rec Run]` 与 `VMC-BNCM1` `EXT-LK` 即时释放
- **实测二进制事实（`O_RDONLY`）**：
  - `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` `appFw.so` 共享 `N5model17setting_tc_make_tE`、`N5model16setting_tc_run_tE`、`N5model24setting_hdmi_tc_output_tE`；`FX3 Ver. 7.02` 检出独有符号 `EXTERN_VAL_TC_MAKE_REGENERATE`、`CAUTION_ID_FACTOR_TC_MAKE_REGENERATE_MSG`、`BKID_APP_setting_tc_run`、`BKID_APP_setting_hdmi_tc_output` 与 `No301_EXTLK`；双方 `CPAPP-B.BIN` 有界切片均检出 `EXTERNALTC_CHECK`、`EXTERNALTC_LOCK`、`cpActTcub`、`Vitc/LTC/DPACK`。
- **精确时间码与外部锁状态机建模**：
  - `[Time Code Make: Regenerate]` 从当前活跃卡槽读取末尾片段结束时间码并按 `+1 frame`（支持 `23.98p / 24.00p / 25p / 29.97p / 50p / 59.94p` NDF 与 `29.97p / 59.94p` DF 整分非整十分跳帧，空卡从 `00:00:00:00` / `00:00:00;00` 起步）衔接；在 **`[Simult. Recording]` 下独占只读 Slot 1 末尾时间码**（忽略 Slot 2 历史时间码），且无视 `[Time Code Run]` 请求强制按 **`[Rec Run]`** 步进。
  - 经 Multi/Micro USB 接入 `VMC-BNCM1` 达成 `EXT-LK`（需同时满足 `Movie` + `[Preset]` + `[Free Run]`）后，一旦切换 `[Time Code Make]`、切换 `[Time Code Run]` 或切入 `S&Q`，**立即释放 `EXT-LK` 外部锁定**。
  - `S&Q` 慢快动作模式下硬性锁定禁用 `[Time Code Run]` 菜单与 HDMI `[Time Code Output]`（强制钳位为 `[Off]`）。

### Pillar C — `ILME-FX3` `[REC Lamp]` 3 态后+顶联动 Tally、独立 HDMI 红框与 `[Silent Mode]` -> `[Audio signals]` 硬锁
- **实测二进制事实（`O_RDONLY`）**：
  - `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` `appFw.so` 共享 `N5model18setting_rec_lamp_tE`、`N5model21setting_silent_mode_tE`、`N5model23setting_audio_signals_tE`；`FX3 Ver. 7.02` 精确检出三态枚举 `VAL_setting_rec_lamp_REC_LAMP_ALL_LIGHTS_UP`、`VAL_setting_rec_lamp_REC_LAMP_ONLY_FRONT_OFF`、`VAL_setting_rec_lamp_REC_LAMP_ALL_LIGHTS_OUT` 及 `VAL_setting_audio_signals_AUDIO_SIGNALS_OFF`（而 `FX6 Ver. 6.01` 为独立 `BKID_APP_SETTING_FRONT_TALLY` / `BKID_APP_SETTING_REAR_TALLY`）。
- **精确物理 Tally 与静音互锁建模**：
  - `ILME-FX3` `[REC Lamp]` 仅支持 3 态：`[All On]`（前、后、顶部 `REC` 键三灯同亮）、`[Only Front Off]`（熄灭前灯，但**后置录制灯与顶部机身 `REC` 键内置红灯保持物理同相常亮** `rear_and_top_coupled_equal = True`）、`[All Off]`（三颗物理灯全灭）；严禁注入 `Only Rear Off`、`Only Top Off` 等非 FX3 独立 Tally 模式。
  - 在 `[REC Lamp] = [All Off]` 下开启 `[Emphasized REC Display] = [On]` 时，若外接 HDMI 且 `[HDMI Info. Display] = [On]`，红色录制边框独立输出至外置 HDMI 监视器（不点亮任何机身物理 LED）。
  - 开启 `[Silent Mode] = [On]` 时，硬性将 `[Audio signals]` 锁死在 `[Off]`，屏蔽对焦合焦与自拍倒计时蜂鸣音。

### Pillar D — 硬件零写防火墙与 `P218-01 .. P218-12` 12 触点四分类矩阵
- 完整建立 `P218-01 .. P218-12` 共 **12 个固件/硬件触点**，覆盖 `NATIVE_PASSTHROUGH`（5）、`SHIM_TRANSLATED`（5）、`MASKED_ABSENT_HW`（1）、`HARD_WRITE_PROTECTED`（1）全部四类桥接等级。
- 零写防火墙拦截对 `p2:/setting/Backup.bin`、`BODYDATA.DAT`、`p5:/wbi`、`p8:/cpapp-b.bin`、`p12:/cert`、`p18:/lens`、`/dev/cnflasha*` 与 `spi_nor:` 的全部持久化写入，仅放行易失性 `/tmp/fx6_wave29_filesettings_tcregen_reclamp_overlay` 与 `ram://`（对未知非易失路径默认拒绝 fail-closed）。
- **边界声明**：本阶段全部工作均为本地主机侧离线 `O_RDONLY` 二进制取证与洁净室状态机建模，**未触碰端口 `8768`，未连接任何物理相机 USB，未生成或下发任何刷机载荷或闪存写入指令**。

---

## 3. 交付文件清单（严格限定归属范围内 6 个文件）

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_filesettings_shotmark_tcregen_and_reclamp_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_filesettings_shotmark_tcregen_and_reclamp_auditor.py)（新增：第 45 号里程碑审计器 `45/45` 实现）
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 218 公共常量、数据类与评估入口）
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：注册 `audit-realhw-filesettings-shotmark-tcregen-reclamp` 并接入 `audit-all` `45/45`）
4. [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/README.md)（更新：补充第 45 号里程碑审计器 `45/45` 架构说明与 CLI 用法）
5. [`outputs/fx3-firmware-lab/tests/test_realhw_filesettings_shotmark_tcregen_and_reclamp.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/outputs/fx3-firmware-lab/tests/test_realhw_filesettings_shotmark_tcregen_and_reclamp.py)（新增：55 项双模单测）
6. [`reports/2026-11-15-phase218-realhw-45th-auditor-filesettings-shotmark-tcregen-reclamp/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/reports/2026-11-15-phase218-realhw-45th-auditor-filesettings-shotmark-tcregen-reclamp/README.md)（新增：本交付报告；上游情报参考 [`Wave-29 README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h241-phase218-45th-auditor-filesettings-shotmark-tcregen-reclamp/reports/2026-11-15-global-sony-wave29-file-settings-sdhc-shotmark-tc-regenerate-slot1-reclamp-coupled-tally-intel/README.md)）

---

## 4. 验证命令与实测结果

| 验证项 | 命令（均带 `/usr/bin/python3 -B`） | 实测结果 |
| :--- | :--- | :--- |
| 第 45 号审计器 CLI | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-filesettings-shotmark-tcregen-reclamp --json` | `all_checks_passed: true`, `auditor_index: "45/45"`, 冷扫 `0.1025s` (`< 0.15s`) |
| 总控 `audit-all` (`45/45`) | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --clean-room --json` | `all_checks_passed: true`（45 号审计器在线且 Donor / 洁净室双模全绿） |
| Phase 218 单测（双模） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_realhw_filesettings_shotmark_tcregen_and_reclamp.py" -v` | `Ran 55 tests in 0.333s — OK`（本地 Donor 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 均全过） |
| 固件实验室全量单测（Donor） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1738 tests in 56.093s — OK` |
| 固件实验室全量单测（洁净室） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1738 tests in 26.402s — OK (skipped=6)` |
| 全局零字节码/合规门禁 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 1.16s`（零 `.pyc` / `__pycache__` / 专有二进制残留） |
