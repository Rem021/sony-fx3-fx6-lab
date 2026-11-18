# Phase 339：VM HIL Stage 74（`74/74` 协同仿真里程碑 — Wave 64：`[Breathing Comp.]` `120p/100p`/RAW/S&Q & Catalyst Prepare-Only 勘误、电影 `[File Settings]` `Cam ID + Reel#`/`37` 字符标题/`SDHC` `4 GB` 分割、`[Copyright Info]` `46` 字符 & `[Write Serial Number]` Reset 免疫 & `CAMSET` 隔离、以及 `[Auto Power OFF Temp.]`/9 条件 `[Power Save Start Time]`/休眠 `[Power Save by Monitor]`/`[NTSC/PAL Selector]` `Slot 1` `EROFS=30` 防火墙 HIL）

- **日期**：`2026-11-17`
- **任务 / 分支**：`H416`（`task_d0d0f2a08a62`） · `codex/h416-phase339-vm-stage74-breathing-camid-copyright-powersave-ntsc-pal-hil`
- **权威输入源**：[`Wave 64 实机情报报告`](../2026-11-17-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/README.md)
- **硬件安全红线**：`physical_device_writes = 0`、`persistent_emmc_writes_authorized = False`、`emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`hardware_live_attachment_authorized = False`、`overall_ready_for_hardware_attach = False`、`slot1_data_sector_writes = 0`、`slot1_avf_info_mutated = False`、`emmc_nflasha_write_count = 0`、`rf_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`

---

## 核心结论速览（Conclusion First）

1. **Stage 74（`74/74` VM HIL 里程碑）已完成实现、全板接入与多模式验证**：
   - 新增 [`realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py`](../../outputs/fx3-vm/realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py)（Schema `phase339_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulation_v1`）及其 `96` 项四模式单元测试 [`test_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py)，并接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为 `stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil`（支持 `--include-stage74`、`--skip-stage74`、`--no-include-stage74`、`--skip-phase339`，推进全板舞台至 **`vm_stages=74/74`**）。
   - 双模式 `make verify-milestone-324` 实测通过：`status=OK`、`pillars=6/6`、`gate142=143/146`、`recovery=60/60`、`auditors=45/45`、`vm_stages=74/74`、`h0_eq_h3=16/16`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`usb_tx=0`、`leaked=0`；`outputs/fx3-vm` 全量发现双模式 `4205/4205` 通过（默认供体 `234.302s`，洁净室 `skipped=23`, `233.930s`）。
