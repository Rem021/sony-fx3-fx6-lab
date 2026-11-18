# Phase 355 里程碑交付报告：Recovery Pillar 65（Wave-63）与 `65/65` 统一恢复总检（`verify-65pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`65/65` 恢复支柱闭环里程碑达成，`VERIFIED_65OF65_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 63 全球实机情报报告](../2026-11-17-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `0x91030080` `PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `PRODUCT_MODEL_CHAPLIN`），落地 **Phase 355 Recovery Pillar 65**（Sub-Pillar **65A** `6/6` + Sub-Pillar **65B** `6/6`）及并发式 **`65/65` 统一恢复总检聚合器** [`evaluate_realhw_65pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py)（`schema_version = "realhw_65pillar_recovery_master_v1"`，`verify-65pillar-recovery` / `verify-pillar65-recovery`），并通过包根动态导出自动接入 `realhw_milestone349_master_gate.py`（`recovery=65/65`），未修改 `Makefile`、`outputs/fx3-safety/`、`outputs/fx3-vm/` 或 `outputs/fx6-on-fx3-closure/` 任何文件。
  2. 全量实现无供体 CI 保护与有界只读取证：[`_resolve_phase355_donor_path`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py) 内置 `work_root is None` 防护，[`inspect_phase355_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py) 严格以 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 在 `<= 2.0s` 预算内检验 **17 项** Wave-63 本地供体（14 项 `FX3 7.02` + 3 项 `FX6 6.01`；大文件仅读前 `4096B` 头部，小文件全量校验），并在缺少本地供体或 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时安全回退至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
  3. 严格仅创建/编辑本次授权的 **6 个所属文件**，零无关目录变更。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar65-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`65A=6/6`、`65B=6/6`，`17` 项 Wave-63 本地供体严格 `O_RDONLY` 核验通过，`elapsed_seconds=0.005`，`suite_sha256=ee73892dd9a4cb2f`（64 位完整摘要 Prefix），`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`65A=6/6`、`65B=6/6`，`elapsed_seconds=0.000`，`suite_sha256=87a1c4ea5e294ebd`，`raw_firmware_bytes_leaked=0`。
  - `verify-65pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=65/65`，`all_passed=True`，`elapsed_seconds=1.210`（`< 1.5s` 快速 CLI 预算，`under_1_5s_fast_cli_budget=True`），`master_65pillar_sha256=dede2577e44527b9`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=65/65`，`all_passed=True`，`elapsed_seconds=0.858`（`< 1.5s` 快速 CLI 预算，`under_1_5s_fast_cli_budget=True`），`master_65pillar_sha256=c9a585e87dc94e8b`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI（`patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))`）：148 项完整套件 `148/148 OK`（`19.850s`），自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=65/65`，`raw_firmware_bytes_leaked=0`。
  - `make verify-milestone-349`（正常模式 & `FX3_FX6_FORCE_CLEAN_ROOM=1`）：
    - 正常模式（`LOCAL_DONOR_O_RDONLY`）：`status=OK pillars=6/6 gate148=147/150 recovery=65/65 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=77/77 h0_eq_h3=16/16 e_nd_tx=0 rf_pkts=0 slot1_writes=0 qemu=47/47(141/141) pngs=94/94(max=27467B) ready_attach=False leaked=0`（`milestone349_sha256=3495b6c467f95971...`）。
    - 洁净室模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）：`status=OK ... recovery=65/65 ... leaked=0`（`milestone349_sha256=505803ce95ae9848...` / `538eb797b86ead8e...`）。
  - **硬件安全护栏硬锁**：`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-63 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`/`BODYDATA.DAT` 头部）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**推断 / 工程安全护栏**。

### 2.1 Sub-Pillar 65A：`[HDMI Output Settings]` `8` 项激活结构、`4264x2408` `16-bit` 线性 RAW 与 `Rec. Media dur HDMI Output` `Slot 1` Vault 防火墙

