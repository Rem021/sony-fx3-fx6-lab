# Phase 164 — 第 34 号统一固件审计器 (`34/34`)：`CXD90057` (`Mira`) + `CXD90058` (`Cetus`) 双 BIONZ XR 芯片间 IPC、`sabin` 32 位 SA-DSP 微码与 `XAVC-I / HEVC` 硬件编码器边界审计

> **结论**：已完成第 34 号统一固件审计器 [`realhw_cxd90057_cxd90058_sabin_codec_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cxd90057_cxd90058_sabin_codec_auditor.py) 及其 48 项双模单元测试，并接入 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) `audit-all` (`34/34`)。全部 19 份本地 Sony `FX3 v7.02` 与 `FX6 v6.01` 供体二进制均严格通过 `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ` 只读验证，未对任何相机闪存或物理实机执行写入/烧录。

---

## 一、已实测的 `O_RDONLY` 供体静态审计事实（Local Donor Mode）

- **单次运行耗时与报告摘要**：
  - Local Donor 模式（`LOCAL_DONOR_VERIFIED`）：`< 0.65 s`，`all_checks_passed = True`，`report_sha256 = 2064a163366098608a9c7572102d192344d1c1662332d972107777b04459b247`。
  - Clean-Room 模式（`CLEAN_ROOM_SYNTHETIC` / `FX3_FX6_FORCE_CLEAN_ROOM=1`）：`~0.012 s`，`all_checks_passed = True`，`report_sha256 = 7bfd4c77d65bed3fe52595b2455623fadfe55696d8ee8f85818e87ada0278420`。
  - 写权限硬锁：`cxd90058_fw_mutation_bytes = 0`、`cp_mutation_bytes = 0`、`sabin_microcode_mutation_bytes = 0`、`emmc_mutation_bytes = 0`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`。

### 四大审计支柱实测结果

1. **Pillar 1 — `CXD90057` (`Mira`) <-> `CXD90058` (`Cetus`) 双 SoC 启动与 PCIe / SLVS-EC 不变性**
   - `7.02-setting-cxd90057.dtb`（`16,875 B`）：验证 FDT 魔数 `0xd00dfeed` 及 `sony,cxd90057`、`cxd90057,pci32`、`snps,dw-pcie`、`cxd900xx-pcie-ep`、`pcie_{i,m0,m1,c}`、`axi2avb_pcie{0,1}` 设备树节点。
   - `nflasha7/sbin/initrc/insmod_drv2`（`1,298 B`）：确认依次加载 `pciedma.ko`、`pci_ep_cp.ko`、`pci_ep_zq.ko`、`pcieatu.ko`、`osal_uipc.ko`、`pcie-if.ko`、`dmm.ko`、`codec_drv.ko`。
   - 内核模块与 CP 固件：`pci_ep_cp.ko`（`6,496 B`）含 `pci:v00001556d00001100`、`pci_ep_cp_probe`、`pcidma_connect`；`pcie-if.ko`（`65,136 B`）含 `PCIEIF_EPAR`、`PCIeDMAC`；FX3（`15,980,568 B`）与 FX6（`17,952,816 B`）`cpapp-b.bin` 均存在 `CetusSlvsecDriver` / `CetusSlvsecLink` / `CetusSlvsecMphy`；FX3/FX6 `Backup.bin`（`2,229,740 B` / `2,253,333 B`）均为完整 `BK4\x00` 容器头。
   - 路线裁决：仅放行 **Route-1 Hybrid Userland Stage-B**（`p8 cpapp-b.bin` 与 `CXD90058` 固件 0 字节改写），Fail-Closed 拦截 Route-2 `p8` 刷写及 PCIe EP ID 失配。

2. **Pillar 2 — `sabin` 32 位 SA-DSP 微码与 `DmmCfg.bin` 内存池对齐**
   - 全部 **34/34** `/usr/sabin/*.bin` 微码与字典路径在 FX3 与 FX6 `cpapp-b.bin` 中 100% 一致存在。
   - `sa_sabin_cp_cam_post.bin`（`1,921,536 B`）头部实测为 `SP\x01\x00`（`53500100`）；`codec_drv.ko`（`19,216 B`）包含 `bdrv_driver.c` / `bdrv_uipc.c` / `EXTERNAL_CODEC_DRIVER_LOAD_FIRM` / `bdrv_uipc_send_sync_msg`。
   - `DmmCfg.bin`：FX3（`66,796 B`，`603` units / `290` rules）与 FX6（`59,364 B`，`556` units / `259` rules）均覆盖全 20 个 `MAIN` 录像单元 ID 且 `max_extents_per_unit <= 8`（满足 `libmpr.so` `0xa8` 栈回复上限），经用户态 `LD_PRELOAD` 翻译而不直接刷写 FX6 `DmmCfg.bin`，同时拦截 `> 8` extents 溢出与 `5016x3344` Open-Gate 池分配。

3. **Pillar 3 — `XAVC-I / HEVC` 硬件编码队列边界与 `16-bit SDI RAW` (`mew.bin` FPGA) 屏蔽**
   - `libmpr.so`（FX3 `3,517,008 B` / `3,541` exports vs FX6 `28,921,824 B` / `4,271` exports）与 `libsencore.so`（FX3 `377,328 B` vs FX6 `401,952 B`，均为 `355` exports）共享 `AVC480_4096_2160_H422IP`、`AVC480_3840_2160_H422IP`、`AVC_3840_2160_H422IP`、`HEVC_3840_2160_M42210P`、`HEVC_3840_2160_M10P`、`SetMovieRecParam`、`ExecEncOpen`、`ExecEncClose`。
   - Stage-B `LD_PRELOAD` 将 FX6 `SELECT_CODEC_XAVC_I`（MXF Class 300/480 `4K DCI / QFHD` `10-bit 4:2:2` `23.98p..119.88p`）与 `SELECT_CODEC_XAVC_L` 经 `MP4` 封装垫片映射至 FX3 原生硬件队列，直通 `XAVC S-I`、`XAVC HS`（`HEVC 10-bit 4:2:2`）与 `HDMI 16-bit RAW`（`4264x2408`）。
   - `1010_spi/mew.bin`（`6,692,572 B`）确认为 Xilinx FPGA 比特流（偏移 `0x20` 总线宽探测 `000000bb11220044`，偏移 `0x30` 同步字 `aa995566`）；`MoniFpgaSdi` / `SetRegSDIOutFormat` / `MoniFpgaAnalog_OutputSelect` 在 FX6 `cpapp-b.bin` 均有命中而在 FX3 `cpapp-b.bin` 中全为 `0`。审计确认通过 `SDI_OUTPUT_NOT_SUPPORT` 优雅屏蔽 `SDI RAW`（`mew.bin`）与 `5016x3344 X-OCN LT` 路径，`appfw_crash_prevented = True`。

4. **Pillar 4 — 非易失性写防火墙与 12 触点 4 类兼容矩阵**
   - 仅放行 `/tmp/`、`ram://`、`memfd:` 与外置 `/mnt/sd/`、`/mnt/sd2/`；硬拦截 `p8:/cpapp-b.bin`、`/usr/sabin/*`、`spi_nor:/mew.bin`、`p2:/Backup.bin`、`p15:/usr/*`、`/setting/DmmCfg.bin` 及 `/dev/nflasha*` / `/dev/cnflasha*` / `/dev/mmcblk0*`。
   - 12 触点 4 类兼容矩阵（`P164-01..P164-12`）：`NATIVE_PASSTHROUGH = 5`、`SHIM_TRANSLATED = 3`、`MASKED_ABSENT_HW = 2`、`HARD_WRITE_PROTECTED = 2`。

---

## 二、验证结果与产物索引

| 验证项目 | 命令 | 实测结果 |
|---|---|---|
| Phase 164 专项单测（Local Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_cxd90057_cxd90058_sabin_codec.py -v` | 48 passed, 0 skipped (`< 0.8 s`) |
| Phase 164 专项单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_cxd90057_cxd90058_sabin_codec.py -v` | 48 ran (`test_43` clean-room skip), 0 failed |
| `outputs/fx3-firmware-lab` 全量单测（Local Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | **1,162 tests passed** (`43.370 s`) |
| `outputs/fx3-firmware-lab` 全量单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | **1,162 tests passed** (3 local-only donor skipped, `21.067 s`) |
| 仓库洁净室卫生与 BYOF 检查 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 2.59s`（无未跟踪二进制/字节码泄漏） |

- 审计器模块：[`realhw_cxd90057_cxd90058_sabin_codec_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cxd90057_cxd90058_sabin_codec_auditor.py)
- 包导出与 CLI：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) · [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) · [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/README.md)
- 48 项双模单元测试：[`test_realhw_cxd90057_cxd90058_sabin_codec.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h178-phase164-cxd90057-cxd90058-sabin-codec/outputs/fx3-firmware-lab/tests/test_realhw_cxd90057_cxd90058_sabin_codec.py)

---

## 三、尚未执行的物理真机实验台架动作（Pending Real-Camera Bench Actions）

以下环节均**未在本阶段执行**（本工作流仅完成了离线只读供体二进制审计与洁净室回归）：
1. 在真实 `ILME-FX3` 机身台架上挂载 Stage-B 用户态运行 `XAVC-I 4K DCI / QFHD` `59.94p / 119.88p` 与 `XAVC HS 10-bit 4:2:2` 长时实录，并用 `dmesg` / `osal_uipc` 日志复核 `CXD90057 <-> CXD90058` PCIe/SLVS-EC 零超时。
2. 在实机菜单切换至 FX6 独占 `SDI RAW` 入口时实测 `LD_PRELOAD` 对 `appFw.so` 的屏蔽响应与无崩溃回退行为。
3. 在物理热电偶与 CFexpress Type A VPG200/400 介质上实测 `sa_sabin_cp_cam_post.bin` 帧池峰值带宽与媒体最终封口（`.MP4` 无 `.RSV` 残留）。
