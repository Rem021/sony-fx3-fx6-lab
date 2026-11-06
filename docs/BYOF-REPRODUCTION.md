# Bring Your Own Firmware (BYOF) & Environment Reproduction Guide / 固件自备与环境复现指南

**[English](#english-guide) | [简体中文](#简体中文指南)**

---

# English Guide

This repository open-sources 100% of our self-developed QEMU AArch64 hardware emulation patches, kernel & userland compatibility shims (CP helper, CAPID pre-init, GRM/FrameBuffer shims), browser-based interactive menu emulator, static/dynamic reverse-engineering scripts, offline recovery tools, and technical audit reports for **Sony ILME-FX3 (Ver. 7.02, Model `0x91030080`)** and **Sony ILME-FX6 (Ver. 6.01, Model `0x91040086`)**.

To comply with copyright laws and GitHub file size limits, **no proprietary Sony firmware binaries (`BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `nflasha*` partition images, or 453 MB `.cpio` archives) are distributed in this repository**. Researchers can reproduce the entire environment by extracting the official Sony firmware update packages and verifying their exact SHA-256 digests against the tables below.

## 1. Official Firmware Reference Digests (SHA-256)

### 1.1 Sony ILME-FX3 Ver. 7.02 (`0x91030080`)

| Component / Path | Size (Bytes) | SHA-256 Digest | Role & Description |
| :--- | ---: | :--- | :--- |
| `nflasha3/vmlinux.bin` | `6,610,952` | `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` | Official FX3 Linux `4.9.337-scel+` AArch64 kernel image (default VM kernel) |
| `0800_appli/setting/cxd90057.dtb` | `16,875` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | CXD90057 main system Device Tree Blob (100% identical to FX6) |
| `0300_partconf/partinf.conf` | `3,999` | `3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189` | FX3 30-partition geometry table (written to eMMC UDA Sector 0) |
| `0750_nor_loader/loader_nor.bin` | `101,888` | `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942` | FX3 Octal-SPI NOR bootloader |
| `pformat_config.txt` | `1,274` | `21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece` | SPI NOR physical sector layout config (100% identical to FX6) |
| `LdrBkupList.txt` | `650` | `ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88` | 65 Loader Backup key list (100% identical to FX6) |
| `libsdfileinputupdaterapi.so` (`p1`) | `60,584` | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` | FX3 `p1` recovery partition update verification library |
| `libupdatercorecommon.so` (`p1`) | `72,864` | `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74` | FX3 `p1` core updater common library |

### 1.2 Sony ILME-FX6 Ver. 6.01 (`0x91040086`)

| Component / Path | Size (Bytes) | SHA-256 Digest | Role & Description |
| :--- | ---: | :--- | :--- |
| `nflasha3/vmlinux.bin` | `6,582,280` | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | Official FX6 Linux `4.9.337-scel+` AArch64 kernel image |
| `nflasha3/initrd.img` | `5,661,696` | `fc97d08139b9ec20a1a511e608f6ed4f55d71f204472467463fdc181d2973da6` | FX6 main system initrd (ext2) |
| `0400_updater/dev/nflasha1` | `16,684,032` | `2a32ea4db3c7cabc5daad3b4e015acbc3c277ac38148b253f241c9c31d456786` | FX6 Updater partition image (FAT16) |
| `nflasha1/boot/initrd.img` | `6,914,048` | `5032fc777296e3e1f1b3bb6c7f2f249f18ee135f3c2424f83b7b6fff1e5831c0` | FX6 Updater initrd |
| `0800_appli/setting/cxd90057.dtb` | `16,875` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | CXD90057 main system Device Tree Blob (100% identical to FX3) |
| `0300_partconf/partinf.conf` | `3,990` | `e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9` | FX6 30-partition geometry table (includes `p20` LUT & `p21` opelog) |
| `0700_part_image/dev/nflasha3` | `31,780,864` | `a78c28d835b0cc9c3105332d82f7f404e319d3bf289146935482fd0c887c9b02` | FX6 `/system` partition image (FAT16) |
| `0700_part_image/dev/nflasha5` | `202,677,056` | `d33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1` | FX6 `/wbi` Warm Boot Image snapshot |
| `0700_part_image/dev/nflasha8` | `22,726,656` | `7fbf12865eef11ea4db2d822af88deb0b95e565d10dbf80eee31f23689858315` | FX6 `/cp` TOPPERS co-processor firmware partition image |
| `0700_part_image/dev/nflasha15` | `445,843,456` | `c62b1775a2fe36669b644a55cac7eab9ce2636e6fb8469cbf791d00b8ed6fc6a` | FX6 `/usr` application & kernel module partition image (ext2) |
| `0700_part_image/dev/nflasha23` | `67,108,864` | `f6dc4a6325652b0650074f23e4facdc7bb51ea1e39fccd119b2e67f7d15713aa` | FX6 `/PMBP` partition image |
| `usr/lib/libgrm.so` (donor) | - | `0f9f922664ad23813fec3f2466d8f453a8741af11be9627583712b752cea9d2b` | FX6 GRM graphics resource manager library |

## 2. Step-by-Step Build & Reproduction Workflow

1. **Build the Patched `qemu-system-aarch64` Binary**:
   - Apply [outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch](../outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) and the hardware model patches under `work/fx3-vm-20261101/host/patches/` (mapping High DDR at `0x400000000`, ESRAM mailbox at `0xfe005000`, Sony timer, SCU request, and GPIO Bank5).
   - Build scripts and provenance metadata are provided in `work/fx3-vm-20261101/host/configure_native.py` and `outputs/fx3-vm/metadata/build-provenance.json`.
2. **Assemble the FX3 Interactive Menu VM CPIO**:
   - Compile the AP70–AP105 runtime helpers in `work/fx3-vm-20261101/menu-repair-01/runtime/` using Zig (`aarch64-linux-gnu`) or an AArch64 GCC toolchain, and pack them with your extracted FX3 rootfs into the guest CPIO.
   - Launch via [outputs/fx3-vm-trial/FX3菜单.command](../outputs/fx3-vm-trial/FX3菜单.command).
3. **Assemble the FX6-on-FX3 Hybrid CPIO (`grmreal*`)**:
   - In `work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/`, use the `build_*_cpio.py` scripts to combine `fx6-cp-backup-sync100-agnostic.c`, `capid-preinit/`, `grm-fbinit/`, and your extracted FX6 userland library closure (`nflasha15-files/lib/*`) into `guest-hybrid-fx6kernel-capid-grmreal*.cpio`.
   - Validate all SHA-256 hashes with `run_gpecap9_once.py --check` before executing `--run`.

---
---

# 简体中文指南

本仓库 100% 开源了围绕 **Sony ILME-FX3 (7.02, Model `0x91030080`)** 与 **Sony ILME-FX6 (6.01, Model `0x91040086`)** 的全部自研模拟器补丁、内核/用户态兼容垫片（Shims/Helpers）、网页交互前端、静态/动态逆向分析脚本、恢复适配工具以及全阶段核查报告。

出于版权合规与 GitHub 文件体积限制，**本仓库不包含任何索尼原厂闭源二进制文件（如 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`nflasha*` 分区镜像或打包后的 453MB `.cpio` 根文件系统）**。研究者可使用官方固件升级包按上表中的 SHA-256 指纹自行提取并复现：

1. **构建定制 QEMU (`qemu-system-aarch64`)**：
   - 使用上游 QEMU 源码，应用 [outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch](../outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) 及 `work/fx3-vm-20261101/host/patches/` 下的设备模型补丁（映射 `0x400000000` 高位 DDR、ESRAM 邮箱、Sony 定时器、SCU 请求与 GPIO Bank5）。
   - 编译脚本参见 `work/fx3-vm-20261101/host/configure_native.py` 与 `prepare_sources.py`。
2. **构建 FX3 菜单模拟器运行环境**：
   - 使用 `work/fx3-vm-20261101/menu-repair-01/` 下的 AP70–AP105 辅助模块源码（通过 Zig 或 AArch64 交叉工具链编译为 `.so` / `.ko`），注入自备的 FX3 根文件系统 CPIO。
   - 运行 [outputs/fx3-vm-trial/FX3菜单.command](../outputs/fx3-vm-trial/FX3菜单.command) 或 `work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r10-independent-diagnostics/run_trial_v25_diag_r3.py`。
3. **构建 FX6-on-FX3 混合启动候选 CPIO**：
   - 在 `work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/` 中，使用 `build_*_cpio.py` 将地址无关 CP helper（`fx6-cp-backup-sync100-agnostic.c`）、CAPID 预初始化（`capid-preinit/`）、GRM/FrameBuffer 垫片（`grm-fbinit/`）与自备的 FX6 用户态库闭包打包生成 `guest-hybrid-fx6kernel-capid-grmreal*.cpio`。
   - 使用 `run_gpecap9_once.py --check` 校验 SHA-256 清单后执行单次受控运行。
