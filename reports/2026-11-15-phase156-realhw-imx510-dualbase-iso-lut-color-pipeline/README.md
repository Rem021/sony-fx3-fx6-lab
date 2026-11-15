# Phase 156 — 真机主线 `IMX510` CMOS 传感器校准、Dual-Base ISO `800 / 12800`（LCG/HCG）与 `S-Log3` / `.cube` 3D MLUT Stage-B 色彩管线第 32 项审计报告

> **结论先行**：已完成第 32 项固件实验室审计器 [`realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.py) 及其 48 项双模式单元测试，接入 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) `audit-all`（总计 **32/32** 全部通过）与新增 CLI 子命令 `audit-realhw-imx510-color-pipeline`。本地真实供体与强制 Clean-Room（`FX3_FX6_FORCE_CLEAN_ROOM=1`）双模式全量测试均已通过。

---

## 一、严格事实边界（`O_RDONLY` 二进制实证 vs 未执行真机实拍）

1. **已验证事实（`os.O_RDONLY` + `mmap.ACCESS_READ` 只读扫描与确定性单元测试）**：
   - 基于本地 FX3 v7.02 与 FX6 v6.01 真实二进制供体（`appFw.so`、`libsencore.so`、`libmpr.so`、`cpapp-b.bin`、`Backup.bin`、`S709.cube`）的只读 ELF64/BK4/字符串符号扫描与干净室回退测试，单次执行耗时 `< 0.75 s`，零原始字节泄漏、零写入操作。
2. **未执行实机验证（显式边界声明）**：
   - 本阶段未在物理 `ILME-FX3` 机身（含实时感光元件上电、实拍 `M4ROOT/CLIP` 录像或物理 SD 卡加载 `.cube`）上执行实体机身拍摄与实测，真机色彩还原与实拍波形仍待真机 Stage-B 验证。

---

## 二、四大审计支柱与 `O_RDONLY` 实证发现

### 1. `IMX510` 单体工厂传感器校准与 `p2` NVS 只读保护
- **驱动与校准表同源性**：FX3 v7.02 `cpapp-b.bin`（`15,980,568 B`）与 FX6 v6.01 `cpapp-b.bin`（`17,952,816 B`）共享完全一致的 `IMX510` 10.2MP 全画幅 BSI Exmor R 驱动类（`N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E`、`N6Camera6Imager21ImagerDrvParam_IMX510E`）、`/setting/defdet.bin` 坏点表、光学黑钳位（`MasterBlackLevelMeta`、`RchBlackLevel`、`BchBlackLevel`）与阴影校准（`CheckSetShadingCorrection` / `setShadingCorrection`）。
- **`Backup.bin` (`0x00fa0080`) Bank-1 `p2` 校准分区只读锁**：
  - FX3（`819` 子系统）：`\defdet.bin` 位于 `p2` DDR `0x809479000`（`5 MiB`），`\psd.bin` 位于 `p2` DDR `0x808730000`（`5 MiB`）。
  - FX6（`840` 子系统）：`\defdet.bin` 位于 `p2` DDR `0x80948d000`（`5 MiB`），`\psd.bin` 位于 `p2` DDR `0x808810000`（`5 MiB`）。
  - 审计强制要求 FX3 Stock `cpapp-b.bin` 仅以只读方式加载**本机自身 `p2:/setting/psd.bin` 与 `defdet.bin`**（`sensor_cal_p2_writes_permitted == False`、`sensor_cal_mutation_bytes == 0`），严禁替换为 FX6 供体校准文件或写入 `p2`。

### 2. Dual-Base ISO `800 / 12800`（LCG / HCG）与 `Cine EI` 管线
- **`appFw.so` / `cpapp-b.bin` / `libmpr.so` 实证符号**：
  - FX3 `appFw.so`（`79,015,712 B`）与 FX6 `appFw.so`（`50,520,424 B`）均具备 `BASE_ISO_LOW_800`、`BASE_ISO_HIGH_12800`、`FLEXIBLE_ISO`、`CINE_EI_QUICK`、`extern_BKID_APP_EXTERN_BASE_ISO`、`convert_MODE_ID_BASE_ISO_SET`。
  - `cpapp-b.bin` 暴露 `HCG`、`HyperGainMode` / `CheckSetHyperGainMode`（FX3）与 `uc_HighGainMode` / `CheckSetHighGainMode` / `shocklessGainMode`（FX6）及 `ExposureIndexMeta`。
  - `libmpr.so`（FX3 `3,541` 导出 / `356` 导入；FX6 `4,271` 导出 / `497` 导入）写入 `ul_RecommendedExposureIndex` / `setMetaData_ExposureIndexRDD18`。
- **管线对齐结果**：`Cine EI`（`ISO 800` LCG `200..3200 EI`；`ISO 12800` HCG `3200..51200 EI`）、`Cine EI Quick`（在 `3200 EI` 自动切换 LCG/HCG）与 `Flexible ISO` 均可干净驱动 Stock FX3 `IMX510` 模拟增益，同时保持未烘焙全宽容度 `S-Log3` 写入 `M4ROOT/CLIP` 与 XML EI 元数据（`dual_base_iso_800_12800_hcg_aligned == True`）。

### 3. `S-Log3` / `S-Cinetone` / `709tone` 与 16 槽位 `.cube` 3D MLUT 管线
- **ISP 与 LUT 链路实证**：
  - `appFw.so` 通过 `/Private/Sony/PRO/LUT`（SD 卡 `/mnt/sd/PRIVATE/SONY/PRO/LUT/`）、`PID_SET_USER_LUT_BINARY_DATA`、`LUT_SETTING_INTERNAL_REC_MLUT_OFF/ON` 与 `LUT_SETTING_MONITOR_OUT_MLUT_OFF` 控制 LUT 加载与去烘焙隔离。
  - `libsencore.so`（FX3/FX6 均 `355` 导出 / `130` 导入，FX6 新增 `SET_MONITOR_MLUT`）、`libmpr.so`（`mpr::SetLutData`、`mpr::ExecuteSetLutData`、`mpr::GetCubeFilePath`）与 `cpapp-b.bin` 硬件 ISP 阶段（`MLUT_YC2RGB_ON`、`MLUT_L1D_A_ON`、`MLUT_MTX_A_ON`、`MLUT_EIGAIN_ON`、`MLUT_ASCCDL_ON`、`MLUT_L3D_ON`）完整对应，且 FX6 预置 `S709.cube`（`1,006,296 B`，`LUT_3D_SIZE 33`）验证通过。
- **防双烘焙与防 NVS 溢出**：`17^3` / `33^3` `.cube`（`1..16` 槽位）仅暂存至易失性 `/tmp/` / `ram://` 供 LCD/HDMI `MLUT` 监看；静默对 `S-Log3` 主文件启用机内烘焙（`LUT Burn-in`）被硬阻断（`slog3_double_bake_prevented == True`）。

### 4. `p2` / `p23` / `p30` NVS 写保护与 12 项 4 类兼容矩阵
- 写守卫仅放行 `/tmp/`、`ram://` 易失暂存与 `/mnt/sd/` 只读路径，硬阻断 `p2:/setting/{psd,defdet}.bin`、`p2:/Backup.bin`、`p23:/INFO/*`、`p30:/usr/data/lut/*` 及 `/dev/nflasha*`/`/dev/cnflasha*`/`/dev/mmcblk0*`（`persistent_emmc_writes_authorized == False`、`emmc_mutation_bytes == 0`）。
- 12 项 4 类（`NATIVE_PASSTHROUGH` / `SHIM_TRANSLATED` / `MASKED_ABSENT_HW` / `HARD_WRITE_PROTECTED`）色彩兼容矩阵全部闭环。

---

## 三、交付文件与验证命令

- 审计器模块：[`realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.py)
- 包导出与 CLI：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) · [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) · [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/README.md)
- 48 项双模式单元测试：[`test_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h168-phase156-realhw-imx510-dualbase-iso-lut-color/outputs/fx3-firmware-lab/tests/test_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline.py)

```sh
PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
