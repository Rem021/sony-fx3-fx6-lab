# Phase 345 里程碑工程报告：`20/20` 第 20 级物理台架准备度预检器（`preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot` / Wave 72）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H429` · **Phase 345 Milestone（`20/20` Physical Bench Preflights Milestone!）**
- **上游情报基线**：[Global Sony Wave 72 报告](../2026-11-18-global-sony-wave72-audio-reclevel-outtiming-touchfunc-pcremote-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` Model `0x91030080` vs `ILME-FX6 Ver. 6.01` `5-024-458-18`）
- **上一级预检模板**：[Phase 342 报告](../2026-11-18-phase342-preflight19-peaking-audio-wind-usbpd-ntscpal-antidust-focusmag-expstd-usbtether/README.md)

---

## 1. 核心结论（结论先行）

1. **`实测事实`：第 20 级物理台架预检器落地并达成 `20/20` 预检里程碑闭环**：
   - 在 `outputs/fx6-on-fx3-closure/` 内新增 [`realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py)（`2,417` 行，Schema `realhw_preflight20_audio_reclevel_outtiming_4ch_touch_remoteshoot_v1`，版本 `phase345_v1`），将主机侧只读物理台架预检链路推至 **`20/20` Milestone**：`Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342 -> Ph345`。
   - 全部公开符号（161 项导入导出符号，模块内共 `192` 个公开属性）已接入 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3384-L3544)，CLI 子命令 `preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot` 及全量选项已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L6214-L7200)，并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L521-L524) 追加第 `# 62.` 节文档。

