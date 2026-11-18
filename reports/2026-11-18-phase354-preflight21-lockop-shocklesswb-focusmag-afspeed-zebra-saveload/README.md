# Phase 354 工程闭合报告：`21/21` 第 21 级物理台架准备度预检器（`preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset` / Global Sony Waves 73–74）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H443` · **Phase 354（`21/21` Physical Bench Readiness Verifiers）**
- **上游情报基线**：
  - [Global Sony Wave 73 实证情报报告](../2026-11-18-global-sony-wave73-lockop-shocklesswb-awblock-mfmag-recoverdb-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`）
  - [Global Sony Wave 74 实证情报报告](../2026-11-18-global-sony-wave74-afspeed-shift-zebra-custom-marker-saveload-camset-intel/README.md)（`AF Transition Speed`/`AF Subj. Shift Sens.`、`[Zebra Display]` `Custom1/2`、15 比例 `[Marker Display]` 与 `[Save/Load Settings]` / `[Camera Set. Memory]`）
- **前序模板基线**：[Phase 345 里程碑报告](../2026-11-18-phase345-milestone-preflight20-audio-reclevel-outtiming-4ch-touch-remoteshoot/README.md)（第 20 级预检器模板 `00d929b70`）

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 21 级物理台架预检器严格在 6 文件所有权范围内落地，覆盖 `21/21` 物理台架预检链路**
   - 新增 [`realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py)（`2,741` 行，Schema `realhw_preflight21_lockop_shocklesswb_focusmag_afspeed_zebra_saveload_camset_v1`，版本 `phase354_v1`），将只读物理台架预检推进至 **`21/21`**：`Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342 -> Ph345 -> Ph354`。
   - 全部 `163` 项公共符号已以非遮蔽方式接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3594-L3757) 与 `__all__`（[#L7246-L7410](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L7246-L7410)）；CLI 子命令 `preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset` 已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7509) 及末尾分发入口（[#L10446](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L10446)），并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L532-L535) 追加第 `# 64.` 节。

2. **`实测事实`：Waves 73–74 Check Groups A–D 契约与 `16/16 H0 == H3` 双介质 `528 B FX3RCPT1` 门控全部 fail-closed 落地**
   - **Check Group A（Wave 73 `[Lock Operation Parts]` / `MENU+Fn` 5s 全局锁定 & `[White Balance]`）**：[`evaluate_p354_check_group_a_lockop_menufn_and_wb`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py#L975) 校验 `Setup -> [Dial Customize] -> [Lock Operation Parts]`（纠偏非 `[Operation Customize]`，4 档 `Off`/`Multi-Selector Only`/`Dial + Wheel`/`All`，由 `Fn` 长按激活、`[AF Area Registration]=On` 时强制 `Off`、`My Dial 1..3` 临时穿透、耐受 `Camera Settings Reset`）+ `MENU + Fn` 5s 锁除 `SHUTTER` 外全部实体键轮（Touch 独立受 `[Touch Operation]` 管辖）+ 休眠 `UIBIZ_SLIKEY_LOCK`（`EOPNOTSUPP=95`）对比 FX6 双物理 `HOLD` 与 `User Menu with Lock`（`0000..9999`）；并核验可 Reset 的 `[Shockless WB]`（`Off`/`1 (Fast)` [def]/`2`/`3 (Slow)`，Movie/`S&Q` 独占）与 `[Priority Set in AWB]`（`Standard`/`Ambience`/`White`），对比 Still 独占且 **Reset 免疫**的 `[Shutter AWB Lock]`（`Shutter Half Press`/`Cont. Shooting`/`Off` [def]；Movie 须用 Custom Key `AWB Lock Hold/Toggle`）及 FX6 `ATW Speed 1..5` 与 `diadem_pro_settings_converter`。
   - **Check Group B（Wave 73 `[Focus Assistant]` 4 项 Reset 免疫子项 / 休眠 `[Focus Ring Rotate]` & `[Recover Image DB]` `Slot 1 EROFS=30` 防火墙）**：[`evaluate_p354_check_group_b_focus_assistant_and_media_db`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py#L1227) 校验 `Focus -> [Focus Assistant]` 4 项（均在 Ver. 2.00..7.02 耐受 `[Camera Settings Reset]`：`[Auto Magnifier in MF]` Still 独占、`[Focus Magnif. Time]`、`[Initial Focus Mag.]` Still FF `x1.0`/`x2.1` [`x4.1` 仅二次按键] vs APS-C `x1.0`/`x1.5` vs Movie `x1.0`/`x4.0`、`[AF in Focus Mag.]` Still 独占）+ 休眠 `[Focus Ring Rotate]`（`FX3 appFw.so` `0` 实现 -> `EOPNOTSUPP=95`）对比 FX6 `AF Assist`、`PUSH AUTO`、VF/LCD `x3/x6` 与 Ver. 6.0 `HDMI Focus Mag x2/x4`；并核验 Playback `[Delete]`（5 种批量模式、Reset 免疫 `[Delete confirm.]`/`[Delete pressing twice]`）、`[Protect]`（7 种模式、零 `"Cancel All Images"`、Proxy 协同保护）、只读 `[Display Media Info.]`（`40,000` 上限）及 `[Recover Image DB]`（`AVF_INFO/AVIN0001.{INP,BNP,INT}` 开机引导危害 -> `Slot 1` 强制 `EROFS=30` 防火墙，`slot1_data_sector_writes == 0`）对比 FX6 `Update Media` / `Restore Media`。
   - **Check Group C（Wave 74 `[AF Transition Speed]`/`[AF Subj. Shift Sens.]`/`Focus Frame Color` & 单选 `[Zebra]`）**：[`evaluate_p354_check_group_c_afspeed_shift_framecolor_and_zebra`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py#L1439) 校验 FX3/FX6 共享 `[AF Transition Speed]`（`1..7` def `5`，`Can be reset`）与 `[AF Subj. Shift Sens.]`（`1..5` def `5`，`MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE` — FX6 无 `6/7`）、`[AF Assist]`（`SELP1650`/`SEL18200LE`/无触点手动头互斥）、Reset 免疫的非对角 `[Circ. of Focus Point]` 与严格双色 `[Focus Frame Color]`（`White`/`Red`，零休眠色），以及 Reset 免疫且 `0 px` HDMI 隔离的 `[Zebra Display]`（`70..100+`、`Custom1/2` `Std+Range`/`Lower Limit`、S-Log3 `41%/61%/94%` IRE vs `Display LUT=On`），同时对 FX6 辟谣执行 fail-closed：**`5-024-458-18` 与 `FX6 appFw.so` 严格单选 `Off / Zebra 1 / Zebra 2`（`0%..109%`），不存在同时开启 `Zebra 1 + Zebra 2`**。
   - **Check Group D + Tier-0（Wave 74 `15` 比例 `[Marker Display]` Clean-HDMI 隔离 & `[Save/Load Settings]` vs `[Camera Set. Memory]` + `16/16 H0 == H3`）**：[`evaluate_p354_check_group_d_marker_saveload_camset_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py#L1916) 校验 Movie/`S&Q` 独占且 Reset 免疫的 15 比例 `[Marker Display]`（`0 px` HDMI 隔离）对比 FX6 `Aspect Mask 0..15` 与 `User Box`（`3..479`/`3..269`/`-476..+476`/`-266..+266`），校验硬锁 `Slot 1` 的 `Setup -> [Reset/Save Settings] -> [Save/Load Settings]`（`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`，零 `PRO/CAMERA`、Ver. `1.xx` 拒绝、`MR` 互斥、`Slot 1` Save/Delete 触发 `EROFS=30`）vs 可选 `Slot 1/2` 的 `[Camera Set. Memory]`（`1..3` NVRAM + `M1..M4` `CAMPR%02d%c.DAT`）对比 FX6 `Project > All File`（`Media(B)` `.ALL` 64 槽位），并实施双介质不同 `st_dev` 的 `528 B FX3RCPT1` 与 `16/16 H0 == H3` 表面不可变校验。

3. **`实测事实`：4 模式 108 项单元测试、CLI 四态、`verify-milestone-349` / `verify-milestone-324` 双模总闸门与 `clean-audit` 全部通过**
   - 新增 [`test_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py) 共 **108 项**单元测试（`>= 100`），在 **4 种模式**（默认 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、无供体 `FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase354_missing` + `work_root=None`）下均实测 **`Ran 108 tests -> OK`**。
   - 双模总闸门 `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-349` 与 `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324`（Makefile 内均已串行覆盖 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 --force-clean-room`）均返回 `status=OK`、`pillars=6/6`、`leaked=0`；`PYTHONDONTWRITEBYTECODE=1 make clean-audit` 输出 `ALL GREEN`（零 `.pyc` 或未跟踪二进制残留）。

4. **`推断`（物理真机边界声明）**
   - 本阶段所有测试均基于宿主机只读契约模型、`os.O_RDONLY` 有界（`<= 64 B`）供体头核验以及确定性模拟回执（`--simulate-bench-dry-run`），尚未在真实物理 `ILME-FX3` 机身上采集双卡 `528 B FX3RCPT1` 实体回执或执行真机 USB/SD 连线操作，因此所有输出均保持 `overall_ready_for_hardware_attach == False`、`hardware_live_attachment_authorized == False`、`persistent_emmc_writes_authorized == False`、`cross_model_flash_authorized == False`；具体台架互锁与 `Slot 1 EROFS=30` 防火墙的实际效果在真机双卡回执到达前属工程安全推断，物理挂接仍需由双介质 `528 B FX3RCPT1` 与独立只读验签放行。

---

## 2. 四态确定性 CLI 实测指纹与 6 文件清单（`实测事实`）

### 2.1 CLI 四态 `report_sha256` 实测表

> 以下四行均于当前工作树通过 `/usr/bin/python3 -B -m fx6_closure preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset ... --json` 实测捕获，且单测断言 `elapsed_seconds` 已从规范化 JSON 与摘要哈希中递归剔除。

| 验证模式（`verification_mode`） | 模拟干跑 | `overall_status` | `go_no_go` | CLI `rc` | 供体读取（`O_RDONLY`） | `raw_firmware_bytes_leaked` | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1/6`（`64 B`） | `0` | `0ce102b3b70427e12dbba735ab23ca1f66bca26a8ffe685c4664e79b4fe53a98` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `1/6`（`64 B`） | `0` | `1bbd8af6088c1e761ee6a8ef96fd4b2bf1035f7a755c7f5532e8c68fb25be47f` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/6`（`0 B`） | `0` | `c43f3f71582780ef2f1eb3fa3b189152a66fd9741574785425181bf83baea378` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/6`（`0 B`） | `0` | `5dc2249540121c49eecc5075841084a5438d8c057c0b251bcf7b9dc240f9dde2` |

### 2.2 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py)（新增，`2,741` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3594-L3757)（新增 Phase 354 `163` 项非遮蔽导入与 `__all__` 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7509)（新增 `preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset` 子命令及全部参数）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L532-L535)（追加 Section `# 64.`）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py)（新增，108 项四模式单元测试，`2,053` 行）
6. [`reports/2026-11-18-phase354-preflight21-lockop-shocklesswb-focusmag-afspeed-zebra-saveload/README.md`](./README.md)（本工程闭合报告）

---

## 3. 可复现验证命令与实测结果（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier.py"
CMD="preflight-lockop-shocklesswb-focusmag-afspeed-zebra-custom-and-saveload-camset"

# 1. 四模式 108 项单元测试（均已实测 Ran 108 tests -> OK）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase354_missing PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v "$TEST"

# 2. CLI 门控实测（rc=0 / rc=2 / rc=0 / rc=2 / rc=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --simulate-bench-dry-run --json

# 3. Milestone 349 & 324 双模总闸门 + 洁净度审计（均已实测 status=OK, pillars=6/6, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-349
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324
PYTHONDONTWRITEBYTECODE=1 make clean-audit
```
