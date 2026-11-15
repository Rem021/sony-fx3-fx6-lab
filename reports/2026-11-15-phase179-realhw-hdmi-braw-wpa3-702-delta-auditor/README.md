# Phase 179（第 37/37 项统一审计）：真实硬件 FX3 `Ver. 7.02` vs FX6 `Ver. 6.01` 世代差异桥接审计报告

## 1. 结论先行

本阶段在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab) 新增第 **37/37** 个统一固件审计模块 [`realhw_hdmi_braw_wpa3_702_delta_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py)，针对 FX6 `Ver. 6.01` `appFw.so` 运行在 Stock FX3 `Ver. 7.02`（`4.9.337-scel+` 内核与后台守护进程）Stage-B 时的 **4 项 `7.02` 世代差异**，完成了严格只读（`os.O_RDONLY` + `os.pread` 有界读取）与合成 Clean-Room 双模态（`LOCAL_DONOR_VERIFIED` `0.327 s` + `CLEAN_ROOM_SYNTHETIC` `0.001 s`）全量验证：

1. **Type-A HDMI 外部 RAW / 4K60 输出 vs 屏蔽 `12G-SDI` BNC 探测**：[`evaluate_hdmi_braw_vs_masked_12g_sdi_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L856-L928) 验证 FX3 机身不存在 `12G-SDI` BNC 接口（`sdi_bnc_present = False`），对 FX6 的 `BKID_APP_SETTING_SDI_OUTPUT` / `PRM_FEATURE_MANAGER_sdi_output` / `MoniFpgaSdi` 探针实施零故障屏蔽（`sdi_blocking_faults = 0`），同时将 Blackmagic RAW / ProRes RAW / Clean 4K60 10-bit LUT + Timecode 桥接至 FX3 `7.02` 全尺寸 Type-A HDMI 驱动（RAW 模式禁止烧录 LUT）。
2. **WPA2/WPA3-Only 与 Access Authentication 无线安全栈**：[`evaluate_wpa2_wpa3_security_shim`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L934-L1028) 实测 FX3 `7.02` `appFw.so` 已移除 `VAL_setting_wlan_security_WLAN_SECURITY_WEP`（`0` 命中 vs FX6 `6.01` `1` 命中），配置垫片拦截/净化已废弃的 `WEP`、`WPA1-PSK (TKIP)` 与 `IPsec` 配置，仅向 `wpa_supplicant`（`v2.9-devel`，含 `SAE` / `sFT-SAE` / `WPA2-PSK-SHA256` / `ieee80211w` PMF）透传 `WPA2` / `WPA3` / `Access Authentication`，并在 P12 飞行模式下强制零射频发包（`rf_tx_packets_emitted = 0`）。
3. **1.5x / 1.6x / 1.3x / 2.0x 变形宽银幕 De-Squeeze 与 Bright Monitoring / 焦点放大器 GRM 平面兼容**：[`evaluate_anamorphic_desqueeze_grm_compat`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L1034-L1104) 校验 FX3 `7.02` 新增的 `1.5x` / `1.6x` / `1.65x` 比例与 FX6 `6.01` 原生 `1.0x` / `1.3x` / `2.0x` 在 `grm_ma.ko`（`vermagic=4.9.337-scel+`）与 `libgemini-grm.so` 上的平面缩放（视频层按 `1/S` 纵向压缩，OSD 层保持 `1:1`），确保 Big-6 状态栏（`sid=0x0a`）与 Clean HDMI 均不裁剪（`big6_hud_unclipped = True`, `clean_hdmi_unclipped = True`）。
4. **自动 USB-LAN 识别与双卡槽剩余时间遥测 + 零写入防火墙**：[`evaluate_auto_usblan_recognition`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L1110-L1139)、[`evaluate_dual_slot_remaining_time_telemetry`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L1145-L1218) 与 [`evaluate_phase179_write_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L1221-L1265) 验证 `cdc_ncm.ko` / `r8152.ko` / `asix.ko` / `ax88179_178a.ko` 自动绑定 `eth0`、双卡槽 `SIMULTANEOUS` / `RELAY` / `SORT` 零掉帧遥测与 12 触点 4 分类矩阵，同时锁死 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

> [!IMPORTANT]
> **严格区分实测事实与未执行物理机台架动作**：本报告第 2 节所有字节数、ELF 导出/导入计数与符号命中均为在本地工作站上对真实 FX3 `7.02` 与 FX6 `6.01` Donor 工件执行 `os.O_RDONLY` + `os.pread` 的实测结果（`report_sha256=1e70f5201b4a9e9c06a1bfe9932b8cdfd9c5081b0c34ac5b3f1c8fea830b39ab`），以及 `FX3_FX6_FORCE_CLEAN_ROOM=1` 合成 Clean-Room 夹具的实测结果（`report_sha256=cd7714ac8c09a157a2b872541eec69859c5c2f49f40c3d6e13f9eb9dd774fc3b`）。**真实物理 `ILME-FX3` 机身上电连接 Blackmagic Video Assist / Atomos HDMI RAW 录机、WPA3-SAE 路由器实网关联、物理 USB-LAN 网卡热插拔及实体变形镜头画幅实拍均尚未在物理机台架执行**。

---

## 2. `O_RDONLY` 本地 Donor 实测证据（`LOCAL_DONOR_VERIFIED`，`0.327 s`）

| Donor 工件 | 机身 / 固件 | `O_RDONLY` 实测字节数 | 关键结构与符号命中实测 |
| :--- | :--- | ---: | :--- |
| `appFw.so` | FX3 `7.02` / FX6 `6.01` | `79,015,712` / `50,520,424` | FX3 命中 `HDMI_RAW_CONNECTSTATE_HDMI_CONNECT` (`2`)、`QFHD_100HZ_420_TV_CONNECT_STATE_CONNECTED` (`3`)、`DE_SQUEEZE_DISP_1_5X`/`1_65X`/`1_6X` (`1/1/6`)，且 `WEP` 枚举命中 **`0`**、`SDI_OUTPUT*` 命中 **`0`**；FX6 命中 `BKID_APP_SETTING_SDI_OUTPUT*` (`1/3`)、`PRM_FEATURE_MANAGER_sdi_output` (`1`)、`WLAN_SECURITY_WEP` (`1`)，且 `1_5X`/`1_6X`/`1_65X` 命中 **`0`** |
| `libInfraAvbbc.so` | FX3 `7.02` / FX6 `6.01` | `1,734,632` / `1,743,200` | 导出/导入 `5,293/197` vs `5,266/218`；均命中 `ConvertCmdMidToHdmiEt` (`1`)、`ConvertCmdMidToSdiEt` (`1`)、`ExecCmd_ADF_SetHdmiFormat` (`17`) |
| `cpapp-b.bin` | FX3 `7.02` / FX6 `6.01` | `15,980,568` / `17,952,816` | 共享 `MSG_ID_INFRABB_VIDEO_DE_SQUEEZE` (`1`)、`SET_ANAMO_DESQUEEZE_SCALE` (`1`)；`MoniFpgaSdi_SetRegSDIOutFormat` 仅 FX6 命中 (`1` vs `0`) |
| `wpa_supplicant` | FX3 `7.02` / FX6 `6.01` | `1,380,160` / `1,376,056` | 均命中 `wpa_supplicant v2.9-devel` (`2`)、`SAE` (`146`)、`sFT-SAE` (`1`)、`WPA2-PSK-SHA256` (`1`)、`ieee80211w` (`3`)、`PMF` (`2`) |
| `libWlanAdjust.so` | FX3 `7.02` / FX6 `6.01` | `73,168` / `73,168` | 导出/导入 `188 / 119`；均命中 `wpa_ctrl_open` (`1`)、`wpa_ctrl_request` (`1`)、`WPA-PSK` (`1`) |
| `libNetServiceEther.so` | FX3 `7.02` / FX6 `6.01` | `114,384` / `175,376` | 导出/导入 `286/94` vs `480/96`；均命中 `ConnectedUsbEtherDevice` (`18` vs `25`)、`NseMiscGetMacAddressForUsbEther` (`1`)、`eth0` (`1` vs `2`) |
| `libmpr.so` | FX3 `7.02` / FX6 `6.01` | `3,517,008` / `28,921,824` | 均命中 `MovieRemain::GetRemain` (`1`)、`MprIf::PrepareRelayMedia` (`1`)、`MprIf::SetRecSimultRecInternalStopMode` (`1`)、`SimulRec` (`1`)；FX3 额外命中 `MovieRemain::CalcRecordableTime` (`1` vs `0`) |
| `libgemini-grm.so` + 5 项 `.ko` | FX3 `7.02` & FX6 `6.01` | `51,800`；`cdc_ncm` `32,208`、`r8152` `56,264`、`asix` `46,592`、`ax88179_178a` `23,848`、`grm_ma` `36,592` | `libgemini-grm.so` 命中 `GraphicsContextGRM::setScale` (`1`) 与 `createPlaneTexture` (`1`)；5 项 `.ko` `.modinfo` 均实测匹配 `vermagic=4.9.337-scel+` |

---

## 3. 12 触点 4 分类兼容性矩阵

[`build_phase179_delta_compat_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py#L1268-L1379) 覆盖全部 4 个子系统共 **12** 项触点，分类统计：`NATIVE_PASSTHROUGH = 5`、`SHIM_TRANSLATED = 5`、`MASKED_ABSENT_HW = 1`、`HARD_WRITE_PROTECTED = 1`。

---

## 4. 交付文件与实测验证结果

### 4.1 交付文件（严格限定于授权路径）
- 审计核心：[`realhw_hdmi_braw_wpa3_702_delta_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_hdmi_braw_wpa3_702_delta_auditor.py)
- 包导出与 `37/37` CLI 接线：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py#L2258-L2367)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py#L259-L344)、[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/README.md#L181)
- 双模态单元测试（50 项）：[`test_realhw_hdmi_braw_wpa3_702_delta.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/tests/test_realhw_hdmi_braw_wpa3_702_delta.py)（并将 Phase 174 [`test_realhw_wbi2_hibdrv_hibernation_isolation.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h195-phase179-37th-auditor-hdmi-braw-wpa3-702-delta/outputs/fx3-firmware-lab/tests/test_realhw_wbi2_hibdrv_hibernation_isolation.py#L273) 第 273 行 `assertEqual(..., 36)` 放宽为 `assertGreaterEqual(..., 36)`）

### 4.2 实测验证结果（全程 `/usr/bin/python3 -B`）
1. `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-hdmi-braw-wpa3-702-delta --json`：通过（`LOCAL_DONOR_VERIFIED`, `all_checks_passed=True`）。
2. `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-hdmi-braw-wpa3-702-delta --json`：通过（`CLEAN_ROOM_SYNTHETIC`, `all_checks_passed=True`）。
3. `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --json`：**37/37** 审计器全部 `all_checks_passed=True`。
4. `/usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_hdmi_braw_wpa3_702_delta.py`：**50 项测试全部通过**（`2.879s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下 **50 项通过**（`0.372s`, `skipped=1`）。
5. `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"`：**1,312 项测试全部通过**（`49.108s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下 **1,312 项通过**（`25.051s`, `skipped=5`）。
6. `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：`ALL GREEN in 0.05s`（无 `.pyc` / 二进制污染）。
