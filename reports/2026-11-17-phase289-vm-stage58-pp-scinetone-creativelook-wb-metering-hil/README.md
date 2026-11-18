# Phase 289（Stage 58 / `58/58`）工程报告 — Wave-48 `[Picture Profile]` `PP11` S-Cinetone 出厂默认 / `Creative Look` 与 `DRO` 互斥与重置持久分裂、`[White Balance]` 13 模式 / `Cine EI` Auto-WB 锁定与 `Custom 1..3` `CAMSET` 隔离、及 `[Metering Mode]` 5 模式 / 对焦点联动 / `CIZ` `Multi` 钳位协同仿真闭环

> **核心结论（GO / 58/58 ALL GREEN）**：已完成 **Phase 289 Stage 58（`58/58`）** Wave-48 真实硬件协同仿真台架落地与全栈合流。严格依据 [Wave-48 权威分析报告](../2026-11-17-global-sony-wave48-picture-profile-scinetone-creative-look-dro-wb-metering-intel/README.md) 与 `11` 份 `ILME-FX3 Ver. 7.02` / `ILME-FX6 Ver. 6.01` `os.O_RDONLY` 实机供体（有界窗口 `<= 4096 B`，`raw_firmware_bytes_leaked == 0`），将 `[Picture Profile]` `PP1..PP11`（`PP11 = S-Cinetone` **Movie 与 Still 双模式出厂默认**）、`[Creative Look]`（`10` 预设 + `Custom Look 1..6` + `Clarity` 电影/连拍锁定）及 `[D-Range Optimizer]` 互斥锁定、`[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）全锁定与 `[Display LUT]` 路由、`[Picture Profile]` 内部参数跨 `[Camera Settings Reset]` 与 `[Initialize]` 双双存活分裂、`[White Balance]` `13` 模式 + `Cine EI` Auto-WB 硬锁 + `Custom 1..3` 跨重存活但被 SD/CFexpress `CAMSET01..10.DAT` 排除（仅 `M1..M4` 卡槽携带），以及 `[Metering Mode]` `5` 模式 + `Spot Metering Point = Focus Point Link`（仅 `Flexible Spot` / `Expand Spot`）+ `Clear Image Zoom > 1.0x` 强制钳位 `[Multi]` 接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)。全部 `76` 项 Stage 58 双模单测（本地 `O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 三模全绿）、`outputs/fx3-vm/tests` 全量 `2,765` 项单测双模全绿、Milestone `264` / `254` 双模门控（`vm_stages=58/58`）以及 `scripts/run_all_lab_tests.py --clean-only` / `make clean-audit` 均实测通过，零硬件写入与零越权修改。

---

## 1. 交付文件清单（严格限定自有域 `5` 项）

