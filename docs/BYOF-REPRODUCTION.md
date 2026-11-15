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

### 1.4 Phase 19–35 Stage-B Outputs, Wireless (`P12`), Peripheral/Codec & `.uxc`/Font Donors

Covers all **4** deterministic Stage-A/B adapted outputs (`fx6_closure.patcher` in-memory `apply_patch_spec` builds) plus **36** Phase 17–35 live FX6/FX3 donors (wireless/BT/network, peripheral/UIPC/presentation/codec, cross-body FX3 `appFw.so`/`libmpr.so`/`string_english.uxc`, `.uxc` UI/locale packs, and Monotype `.ltt`/`.ttf` icon fonts):

| Component / Path | Size (Bytes) | SHA-256 Digest | Role & Description |
| :--- | ---: | :--- | :--- |
| `usr/lib/appFw.so (Stage-A P1+P4+P8 adapted)` | `50,520,424` | `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0` | Stage-A `P1+P4+P8` deterministic `appFw.so` build (`FX6_APPFW_STAGE_A_SHA256`) |
| `usr/lib/appFw.so (Stage-B P10-only adapted)` | `50,520,424` | `07a5405830becb169df4adc7d51eb19f53febe94e36b72de83e2bcad7081b84b` | Isolated `P10` 24 B physical keymap build (`FX6_APPFW_P10_ONLY_SHA256`) |
| `usr/lib/appFw.so (Stage-B P1+P4+P8+P10 adapted)` | `50,520,424` | `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4` | Full Stage-B combined `P1+P4+P8+P10` `appFw.so` build (`FX6_APPFW_STAGE_B_SHA256`) |
| `usr/lib/libWlanResource.so (Stage-B P12 adapted)` | `56,464` | `47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995` | Stage-B `P12` `_Z16handleFatalErrorv` non-blocking guard build (`FX6_WLAN_RSRC_P12_SHA256`) |
| `usr/lib/libWlanResource.so (FX6 6.01)` | `56,464` | `eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88` | FX6 `WF-12` Wi-Fi resource manager donor (`P12` input; `0x70d4` fatal-loop target) |
| `usr/lib/libWlanControlCommon.so (FX6 6.01)` | `18,528` | `4dccfa865720f662c2f02c741bce609bbe132280ab537eae990d913450f2f2c9` | FX6 `WF-12` SDIO/PCIe port & WLAN driver loader (`Phase 22/26`) |
| `usr/lib/libInfraBluetooth.so (FX6 6.01)` | `154,840` | `3b3c1a411f3e157c6d6f7db6ae4dbbb0fc29920561eb3743b7c7723f974cc788` | FX6 Bluetooth service manager (`Init` Airplane-Mode `cbz w0` gate) |
| `usr/lib/libInfraBluetoothCore.so (FX6 6.01)` | `267,576` | `84a9bf33d26914a42c46ffc34381041d56006b3fdf76a2f475d954b602292694` | FX6 Bluetooth QCA BSA UART/HAL bridge (`0x0bb9` fallback) |
| `usr/lib/libResourceBluetooth.so (FX6 6.01)` | `14,464` | `2be9da99a2d45980449ac04814950896058b375c0a565f99bc5eb3fc92a0a16c` | FX6 Bluetooth resource allocator (`ResourceBluetooth_init` `cbz w0` gate) |
| `usr/lib/libbt-vendor.so (FX6 6.01)` | `47,968` | `3c9a48fedd5bbc829d3d166feac090d3d5df3f347d9599f864722f885bdbf8bb` | FX6 Bluetooth HCI vendor HAL (`/dev/ttyAMA3`) |
| `usr/lib/libInfraNetInitializer.so (FX6 6.01)` | `18,792` | `9628f8d97434734742078347d99c1c0a6c00fec43534d1b608f6ca6899c0fc5d` | FX6 network initializer (`SeqQueueNetwork` non-blocking drain) |
| `usr/lib/libInfraInput.so (FX6 6.01)` | `93,448` | `1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02` | FX6 physical input/dial UIPC client (`Phase 17` peripheral UX) |
| `usr/lib/libInfraTp.so (FX6 6.01)` | `47,776` | `ea1c123412fc048d93bd7492bdcc59a7fab0d472c895b73a60d463d5fafe8652` | FX6 capacitive touch panel UIPC client (`SetTpSize` `0x55b8`) |
| `usr/lib/libInfraHotshoe.so (FX6 6.01)` | `47,808` | `0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6` | FX6 MI Smart Handle / digital audio UIPC client (`0x5d90` timeout) |
| `usr/lib/libgpe.so (FX6 6.01)` | `106,520` | `4541f6e22d7c598c3eacedee553015fb12dc35d5068e1f76cddc07dd82cfd79d` | FX6 Graphics Processing Engine display routing library (`GpeInit`) |
| `usr/scenario/AVBB_SCN_START_PANELEVF.so (FX6 6.01)` | `275,968` | `36d98e83611f3e26c7db4d84a7e045fceafc370470744352598db62f54b09b2b` | FX6 panel/EVF startup scenario (`_Z12GetOutputSelhPh` @ `0x173c`) |
| `usr/scenario/AVBB_SCN_START_AUDIO.so (FX6 6.01)` | `70,096` | `96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a` | FX6 digital/analog audio startup scenario (`XLR-H1` / handle audio) |
| `usr/lib/libosal_uipc.so (FX6 6.01)` | `43,752` | `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a` | FX6 OSAL Userland IPC library (`P11` AP<->CP shim & Presenter) |
| `usr/lib/liblibra.so (FX6 6.01)` | `290,992` | `3dffc66daede059cbbdde30d3106185cb3f634cc0309dff69d5a63758ceb5d90` | FX6 `.uxc` resource & localization engine (`sys_getNamespaceID`) |
| `usr/lib/libux_core.so (FX6 6.01)` | `232,960` | `c72d52b41e09d547dd4129fb2af271e2ac52b62dee2d8f27a362ce6dcc35003d` | FX6 UI core toolkit (`Lz77Decoder` & widget renderer) |
| `usr/lib/libmpr.so (FX6 6.01)` | `28,921,824` | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` | FX6 Media Processing Engine (`IMX510` / `XAVC` / sensor-codec parity) |
| `usr/lib/appFw.so (FX3 7.02)` | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | FX3 `ALCIN_UUD` reference `appFw.so` (cross-body `BKID`, `UIPC`, `IMX510` baseline) |
| `usr/lib/libmpr.so (FX3 7.02)` | `3,517,008` | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` | FX3 `ALCIN_UUD` reference `libmpr.so` (`G01` & codec comparison baseline) |
| `usr/share/app/string_english.uxc (FX3 7.02)` | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | FX3 English `.uxc` string pack (`ns=1` cross-body diff baseline) |
| `usr/share/app/image_00_169.uxc (FX6 6.01)` | `3,941,000` | `f9bb82a2cf6364e5683ea9cce7e63b0a891325a8c250904cf28d2417fe2c4148` | FX6 1,610-sprite LDEC/LZ77 `16:9` OSD image pack (`ns=0`) |
| `usr/share/app/string_english.uxc (FX6 6.01)` | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | FX6 English namespace-1 string pack (`ns=1`, `5,044` strings) |
| `usr/share/app/string_english_2.uxc (FX6 6.01)` | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 English namespace-2 string pack (`ns=2`, `5,915` strings) |
| `usr/share/app/string_simplifiedchinese.uxc (FX6 6.01)` | `118,644` | `ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f` | FX6 Simplified Chinese `ns=1` string pack (`100%` UTF-8 & `STRID` parity) |
| `usr/share/app/string_simplifiedchinese_2.uxc (FX6 6.01)` | `122,084` | `058c09066cd7cd4eb5d68fa4228255fa7d2ad195a4088f145ac647e3577e58a3` | FX6 Simplified Chinese `ns=2` (`string_schinese_2`) pack (`5,915` strings) |
| `usr/share/app/string_traditionalchinese_2.uxc (FX6 6.01)` | `121,824` | `07fa20ae03457465a8c4922f479d6cfe1280980a70ac43797081e87654680c6d` | FX6 Traditional Chinese `ns=2` string pack (`5,915` strings) |
| `usr/share/app/string_japanese_2.uxc (FX6 6.01)` | `144,720` | `98315732d7e29078a98dc32c077a799f8831d8bb3d96ec26ca2110ed8e36aa26` | FX6 Japanese `ns=2` string pack (`5,915` strings) |
| `usr/share/app/color_cmn.uxc (FX6 6.01)` | `288` | `ea2e508f9ba567655dd36be6245ada221e595e83f8343b733f3894109f9dd230` | FX6 common palette resource pack (`ns=6`) |
| `usr/share/app/lang_cmn.uxc (FX6 6.01)` | `1,048` | `ad547c47444e134bcf3622b84344d82273d4c5d04fd3775a7cf6fb58f5db63c5` | FX6 common 29-language selector table (`ns=5`) |
| `usr/share/app/style_cmn.uxc (FX6 6.01)` | `1,980` | `b22501655d3d933fdf5a8f6aed6de0aa944b691f4ecb9625c64111e7483ba2c1` | FX6 common UI typography & layout style pack (`ns=3`) |
| `usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt (FX6 6.01)` | `2,054,740` | `3ed0c7dda3f1aebf8334532ba35e945ed6bfd58f25c3aa3fa0cd31aa67cc55d1` | Monotype Simplified Chinese `GB18030` + Sony icon linked font |
| `usr/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt (FX6 6.01)` | `1,552,252` | `3cf4238d210dbd472fd207969eec9660eedd335905137b38566e04a8c8e04448` | Monotype Traditional Chinese `Big5-HKSCS` + Sony icon linked font |
| `usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt (FX6 6.01)` | `851,496` | `dda0a2400add24d829d958adf338899c80b20adc122cf2946d8f0c99f8b0fed3` | Monotype Japanese Heisei Kaku Gothic + Sony icon linked font |
| `usr/share/app/UniversOTS-SJ_wIcon.ltt (FX6 6.01)` | `611,416` | `eea4d814854d2cefc18e5631c82138b2b69824687cd31002b7df34eae025dd0d` | Monotype Latin/European Univers OTS + Sony icon linked font |
| `usr/share/app/MYingHeiC-KSX1001-SJ_wIcon.ltt (FX6 6.01)` | `924,104` | `96a5e21ce562965d0d6c96c711f1a9d7c5e65cee32b80c2dbd793d8b1e440351` | Monotype Korean `KS X 1001` + Sony icon linked font |
| `usr/share/app/Sony_DI_Icons.ttf (FX6 6.01)` | `629,604` | `058c1b07eb768638f984b1d6219cf2375ef771f86aba9d553743a029541a62be` | Sony Digital Imaging PUA (`U+E000..U+F8FF`) vector icon TrueType font |

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

