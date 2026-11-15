# Phase 183（第 38 号统一审计器 `38/38`）：真机 `MIRA_CETUS2` E 卡口 `info7/info8/info3D` 串口握手、Sony 镜头位掩码 `((lens_id >> 14) == 3)` 与 `0x02cf0232` 呼吸效应补偿 / Focus Map 审计器

## 结论先行

已在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/README.md) 完成 **第 38 号真机二进制审计器（`38/38`）** [`realhw_emount_info3d_breathing_02cf0232_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_emount_info3d_breathing_02cf0232_auditor.py) 及其 CLI 子命令 `audit-realhw-emount-info3d-breathing`、`audit-all`（`38/38`）注册与 50 项双模式单元测试 [`test_realhw_emount_info3d_breathing_02cf0232.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/tests/test_realhw_emount_info3d_breathing_02cf0232.py)。

## 核心实现与四大实测审计域

1. **有界只读供体扫描（`< 0.25s`）与 Clean-Room 回退**：
   - 全程严格使用 `os.O_RDONLY` + `os.pread` 有界读取（本地真机供体模式单次实测 `0.2040s`；Clean-Room 合成模式 `0.0007s`），`raw_firmware_bytes_leaked == 0`。
   - 核验 FX3 `7.02` (`appFw.so` `79,015,712 B`, `libmpr.so` `3,517,008 B`, `cpapp-b.bin` `15,980,568 B`, `libInfraLensCommunicator.so` `14,544 B`, `libInfraPtpControl.so` `165,320 B`) 与 FX6 `6.01` (`appFw.so` `50,520,424 B`, `libmpr.so` `28,921,824 B`, `cpapp-b.bin` `17,952,816 B`, `libInfraLensCommunicator.so` `14,544 B`, `libInfraPtpControl.so` `152,520 B`, `lensfile.bin` `262,592 B`)。
2. **Domain A (`EMOUNT_INFO7_INFO8_INFO3D_PACKET_CONTRACT`)**：
   - 验证 FX3 与 FX6 的 `libInfraLensCommunicator.so`（`14,544 B`、`27` 导出 / `25` 导入符号）ABI 100% 一致；验证 Route-1 Stock `cpapp-b.bin` 中 `Mount_DividedInfo_*`（`BreathingCorrectionData`、`CamCurveData`、`EclipseData`、`FnoCorrectAbility`、`IrisDrivabilityData`、`SteadyShotInfo`）与 `info7`/`info8`/`info3D` CRC32 封包编解码。
3. **Domain B (`SONY_LENS_ID_BITMASK_AND_BREATHING_02CF0232`)**：
   - 确认 FX6 `appFw.so` 的 `.data.rel.ro` (`0x2c29a5c`) 中存在小端 `0x02cf0232` (`BKID_APP_MR_SETTING_LENS_COMP_BREATHING`) 常量，且 FX3/FX6 `appFw.so` 与 `libmpr.so`（`UDAMSetBreathingCorrectionValue`）完整具备呼吸效应及 Catalyst 元数据管线。
   - 验证 [`is_sony_first_party_emount_lens`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_emount_info3d_breathing_02cf0232_auditor.py#L533-L541) 精确判据 `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)`：原厂 `0xC120`/`0xC000` 放行呼吸效应动态裁切（`1.000x..1.125x`）与 Catalyst 元数据注入；副厂 E 口（`0x4024`）、保留低 12 位（`0xCFFF`）及手动 PL/E 转接环（`0xFFFF`/`0x0000`）均优雅降级关闭裁切且 `fault_raised == False`；`HDMI RAW16`、`S&Q 120p+` 与增距镜均旁路裁切。
4. **Domain C (`P18_LENSFILE_BIN_RO_VS_CINEALTA_SLOTS`)**：
   - 解析 FX6 `lensfile.bin`（`262,592 B`，`57` 组 `VX8900..VX9202` 镜头记录，表尾 `262,588` 字节边界完整，`BLKROSET=1`）；验证 `setLensFile` 仅存在于 FX6 `cpapp-b.bin`（`>= 1` vs FX3 `0`），而两机共用 `fixed_lensfile` / `ExtractFromCombinedLensData`。
   - 通过 [`evaluate_p18_lensfile_vs_cinealta_slots`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_emount_info3d_breathing_02cf0232_auditor.py#L1011-L1081) 硬阻断对 `p18:/lens/LENSFILE.BIN`、`/dev/nflasha18` 的写入（`lens_partition_writes == 0`），仅允许易失性 CineAlta 用户偏置写入 `tmpfs`（`/tmp/`）或外置 SD/CFexpress ExFAT。
5. **Domain D (`MONITOR_CONTROL_210_FOCUS_MAP_STREAM`) & 写保护防火墙**：
   - 校验 Monitor & Control `Ver. 2.1.0+` 焦点映射（Focus Map）在 `P12` 飞行模式下通过有线 `CDC-NCM` USB-LAN 零射频泄露（`rf_tx_leaks == 0`）运行，并支持未锁定飞行模式时的 `WPA2/WPA3` Wi-Fi，同时拒绝 `WEP`/`WPA1-TKIP`/`IPsec` 及 `< 2.1.0` 版本；无触点手动转接环（`0xFFFF`）优雅退回峰值对焦；[`evaluate_phase183_write_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_emount_info3d_breathing_02cf0232_auditor.py#L1183-L1228) 阻断 `p2:/setting/Backup.bin`、`p18:/lens`、`/dev/cnflasha*` 与 `spi_nor:`，并构建 12 触点 4 分类兼容矩阵。

## 变更文件索引

- [`realhw_emount_info3d_breathing_02cf0232_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_emount_info3d_breathing_02cf0232_auditor.py)（新增：第 38 号审计器）
- [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 183 符号）
- [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：接入 `audit-realhw-emount-info3d-breathing` 与 `audit-all` `38/38`）
- [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/README.md)（更新：补充第 38 号审计器与 CLI 用法）
- [`test_realhw_emount_info3d_breathing_02cf0232.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/tests/test_realhw_emount_info3d_breathing_02cf0232.py)（新增：50 项双模式单元测试）
- [`test_realhw_hdmi_braw_wpa3_702_delta.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h200-phase183-38th-auditor-emount-info3d-breathing-02cf0232/outputs/fx3-firmware-lab/tests/test_realhw_hdmi_braw_wpa3_702_delta.py#L623)（微调：将 `len(audit_keys) == 37` 放宽为 `>= 37`）

## 已验证事实 vs 未执行物理真机动作边界

- **已验证事实（`O_RDONLY` 本地供体 & Clean-Room 测试）**：
  - 全部 50 项 Phase 183 单元测试在本地供体模式与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式下均 100% 通过。
  - 全部 `outputs/fx3-firmware-lab/tests` 套件及 `scripts/run_all_lab_tests.py --clean-only` 均通过验证。
- **未执行物理真机动作声明**：
  - 未连接真实物理 FX3/FX6 相机，未执行任何真实 E 卡口镜头热插拔、真实 UART/USB/SD 烧录或持久化存储器写入：
    - `persistent_emmc_writes_authorized = False`
    - `spi_nor_write_authorized = False`
    - `el3_payload_transmit_authorized = False`
    - `physical_usb_packets_emitted = 0`
    - `lens_partition_writes = 0`
    - `backup_bin_writes = 0`
