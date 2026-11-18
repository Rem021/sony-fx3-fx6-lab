# Phase 342 第 19 级物理台架准备度预检器工程报告（`preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether` / Waves 70–71）

## 1. 核心结论（Conclusion-First）

1. **实测事实：Waves 70–71 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`，Model `0x91030080`）vs `ILME-FX6`（`Ver. 6.01`）物理台架检查组（`Check Group A..D`）全部落地闭环**：
   - 在 `outputs/fx6-on-fx3-closure/` 新增第 19 级宿主机侧只读物理台架与实拍前准备度预检器 [`realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py)（Schema `realhw_preflight19_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether_v1`，版本 `phase342_v1`，CLI 子命令 `preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether`，共 `2,463` 行），将 19 级预检链路推进至 `Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341 -> Ph342`。
   - 全部 `187` 个公共符号已在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L6470) 导出，CLI 子命令与全部参数（含 `argparse` `help=` 字符串 `%%` 转义）已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L6275)（默认 `rc=2` 等待物理 Tier-0 双卡回执，`--simulate-bench-dry-run` `rc=0`），并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L516) 新增 Section `# 61.` 文档条目。

2. **实测事实：Check Groups A–D 关键硬件/固件契约、辟谣护栏、官方错字指纹、Slot-1 `EROFS=30` 与 `16/16 H0 == H3` 门控全部 fail-closed 实现**：
   - **Check Group A（Wave 70 §§1–2：`[Peaking Display]` `0 px` HDMI 与辟谣 FX6 `Peaking Type/Freq` + Ver. 2.00+ 移除 `[Audio Level Display]` 与辟谣 `[Wind Noise Reduct.]` `Auto`）**：[`evaluate_p342_check_group_a_peaking_audio_and_wind`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py#L815) 校验抗 `[Camera Settings Reset]` 的 `Shooting -> [Focus] -> [Peaking Display]`（`0x7615`，`Off/On`、`High/Mid/Low`、`Red/Yellow/Blue/White` 3 项全抗 Reset），无论 `[HDMI Info. Display]` 如何设置**永远向 HDMI 输出 `0` 像素**，可与 `Focus Magnifier` 并存且在 Movie `AF` 下保持可用，拦截机身休眠的 `Focus Map`（`0x61f9`/`0x6247` -> `EOPNOTSUPP=95`，仅无线 *Monitor & Control* 专属），同时**辟谣 FX6 `Peaking Type/Freq` 迷思**（`FX6 appFw.so` `0` 处 `PEAKING_TYPE`/`PEAKING_FREQ` 符号；FX6 仅暴露 `Setting` / `Peaking Level` / `Color` `B&W/Red/Yellow/Blue`）；校验 Ver. 2.00+ **移除独立 `[Audio Level Display]`**（`0x7a36` -> `EOPNOTSUPP=95`）后精确剩余 5 项可 Reset 的 `[Audio Recording]` 菜单（含 `Audio Rec Level` `0..31` 默认 `26` 与索尼原厂 ELF 错字 `adj_audio_rec_level_defult`、`Audio Out Timing` `Live`/`Lip Sync`、不可关闭的机身内置限幅器、`Shoe Audio Set.`），并**辟谣 FX3 `[Wind Noise Reduct.]` `Auto` 迷思**（`0x6f96` 仅 `On/Off` 且仅作用于机内立体声麦克风，在 `3.5mm` / `XLR-H1 HANDLE AUDIO=ON` / `MI Shoe` 外接麦或 `S&Q` 下被旁路/禁用），对比 `FX6` `CH1..CH4 Wind Filter`（手柄无物理 `LOW CUT` 开关）与 6 档 `Limiter Mode`。
   - **Check Group B（Wave 70 §§3–4：`[USB Power Supply]` `9V/3A` `27W+` PD + 强制 `NP-FZ100` 在位律 vs FX6 `19.5V DC IN` + `[NTSC/PAL Selector]` `J1/CE/U2` 与 `Slot 1` `EROFS=30`）**：[`evaluate_p342_check_group_b_usb_pd_and_ntsc_pal`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py#L1069) 校验抗 Reset 的 `[USB Power Supply]`（`0x785b`，仅限 `USB Type-C` 口供电，`Multi/Micro USB` 禁用），强制执行 `libUsbBusPower.so`（`GetCurrentBattState` / `BATTERY_IS_INSERTED`）的**强制 `NP-FZ100` 在位律**（严禁无电池 Type-C PD 启动与热插拔），确认**开机状态零电池充电**（`CHARGE` 橙灯仅关机亮起），校验 `DC-C1` 假电池需 `>= 65W PD + 5A` 线缆，对比 `FX6` `19.5V` EIAJ `DC IN` 无电池启动（但严禁 `REC` 中热插拔断电，且 FX6 `USB-C` 不给机身供电）；同时校验抗 Reset 的 `[NTSC/PAL Selector]`（`0x6b6f`，`lib::backup_get_ntsc_pal_selector_dst`）：`J1` 锁定 `NTSC`（`EOPNOTSUPP=95`）、`CE/E33` 切 `NTSC` 弹窗 `"Running on NTSC."`（`0xe77a`）、`U2` 切 `PAL` 弹窗 `"Running on PAL."`（`0xe0b6`），切换触发冷重启且 Ver. 7.02 纯 XAVC 不强制格式化，仅对 `AVF_INFO` 提示 `Create?`/`Update?`（在物理 `Slot 1` Tier-0 保险库上强制返回 **`EROFS=30`**），对比 `FX6 System Frequency`（6 频点与 `Thumbnail` 按制式过滤片库隐患）。
   - **Check Group C（Wave 71 §§1–2：休眠 `[Anti-Dust Function]` / `[Shutter When Pwr OFF]` 辟谣 + `[Sensor Cleaning]` vs FX6 密封 `e-ND` + `APR` & 抗 Reset `[Focus Assistant]`）**：[`evaluate_p342_check_group_c_antidust_and_focus_assistant`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py#L1273) 拦截 100% 休眠的 `[Anti-Dust Function]`（`0x7495`）与 `[Shutter When Pwr OFF]`（`0x709f`，`BKID_APP_setting_image_sensor_barrier` 在 `ALCIN_UUD` 上被屏蔽、`ilc/2210` `0` 次命中 -> `EOPNOTSUPP=95`），确认 FX3 机械帘幕关机**保持 `OPEN`**，唯一可用清灰入口为 `Setup -> [Setup Option] -> [Sensor Cleaning]`（`0x67d6`，需 `>= 51%` 电量 + IBIS 抖尘 + 强制关机），对比 `FX6` 密封 `1/4..1/128 + CLEAR` `e-ND` + IR-cut 光学舱与 `Technical > APR`；校验全 5 项均抗 Reset 的 `[Focus Assistant]`：`[Focus Magnif. Time]`（`2s/5s/No Limit`）、精确倍率循环（**FF `x1.0 -> x2.1 -> x4.1`**、**APS-C `x1.0 -> x1.5 -> x3.0`**、**Movie `x1.0 <-> x4.0`**，拦截休眠高像素倍率 `EOPNOTSUPP=95`）、Still 专属 `[AF in Focus Mag.]` 与 `[Auto Magnifier in MF]`（Movie 下不可用）、**Movie `REC` 期间保持放大且对 Clean-HDMI 与内录画面零裁切**，对比 `FX6` `x3/x6` VF 与 Ver. 6.0+ `x2/x4` HDMI `Focus Magnifier`。
   - **Check Group D（Wave 71 §§3–4 & Tier-0 `H0 == H3`：`[Exposure Std. Adjust]` 标定陷阱 + 辟谣 FX6 `±2.0` 迷思 + 有线 `[USB-LAN/Tethering]` + `Slot 1` 只读防火墙）**：[`evaluate_p342_check_group_d_exp_std_usblan_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py#L1479) 校验抗 Reset 校准陷阱 **`[Exposure Std. Adjust]`**（`0x6f71`，全 5 种测光模式均支持 `-1..+1 EV` `1/6 EV` 13 档步进，`EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6`；`1/8 EV` 休眠），只偏移 `M.M.` 零点而**不修改 EXIF `ExposureBiasValue`**（非零触发告警图标 `0xe567`，台架默认要求 `0 EV` 除非显式确认），并**辟谣 FX6 `±2.0` 迷思**（`FX6 Auto Exposure > Level` 实为 **`-3.0..+3.0`、`0.25` 步进共 25 档** + 每条 LUT `AE Level Offset`）；校验有线智能手机 **`[USB-LAN/Tethering]`**（`0x7d2a`，`libNetServiceTethering.so` + `libTetheringResource.so` + `cdc_ncm/cdc_ether/rndis_host/ipheth.ko`）在 **`[Airplane Mode]=On` 零射频（`wireless_rf_packets_emitted = 0`）** 下驱动 `RTMP/RTMPS/SRT` 与 `FTP`，禁止 `USB Type-C` 与 `Multi` 双口并插，提示 `[Reset Network Set.]` 自动重启风险，拦截休眠 `USB Streaming` UVC，并强制 `usbgmscif_setReadOnly` + **`EROFS=30`** 阻止 `MTP`/`MSC` 宿主机写入 `Slot 1`，校验 FX3 移除 `CUsbGadgetIAP`（`0` 命中）vs FX6 `usbg_iap.ko`，最后叠加双介质 `528 B FX3RCPT1`（不同 `st_dev`）**`16/16 H0 == H3`** 与 `emmc_write_count = 0` 门控。

3. **实测事实：CI 规则（递归剔除 `elapsed_seconds`、`work_root=None` 安全回退、4 模式 100 项单测、Milestone 324 双模与洁净度审计）全绿**：
   - `to_deterministic_json()` 与 `_canonical_sha256_dict()` 递归剔除全部 `elapsed_seconds` / `*_elapsed*` 计时键；`resolve_phase342_donor_file_or_none(None, ...)` 与不存在的 `work_root` 均无报错回退 `CLEAN_ROOM_SYNTHETIC`（`0 B` 读取、`0` 固件字节泄漏）。
   - 新增 [`test_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py) 共 **100** 项单测（`>= 96`），在默认本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与无供体回退（`FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase342_missing` + `work_root=None`）4 种模式下全部 **100/100 OK**。
   - CLI `--help` 退出码 **`0`**（确认全部 `%%` 正确转义，含 `51%%`、`100%%` 等）；默认未提供物理 Tier-0 回执返回 **`rc=2`**（`BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`）；`--simulate-bench-dry-run` 返回 **`rc=0`**（`DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0 == H3`）。
   - `make verify-milestone-324`（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模）与 `make clean-audit` 实测全部通过（具体输出摘要见 §2.1 与 §4）。

4. **推断（非实测物理真机结论）**：
   - 以上 100 项单测、四态 CLI 指纹及 `--simulate-bench-dry-run` 仅证明宿主机只读模型、供体头检查与确定性 SHA-256 门控在离线与模拟回执条件下成立；真实 `ILME-FX3` 机台菜单交互、物理 HDMI/PD/USB-LAN 连线与 Tier-0 物理双卡 `528 B FX3RCPT1` 校验仍待后续离线物理台架实测补齐（当前 `overall_ready_for_hardware_attach = False`、`emmc_write_count = 0`、`slot1_data_sector_writes = 0`）。

---

## 2. 四态确定性报告指纹与实测命令回执

### 2.1 四态确定性 `report_sha256`（实测事实）

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | `O_RDONLY` 供体读取 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `512 B` (`0.824 ms`) | `c28a0ed54b102a739d7a197dcaf5caadb4e8db914693e07bd6b0383da89e8dc2` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `512 B` (`0.943 ms`) | `7b429404ca16b14def9506e03c8669fd72c95fa340068aac8d567b5587be67cb` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0 B` (`0.002 ms`) | `163f2795f8f8e68eb5d00f98847aa44b6846c859db81cb636d18aa066da2263f` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0 B` (`0.001 ms`) | `f4f72b5922ea82c084a6e0bf9ca096a0932952f341b7ab4cf95032505c3c2434` |

### 2.2 本次交付与修改文件清单（严格 6 文件所有权）

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py)（新增，`2,463` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L6470)（导出全部 `187` 个 Phase 342 公共符号）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L6275)（接入 `preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether` CLI 子命令与参数解析）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L516)（新增 Section `# 61.`）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py)（新增，100 项四模式单测，`1,403` 行）
6. [`reports/2026-11-18-phase342-preflight19-peaking-audio-wind-usbpd-ntscpal-antidust-focusmag-expstd-usbtether/README.md`](./README.md)（本报告）

