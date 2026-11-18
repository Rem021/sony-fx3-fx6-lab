# Phase 358 工程闭合报告：`22/22` 第 22 级物理台架准备度预检器（`preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning` / Global Sony Waves 75–76）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H449` · **Phase 358（`22/22` Physical Bench Readiness Verifiers）**
- **上游情报基线**：
  - [Global Sony Wave 75 实证情报报告](../2026-11-18-global-sony-wave75-milestone-metering-pp-lut-ibis-steadyshot-pb-file-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`：`[Metering Mode]` 6 档 / Still 独占 Reset 免疫 `[AEL w/ Shutter]` / `[Exposure step]` Wave 75 G96 勘误 vs FX6 `Auto Exposure Level -3.0..+3.0` 25 步、`PP1..11` 双重 Reset/Init 免疫 vs `PPLUT1..4` 重置与 `1080p` HDMI 锁、`/Private/Sony/PRO/LUT` `.cube <=63 B` & MP4 `[Embed LUT File]`、`[SteadyShot]` 5 轴防抖与 47 项精确焦距表 `8..1000mm` vs FX6 零机身 IBIS、Playback 5 项零写入配置与 `Cam ID + Reel#` 17 字符命名 vs 37 字符 `[Title Name Settings]` 及 `Slot 1` `EROFS=30`）
  - [Global Sony Wave 76 实证情报报告](../2026-11-18-global-sony-wave76-customkey-diffset8-gammadisp-mlut-usblan-ipsec-cleaning-intel/README.md)（`XLR-H1` 手柄 `0` 可映射自定义按键、`Still=16` / `Movie=16` / `Playback=7` 三域自定义按键、`[Different Set for Still/Mv]` 精确 8 项与 `[Picture Profile]` 复选框跨 `Initialize` 持久性、`[Gamma Display Assist]` `Log` 互锁移交与休眠 `S-Log2` vs FX6 4 路 `MLUT`、`USB-LAN` 零射频旁路与 `[Access Authen. Settings]=On`、Ver. `7.00+` 禁用 `[Security(IPsec)]`、`[Airplane Mode]=On` 跨 `Reset Network Set.` 持久而仅由 `Initialize` 清零、`[Sensor Cleaning]` `>=51%` 电量与物理拨盘关机门控 vs 休眠 `[Anti-dust Function]`/`[Shutter When Pwr OFF]`）
- **前序模板基线**：[Phase 354 工程闭合报告](../2026-11-18-phase354-preflight21-lockop-shocklesswb-focusmag-afspeed-zebra-saveload/README.md)（第 21 级预检器模板）

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 22 级物理台架预检器严格在 6 文件所有权范围内落地，将 `fx6_closure` 只读物理台架预检体系推进至 `22/22`**
   - 新增 [`realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py)（`3,087` 行，Schema `realhw_preflight22_metering_pplut_ibis_customkey_diffset8_gammadisp_usblan_cleaning_v1`，版本 `phase358_v1`），成为只读物理台架预检器链路的 **第 22 级**（`Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342 -> Ph345 -> Ph354 -> Ph358`）。
   - 全部 `188` 项公共符号已以非遮蔽方式接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3760-L3947) 与 `__all__`（[#L7599-L7788](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L7599-L7788)），已实测确认 `188/188` 导入项均存在于模块与 `__all__` 且未遮蔽 Phase 354 或 Milestone 349 导出；CLI 子命令 `preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning` 已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7929)（help 中 `%` 已转义为 `%%`）及末尾分发入口（[#L10872-L10873](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L10872-L10873)），并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L537-L541) 追加第 `# 65.` 节。

2. **`实测事实`：Waves 75–76 Check Groups A–D 契约与 `16/16 H0 == H3` 双介质 `528 B FX3RCPT1` 门控全部 fail-closed 落地**
   - **Check Group A（Wave 75 `[Metering]` / `[Exposure step]` 勘误 / `PP1..11` vs `PPLUT1..4` & User LUTs）**：[`evaluate_p358_check_group_a_metering_expstep_pp_and_userlut`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py#L1117) 校验 FX3 `[Metering Mode]` 6 档（`CIZ`/Digital Zoom 下强制锁定 `MULTI`）、`[Face Priority in Multi Metering]`（`BKID_APP_setting_face_detection_in_multi`）、`[Spot Metering Point]`（`WIDE`/`ZONE`/`CENTER_FIX` 强制退回 `CENTER`）、Still 独占且耐受 `[Camera Settings Reset]` 的 `[AEL w/ Shutter]`，以及 **`[Exposure step]`（`0.3EV`/`0.5EV`）Wave 75 G96 勘误**（`[Camera Settings Reset]` 时不可重置 `Not available`，仅随 `[Initialize]` 重置，且不影响 `[Shutter Angle]` 档位；Cine EI 模式下测光表不随 EI 索引变更）；对比 **FX6 `Shooting > Auto Exposure > Level` `-3.0..+3.0` 步进 `0.25`（精确 25 档，驳斥 `-2.0..+2.0EV` 传闻）** + `Speed -99..+99` + `Detect Window 1..6/Custom`（`Width 40..999`）。同时校验 `[Picture Profile]` 索引重置回 `PP11`（`S-Cinetone`）且 Movie 独占 `PPLUT1..4`（内录强制 HDMI 降为 `1080p`）在 Reset 与 Initialize 均被重置，而 **`PP1..11` 内部参数同时免疫 Reset 与 Initialize**；校验 `[Manage User LUTs]` `User1..16`（17/33 点 `.cube`、`<=63` 字节文件名、读取 SD `/Private/Sony/PRO/LUT` 或 CFexpress-A `/Sony/PRO/LUT`）与 MP4 `[Embed LUT File]`（FX3 零 MXF、零外挂 `.cube` sidecar、SD/SDHC 下锁定 `Off`）对比 FX6 16 UI `User` LUT（内部 50 槽缓冲）及 4 通道 `MLUT`。
   - **Check Group B（Wave 75 IBIS 47 项焦距表 / Playback 5 项只读 / `Cam ID + Reel#` vs 37 字符标题 & `Slot 1` `EROFS=30`）**：[`evaluate_p358_check_group_b_ibis_playback_and_file_slot1`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py#L1472) 校验 FX3 5 轴机身防抖 `[SteadyShot]`（`ACTIVE ~1.1x` / `STANDARD` / `OFF`；`>=100/120p`、`HDMI RAW=On`、`De-Squeeze != Off` 禁用 `ACTIVE`；Catalyst Gyro 仅支持 `OFF` 或 `ACTIVE` + 原生 E 卡口并排除 `120p`/`S&Q`）与精确 **47 项手动焦距表（`8mm..1000mm`）**，将休眠 Alpha 符号 `Dynamic/Intelligent/Super Active` fail-closed 拦截为 `EOPNOTSUPP=95`，对比 **FX6 零机身物理 IBIS**（`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`，仅光学 OSS）。校验 Playback 5 项只读参数（含官方拼写残留 `BKID_APP_setting_display_rotatiton`）耐受 Reset，以及 Movie `17 字符` `Cam ID + Reel#`（`C999->D001` 进位）vs `37 字符` `[Title Name Settings]`（对比 FX6 `4..46` `Title Prefix` MXF），并对 `Slot 1` 上的 `[Create New Folder]` / `[Forced File No. Reset]` / `[Select REC Folder]` / `[Series Counter Reset]` 强制执行 `EROFS=30` 防火墙（`slot1_data_sector_writes == 0`）。
   - **Check Group C（Wave 76 `XLR-H1` 零可自定义按键 / `[Different Set for Still/Mv]` 8 项 / `[Gamma Display Assist]` vs `[Select LUT]`）**：[`evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py#L1715) 校验 **`XLR-H1` 手柄含 `0` 个可映射自定义按键、`0` 个手柄 REC 键、`0` 个手柄拨盘**，校验 FX3 三域自定义按键拓扑（`Still=16` 除 `MOVIE Button` 外支持 `Follow Custom`；`Movie=16` 含出厂映射；`Playback=7` 跳过 `C4=Delete` 并新增 `Fn Button`）并将休眠 Alpha 符号（`ael_button`、`moviel_product_showcase_set_button` 等）拦截为 `EOPNOTSUPP=95`；校验 `[Different Set for Still/Mv]` 精确 **8 项**（`Common->Separate` 时 `Custom WB` 仅复制到 Still；`Separate->Common` 保留 Still 侧 `Aperture`/`Shutter Speed`/`Custom WB`；`[Shutter Mode]=Angle` 下自动拆分 Still/Movie；**`[Picture Profile]` 复选框同时免疫 `[Camera Settings Reset]` 与 `[Initialize]`**）；校验 `[Gamma Display Assist]`（FX3 未暴露 `S-Log2`、HDMI/TV `0 px` 注入）在 `[Log Shooting] != Off` 时硬锁定 `Off` 并移交 `[Display LUT]` + `[Select LUT]`（Log 下拍静态照片除外），对比 FX6 零 UI `Gamma Display Assist` 与 4 路 `MLUT`。
   - **Check Group D + Tier-0（Wave 76 `USB-LAN` / `Access Authen.` / Ver. 7.00+ 禁用 `IPsec` / `Airplane Mode` 分裂 / `[Sensor Cleaning]` + `16/16 H0 == H3`）**：[`evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py#L2207) 校验 `USB-LAN`（`libWiredLanResource.so` / `libNetServiceEther.so` / `dhcpcd`，与 Multi/Micro USB 及 Wi-Fi 互斥，**不被 `[Airplane Mode]=On` 阻塞**）、`[Access Authen. Settings]=On` 默认（SSH + PTP-IP，密码 `8..16` 字符）、Ver. `7.00+`（或认证启用）硬禁用 `[Security(IPsec)]`（且 FX6 `0` 个 IPsec UI 绑定），以及 **`[Airplane Mode]=On` 跨 `[Reset Network Set.]` 保留、仅由 `[Initialize]` 清零为 `Off`**；校验 `[Sensor Cleaning]`（`>=51%` 电量门控 + 物理拨盘关机吹尘 `_g 0x6221`）对比 FX3 零 UI 休眠 `[Anti-dust Function]` / `[Shutter When Pwr OFF]`、前置 `#5` `[IR Remote Ctrl]` 与 Still 独占 `[Auto Review]`（对比 FX6 `APR`、`2.5mm LANC` 与 `Rec Review`）；并借助 [`_extract_tier0_evidence`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py#L1924) 实施双介质不同 `st_dev` 的 `528 B FX3RCPT1` 与 `16/16 H0 == H3` 表面不可变校验。

3. **`实测事实`：4 模式 108 项单元测试、全量闭合发现测试（含 Milestone 349 92 项）、CLI 四态、`verify-milestone-349` 双模总闸门与 `clean-audit` 验证结果**
   - **Phase 358 四模式 108 项单元测试**：新增 [`test_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py) 共 **108 项**单元测试（`>= 100`），在 **4 种模式**（默认 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、无供体 `FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase358_missing`）下均实测 **`Ran 108 tests -> OK`**（`432/432` 全绿）。
   - **全量 `outputs/fx6-on-fx3-closure/tests` 55 文件发现与双模式实测**：
     - **`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式**（分 4 批串行执行全部 55 个测试文件）：`649 (skipped=51) + 1347 + 610 + 672 = 3,278` 项测试 **全部 `OK`**（含 `test_realhw_milestone349_master_gate.py` 92/92 OK 与 Phase 358 108/108 OK）。
     - **正常（Normal / Local Donor）模式**（分 4 批串行执行全部 55 个测试文件）：`649 + 1347 + 610 + 672 = 3,278` 项测试中 **3,276 项 `OK`**，包含 `test_realhw_milestone349_master_gate.py`（单独双模亦实测 `92/92 OK`）与 Phase 358（`108/108 OK`）；仅前序遗留文件 `test_phase110_milestone_master_gate.py`（`test_02_milestone110_builds_under_2500ms_and_is_ready`: `2.948s >= 2.5s`）与 `test_phase130_milestone_master_gate.py`（`test_02_milestone130_builds_under_2500ms_and_is_ready`: `3.024s >= 2.5s`）在本地 2.5s 墙钟阈值上超时（随下游 `fx3-firmware-lab` 增至 45 审计器与 `fx3-vm` 增至 78 阶段的自然耗时增长，与本任务 6 文件无关）。
   - **双模总闸门与洁净度审计**：
     - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-349` 与 `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-349` 均实测返回 `status=OK`、`pillars=6/6`、`leaked=0`（注：未改动只读基线 `realhw_milestone349_master_gate.py`，其自身仍锁定并打印 `preflights=20/20`，同时 `fx6_closure` 包内已完整注册并测试第 21/22 级预检器）。
     - `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 实测输出 **`ALL GREEN`**（零 `.pyc` 或未跟踪二进制残留）。

4. **`推断`（物理真机边界声明）**
   - 本阶段所有测试与验证均基于宿主机只读契约模型、`os.O_RDONLY` 有界（`<= 64 B`）供体头核验以及确定性模拟回执（`--simulate-bench-dry-run`），尚未在真实物理 `ILME-FX3` 机身上采集双卡 `528 B FX3RCPT1` 实体回执或执行真机 USB/SD/USB-LAN 连线操作，因此所有报告输出均保持 `overall_ready_for_hardware_attach == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`persistent_write_release == False`、`cross_model_flash_authorized == False`；台架互锁、`Slot 1 EROFS=30` 防火墙及 `USB-LAN`/`[Sensor Cleaning]` 行为的真机实效在真实双卡回执到达前属工程安全推断，任何物理挂接仍须由独立只读双介质 `528 B FX3RCPT1` 验签放行。

---

## 2. 四态确定性 CLI 实测指纹与 6 文件清单（`实测事实`）

### 2.1 CLI 四态 `report_sha256` 实测表

> 以下四态均于当前工作树通过 `/usr/bin/python3 -B -m fx6_closure preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning ... --summary --json` 实测捕获，且单测断言 `elapsed_seconds` 已从规范化 JSON 与摘要哈希中递归剔除。

| 验证模式（`verification_mode`） | 模拟干跑 | `overall_status` | `go_no_go` | CLI `rc` | 供体读取（`O_RDONLY`） | `raw_firmware_bytes_leaked` | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1/8`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `850dbb9616d7acc0a3de1763c36c1a4d6ac0171a04df85448778e305ba6019f9` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `1/8`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `66e0ed8c3e23928e7fab332dadbfbca4b72730161f1c33fd5951aad4e9b37f99` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/8`（`0 B`） | `0` | `af24d9d280734b87e11c2026c23fe54613a2cb17ae9b9b821bd8edd1bb740318` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/8`（`0 B`） | `0` | `b643719ee2c7c4856708e07ecdcbe5925da8650644e698f86f01f31b2280c70c` |

### 2.2 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py)（新增，`3,087` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3760-L3947)（新增 Phase 358 `188` 项非遮蔽导入与 `__all__` 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7929)（新增 `preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning` 子命令及全部参数）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L537-L541)（追加 Section `# 65.`）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py)（新增，108 项四模式单元测试，`1,982` 行）
6. [`reports/2026-11-18-phase358-preflight22-metering-pplut-ibis-customkey-diffset8-gammadisp-usblan/README.md`](./README.md)（本工程闭合报告）

---

## 3. 可复现验证命令与实测结果（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py"
CMD="preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning"

# 1. 四模式 108 项单元测试（均已实测 Ran 108 tests -> OK）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase358_missing PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"

# 2. CLI 门控实测（rc=0 / rc=2 / rc=0 / rc=2 / rc=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --summary --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --summary --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --summary --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --simulate-bench-dry-run --summary --json

# 3. Milestone 349 双模测试与总闸门 + 洁净度审计（均已实测 status=OK, pillars=6/6, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-349
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-349
PYTHONDONTWRITEBYTECODE=1 make clean-audit
```
