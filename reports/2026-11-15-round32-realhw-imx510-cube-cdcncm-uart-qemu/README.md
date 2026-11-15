# Round 32：FX3 7.02 原厂内核真机准备实跑（Part 11）— `IMX510` 双原生 ISO `800/12800`、`p2:/setting` `EROFS` 锁、`.cube` 3D MLUT 防双重烘焙、`CDC-NCM`/`054C:0DA1` 与 `1.8V ttyAMA0` 六阶段诊断

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r32a` / `r32b` / `r32c`）测得；**物理实体 FX3 相机机身尚未上电接入执行实机板级联调**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r32a` / `r32b` / `r32c`）

| 实跑场景 | Run ID | `r32_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **32A：`IMX510` 双原生 ISO + `p2:/setting` `EROFS` + `.cube` 3D MLUT + Big-6** | `r32a-imx510-cube-big6-schinese` | `imx510_cube_big6` | `psd.bin` & `defdet.bin` `O_RDWR -> EROFS (errno=30)`（`sensor_cal_sha256_match=1`）· `libsencore.so` `dlopen/dlsym` + `IMX510` `ISO 800 LCG <-> 12800 HCG` (`imx510_dual_base_ok=1`) · `17x17x17` `.cube -> /tmp/mlut_slot0.bin` (`58,972 B`, `mlut_baked_into_master=0`) · `NaN .cube` 故障闭门拦截 (`bad_cube_rejected=1`) | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.32s` | [`r32a-imx510-cube-big6-schinese-composited.png`](assets/r32a-imx510-cube-big6-schinese-composited.png) |
| **32B：零差异共享库 `dlopen/dlsym` + `p12/p13` `EROFS` + `CDC-NCM -> 054C:0DA1`** | `r32b-cdcncm-usb-0da1` | `cdcncm_usb_0da1` | 4 个零差异库真机 ARM64 `dlopen_libs_ok=4` / `dlsym_resolved=8`（`libInfraMscServer.so`、`libUsbControl.so`、`libWlanAdjust.so`、`libWlanResource.so`）· `p12/p13` RF NVS `EROFS (errno=30)` (`rf_nvs_writes=0`) · `/dev/ttyAMA3` 零阻塞 (`bt_wait_ms=0`) · `CDC-NCM (1000 Mbps)` -> `054C:0DA1` (`usb_0da1_intact=1`, `usb_0336_preserved=1`) | 早期共享库与 USB 恢复验证退出 | 跳过（共享库/`CDC-NCM` 恢复验证后停机） | **`0`** / **`0`** / **`0`** | `5.31s` | — |
| **32C：`1.8V ttyAMA0 (460800 8N1)` 六阶段遥测 + `VMC-BNCM1` / 过压熔断** | `r32c-uart-6stage-triage` | `uart_6stage_triage` | `4.9.337-scel+` + `/dev/ttyAMA0` 6 个结构化启动检查点全通过 (`checkpoints_passed=6`) · `VMC-BNCM1` 脚位争用注入故障闭门中止 (`vmc_bncm1_contention_aborted=1`, `rc=-16`) · `3.3V (>1.95V)` 过压注入闭门中止 (`uart_overvoltage_aborted=1`, `rc=-34`) | 早期 UART 六阶段诊断退出 | 跳过（UART 六阶段与过压门禁验证后停机） | **`0`** / **`0`** / **`0`** | `4.87s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `IMX510` 双原生 ISO、`p2:/setting` `EROFS` 与 `.cube` 3D MLUT 非烘焙（`r32a`）
```text
FX6_R32_IMX510_CUBE_INIT psd_erofs=1 psd_errno=30 defdet_erofs=1 defdet_errno=30
  sensor_cal_sha256_before=4c2c1b59048422076f4db269ad022849581783c3aa8975eaf4460522f20678b0
  sensor_cal_sha256_after=4c2c1b59048422076f4db269ad022849581783c3aa8975eaf4460522f20678b0
  sensor_cal_sha256_match=1 mlut_lut_size=17 mlut_entries=4913 mlut_slot0_loaded=1
  mlut_slot0_bytes=58972 mlut_baked_into_master=0 bad_cube_nan_detected=1
  bad_cube_rejected=1 slot0_untouched_on_bad_cube=1 sencore_elf_ok=1 appfw_elf_ok=1
  emmc_write_count=0 r32_init_ok=1

FX6_R32_IMX510_CUBE_BRIDGE sensor=IMX510 imx510_lcg_iso=800 imx510_hcg_iso=12800
  imx510_readout_us=8700 imx510_dual_base_ok=1 sencore_dlopen_ok=1 sencore_dlsym_ok=1
  p2_psd_erofs=1 p2_defdet_erofs=1 sensor_cal_erofs_ok=1 mlut_slot0_active=1
  mlut_lut_size=17 mlut_baked_into_master=0 slog3_xavc_master_clean=1
  emmc_write_count=0 r32_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028 -> 0x718c`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`。

