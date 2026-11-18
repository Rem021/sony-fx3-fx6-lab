# Phase 361 里程碑交付报告：Recovery Pillar 66（Wave-64）与 `66/66` 统一恢复总检（`verify-66pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`66/66` 恢复支柱闭环里程碑达成，`VERIFIED_66OF66_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 64 全球实机情报报告](../2026-11-17-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `0x91030080` `PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `PRODUCT_MODEL_CHAPLIN`），落地 **Phase 361 Recovery Pillar 66**（Sub-Pillar **66A** `6/6` + Sub-Pillar **66B** `6/6`）及并发式 **`66/66` 统一恢复总检聚合器** [`evaluate_realhw_66pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py)（`schema_version = "realhw_66pillar_recovery_master_v1"`，`verify-66pillar-recovery` / `verify-pillar66-recovery`），并通过包根动态导出自动接入 `realhw_milestone349_master_gate.py` 与 `realhw_milestone311_master_gate.py`（`recovery=66/66`），未修改 `Makefile`、`outputs/fx3-safety/`、`outputs/fx3-vm/`、`outputs/fx6-on-fx3-closure/` 或其他任何未授权文件。
  2. 全量实现无供体 CI 防护与有界只读取证：[`_resolve_phase361_donor_path`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py) 内置 `work_root is None` 防护，[`inspect_phase361_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py) 严格以 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 在 `<= 2.0s` 预算内检验 **18 项** Wave-64 本地供体（15 项 `FX3 7.02` 含 `libSaveLoadSettings.so` `18,760 B` + 3 项 `FX6 6.01`；大文件仅读前 `4096B` 头部，小文件全量校验），并在缺少本地供体或 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时安全回退至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
  3. 严格仅创建/编辑本次授权的 **6 个所属文件**，零无关目录变更。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar66-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`66A=6/6`、`66B=6/6`，`18` 项 Wave-64 本地供体严格 `O_RDONLY` 核验通过，`elapsed_seconds=0.006`，`suite_sha256=ab0480fac143d07e`（64 位完整摘要 Prefix），`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`66A=6/6`、`66B=6/6`，`elapsed_seconds=0.001`，`suite_sha256=b7aa189f6cf7cf09`，`raw_firmware_bytes_leaked=0`。
  - `verify-66pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=66/66`，`all_passed=True`，`elapsed_seconds=1.372`（`< 1.5s` 快速 CLI 预算，`under_1_5s_fast_cli_budget=True`），`master_66pillar_sha256=248076720f2b7a1c`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=66/66`，`all_passed=True`，`elapsed_seconds=0.914`（`< 1.5s` 快速 CLI 预算，`under_1_5s_fast_cli_budget=True`），`master_66pillar_sha256=6fcf3cd410bf7b69`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI（`patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))`）：146 项完整套件 `146/146 OK`（`27.185s`），自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=66/66`，`raw_firmware_bytes_leaked=0`。
  - `verify-milestone-349`（双模）与 `verify-milestone-311 --force-clean-room`：
    - `verify-milestone-349` 正常模式（`LOCAL_DONOR_O_RDONLY`）：`status=OK pillars=6/6 gate148=151/154 recovery=66/66 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=79/79 preflights=20/20 h0_eq_h3=16/16 e_nd_tx=0 rf_pkts=0 slot1_writes=0 qemu=48/48(144/144) pngs=96/96(max=27467B) ready_attach=False leaked=0`（`milestone349_sha256=b4812780afa4ab70...`）。
    - `verify-milestone-349 --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`status=OK ... recovery=66/66 ... leaked=0`（`milestone349_sha256=2b69e0deb9c43520...`）。
    - `verify-milestone-311 --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`status=OK ... gate134=151/154 recovery=66/66 ... ready_attach=False leaked=0`（`milestone311_sha256=28f8da27a5b93ccf...`）。
  - **硬件安全护栏硬锁**：`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-64 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/`libSaveLoadSettings.so`/UXC/`Backup.bin`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**推断 / 工程安全护栏**。

### 2.1 Sub-Pillar 66A：`[Breathing Comp.]` 光学裁切 / `120p` + `S&Q >= 100fps` + `RAW` / `Catalyst Prepare` vs FX6 3 锁与电影 `[File Settings]`

1. **实测事实 — `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（Ver. 3.00+..7.02）**：
   - 默认 `Off`（可选 `On`）；与同组 3 项（`Shading Comp.`/`Chromatic Aberration Comp.`/`Distortion Comp.` 为 `Not available`）不同，唯独 **`[Breathing Comp.]` 标注 `Can be reset`**（会被 `[Camera Settings Reset]` 复位为 `Off`）。
   - 控制链：`BKID_APP_setting_lens_comp_breathing` + `PRM_HAITA_breathing_correction_lens_type_lens_information`（`SUPPORT`/`NOT_SUPPORT`/`NA`），明确排除 `SEL100F28GM` 微距环 `0.57m..1.0m` 档及 `SEL14TC` / `SEL20TC` 增距镜。
   - **禁用与旁路边界**：在 **Still** 静态、常规电影 **`119.88p / 100p`（`120p`）** 与 **`S&Q >= 100/120fps`** 下强制禁止（`EOPNOTSUPP=95`），但在 **`S&Q < 100fps`** 下 FX3 仍可启用；在 `Clear Image Zoom > 1.0` / `Auto Framing` / `Framing Stabilizer` 下菜单保持可选但旁路独立裁切与后期元数据；在外录 HDMI 16-bit **`RAW Output`** 上旁路不裁切（`effective_breathing = "Off"`、`optical_crop_active = False`）。
   - **Catalyst 纠偏**：**`Catalyst Browse` 不支持**后期呼吸补偿；元数据后期补偿为付费版 **`Catalyst Prepare` / `Catalyst Prepare Plugin`** 独占能力，且拍摄前机内 **`[Distortion Comp.]` 必须设为 `[Auto]`**。
   - **对照 `ILME-FX6 Ver. 6.01`**：位于 `Technical > Lens > Breathing Compensation`（`Auto` / `Off`），在以下 **3 项条件**下硬锁定 `Off`：① `Distortion Comp. = Off`；② **全部** `S&Q Motion = On`（不限帧率）；③ 任何含 `RAW` 编码（`RAW` / `RAW & XAVC-I` / `RAW(HDMI)` / `RAW(HDMI) & XAVC-I`）。