### 2.5 Track 5 & Stage-B — Phase 19–35 (`P10` Keymap, `P11` UIPC-CP, `P12` Wireless, `.uxc`/CJK Font & Sensor/Codec) Audits

- Reproduces Stage-B combined `P1+P4+P8+P10` (`appFw.so` `e2bc2619...`) and `P12` (`libWlanResource.so` `47fec188...`) adaptations purely in RAM, plus hardware-free `.uxc`/LDEC sprite decoding (`1,610` sprites), 62-pack multi-language & Monotype `.ltt`/`.ttf` `cmap` glyph sweeps, and `IMX510` / `XAVC` sensor-codec parity audits (`O_RDONLY` on local donors or `FX3_FX6_FORCE_CLEAN_ROOM=1`):
  ```sh
  make verify-peripheral-ux
  make verify-ap-cp-imaging
  make verify-stage-b-p10
  make verify-uipc-cp-shim
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" \
    /usr/bin/python3 -B -m fx6_closure verify-wireless-guard
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-firmware-lab" \
    /usr/bin/python3 -B -m fx3_firmware_lab audit-all
  ```

### 2.6 Phase 83 Stage-B Capstone — 22-Gate Safety, OTP/RPMB Anti-Rollback, 11-Stage VM, 14+ Firmware Auditors, Round 15 Multi-Tab UI & Live `8768` Console