2. **18 份真实供体 `os.O_RDONLY` + 受界 `os.pread` 与 `work_root is None` 洁净室回退**：
   - **`实测事实`**：通过 `os.open(..., os.O_RDONLY)` 与受界 `os.pread`（`<= 4096 B`）完成 Wave-64 全部 **18 份本地真实供体**（`12` 份 FX3 四语 `_f` / 基础 / `_g` `.uxc` + `libSaveLoadSettings.so` `18,760 B` + `2` 份 FX6 英文 `.uxc` + `FX3 appFw.so` `79,015,712 B`、`FX3-CX95900_ALLLANG-Backup.bin` `2,229,740 B`、`FX6 appFw.so` `50,520,424 B`）的只读校验，冷读 `< 0.20s`；`resolve_phase339_donor_paths(work_root)` 严格守卫 `if work_root is None: return None`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__` 及 Mock 无供体 CI 路径下零异常切换至 `CLEAN_ROOM_SYNTHETIC`（`raw_firmware_bytes_leaked = 0`）。
3. **Wave-64 四大实机子系统闭环（严格区分 `实测事实` vs `推断`）**：
   - **74A `[Breathing Comp.]` `Ver. 3.00+` Reset 反对称、`120p/100p`/RAW/S&Q 锁死 & Catalyst Prepare-Only 勘误**：
     - **`实测事实`**：`Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（`Off[def]` / `On`）在 `ilc/2210` 中与同组抗 Reset 的 `Shading` / `Chromatic` / `Distortion Comp.` 不同，**可被 `[Camera Settings Reset]` 复位（`Can be reset`）**。真机在 Still 模式、普通电影 `119.88p / 100p`、`S&Q >= 100/120fps`（`<100/120fps` 的 S&Q 在 FX3 可用，而 FX6 禁用全部 S&Q）、HDMI 16-bit `RAW Output`、增距镜 `SEL14TC`/`SEL20TC`、`SEL100F28GM` 微距环 `0.57m–1.0m`、第三方/手动镜头、数字变焦与 `Auto Framing` 下均禁用机内呼吸补偿；机内 `Off` 时的后期元数据呼吸补偿为 **付费版 `Catalyst Prepare` / `Catalyst Prepare Plugin` 独占**且要求 `[Distortion Comp.] = Auto`（**免费版 `Catalyst Browse` 不支持** -> `EOPNOTSUPP=95`）。对比 `ILME-FX6 Ver. 6.01` `Technical > Lens > Breathing Compensation`（`Auto` / `Off`，在 `Distortion = Off`、全部 S&Q、及任何 RAW 编码下均硬锁 `Off`）。
     - **`推断`**：若台架同时启用机内 `On` 与 `Catalyst Prepare` 后期补偿或启用 HDMI RAW/120p，VM 状态机必须返回 `EINVAL`/`EOPNOTSUPP` 或旁路机内裁剪，防止错误估算视场角及裁切管线。
   - **74B 电影 `[File Settings]` Reset 免疫、`Cam ID + Reel#`（`C999 -> D001` / `YYMMDD`）、`37` 字符 `Title`、`SDHC` `4 GB` 分割 & `Slot 1` `EROFS=30`**：
     - **`实测事实`**：`Shooting -> [File] -> [File Settings]` 全部子项抗 `[Camera Settings Reset]`（`Not available`，仅 `[Initialize]` 复位；目录固定 `PRIVATE/M4ROOT/CLIP/*.MP4`）：`File Number`（`Series[def]` / `Reset` + `Series Counter Reset` 在目录非空时设 `max + 1`）、`Cam ID + Reel#`（`YYMMDD` 6 位日期；到达 `999` 时触发 `C999 -> D001` 文件名位置字母递增而菜单 `[Camera Position]` 保持不变；更改 `Camera ID` 重置 `Reel#` 至 `001` 而 `File Number = Reset` 保留 `Reel#`）、`Title`（上限 `37` 字符，默认 `"C"`）、`Date + Title` / `Title + Date`（`YYYYMMDD` 8 位日期）；`SDHC`（`FAT32 <= 32 GB`）强制锁死 `Standard` 与 `4 GB` 文件分割且禁止与 `exFAT` 卡混用 `[Simult. Recording]`（`EINVAL=22`）。对比 `ILME-FX6` `TC/Media > Clip Name Format`（`Auto Naming = Cam ID + Reel# / Title`，`Title Prefix` `4..46` 字符默认 `nnn_`，`/XDROOT/Clip/*.MXF` 或 `/PRIVATE/XDROOT/Clip/*.MXF` 并支持卡内片段继承）。
     - **`推断`**：当 `Slot 1` 挂载 Tier-0 只读恢复保险库时，任何落盘录制、Reel 更新或 `Series Counter Reset` 写卡企图均由台架防火墙阻断返回 `EROFS=30`（`slot1_data_sector_writes = 0`）。
   - **74C `[Copyright Info]` `46` 字符、Still+Movie `[Write Serial Number]` Round-57 Reset 勘误修复 & `CAMSET*.DAT` 隔离**：
     - **`实测事实`**：直接对照 `ilc/2210` *List of default setting values* 与 `FX3 appFw.so` 证实：**`[Copyright Info]` 全部 4 项（`Write Copyright Info`、`Set Photographer` `<= 46` ASCII、`Set Copyright` `<= 46` ASCII、`Disp. Copyright Info`）以及 `[Write Serial Number]` 全部 5 项均抗 `[Camera Settings Reset]`（`Not available`）**——正式修复 Round-57 认为 Reset 会清空 `Write Copyright Info` 开关的勘误（仅 `[Initialize]` 清零）；且 `[Write Serial Number]` 在 `Ver. 2.00..7.02` 已由初版 Still-only（`BKID_APP_setting_still_write_serial_number`）升级为 **Still + Movie 活跃** 的 `BKID_APP_setting_write_serial_number_still_movie`；`[Save/Load Settings]`（`CAMSET*.DAT`）明确排除 `Copyright Info`（0 字节 PII 泄漏），而 `Write Serial Number` 仅记录开关状态且不泄漏机身物理序列号。对比 `ILME-FX6` 无消费级 EXIF 版权菜单，仅追踪 `CURRENT/PRESET_LENS_SERIAL_NUMBER0..5`。
     - **`推断`**：向 `Slot 1` 发起静态拍照/录影写入或导出 `CAMSET*.DAT` 至 `Slot 1` 时，Tier-0 守卫必须 fail-closed 返回 `EROFS=30`，且序列化 JSON/CAMSET 工件严禁出现任何摄影师姓名、版权串或真实机身序列号。
   - **74D `[Power Setting Option]`（6 档 / 9 条件 / 100% 休眠 `[Power Save by Monitor]`）+ `[NTSC/PAL Selector]` `Slot 1` `EROFS=30` 格式化防呆**：
     - **`实测事实`**：`Setup -> [Power Setting Option]` 抗 Reset，FX3 `Ver. 7.02` 仅暴露 6 档活跃 `[Power Save Start Time]`（`Off`/`30 Min`/`5 Min[def]`/`2 Min`/`1 Min`/`10 Sec`，而 `20 Sec`/`30 Sec`/`60 Min`/`240 Min`/`No Limit` 为休眠档位 -> `EOPNOTSUPP=95`），受 **9 类官方自动旁路条件**控制；`[Auto Power OFF Temp.] = High` 触发仅建议三脚架使用的告警；**`[Power Save by Monitor]`**（`BKID_APP_setting_monitor_power_linkage`）在无 EVF 眼感应器的 FX3 上 **100% 休眠**（`EOPNOTSUPP=95`）。`[NTSC/PAL Selector]` 抗 Reset，切换触发强制自动重启与 `Running on NTSC.` / `Running on PAL.` 横幅；`PAL` 禁用 `23.98p` 与 `DF` 丢帧时间码（强制 `NDF`）并阻止跨制式回放（`_g`）；对比 `ILME-FX6` `Project > Rec Format > Frequency`（`59.94/50/29.97/25/24/23.98`，无消费级格式化弹窗）。
     - **`推断`**：由于双代 `base.uxc` 中依然保留 `Format? Slot 1` / `SD-Erase` 弹窗提示字符串，台架必须将针对 `Slot 1` 的格式化/SD-Erase/TRIM 操作作为高危故障门控，强制 fail-closed 返回 `EROFS=30`（`slot1_data_sector_writes = 0`）。

