# Phase 374 工程闭合报告：`25/25` 里程碑第 25 级物理台架准备度预检器（`preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format` / `preflight-phase374`，Global Sony Waves 81–82）

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H474` · **Milestone Phase 374（`25/25` Physical Bench Readiness Verifiers）**
- **上游实证情报基线**：
  - [Global Sony Wave 81 实证情报报告](../2026-11-18-global-sony-wave81-silentmode-target2-dro-autohdr-fanctrl-hoursmeter-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`：`[Silent Mode Settings] -> [Target Function Settings]` 精确 2 项且 3 项全 `Can be reset` vs 抗 Reset 顶层 `Setup -> [Auto Pixel Mapping]` 与 100% 休眠 `[Shutter When Pwr OFF]`/`[Anti-dust Function]`、`[D-Range Optimizer]` 被出厂默认 `PP11`/Log/HLG 锁 `Off` 与零 `Auto HDR`/零 `Multi Frame NR` vs FX6 `Custom`-only `Paint/Look` `Black` & `Knee`、`G85` 勘误 2 项抗 Reset `[Audio signals]` `On`/`Off`、`G82` 勘误 4 档抗 Reset `[Fan Control]` vs FX6 3 档 `Fan Control` + `Alarm Level` `0..7`、`[Version]` `/BODYDATA.DAT` & `LENSDATA.DAT`/UUD 严格 `NO-GO`、`[Certification Logo]` 区域门控，以及 FX6 `Hours(System)` 永久不可清零 vs `Hours(Reset)`）
  - [Global Sony Wave 82 实证情报报告](../2026-11-18-global-sony-wave82-afilluminator-shuttertype-efcs-flash-longexpnr-format-intel/README.md)（`ILME-FX3` 前面板实体 `AF Illuminator` LED `0.3–3.0 m` Still-only 且不被 `Silent Mode=On` 禁用、`Focus -> [AF/MF]` 3 项抗 Reset Still 控件 vs FX6 零辅助灯/`Push AF Mode`、`[Shutter Type]` 精确 2 项无 `Auto` + `1/8000 s` + 机械专属 `BULB`、抗 Reset `[e-Front Curtain Shut.]` `BKID_APP_setting_front_curtaion_shutter` 与散景截断/第三方镜头指引 vs FX6 无机械帘幕 `ECS`、`G156` 勘误严格 `1/250 s` 机械闪光同步上限 `<250 V` 正极性/零 PC 同步/`[External Flash Set.]` `0` 机身 `BKID` 排除 `CAMSET*.DAT`/零 `[Reg. Flash Shooting Set.]`、`[Long Exposure NR]` 与精确 3 档 `[High ISO NR]` 绝不改写 `.ARW`，以及 `[Format]` `Quick Format` `:/AVF_INFO` vs `Full Format` `fsysDepMCmn_EraseDataFull` SD/NVMe 不可逆擦除对 `Slot 1` 强制 `EROFS=30`）