### 2.2 4 个零差异共享库 `dlopen/dlsym`、`p12/p13` `EROFS` 与 `CDC-NCM -> 054C:0DA1`（`r32b`）
```text
FX6_R32_CDCNCM_USB_0DA1 dlopen_libs_ok=4 dlsym_resolved=8 zero_diff_libs_ok=1
  rf_nvs_erofs_ok=1 rf_nvs_writes=0 rf_nvs_p12_errno=30 rf_nvs_p13_errno=30
  bt_ttyama3_masked=1 bt_wait_ms=0 bt_probe_us=23
  usb_cdcncm_link_mbps=1000 usb_ptp_ip_port=15740 usb_cdcncm_tested=1
  usb_vid=0x054c usb_msc_pid=0x0da1 usb_service_pid=0x0336
  usb_0da1_intact=1 usb_0336_preserved=1 emmc_write_count=0 r32b_ok=1 verify_us=15002
```
- 在 FX3 `7.02` 原生运行时（预载 `libosal_uipc.so` 与 `libMWF.so` 全局符号后），真实 `/lib/ld-2.25.so` 成功对 `/usr/lib/libInfraMscServer.so`、`libUsbControl.so`、`libWlanAdjust.so`、`libWlanResource.so` 完成 `dlopen` 与 `8/8` `dlsym` 符号解析；`p12/p13` RF NVS 返回 `EROFS (errno=30)`；`/dev/ttyAMA3` 零阻塞（`bt_wait_ms=0`）；`CDC-NCM` 切回 `Mass Storage (054C:0DA1)` 与 `SERVICE (054C:0336)` 完好无损。

### 2.3 `1.8V ttyAMA0 (460800 8N1)` 六阶段控制台遥测与 `VMC-BNCM1` / 过压中止（`r32c`）
```text
FX6_R32_UART_CP stage=1 name=IPL_BL2 baud=460800 framing=8N1 logic_mv=1800
FX6_R32_UART_CP stage=2 name=KERNEL_4_9_337_SCEL release=4.9.337-scel+ baud=460800 framing=8N1 logic_mv=1800
FX6_R32_UART_CP stage=3 name=SETUP_NFLASH devtmpfs_rc=0 baud=460800 framing=8N1 logic_mv=1800
FX6_R32_UART_CP stage=4 name=STAGE_A_47US_DLOPEN trigger_us=47 baud=460800 framing=8N1 logic_mv=1800
FX6_R32_UART_CP stage=5 name=STRATEGY_A_MOUNT ro_guards=1 baud=460800 framing=8N1 logic_mv=1800
FX6_R32_UART_CP stage=6 name=STAGE_B_APPFW_BIG6 sid=0x0a baud=460800 framing=8N1 logic_mv=1800
FX6_R32_UART_6STAGE kernel_release_ok=1 cmdline_ttyama0_ok=1 uart_device=/dev/ttyAMA0
  uart_baud=460800 uart_framing=8N1 uart_logic_mv=1800 uart_max_safe_mv=1950
  checkpoints_passed=6 uart_nominal_ok=1 vmc_bncm1_contention_aborted=1 vmc_bncm1_abort_rc=-16
  uart_overvoltage_injected_mv=3300 uart_overvoltage_aborted=1 uart_overvoltage_abort_rc=-34
  emmc_write_count=0 r32c_ok=1 verify_us=1536
```

---

## 3. `r32a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r32a` Alpha（`26.21 KiB` / `26,842 B`） | `r32a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r32a Big6 Alpha](assets/r32a-imx510-cube-big6-schinese-alpha.png) | ![r32a Big6 Composited](assets/r32a-imx510-cube-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目仅能在物理 Sony ILME-FX3 相机上执行，**本次未运行**：
1. 物理相机实拍下 `IMX510` 传感器于 `ISO 800 (LCG)` 与 `ISO 12800 (HCG)` 切换时的实感动态范围、暗电流及 XAVC `S-Log3` 母版与监视 LUT 分离校验。
2. 物理相机 Type-C 端口实插 `CDC-NCM` 千兆网卡（`RTL8153` / `AX88179`）联调 `Monitor & Control`（`PTP-IP TCP/15740`）后退回 `Mass Storage (054C:0DA1)` 的实体总线枚举。
3. 物理相机 Multi-USB `Pins 7/8/9` 接入 `1.8V` 串口转接器在 `460800 8N1` 下读取上电 `BL2 -> Kernel -> Stage-B` 实机波形与 `VMC-BNCM1` 物理拔插互锁验证。

---

## 5. 复现命令与洁净室合规

```bash
# Run 32A: IMX510 Dual-Base + p2:/setting EROFS + 17^3 .cube MLUT + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 32 --r32-mode imx510_cube_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r32a-imx510-cube-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r32-runs/r32a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r32a-imx510-cube-big6-schinese \
  --export-png-dir reports/2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu/assets

# Run 32B: Zero-Diff Shared Libraries dlopen/dlsym + p12/p13 EROFS + CDC-NCM -> 054C:0DA1 Recovery
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 32 --r32-mode cdcncm_usb_0da1 --lang en --run-id r32b-cdcncm-usb-0da1 \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r32-runs/r32b

# Run 32C: 1.8V ttyAMA0 (460800 8N1) 6-Stage Telemetry + VMC-BNCM1 / >1.95V Overvoltage Abort
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 32 --r32-mode uart_6stage_triage --lang en --run-id r32c-uart-6stage-triage \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r32-runs/r32c

# Dual-Mode Unit Tests & Clean Audit
PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
