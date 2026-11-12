# Bring Your Own Firmware (BYOF) & Environment Reproduction Guide / 固件自备与环境复现指南

**[English](#english-guide) | [简体中文](#简体中文指南)**

---

# English Guide

This repository open-sources 100% of our self-developed QEMU AArch64 hardware emulation patches, kernel & userland compatibility shims (CP helper, CAPID pre-init, GRM/FrameBuffer shims, native presenter closure harness), browser-based interactive menu emulator, deterministic offline binary adaptation & Unicorn verification suite, `p1`/`boot0`/`boot1` offline recovery tools, and technical audit reports for **Sony ILME-FX3 (Ver. 7.02, Model `0x91030080`)** and **Sony ILME-FX6 (Ver. 6.01, Model `0x91040086`)**.

To comply with copyright laws and GitHub file size limits, **no proprietary Sony firmware binaries (`BODYDATA.DAT`, `vmlinux.bin`, `appFw.so`, `nflasha*` partition images, or `.cpio` rootfs archives) are distributed in this repository**. Researchers can reproduce every track from clean source by extracting official Sony firmware update packages and verifying exact byte sizes and SHA-256 digests with `make verify-byof` (`scripts/verify_byof_manifest.py`).

## 1. Official Firmware Reference Digests (SHA-256)

### 1.1 Sony ILME-FX3 Ver. 7.02 (`0x91030080`) & `2.04`/`2.05` Recovery Engine

| Component / Path | Size (Bytes) | SHA-256 Digest | Role & Description |
| :--- | ---: | :--- | :--- |
| `nflasha3/vmlinux.bin` | `6,610,952` | `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` | Official FX3 Linux `4.9.337-scel+` AArch64 kernel image (default VM & Bank 0 kernel) |
| `0800_appli/setting/cxd90057.dtb` | `16,875` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | CXD90057 main system Device Tree Blob (100% identical to FX6) |
| `nflasha1/boot/cxd90057.dtb` | `17,131` | `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca` | CXD90057 `p1` updater Device Tree Blob (100% identical to FX6) |
| `0300_partconf/partinf.conf` | `3,999` | `3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189` | FX3 30-partition geometry table (written to eMMC UDA Sector 0; max `p19`) |
| `0750_nor_loader/loader_nor.bin` | `101,888` | `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942` | FX3 Octal-SPI NOR bootloader |
| `pformat_config.txt` | `1,274` | `21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece` | SPI NOR physical sector layout config (100% identical to FX6) |
| `LdrBkupList.txt` | `650` | `ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88` | 65 Loader Backup key list (100% identical to FX6) |
| `nflasha8/tomco.txt` | `710` | `42f1785422bce152dbb21c4e82f42dd4b053a1729c7694e54b7cc9f118592722` | FX3 runtime CP RTOS load manifest (`cpapp-b.bin` @ `0xFC000000` + `11` sub-firmwares) |
| `updaterfs/cp/tomco.txt` | `618` | `d9401e6a7d0cdd85803e2a6823fd9dac0ff186910d82a5671f32fc0a37fc21f1` | FX3 updater CP RTOS load manifest (`udtrcp.bin`; 100% identical to FX6 updater) |
| `nflasha8/cpapp-b.bin` | `15,980,568` | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` | FX3 TOPPERS CP RTOS main firmware (`p8` `/cp`, preserved untouched on FX3 hardware) |
| `usr/bin/ud_send_lsi.elf` (`p1-initrd`) | `10,248` | `9fb4bd02b3434bd9fe8fb49fcf4359f7720b292506960ae0d9894332d3453c80` | `p1` updater SCU boot-mode dispatcher (`ioctl(fd, 0x804b0376, req)`; identical in FX6 `p1`) |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | FX3 factory Bk4 (`CX95900`) dual-bank Backup seed container (`6,994` keys) |
| `original-update-engine/2.04/nflasha1` | `19,377,152` | `e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67` | FX3 `2.04` official decrypted `p1` recovery reference image (`fx3_recovery`) |
| `original-update-engine/2.05/nflasha1` | `19,377,152` | `ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591` | FX3 `2.05` official decrypted `p1` recovery reference image (`fx3_recovery`) |
| `libsdfileinputupdaterapi.so` (`p1`) | `60,584` | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` | FX3 `p1` recovery partition update verification library |
| `libupdatercorecommon.so` (`p1`) | `72,864` | `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74` | `p1` core updater common library (100% identical in FX3 `2.04`/`2.05` & FX6 `p1`) |
| `usr/kmod/upm.ko` | `453,896` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | FX3 Ver. 7.02 `upm.ko` kernel module (`P9` `sub28` `CBZ X1` guard target) |

### 1.2 Sony ILME-FX6 Ver. 6.01 (`0x91040086`)

| Component / Path | Size (Bytes) | SHA-256 Digest | Role & Description |
| :--- | ---: | :--- | :--- |
| `nflasha3/vmlinux.bin` | `6,610,952` | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | Official FX6 Linux `4.9.337-scel+` AArch64 main system kernel image |
| `nflasha3/initrd.img` | `5,661,696` | `fc97d08139b9ec20a1a511e608f6ed4f55d71f204472467463fdc181d2973da6` | FX6 main system initrd (ext2) |
| `0400_updater/dev/nflasha1` | `16,684,032` | `2a32ea4db3c7cabc5daad3b4e015acbc3c277ac38148b253f241c9c31d456786` | FX6 Updater partition image (VFAT + `/boot/initrd.img` SquashFS + `/p1chksum`) |
| `nflasha1/boot/vmlinux.bin` | `6,582,280` | `58f595d53a0bfb328ee6530c7e93cbdd29d3296d1f2ee08c8322f5b1ba77c70b` | FX6 `p1` Updater Linux kernel image |
| `nflasha1/boot/initrd.img` | `6,914,048` | `5032fc777296e3e1f1b3bb6c7f2f249f18ee135f3c2424f83b7b6fff1e5831c0` | FX6 `p1` Updater SquashFS `4.0` initrd (`342` inodes) |
| `nflasha1/boot/cxd90057.dtb` | `17,131` | `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca` | CXD90057 `p1` updater Device Tree Blob (100% identical to FX3) |
| `0800_appli/setting/cxd90057.dtb` | `16,875` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | CXD90057 main system Device Tree Blob (100% identical to FX3) |
| `0300_partconf/partinf.conf` | `3,990` | `e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9` | FX6 30-partition geometry table (includes `p20` LUT & `p21` opelog) |
| `0700_part_image/dev/nflasha3` | `31,780,864` | `a78c28d835b0cc9c3105332d82f7f404e319d3bf289146935482fd0c887c9b02` | FX6 `/system` partition image (FAT16) |
| `0700_part_image/dev/nflasha5` | `202,677,056` | `d33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1` | FX6 `/wbi` Warm Boot Image snapshot |
| `0700_part_image/dev/nflasha8` | `22,726,656` | `7fbf12865eef11ea4db2d822af88deb0b95e565d10dbf80eee31f23689858315` | FX6 `/cp` TOPPERS co-processor firmware partition image |
| `0700_part_image/dev/nflasha15` | `445,843,456` | `c62b1775a2fe36669b644a55cac7eab9ce2636e6fb8469cbf791d00b8ed6fc6a` | FX6 `/usr` application & kernel module partition image (ext2) |
| `0700_part_image/dev/nflasha23` | `67,108,864` | `f6dc4a6325652b0650074f23e4facdc7bb51ea1e39fccd119b2e67f7d15713aa` | FX6 `/PMBP` partition image |
| `nflasha8/tomco.txt` | `810` | `36566d47fe61e9560f4ce7f1b579bc2404b330bb7940b54e462abcff9c360140` | FX6 runtime CP RTOS load manifest (`cpapp-b.bin` + `13` sub-firmwares incl. `lena.bin`) |
| `nflasha8/cpapp-b.bin` | `17,952,816` | `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668` | FX6 TOPPERS CP RTOS main firmware (`p8` `/cp`, never flashed onto FX3) |
| `usr/bin/ud_send_lsi.elf` (`p15`) | `10,248` | `d0ece6ca2b8e18d79ed1abe1f96fe40a22628aa458f5d37a19a83a3f51e4fb44` | FX6 `/usr/bin/ud_send_lsi.elf` (`p15` normal userland SCU boot-mode dispatcher) |
| `usr/bin/ud_send_lsi.elf` (`p1-initrd`) | `10,248` | `9fb4bd02b3434bd9fe8fb49fcf4359f7720b292506960ae0d9894332d3453c80` | FX6 `p1` initrd `/usr/bin/ud_send_lsi.elf` (`U5` mode `0` sticky-free exit helper) |
| `0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin` | `2,253,333` | `e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e` | FX6 factory Bk4 (`CX95898`) NTSC Backup template (`7,077` keys; `P7` / Track 1B seed) |
| `usr/lib/libgrm.so` | `265,376` | `0f9f922664ad23813fec3f2466d8f453a8741af11be9627583712b752cea9d2b` | FX6 GRM graphics resource manager library |
| `nflasha3-initrd/sbin/init` | `735` | `c83de1abeeb779f7473181b51face32ecfedfa3bd5c0fc346ae0c628f1b0ac5e` | FX6 `nflasha3-initrd` Stage-1 bootstrap (`insmod_drv1` -> `setup_nflash` -> `/sbin/init2`) |
| `nflasha3-initrd/sbin/init2` | `1,658` | `45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb` | FX6 `nflasha3-initrd` Stage-2 userland init (`fstab` -> `insmod_drv2` -> `bootin.elf` -> `im.elf`) |
| `nflasha3-initrd/sbin/initrc/insmod_drv1` | `152` | `22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591` | FX6 early 4-module eMMC storage loader (`devno.ko` -> `dma330.ko` -> `crypt-emmc.ko` -> `emmc.ko`) |
| `nflasha3-initrd/sbin/initrc/insmod_drv2` | `1,298` | `19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e` | FX6 39-module `/usr/kmod/*.ko` loader (`/usr/kmod/upm.ko` at 1-based slot `#24`) |
| `usr/bin/bootin.elf` (`p15`) | `23,960` | `72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6` | FX6 `/usr/bin/bootin.elf` early boot handoff daemon (`p15`) |
| `usr/bin/im.elf` (`p15`) | `40,920` | `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec` | FX6 `/usr/bin/im.elf` primary process manager & `appFw.so` supervisor (`p15`) |
| `bin/ud_wbi_drop.elf` (`updater`) | `10,304` | `4cfc8f979a4289915e2a3db6cd7e96bb97b35645149977619c04b0d9c5fbc7b3` | FX6 updater WBI header invalidator (`"invl"` sector-0 overwrite on `/dev/nflasha5`; forbidden in Stage-A) |
| `0800_appli/setting/kemco.txt` | `1,788` | `6a609ee6b96c2ed0db47e9056ca67dfd8d419f9445302dacf09c262eace3b4fc` | FX6 kernel cmdline template (`warm.mode=2`, `wbimem=0x01919000@0x410524000` `+13.47 MiB` vs FX3) |
| `usr/kmod/emg.ko` | `18,424` | `7680413f1ae0e575478b7a3989710ad2eee0b7584647ccb501e6d6d6a24b2682` | FX6-exclusive emergency GPIO kernel module (`insmod_drv2` slot `#31`; benignly skipped via `ENOENT` on stock FX3, zero `/dev/*` node) |
| `usr/lib/libgemini-grm.so` | `51,800` | `f47c8f3ecff0710d2c246d7d0c0ccdb5381a9f39b1b8d68464d184c0be8070b9` | FX6 Gemini GRM userland interface library (`Surface B` `/dev/*` & `Surface C` ELF64 linkage closure) |
| `usr/lib/libuxengine.so` | `742,128` | `11dbc9a7283587d27692cfdf5d54c9b89e79ac6d509e88107d4c7f3878868876` | FX6 UXEngine menu presentation engine (`Surface B` `/dev/*` & `Surface C` ELF64 linkage closure) |
| `nflasha3-initrd/lib/libc-2.25.so` | `1,283,936` | `4ecddf81915c4e03d9815eade4e626363616618be7f70aabfa467d52cb0348fd` | Base GNU C Library (`libc.so.6`, `GLIBC_2.17..GLIBC_PRIVATE` `VERDEF` parity across FX3 & FX6) |
| `usr/lib/libstdc++.so.6.0.22` | `1,549,496` | `60857b39f0c34a09a889d937683bd8dae68200b6f10335fe94dee130a770247c` | Base C++ Standard Library (`libstdc++.so.6`, `GLIBCXX_3.4*` & `CXXABI_1.3*` `VERDEF` parity across FX3 & FX6) |
| `usr/lib/libgcc_s.so.1` | `71,920` | `9a348469b43aaf815f32104139a62116ef1247662a965b24e38e88e574814805` | Base GCC runtime support library (`GCC_3.0..GCC_4.5.0` `VERDEF` parity across FX3 & FX6) |

### 1.3 Phase 2 Binary Adaptation Donor Inputs (`P1` / `P3` / `P4` / `P8` / `P9` / `Fan`)

All 7 donor binaries modified purely in RAM / temporary directories by `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py` (`ALL_PHASE2_TARGET_SPECS`, 100% byte-reversible via `rollback_patch_spec`):

| Component / Path | Size (Bytes) | SHA-256 Digest | Role & Description |
| :--- | ---: | :--- | :--- |
| `usr/lib/libInfraSetupFile.so` (FX6 6.01) | `202,664` | `b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357` | `P1` `/3dlut` -> `/setting/3dlut` path-literal redirect (`1` site) |
| `usr/lib/libInfraMediaCommon.so` (FX6 6.01) | `402,624` | `acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd` | `P1` `/3dlut` -> `/setting/3dlut` path-literal redirect (`1` site) |
| `usr/lib/libInfraMediaConfig.so` (FX6 6.01) | `52,312` | `9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3` | `P1` `/3dlut` -> `/setting/3dlut` path-literal redirect (`2` sites) |
| `usr/lib/libInfraAppRemoteBoard.so` (FX6 6.01) | `10,448` | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | `P3` ECM-G10M (`UIPC_TYPE_250` `0xFA`) remote-board stub (`MOV W0, #0; RET`) |
| `usr/lib/appFw.so` (FX6 6.01) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | Combined `P1` (`3` `/3dlut` sites) + `P4` Electronic ND Clear clamp + `P8` SubLCD no-op |
| `usr/lib/libfan.so` (FX6 6.01) | `31,176` | `d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850` | `Fan` `ufan_read_ic_type` return FX3 fan controller ID `1` (`MOV W0, #1; RET`) |
| `usr/kmod/upm.ko` (FX3 7.02) | `453,896` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | `P9` `sub28` `CBZ X1` null-callback guard (`0x5A28`/`0x5A2C` + `.eh_frame` cave `0x32930`) |

---

## 2. Clean-Room Build & Reproduction Workflows

### 2.1 Track 1A — Interactive FX6 / FX3 Menu QEMU VM (`outputs/fx3-vm-trial/`)

1. **Build the Patched `qemu-system-aarch64` Binary**:
   - Apply [`outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch`](../outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch) (mapping High DDR at `0x400000000`, ESRAM mailbox at `0xFE005000`, Sony timer, SCU request, and GPIO Bank5). Provenance metadata is recorded in `outputs/fx3-vm/metadata/build-provenance.json`.
2. **Compile `libgrm-fbinit25-live700.so` & Synchronize BYOF CPIO**:
   - Run the deterministic pure-stdlib builder [`outputs/fx3-vm-trial/build_live700.py`](../outputs/fx3-vm-trial/build_live700.py):
     ```sh
     # Clean-room compile-only check (no BYOF CPIO required):
     PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm-trial/build_live700.py --compile-only

     # Full CPIO member update + manifest sync when BYOF live700 CPIO is present:
     PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm-trial/build_live700.py
     ```
3. **Launch Interactive Menu Emulators**:
   - Double-click or execute [`outputs/fx3-vm-trial/FX6菜单.command`](../outputs/fx3-vm-trial/FX6菜单.command) (FX6 Ver. 6.01 full 10-tab interactive menu & `1024×540` live OSD) or [`outputs/fx3-vm-trial/FX3菜单.command`](../outputs/fx3-vm-trial/FX3菜单.command) (FX3 Ver. 7.02 interactive menu).

### 2.2 Track 1B — Native Presenter Closure (`outputs/fx6-native-presenter-closure/`)

- Compiles `outputs/fx6-native-presenter-closure/src/fx6_presenter_closure.c` with AArch64 Zig `0.17.0`, injects donor `CX95898_NTSC.bin` Bk4 NVRAM state, boots under QEMU with QMP `GPE0` (`0x41E001000`, `1024×540×4` ARGB8888) physical framebuffer readback, and writes clean JSON/serial summaries:
  ```sh
  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
    --run-id r4-verify --round 4 --restore-infra70 1 --restore-all-early 1 \
    --reply-all-200d 1 --initial-setting-done 1 --duration 55
  ```

### 2.3 Track 3 — Offline FX6-on-FX3 Hardware Readiness & 12-Gate Safety Closure (`outputs/fx6-on-fx3-closure/` + `outputs/fx3-safety/`)

- Executes the entire unified lab test suite (`fx3-recovery-adapter` + `fx3-safety` + `fx6-on-fx3-closure` + `fx3-vm-trial` + BYOF manifest consistency + tracked-tree clean-room hygiene), assembles the ephemeral `P1..P9 + Fan` Stage-A RAM-Overlay candidate inside `TemporaryDirectory`, and evaluates all 12 pre-flash safety gates (`G1..G12`) with zero persistent binary residue:
  ```sh
  make test
  make dry-run
  make verify-storage-ram-budget
  make verify-stage-a-orchestrator
  make verify-kmod-userland-abi
  # Donorless clean-room CI simulation (matches .github/workflows/clean-room-ci.yml):
  FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof
  FX3_FX6_FORCE_CLEAN_ROOM=1 make test
  ```

### 2.4 Track 4 — Offline `p1` / `boot0` / `boot1` Recovery Adapter (`outputs/fx3-recovery-adapter/`)

- Pure-stdlib offline VFAT/SquashFS/`/p1chksum` inspection, fixed-length candidate build, byte-exact rollback, two-pass `O_RDONLY` chunked capture (`383 × 65,536 B`), and static Linux AArch64 ELF worker linking (`fx3_p1_reader` & `fx3_boot_reader`) with zero camera upload or flash paths:
  ```sh
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" \
    /usr/bin/python3 -B -m fx3_recovery --help
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" \
    /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"
  ```

---

## 3. Automated BYOF Manifest Auditor (`make verify-byof`)

Run [`scripts/verify_byof_manifest.py`](../scripts/verify_byof_manifest.py) via `make verify-byof`:
```sh
make verify-byof
```
- **In a clean Git clone (without proprietary Sony firmware)**: Validates every `(path, size_bytes, sha256)` entry across both English and Simplified Chinese tables, checks 100% EN/ZH digest & size parity, cross-checks digests against pinned constants in `fx6_closure`, `fx3_safety`, and `fx3_recovery`, and exits `0` with `CLEAN_ROOM_SCHEMA_VERIFIED`.
- **When local BYOF donor files are present**: Streams and verifies live byte sizes and SHA-256 digests on disk, exiting `0` with `LOCAL_DONOR_VERIFIED` (or failing closed with exit code `1` on any mismatch).

---
---

# 简体中文指南

本仓库 100% 开源了围绕 **Sony ILME-FX3 (Ver. 7.02, Model `0x91030080`)** 与 **Sony ILME-FX6 (Ver. 6.01, Model `0x91040086`)** 的全部自研 QEMU AArch64 硬件仿真补丁、内核/用户态兼容垫片（CP helper、CAPID 预初始化、GRM/FrameBuffer 垫片、原生 Presenter 闭环线束）、浏览器交互菜单前端、确定性离线二进制适配与 Unicorn 指令级验证套件、`p1`/`boot0`/`boot1` 离线恢复适配工具以及全阶段技术审计报告。

出于版权合规与 GitHub 文件体积限制，**本仓库不包含任何索尼原厂闭源二进制文件（如 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`nflasha*` 分区镜像或 `.cpio` 根文件系统归档）**。研究者可从索尼官方固件升级包提取对应组件，并通过 `make verify-byof`（`scripts/verify_byof_manifest.py`）自动核对下表中的精确字节数与 SHA-256 指纹。

## 1. 官方固件参考指纹清单 (SHA-256)

### 1.1 Sony ILME-FX3 Ver. 7.02 (`0x91030080`) 与 `2.04`/`2.05` 恢复引擎

| 组件 / 路径 | 大小 (字节) | SHA-256 摘要 | 角色与说明 |
| :--- | ---: | :--- | :--- |
| `nflasha3/vmlinux.bin` | `6,610,952` | `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` | FX3 官方 Linux `4.9.337-scel+` AArch64 内核镜像（默认 VM 与 Bank 0 内核） |
| `0800_appli/setting/cxd90057.dtb` | `16,875` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | CXD90057 主系统设备树 DTB（与 FX6 100% 字节一致） |
| `nflasha1/boot/cxd90057.dtb` | `17,131` | `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca` | CXD90057 `p1` 升级器设备树 DTB（与 FX6 100% 字节一致） |
| `0300_partconf/partinf.conf` | `3,999` | `3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189` | FX3 30 槽位分区几何表（写入 eMMC UDA 0 号扇区；最高有效槽位 `p19`） |
| `0750_nor_loader/loader_nor.bin` | `101,888` | `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942` | FX3 Octal-SPI NOR 启动加载器 |
| `pformat_config.txt` | `1,274` | `21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece` | SPI NOR 物理扇区布局配置（与 FX6 100% 字节一致） |
| `LdrBkupList.txt` | `650` | `ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88` | 65 项 Loader Backup 键值清单（与 FX6 100% 字节一致） |
| `nflasha8/tomco.txt` | `710` | `42f1785422bce152dbb21c4e82f42dd4b053a1729c7694e54b7cc9f118592722` | FX3 主系统 CP RTOS 加载清单（`cpapp-b.bin` @ `0xFC000000` + `11` 项子固件） |
| `updaterfs/cp/tomco.txt` | `618` | `d9401e6a7d0cdd85803e2a6823fd9dac0ff186910d82a5671f32fc0a37fc21f1` | FX3 升级态 CP RTOS 加载清单（`udtrcp.bin`；与 FX6 升级器 100% 一致） |
| `nflasha8/cpapp-b.bin` | `15,980,568` | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` | FX3 TOPPERS CP RTOS 主固件（`p8` `/cp`，真机原样保留严禁改写） |
| `usr/bin/ud_send_lsi.elf` (`p1-initrd`) | `10,248` | `9fb4bd02b3434bd9fe8fb49fcf4359f7720b292506960ae0d9894332d3453c80` | `p1` 升级器 SCU 启动模式切换器（`ioctl(fd, 0x804b0376, req)`；与 FX6 `p1` 100% 一致） |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | FX3 原厂 Bk4 (`CX95900`) 双槽 Backup 种子镜像（`6,994` 个键） |
| `original-update-engine/2.04/nflasha1` | `19,377,152` | `e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67` | FX3 `2.04` 官方已解密 `p1` 恢复参考镜像（`fx3_recovery`） |
| `original-update-engine/2.05/nflasha1` | `19,377,152` | `ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591` | FX3 `2.05` 官方已解密 `p1` 恢复参考镜像（`fx3_recovery`） |
| `libsdfileinputupdaterapi.so` (`p1`) | `60,584` | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` | FX3 `p1` 恢复分区升级校验库 |
| `libupdatercorecommon.so` (`p1`) | `72,864` | `b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74` | `p1` 核心升级公共库（FX3 `2.04`/`2.05` 与 FX6 `p1` 100% 字节一致） |
| `usr/kmod/upm.ko` | `453,896` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | FX3 Ver. 7.02 `upm.ko` 内核模块（`P9` `sub28` `CBZ X1` 空回调防护目标） |

### 1.2 Sony ILME-FX6 Ver. 6.01 (`0x91040086`)

| 组件 / 路径 | 大小 (字节) | SHA-256 摘要 | 角色与说明 |
| :--- | ---: | :--- | :--- |
| `nflasha3/vmlinux.bin` | `6,610,952` | `bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9` | FX6 官方 Linux `4.9.337-scel+` AArch64 主系统内核镜像 |
| `nflasha3/initrd.img` | `5,661,696` | `fc97d08139b9ec20a1a511e608f6ed4f55d71f204472467463fdc181d2973da6` | FX6 主系统 initrd (ext2) |
| `0400_updater/dev/nflasha1` | `16,684,032` | `2a32ea4db3c7cabc5daad3b4e015acbc3c277ac38148b253f241c9c31d456786` | FX6 升级分区镜像（VFAT + `/boot/initrd.img` SquashFS + `/p1chksum`） |
| `nflasha1/boot/vmlinux.bin` | `6,582,280` | `58f595d53a0bfb328ee6530c7e93cbdd29d3296d1f2ee08c8322f5b1ba77c70b` | FX6 `p1` 升级器 Linux 内核镜像 |
| `nflasha1/boot/initrd.img` | `6,914,048` | `5032fc777296e3e1f1b3bb6c7f2f249f18ee135f3c2424f83b7b6fff1e5831c0` | FX6 `p1` 升级器 SquashFS `4.0` initrd（`342` 个 inode） |
| `nflasha1/boot/cxd90057.dtb` | `17,131` | `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca` | CXD90057 `p1` 升级器设备树 DTB（与 FX3 100% 字节一致） |
| `0800_appli/setting/cxd90057.dtb` | `16,875` | `c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280` | CXD90057 主系统设备树 DTB（与 FX3 100% 字节一致） |
| `0300_partconf/partinf.conf` | `3,990` | `e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9` | FX6 30 槽位分区几何表（含 `p20` LUT 与 `p21` opelog） |
| `0700_part_image/dev/nflasha3` | `31,780,864` | `a78c28d835b0cc9c3105332d82f7f404e319d3bf289146935482fd0c887c9b02` | FX6 `/system` 分区镜像 (FAT16) |
| `0700_part_image/dev/nflasha5` | `202,677,056` | `d33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1` | FX6 `/wbi` Warm Boot Image 快照 |
| `0700_part_image/dev/nflasha8` | `22,726,656` | `7fbf12865eef11ea4db2d822af88deb0b95e565d10dbf80eee31f23689858315` | FX6 `/cp` TOPPERS 协处理器固件分区镜像 |
| `0700_part_image/dev/nflasha15` | `445,843,456` | `c62b1775a2fe36669b644a55cac7eab9ce2636e6fb8469cbf791d00b8ed6fc6a` | FX6 `/usr` 应用与内核模块分区镜像 (ext2) |
| `0700_part_image/dev/nflasha23` | `67,108,864` | `f6dc4a6325652b0650074f23e4facdc7bb51ea1e39fccd119b2e67f7d15713aa` | FX6 `/PMBP` 分区镜像 |
| `nflasha8/tomco.txt` | `810` | `36566d47fe61e9560f4ce7f1b579bc2404b330bb7940b54e462abcff9c360140` | FX6 主系统 CP RTOS 加载清单（`cpapp-b.bin` + `13` 项子固件含 `lena.bin`） |
| `nflasha8/cpapp-b.bin` | `17,952,816` | `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668` | FX6 TOPPERS CP RTOS 主固件（`p8` `/cp`，严禁刷入 FX3 真机） |
| `usr/bin/ud_send_lsi.elf` (`p15`) | `10,248` | `d0ece6ca2b8e18d79ed1abe1f96fe40a22628aa458f5d37a19a83a3f51e4fb44` | FX6 `/usr/bin/ud_send_lsi.elf`（`p15` 常态用户态 SCU 启动模式切换器） |
| `usr/bin/ud_send_lsi.elf` (`p1-initrd`) | `10,248` | `9fb4bd02b3434bd9fe8fb49fcf4359f7720b292506960ae0d9894332d3453c80` | FX6 `p1` initrd `/usr/bin/ud_send_lsi.elf`（`U5` `mode 0` 无粘滞退出助手） |
| `0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin` | `2,253,333` | `e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e` | FX6 原厂 Bk4 (`CX95898`) NTSC Backup 模板（`7,077` 个键；`P7` / Track 1B 种子） |
| `usr/lib/libgrm.so` | `265,376` | `0f9f922664ad23813fec3f2466d8f453a8741af11be9627583712b752cea9d2b` | FX6 GRM 图形资源管理库 |
| `nflasha3-initrd/sbin/init` | `735` | `c83de1abeeb779f7473181b51face32ecfedfa3bd5c0fc346ae0c628f1b0ac5e` | FX6 `nflasha3-initrd` 一阶段引导脚本（`insmod_drv1` -> `setup_nflash` -> `/sbin/init2`） |
| `nflasha3-initrd/sbin/init2` | `1,658` | `45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb` | FX6 `nflasha3-initrd` 二阶段用户态引导脚本（`fstab` -> `insmod_drv2` -> `bootin.elf` -> `im.elf`） |
| `nflasha3-initrd/sbin/initrc/insmod_drv1` | `152` | `22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591` | FX6 早期 4 模块 eMMC 存储驱动加载清单（`devno.ko` -> `dma330.ko` -> `crypt-emmc.ko` -> `emmc.ko`） |
| `nflasha3-initrd/sbin/initrc/insmod_drv2` | `1,298` | `19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e` | FX6 39 模块 `/usr/kmod/*.ko` 加载清单（`/usr/kmod/upm.ko` 位于第 `#24` 顺位） |
| `usr/bin/bootin.elf` (`p15`) | `23,960` | `72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6` | FX6 `/usr/bin/bootin.elf` 早期引导交接守护进程（`p15`） |
| `usr/bin/im.elf` (`p15`) | `40,920` | `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec` | FX6 `/usr/bin/im.elf` 主进程管理器与 `appFw.so` 监管入口（`p15`） |
| `bin/ud_wbi_drop.elf` (`updater`) | `10,304` | `4cfc8f979a4289915e2a3db6cd7e96bb97b35645149977619c04b0d9c5fbc7b3` | FX6 升级态 WBI 头部作废工具（向 `/dev/nflasha5` 0 扇区写入 `"invl"`；Stage-A 严禁调用） |
| `0800_appli/setting/kemco.txt` | `1,788` | `6a609ee6b96c2ed0db47e9056ca67dfd8d419f9445302dacf09c262eace3b4fc` | FX6 内核启动参数模板（`warm.mode=2`，`wbimem=0x01919000@0x410524000`，较 FX3 大 `+13.47 MiB`） |
| `usr/kmod/emg.ko` | `18,424` | `7680413f1ae0e575478b7a3989710ad2eee0b7584647ccb501e6d6d6a24b2682` | FX6 独占应急 GPIO 内核模块（`insmod_drv2` 第 `#31` 顺位；在 FX3 原厂内核下按 `ENOENT` 无害跳过，零 `/dev/*` 节点） |
| `usr/lib/libgemini-grm.so` | `51,800` | `f47c8f3ecff0710d2c246d7d0c0ccdb5381a9f39b1b8d68464d184c0be8070b9` | FX6 Gemini GRM 用户态接口库（`Surface B` `/dev/*` 与 `Surface C` ELF64 符号链接闭环审计） |
| `usr/lib/libuxengine.so` | `742,128` | `11dbc9a7283587d27692cfdf5d54c9b89e79ac6d509e88107d4c7f3878868876` | FX6 UXEngine 菜单呈现引擎库（`Surface B` `/dev/*` 与 `Surface C` ELF64 符号链接闭环审计） |
| `nflasha3-initrd/lib/libc-2.25.so` | `1,283,936` | `4ecddf81915c4e03d9815eade4e626363616618be7f70aabfa467d52cb0348fd` | 基础 GNU C 运行时库（`libc.so.6`，FX3 与 FX6 `GLIBC_2.17..GLIBC_PRIVATE` `VERDEF` 100% 一致） |
| `usr/lib/libstdc++.so.6.0.22` | `1,549,496` | `60857b39f0c34a09a889d937683bd8dae68200b6f10335fe94dee130a770247c` | 基础 C++ 标准库（`libstdc++.so.6`，FX3 与 FX6 `GLIBCXX_3.4*` 及 `CXXABI_1.3*` `VERDEF` 100% 一致） |
| `usr/lib/libgcc_s.so.1` | `71,920` | `9a348469b43aaf815f32104139a62116ef1247662a965b24e38e88e574814805` | 基础 GCC 运行时支持库（`GCC_3.0..GCC_4.5.0` `VERDEF` 在 FX3 与 FX6 间 100% 一致） |

### 1.3 Phase 2 二进制适配 Donor 输入清单（7 项 — `P1` / `P3` / `P4` / `P8` / `P9` / `Fan`）

由 `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py`（`ALL_PHASE2_TARGET_SPECS`）纯内存/临时目录生成的全部 7 份 Donor 原件（支持 `rollback_patch_spec` 100% 逐字节可逆回滚）：

| 组件 / 路径 | 大小 (字节) | SHA-256 摘要 | 角色与说明 |
| :--- | ---: | :--- | :--- |
| `usr/lib/libInfraSetupFile.so` (FX6 6.01) | `202,664` | `b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357` | `P1` `/3dlut` -> `/setting/3dlut` 路径常量重定向（`1` 处） |
| `usr/lib/libInfraMediaCommon.so` (FX6 6.01) | `402,624` | `acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd` | `P1` `/3dlut` -> `/setting/3dlut` 路径常量重定向（`1` 处） |
| `usr/lib/libInfraMediaConfig.so` (FX6 6.01) | `52,312` | `9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3` | `P1` `/3dlut` -> `/setting/3dlut` 路径常量重定向（`2` 处） |
| `usr/lib/libInfraAppRemoteBoard.so` (FX6 6.01) | `10,448` | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | `P3` ECM-G10M (`UIPC_TYPE_250` `0xFA`) 远端手柄板裁剪桩（`MOV W0, #0; RET`） |
| `usr/lib/appFw.so` (FX6 6.01) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | 组合补丁：`P1`（`3` 处 `/3dlut`）+ `P4` 电子 ND Clear 钳位 + `P8` SubLCD 空操作 |
| `usr/lib/libfan.so` (FX6 6.01) | `31,176` | `d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850` | `Fan` `ufan_read_ic_type` 返回 FX3 风扇控制器类型 `1`（`MOV W0, #1; RET`） |
| `usr/kmod/upm.ko` (FX3 7.02) | `453,896` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | `P9` `sub28` `CBZ X1` 空回调防护（`0x5A28`/`0x5A2C` + `.eh_frame` 代码洞穴 `0x32930`） |

---

## 2. 净室构建与全轨道复现工作流

### 2.1 Track 1A — FX6 / FX3 交互式菜单 QEMU 虚拟机 (`outputs/fx3-vm-trial/`)

1. **构建定制 `qemu-system-aarch64`**：
   - 基于上游 QEMU 源码应用 [`outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch`](../outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch)（映射 `0x400000000` 高位 DDR、`0xFE005000` ESRAM 邮箱、Sony 定时器、SCU 请求与 GPIO Bank5）。构建溯源记录见 `outputs/fx3-vm/metadata/build-provenance.json`。
2. **确定性编译 `libgrm-fbinit25-live700.so` 并同步 BYOF CPIO**：
   - 运行纯标准库构建脚本 [`outputs/fx3-vm-trial/build_live700.py`](../outputs/fx3-vm-trial/build_live700.py)：
     ```sh
     # 净室仅编译模式（无需自备 CPIO）：
     PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm-trial/build_live700.py --compile-only

     # 当自备 live700 CPIO 就位时，原地更新成员并同步 manifest SHA-256：
     PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm-trial/build_live700.py
     ```
3. **一键启动交互菜单模拟器**：
   - 双击或运行 [`outputs/fx3-vm-trial/FX6菜单.command`](../outputs/fx3-vm-trial/FX6菜单.command)（FX6 Ver. 6.01 完整 10 页签交互菜单与 `1024×540` 实时画面）或 [`outputs/fx3-vm-trial/FX3菜单.command`](../outputs/fx3-vm-trial/FX3菜单.command)（FX3 Ver. 7.02 交互菜单）。

### 2.2 Track 1B — 原生 Presenter 渲染闭环 (`outputs/fx6-native-presenter-closure/`)

- 使用 AArch64 Zig `0.17.0` 编译 `outputs/fx6-native-presenter-closure/src/fx6_presenter_closure.c`，注入 `CX95898_NTSC.bin` Bk4 NVRAM 状态，在 QEMU 下启动并通过 QMP 读取 `GPE0`（`0x41E001000`，`1024×540×4` ARGB8888）物理帧缓冲：
  ```sh
  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
    --run-id r4-verify --round 4 --restore-infra70 1 --restore-all-early 1 \
    --reply-all-200d 1 --initial-setting-done 1 --duration 55
  ```

### 2.3 Track 3 — FX6-on-FX3 离线硬件就绪与 12 道安全门禁闭环 (`outputs/fx6-on-fx3-closure/` + `outputs/fx3-safety/`)

- 一键运行全仓统一测试套件（涵盖 `fx3-recovery-adapter` + `fx3-safety` + `fx6-on-fx3-closure` + `fx3-vm-trial` + BYOF 清单一致性校验 + 净室零残留审计），在 `TemporaryDirectory` 中组装 `P1..P9 + Fan` Stage-A RAM-Overlay 候选包并通过全部 12 道首刷安全门禁（`G1..G12`），磁盘零残留：
  ```sh
  make test
  make dry-run
  make verify-storage-ram-budget
  make verify-stage-a-orchestrator
  make verify-kmod-userland-abi
  # 无 Donor 净室 CI 模拟（对应 .github/workflows/clean-room-ci.yml）：
  FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof
  FX3_FX6_FORCE_CLEAN_ROOM=1 make test
  ```

### 2.4 Track 4 — 离线 `p1` / `boot0` / `boot1` 恢复适配工具 (`outputs/fx3-recovery-adapter/`)

- 纯标准库离线 VFAT/SquashFS/`/p1chksum` 检查、定长候选镜像生成、逐字节回滚、双遍 `O_RDONLY` 分块采集（`383 × 65,536 B`）以及静态 Linux AArch64 ELF 工作器链接（`fx3_p1_reader` 与 `fx3_boot_reader`），不包含任何相机上传或刷写入口：
  ```sh
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" \
    /usr/bin/python3 -B -m fx3_recovery --help
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-recovery-adapter" \
    /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"
  ```

---

## 3. 自动化 BYOF 指纹清单审计 (`make verify-byof`)

通过 `make verify-byof` 运行 [`scripts/verify_byof_manifest.py`](../scripts/verify_byof_manifest.py)：
```sh
make verify-byof
```
- **净室克隆模式（无索尼原厂固件）**：解析中英文双语表格中的全部 `(path, size_bytes, sha256)` 条目，校验 64 位小写十六进制 SHA-256 语法、中英文表格 100% 对齐无冲突，并与 `fx6_closure`、`fx3_safety`、`fx3_recovery` 代码内固定常量交叉核对，输出 `CLEAN_ROOM_SCHEMA_VERIFIED` 并以状态码 `0` 退出。
- **本地 BYOF 固件就位模式**：对本地 Donor 固件逐流计算真实字节数与 SHA-256 摘要，全部匹配时输出 `LOCAL_DONOR_VERIFIED`（状态码 `0`）；任何不一致均阻断并以非零状态码退出。