1. **实测事实 — `Setup -> [External Output] -> [HDMI Output Settings]` 8 项激活结构与 `[Color Gamut for RAW Output]` 移除**：
   - 该整页在 `Camera Settings Reset` 下全部抗 Reset（`Not available`，仅随 `[Initialize]` 恢复默认），共开放 **8 项**激活配置：
     1. `[Rec. Media dur HDMI Output]`（`On` 默认 / `Off(HDMI Only)`；`S&Q` 模式下硬锁 `On`，请求关闭返回 `EOPNOTSUPP=95`）
     2. `[Output Resolution]`
     3. `[4K Output Set.(HDMI Only)]`（仅支持 `10bit`：`59.94p / 50p / 29.97p / 23.98p / 24.00p 10bit`；休眠条目 `24.00p 8bit` 在 FX3 不可选并触发 `EOPNOTSUPP=95`；切换 `24.00p` 强制重启）
     4. `[RAW Output]`（通过 HDMI Type-A 输出 **`4264x2408` 16-bit 线性 RAW**；要求 `Movie` 域且 `Log Shooting != Off`，`S&Q` 模式下硬锁 `Off` 返回 `EOPNOTSUPP=95`）
     5. `[RAW Output Setting]`（`59.94p / 50p / 29.97p / 25p / 23.98p / 24.00p`）
     6. `[Time Code Output]`（作为 `[REC Control]` 的硬性前置条件）
     7. `[REC Control]`（若 `[Time Code Output] = Off` 时请求开启返回 `EOPNOTSUPP=95`）
     8. `[4ch Audio Output]`（`CH1/CH2` 或 `CH3/CH4` 双声道 LPCM 映射）
   - 旧版独立条目 `[Color Gamut for RAW Output]`（`_f 0x6bdc` / `BKID_APP_setting_color_gamut_for_raw_out`）已在 Ver. `2.00..7.02` 移除并统一并入 `[Log Shooting Setting] -> [Color Gamut]`（请求旧条目返回 `EOPNOTSUPP=95`）。
   - 开启 `RAW Output = On` 时，强制锁定 `S-Log3` 曲线、禁用 `Active` 机内防抖（降至 `Off` / `Standard`）并强制 `HDMI Info. Display = Off`。
2. **实测事实 — `RAW Output` + `Rec. Media dur HDMI Output` 写卡路径与 `ILME-FX6` 对照**：
   - 当 `RAW Output = On` 且 `[Rec. Media dur HDMI Output] = On`（默认）时，FX3 **仍同步向 `[Recording Media]` 写入内录 XAVC（及 Proxy）**；仅当设为 `Off(HDMI Only)` 时，卡槽写入通道完全停写（`card_write_pathway_active = False`）。
   - 对照 `ILME-FX6 Ver. 6.01`：支持双 `12G-SDI RAW`（`4096x2160` / `3840x2160 "C"`，激活时将 HDMI 输出封顶至 `<= 1080p`）、`RAW(HDMI)`（`4240x2392`，不支持 `24Hz`）、SDI 原生 4ch 24-bit 48kHz 音频以及 `SDI/HDMI Remote I/F` / `Parallel Rec` 控制分支。
3. **推断 / 安全护栏（Tier-0 `Slot 1` `EROFS=30` 防火墙）**：
   - 当 `RAW Output = On` 且 `Rec. Media dur HDMI Output = On` 时，内录通道仍尝试写入卡槽；恢复检验器将其强锁在 `Slot 1` 只读审计隔离防火墙之后，任何写入/格式化/覆盖操作均返回 **`EROFS=30`**（`slot1_data_sector_writes == 0`、`slot1_vault_mutation_bytes == 0`），Stage-B 覆写限 `/tmp/fx3_stage_b_overlay/pillar65`，并要求 `Backup.bin H0 == H3`（`16/16`）。