2. **实测事实 — `Shooting -> [File] -> [File Settings]` 全项抗 Reset 与日期格式分化**：
   - `[File Number]`、`[File Name Format]`、`[Cam ID + Reel# Settings]`、`[Title Name Settings]` 全部为 **Reset 免疫（`Not available`）**，仅 `[Initialize]` 还原默认值。
   - `[File Number]`：`Series`（跨 Slot 1/2 连续递增）/ `Reset` + `[Series Counter Reset]`（若目录已有片段则重置为 **`max + 1`**）。
   - `[File Name Format]`（5 模式）：`Standard`、`Cam ID + Reel#`、`Title`、`Date + Title`、`Title + Date`；使用 **`SDHC <= 32GB (FAT32)`** 时强制锁死 **`[Standard]`**（`EOPNOTSUPP=95`）、XAVC S 按 **`4 GB`** 自动分割，并禁止 `FAT32 + exFAT` 混卡 `[Simult. Recording]`。
   - **`[Cam ID + Reel# Settings]`**：修改 `Camera ID`（`A..Z`）会重置 `Reel Number`（`001..999` -> `1`），而执行 `File Number = Reset` **不会**重置 `Reel Number`；`Camera Position`（`C/L/R`）在序号超过 `999` 时**仅输出文件名顺延递增**（如 `C999 -> D001`），菜单设定值本身保持不变；`Cam ID + Reel#` 使用 **6 位 `YYMMDD`** + 2 位随机字符，而 `Date + Title` / `Title + Date` 使用 **8 位 `YYYYMMDD`**。
   - **`[Title Name Settings]`**：上限 **`37` 字符**，默认 **`"C"`**，电影存储目录固定为 **`PRIVATE/M4ROOT/CLIP`**。
   - **对照 `ILME-FX6 Ver. 6.01`**：位于 **`TC/Media > Clip Name Format`**（`Cam ID + Reel#` / `Title`），`Title Prefix` 支持 **`4..46` 字符**（默认 `nnn_`），具备卡内片段继承（`DIADEM_PRO` 符号），目录为 `/XDROOT/Clip/*.MXF`（CFexpress Type A）或 `/PRIVATE/XDROOT/Clip/*.MXF`（SDXC）。
