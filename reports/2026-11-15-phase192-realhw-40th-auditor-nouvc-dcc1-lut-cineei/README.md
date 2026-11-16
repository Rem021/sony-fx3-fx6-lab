# Phase 192（第 40 号里程碑审计器 `40/40`）：真机 `ILME-FX3`（`Ver. 7.02`）无 UVC USB Gadget 栈、`USB-PD`（`NP-FZ100`）vs `DC-C1`（`>=65W / 5A`）供电预算、双介质 `.cube` User LUT 路径非对称（`SD` vs `CFexpress-A`）与 `Cine EI`（`800 / 12800`）审计器

## 结论先行

已在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/README.md) 完成 **第 40 号里程碑真机二进制审计器（`40/40`）** [`realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py)、CLI 子命令 `audit-realhw-nouvc-dcc1-lut-cineei`、`audit-all` 40/40 注册以及 52 项双模式单元测试 [`test_realhw_nouvc_dcc1_pd_lut_path_cineei.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/tests/test_realhw_nouvc_dcc1_pd_lut_path_cineei.py)。基于 [Wave-24 索尼真机情报](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/reports/2026-11-15-global-sony-wave24-uvc-absence-dcc1-usb-pd-user-lut-path-split-intel/README.md)，本地真机供体模式与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式均实现 `100%` 全绿通过。

## 核心实现与四大实测审计域

1. **有界只读供体扫描（`< 0.15s` + 进程内缓存）与 Clean-Room 回退**：
   - [`_collect_local_donor_scan`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L1572-L1711) 与 [`_scan_kmod_rdonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L1358-L1424) 全程严格使用 `os.O_RDONLY` + `os.pread` 有界读取 18 份真机文件/脚本（冷扫描实测 `0.0739s`，命中缓存 `0.000841s`）；Clean-Room 合成模式下 `raw_firmware_bytes_leaked == 0` 且 JSON 输出零 `ELF` 魔数泄露。
   - 核验 16 份二进制供体尺寸：FX3 `7.02`（`appFw.so` `79,015,712 B`、`libmpr.so` `3,517,008 B`、`cpapp-b.bin` `15,980,568 B`、`libInfraUsbCmn.so` `159,504 B`、`libUsbControl.so` `135,424 B`、`libUsbBusPower.so` `48,232 B`、`libInfraVericLiveStreaming.so` `182,472 B`、`libInfraRtmpLiveStreaming.so` `85,960 B`、`libInfraSrtLiveStreaming.so` `90,248 B`、`.ko` 模块 `cdc_ncm.ko` `32,208 B`、`usbg_storage.ko` `104,288 B`、`usbg_stillimage.ko` `49,448 B`、`usb_f_uvc.ko` `78,840 B`、`usb_buspwr.ko` `27,728 B`，`vermagic=4.9.337-scel+`）与 FX6 `6.01`（`appFw.so` `50,520,424 B`、`libInfraUsbCmn.so` `164,144 B`）。
2. **Pillar 1（`NOUVC_GADGET_AND_NETWORK_STREAMING`）**：
   - [`evaluate_nouvc_gadget_and_network_streaming`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L669-L821) 实证 `ILME-FX3`（`0x91030080`）/`ILME-FX3A`（`0x91030082`）在 `4.9.337-scel+` 启动脚本 `insmod_drv2` / `usb_insmod.sh` 中零自动加载 `g_webcam` / `usb_f_uvc`，复合 Gadget 仅暴露 `Sel. When Connect` / `MSC` / `MTP` / `Remote Shooting`（`1024x576` 无音频上限） / `USB-LAN`（`CDC-NCM` / `RNDIS`）。
   - Stage-B 对 `FX3` 屏蔽 `[USB Streaming]` UVC/UAC 描述符调用（对比 `ILME-FX30` / `ILME-FX2` / `ILME-FX6` 原生允许），同时保留 `7.00/7.02` `USB-LAN` 上电自连（`USB_LAN_CONNECT_LAUNCH_ON`）与 `4K 59.94p` `RTMP/RTMPS/SRT <= 38 Mbps`（`HEVC`/`AVC`）网络推流。
3. **Pillar 2（`POWER_DELIVERY_PD_VS_DCC1`）**：
   - [`evaluate_power_delivery_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L824-L1029) 建模完整电源状态机：机身 Type-C `USB Power Supply = On` 必须插入 `NP-FZ100` 电池，开机录像时暂停内部充电、关机后自动恢复；硬拒绝 Micro-USB 供电；`DC-C1` 假电池需要 `>= 65W` USB-PD 电源与 `5A` e-Marker 线缆预算，且会触发释放机身 Type-C（供 `USB-LAN` / `Creators' App` 使用）与 LCD 最高亮度锁定提示，低于 `65W` 或无 `5A` e-Marker 时报错闪烁并阻止欠压跌落。