### 2.2 Sub-Pillar 65B：`De-Squeeze Display` `1.6x[1.65x]` vs Zero `1.8x`、`[REC Lamp]` 3-LED 耦合、休眠 `[Var. Shutter]` vs FX6 `ECS` 与 `[APS-C S35]` Reset 勘误

1. **实测事实 — Ver. `7.00/7.02` `De-Squeeze Display` `1.6x (1.65x)` 与零 `1.8x` 依据**：
   - `Setup -> [Display Option] -> [De-Squeeze Display]`（抗 `Camera Settings Reset`）：FX3 Ver. `7.00/7.02` 激活 `Off / 1.3x / 1.5x / 1.6x (实为 VAL_DE_SQUEEZE_DISP_1_65X / _f 0x7d0c 的 1.65x 横向拉伸) / 2.0x`（Ver. `3.00` 仅开放 `Off / 1.3x / 2.0x`），全量二进制与 UXC 检索**零 `1.8x` 命中（`P355_DESQUEEZE_1_8X_HITS == 0`）**。
   - 激活反变形显示时强加 **4 项硬锁定**：`Manual Focus`、`Focus Area = Wide`、`SteadyShot = Off`、`Face Priority in Multi Metering = Off`；**不禁用** `Focus Magnifier` 与 `Bright Monitoring`；绝不修改内录成片像素（`recorded_media_desqueeze_pixels == 0`）；并在 **6 种条件**下旁路（`Log=Off`、`RAW=On` HDMI、`HDMI Only`、Still 域下按 `MOVIE` 键、Remote Shooting、Photo Capture）。
   - 对照 `ILME-FX6 Ver. 6.01`：支持 `Off / 1.3x / 1.5x(v5.00+) / 2.0x`（无 `1.6x`），且仅作用于 `VF + HDMI`，**SDI 永不输出反变形拉伸画面（`fx6_sdi_desqueeze_pixels == 0`）**。
2. **实测事实 — `[REC Lamp]` 3-LED 硬件耦合、`[Silent Mode]` 解耦与显示子项**：
   - `Setup -> [Setup Option] -> [REC Lamp]`（抗 Reset；FX3 **无** `[Tally Light]` 独立菜单 `P355_FX3_TALLY_LIGHT_MENU_COUNT == 0`）：控制机身上 **3 颗物理指示灯**（前、后、顶部 `REC` 键环），其中**后灯与顶部 `REC` 环硬件耦合**，因此仅开放 `All On` / `Only Front Off`（默认）/ `All Off`，旧版 `REC_LAMP_LIGHT_UP_ONLY_ONE` 处于休眠态；且 **`[Silent Mode] = On` 严格不关闭 `[REC Lamp]`**（与部分社区误传相反）。对照 FX6 `Technical > Tally` 提供分路控制。
   - `[Emphasized REC Display]`（可被 `Camera Settings Reset` 复位至默认 `On`）：红框仅绘制于机内/带 OSD 显示，Clean-HDMI 零泄漏（`0 px`）。
   - `[Remain Shoot Display]`（活跃静态连拍余量显示，抗 Reset）与 `[Auto Review]`（仅 Still 域 `Off/2/5/10 Sec`、Interval 间隔拍摄禁用，抗 Reset）。
3. **实测事实 — 休眠 `[Var. Shutter]` vs FX6 `ECS` 与 `[APS-C S35 Shooting]` Reset 勘误**：
   - `[Var. Shutter]`（`BKID_APP_setting_high_res_ss` / `_f 0x6831`）在 FX3 Ver. `7.02` 中 **`TYPE_MENU_ITEM_*HIGH_RES* == 0`**，彻底休眠（请求开启返回 `EOPNOTSUPP=95`）；FX3 仅在 Still 机械快门下保留 `[Anti-flicker Shoot.]`（100/120Hz，可 Reset，Electronic Shutter / BULB / Silent Mode 下禁用），而 **FX6 原生具备 `ECS`（`23.99..8000 Hz`）**。
   - **修正 Wave-42 勘误**：`[APS-C S35 Shooting]`（`Auto / On / Off`，默认 `Auto`）实测为 **抗 `Camera Settings Reset`（`Not available`）**，仅随 `[Initialize]` 归位；当强制为 `On` 时，硬锁死全部 4K / DCI 4K / 4K HDMI Only 视频规格（返回 `EOPNOTSUPP=95`），仅保留 HD（`<= 120p`）以及 Still 静态裁剪分辨率 `M: 5.1M (2768x1848)`（3:2）/ `M: 4.3M (2768x1560)`（16:9）。