### 2.3 受限只读供体检查清单（8 项 × 64 B = `512 B`）

| 序号 | 标签 | 相对路径（相对于本地 `work_root`） | 用途与读取方式 |
| :---: | :--- | :--- | :--- |
| 1 | `fx6_appfw_so` | `fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so` | `O_RDONLY` 前 `64 B` ELF 头与 SHA-256 校验 |
| 2 | `fx3_im_elf` | `sony-firmware-20261024/stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/bin/im.elf` | `O_RDONLY` 前 `64 B` 头校验 |
| 3 | `fx3_libjiritsu_so` | `sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so` | `O_RDONLY` 前 `64 B` 头校验 |
| 4 | `fx3_libusbbuspower_so` | `fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so` | `O_RDONLY` 前 `64 B` 头校验 |
| 5 | `fx3_libnetservicetethering_so` | `fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libNetServiceTethering.so` | `O_RDONLY` 前 `64 B` 头校验 |
| 6 | `fx3_libtetheringresource_so` | `fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libTetheringResource.so` | `O_RDONLY` 前 `64 B` 头校验 |
| 7 | `fx3_libinfrausbcmn_so` | `fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraUsbCmn.so` | `O_RDONLY` 前 `64 B` 头校验 |
| 8 | `fx3_upm_ko` | `fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko` | `O_RDONLY` 前 `64 B` 内核模块 ELF 头校验 |