Every Capstone suite supports both **Local BYOF Donor (`os.O_RDONLY`) mode** and **Donorless Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**, with persistent eMMC writes, OTP fuse touches, and RPMB counter increments hard-locked to zero (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `otp_fuse_touches = 0`, `rpmb_counter_increments = 0`):

```sh
# Unified Environment (prepend FX3_FX6_FORCE_CLEAN_ROOM=1 for donorless clean-room CI mode)
export PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure"

# 1. Unified Stage-B Capstone 22-Gate + OTP/RPMB + 11-Stage VM + Round 15 CLI Certificate (< 3.5s)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx6_closure verify-stage-b-capstone --json
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx6_closure verify-stage-b-capstone --clean-room --markdown-out /tmp/stage_b_capstone_22gate.md

# 2. 22-Gate Master Preflight (G01..G22 incl. G21 XLR-H1 +48V Firewall & G22 Gimbal/Laser/Shutter Guard)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -c "import fx3_safety.phantom48v_gimbal_and_22gate_guard as g; r = g.evaluate_22gate_preflight(dry_run_simulated_backup=True); print(r.schema, r.summary['verified_gates'], r.g21_to_g22_all_passed)"

# 3. OTP / RPMB Anti-Rollback, Cross-SKU & EXT_CSD Permanent Write-Protect Firewall
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -c "from fx3_recovery.firmware_updata_and_antirollback_guard import run_antirollback_and_byof_guard_suite; r = run_antirollback_and_byof_guard_suite(); print(r.schema, r.all_passed, r.otp_fuse_touches, r.rpmb_counter_increments)"

# 4. GF(256) P+Q Tier-0 Self-Healer, Anti-Transplant Lock & SD FX3_SAFE_STOCK.FLG Escape
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx3_recovery.tier0_gf256_selfheal_and_manifest_guard
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx3_recovery.init2_escape_watchdog_fat_verifier

# 5. 11-Stage Heterogeneous VM Co-Emulation Suite (Stages 1..11 incl. Touch-AF / CIZ / Assignable)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 6. 14+ Firmware-Lab Auditors & Round 15 Real-Kernel Multi-Tab Closure
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx3_firmware_lab audit-all
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase83_stage_b_capstone_22gate_verifier.py

# 7. Browser Interactive Menu Emulator Console (HTTP port 8768, read-only local trial)
# Check readiness on http://127.0.0.1:8768/ or launch when not already running:
# curl -s http://127.0.0.1:8768/ | head -n 5
# /usr/bin/python3 -B outputs/fx3-vm-trial/run_fx6_menu_trial.py --port 8768

# Run full repository clean-only suite + dual-mode BYOF manifest audit:
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py
```