- **前序模板基线**：
  - [Phase 371 工程闭合报告](../2026-11-18-phase371-preflight24-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-ble-shotmark/README.md)（第 24 级预检器模板）
  - [Grand Milestone Phase 364 闭合报告](../2026-11-18-phase364-grand-milestone-364-master-gate/README.md)（6 支柱总闸门基线）

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 25 级物理台架预检器严格在 6 文件所有权范围内落地，将 `fx6_closure` 只读物理台架预检体系推进至 `25/25` 里程碑**
   - 新增 [`realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py)（`2,833` 行，Schema `realhw_preflight25_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_format_v1`，版本 `phase374_v1`），成为只读物理台架预检器链路的 **第 25 级（`25/25` 里程碑）**（`Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342 -> Ph345 -> Ph354 -> Ph358 -> Ph368 -> Ph371 -> Ph374`）。
   - 全部 `149` 项公共符号已以非遮蔽方式接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L4341-L4491) 与 `__all__`（[#L8718-L8866](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L8718-L8866)，AST 查重 `DUPLICATES_IMP: []`、`DUPLICATES_ALL: []`，全包导入 `4,336` 项 / `__all__` `4,334` 项零回归）；CLI 主命令 `preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format` 与短别名 `preflight-phase374` 已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7962-L7974)（处理入口 [#L7593](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7593)、参数定义 [#L9385](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L9385)、分派 [#L12351-L12355](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L12351-L12355)，`help=` 中 `%` 已全部转义为 `%%` 且 `--help` 实测返回 `rc=0`），长命令与短别名在干跑模式下生成 **字节级一致的 `report_sha256`**；并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L558-L561) 追加第 `# 69.` 节。

2. **`实测事实`：Waves 81–82 全部实证勘误已建模为 Check Groups A–D 并与 `16/16 H0 == H3` 双介质 `528 B FX3RCPT1` Tier-0 门控闭环**
   - **Check Group A（Wave 81.1–81.2：`[Silent Mode Settings]` 精确 2 项 `[Target Function Settings]` & `[D-Range Optimizer]` vs 休眠 `[Auto HDR]` / FX6 `Paint/Look`）**：[`evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py#L1225) 强制 `[Target Function Settings]` 仅暴露 `[Aperture Drive in AF]`（`Standard`/`Silent Priority`/`Not Target`）+ `[Auto Pixel Mapping]`（`Off`/`Not Target`），100% 阻断休眠 `[Shutter When Pwr OFF]`（`image_sensor_barrier`）与 `[Anti-dust Function]`（`EOPNOTSUPP=95`）；校验 Silent Mode 下 3 项全属 `Can be reset`（仅顶层 `Setup -> [Auto Pixel Mapping]` 抗 Camera Reset）及 5 项硬禁用互锁；校验 `[D-Range Optimizer]` 被开箱默认 `PP11` / `[Log Shooting] != Off` / `[HLG Still Image] = On` 锁定为 `Off`，且零 `Auto HDR` / 零 `Multi Frame NR`（`0` ELF 命中），对比 FX6 无机械快门电子卷帘架构及 `Custom`-only `Paint/Look` `Black` & `Knee`（零 UI `Black Gamma` / `White Clip`）。
   - **Check Group B（Wave 81.3–81.4：`G85` 2 项 `[Audio signals]`、`G82` 4 档 `[Fan Control]`、`[Version]`/`LENSDATA.DAT` `NO-GO` 与 FX6 `[Hours Meter]`）**：[`evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py#L1470) 落地 Wave 81 `G85` 勘误（FX3 `[Audio signals]` 仅暴露抗 Camera Reset 的 `On`/`Off`，拒绝休眠 `On: all`/`On: shutter only`/`On: e-shutter only`）与 `G82` 勘误（FX3 `[Fan Control]` 精确 4 档抗 Camera Reset `Auto`/`Minimum`/`Off in Rec`/`Always Off`，零 `Auto1`/`Auto2`）对比 FX6 精确 3 档 `Fan Control`（零 `Max`、零 UI `Always Off`）+ `Alarm Level` `0..7`；对 `/BODYDATA.DAT`、`LENSDATA.DAT`、USB UUD 镜头升级及 FX6 Slot B Version Up 全量实施 **`NO-GO / BLOCKED`**（`Slot 1 EROFS=30`）；校验 `[Certification Logo]` 区域门控及 FX6 `Hours(System)`（抗 `Hours Meter > Reset` 与 `All Reset` 永久存活、排除 ALL 文件）vs `Hours(Reset)`（对比 FX3 UI 零暴露）。
   - **Check Group C（Wave 82.1–82.2：前面板实体 `AF Illuminator` LED、3 项抗 Reset Still AF 控件、精确 2 项 `[Shutter Type]` 与抗 Reset `[e-Front Curtain Shut.]`）**：[`evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py#L1687) 校验 FX3 实体 `AF Illuminator` LED（`0.3–3.0 m`、`Can be reset`、Still-only、**不被 `[Silent Mode] = On` 禁用**，在 Movie/S&Q/AF-C/移动 AF-A/Focus Mag/转接环下禁用）；校验 `Focus -> [AF/MF]` 3 项 Still-only 控件（`[Aperture Drive in AF]`、`[AF w/ Shutter]`、`[Pre-AF]`）全抗 `[Camera Settings Reset]`（与 Silent Mode 同名子项形成显式 Reset 对照）对比 FX6 `Push AF Mode`；校验 `[Shutter Type]` 精确 2 项（`Mechanical Shutter`/`Electronic Shutter`，**零 `Auto`**，`Can be reset`，`1/8000 s` 上限，`BULB` 机械专属）与抗 Camera Reset 的 `[e-Front Curtain Shut.]`（原厂 ELF 拼写 `BKID_APP_setting_front_curtaion_shutter` + 高速大光圈散景截断/第三方镜头关闭指引）对比 FX6 无机械帘幕 `ECS`。
   - **Check Group D + Tier-0（Wave 82.3–82.4 + `16/16 H0 == H3`：`G156` `1/250 s` MI 热靴闪光、`[External Flash Set.]`、`[Long Exposure NR]`/`[High ISO NR]`、`[Format]` `Slot 1 EROFS=30` 与双介质回执）**：[`evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py#L1934) 与 [`_extract_tier0_evidence`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py#L643) 强制 FX3 机械闪光同步天花板严格为 `1/250 s`（Wave 82 `G156` 勘误：零 `1/320 s` APS-C、零 `1/160 s`/`1/200 s` EFCS 降档、电子快门/静音模式 100% 锁死、HSS `>1/250 s` 与 `>1/4000 s` 条纹告警、`<250 V` 正极性、零 PC 同步端子），校验抗 Reset `[Exp.comp.set]`、`[External Flash Set.]` `0` 机身 `BKID`（抗 Reset 且排除 `CAMSET*.DAT`）及零 `[Reg. Flash Shooting Set.]`（`EOPNOTSUPP=95`）对比 FX6 零引闪同步 + `Flash Band Reduce`；校验 `[Long Exposure NR]`（`>=1 s`/BULB，电子快门/连拍/连拍包围禁用）与精确 3 档 `[High ISO NR]`（`Normal`/`Low`/`Off`，零 `High`，绝不改写 `.ARW`）；校验 `[Format]` `Quick Format`（`libmpr.so` `:/AVF_INFO`）与 `Full Format`（`fsysDepMCmn_EraseDataFull`，SD `EraseBlock`/`DISCARD` 与 CFexpress `NVME_FORMAT`/`DISCARD`，中途取消仍不可逆）对任何指向 **`Slot 1`** 的操作一律强制 **`EROFS=30`**（`slot1_data_sector_writes == 0`），并强制双介质（不同 `st_dev`）`528 B FX3RCPT1` 与 `16/16 H0 == H3` 验签。

3. **`实测事实`：4 模式 `116` 项单元测试、双模 `verify-milestone-364` 与 `clean-audit` 实测全数通过**
   - **Phase 374 四模式 `116` 项单元测试**：[`test_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py)（`1,654` 行，`116` 项测试，`>= 108` 要求，子进程统一 `timeout=60`）在 **4 种环境模式** 下全部实测 **`Ran 116 tests -> OK`**（`464/464` 全绿）：
     1. Normal（默认 `LOCAL_DONOR_O_RDONLY`，清除 clean-room 环境变量）：`Ran 116 tests in 79.321s -> OK`；
     2. `FX3_CLEAN_ROOM_TEST=1`：`Ran 116 tests in 79.328s -> OK`；
     3. `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 116 tests in 79.227s -> OK`；
     4. 无供体模式（`FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase374_missing`，且测试内含显式 mock `_resolve_work_root_or_none -> None` 与 `work_root=Path("/nonexistent/phase374_missing")` 用例）：`Ran 116 tests in 78.359s -> OK`。
   - **Grand Milestone Phase 364 双模总闸门**：
     - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364` 双模式（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` `CLEAN_ROOM_SYNTHETIC`）均实测返回 **`status=OK`**、`pillars=6/6`、`gate156=155/158`、`recovery=67/67`、`cnflasha_ro=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`auditors=45/45`、`vm_stages=84/84`、`preflights=22/22`、`h0_eq_h3=16/16`、`qemu=50/50(150/150)`、`pngs=100/100(max=27467B)`、`leaked=0`、`ready_attach=False`（`milestone364_sha256` 分别为 `ade9b83849726f0a...` 与 `4d546da45c79d2f2...`）。
   - **洁净度审计**：见提交前最后一次 `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 实测（零 `.pyc` / 二进制污染）。

4. **`推断`（未执行物理真机边界声明）**
   - 本阶段全部验证均基于宿主机只读契约模型、`os.O_RDONLY` 有界（`<= 64 B`）供体头核验以及确定性模拟回执（`--simulate-bench-dry-run`），尚未在真实物理 `ILME-FX3` 机身上采集双介质 `528 B FX3RCPT1` 实体回执或执行真机 USB/SD/MI 热靴/格式化/固件升级操作，因此所有报告输出均硬锁定 `overall_ready_for_hardware_attach == False`、`live_attach_authorized == False`、`hardware_live_attachment_authorized == False`、`emmc_writes_authorized == False`、`persistent_emmc_writes_authorized == False`、`cross_model_flash_authorized == False`、`lens_or_body_dat_update_authorized == False`；物理台架联机前仍须以真实双介质 `528 B FX3RCPT1` 验签放行。

---

## 2. 四态确定性 CLI 实测指纹与 6 文件清单（`实测事实`）

### 2.1 CLI 四态 `report_sha256` 实测表

> 以下四态均于当前工作树通过 `/usr/bin/python3 -B -m fx6_closure preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format ... --json` 与短别名 `preflight-phase374` 实测捕获，长命令与短别名在 `LOCAL_DONOR_O_RDONLY` 干跑（`9f1fd20c...`）及 `CLEAN_ROOM_SYNTHETIC` 干跑（`d5279542...`）下均生成 **字节级一致的 `report_sha256`**。

| 验证模式（`verification_mode`） | 模拟干跑 | `overall_status` | `go_no_go` | CLI `rc` | 供体读取（`O_RDONLY`） | `raw_firmware_bytes_leaked` | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `1/11`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `2ffc7318161edfbd00a23c9e46da857cfbd4470c54d902402ec21ae140b5827c` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `1/11`（`64 B`，`fx6_appfw_so=4809d8af884a2ecc`） | `0` | `9f1fd20c3fa4b01ecdc14077f9b9acb12ddb5b44aad3b3f477e25f6808758647` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/11`（`0 B`） | `0` | `85c3e49d34cf60d976f583dca59a357fbba1d526f5555e2278aaa72aa66bff1c` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/11`（`0 B`） | `0` | `d527954201a0e0f7b2cdda02445674fec4b17357d161d5ffdbf74431d7bcfea4` |

### 2.2 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py)（新增，`2,833` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L4341-L4491)（新增 Phase 374 `149` 项非遮蔽导入与 `__all__` 导出 [#L8718-L8866](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L8718-L8866)）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L7962-L7974)（新增 `preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format` 主命令及 `preflight-phase374` 短别名、全量参数 [#L9385](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L9385) 与分派 [#L12351-L12355](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L12351-L12355)）
4. [`outputs/fx6-on-fx3-closure/tests/test_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py)（新增，`116` 项 4 模式单元测试，`1,654` 行）
5. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L558-L561)（追加 Section `# 69.`）
6. [`reports/2026-11-21-phase374-preflight25-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-format/README.md`](./README.md)（本工程闭合报告）

---

## 3. 可复现验证命令与实测结果（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py"
CMD="preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format"

# 1. 四模式 116 项单元测试（均已实测 Ran 116 tests -> OK）
env -u FX3_CLEAN_ROOM_TEST -u FX3_FX6_FORCE_CLEAN_ROOM -u FX3_FX6_MAC_WORK_ROOT PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase374_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"

# 2. CLI 门控与别名一致性实测（rc=0 / rc=2 / rc=0 / rc=0 / rc=2 / rc=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase374 --simulate-bench-dry-run --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --json
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure preflight-phase374 --force-clean-room --simulate-bench-dry-run --json

# 3. Milestone 364 双模总闸门与洁净度审计（均已实测 status=OK, pillars=6/6, auditors=45/45, preflights=22/22, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364
PYTHONDONTWRITEBYTECODE=1 make clean-audit
```