3. **推断 / 安全护栏（Tier-0 `Slot 1 EROFS=30` 防火墙）**：
   - 将 `BKID_APP_update_required_xavcs_file_name_reel_number` 等写卡状态刷新动作锁闭在 Tier-0 `Slot 1` 只读守卫之后，任何写/改卡操作均 fail-closed 返回 `EROFS (errno 30)`（`slot1_data_sector_writes == 0`），Stage-B 覆写仅限 `/tmp/fx3_stage_b_overlay/pillar66`，并核验 `Backup.bin H0 == H3`（`16/16`）。

### 2.2 Sub-Pillar 66B：`[Copyright Info]` `46` 字符抗 Reset（Round 57 勘误）/ 活跃 `[Write Serial Number]` / `CAMSET` 隔离与 `[Power Setting Option]` / `[NTSC/PAL Selector]`

1. **实测事实 — `[Copyright Info]` 与 `[Write Serial Number]`（显式 Round 57 勘误）**：
   - **Round 57 勘误纠正**：`ilc/2210` *List of default setting values* 证实，`[Copyright Info]` 全部 4 项（含 **`[Write Copyright Info]`** `Off`/`On` 开关本身、以及 `<= 46` ASCII `[Set Photographer]`、`<= 46` ASCII `[Set Copyright]`、`[Disp. Copyright Info]`）与 **`[Write Serial Number]`**（`Off`/`On`）**均标注 `Resettable using [Camera Settings Reset]: Not available`**；唯有 `[Initialize]` 清除 PII 字符串并将开关复位 `Off`。
   - **Ver. 7.02 活跃域**：`[Write Serial Number]` 在 Ver. 2.00..7.02 上已由初版 Still-only 升级替换为全域 **`BKID_APP_setting_write_serial_number_still_movie`**（`_f 0x6704`，覆盖 **Still + Movie**）。
   - **`CAMSET*.DAT` 隐私隔离（`libSaveLoadSettings.so` `18,760 B`）**：`Copyright Info` 被官方严格排除出 `CAMSET*.DAT` 导出表（0 字节 PII 泄漏），而 `Write Serial Number` 布尔开关可随配置保存（不含机身序列号字符串），且卡内 `CAMSET` 最多 `10` 组。
   - **对照 `ILME-FX6 Ver. 6.01`**：无消费级 EXIF `[Copyright Info]` 菜单，仅活跃追踪镜头序列号 `CURRENT/PRESET_LENS_SERIAL_NUMBER0..5`。
2. **实测事实 — `Setup -> [Power Setting Option]` 与 `[NTSC/PAL Selector]`**：
   - **`[Power Setting Option]`**（全项抗 Reset `Not available`）在 FX3 Ver. 7.02 上仅暴露 **2 项**：
     1. **`[Power Save Start Time]`**（`Off` / `30 Min` / `5 Min` 默认 / `2 Min` / `1 Min` / `10 Sec`；`20SEC`/`NO_LIMIT` 为休眠档位 `EOPNOTSUPP=95`），严格受官方精确 **9 大旁路条件**抑制（USB 供电、幻灯片播放、FTP 传输、电影录制中、连接 PC、连接 TV/HDMI、`IR Remote Ctrl=On`、`Bluetooth Rmt Ctrl=On`、流媒体/Creators' Cloud）；
     2. **`[Auto Power OFF Temp.]`**（`Standard` 默认 / `High` 三脚架警示 `_g 0x61a9`）；
     3. **`[Power Save by Monitor]`**（`BKID_APP_setting_monitor_power_linkage`）在无 EVF 的 FX3 上 **100% 休眠未暴露**（`dormant_power_save_by_monitor_exposed_events == 0`，请求返回 `EOPNOTSUPP=95`）。
   - **`[NTSC/PAL Selector]`**（抗 Reset `Not available`）：切换即触发自动重启（`base 0xe5c1`），非出厂制式开机弹出 `Running on NTSC.`（`base 0xe77a`）/ `Running on PAL.`（`base 0xe0b6`），以 `_g 0x61ca`/`0x644e` 阻止跨制式回放（强制匹配帧率与 DF/NDF 制式约束）；同时对 `base.uxc` 中内嵌的遗留格式化提示 `base 0xe595`（`"Format? Slot 1"` SD-Erase/TRIM 隐患）在台架侧实施硬核 `EROFS=30` 防火墙拦截。