### 2.7 Milestone Phase 110 — 32-Gate Safety, 10-Pillar Recovery, 20+ Firmware Auditors, 18-Stage VM & Complete `10/10` Status + `11/11` Full-Menu Real-Kernel Closures

All Milestone Phase 110 gates execute in **both Local Donor (`os.O_RDONLY`) and Donorless Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) modes**, maintaining `2,980` Local Donor / `2,922` Clean-Room passing tests across all 7 suites while locking `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `otp_fuse_touches = 0`, and `passive_tx_bytes_emitted = 0`:

```sh
# 1. Unified 6-Pillar Milestone Phase 110 Master Gate (< 2.5s in BOTH modes)
make verify-milestone-110
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-110
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" \
  /usr/bin/python3 -B -m fx6_closure verify-milestone-110 --json

# 2. 32-Gate Master Preflight (G01..G32 incl. G25..G32 Fan Intake, Tripod, IMX510 Curtain/Subzero, Wireless EMI/6h+ exFAT, PL Cantilever & V-Mount Dummy Battery OVP)
make verify-32-gates
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-32-gates

# 3. 10-Pillar Recovery Master Suite (OTP/RPMB + GF(256) + init2 + Passive RX-Only UART S0..S6 + GPT/RPMB + Ramdisk/eMMC Pre-EOL + FDT bootargs/ARM64 Image)
make verify-10pillar-recovery
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-10pillar-recovery