2. **`实测事实`：Wave 72 Check Groups A–D 契约、四大辟谣边界与 `16/16 H0 == H3` 双介质 Tier-0 门控全部以 fail-closed 模式实现**：
   - **Check Group A（`Shooting -> [Audio Recording] -> [Audio Rec Level]`、常驻机身限幅、`XLR-H1` 硬件接管与 FX6 6 档 `Limiter Mode`）**：[`evaluate_p345_check_group_a_audio_reclevel_and_limiter`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py#L947) 强制校验精确菜单路径 `Shooting -> [Audio Recording] -> [Audio Rec Level]`（`0..31` 32 档，默认 `26` `adj_audio_rec_level_defult`，`Delete` 键归位 `26`，`Can be reset`）、`3.5mm MIC` 强抢占 MI 热靴、机身内置限幅器永久运行（零菜单 `Off` 开关）、`XLR-H1 HANDLE AUDIO=ON` 旁路接管（`LINE` 锁 `+4 dBu`，`MIC/MIC+48V` `ATT 0/10/20 dB = -60/-50/-40 dBu` + `AUTO/MAN(/LINK)` + `0..10` 旋钮）及 `S&Q` `0ch` 4 项互斥锁死；对比 `FX6` `CH1..CH4 Input Select` 矩阵、3 级 Reference（含 5 档 `Reference Level`: `-20dB/-18dB/-16dB/-12dB/EBUL`）及 **6 档 `Limiter Mode`**（`Off / -6dB / -9dB / -12dB / -15dB / -17dB`）。
   - **Check Group B（`[Audio Out Timing]`、耐受 Reset 的 `[Volume Settings]` 与 `[4ch Audio Monitoring]` 精确 5 项 vs FX6 7 项 `Monitor CH` 与零侧键）**：[`evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py#L1155) 校验位于 `Shooting -> [Audio Recording]` 的可 Reset 项 `[Audio Out Timing]`（`Live` 默认 / `Lip Sync`，`S&Q` 禁用）；校验位于 `Setup -> [Sound Option]` 且**耐受 `[Camera Settings Reset]`** 的 `[Volume Settings]`（`0..15` 默认 `7`，防靠近 `XLR-H1` 声反馈啸叫）与 `[4ch Audio Monitoring]`（严格 5 项 `CH1/CH2` [def], `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2`——拦截 `"CH1/CH2 mono mix"` / `CH1+2/CH3+4` / `All` 误区）；对比 `FX6` `Monitor CH` 7 项（含 `MIX ALL`）、`Headphone Out`（`Stereo/Mono`）、`Volume 0..50`（**辟谣侧面 `"MONITOR VOL +/-"` 物理键：`5-024-458-18` 命中 `0`**）与 `SDI OUT` 4ch vs `HDMI` 2ch。
   - **Check Group C（`Setup -> [Touch Operation]` 精确 4 项 vs 100% 休眠 `[Touch Panel/Pad]`/`[Touch Shutter]`/`[Touch AE]` 辟谣）**：[`evaluate_p345_check_group_c_touch_dormant_and_spot_link`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py#L1306) 严格校验 4 个耐受 `[Camera Settings Reset]` 的活跃子项（`[Touch Operation]`、`[Touch Sensitivity]`、`[Touch Func. in Shooting]` 在 Still/Movie/`S&Q` 全一致、`[Swipe Up]`）；对无 EVF `ALCIN_UUD` 上 100% 休眠的 `[Touch Panel/Pad]`、`[Touch Pad (vertical)]`、`[Touch Shutter]`、`[Touch AE]`（`ilc/2210` 均 `0` 命中）返回 `EOPNOTSUPP=95`；校验 `[Spot Metering Point]`（`Center`/`Focus Point Link`）不随追踪框移动；对比 `FX6` `Touch Function in MF`（`Spot Focus`/`Tracking AF` 及手动镜头/变形反挤压/对焦放大互锁）+ Ver. 6.00+ `BIG6` 全触控。
   - **Check Group D（`Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]` `Destination Only` RAM 直传 vs 出厂默认 `Dest.+Camera` `Slot 1 EROFS=30` 防火墙与 `16/16 H0 == H3`）**：[`evaluate_p345_check_group_d_remote_shoot_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py#L1704) 校验 Ver. 2.00..7.02 更名后全部耐受常规复位（仅 `[Reset Network Set.]` 或 `[Initialize]` 还原）的 4 项设置，其中**仅 `Destination Only`**（`stillrec_running_without_pseudo_rec_t`）通过 PTP USB（`/dev/usb/sicd_*`）与 PTP-IP（`TCP 15740`）零写卡直传 RAM；对**出厂默认 `Dest.+Camera`** 与 `Camera Only` 在 `Slot 1` Tier-0 保险库强制施加 `EROFS=30` 防火墙（`slot1_data_sector_writes == 0`、`Airplane Mode=On` 下 `wireless_rf_packets_emitted == 0`、会话中切换 `EBUSY=16`），对比 `FX6` 零 `Still Img. Save Dest.` UI；并强制要求不同 `st_dev` 双介质 `528 B FX3RCPT1` **`16/16 H0 == H3`** 回执门控。

3. **`实测事实`：全量四态验证、CLI 门控、`verify-milestone-324` 双模与 `clean-audit` 全部通过**：
   - 新增 [`test_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py) 共 **105 项**单元测试（`>= 100`），在 **4 种运行模式**（本地供体默认、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、模拟无供体 `FX3_FX6_MAC_WORK_ROOT=/nonexistent/...` + `work_root=None`）下均实测 **`105/105 OK`**（`0` 失败、`0` 错误、`elapsed_seconds` 全量剔除后 4 种 Clean-Room 路径 `report_sha256` 逐位一致）。
   - CLI `preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot`：`--help` 返回 `rc=0`；默认无回执返回 `rc=2`（`BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`）；`--simulate-bench-dry-run` 返回 `rc=0`（`DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0 == H3`）；`--force-clean-room --simulate-bench-dry-run` 返回 `rc=0`（`CLEAN_ROOM_SYNTHETIC`）。
   - 双模总闸门 `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324` 与 `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` 均输出 `status=OK`、`pillars=6/6`、`leaked=0`；`make clean-audit` 输出 `ALL GREEN`（`0` 残留 `.pyc` 与未跟踪二进制文件）。

4. **`推断`（非物理真机实测结论）**：
   - 本报告所有通过项均基于**宿主机只读模型、`os.O_RDONLY` 有限头读取与确定性模拟回执（`--simulate-bench-dry-run`）**；真实 `ILME-FX3` 机身上的 `XLR-H1` 实体切换、`3.5mm` 抢占插拔、`PTP/PTP-IP` 真机抓拍以及物理双卡 `528 B FX3RCPT1` 回执尚未接入实机，因此全链路严格保持 `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`。

---

## 2. 四态确定性报告指纹与交付清单（`实测事实`）

### 2.1 四态 CLI 确定性 `report_sha256` 实测表

> 以下四行均由 `/usr/bin/python3 -B -m fx6_closure preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot ... --json` 实测捕获，并断言 `"elapsed_seconds"` 已从 JSON 序列化输出中递归剔除。

| 验证模式（`verification_mode`） | 模拟开关 | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 返回码 | 供体读取（`O_RDONLY`） | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `3/10`（`192 B`，`0` 泄露） | `99936ae216d428162db606cfcb3f2063b7e817508d38265553a09759739b3eca` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `3/10`（`192 B`，`0` 泄露） | `208e328edd139c6fc5cc68f1233bde04dce65b2c0bf3d70e4289c83bc34506d3` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0/10`（`0 B`，`0` 泄露） | `ec1fe23404c91351a09aa971cb200f20b6542a094b47edeee81419295d28f92e` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0/10`（`0 B`，`0` 泄露） | `a2c28420ef410a4b25d970a57ab5420963680551a3c8508817eba58ba8eb6c83` |

> **说明（`实测事实`）**：在 CLI 默认传参下，`--fx6-lib-dir` 指向存在本地 `FX6` 供体库目录，因此 `fx6_appfw_so`（摘要前缀 `4809d8af884a2ecc`）、`fx6_libinfraptpcontrol_so`（`905a32de81df3f90`）与 `fx6_libinfraremote_so`（`ae3b58da9080e084`）完成 `3 × 64 B = 192 B` 只读 ELF 头核验；其余 7 项位于独立工作目录的 `FX3` 供体路径在未显式指定 `--work-root` 时不强依赖、无报错回退；当显式传入 `--force-clean-room` 或置位 `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` 时，全部 10 项探针统一使用确定性合成头摘要且 `bytes_read_total = 0`、`raw_firmware_bytes_leaked = 0`。

### 2.2 严格 6 文件所有权修改清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py)（新增，`2,417` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3384-L3544)（导出 Phase 345 公共符号）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L6214-L7200)（新增 `preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot` 子命令与参数）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L521-L524)（追加 Section `# 62.`）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py)（新增，105 项四模式单元测试，`1,331` 行）
6. [`reports/2026-11-18-phase345-milestone-preflight20-audio-reclevel-outtiming-4ch-touch-remoteshoot/README.md`](./README.md)（本关闭报告）

---

## 3. Wave 72 Check Group A–D 实测契约与辟谣矩阵（`实测事实`）

| 检查组 | FX3 Ver. 7.02 (`ilc/2210` / `appFw.so` / `_f,_g.uxc`) 核验契约 | Reset / 持久化与错误码门控 | `ILME-FX6 Ver. 6.01` 架构对比与辟谣 |
| :--- | :--- | :--- | :--- |
| **Group A**<br>`[Audio Rec Level]` & `XLR-H1` | 精确路径 `Shooting -> [Audio Recording] -> [Audio Rec Level]`（`_f 0x63b9/0x6f0a`，`0..31` 32 档，默认 `26` `adj_audio_rec_level_defult`，`Delete` 键归位 `26`）；仅控内置立体声麦与机身 `3.5mm MIC`（`3.5mm` 强抢占 MI 靴）；内置限幅器永久开启无 Off 开关；`XLR-H1 HANDLE AUDIO=ON`（且无 `3.5mm`）接管 `UIBIZ_INP_HOTSHOE_XLRMIC` 并灰置 `[Audio Rec Level]`（`LINE +4 dBu`、`MIC/MIC+48V` `ATT 0/10/20 dB = -60/-50/-40 dBu`、`AUTO/MAN(/LINK)`、`0..10` 物理拨盘）；`S&Q` 强锁 `0ch` 与全部 4 个音频项 | **`Can be reset`**（`[Camera Settings Reset]` 复位为 `26`）；越界、错误声源抢占、尝试关内置限幅或声称 `S&Q` 有声均 fail-closed 报错 | `FX6` `CH1..CH4 Input Select` 独立路由矩阵；3 级 Reference（`INPUT1/2 MIC Reference -80..-30dB`、`Line Input Reference +4/0/-3dB/EBUL`、**5 档 `Reference Level`** `-20/-18/-16/-12dB/EBUL`）；**6 档 `Limiter Mode`**（`Off / -6dB / -9dB / -12dB / -15dB / -17dB`，非 4 档） |
| **Group B**<br>`[Audio Out Timing]`, `[Volume Settings]`, `[4ch Audio Monitoring]` | `[Audio Out Timing]` 位于 `Shooting -> [Audio Recording]`（`_f 0x6bc2`：`Live` def `0x753d` / `Lip Sync` `0x6bbc`，`S&Q` 禁用）；`Setup -> [Sound Option] -> [Volume Settings]`（`base 0xe8c9`，`0..15` def `7`，告警靠近 `XLR-H1` 声反馈啸叫）与 `[4ch Audio Monitoring]`（`_f 0x70dd`，精确 **5 项** `CH1/CH2` def、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`，拦截 `"CH1/CH2 mono mix"` / `CH1+2/CH3+4` / `All` 伪选项） | `[Audio Out Timing]` **`Can be reset`**；Setup 下 `[Volume Settings]` 与 `[4ch Audio Monitoring]` **耐受 `[Camera Settings Reset]`**（仅 `[Initialize]` 还原） | `FX6` `Monitor CH` **7 项**（`CH1/CH2/CH3/CH4/CH1/CH2/CH3/CH4/MIX ALL`）、`Headphone Out`（`Stereo/Mono`）、`Volume 0..50`（**辟谣侧面 `"MONITOR VOL +/-"` 实体键：`5-024-458-18` `0` 命中**）；`SDI OUT` 4ch vs `HDMI` 2ch 成对 |
| **Group C**<br>`[Touch Operation]` 4 项 vs 休眠触控辟谣 | `Setup -> [Touch Operation]`（`_g 0x6345` / `base 0xe8e3`）严格 **4 项**：`[Touch Operation]`（`On` def / `On: Playback Only` / `Off`）、`[Touch Sensitivity]`（`Standard` def / `Sensitive`）、`[Touch Func. in Shooting]`（`_f 0x7575`：`Touch Focus` / `Touch Tracking` def / `Off`，**Still / Movie / `S&Q` 完全一致**）与 `[Swipe Up]`（`Open the Fn Menu` def / `Off`）；`[Spot Metering Point]`（`Center`/`Focus Point Link`）锚定初始对焦点，**不随追踪框动态移动** | 全 4 项**耐受 `[Camera Settings Reset]`**；对 100% 休眠符号 `[Touch Panel/Pad]`（`_f 0x76ec`）、`[Touch Pad (vertical)]`（`_f 0x7312`）、`[Touch Shutter]`（`_f 0x6a80`）与 `[Touch AE]`（`_f 0x702a`，`ilc/2210` 均 `0` 命中）统一返回 **`EOPNOTSUPP=95`** | `FX6` `Technical > Touch Operation`、`Shooting > Focus > Touch Function in MF`（`Spot Focus` / `Tracking AF`，手动镜头/`De-Squeeze != Off`/`Focus Magnifier` 锁定 `Spot Focus`）与 Ver. 6.00+ **`BIG6` 主屏及全菜单触控**（`BKID_APP_HOME_SCREEN_STATE`） |
| **Group D**<br>`[Remote Shoot Setting]`, PTP/PTP-IP & `Slot 1` `EROFS=30` | Ver. 2.00..7.02 将 `PC Remote Function` 整合更名为 `Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]`（`_g 0x64c5` / `_f 0x7ba4`）：`[Still Img. Save Dest.]`（`Destination Only` / **`Dest.+Camera` 出厂默认!** / `Camera Only`）、`[Save Image Size]`（`Original` / `2M` def）、`[RAW+J Save Image]`（`JPEG Only` def）、`[RAW+H Save Image]`（`HEIF Only` def）；`libInfraPtpControl.so` USB（`/dev/usb/sicd_*`）与 `libInfraRemote.so` PTP-IP（`TCP 15740`）仅 **`Destination Only`** 走 `stillrec_running_without_pseudo_rec_t` 零写卡 RAM 直传 | 全 4 项**耐受 `[Camera Settings Reset]`**（仅 `[Reset Network Set.]` / `[Initialize]` 还原）；连接态改目标触发 **`EBUSY=16`**；默认 `Dest.+Camera` 或 `Camera Only` 写 `Slot 1` 触发 **`EROFS=30`** 防火墙；零射频 `Airplane Mode=On`（`rf_pkts=0`）；双介质 `528 B FX3RCPT1` **`16/16 H0 == H3`** | `FX6` 采用 `Network Client Mode` & `Camera Remote Control` / *Monitor & Control* / Camera Remote SDK（**UI 零 `Still Img. Save Dest.` 暴露**） |

---

## 4. 只读与安全约束边界（`实测事实` vs `推断`）

- **`实测事实`**：所有代码与单测均强制设置 `PYTHONDONTWRITEBYTECODE=1` / `sys.dont_write_bytecode = True`，供体头读取严格经由 `os.O_RDONLY` 有界读取 64 B 并计入 `raw_firmware_bytes_leaked = 0`。所有报告均硬锁以下不变式并经 `verify_phase345_report()` 与 `test_096..test_105` 校验：
  - `overall_ready_for_hardware_attach == False`
  - `hardware_live_attachment_authorized == False`
  - `persistent_emmc_writes_authorized == False`
  - `cross_model_flash_authorized == False`
  - `slot1_tier0_vault_mutated == False`
  - `emmc_write_count == 0`、`e_nd_actuator_tx_count == 0`、`rf_packets_transmitted == 0`、`wireless_rf_packets_emitted == 0`、`slot1_data_sector_writes == 0`、`usb_packets_transmitted == 0`、`passive_tx_bytes_emitted == 0`、`raw_firmware_bytes_leaked == 0`
- **`推断`**：真机上电连线、`XLR-H1` 实声源压限曲线、PTP-IP 实包吞吐率及真实 SD 卡 `FX3RCPT1` 提取尚未执行，需在物理台架阶段另行采集并由独立只读验签确认。

---

## 5. 可复现全量验证命令与实测记录（`实测事实`）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier.py"
CMD="preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot"

# 1. 四模式 105 项单元测试（已实测全数 Ran 105 tests -> OK）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest -v "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase345_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest -v "$TEST"

# 2. CLI 子命令门控检查（已实测 rc=0 / rc=2 / rc=0 / rc=0）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --summary
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --force-clean-room --simulate-bench-dry-run --summary

# 3. Milestone 324 双模总闸门 + 洁净度审计（已实测 status=OK, pillars=6/6, leaked=0, ALL GREEN）
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324
make clean-audit
```
