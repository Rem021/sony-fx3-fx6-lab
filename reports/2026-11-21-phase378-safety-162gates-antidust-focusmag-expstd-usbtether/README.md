# Phase 378（`Task H480`，Wave-71，`162/162` 硬件安全门禁）：`[Anti-Dust Function]` / `[Shutter When Pwr OFF]` 休眠常开快门与 `[Sensor Cleaning]` `>=51%` + `[Focus Magnifier]` 全链路与 Clean-HDMI 隔离（`G161`），及 `[Exposure Std. Adjust]` 5 模式抗复位隐藏偏移 + 有线智能手机 USB 网络共享零射频与 `Slot 1` `EROFS=30` 防火墙（`G162`）

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H480` · **Phase 378（`162/162` 硬件安全门禁）**
- **核心结论（`实测事实`）**：
  1. 已交付门禁 **`G161`**（[`verify_antidust_focusmag_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/fx3_safety/realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.py)）与 **`G162`**（[`verify_expstd_usbtether_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/fx3_safety/realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.py)）及统一预检引擎 **`verify-162-gates`**（[`evaluate_162gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/fx3_safety/realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.py) / `verify_real_hardware_162gate_readiness`）。
  2. 离线默认模式实测通过 **`159/162`** 项门禁（`VERIFIED_159_OF_162_AWAITING_PHYSICAL_TIER0`，因 Tier-0 物理台架收据 `G10..G12` 未连机而 fail-closed，`overall_ready_for_hardware_attach = False`）；`--simulate-bench-dry-run --force-clean-room` 模拟干跑模式通过 **`162/162`** 项（`VERIFIED_ALL_162_GATES_DRY_RUN_SIMULATED_BACKUP`），所有物理写盘/跨机型刷机/实时连机红线恒锁 `False` 与 `0`（`raw_firmware_bytes_leaked = 0`、`usb_packets_transmitted = 0`、`cross_model_flash_authorized = False`）。
  3. 4 模式 162 门禁单元测试（`109/109` × 4：`34.46s` / `35.21s` / `34.83s` / `32.57s`）、全量 `outputs/fx3-safety/tests`（`83` 个测试文件共 `5,038/5,038` 项测试，Normal 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模均 `0` 失败）、双模 `make verify-milestone-364`（自动发现 `gate156=159/162`、`leaked=0`）及 `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 全部通过（`ALL GREEN`，零 `.pyc`）。
- **Wave-71 实证基线**：[Wave-71 调研报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/reports/2026-11-17-global-sony-wave71-antidust-shutter-pwroff-focus-mag-expstd-usb-tether-intel/README.md)
- **硬件安全态势**：对 `24` 个本地 donor 构件（含 `FX3 appFw.so` `31` 个有界切片、`libNetServiceTethering.so`、`libTetheringResource.so`、`libInfraUsbCmn.so`、`libUsbControl.so`、`cdc_ncm.ko`/`rndis_host.ko`/`ipheth.ko`、4 语种 UXC 与 `FX6 appFw.so` `14` 个切片 / `libInfraUsbCmn.so`）严格执行只读 `os.open(..., os.O_RDONLY)` + `os.pread`（实测耗时 `0.0051s < 0.20s`）并内置无盘 clean-room 回退（`raw_firmware_bytes_leaked == 0`、`emmc_writes_authorized == False`、`persistent_emmc_writes_authorized == False`、`cross_model_flash_authorized == False`、`hardware_live_attachment_authorized == False`、`usb_packets_transmitted == 0`）。

---

## 1. 交付物清单（严格 6 个受控文件）

1. 门禁与 162 门禁统一预检模块：[`realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/fx3_safety/realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.py)
2. 包导出注册：[`fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/fx3_safety/__init__.py)
3. CLI 注册（`verify-antidust-focusmag-guard` / `verify-g161`、`verify-expstd-usbtether-guard` / `verify-g162`、`verify-162-gates`）：[`fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/fx3_safety/__main__.py)
4. 安全套件文档更新（新增 §81）：[`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/README.md)
5. 4 模式单元测试套件（`109` 项测试）：[`test_realhw_antidust_focusmag_expstd_usbtether_162gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/outputs/fx3-safety/tests/test_realhw_antidust_focusmag_expstd_usbtether_162gate_guard.py)
6. 中文工程收尾报告（本文件）：[`reports/2026-11-21-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h480-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/reports/2026-11-21-phase378-safety-162gates-antidust-focusmag-expstd-usbtether/README.md)

---

## 2. 新增安全门禁与实测 / 推断边界

### 2.1 门禁 `G161`：`DORMANT_ANTIDUST_OPEN_SHUTTER_CLEANING51_AND_FOCUS_MAG_CLEAN_HDMI_ISOLATION_FIREWALL`
- **`实测事实`（`ALCIN_UUD` 关机常开快门与 `[Sensor Cleaning]` `>=51%` vs FX6 密封 `e-ND` + `APR`）**：
  - `FX3 appFw.so` 虽编译保留休眠符号 `anti_dust_shutter_when_power_off`、`silent_mode_shutter_when_power_off`、`BKID_APP_setting_image_sensor_barrier`、`PID_SET_IMAGE_SENSOR_BARRIER` 与 UXC `_f 0x7495`（`Anti-dust Function`）、`_f 0x709f`（`Shutter When Pwr OFF`），但被 `VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD` 屏蔽；任何调用或强制关机闭帘请求均在 `G161` 返 **`EOPNOTSUPP=95`**，强锁关机焦平面快门常开（`OPEN`）。
  - 唯一活跃入口 `Setup -> [Setup Option] -> [Sensor Cleaning]`（`_f 0x67d6` / 旧 `Cleaning Mode` `0xe7d7`）强锁 `NP-FZ100 >= 51%` 电量门限与物理断电提示（`_g 0x6221`），低于 `51%` 或跳过断电提示返 `EINVAL=22`。
  - 对照 `ILME-FX6 Ver. 6.01`：无焦平面机械快门（`0` `shutter_when_power_off` 命中），前端由可变电子 `e-ND`（`1/4..1/128 + CLEAR`，`PID_SET_VARIABLE_ND_VALUE`）密封，不支持用户 IBIS 振尘（返 `EOPNOTSUPP=95`），像素校准走 `Technical > APR`（`MODEL_APR_EXECUTE_COMP`）。
- **`实测事实`（`[Focus Magnifier]` 全链路、Clean-HDMI 零裁切与 FX6 `VF/HDMI` 目标）**：
  - `Shooting -> [Focus] -> [Focus Assistant]` 精确 **5 项**在 Ver. 2.00+ **全部抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 还原）；锁定 12.1MP 真实倍率（Still FF `x1.0->x2.1->x4.1`、Still APS-C `x1.0->x1.5->x3.0`、Movie/`S&Q` `x1.0<->x4.0`），拒绝 10 项高像素 Alpha 休眠倍率（`x1.6/x2.7/x3.1/x3.6/x3.7/x4.2/x4.7/x5.3/x5.5/x6.1` -> `EOPNOTSUPP=95`）。
  - `[Focus Magnif. Time]` 为 `2 Sec` / `5 Sec` / `No Limit`（默认）；`[AF in Focus Mag.]` 与 `[Auto Magnifier in MF]` 严格仅限 Still（Movie/`S&Q` 调起返 `EOPNOTSUPP=95`）；Movie `REC` 不取消放大；`HDMI Info. Display = Off` 下 Clean-HDMI 与机内录制均 **0 裁切像素**；可与 `Peaking`、`Bright Monitoring`（Ver. 7.00+）、`De-Squeeze` 共存，并压制 `Marker Display`、`Switch V/H AF Area`、`AF Illuminator`。
  - 对照 FX6 `Monitoring > Focus Magnifier`：`VF` `x3/x6` 与 Ver. 6.0+ `Focus Mag Button Target = HDMI` `x2/x4`，SDI 与内录均零裁切，休眠 FS7 `x8.0` 返 `EOPNOTSUPP=95`（`384` 状态矩阵全通过）。
- **`推断`**：在台架及自动化仿真中将休眠 `image_sensor_barrier` 或高像素倍率误映为活跃项会导致 NVS 状态漂移及换镜头机械快门受损风险，故由 `G161` 统一以 `EOPNOTSUPP=95` 阻断。

### 2.2 门禁 `G162`：`EXPOSURE_STD_ADJUST_5MODE_RESET_IMMUNE_AND_USB_TETHERING_ZERORF_SLOT1_EROFS_FIREWALL`
- **`实测事实`（`[Exposure Std. Adjust]` 5 模式抗复位隐藏偏移 vs FX6 `±3.0` 25 档 `AE Level`）**：
  - `Exposure/Color -> [Exposure Comp.] -> [Exposure Std. Adjust]` 覆盖全部 **5 种测光模式**（`Multi`/`Center`/`Spot`/`Entire Screen Avg.`/`Highlight`），范围 `-1.0 EV..+1.0 EV`、`1/6 EV` 步进（`13` 档，休眠 `1/8 EV` 返 `EOPNOTSUPP=95`）。
  - **抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 归零，非零时显示测光警示图标），平移 `M.M.` 零点与 Spot AEL 基准但**绝不改变 EXIF `ExposureBiasValue`**（`0.0 EV` 增量），包围中途调整将清零包围计数；`Cine EI` / `Cine EI Quick` 下仅偏置 `M.M.` 读数而不改写固定 Base ISO 曝光。
  - 对照 FX6 `Shooting > Auto Exposure > Level`：实证 **`-3.0..+3.0`（`0.25 EV` 步进，共 `25` 档，驳斥 `±2.0` 误传）**，并支持每 LUT 独立 `Base Look > AE Level Offset`。
- **`实测事实`（有线智能手机 USB 网络共享、零射频 `Airplane Mode` 旁路与 Tier-0 `Slot 1` `EROFS=30` 防火墙）**：
  - `Network -> [USB-LAN/Tethering]` + Ver. 7.00+ `[USB-LAN Cnct. Launch]` 通过 `libNetServiceTethering.so` / `libTetheringResource.so`（`cdc_ether`/`cdc_ncm`/`ipheth`/`rndis_host` + `dhcpcd`）支持在 **`[Airplane Mode] = On`（零射频 `rf_tx_packets = 0`）** 下稳定执行 `RTMP/RTMPS/SRT` 与 `FTP`；并强制检查 `[Reset Network Set.]` 重启后重设 `[Airplane Mode] = On`。
  - 强锁双 USB 物理口并发互斥（`EBUSY=16`）、*Monitor & Control* Ver. 4.00+ FX3 USB 模式下缺失时间码 / `Focus map` / LUT 导入（`EOPNOTSUPP=95`）、*Creators' App* USB 直推直播禁用（`EOPNOTSUPP=95`）、休眠 `USB Streaming`（`NOUVC` -> `EOPNOTSUPP=95`）及 FX3 `libInfraUsbCmn.so` 零 `CUsbGadgetIAP` 剥离（`EOPNOTSUPP=95`，对照 FX6 主动链接 `/usr/kmod/usbg_iap.ko`）。
  - 强锁 **Tier-0 `Slot 1` `EROFS=30` 防火墙**：`MTP` 硬锁 `Slot 1`，`MSC`（`usbg_storage.ko`，实证 `FX3 appFw.so` 原始拼写 `USB_CONNECTION_METHOD_MASS_STRAGE`）无论 `Multi` 还是 `Single` LUN 均将 `Slot 1` 暴露为可写块设备，任何未受只读保护的可写暴露均硬返 **`EROFS (errno 30)`**，恒守 `slot1_writes == 0`、`usb_tx == 0`、`cross_model_flash_authorized == False`、`live_attach_authorized == False`（`480` 状态矩阵全通过）。
- **`推断`**：未隔离的 `MSC`/`MTP` 会导致宿主机（如 macOS `mds`/`.Spotlight-V100`/`.fseventsd`）静默改写 Tier-0 `Slot 1` 恢复卡，因此必须在协议入口层先于 `EBUSY`/`EOPNOTSUPP` 优先以 `EROFS=30` 拦截。

---

## 3. 实测验证结果（`实测事实`）

| 检查项 / 命令 | 覆盖范围 | 执行模式 | 实测结果 |
| :--- | :--- | :--- | :--- |
| `test_realhw_antidust_focusmag_expstd_usbtether_162gate_guard.py` | `109` 项单元测试（4 模式） | Normal / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / Donorless (`work_root=None`) | 全部 PASS（`109/109` × 4：`34.46s` / `35.21s` / `34.83s` / `32.57s`，`0` 失败） |
| `python3 -B -m fx3_safety verify-g161 --summary` & `verify-g162 --summary` | 单门禁 CLI 校验 | `LOCAL_DONOR_O_RDONLY` | PASS（`G161` 与 `G162` 均 `valid=True`，`24` donor `0.0051s`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-162-gates --summary` | `G01..G162` 统一预检 | 离线默认 NO-GO（`LOCAL_DONOR_O_RDONLY`） | PASS（`159/162`，`VERIFIED_159_OF_162_AWAITING_PHYSICAL_TIER0`，`overall_ready_for_hardware_attach=False`，`leaked=0`） |
| `python3 -B -m fx3_safety verify-162-gates --simulate-bench-dry-run --force-clean-room --summary` | `G01..G162` 统一预检 | 离线模拟干跑（`CLEAN_ROOM_SYNTHETIC`） | PASS（`162/162`，`VERIFIED_ALL_162_GATES_DRY_RUN_SIMULATED_BACKUP`，`usb_tx=0`，`cross_model_flash_authorized=False`） |
| 全量 `outputs/fx3-safety/tests`（`83` 个测试文件，3 并发） | `5,038` 项安全测试 | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 PASS（Normal `5,038/5,038` `352.30s`；Clean-Room `5,038/5,038` `314.38s`，`0` 失败） |
| `make verify-milestone-364`（双模） | 上游主闭环自动发现 | Normal & `FX3_FX6_FORCE_CLEAN_ROOM=1` | 全部 PASS（`status=OK`，`pillars=6/6`，自动发现 `gate156=159/162`，`leaked=0`） |
| `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | 仓库洁净度与字节码审计 | 离线 | `ALL GREEN`（零未跟踪二进制，零 `.pyc`，仅含 6 个受控文件） |