| # | 交付文件 | 角色与实测状态 |
|---|---|---|
| 1 | [`outputs/fx3-vm/realhw_pp_scinetone_creativelook_wb_metering_coemulator.py`](../../outputs/fx3-vm/realhw_pp_scinetone_creativelook_wb_metering_coemulator.py) | **新增**：Phase 289 Stage 58 (`58/58`) 协同仿真器（11 供体 `O_RDONLY` 有界检查 + Sub-Model A/B/C + 16 项红线探针 + `CLEAN_ROOM_SYNTHETIC` 确定性回退） |
| 2 | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | **修改**：注册 `stage58_realhw_pp_scinetone_creativelook_wb_metering_hil`，扩展 `CoEmulationConfig` 与 `--include-stage58` / `--skip-stage58` / `--no-include-stage58` / `--skip-phase289` CLI 开关及 `--summary` 摘要行（`vm_stages=58/58`） |
| 3 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | **修改**：补充 Phase 289 Stage 58（`58/58`）架构说明、三模 CLI 与单测验收命令 |
| 4 | [`outputs/fx3-vm/tests/test_realhw_pp_scinetone_creativelook_wb_metering_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_pp_scinetone_creativelook_wb_metering_coemulator.py) | **新增**：`76` 项双模单元/CLI/套件回归测试（覆盖 3 种运行模式、前向兼容 `assertGreaterEqual(len(stage_keys), 58)`、`sys.executable` 可移植性与 `15.0s` CI 时限裕量） |
| 5 | [`reports/2026-11-17-phase289-vm-stage58-pp-scinetone-creativelook-wb-metering-hil/README.md`](README.md) | **新增**：本 Phase 289 结论先行工程验收报告 |

---

## 2. 技术实现摘要与三子模型闭环

### 2.1 高速 `O_RDONLY` 11 供体精确锚定与 `CLEAN_ROOM_SYNTHETIC` 对等性
对 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 共 `11` 份只读供体（全部经 `_read_bounded_o_rdonly(..., size <= 4096)` 与只读 SHA-256 校验，`raw_firmware_bytes_leaked == 0`）建立真实硬件锚点，并在缺失私有固件的 CI 洁净室自动确定性切换至 `CLEAN_ROOM_SYNTHETIC`：

| 供体键 | 机型 / 构件 | 文件长度 | SHA-256 前 16 位（文件/窗口头） | 校验范围 |
|---|---|---|---|---|
| `fx3_string_en_f` | `ILME-FX3 7.02 en_f` | `373,820 B` | `7e1f78fc8722671c` | 全文件 SHA-256 + 12 项主字符串标记 |
| `fx3_string_sc_f` | `ILME-FX3 7.02 sc_f` | `322,652 B` | `4c034acb454208b6` | 全文件 SHA-256 + 简体中文菜单标记 |
| `fx3_string_tc_f` | `ILME-FX3 7.02 tc_f` | `324,148 B` | `32c2f18528e1f5a2` | 全文件 SHA-256 + 繁体中文菜单标记 |
| `fx3_string_ja_f` | `ILME-FX3 7.02 ja_f` | `447,840 B` | `45ba0b3625f3cdad` | 全文件 SHA-256 + 日文菜单标记 |
| `fx3_string_en` | `ILME-FX3 7.02 en` | `165,740 B` | `204328c311f09920` | 全文件 SHA-256 + DRO/WB/Metering 选项 |
| `fx3_string_en_g` | `ILME-FX3 7.02 en_g` | `69,600 B` | `a4a15a548f7e0b79` | 全文件 SHA-256 + Guide/Gamma Assist 文本 |
| `fx6_string_en` | `ILME-FX6 6.01 en` | `118,208 B` | `5e88dd707cb46a29` | 全文件 SHA-256 + `S-Cinetone`/`Base Look`/`ATW` |
| `fx6_string_en_2` | `ILME-FX6 6.01 en_2` | `118,676 B` | `3f11f9200f576575` | 全文件 SHA-256 + `Memory A/B`/`Shockless White` |
| `fx3_appfw` | `ILME-FX3 7.02 appFw.so` | `79,015,712 B` | `de3201c6615a5307` | 4 KiB 头部 SHA-256 + 26 个有界窗口（累计读 `45,056 B`） |
| `fx3_bk4` | `ILME-FX3 7.02 BK4` | `2,229,740 B` | `87b30e89cbf4a649` | 4 KiB 头部 SHA-256 + `BK4`/`ALLLANG`/`ILME_FX3`（累计读 `8,192 B`） |
| `fx6_appfw` | `ILME-FX6 6.01 appFw.so` | `50,520,424 B` | `18a5d71362317f3f` | 4 KiB 头部 SHA-256 + 6 个有界窗口（累计读 `24,576 B`） |

### 2.2 Sub-Model 58A：`PP11` S-Cinetone 出厂默认、`Creative Look` / `DRO` 互斥与重置持久分裂
- **`PP11` 双模式出厂默认与 FX6 对照**：`ILME-FX3 Ver. 7.02` 出厂默认激活 `[Picture Profile] = PP11`（`Gamma: S-Cinetone`, `Color Mode: S-Cinetone`），且在 **Movie 与 Still 双拍摄模式下均默认生效**（`PP7/8/9 = S-Log2/S-Log3`，`PP10 = HLG2 + BT.2020`）；对照 `ILME-FX6 Ver. 6.01` 在 Custom 模式下使用 `Base Look`（`S-Cinetone` 默认）+ `Scene File`，无 FX3 式 `PP1..11` / `Creative Look` 菜单树。
- **`Creative Look`（10 预设 + `Custom Look 1..6` + `8` 参数）与 `DRO` 硬锁**：当任一 `PP1..PP11` 处于激活态（非 `Off`）时，`[Creative Look]`（`ST, PT, NT, VV, VV2, FL, IN, SH, BW, SE` 与 `Custom Look 1..6`）强制锁死为 `'-'`（越权写入返回 `EOPNOTSUPP = 95`），`[D-Range Optimizer]`（`Off / Auto / Lv1..Lv5`）强制固定为 `Off`（`EOPNOTSUPP = 95`）。仅当 `PP = Off` 且 `Log Shooting = Off` 时方允许切换 `Creative Look` 与 `DRO`；且在 Movie/`S&Q` 或连续驱动模式下，`Creative Look` 的第 8 参数 `Clarity` 仍被硬锁（`EOPNOTSUPP = 95`）。
- **`Log Shooting` 三模式全锁与 `[Display LUT]` 路由**：开启 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）后，系统同时硬锁 `[Picture Profile]`、`[Creative Look]` 与 `[D-Range Optimizer]`（`EOPNOTSUPP = 95`），并将监看引导至 `[Display LUT]`（`s709`, `709(800%)`, `User1..User16`）。
- **关键重置持久分裂（`pp_creative_look_or_reset_wipe_misroute_events == 0`）**：

| 重置/恢复动作 | `PP` 激活选择器（默认回归 `PP11`） | `PP1..PP11` 内部自定义配方 | `Creative Look` 参数 |
|---|---|---|---|
| `[Camera Settings Reset]` | 复位为 `PP11` | **完整存活** | **完整存活** |
| `[Initialize]`（整机初始化） | 复位为 `PP11` | **依然存活** | 恢复出厂 |
| `[Picture Profile] -> [Reset]`（单档重置） | 保持目标 `PPn` | **仅此动作清除 `PPn` 内部修改** | 不受影响 |

### 2.3 Sub-Model 58B：`[White Balance]` `13` 模式、`Cine EI` Auto-WB 硬锁与 `Custom 1..3` `CAMSET` 隔离
- **全 `13` 项 FX3 WB 模式 + 辅助锁定建模**：完整覆盖 `Auto`、`Daylight`、`Shade`、`Cloudy`、`Incandescent`、`Fluorescent: Warm White / Cool White / Day White / Daylight`、`Flash`（**仅限 Still**，Movie/`S&Q` 拒绝返回 `EOPNOTSUPP = 95`）、`Underwater Auto`、`C.Temp./Filter`（`2500K..9900K` 合法步进与 `G7..M7` / `A7..B7` 补偿，越界返回 `EINVAL = 22`）、以及 `Custom 1..3`（对比 FX6 机身硬开关 `WHT BAL` `B / A / PRESET` 与 `ATW`）。
- **`Cine EI` Auto-WB 硬锁与 `[Shutter AWB Lock]` 边界**：在 `Log Shooting = Cine EI` 或 `Cine EI Quick` 下，`Auto` 与 `Underwater Auto` 被强制硬锁（`EOPNOTSUPP = 95`），仅放行固定预设、`C.Temp./Filter` 与 `Custom 1..3`；`[Priority Set in AWB]`（`Standard / Ambience / White`）与 `[Shutter AWB Lock]`（`Shut. Halfway / Cont. Shooting / Off`）仅在 Still + Auto-WB 系列下生效。
- **`Custom 1..3` 持久化与存储介质分裂（`wb_cine_ei_auto_or_camset_custom_leak_events == 0`）**：

| 介质 / 重置操作 | `Custom 1..3` 注册值行为 | 验证口径 |
|---|---|---|
| `[Camera Settings Reset]` | **跨重置存活** | `wb_custom_survived == True` |
| `[Initialize]` | **彻底擦除还原** | `wb_custom_wiped == True` |
| `[Save/Load Settings]`（`CAMSET01..10.DAT`） | **不写入亦不加载**（报错/跳过 `EOPNOTSUPP` 防误泄漏） | `wb_cine_ei_auto_or_camset_custom_leak_events == 0` |
| `Memory Recall`（`M1..M4` 卡槽） | **可随 `M1..M4` 携带自定义白平衡** | `m1_m4_carries_custom_wb == True` |

### 2.4 Sub-Model 58C & 16 项红线：`[Metering Mode]` `5` 模式、`Focus Point Link`、`CIZ` `[Multi]` 钳位与硬件铁律
- **`5` 项测光模式与 FX6 对照**：建模 `Multi`、`Center`、`Spot: Standard` / `Spot: Large`、`Entire Screen Avg.`、`Highlight`（对比 FX6 专业 Cine EI 波形图/斑马纹/伪色彩与 Backlight/Spotlight/Standard 自动曝光体系）。
- **对焦点联动与 `Clear Image Zoom` 钳位（`metering_spot_link_or_ciz_multi_bypass_events == 0`）**：
  - `[Spot Metering Point] = Focus Point Link` 仅在 `Flexible Spot` 或 `Expand Spot` 对焦区域下与 AF 对焦点真实联动，其他对焦区域下自动退化回画面中心（`Center`）。
  - 一旦 `Clear Image Zoom / Digital Zoom > 1.0x`，测光模式强制钳位至 `[Multi]` 且 `[Face Priority in Multi Metering]` 强制关闭为 `Off`（任何绕过尝试均返回 `EOPNOTSUPP = 95`）；当变焦回落至 `1.0x` 后，用户原有测光模式与人脸优先设置干净恢复。
- **16 项硬件安全红线全锁定**：全部 `16` 项红线探针（覆盖 `eMMC`/`nflasha` 写入、实机挂载、`SPI-NOR`、`EL3`、`ISP`、`cnflasha`、CP/WBI、`NOP` 注入、PP/CreativeLook/Reset 分裂绕过、Cine EI Auto-WB / `CAMSET` 泄漏、`Spot`/`CIZ Multi` 绕过、USB 物理发包与固件字节泄漏）均确定性 fail-closed 拦截，保持 `persistent_emmc_writes_authorized == False`、`hardware_live_attachment_authorized == False`、`overall_ready_for_hardware_attach == False`、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、`cnflasha_userspace_write_blocked == True`、`emmc_nflasha_write_count == 0`、`physical_usb_packets_emitted == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 3. 实测验证矩阵（实测命令与结果）

| 验证项目 | 运行模式 / 覆盖范围 | 实测结果 |
|---|---|---|
| Stage 58 独立自检 CLI（`--self-test --summary` / `--json`） | `LOCAL_DONOR_O_RDONLY` / `--clean-room` | 双模 `PASS`：`donors=11`，`pp_mis=0`，`wb_leak=0`，`mtr_byp=0`，`phys_wr=0`，`leaked=0`，摘要哈希 `e6c1ff3bfc8d`（本地）/ `667ecd9b73c4`（洁净室） |
| Stage 58 单元/套件测试（`76` 项） | 默认 `O_RDONLY` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **76/76 PASS**（三模全绿：3.268s / 2.895s / 1.421s） |
| 全板 `58` 阶段协同套件（`fx3_vm_coemulation_suite.py --include-stage58 --summary`） | 默认本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | `[PASS]` `realhw_pp_scinetone_creativelook_wb_metering_hil` 双模全绿，`digest=eb6bdea7ad85`（本地）/ `e70eb1626b20`（洁净室） |
| `outputs/fx3-vm/tests` 全量自动发现套件 | 本地供体 + `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`2,765` tests OK**（本地 160.266s 全过；洁净室 147.344s，4 skip 其余全过） |
| Milestone `264` & `254` 门控（`make verify-milestone-264` / `verify-milestone-254`） | 本地供体 + `--force-clean-room` 双模（`vm_stages=58/58`） | **ALL GREEN**：`status=OK`，`vm_stages=58/58`，`milestone264_sha256=e01477729f09582b...` / `444fd4f49148e069...`，`milestone254_sha256=a5659c1da0c5eabb...` / `819536143109cbb1...` |
| 全仓洁净回归与审计（`scripts/run_all_lab_tests.py --clean-only` & `make clean-audit`） | 洁净室全仓回归 + Git 二进制/`.pyc` 审计 | **ALL GREEN**（zero `.pyc`/`__pycache__`，`raw_firmware_bytes_leaked == 0`） |
