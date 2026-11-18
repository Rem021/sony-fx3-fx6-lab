# Phase 298（Stage 60 / `60/60` VM 阶段里程碑！）工程报告 — Wave-50 `[Focus Area]` 14 区 Still-vs-Movie 追踪与 `[AF Area Registration]`、机身 `W/T` `[Zoom Lever Speed]` vs 无摇杆 `XLR-H1`、`[ISO Range Limit]` / Still-Only `[ISO AUTO Min. SS]` vs `Cine EI` 及 `[Flash Mode]` 机械快门门控 vs `[Video Light Mode]` `PMIC 5V <= 900 mA` 协同仿真闭环

> **核心结论（GO / `60/60` MILESTONE ALL GREEN）**：已完成 **Phase 298 Stage 60（`60/60` VM Stages Milestone!）** Wave-50 真实硬件协同仿真台架落地与全栈合流。严格依据 [Wave-50 权威分析报告](../2026-11-17-global-sony-wave50-milestone-focus-area-zoom-lever-speed-iso-auto-minss-flash-intel/README.md) 与 `11` 份 `ILME-FX3 Ver. 7.02` / `ILME-FX6 Ver. 6.01` `os.O_RDONLY` 实机供体（有界窗口 `<= 4096 B`，`raw_firmware_bytes_leaked == 0`），将 `[Focus Area]` 14 区 Still-vs-Movie `Tracking:` 分裂、`[AF Area Registration]` 耦合解锁 `[Lock Operation Parts]` 与 `[Focus Area Limit]`（`>= 2` 下限）、机身 `W/T` `[Zoom Lever Speed]`（`1st=3 / 2nd=8` STBY/REC）/ `[Custom Key Z. Speed]` / `[Remote Zoom Speed]` 与无摇杆 `XLR-H1` 实证辟谣、`[ISO Range Limit]` 与 Still-Only `[ISO AUTO Min. SS]` 对抗 `Cine EI` Base ISO `800 / 12800` 硬锁，以及 `[Flash Mode]` 机械快门静态门控与 `[Video Light Mode]` `PMIC 5V <= 900 mA` MI 热靴保护接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)。全部 `80` 项 Stage 60 三模单测（本地 `O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 全绿）、`outputs/fx3-vm/tests` 全量 `2,923` 项单测双模全绿、Milestone `264` / `254` 双模门控（`vm_stages=60/60`）以及 `scripts/run_all_lab_tests.py --clean-only` / `make clean-audit` 均实测通过，零硬件写入与零越权修改。

---

## 1. 交付文件清单（严格限定自有域 `5` 项）

| # | 交付文件 | 角色与实测状态 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py`](../../outputs/fx3-vm/realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py) | **新增**：Phase 298 Stage 60 (`60/60` 里程碑) 协同仿真器（11 供体 `O_RDONLY` 有界检查 + Sub-Model 60A/60B/60C + 16 项红线探针 + `CLEAN_ROOM_SYNTHETIC` 确定性回退） |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | **修改**：注册 `stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil`，扩展 `CoEmulationConfig` 与 `--include-stage60` / `--skip-stage60` / `--no-include-stage60` / `--skip-phase298` CLI 开关及 `--summary` 摘要行（`vm_stages=60/60`） |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | **修改**：补充 Phase 298 Stage 60（`60/60` 里程碑）架构说明、三模 CLI 与单测验收命令 |
| 4 | [`outputs/fx3-vm/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py) | **新增**：`80` 项双模单元/CLI/套件回归测试（覆盖 3 种运行模式、前向兼容 `assertGreaterEqual(len(stage_keys), 60)`、`sys.executable` 可移植性与 `15.0s` CI 时限裕量） |
| 5 | [`reports/2026-11-17-phase298-milestone-vm-stage60-focus-area-zoom-lever-iso-minss-flash-hil/README.md`](README.md) | **新增**：本 Phase 298 结论先行工程验收报告 |

---

## 2. 技术实现摘要与三子模型闭环

### 2.1 高速 `O_RDONLY` 11 供体精确锚定与 `CLEAN_ROOM_SYNTHETIC` 对等性
对 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 共 `11` 份只读供体（全部经 `_read_bounded_o_rdonly(..., size <= 4096)` 与只读 SHA-256 校验，`raw_firmware_bytes_leaked == 0`）建立真实硬件锚点，并在缺失私有固件的 CI 洁净室自动确定性切换至 `CLEAN_ROOM_SYNTHETIC`：

| 供体键 | 机型 / 构件 | 文件长度 | SHA-256 前 16 位（文件/窗口头） | 校验范围 |
|---|---|---:|---|---|
| `fx3_string_en_f` | `ILME-FX3 7.02 en_f` | `373,820 B` | `7e1f78fc8722671c` | 全文件 SHA-256 + 26 项 Wave-50 英文字符串标记 |
| `fx3_string_sc_f` | `ILME-FX3 7.02 sc_f` | `322,652 B` | `4c034acb454208b6` | 全文件 SHA-256 + 简体中文菜单标记（13 项） |
| `fx3_string_tc_f` | `ILME-FX3 7.02 tc_f` | `324,148 B` | `32c2f18528e1f5a2` | 全文件 SHA-256 + 繁体中文菜单标记（13 项） |
| `fx3_string_ja_f` | `ILME-FX3 7.02 ja_f` | `447,840 B` | `45ba0b3625f3cdad` | 全文件 SHA-256 + 日文菜单标记（13 项） |
| `fx3_string_en` | `ILME-FX3 7.02 en` | `165,740 B` | `204328c311f09920` | 全文件 SHA-256 + `Flash Mode`/`Autoflash`/`Fill-flash`/`Slow Sync.`/`Rear Sync.` |
| `fx3_string_en_g` | `ILME-FX3 7.02 en_g` | `69,600 B` | `a4a15a548f7e0b79` | 全文件 SHA-256 + `Focus Area`/`Zoom`/`Flash` |
| `fx6_string_en` | `ILME-FX6 6.01 en` | `118,208 B` | `5e88dd707cb46a29` | 全文件 SHA-256 + `Handle Zoom`/`Handle HOLD Switch`/`Zoom Position Display` |
| `fx6_string_en_2` | `ILME-FX6 6.01 en_2` | `118,676 B` | `3f11f9200f576575` | 全文件 SHA-256 + `Handle Zoom: Off/Low/High/Variable`/`Flexible Spot` |
| `fx3_appfw` | `ILME-FX3 7.02 appFw.so` | `79,015,712 B` | `de3201c6615a5307` | 4 KiB 头部 SHA-256 + 27 个有界窗口（`BKID_FOCUS_AREA_LIMIT_*`/`BKID_1ST_ZOOM_SPD_*`/`BKID_ISO_AUTO_MIN_SS`/`VAL_HAITA_setting_flash_mode_exposure_mode`/`VIDEO_LIGHT_SET_POWER_LINK`） |
| `fx3_bk4` | `ILME-FX3 7.02 BK4` | `2,229,740 B` | `87b30e89cbf4a649` | 4 KiB 头部 SHA-256 + `BK4`/`ALLLANG`/`ILME-FX3` |
| `fx6_appfw` | `ILME-FX6 6.01 appFw.so` | `50,520,424 B` | `18a5d71362317f3f` | 4 KiB 头部 SHA-256 + `FX6_HANDLE_ZOOM`/`FX6_HANDLE_HOLD_SWITCH`/`FX6_BASE_ISO`/`FX6_ZOOM_POSITION_DISPLAY` |

### 2.2 Sub-Model 60A：`[Focus Area]` 14 区 Still-vs-Movie `Tracking:` 分裂与 `[AF Area Registration]`
- **14 区对焦层次与 Movie/`S&Q` 隔离**：`ILME-FX3 Ver. 7.02` 暴露 7 项跨 Still + Movie + `S&Q` 通用区域（`Wide` 默认、`Zone`、`Center Fix`、`Spot: S/M/L`、`Expand Spot`）以及 **7 项仅限静态照片（Still-only）** 的 `Tracking:` 区域（`Tracking: Wide / Zone / Center Fix / Spot S/M/L / Expand Spot`）。在 Movie 或 `S&Q` 下请求任一 `Tracking:` 区域会被硬件门控拦截并返回 `EOPNOTSUPP = 95`（Movie/`S&Q` 主体追踪使用 `Touch Tracking`，`still_only_tracking_exposed_in_movie_events == 0`），对照 `ILME-FX6` 仅暴露 `Wide / Zone / Flexible Spot`。
- **`[AF Area Registration]` 与 `[Focus Area Limit]`**：`[AF Area Registration]`（`Off / On`，跨 `Camera Settings Reset` 存活，在 Movie/`S&Q`/`iAuto` 禁用）开启时自动强制解除 `[Lock Operation Parts] = Off`（消除互斥冲突，`af_area_reg_lock_op_parts_conflict_events == 0`）；`[Focus Area Limit]` 强制勾选数 `>= 2`（少于 2 项返回 `EINVAL = 22`），并建模 `[Switch V/H AF Area]`、`[Focus Area Color]`（`White` / `Red`）与 `[Circ. of Focus Point]` 边界换行。

### 2.3 Sub-Model 60B：机身 `W/T` `[Zoom Lever Speed]` vs 无摇杆 `XLR-H1` 实证辟谣与 `ILME-FX6` Smart Handle 对照
- **实证辟谣（`XLR-H1` 零变焦摇杆 / 零 `ZOOM HOLD` 开关）**：`ILME-FX3` 的 `XLR-H1` 仅是纯音频接口手柄，物理上**不存在变焦摇杆、不存在录制键、也不存在 `ZOOM HOLD` 开关**；仿真中向 FX3 注入任何 `XLR-H1` 手柄变焦或手柄 Hold 请求均被拦截并返回 `EOPNOTSUPP = 95`（`xlr_h1_phantom_zoom_or_hold_events == 0`）。对照 `ILME-FX6` Smart Handle 暴露 `Handle Zoom`（`Off / Low / High / Variable 1..8`）+ `Handle HOLD Switch`（`Normal / Rec Button Only`），且 `0..99` 为 `Zoom Position Display` 刻度而非速度值。
- **机身 `W/T` 两段比例翘板与三路变焦速度**：建模 FX3 机身顶部 `W/T` `[Zoom Lever Speed]`（`1st Zoom Spd.` `1..8` 默认 `3`，`2nd Zoom Spd.` `1..8` 默认 `8`，独立 `STBY` & `REC` 寄存器）、`[Custom Key Z. Speed]`（`1..8` 默认 `3`，STBY/REC）与 `[Remote Zoom Speed]`（`Speed Type: Variable / Fixed`、`Fixed Speed 1..8` STBY/REC），并严格门控 `Zoom Range`（`ClearImage Zoom` / `Digital Zoom` 在 `RAW` 与 `119.88p`/`100p` 下拒绝 `EOPNOTSUPP = 95`）。

### 2.4 Sub-Model 60C & Redlines：`[ISO Range Limit]` / Still-Only `[ISO AUTO Min. SS]` vs `Cine EI` 与 `[Flash Mode]` 机械快门门控 vs `[Video Light Mode]` `PMIC 5V <= 900 mA`
- **ISO 限幅 / 最小快门与 `Cine EI` 硬锁**：`[ISO Range Limit]`（`Min/Max` 同时钳制手动 ISO 与 `ISO AUTO`）与 **Still-only** `[ISO AUTO Min. SS]`（`Slower / Slow / Standard / Fast / Faster` 与 `1/8000..30"`，仅在 `P/A` 或 `M + ISO AUTO` 生效，Movie/`S&Q` 拒绝 `EOPNOTSUPP = 95`）在 Movie `Cine EI` / `Cine EI Quick` 下均被 Base ISO `800 / 12800` 硬锁（`EOPNOTSUPP = 95`，`cine_ei_iso_range_or_minss_bypass_events == 0`）。
- **Flash 机械快门静态门控 vs `Video Light` `PMIC 5V` 限流 & 16 项红线**：`[Flash Mode]`（`Flash Off / Autoflash / Fill-flash [默认] / Slow Sync. / Rear Sync.`，`1/250 s` 全画幅同步）严格门控至 `EXPOSURE_MODE_STILL` + `Mechanical Shutter` + `Silent Mode = Off`（Movie/`S&Q`、电子快门与静音模式均返回 `EOPNOTSUPP = 95`，`flash_non_mech_or_movie_bypass_events == 0`）；`[Video Light Mode]`（`Power Link` 默认 / `REC Link` / `REC Link & STBY` / `Auto`）贯穿 Still + Movie + `S&Q` 并严格执行 MI 热靴 `PMIC 5V <= 900 mA` 电流护栏（超流即刻拒绝 `EOPNOTSUPP = 95`，`mishoe_pmic_5v_900ma_overcurrent_events == 0`），全套 `16` 项安全红线探针全部 `0` 越权、`0` 写入、`0` 泄漏。

---

## 3. 实测验证矩阵（实测命令与结果）

| 验证项目 | 运行模式 / 覆盖范围 | 实测结果 |
|---|---|---|
| Stage 60 独立自检 CLI（`--self-test --summary` / `--json`） | `LOCAL_DONOR_O_RDONLY` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | 双模 `PASS`：`donors=11`，`mv_trk=0`，`reg_lk=0`，`xlr_zm=0`，`ei_byp=0`，`fl_byp=0`，`mi_oc=0`，`phys_wr=0`，`leaked=0`，摘要哈希 `bc56f0abfd21`（本地）/ `2b721c83e61f`（洁净室） |
| Stage 60 单元/套件测试（`80` 项） | 默认 `O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **80/80 PASS**（三模全绿：`2.616s` / `2.655s` / `0.998s`） |
| 全板 `60` 阶段协同套件（`fx3_vm_coemulation_suite.py --include-stage60 --summary`） | 默认本地供体 + `FX3_CLEAN_ROOM_TEST=1` | `[PASS]` `realhw_focus_area_zoom_lever_iso_minss_flash_hil` 双模全绿（`fa14=14,mv_trk=0,xlr_zm=0,ei_byp=0,fl_byp=0,mi_oc=0,emmc_wr=0`），`digest=fa88f313ee7e`（本地）/ `11c01ae82431`（洁净室） |
| `outputs/fx3-vm/tests` 全量自动发现套件 | 本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2,923` tests OK**（本地 `176.547s` 全过；洁净室 `166.063s`，`4` skip 其余全过） |
| Milestone `264` & `254` 门控（`make verify-milestone-264` / `verify-milestone-254`） | 本地供体 + `--force-clean-room` 双模（`vm_stages=60/60`） | **ALL GREEN**：`status=OK`，`vm_stages=60/60`，`milestone264_sha256=83a3bcc887e000fc...` / `87bf5a5ce9be3b82...`，`milestone254_sha256=0e0fe17b115aa3b1...` / `c197c44639912992...` |
| 全仓洁净回归与审计（`scripts/run_all_lab_tests.py --clean-only` & `make clean-audit`） | 洁净室全仓回归 + Git 二进制/`.pyc` 审计 | **ALL GREEN**（zero `.pyc`/`__pycache__`，`raw_firmware_bytes_leaked == 0`） |