---

## 3. 授权交付文件清单（Strict 6-File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py) | Pillar 66A/66B 状态机与评估器、18 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `66/66` 并发主控 `evaluate_realhw_66pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 361 全部 **293** 个公开符号与 `__all__`（不覆盖 Pillar 65 及先前导出） |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar66-breathing-camid-reel-copyright46-powersave-ntscpal-vault`、`verify-pillar66-recovery` 与 `verify-66pillar-recovery` CLI 子命令（`help=` 无未转义 `%`） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 361 Pillar 66 & `66/66` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier.py) | **146 项**（`>= 130`）四模（正常本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`work_root=None`）单元测试、参数化矩阵与 `66/66` 总控断言 |
| 6 | NEW | [`reports/2026-11-18-phase361-pillar66-66pillar-breathing-camid-reel-copyright46-powersave-ntscpal-vault/README.md`](README.md) | 本 Phase 361 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 66 单测（正常模式 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p 'test_realhw_66pillar_*.py'` | **`146/146 OK`**（`27.467s`） |
| Pillar 66 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p 'test_realhw_66pillar_*.py'` | **`146/146 OK`**（`25.116s`） |
| Pillar 66 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p 'test_realhw_66pillar_*.py'` | **`146/146 OK`**（`25.016s`） |
| Pillar 66 全套模拟无供体 CI（`work_root=None`） | `patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))` 全量发现执行 `test_realhw_66pillar_*.py` | **`146/146 OK`**（`27.185s`，`CLEAN_ROOM_SYNTHETIC`，`rc=0`，`leaked=0`） |
| `verify-pillar66-recovery` CLI（供体 / 洁净室） | `verify-pillar66-recovery` & `verify-pillar66-recovery --force-clean-room` | **`66A=6/6, 66B=6/6`**（`0.006s` / `0.001s`，`suite_sha256=ab0480fac143d07e` / `b7aa189f6cf7cf09`，`leaked=0`） |
| `verify-66pillar-recovery` CLI（供体 / 洁净室） | `verify-66pillar-recovery` & `verify-66pillar-recovery --force-clean-room` | **`66/66 PASS`**（`1.372s` / `0.914s` `< 1.5s`，`master_66pillar_sha256=248076720f2b7a1c` / `6fcf3cd410bf7b69`，`leaked=0`） |
| `verify-milestone-349`（双模） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-milestone-349`（及 `--force-clean-room`） | **`status=OK pillars=6/6 gate148=151/154 recovery=66/66 auditors=45/45 vm_stages=79/79 h0_eq_h3=16/16 slot1_writes=0 qemu=48/48(144/144) pngs=96/96(max=27467B) ready_attach=False leaked=0`** |
| `verify-milestone-311 --force-clean-room` | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-milestone-311 --force-clean-room` | **`status=OK pillars=6/6 gate134=151/154 recovery=66/66 cnflasha_ro=True ready_attach=False leaked=0`** |
| `fx3-recovery-adapter` 全套 74 文件全量发现（正常模式） | 前半 37 文件 + 后半 37 文件 `unittest` discovery（含 `test_realhw_65pillar_*` 与 `test_realhw_66pillar_*`） | **`1,672 OK (skipped=1)` + `2,779 OK` = `4,451 tests OK (skipped=1)`**（`583.900s`） |
| `fx3-recovery-adapter` 全套 74 文件全量发现（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1` 前半 37 文件 + 后半 37 文件 `unittest` discovery | **`1,625 OK (skipped=13)` + `2,768 OK (skipped=5)` = `4,393 tests OK (skipped=18)`**（`518.832s`） |
| 清洁审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **`ALL GREEN`** |
