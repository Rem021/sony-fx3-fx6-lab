# Phase 368 工程闭合报告：`23/23` 第 23 级物理台架准备度预检器（`preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt` / `preflight-phase368`，Global Sony Waves 77–78）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H464` · **Phase 368（`23/23` Physical Bench Readiness Verifiers）**
- **上游情报基线**：
  - [Global Sony Wave 77 实证情报报告](../2026-11-18-global-sony-wave77-movieset-vpg-awbprio-atw-touchpad-screenreader-version-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`：`[File Format]` 6 编码与 `XAVC S-I DCI 4K` `24.00p` `MODEL_EVENT_REBOOT_BY_CROSS_2400P` / 回放隔离、5 阶 `100..1350MBPS` `V60`/`V90`/`VPG200`/`VPG400` 门禁与 `G139` 勘误、`xavc_hs_8k` 休眠拒止 vs FX6 `Class300`；`[Priority Set in AWB]` vs Still 独占且抗 Reset 的 `[Shutter AWB Lock]` 与 `2500K..9900K` 75 步色温 vs FX6 `WHT BAL B/A/PRESET` & `ATW Speed 1..5`；`G109` 勘误校正——`[Focus Assistant]` 4 项与 `[Peaking Display]` 3 项全抗 `[Camera Settings Reset]`、休眠 `[Touch Panel/Pad]` / `[Touch Shutter]` 证伪与 FX6 3 项 `Peaking`；双机型编译但受 SKU/语言门禁隐藏的 `[Accessibility]`/`[Screen Reader]` 0 暴露、`G104` 勘误精确 2 行 `[Version]` 弹窗与 `BODYDATA.DAT` `EROFS=30` 防火墙）
  - [Global Sony Wave 78 实证情报报告](../2026-11-18-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/README.md)（`78/78 Waves` 收官：`G86` 缺口补全——抗 Reset 父项 `[Exposure Ctrl Type]` vs 可重置 `[Auto/Manual Swt. Set.]`/`[Auto Slow Shutter]` 与 Ver. 6.00+ Movie/S&Q `[Shutter Mode]` `Speed`/`Angle` `BK4` 独立寄存器及休眠 `Var. Shutter` 证伪 vs FX6 4 模 `Angle/Speed/ECS/Off`；`[SteadyShot]` `Active ~1.104x` 4 互斥锁、`Catalyst` 陀螺仪 `RTMD` 仅限 `Off/Active` 且排除 `120p`/`S&Q`、`47` 项 `8..1000mm` 焦距表与 Ver. 2.00+ 移除 `200mm` 注记 vs FX6 零机身 IBIS + 3 档光学镜头 OSS；`Playback -> [Photo Capture]` `8.3M`/`2.1M` 禁 `DCI 4K` 与抗 Reset Playback `[JPEG/HEIF Switch]`、`G126` 补全精确 3 项 `[View Mode]` 与休眠 `AVCHD/MP4` 拒止、`[Rating]` `1..5` 与 `Slot 1 EROFS=30` 防火墙 vs FX6 `Clip Flag` `OK/NG/KEEP`；零原生 UVC `[USB Streaming]` `4K 30p` 谣言证伪、仅出站 `SRT Caller` 与 `38 Mbps` / 禁 `24p`/`120p` 推流矩阵、零射频 `Airplane Mode = On` + `USB-LAN` 旁路 vs FX6 外接 `CBK-WA100`/`PDT-FP1`）
- **前序模板基线**：
  - [Phase 358 工程闭合报告](../2026-11-18-phase358-preflight22-metering-pplut-ibis-customkey-diffset8-gammadisp-usblan/README.md)（第 22 级预检器模板）
  - [Grand Milestone Phase 364 闭合报告](../2026-11-18-phase364-grand-milestone-364-master-gate/README.md)（6 支柱总闸门基线）

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 23 级物理台架预检器严格在 6 文件所有权范围内落地，将 `fx6_closure` 只读物理台架预检体系推进至 `23/23`**
   - 新增 [`realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py)（`3,232` 行，Schema `realhw_preflight23_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_srt_v1`，版本 `phase368_v1`），成为只读物理台架预检器链路的 **第 23 级**（`Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342 -> Ph345 -> Ph354 -> Ph358 -> Ph368`）。
   - 全部 `182` 项公共符号已以非遮蔽方式接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3996-L4179) 与 `__all__`（[#L8064-L8246](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L8064-L8246)），未遮蔽 Phase 358 或 Milestone 364 任何导出；CLI 主命令 `preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt` 与短别名 `preflight-phase368` 已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7360-L7371)（处理入口 [#L6980](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L6980)、参数定义 [#L8426](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L8426)、分派 [#L11404-L11407](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L11404-L11407)，`help=` 中 `%` 已全部转义为 `%%`），实测长命令与短别名在离线/干跑模式下生成 **字节级一致的 `report_sha256`**；并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L548-L552) 追加第 `# 67.` 节。

2. **`实测事实`：Waves 77–78 8 项实证子审计已建模为 Check Groups A–D 合约并与 `16/16 H0 == H3` 双介质 `528 B FX3RCPT1` Tier-0 门控闭环**
   - **Check Group A（Wave 77.1 & 77.2：`[File Format]` 6 编码 / `DCI 4K` `24.00p` 隔离 / 5 阶卡速防火墙 & `[Priority Set in AWB]` / `[Shutter AWB Lock]` / `75` 步色温）**：[`evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py#L1159) 校验 FX3 6 编码矩阵（`XAVC HS 4K` 无 `29.97p/25p`；`XAVC S-I DCI 4K` `24.00p` 跨帧率触发 `MODEL_EVENT_REBOOT_BY_CROSS_2400P` 且回放隔离为仅 `24.00p`；`S&Q DCI 4K` 封顶 `60/50fps` `600M` 而禁止 `100/120fps`，`48fps` 独占 `24.00p + DCI 4K`；校对 `G139` 勘误使 `S&Q XAVC S HD 100/120fps` 仅要求 `SDXC V60+`、仅 `200/240fps` 要求 `V90+`；校对 `100..1350MBPS` 5 阶与 `VPG400` `0xea64/0xea6c/0xea78/0xea7b` 高码率 `S&Q + Proxy` 触发门限；拒止休眠 `xavc_hs_8k` 为 `EOPNOTSUPP=95`）对比 FX6 `XAVC-I`/`XAVC-L` `Class300`（休眠 `Class480` / `XAVC-L25`；`XAVC-L` 无 DCI 4K）；校验可重置 `[Priority Set in AWB]`（`_f 0x67a7`，在 `Cine EI / Cine EI Quick` 下因禁用 `Auto` 而不生效）对比 Still 独占且抗 Reset 的 `[Shutter AWB Lock]`（`_f 0x66db`，Movie 需走 Custom Key `AWB Lock Hold/Toggle`）及 `2500K..9900K`（`100K` 步进 `75` 档）对比 FX6 `WHT BAL` `B/A/PRESET`（`2000K..15000K`）与 `ATW Speed 1..5`（`Cine EI` 禁用）。
   - **Check Group B（Wave 77.3 & 77.4：抗 Reset `[Focus Assistant]` 4 + `[Peaking Display]` 3 `G109` 勘误、`[Touch Operation]` vs 休眠 `[Touch Panel/Pad]`、`[Screen Reader]` SKU 门禁 & 2 行 `[Version]` `G104` 勘误）**：[`evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py#L1454) 校正 `G109` 勘误，强制全部 4 项 `[Focus Assistant]`（含 Still 独占且受 5 项互斥约束的 `[AF in Focus Mag.]`）与全部 3 项 `[Peaking Display]`（`0 px` HDMI）在 `[Camera Settings Reset]` 下均保持 `Not available`（仅 `Initialize` 复位）；校验 4 项抗 Reset `[Touch Operation]` 并对休眠 `[Touch Panel/Pad]` / `[Touch Shutter]` 返回 `EOPNOTSUPP=95`，对比 FX6 仅 3 项 `Peaking`（`0` 绑定休眠 `Normal`/`Frequency`）与 `VF x3/x6` / `HDMI x2/x4` 放大；校验证实双机型均编译但通过机型/SKU 门禁隐藏 `[Accessibility]` / `[Screen Reader]`（FX3 & FX6 UI 均暴露 `0` 项，`0` HDMI 音频交叉符号）；校正 `G104` 勘误，锁定 FX3 `[Version]` 仅显示 `Body` + `Lens` 精确 2 行（卡口适配器复用 `Lens` 槽位、`0` MI-Shoe 版本显示、飞行模式下静默联网更新红点、`Slot 1 BODYDATA.DAT` 受 `EROFS=30` 防火墙阻断），对比 FX6 `Body` + `Lens` + `Ext. Unit`。
   - **Check Group C（Wave 78.1 & 78.2：`G86` 抗 Reset 父项 `[Exposure Ctrl Type]` vs `[Shutter Mode]` `Speed`/`Angle` & `[SteadyShot]` `Active` 4 锁 / `Catalyst` vs FX6 零机身 IBIS + 3 档镜头 OSS）**：[`evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py#L1693) 补全 `G86` 缺口，强制父项 `[Exposure Ctrl Type]`（`_f 0x787e`）抗 `[Camera Settings Reset]`（`Not available`，仅 `Initialize` 退回 `Flexible Exp. Mode`），而子项 `[Auto/Manual Swt. Set.]`（`Av`/`Tv`/`ISO`）与 `[Auto Slow Shutter]` 随 Reset 归位；校验 Ver. 6.00+ Movie/S&Q `[Shutter Mode]` `Speed`/`Angle`（`BK4` `0x01120024` vs `0x01120028` 独立寄存器、`19` 个标准角符号 + `10` 档 `2F..64F` 慢速等效角、免疫 `[Exposure step]`、强制 Still/Movie 快门拆分）并拒止休眠 `Var. Shutter`（`EOPNOTSUPP=95`），对比 FX6 4 模 `Angle/Speed/ECS/Off`；校验 `[SteadyShot]` `Active`（`~1.104x` 裁切）在 `119.88p/100p`、`S&Q >= 100fps`、`HDMI RAW=On`、`De-Squeeze != Off` 下的 4 重互锁与 Ver. 2.00+ 删除旧版 `>=200mm` 注记、`47` 档 `8..1000mm` 焦距表、休眠 `Dynamic active`/`Intelligent Active`/`Super Active` 拒止、`Catalyst` 陀螺仪 `RTMD` 仅支持 `Off/Active`（排除 `120p` 与 `S&Q`），对比 FX6 零机身 IBIS（`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`）与 3 档光学镜头 OSS `Active/Standard/Off`（Catalyst 需关闭镜头 OSS）。
   - **Check Group D + Tier-0（Wave 78.3 & 78.4 + `16/16 H0 == H3`：`Playback -> [Photo Capture]` / 3 项 `[View Mode]` `G126` / `[Rating]` & 零原生 UVC / `SRT Caller` / `Airplane Mode = On` 零射频）**：[`evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py#L2227) 与 [`_extract_tier0_evidence`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py#L1955) 校验 `[Photo Capture]` `8.3M`（4K）/ `2.1M`（HD）输出与 `XAVC S-I DCI 4K` 硬阻断、抗 Reset Playback `[JPEG/HEIF Switch]`、补全 `G126` 精确 3 项 `[View Mode]`（`Date View`/`Folder View(Still)`/`Movie View`，拒止休眠 `AVCHD View`/`Folder View(MP4)`）、`[Rating]` `1..5`（抗 Reset）与 `Slot 1 EROFS=30` 写入防火墙对比 FX6 `Clip Flag` `OK/NG/KEEP`；校验零原生 UVC `[USB Streaming]` 铁证（推翻 `4K 30p` 谣言，锁定 `[USB Connection Mode]` 精确 4 项、休眠 UVC 仅含 `4K_12_5P/15P` 等）、仅出站 `SRT Caller`（零 `SRT Listener`）、`RTMP/RTMPS/SRT` 最高 `38 Mbps` / 禁用 `24p`/`120p` / `8` 组码率配置与 `[Movie Rec During Streaming]` 规则、`Airplane Mode = On` 零射频（`rf_tx_packets == 0`）+ `USB-LAN` 旁路对比 FX6 外置 `CBK-WA100`/`PDT-FP1`，并强制双介质（不同 `st_dev`）`528 B FX3RCPT1` 与 `16/16 H0 == H3` 验签。

3. **`实测事实`：4 模式 `108` 项单元测试、`verify-milestone-364` 双模总闸门、`Milestone 364` / `Phase 358` 回归与 `clean-audit` 实测全部通过**
   - **Phase 368 四模式 108 项单元测试**：[`test_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py)（`2,194` 行，`108` 项测试，`>= 96` 要求，子进程统一设置 `timeout=45`）在 **4 种环境模式** 下全部实测 **`Ran 108 tests -> OK`**（`432/432` 全绿）：
     1. Normal（默认 `LOCAL_DONOR_O_RDONLY`，清除 clean-room 环境变量）：`Ran 108 tests in 118.798s -> OK`；
     2. `FX3_CLEAN_ROOM_TEST=1`：`Ran 108 tests in 120.088s -> OK`；
     3. `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 108 tests in 120.797s -> OK`；
     4. 无供体模式（`FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase368_missing`，且测试内含显式 mock `_resolve_work_root_or_none -> None` 与 `work_root=Path("/nonexistent/...")` 用例）：`Ran 108 tests in 132.061s -> OK`。
   - **Grand Milestone Phase 364 双模总闸门 & 回归**：
     - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364` 双模式（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` `CLEAN_ROOM_SYNTHETIC`）均实测返回 **`status=OK`**、`pillars=6/6`、`gate156=153/156`、`recovery=66/66`、`auditors=45/45`、`vm_stages=82/82`、`preflights=22/22`、`h0_eq_h3=16/16`、`qemu=48/48(144/144)`、`pngs=96/96(max=27467B)`、`leaked=0`、`ready_attach=False`；
     - `test_realhw_milestone364_master_gate.py`：Normal 模式实测 **`Ran 96 tests in 73.748s -> OK`**，`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式实测 **`Ran 96 tests in 68.512s -> OK`**；
     - Phase 358 前置回归 `test_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier.py` 实测 **`Ran 108 tests in 88.886s -> OK`**（无遮蔽/无回归）。
   - **洁净度审计**：`PYTHONDONTWRITEBYTECODE=1 make clean-audit` 实测输出 **`ALL GREEN`**（零 `.pyc` 或未跟踪二进制残留）。

4. **`推断`（未执行物理真机边界声明）**
   - 本阶段全部验证均基于宿主机只读合约模型、`os.O_RDONLY` 有界（`<= 64 B`）供体头核验以及确定性模拟回执（`--simulate-bench-dry-run`），尚未在真实物理 `ILME-FX3` 机身上采集双卡 `528 B FX3RCPT1` 实体回执或执行真机 USB/SD/HDMI/网络联机操作，因此所有报告输出均硬锁定 `overall_ready_for_hardware_attach == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`persistent_write_release == False`、`cross_model_flash_authorized == False`；台架互锁、`Slot 1 EROFS=30` 防火墙及无射频 `USB-LAN` 行为的真机实效在真实双卡回执到达前属工程安全推断，任何物理挂接仍须由独立只读双介质 `528 B FX3RCPT1` 验签放行。

---

## 2. 四态确定性 CLI 实测指纹与 6 文件清单（`实测事实`）

### 2.1 CLI 四态 `report_sha256` 实测表

> 以下四态均于当前工作树通过 `/usr/bin/python3 -B -m fx6_closure preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt ... --json` 与短别名 `preflight-phase368` 实测捕获，长命令与短别名生成的 `report_sha256` 字节级一致，且单测断言 `elapsed_seconds` 已从规范化 JSON 与摘要哈希中递归剔除。

| 验证模式（`verification_mode`） | 模拟干跑 | `overall_status` | `go_no_go` | CLI `rc` | 供体读取（`O_RDONLY`） | `raw_firmware_bytes_leaked` | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1/8`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `c048118602256448e79a23feaf9709a9ce5b9b2f66318478f08e858664dc3607` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `1/8`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `8e5c882feb4d5b4b1b5b98b21601503a8fc0078bebe43b9cd16a3af505282971` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/8`（`0 B`） | `0` | `07cca497cca8ca8e31d1e34883c2637e46998e8f87da75d9636def2d92f5f574` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/8`（`0 B`） | `0` | `0e07a1513d12f4fba29b6683bda38a4f4c670bc28701ba7783fd709c9e9606fd` |

### 2.2 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py)（新增，`3,232` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3996-L4179)（新增 Phase 368 `182` 项非遮蔽导入与 `__all__` 导出 [#L8064-L8246](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L8064-L8246)）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7360-L7371)（新增 `preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt` 主命令及 `preflight-phase368` 短别名、全量参数 [#L8426](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L8426) 与分派 [#L11404-L11407](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L11404-L11407)）
4. [`outputs/fx6-on-fx3-closure/tests/test_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py)（新增，`108` 项 4 模式单元测试，`2,194` 行）
5. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L548-L552)（追加 Section `# 67.`）
6. [`reports/2026-11-18-phase368-preflight23-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-srt/README.md`](./README.md)（本工程闭合报告）

---

## 3. 可复现验证命令与实测结果（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py"
CMD="preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt"

# 1. 四模式 108 项单元测试（均已实测 Ran 108 tests -> OK）
env -u FX3_CLEAN_ROOM_TEST -u FX3_FX6_FORCE_CLEAN_ROOM -u FX3_FX6_MAC_WORK_ROOT PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase368_missing PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"

# 2. CLI 门控与别名一致性实测（rc=0 / rc=2 / rc=0 / rc=2 / rc=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase368 --simulate-bench-dry-run --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --simulate-bench-dry-run --json

# 3. Milestone 364 双模总闸门与洁净度审计（均已实测 status=OK, pillars=6/6, preflights=22/22, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364
PYTHONDONTWRITEBYTECODE=1 make clean-audit
```