# 4. 20+ Unified Firmware-Lab Auditors, 18-Stage VM Co-Emulation & Phase 110 Fast Gate Suite
make verify-firmware-lab
make verify-coemulation
make verify-milestone-90
```

---

## 3. Automated BYOF Manifest Auditor (`make verify-byof`)

Run [`scripts/verify_byof_manifest.py`](../scripts/verify_byof_manifest.py) via `make verify-byof`:
```sh
make verify-byof
```
- **In a clean Git clone (without proprietary Sony firmware)**: Validates every `(path, size_bytes, sha256)` entry across both English and Simplified Chinese tables (`57` Stage-A `§1.1–1.3` + `40` Stage-B/Phase 19–35 `§1.4` entries), checks 100% EN/ZH digest & size parity, cross-checks digests against pinned constants in `fx6_closure`, `fx3_safety`, and `fx3_recovery`, and exits `0` with `CLEAN_ROOM_SCHEMA_VERIFIED`.
- **When local BYOF donor files are present**: Streams and verifies live byte sizes and SHA-256 digests on disk (`O_RDONLY`, `54` Stage-A + `36` Stage-B donors) plus `4` deterministic in-memory Stage-A/B adapted outputs (`appFw.so` & `libWlanResource.so`), exiting `0` with `LOCAL_DONOR_VERIFIED` (or failing closed with exit code `1` on any mismatch).
- **Dynamic donor root resolution**: Resolves `work/` trees in priority order: explicit environment overrides (`FX3_FX6_MAC_WORK_ROOT`, `FX3_FX6_MAIN_LAB_WORK_ROOT`, `FX3_FX6_MAC_ROOT`), the current worktree `work/` (when target binaries exist), internal SSD defaults (`~/AI-Workspace/AI/Projects/Mac/{outputs/sony-fx3-fx6-lab/work,work}`), and legacy external volume fallback. Set `FX3_FX6_FORCE_CLEAN_ROOM=1` to strictly force donorless CI isolation.

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

### 1.4 Phase 19–35 Stage-B 适配产物、无线 (`P12`)、外设/编解码与 `.uxc`/字库 Donor 清单

覆盖全部 **4** 项确定性 Stage-A/B 适配输出（`fx6_closure.patcher` 纯内存 `apply_patch_spec` 构建）与 **36** 项 Phase 17–35 本地 FX6/FX3 Donor（无线/蓝牙/网络、外设/UIPC/呈现/编解码、跨机型 FX3 `appFw.so`/`libmpr.so`/`string_english.uxc`、`.uxc` 多语言资源包与 Monotype `.ltt`/`.ttf` 图标字库）：

| 组件 / 路径 | 大小 (字节) | SHA-256 摘要 | 角色与说明 |
| :--- | ---: | :--- | :--- |
| `usr/lib/appFw.so (Stage-A P1+P4+P8 adapted)` | `50,520,424` | `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0` | Stage-A `P1+P4+P8` 确定性 `appFw.so` 构建产物（`FX6_APPFW_STAGE_A_SHA256`） |
| `usr/lib/appFw.so (Stage-B P10-only adapted)` | `50,520,424` | `07a5405830becb169df4adc7d51eb19f53febe94e36b72de83e2bcad7081b84b` | 独立 `P10` 24 B 物理按键映射 `appFw.so` 构建产物（`FX6_APPFW_P10_ONLY_SHA256`） |
| `usr/lib/appFw.so (Stage-B P1+P4+P8+P10 adapted)` | `50,520,424` | `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4` | Stage-B 全量组合 `P1+P4+P8+P10` `appFw.so` 构建产物（`FX6_APPFW_STAGE_B_SHA256`） |
| `usr/lib/libWlanResource.so (Stage-B P12 adapted)` | `56,464` | `47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995` | Stage-B `P12` `_Z16handleFatalErrorv` 非阻塞防护产物（`FX6_WLAN_RSRC_P12_SHA256`） |
| `usr/lib/libWlanResource.so (FX6 6.01)` | `56,464` | `eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88` | FX6 `WF-12` Wi-Fi 资源管理 Donor（`P12` 输入；`0x70d4` 死循环靶点） |
| `usr/lib/libWlanControlCommon.so (FX6 6.01)` | `18,528` | `4dccfa865720f662c2f02c741bce609bbe132280ab537eae990d913450f2f2c9` | FX6 `WF-12` SDIO/PCIe 端口与 WLAN 驱动加载器（`Phase 22/26`） |
| `usr/lib/libInfraBluetooth.so (FX6 6.01)` | `154,840` | `3b3c1a411f3e157c6d6f7db6ae4dbbb0fc29920561eb3743b7c7723f974cc788` | FX6 蓝牙服务管理库（`Init` 飞行模式 `cbz w0` 早退门控） |
| `usr/lib/libInfraBluetoothCore.so (FX6 6.01)` | `267,576` | `84a9bf33d26914a42c46ffc34381041d56006b3fdf76a2f475d954b602292694` | FX6 蓝牙 QCA BSA UART/HAL 桥接库（`0x0bb9` 降级回退） |
| `usr/lib/libResourceBluetooth.so (FX6 6.01)` | `14,464` | `2be9da99a2d45980449ac04814950896058b375c0a565f99bc5eb3fc92a0a16c` | FX6 蓝牙资源分配器（`ResourceBluetooth_init` `cbz w0` 门控） |
| `usr/lib/libbt-vendor.so (FX6 6.01)` | `47,968` | `3c9a48fedd5bbc829d3d166feac090d3d5df3f347d9599f864722f885bdbf8bb` | FX6 蓝牙 HCI 厂商 HAL 库（`/dev/ttyAMA3`） |
| `usr/lib/libInfraNetInitializer.so (FX6 6.01)` | `18,792` | `9628f8d97434734742078347d99c1c0a6c00fec43534d1b608f6ca6899c0fc5d` | FX6 网络初始化器（`SeqQueueNetwork` 有界非阻塞排空） |
| `usr/lib/libInfraInput.so (FX6 6.01)` | `93,448` | `1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02` | FX6 物理按键与拨盘 UIPC 客户端库（`Phase 17` 外设 UX） |
| `usr/lib/libInfraTp.so (FX6 6.01)` | `47,776` | `ea1c123412fc048d93bd7492bdcc59a7fab0d472c895b73a60d463d5fafe8652` | FX6 电容触控屏 UIPC 客户端库（`SetTpSize` `0x55b8`） |
| `usr/lib/libInfraHotshoe.so (FX6 6.01)` | `47,808` | `0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6` | FX6 MI 热靴手柄与数字音频 UIPC 客户端库（`0x5d90` 超时回退） |
| `usr/lib/libgpe.so (FX6 6.01)` | `106,520` | `4541f6e22d7c598c3eacedee553015fb12dc35d5068e1f76cddc07dd82cfd79d` | FX6 图形处理引擎显示路由库（`GpeInit`） |
| `usr/scenario/AVBB_SCN_START_PANELEVF.so (FX6 6.01)` | `275,968` | `36d98e83611f3e26c7db4d84a7e045fceafc370470744352598db62f54b09b2b` | FX6 面板/EVF 启动场景插件（`_Z12GetOutputSelhPh` @ `0x173c`） |
| `usr/scenario/AVBB_SCN_START_AUDIO.so (FX6 6.01)` | `70,096` | `96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a` | FX6 数字/模拟音频启动场景插件（`XLR-H1` / 手柄音频） |
| `usr/lib/libosal_uipc.so (FX6 6.01)` | `43,752` | `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a` | FX6 OSAL 用户态 IPC 核心库（`P11` AP<->CP 垫片与 Presenter） |
| `usr/lib/liblibra.so (FX6 6.01)` | `290,992` | `3dffc66daede059cbbdde30d3106185cb3f634cc0309dff69d5a63758ceb5d90` | FX6 `.uxc` 资源与本地化管理引擎（`sys_getNamespaceID`） |
| `usr/lib/libux_core.so (FX6 6.01)` | `232,960` | `c72d52b41e09d547dd4129fb2af271e2ac52b62dee2d8f27a362ce6dcc35003d` | FX6 UI 核心工具库（`Lz77Decoder` 与控件渲染） |
| `usr/lib/libmpr.so (FX6 6.01)` | `28,921,824` | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` | FX6 媒体处理引擎（`IMX510` / `XAVC` / 传感器与编解码基线） |
| `usr/lib/appFw.so (FX3 7.02)` | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | FX3 `ALCIN_UUD` 参考 `appFw.so`（跨机身 `BKID`、`UIPC`、`IMX510` 基线） |
| `usr/lib/libmpr.so (FX3 7.02)` | `3,517,008` | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` | FX3 `ALCIN_UUD` 参考 `libmpr.so`（`G01` 与编解码对比基线） |
| `usr/share/app/string_english.uxc (FX3 7.02)` | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | FX3 英文 `.uxc` 字符串资源包（`ns=1` 跨机身差异基线） |
| `usr/share/app/image_00_169.uxc (FX6 6.01)` | `3,941,000` | `f9bb82a2cf6364e5683ea9cce7e63b0a891325a8c250904cf28d2417fe2c4148` | FX6 1,610 枚 LDEC/LZ77 精灵图 `16:9` OSD 图像包（`ns=0`） |
| `usr/share/app/string_english.uxc (FX6 6.01)` | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | FX6 英文命名空间 1 字符串包（`ns=1`，`5,044` 条词条） |
| `usr/share/app/string_english_2.uxc (FX6 6.01)` | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 英文命名空间 2 字符串包（`ns=2`，`5,915` 条词条） |
| `usr/share/app/string_simplifiedchinese.uxc (FX6 6.01)` | `118,644` | `ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f` | FX6 简体中文 `ns=1` 字符串包（`100%` UTF-8 与 `STRID` 槽位对齐） |
| `usr/share/app/string_simplifiedchinese_2.uxc (FX6 6.01)` | `122,084` | `058c09066cd7cd4eb5d68fa4228255fa7d2ad195a4088f145ac647e3577e58a3` | FX6 简体中文 `ns=2`（`string_schinese_2`）字符串包（`5,915` 条词条） |
| `usr/share/app/string_traditionalchinese_2.uxc (FX6 6.01)` | `121,824` | `07fa20ae03457465a8c4922f479d6cfe1280980a70ac43797081e87654680c6d` | FX6 繁体中文 `ns=2` 字符串包（`5,915` 条词条） |
| `usr/share/app/string_japanese_2.uxc (FX6 6.01)` | `144,720` | `98315732d7e29078a98dc32c077a799f8831d8bb3d96ec26ca2110ed8e36aa26` | FX6 日文 `ns=2` 字符串包（`5,915` 条词条） |
| `usr/share/app/color_cmn.uxc (FX6 6.01)` | `288` | `ea2e508f9ba567655dd36be6245ada221e595e83f8343b733f3894109f9dd230` | FX6 公共调色板资源包（`ns=6`） |
| `usr/share/app/lang_cmn.uxc (FX6 6.01)` | `1,048` | `ad547c47444e134bcf3622b84344d82273d4c5d04fd3775a7cf6fb58f5db63c5` | FX6 公共 29 语种索引表（`ns=5`） |
| `usr/share/app/style_cmn.uxc (FX6 6.01)` | `1,980` | `b22501655d3d933fdf5a8f6aed6de0aa944b691f4ecb9625c64111e7483ba2c1` | FX6 公共排版与 UI 样式资源包（`ns=3`） |
| `usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt (FX6 6.01)` | `2,054,740` | `3ed0c7dda3f1aebf8334532ba35e945ed6bfd58f25c3aa3fa0cd31aa67cc55d1` | Monotype 简体中文 `GB18030` 嵌合 Sony 图标链接字库 |
| `usr/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt (FX6 6.01)` | `1,552,252` | `3cf4238d210dbd472fd207969eec9660eedd335905137b38566e04a8c8e04448` | Monotype 繁体中文 `Big5-HKSCS` 嵌合 Sony 图标链接字库 |
| `usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt (FX6 6.01)` | `851,496` | `dda0a2400add24d829d958adf338899c80b20adc122cf2946d8f0c99f8b0fed3` | Monotype 日文平成角黑嵌合 Sony 图标链接字库 |
| `usr/share/app/UniversOTS-SJ_wIcon.ltt (FX6 6.01)` | `611,416` | `eea4d814854d2cefc18e5631c82138b2b69824687cd31002b7df34eae025dd0d` | Monotype 拉丁/欧洲 Univers OTS 嵌合 Sony 图标链接字库 |
| `usr/share/app/MYingHeiC-KSX1001-SJ_wIcon.ltt (FX6 6.01)` | `924,104` | `96a5e21ce562965d0d6c96c711f1a9d7c5e65cee32b80c2dbd793d8b1e440351` | Monotype 韩文 `KS X 1001` 嵌合 Sony 图标链接字库 |
| `usr/share/app/Sony_DI_Icons.ttf (FX6 6.01)` | `629,604` | `058c1b07eb768638f984b1d6219cf2375ef771f86aba9d553743a029541a62be` | Sony 数字影像私用区 (`U+E000..U+F8FF`) 矢量图标 TrueType 字库 |

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

### 2.5 Track 5 与 Stage-B — Phase 19–35（`P10` 按键、`P11` UIPC-CP、`P12` 无线、`.uxc`/CJK 字库与传感器编解码）审计

- 在纯内存中复现 Stage-B 组合补丁 `P1+P4+P8+P10`（`appFw.so` `e2bc2619...`）与 `P12`（`libWlanResource.so` `47fec188...`），并运行无硬件 `.uxc`/LDEC 精灵图解码（`1,610` 枚精灵）、62 包多语言与 Monotype `.ltt`/`.ttf` `cmap` 字形覆盖扫描，以及 `IMX510` / `XAVC` 传感器编解码对等审计（本地 Donor 严格只读 `O_RDONLY`，或 `FX3_FX6_FORCE_CLEAN_ROOM=1`）：
  ```sh
  make verify-peripheral-ux
  make verify-ap-cp-imaging
  make verify-stage-b-p10
  make verify-uipc-cp-shim
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure" \
    /usr/bin/python3 -B -m fx6_closure verify-wireless-guard
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-firmware-lab" \
    /usr/bin/python3 -B -m fx3_firmware_lab audit-all
  ```

### 2.6 Phase 83 Stage-B 终局闭环 — 22-Gate 安全门禁、OTP/RPMB 防回滚、11 阶段共仿真、14+ 固件审计与 Round 15 多标签真核验证 + `8768` 交互台

本节 7 大验证套件均原生支持 **本地 BYOF Donor (`os.O_RDONLY`) 模式** 与 **无供体净室 CI 模式 (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**，且强制锁死零持久写入、零 OTP 熔丝触碰与零 RPMB 计数递增（`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`）：

```sh
# 统一环境变量（无供体净室 CI 模式下请在命令前添加 FX3_FX6_FORCE_CLEAN_ROOM=1）
export PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure"

