# Phase 318（Stage 66 — `66/66` 里程碑）：Wave-56 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 5 项 `[Dial Customize]` & 3 物理拨盘 `Rear Dial L/R` 禁令、`My Dial 1..3` 锁定覆盖与 `12 Still + 12 Movie` `Fn Menu`、3 项 `[Live View Display Set.]` & 干净 HDMI `[Grid Line]`，以及 `[Manage User LUTs]` `User1..16` / `[Embed LUT File]` SD/SDHC 硬锁 / `PPLUT1..4` 像素烘焙 & `Slot-1` Vault 防火墙 HIL 协同仿真报告

## 结论先行

1. **Stage 66（`66/66` 里程碑）全闭环通过并接入全板总装门禁**：新增 [`outputs/fx3-vm/realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py`](../../outputs/fx3-vm/realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py)（Schema `realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator_v1`），并接线至 [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为第 66 阶段（`vm_stages=66/66`），`Stage 1..65` 保持完全向后兼容（支持 `--include-stage66`、`--skip-stage66`、`--no-include-stage66`、`--skip-phase318`）。
2. **17 份真实 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 实机供体双模审计零失真**：通过受界 `os.O_RDONLY`（`<= 4096 B`）核验全部 17 份供体（FX3 `string_*_f.uxc` 4 语全集 + `string_*.uxc` 4 语全集 + `string_*_g.uxc` 4 语全集 + FX6 `string_english.uxc` / `string_english_2.uxc` + `FX3 appFw.so`、`FX3 BK4`、`FX6 appFw.so`）字节长度、SHA-256 与符号/词条锚点；`LOCAL_DONOR_O_RDONLY`（摘要 `9dad958c6261`）、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（双洁净室环境变量产生完全一致的确定性摘要 `37bef535691e`）三模全部通过，且 `raw_firmware_bytes_leaked == 0`。
3. **90 项 Stage 66 专项单测（三模全绿）+ 全量 `fx3-vm` 单测（`3,449` 项双模全绿）+ `Milestone 311` & `Milestone 295` 双模门禁全绿 + `clean-audit` 零残留**：全部硬件写安全红线与 Wave-56 实机真值红线锁定（`persistent_emmc_writes_authorized=False`、`hardware_live_attachment_authorized=False`、`overall_ready_for_hardware_attach=False`、`fx3_physical_dial_count=3`、`fx3_has_dual_rear_dials_l_r=False`、`fx3_has_hardware_hold_switch=False`、`dial_bypass_events=0`、`fn_empty_invocation_leak_events=0`、`live_view_movie_sq_bypass_events=0`、`hdmi_clean_feed_grid_leaked_pixels=0`、`embed_lut_sd_bypass_events=0`、`slot1_data_sector_writes=0`、`physical_device_writes=0`）。

---

## 一、交付文件清单（严格限定 5 个自有文件）

| 序号 | 类型 | 路径 | 职责摘要 |
| --- | --- | --- | --- |
| 1 | NEW | [`outputs/fx3-vm/realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py`](../../outputs/fx3-vm/realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py) | Phase 318 Stage 66 核心模型、17 供体 `O_RDONLY` 审计、66A..66D 仿真器、安全/真值红线门禁与 CLI |
| 2 | EDIT | [`outputs/fx3-vm/fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil`（总阶段 `66/66` Milestone）与 CLI 开关 |
| 3 | EDIT | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 318 Stage 66 架构契约与三模运行/单测命令 |
| 4 | NEW | [`outputs/fx3-vm/tests/test_realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py) | 90 项双模单测（覆盖 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`） |
| 5 | NEW | [`reports/2026-11-17-phase318-vm-stage66-dial-customize-mydial-fn12x2-liveview-lut-embed-hil/README.md`](README.md) | 本中文结论先行工程报告 |

---

## 二、Wave-56 实机四大硬件契约验证摘要（实测事实）

### 1. Sub-Model 66A：5 项 `[Dial Customize]`（`Initialize`-Only）& Ver. 2.00+ 菜单演进 vs `FX6` 硬件拨盘

- **`MENU -> Setup -> [Dial Customize]` 精确暴露 5 项有效配置**，且**全部跨 `[Camera Settings Reset]` 留存（仅通过 `[Initialize]` 复位）**：
  1. `[Custom Key/Dial Set.]`（Ver. 2.00+ 取代 Ver. 1.xx `[Dial Setup]`）；
  2. `[My Dial Settings]`；
  3. `[Av/Tv Rotate]`：`Normal`（默认）/ `Reverse`；
  4. `[Function Ring(Lens)]`：`Power Focus`（默认）/ `APS-C/Super 35 mm / Full Frame`（严格拒绝 `"INVALID"` 返回 `EINVAL=22`）；
  5. `[Lock Operation Parts]`（Ver. 2.00+ 取代 Ver. 1.xx `[Dial / Wheel Lock]`）：`Off`（默认）/ `Multi-Selector Only` / `Dial + Wheel` / `All`，支持 `Fn` 长按与 **`MENU + Fn` 5 秒组合键**切换锁定。
- **休眠 Ver. 1.xx 符号 fail-closed 护栏**：对 `BKID_APP_setting_dial_setup`、`DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO` 与 `Dial/Wheel Setup`（`0x6a89`）统一拦截并返回 `EOPNOTSUPP=95`；
- **对比 `ILME-FX6 Ver. 6.01`**：FX6 无此菜单树，采用物理 `Multi Function Dial` + `Grip Dial` + `Handle Dial` + `IRIS` 拨盘 + `ND` 拨盘 + 物理 `HOLD` 滑动开关（双向跨机型调用分别 fail-closed 返回 `EOPNOTSUPP=95`）。

### 2. Sub-Model 66B：3 物理拨盘拓扑（禁用 `Rear Dial L/R`）、`My Dial 1..3` 锁定临时覆盖与 `12 Still + 12 Movie` `[Fn Menu Settings]`

- **`ILME-FX3` 物理拨盘拓扑真值**：机身严格仅配 **3 个物理拨盘**（`Front Dial` `0xe4da`、单个 `Rear Dial` `0xe4db`、`Control Wheel` `0xe353`）；对休眠 4 拨盘 Alpha 符号 **`Rear Dial L`（`0x6a5c`）与 `Rear Dial R`（`0x680d`）fail-closed 返回 `EOPNOTSUPP=95`**。
- **`My Dial 1..3`（`list0..2`，`Initialize`-only）**：
  - 3 组 NVRAM 银行（`My Dial 1..3`）在 Still/Movie/`S&Q` 间共享，而 `Hold` / `Toggle` / `1->2->3` 自定义键分别按 **Still 与 Movie 独立绑定**；
  - `1->2->3` 轮循自动跳过全为 `Not set` 的空银行；
  - **召回覆盖锁定语义**：召回激活 `My Dial` 时**临时解锁 `[Lock Operation Parts]`**（即使处于 `Dial + Wheel` 或 `All` 锁定态也允许 3 个物理拨盘生效），退出召回后精确恢复进入前的原始锁定模式。
- **`12 Still + 12 Movie` `[Fn Menu Settings]`（`_g 0x614b`，`Initialize`-only）**：
  - 严格分离 `fn_menu_item_ids_for_still0..11` 与 `fn_menu_item_ids_for_movie0..11`（`S&Q` 复用 Movie `Fn` 组），单组修改互不污染；
  - 当当前模式全部 12 槽位均为 `Not set`（`0xe0ac`）时，通过 `_f 0x6220` 契约阻断呼出并返回 `EINVAL=22`（`fn_empty_invocation_leak_events == 0`）；
  - 对比 `ILME-FX6`：使用 `Status Screens` 与 `Direct Menu`（`Home Screen Priority` / `Direct Menu Priority`），对 FX3 `My Dial` 与 `Fn 12x2` 返回 `EOPNOTSUPP=95`。

### 3. Sub-Model 66C：3 项 `[Live View Display Set.]`（Still-Only）& `[Grid Line]` 干净 HDMI 零渗漏隔离

- **严格 Still-Only 菜单位置**：位于 `Shooting -> Shooting Display -> [Live View Display Set.]`（`_f 0x6429`），在 `Movie` 与 `S&Q` 模式下访问 fail-closed 返回 **`EBUSY=16`**（且不暴露 3 个子项列表，`live_view_movie_sq_bypass_events == 0`）：
  1. `[Live View Display]`：`Setting Effect ON`（默认）/ `Setting Effect OFF`（**`Initialize`-only**；且在 **`[Bright Monitoring]` 激活时强制切至 `Setting Effect OFF`**）；
  2. `[Exposure Effect]`：`Exposure Set. & flash`（默认）/ `Exposure Setting Only`（**`Initialize`-only**）；
  3. **`[Frame Rate Low Limit]`**：`Off`（默认）/ `On`（**本组中唯一支持 `[Camera Settings Reset]` 复位的一项目**）。
- **`[Grid Line]`（`Initialize`-only）与干净 HDMI 隔离**：
  - `[Grid Line Display]`（`Off` 默认 / `On`）与 `[Grid Line Type]`（`Rule of 3rds Grid` 默认 / `Square Grid` / `Diag. + Square Grid`）跨 `[Camera Settings Reset]` 留存（仅 `[Initialize]` 复位）；
  - 当 `HDMI Info. Display = Off`（Clean HDMI）时，HDMI 输出流保持零 OSD/零网格线渗漏（**`hdmi_clean_feed_grid_leaked_pixels == 0`**）；当 `HDMI Info. Display = On` 时本地 LCD 按实机行为消隐且录制流仍零烧录；
  - 对比 `ILME-FX6`：使用 `Marker` / `Guide Frame`（同样 HDMI/RAW 零烧录），并对休眠 `CUSTOM_GRID_LINE0..3` PNG 槽位 fail-closed 返回 `EOPNOTSUPP=95`。

### 4. Sub-Model 66D & Redlines：`[Manage User LUTs]`（`User1..16`）、`[Embed LUT File]`（`Log Shooting Setting` SD/SDHC 硬锁）vs `PPLUT1..4` 像素烘焙 & `Slot-1` Tier-0 Vault 防火墙

- **`[Manage User LUTs]` & `[Select LUT]`**：
  - 位于 `Color/Tone -> [Manage User LUTs]`（`Initialize`-only），支持从 SD **`/Private/Sony/PRO/LUT`** 或 CFexpress **`/Sony/PRO/LUT`** 纯只读导入 17 点或 33 点 `.cube` 文件至 `User1..16`（超上限 `User17` 拦截 `EOPNOTSUPP=95`；**即使从挂载 Tier-0 Vault 的 `Slot 1` 导入，亦严格零写扇区 `slot1_data_sector_writes == 0`**）；
  - `[Select LUT]`（`S-Log3` / **`s709` 默认** / `709(800%)` / `User1..16`）支持 `[Camera Settings Reset]` 复位回 `s709`；选中尚未导入 `.cube` 的 `User` 槽位时回落输出 `S-Log3`。
- **`[Embed LUT File]`（`Log Shooting Setting`，SD/SDHC 硬锁 `Off`）vs `PPLUT1..4` 不可逆像素烘焙**：
  - `[Embed LUT File]` 位于 `Shooting -> Image Quality/Rec -> Log Shooting Setting`（非 `Color/Tone`，错误父菜单返回 `EOPNOTSUPP=95`），默认 `On` 且支持 `[Camera Settings Reset]`；仅在**合法 Log Shooting 且使用 CFexpress Type A / SDXC 介质**时于封装容器内嵌 `.cube` 元数据（无旁路 `.cube` 文件、无像素烘焙）；
  - 当介质为 **`SD` 或 `SDHC`** 时，`_g 0x61a0` **硬锁 `[Embed LUT File] = Off`**，强行设为 `On` 返回 **`EOPNOTSUPP=95`**（`embed_lut_sd_bypass_events == 0`）；
  - `Picture Profile -> PPLUT1..4`（需处于 `LOG_SHOOTING_OFF`）执行**不可逆像素烘焙**，无容器 LUT 元数据嵌入，且同时在 `[Camera Settings Reset]` 与 `[Initialize]` 时被复位；
  - `ILME-FX6`：禁止 `!` 前缀 `.cube` 文件名（返回 `EINVAL=22`），支持多声道 XAVC 容器 LUT 行为差异模型。
- **`Slot-1` Tier-0 Vault 100% Fail-Closed 防火墙**：
  - 任何试图向 `Slot 1`（Tier-0 Vault）录制、`Embed LUT` 落盘、`PPLUT` 烘焙写卡或创建 LUT 目录（`Make Cube Folder`）的请求 **100% fail-closed 拦截并返回 `EROFS=30`**，实测 **`slot1_data_sector_writes == 0`**；非 Vault 虚拟 `Slot 2` 上的相关操作在 `physical_device_writes == 0` 约束下非破坏性完成。

---

## 三、跨平台 CI 合规与验证实测数据（全量通过）

- **Stage 66 独立 CLI 自检（三模）**：
  - `LOCAL_DONOR_O_RDONLY`：`[PASS] Phase 318 Stage 66 (66/66 Milestone) | mode=LOCAL_DONOR_O_RDONLY donors=17 dials=3 dl_byp=0 fn_leak=0 lv_byp=0 hdmi_px=0 emb_byp=0 s1_wr=0 emmc_wr=0 leak=0 digest=9dad958c6261`
  - `FX3_CLEAN_ROOM_TEST=1` & `FX3_FX6_FORCE_CLEAN_ROOM=1`：双洁净室环境变量均输出完全一致的确定性摘要 `digest=37bef535691e`
- **全板 66 阶段套件 `fx3_vm_coemulation_suite.py --include-stage66 --summary`**：
  - `LOCAL_DONOR_O_RDONLY`：`m66=66/66`，`digest=4816ec1af1a7`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`m66=66/66`，`digest=8bfa94b7e7cb`
- **Stage 66 专项 90 项单测（三模全绿）**：
  - `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 全部 `Ran 90 tests (OK)`（无硬件写操作、无固件字节泄漏）。
- **全量 `outputs/fx3-vm/tests` 单测发现（双模全绿）**：
  - `LOCAL_DONOR_O_RDONLY`：`Ran 3449 tests in 196.483s (OK)`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 3449 tests in 189.123s (OK, skipped=5)`
- **主线总门禁 `make verify-milestone-311` & `make verify-milestone-295`（双模全绿）**：
  - `verify-milestone-311`（`LOCAL_DONOR_O_RDONLY`）：`status=OK`、`vm_stages=66/66`、`pillars=6/6`、`gate134=137/140`、`recovery=55/55`、`auditors=45/45`、`qemu=37/37(111/111)`、`pngs=74/74(max=27467B)`、`leaked=0`、`milestone311_sha256=b5b949e84eea1550...`
  - `verify-milestone-311 --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`status=OK`、`vm_stages=66/66`、`leaked=0`、`milestone311_sha256=e3bcda6834f70b35...`
  - `verify-milestone-295`（`LOCAL_DONOR_O_RDONLY`）：`status=OK`、`vm_stages=66/66`、`gate124=137/140`、`recovery=55/55`、`leaked=0`、`milestone295_sha256=f1a21a456a2a2920...`
  - `verify-milestone-295 --force-clean-room`（`CLEAN_ROOM_SYNTHETIC`）：`status=OK`、`vm_stages=66/66`、`leaked=0`、`milestone295_sha256=5ca1d1e19b715f5a...`
- **洁净室卫生与无泄漏审计 `make clean-audit`**：`[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.05s)`，`ALL GREEN in 0.05s`。
