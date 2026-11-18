# Phase 293（Stage 59 / `59/59`）工程报告 — Wave-49 Still `[Image Quality Settings]`（`RAW` / `HEIF 4:2:0/4:2:2` & `[HLG Still Image]` `BT.2100`）、`[Color Space]` `AdobeRGB` `_DSC` 前缀 & `[Set File Name]` 首字符 `_` 禁令，及 `[Shutter Type]` 2 选 / Electronic-Silent 5 锁 / NR / `10 fps` `Slot-1` 保险库协同仿真闭环

> **核心结论（GO / 59/59 ALL GREEN）**：已完成 **Phase 293 Stage 59（`59/59`）** Wave-49 真实硬件协同仿真台架落地与全栈合流。严格依据 [Wave-49 权威分析报告](../2026-11-17-global-sony-wave49-still-raw-heif-colorspace-adobersgb-shutter-type-nr-drive-intel/README.md) 与 `11` 份 `ILME-FX3 Ver. 7.02` / `ILME-FX6 Ver. 6.01` `os.O_RDONLY` 实机供体（有界窗口 `<= 4096 B`，`raw_firmware_bytes_leaked == 0`），将 Still `[Image Quality Settings]`（`RAW` `Compressed`/`Uncompressed` vs 休眠 `Lossless Comp` `EOPNOTSUPP = 95` 门控、`JPEG/HEIF Switch` `10-bit` `.HIF`、`[HLG Still Image]` 前置校验 + `PP`/`Creative Look`/`DRO`/`DRO Bracket` 硬锁 + `BT.2100` 覆写与 `Gamma Display Assist`、对照无静态流水线 `ILME-FX6`）、`[Color Space]`（`sRGB` `DSC` vs `AdobeRGB` 自动前置 `_DSC`、`[Set File Name]` 首字符 `_` `EINVAL = 22` 禁令、`HEIF` 忽略色彩空间、`Camera Settings Reset` vs `Initialize` 持久分裂），以及 `[Shutter Type]` 精确 2 选（`Mechanical Shutter` vs `Electronic Shutter` 无 `Auto`、`Electronic`/`Silent` 5 锁矩阵、`e-Front Curtain Shut.` 复位存活、`Long Exposure NR` `>= 1 s` 暗帧减除、`High ISO NR` RAW 免疫、`10 fps` `Hi+` 与 `8 fps` Uncompressed/Flash 降档、`Slot-1` Tier-0 保险库 `EROFS = 30` / `EBUSY = 16` 防火墙）接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)。全部 `78` 项 Stage 59 三模单测（本地 `O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 全绿）、`outputs/fx3-vm/tests` 全量 `2,843` 项单测双模全绿、Milestone `264` / `254` 双模门控（`vm_stages=59/59`）以及 `scripts/run_all_lab_tests.py --clean-only` / `make clean-audit` 均实测通过，零硬件写入与零越权修改。

---

## 1. 交付文件清单（严格限定自有域 `5` 项）

| # | 交付文件 | 角色与实测状态 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py`](../../outputs/fx3-vm/realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py) | **新增**：Phase 293 Stage 59 (`59/59`) 协同仿真器（11 供体 `O_RDONLY` 有界检查 + Sub-Model 59A/59B/59C + 16 项红线探针 + `CLEAN_ROOM_SYNTHETIC` 确定性回退） |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | **修改**：注册 `stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil`，扩展 `CoEmulationConfig` 与 `--include-stage59` / `--skip-stage59` / `--no-include-stage59` / `--skip-phase293` CLI 开关及 `--summary` 摘要行（`vm_stages=59/59`） |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | **修改**：补充 Phase 293 Stage 59（`59/59`）架构说明、三模 CLI 与单测验收命令 |
| 4 | [`outputs/fx3-vm/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py) | **新增**：`78` 项双模单元/CLI/套件回归测试（覆盖 3 种运行模式、前向兼容 `assertGreaterEqual(len(stage_keys), 59)`、`sys.executable` 可移植性与 `15.0s` CI 时限裕量） |
| 5 | [`reports/2026-11-17-phase293-vm-stage59-raw-heif-colorspace-shuttertype-nr-drive-hil/README.md`](README.md) | **新增**：本 Phase 293 结论先行工程验收报告 |

---

## 2. 技术实现摘要与三子模型闭环

### 2.1 高速 `O_RDONLY` 11 供体精确锚定与 `CLEAN_ROOM_SYNTHETIC` 对等性
对 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 共 `11` 份只读供体（全部经 `_read_bounded_o_rdonly(..., size <= 4096)` 与只读 SHA-256 校验，`raw_firmware_bytes_leaked == 0`）建立真实硬件锚点，并在缺失私有固件的 CI 洁净室自动确定性切换至 `CLEAN_ROOM_SYNTHETIC`：

| 供体键 | 机型 / 构件 | 文件长度 | SHA-256 前 16 位（文件/窗口头） | 校验范围 |
|---|---|---|---|---|
| `fx3_string_en_f` | `ILME-FX3 7.02 en_f` | `373,820 B` | `7e1f78fc8722671c` | 全文件 SHA-256 + 25 项 Wave-49 英文字符串标记 |
| `fx3_string_sc_f` | `ILME-FX3 7.02 sc_f` | `322,652 B` | `4c034acb454208b6` | 全文件 SHA-256 + 简体中文菜单标记 |
| `fx3_string_tc_f` | `ILME-FX3 7.02 tc_f` | `324,148 B` | `32c2f18528e1f5a2` | 全文件 SHA-256 + 繁体中文菜单标记 |
| `fx3_string_ja_f` | `ILME-FX3 7.02 ja_f` | `447,840 B` | `45ba0b3625f3cdad` | 全文件 SHA-256 + 日文菜单标记 |
| `fx3_string_en` | `ILME-FX3 7.02 en` | `165,740 B` | `204328c311f09920` | 全文件 SHA-256 + `sRGB`/`AdobeRGB`/`Drive Mode`/`High ISO NR` |
| `fx3_string_en_g` | `ILME-FX3 7.02 en_g` | `69,600 B` | `a4a15a548f7e0b79` | 全文件 SHA-256 + `Image Quality/Rec`/`Shutter/Silent` |
| `fx6_string_en` | `ILME-FX6 6.01 en` | `118,208 B` | `5e88dd707cb46a29` | 全文件 SHA-256 + `RAW Output Format`/`Shutter Category` |
| `fx6_string_en_2` | `ILME-FX6 6.01 en_2` | `118,676 B` | `3f11f9200f576575` | 全文件 SHA-256 + `Shutter Mode`/`HLG_BT.2100` |
| `fx3_appfw` | `ILME-FX3 7.02 appFw.so` | `79,015,712 B` | `de3201c6615a5307` | 4 KiB 头部 SHA-256 + 25 个有界窗口（`JH_FILE_TYPE_*`/`RAW_FILE_TYPE_*`/`STILL_SHUTTER_TYPE_*`/`BKID_*`） |
| `fx3_bk4` | `ILME-FX3 7.02 BK4` | `2,229,740 B` | `87b30e89cbf4a649` | 4 KiB 头部 SHA-256 + `BK4`/`ALLLANG`/`ILME-FX3` |
| `fx6_appfw` | `ILME-FX6 6.01 appFw.so` | `50,520,424 B` | `18a5d71362317f3f` | 4 KiB 头部 SHA-256 + `FX6_SHUTTER_SELECT`/`FX6_RAW_OUTPUT_FORMAT`/`FX6_FILE_FORMAT` |

### 2.2 Sub-Model 59A：Still `[Image Quality Settings]`、`RAW` 休眠 `Lossless Comp` 门控与 `[HLG Still Image]` `BT.2100`
- **`RAW File Type` 严格 2 选与休眠枚举拦截**：`ILME-FX3 Ver. 7.02`（`12 MP IMX510`）仅暴露 `[Compressed]`（默认）与 `[Uncompressed]` 14-bit `.ARW`；共享引擎中的休眠枚举 `Lossless Comp` / `Lossless Comp (L)/(M)/(S)`（`_f.uxc` `0x6b56`）被硬件型号门控屏蔽，请求时确定性返回 `EOPNOTSUPP = 95`（`dormant_lossless_raw_exposed_events == 0`）。对照 `ILME-FX6 Ver. 6.01` 完全无静态 `DCIM`/`.ARW`/`.JPG`/`.HIF` 流水线（`still_pipeline_present = False`，仅 Movie SDI/HDMI 16-bit 线性 RAW）。
- **`JPEG/HEIF Switch` 10-bit `.HIF` 与 `[HLG Still Image]` 前置/锁定矩阵**：`JPEG` 输出 8-bit `.JPG`，`HEIF(4:2:0)` / `HEIF(4:2:2)` 输出 10-bit `.HIF`。启用 `[HLG Still Image] = On` 须同时满足 ① `HEIF(4:2:0)` 或 `HEIF(4:2:2)`、② `File Format = HEIF` 单选（`JPEG`/`RAW`/`RAW & JPEG`/`RAW & HEIF` 均拒绝 `EOPNOTSUPP = 95`）、③ `P/A/S/M`（`iAuto` 拒绝 `EOPNOTSUPP = 95`）；激活后硬锁 `Picture Profile` / `Creative Look` / `D-Range Optimizer` / `DRO Bracket`，覆写色彩空间为 `BT.2100`（`BT.2020`），并将监视引至 `Gamma Display Assist`（`Auto` / `HLG(BT.2020)`）。

### 2.3 Sub-Model 59B：`[Color Space]`（`sRGB` vs `AdobeRGB` `_DSC`）与 `[Set File Name]` 首字符 `_` 禁令
- **DCF 2.0 `_DSC` 自动前置与 `[Set File Name]` 首 `_` 封禁**：`sRGB` 生成 `DSC0001.JPG/.ARW`（`100MSDCF`），切换 `AdobeRGB` 自动在自定义前缀前插入 `_` 生成 `_DSC0001.JPG/.ARW`（如自定义 `FX3` -> `_FX30001`）。`[Set File Name]` 仅允许 3 位 `A-Z0-9_`，且**禁止以 `_` 作为第 1 个字符**（`EINVAL = 22`），非首字符 `_`（如 `A_1`、`FX_`）合法放行。
- **`HEIF` 忽略 `[Color Space]` 与重置持久分裂**：`File Format = HEIF` 下 `[Color Space]` 不起作用（`HLG = Off` 固定 `sRGB`，`On` 固定 `BT.2100`）；`[Camera Settings Reset]` 将 `[Color Space]` 复位为 `sRGB`，但**保留 `[Set File Name]`**，仅 `[Initialize]` 将其恢复为默认 `DSC`（`color_space_leading_underscore_bypass_events == 0`）。

### 2.4 Sub-Model 59C & 16 项红线：`[Shutter Type]` 2 选（无 `Auto`）、5 锁矩阵、NR、`10 fps` 与 `Slot-1` 保险库
- **精确 2 选 `[Shutter Type]` 与 Electronic/Silent 5 锁**：`ILME-FX3 Ver. 7.02` 仅暴露 `Mechanical Shutter`（默认）与 `Electronic Shutter`（**无 `Auto` 选项**，请求 `Auto` 返回 `EINVAL = 22`）；对照 `ILME-FX6` 无机械快门（`mechanical_shutter_present = False`，请求机械快门 `EOPNOTSUPP = 95`）。在 `Electronic Shutter` 或 `Silent Mode = On`（未设 `Target Function` 覆写）下，强制锁定 ① `Flash`（机械 `1/250 s` 全画幅闪光同步）、② `Long Exposure NR`、③ `e-Front Curtain Shut.`（默认 `On`，跨 `Camera Settings Reset` 存活）、④ `BULB`、⑤ `Anti-flicker Shoot.`（`EOPNOTSUPP = 95`）。
- **NR 边界、`10 fps` 驱动、16 项红线与 `Slot-1` 保险库**：`Long Exposure NR` 仅在 `>= 1.0 s` / `BULB` 下执行暗帧减除；`High ISO NR` 对 `.ARW` 免处理并在 `RAW` 单选时锁定；`Cont. Shooting: Hi+` 在压缩 RAW/JPEG 下达 `10.0 fps`，`Uncompressed RAW` 与闪光降至 `8.0 fps`，连拍 `>= 1000` 帧触发 `SLOW` 限速，`> F11` 锁 AF；对 `Slot 1 Tier-0 Vault` 的任意单拍/连拍/包围曝光写入均触发 fail-closed `EROFS = 30` / `EBUSY = 16` 拦截，全套 `16` 项安全红线探针全部 `0` 越权、`0` 写入、`0` 泄漏。

---

## 3. 实测验证矩阵（实测命令与结果）

| 验证项目 | 运行模式 / 覆盖范围 | 实测结果 |
|---|---|---|
| Stage 59 独立自检 CLI（`--self-test --summary` / `--json`） | `LOCAL_DONOR_O_RDONLY` / `--clean-room` | 双模 `PASS`：`donors=11`，`lossless_exp=0`，`hlg_byp=0`，`cs_byp=0`，`shut_byp=0`，`s1_wr=0`，`phys_wr=0`，`leaked=0`，摘要哈希 `c9e053bbaf7d`（本地）/ `75421fd3621c`（洁净室） |
| Stage 59 单元/套件测试（`78` 项） | 默认 `O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **78/78 PASS**（三模全绿） |
| 全板 `59` 阶段协同套件（`fx3_vm_coemulation_suite.py --summary`） | 默认本地供体 + `FX3_CLEAN_ROOM_TEST=1` | `[PASS]` `realhw_raw_heif_colorspace_shuttertype_nr_drive_hil` 双模全绿，`digest=04c5b7de117b`（本地）/ `29392e13ec2a`（洁净室） |
| `outputs/fx3-vm/tests` 全量自动发现套件 | 本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2,843` tests OK**（本地 181.678s 全过；洁净室 152.817s，4 skip 其余全过） |
| Milestone `264` & `254` 门控（`make verify-milestone-264` / `verify-milestone-254`） | 本地供体 + `--force-clean-room` 双模（`vm_stages=59/59`） | **ALL GREEN**：`status=OK`，`vm_stages=59/59`，`milestone264_sha256=0fbaa36855aa6c65...` / `6c7b7186c01ee5d9...`，`milestone254_sha256=14f47841216bb948...` / `5f1e1e3291d4822d...` |
| 全仓洁净回归与审计（`scripts/run_all_lab_tests.py --clean-only` & `make clean-audit`） | 洁净室全仓回归 + Git 二进制/`.pyc` 审计 | **ALL GREEN**（zero `.pyc`/`__pycache__`，`raw_firmware_bytes_leaked == 0`） |
