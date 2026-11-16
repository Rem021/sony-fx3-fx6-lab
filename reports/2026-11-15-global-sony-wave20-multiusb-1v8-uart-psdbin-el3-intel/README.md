# Wave-20 全球索尼 BIONZ XR 真机情报同步：`15-Pin Multi/Micro-USB` `1.8V UART` / `VMC-BNCM1` 引脚复用、`p2:/setting/psd.bin` (`FinalFormat.bin`) 传感器标定与 `CXD90057` EL3 串口冷恢复边界

## 1. 核心结论（结论先行）
- **实测/公开逆向交叉验证（Wave-20 实时检索同步）**：
  1. **`15-Pin Multi/Micro-USB` 物理引脚与 `1.8V CMOS UART` / `VMC-BNCM1` 电气互斥**：
     - 索尼官方维修手册 `15-Pin Multi/Micro-USB` 定义中，Pin 8 为 `UART TX / LANC_SIG`、Pin 9 为 `UART RX`（Boot Serial Input）、Pin 7 为 `XRESET_REQ`、Pin 10 为 `AD_JACK_IN`（电阻分压附件识别 ID）、Pin 12/13 为 `LOUT/V_LINE_OUT`（SMPTE-12M LTC 时码模拟输入通路）。
     - 在 `ILME-FX3`（`CXD90057` *Mira* + `CXD90058` *Cetus* 双 BIONZ XR 架构）上，SoC 原生调试串口运行于 **`1.8V CMOS` 电平**（严禁直连 `3.3V/5V` TTL 串口线，且严禁在机身断电 `VCC=0V` 时由宿主机 `TX` 倒灌电流）。
     - 当插入索尼官方 **`VMC-BNCM1`（维修料号 `A-5051-506-A`）** 或第三方 `Deity C23` / `Tentacle C24` LTC 时码线时，`AD_JACK_IN`（Pin 10）通过特定识别电阻将复用通道切入 `TC-IN`（屏幕显示 `EXT-LK`，输入 `0.5V–4.5V p-p` SMPTE-12M 信号）。因此台架严禁通过分线器同时挂载 `Multi-USB 1.8V UART` 与 `VMC-BNCM1`（已由 `Phase 155` Pillar 20 与 `Phase 158` Gate `G49` 闭环拦截）。
  2. **`p2:/setting/psd.bin`、`defdet.bin` 与 `p18:/lens` `LENSFILE.BIN` 单机唯一标定红线**：
     - 公开 BIONZ XR 维修与固件研究确认：`/setting/psd.bin` 与索尼售后更换传感器组件附带的工厂标定光盘 `FinalFormat.bin`（如组件 `A-5012-098-A`）具有同源头部与尺寸，存储**单机唯一传感器暗电流/阴影（Pixel Shading）标定表**；`defdet.bin`（`DEFDET`）存储单颗 `IMX510` CMOS 坏点/热噪点补偿坐标；`p18:/lens` 下的 `LENSFILE.BIN`（`262,592 B`）承载 E 卡口 `VX...` 镜头像差与对焦马达参数表。
     - **真机工程铁律**：严禁跨机身或跨机型（FX6 -> FX3）覆盖 `p2:/setting/psd.bin`、`defdet.bin` 或 `p18:/lens/LENSFILE.BIN`；所有 Stage-B 运行态必须对 `p2` 与 `p18` 保持只读保护（已纳入 `Phase 146`、`Phase 156`、`Phase 158` Gate `G50` 与 `Round 32`）。
  3. **三级硬件救砖梯度（USB `054C:0DA1/0336` -> SD `47 µs` 逃生舱 -> `CXD90057` BootROM EL3 / `8-bit` eMMC ISP）**：
     - 常规 USB 枚举覆盖 `054C:0DA3`（PTP/MTP/Remote）、`054C:0DA1`（Mass Storage 入口）与 `054C:0336`（Vendor Class `0xFF` Jiritsu 服务态）。
     - 公开研究（`DavidBuchanan314/ILCE-7M4-RE` / `Sony-ILCE-7M4-Linux`）记录了 `CXD90057` 冷启动 BootROM 在 Multi-USB 串口上的 EL3（`0xfe020000`）串行引导接收机制以及 `SPAcc` 分区透明加解密机制，与本实验室 `Phase 151` 的 `pnflasha*`（原始 ISP 密文）vs `cnflasha*`（SPACC 明文）双层冷备金库完全吻合。
- **实测事实 vs 未执行物理真机边界**：
  - 上述二进制结构、`O_RDONLY` 本地 donor 校验与 FX3 `7.02`（`4.9.337-scel+`）ARM64 QEMU 演练均已在离线/仿真环境实测闭环；**尚未连接真实物理 FX3 相机执行 USB/SD 写入**（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`physical_usb_packets_emitted = 0`）。

## 2. 对齐的实验室模块链接
- 台架被动预检与 USB 分类器：[realhw_bench_preflight_and_usb_classifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py)
- 双层 `pnflasha/cnflasha/mtd0ro` Tier-0 冷备金库：[realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/outputs/fx3-recovery-adapter/fx3_recovery/realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.py)
- 48 门安全护栏（正升级至 50 门）：[realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/outputs/fx3-safety/fx3_safety/realhw_pnflasha_mtdro_rfnvs_and_48gate_guard.py)
- 真机部署权威手册：[REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/oarfish/docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)