> **说明**：所有 `64 B` 头读取均经由 `os.O_RDONLY` 完成，不导出任何原始固件字节（`PHASE342_RAW_FIRMWARE_BYTES_LEAKED = 0`）；无本地供体环境或设置 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root=None` 时安全退化为 `CLEAN_ROOM_SYNTHETIC`（`0 B` 读取）。

---

## 3. Check Group A–D 技术核查矩阵（Waves 70–71）

| 检查组 | 对应 Wave | FX3 Ver. 7.02 (`ilc/2210`) 关键事实与台架门控 | FX6 Ver. 6.01 对比与辟谣护栏 | Reset 行为 |
| :--- | :---: | :--- | :--- | :--- |
| **Group A.1** `[Peaking Display]` | Wave 70 §1 | `0x7615` (`Off/On`, `High/Mid/Low`, `Red/Yellow/Blue/White`)；**永远 `0 px` HDMI 输出**；可与 `Focus Magnifier` 并存；Movie `AF` 可用；机身 `Focus Map` (`0x61f9`/`0x6247`) 休眠 `EOPNOTSUPP=95`（仅无线 *Monitor & Control*） | **辟谣 `FX6 Peaking Type/Freq` 迷思**：`FX6 appFw.so` `0` 命中，仅 `Setting`/`Peaking Level`/`Color` (`B&W/Red/Yellow/Blue`) | **抗 Reset**（3 项全免疫） |
| **Group A.2** `[Audio Recording]` / `[Wind Noise Reduct.]` | Wave 70 §2 | Ver. 2.00+ **移除 `[Audio Level Display]`**（`0x7a36` -> `EOPNOTSUPP=95`）；保留精确 5 项；`Audio Rec Level` `0..31` 默认 `26`（`adj_audio_rec_level_defult`）；内置限幅器不可关闭；**辟谣 `[Wind Noise Reduct.]` `Auto`**（`0x6f96` 仅 `On/Off`，且仅作用于机内麦，外接 `3.5mm`/`XLR-H1`/`MI Shoe` 及 `S&Q` 旁路/禁用） | `FX6` `CH1..CH4 Wind Filter`（智能手柄无物理 `LOW CUT` 开关）+ **6 档** `Limiter Mode` + `Audio Level Meter` UXC | **可 Reset**（5 项全复位） |
| **Group B.1** `[USB Power Supply]` | Wave 70 §3 | `0x785b`；`USB Type-C` `9V/3A` (`27W+`) PD；**强制 `NP-FZ100` 在位律**（`libUsbBusPower.so` `GetCurrentBattState`/`BATTERY_IS_INSERTED`，无电池或热拔立即报错）；开机 `ON` **零电池充电**；`DC-C1` 需 `>= 65W PD + 5A` 线 | `FX6` 支持 `19.5V` EIAJ `DC IN` 无电池启动（但严禁 `REC` 中热插拔）；`FX6 USB-C` 不给机身供电 | **抗 Reset** |
| **Group B.2** `[NTSC/PAL Selector]` | Wave 70 §4 | `0x6b6f` (`lib::backup_get_ntsc_pal_selector_dst`)：`J1` 锁 `NTSC`（`EOPNOTSUPP=95`）；`CE/E33` -> `"Running on NTSC."` (`0xe77a`)；`U2` -> `"Running on PAL."` (`0xe0b6`)；强制冷重启、Ver. 7.02 纯 XAVC 无需格卡；`AVF_INFO Create?` 在 `Slot 1` Tier-0 保险库触发 **`EROFS=30`** | `FX6 System Frequency`（6 频点，`Thumbnail` 按制式过滤短片列表风险） | **抗 Reset** |
| **Group C.1** 休眠 `[Anti-Dust]` / `[Shutter When Pwr OFF]` | Wave 71 §1 | `0x7495` / `0x709f` (`BKID_APP_setting_image_sensor_barrier`) 被 `ALCIN_UUD` 屏蔽，`ilc/2210` **`0` 命中** -> `EOPNOTSUPP=95`；机械帘幕关机**保持 `OPEN`**；仅剩 `[Sensor Cleaning]`（`0x67d6`，`>= 51%` + IBIS 抖尘 + 强制关机） | `FX6` 无机械快门与机内抖尘，采用密封 `1/4..1/128 + CLEAR` `e-ND` + IR-cut 光学舱与 `Technical > APR` | `[Sensor Cleaning]` 为一次性动作 |
| **Group C.2** `[Focus Assistant]` | Wave 71 §2 | 精确 5 项全**抗 Reset**；`2s/5s/No Limit`；**FF `x1.0->x2.1->x4.1`、APS-C `x1.0->x1.5->x3.0`、Movie `x1.0<->x4.0`**；`AF in Focus Mag.` 与 `Auto Magnifier in MF` **仅限 Still**；Movie `REC` 中保持放大，且 Clean-HDMI 与内录 `0` 裁切 | `FX6` VF `x3/x6`（及 Ver. 6.0+ HDMI `x2/x4` `Focus Magnifier`） | **抗 Reset**（全 5 项免疫） |
| **Group D.1** `[Exposure Std. Adjust]` | Wave 71 §3 | `0x6f71`；全 5 种测光模式均支持 **`-1..+1 EV`（`1/6 EV` 13 档**，`EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6`）；偏移 `M.M.` 零点而**不改变 EXIF `ExposureBiasValue`**；台架强制 `0 EV` 除非显式确认标定陷阱 | **辟谣 `FX6 ±2.0` 迷思**：`FX6 Auto Exposure > Level` 实为 **`-3.0..+3.0`（`0.25` 步进、25 档）** + 每条 LUT `AE Level Offset` | **抗 Reset**（操作员标定陷阱！） |
| **Group D.2** `[USB-LAN/Tethering]` & Tier-0 | Wave 71 §4 | `0x7d2a`（`libNetServiceTethering.so` + `cdc_ncm/cdc_ether/rndis_host/ipheth.ko`）在 **`[Airplane Mode]=On` 零射频**下驱动 `RTMP/RTMPS/SRT/FTP`；禁止 `Type-C + Multi` 并插；警示 `[Reset Network Set.]` 自动重启；拦截休眠 `USB Streaming`；`usbgmscif_setReadOnly` + `EROFS=30` 阻断 `MTP`/`MSC` 写 `Slot 1`；`16/16 H0 == H3` + `emmc_write_count = 0` | `FX6` `usbg_iap.ko` `CUsbGadgetIAP`（FX3 上 `0` 命中已剥离） | `[Reset Network Set.]` 复位网络配置并触发自动重启 |

---

## 4. 可复现全量验证命令（实测记录）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier.py"
CMD="preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether"

# 1. 四模式 100 项单元测试（均需 100/100 OK）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase342_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m unittest "$TEST"

# 2. CLI 子命令门控检查
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m fx6_closure "$CMD" --help                      # expect rc=0
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m fx6_closure "$CMD" --summary                   # expect rc=2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -m fx6_closure "$CMD" --simulate-bench-dry-run --summary  # expect rc=0

# 3. Milestone 324 双模全量总闸门 + 洁净度审计
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324
make clean-audit
```