---

## 交付物与验证矩阵

| 交付文件（严格 5/5 文件所有权） | 职责与核心结果 |
| :--- | :--- |
| [`realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py`](../../outputs/fx3-vm/realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py) | Stage 74（Phase 339，`74/74` 里程碑）主协同仿真器 + 18 供体 `os.O_RDONLY` / 受界 `os.pread`（`<=4096 B`）与 `work_root is None` 洁净室回退 |
| [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil`（支持 `--include-stage74` / `--skip-stage74` / `--no-include-stage74` / `--skip-phase339`，推进 `vm_stages=74/74`） |
| [`test_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py) | `96` 项四模式单元测试（覆盖 18 供体、`74A` Breathing Comp. & Catalyst Prepare-Only、`74B` File Settings & Cam ID/Reel# & SDHC 4GB/Slot-1、`74C` Copyright 46ch & Write Serial Reset 免疫/CAMSET、`74D` Power Save 6/9/休眠 Monitor & NTSC/PAL 防呆及 Suite 篡改检测） |
| [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 追加 Phase 339 Stage 74（`74/74` 里程碑）架构说明与四模式 CLI/测试命令 |
| [`reports/2026-11-17-phase339-vm-stage74-breathing-camid-copyright-powersave-ntsc-pal-hil/README.md`](README.md) | 本工程结案报告（结论先行，严格区分 `实测事实` 与 `推断`） |

### 实测验证记录

| 验证项 | 模式 / 命令 | 实测结果 |
| :--- | :--- | :--- |
| Stage 74 独立三模式自检 | `realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py --self-test --summary`（默认 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 全部 `[PASS]`（`mode=LOCAL_DONOR_O_RDONLY` / `CLEAN_ROOM_SYNTHETIC`，`hfr=100.0fps`, `cat_browse=0`, `title=37ch`, `sdhc=4GB`, `copy=46ch`, `ps=6/9`, `mon=0`, `s1_wr=0`, `leak=0`；digest `44c7c269adf8` / `62d271b7d14c`） |
| Stage 74 单元测试（四模式） | `unittest outputs/fx3-vm/tests/test_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py`（默认 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__`） | 正常模式 `96/96 OK`（`4.085s`）；`FX3_CLEAN_ROOM_TEST=1`（`3.679s`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（`1.615s`）与无供体哨兵回退（`3.330s`）均为 `96` run, `skipped=3`, `OK`（`0` 失败/`0` 错误） |
| 全板 74 阶段 Suite CLI | `fx3_vm_coemulation_suite.py --summary`（`LOCAL_DONOR_O_RDONLY` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 全部退出 `0`（`m74=74/74`, `hfr=100.0p`, `title=37ch`, `sdhc=4GB`, `copy=46ch`, `pwr=6/9`, `mon_dorm=0`, `s1_wr=0`, `emmc_wr=0`；digest `105483769e7e` / Clean-Room `6ebbcd50a4ed`；Stage 74 独立确定性 digest `62d271b7d14c...`） |
| `outputs/fx3-vm` 全量发现 | `unittest discover -s outputs/fx3-vm/tests -t outputs/fx3-vm -p 'test_*.py'`（正常与 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 默认供体模式 `4205/4205 OK`（`234.302s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` `4205` 项通过（`skipped=23`, `233.930s`, `0` 失败/`0` 错误） |
| Master Gate 里程碑校验 | `make verify-milestone-324` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | 4 次校验全数 `status=OK`、`pillars=6/6`、`gate142=143/146`、`recovery=60/60`、`auditors=45/45`、`vm_stages=74/74`、`h0_eq_h3=16/16`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`usb_tx=0`、`leaked=0`（`milestone324_sha256`: `ca6684a07e996d3e...` / `343720e2c404b6bf...` / `c66615269e7cfafa...` / `fb3530ac9854f90f...`） |
| 工作区卫生审计 | `make clean-audit` | `[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.05s)` · `ALL GREEN in 0.05s`（零 `.pyc`、零未跟踪杂文件，仅 5 个自有文件变更） |