# 1. Stage-B 终局 22-Gate + OTP/RPMB + 11 阶段 VM + Round 15 统一签章验证 CLI (< 3.5s)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx6_closure verify-stage-b-capstone --json
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx6_closure verify-stage-b-capstone --clean-room --markdown-out /tmp/stage_b_capstone_22gate.md

# 2. 22-Gate 主预检（G01..G22，含 G21 XLR-H1 +48V 防烧毁防火墙与 G22 稳定器/跟焦器/激光/快门保护）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -c "import fx3_safety.phantom48v_gimbal_and_22gate_guard as g; r = g.evaluate_22gate_preflight(dry_run_simulated_backup=True); print(r.schema, r.summary['verified_gates'], r.g21_to_g22_all_passed)"

# 3. OTP / RPMB 防回滚、跨机身防火墙与 EXT_CSD 永久写保护熔丝拦截
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -c "from fx3_recovery.firmware_updata_and_antirollback_guard import run_antirollback_and_byof_guard_suite; r = run_antirollback_and_byof_guard_suite(); print(r.schema, r.all_passed, r.otp_fuse_touches, r.rpmb_counter_increments)"

# 4. GF(256) P+Q Tier-0 自愈、防跨机移植锁与 SD 卡 FX3_SAFE_STOCK.FLG 一秒回退逃生
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx3_recovery.tier0_gf256_selfheal_and_manifest_guard
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx3_recovery.init2_escape_watchdog_fat_verifier