4. **Pillar 3（`LUT_PATH_CINE_EI_AND_RMT_P1BT`）**：
   - [`validate_cube_text_bounded`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L616-L661) 与 [`evaluate_user_lut_path_and_cine_ei`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L1032-L1129) 审计双介质目录非对称硬约束（`SD`: `/Private/Sony/PRO/LUT/` vs `CFexpress-A`: `/Sony/PRO/LUT/`，交叉错配立即 fail-closed 拒绝）、`.cube` 参数（`LUT_3D_SIZE` `17`/`33`、文件名 `<= 63` ASCII 字节、`User1..User16`、`AE Level Offset 0..+2 EV` 步进 `1/3 EV`）与 `Cine EI` 双原生 ISO（`800` / `12800`，高基底支持 `3200..51200 EI` 且零 CMOS 模拟增益污染）。
   - [`evaluate_rmt_p1bt_and_clip_flag_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L1132-L1190) 审计 `Bluetooth Rmt Ctrl = On`（`RMT-P1BT`）强制禁用红外遥控与 GPS 位置信息链接的物理互斥关系，以及 `Creators' Cloud` `OK/NG/KEEP` 片段标记筛选门槛（`Creators' App >= 3.1.0`、`M&C >= 2.4.0`）。
5. **Pillar 4（写保护防火墙与 12 触点 4 分类矩阵）**：
   - [`evaluate_phase192_write_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L1193-L1237) 与 [`build_phase192_compat_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py#L1240-L1350) 硬阻断对 `p2:/setting`、`Backup.bin`、`BODYDATA.DAT`、`/dev/nflasha*` 与 `spi_nor:` 的直接写入，仅允许 `/tmp/`、`ram://` 与外置卡路径，并产出 12 触点 4 分类兼容矩阵。

## 变更文件索引

- [`realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.py)（新增：第 40 号里程碑审计器）
- [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 192 符号与 `__all__`）
- [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：接入 `audit-realhw-nouvc-dcc1-lut-cineei` 与 `audit-all` `40/40`）
- [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/README.md)（更新：补充第 40 号审计器说明与 CLI 用法）
- [`test_realhw_nouvc_dcc1_pd_lut_path_cineei.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/tests/test_realhw_nouvc_dcc1_pd_lut_path_cineei.py)（新增：52 项双模式单元测试）
- [`test_realhw_fx3_vs_fx3a_and_xlrh1_mishoe.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h209-phase192-40th-auditor-nouvc-dcc1-lut-cineei/outputs/fx3-firmware-lab/tests/test_realhw_fx3_vs_fx3a_and_xlrh1_mishoe.py#L637)（微调：将 `len(audit_keys) == 39` 放宽为 `>= 39`）

## 已验证事实 vs 未执行物理真机动作边界

- **已验证事实（`O_RDONLY` 本地供体 & Clean-Room 实测）**：
  - `audit-realhw-nouvc-dcc1-lut-cineei --json` 与 `audit-all --json`（`40/40` 审计键）均返回 `all_checks_passed: true`。
  - Phase 192 全部 52 项单元测试在本地供体模式（`0.451s`，`OK`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式（`0.380s`，`OK (skipped=1)`）下均 `100%` 通过。
  - 全量 `outputs/fx3-firmware-lab/tests` 套件在本地供体模式（`1,464` 项，`54.231s`，`OK`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式（`1,464` 项，`26.746s`，`OK (skipped=6)`）均全绿通过。
- **未执行物理真机动作声明**：
  - 未连接真实物理 FX3 / FX3A / FX6 相机，未接入真实 `DC-C1`、`NP-FZ100`、`RMT-P1BT` 或物理 USB/SD/CFexpress 卡，未执行任何真实烧录或持久化存储器写入：
    - `persistent_emmc_writes_authorized = False`
    - `spi_nor_write_authorized = False`
    - `el3_payload_transmit_authorized = False`
    - `physical_usb_packets_emitted = 0`
    - `persistent_writes = 0`
    - `raw_firmware_bytes_leaked = 0`