4. **推断 / 安全护栏**：
   - 恢复适配器与仿真器强制禁止伪造 `1.8x` De-Squeeze、`[Tally Light]`、`[Var. Shutter]` 或错误的 `APS-C Reset` 复位行为，所有越界状态在纯内存状态机内 fail-closed 拦截（`EOPNOTSUPP=95`）且零硬件接触。

---

## 3. 授权交付文件清单（Strict 6-File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py) | Pillar 65A/65B 状态机与评估器、17 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `65/65` 并发主控 `evaluate_realhw_65pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 355 `P355_*` / `PHASE355_*` / `MASTER_65_*` / `evaluate_realhw_65pillar_recovery_master` / `verify_65pillar_recovery` / `verify_all_65_recovery_pillars` 等全部公开符号与 `__all__`（不覆盖 Pillar 64 导出） |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault`、`verify-pillar65-recovery` 与 `verify-65pillar-recovery` CLI 子命令（`help=` 已做 `%%` 转义） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 355 Pillar 65 & `65/65` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier.py) | **148 项**（`>= 120`）四模（正常本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`work_root=None`）单元测试、参数化矩阵与 `65/65` 总控断言 |
| 6 | NEW | [`reports/2026-11-18-phase355-pillar65-65pillar-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault/README.md`](README.md) | 本 Phase 355 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 65 单测（正常模式 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p 'test_realhw_65pillar_*.py'` | **`148/148 OK`**（`22.265s`） |
| Pillar 65 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p 'test_realhw_65pillar_*.py'` | **`148/148 OK`**（`20.485s`） |
| Pillar 65 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p 'test_realhw_65pillar_*.py'` | **`148/148 OK`**（`20.184s`） |
| Pillar 65 全套模拟无供体 CI（`work_root=None`） | `patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))` 全量发现执行 `test_realhw_65pillar_*.py` | **`148/148 OK`**（`19.850s`，`CLEAN_ROOM_SYNTHETIC`，`rc=0`，`leaked=0`） |
| `verify-pillar65-recovery` CLI（供体 / 洁净室） | `verify-pillar65-recovery` & `verify-pillar65-recovery --force-clean-room` | **`65A=6/6, 65B=6/6`**（`0.005s` / `0.000s`，`suite_sha256=ee73892dd9a4cb2f` / `87a1c4ea5e294ebd`，`leaked=0`） |
| `verify-65pillar-recovery` CLI（供体 / 洁净室） | `verify-65pillar-recovery` & `verify-65pillar-recovery --force-clean-room` | **`65/65 PASS`**（`1.210s` / `0.858s` `< 1.5s`，`master_65pillar_sha256=dede2577e44527b9` / `c9a585e87dc94e8b`，`leaked=0`） |
| `make verify-milestone-349`（双模） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-349` & `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-349` | **`status=OK pillars=6/6 gate148=147/150 recovery=65/65 auditors=45/45 vm_stages=77/77 h0_eq_h3=16/16 slot1_writes=0 qemu=47/47(141/141) pngs=94/94(max=27467B) ready_attach=False leaked=0`** |
| `fx3-recovery-adapter` 全套 `unittest discover`（正常模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`4,305 tests OK (skipped=1)`**（`533.707s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-recovery-adapter" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`4,247 tests OK (skipped=18)`**（`496.917s`） |
| 清洁审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **`ALL GREEN`**（`1.86s`，零 `.pyc` / 零二进制残留） |