# 5. 11 阶段异构硬件共仿真全集（Stage 1..11，含 Touch-AF / CIZ / 可自定义键）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 6. 14+ 固件实验室审计器与 Round 15 真核多标签 UI 闭环单测
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m fx3_firmware_lab audit-all
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase83_stage_b_capstone_22gate_verifier.py

# 7. 浏览器交互式菜单仿真控制台（HTTP 8768 端口，只读本地试用）
# 可先探测 http://127.0.0.1:8768/ 是否已在运行，未启动时再按需运行：
# curl -s http://127.0.0.1:8768/ | head -n 5
# /usr/bin/python3 -B outputs/fx3-vm-trial/run_fx6_menu_trial.py --port 8768

# 全仓净室回归测试与双模 BYOF 清单审计：
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py
```

### 2.7 Milestone Phase 110 — 32 门禁安全、10 支柱救砖、20+ 固件审计、18 阶段共仿真与 10/10 状态页 + 11/11 全菜单真内核闭环

全部 Milestone Phase 110 门禁均原生支持 **本地 BYOF Donor (`os.O_RDONLY`) 模式** 与 **无供体洁净室 CI 模式 (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**，在全仓 `7` 大套件保持 **`2,980` 本地供体 / `2,922` 洁净室** 全绿通过的同时，硬锁 `persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`otp_fuse_touches = 0` 与 `passive_tx_bytes_emitted = 0`：

```sh
# 1. Milestone Phase 110 六柱一体化总闸（双模式均 < 2.5s）
make verify-milestone-110
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-110
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" \
  /usr/bin/python3 -B -m fx6_closure verify-milestone-110 --json

# 2. 32 门禁主安全预检（G01..G32，含 G25..G32 风扇进气、三脚架、IMX510 快门帘/低温、无线 EMI/6h+ exFAT、PL 悬臂力矩与假电池 OVP 拦截）
make verify-32-gates
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-32-gates

# 3. 10 支柱救砖恢复主套件（OTP/RPMB + GF(256) + init2 + 被动只收串口 S0..S6 + GPT/RPMB + Ramdisk/eMMC Pre-EOL + FDT bootargs/ARM64 Image）
make verify-10pillar-recovery
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-10pillar-recovery

# 4. 20+ 固件实验室审计器、18 阶段 VM 协同仿真与 Phase 90 兼容基线总闸
make verify-firmware-lab
make verify-coemulation
make verify-milestone-90
```

---

## 3. 自动化 BYOF 指纹清单审计 (`make verify-byof`)

通过 `make verify-byof` 运行 [`scripts/verify_byof_manifest.py`](../scripts/verify_byof_manifest.py)：
```sh
make verify-byof
```
- **净室克隆模式（无索尼原厂固件）**：解析中英文双语表格中的全部 `(path, size_bytes, sha256)` 条目（`§1.1–1.3` Stage-A `57` 项 + `§1.4` Stage-B/Phase 19–35 `40` 项），校验 64 位小写十六进制 SHA-256 语法、中英文表格 100% 对齐无冲突，并与 `fx6_closure`、`fx3_safety`、`fx3_recovery` 代码内固定常量交叉核对，输出 `CLEAN_ROOM_SCHEMA_VERIFIED` 并以状态码 `0` 退出。
- **本地 BYOF 固件就位模式**：对本地 Donor 固件通过 `O_RDONLY` 逐流计算真实字节数与 SHA-256 摘要（`54` 项 Stage-A + `36` 项 Stage-B Donor），同时在纯内存中校验 `4` 项确定性 Stage-A/B 适配输出（`appFw.so` 与 `libWlanResource.so`），全部匹配时输出 `LOCAL_DONOR_VERIFIED`（状态码 `0`）；任何不一致均阻断并以非零状态码退出。
- **动态 Donor 路径解析优先级**：按顺序探测 `work/` 根目录：显式环境变量覆盖（`FX3_FX6_MAC_WORK_ROOT`、`FX3_FX6_MAIN_LAB_WORK_ROOT`、`FX3_FX6_MAC_ROOT`）、当前工作树自身 `work/`（仅当目标文件存在时命中）、内盘 SSD 默认路径（`~/AI-Workspace/AI/Projects/Mac/{outputs/sony-fx3-fx6-lab/work,work}`）及旧外置盘回退。设置 `FX3_FX6_FORCE_CLEAN_ROOM=1` 可严格强制无供体洁净室隔离。
