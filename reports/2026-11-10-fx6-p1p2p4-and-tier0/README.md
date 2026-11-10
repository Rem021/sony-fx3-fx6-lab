# FX6-on-FX3 P1–P9（9/9）全矩陣兼容適配、五大核心功能路由、`U4`/`U5` 閉環、`U3` Bank 0/1 DDR、`cxd90057.dtb` FDT 與 `.ko` 完整性及 12 道安全門驗證報告（Phase 8）

- **日期**：2026-11-10
- **正式受控工程包路徑**：`outputs/fx6-on-fx3-closure/`
- **對接安全評估套件**：`outputs/fx3-safety/`（`verify_failsafe_hook_script`、`parse_bk4_record` 與 `evaluate_12_safety_gates`）
- **運行時與潔淨室約束**：全離線內存與 `tempfile.TemporaryDirectory()` 驗證；POSIX `/bin/sh` 演練全程以 `PREFIX` 隔離沙盒根目錄（絕不觸碰宿主機真實 `/dev` 或 `/tmp`）；零 QEMU 進程操作、零 USB/硬件交互、倉庫零 `.so` / `.bin` / `.img` / `.vfat` / `.ko` / `.cpio` 二進制產物留存；兼容 macOS 系統 `/usr/bin/python3`（Python 3.9.6）與 Unicorn AArch64 2.1.4。

---

## 1. 正式受控工程包結構與全矩陣覆蓋表

全部純源碼模組集中受控於 `outputs/fx6-on-fx3-closure/`，完整閉合 **P1 至 P9 全 9 項（9/9）+ Fan + 藍圖 §3 五大核心相機功能路由與 ELF 動態符號閉包核驗 + 藍圖 `U4` 存儲掛載容錯審計 + 跨機型 RAM-Shadow `BK4\0` 備份合成校驗 + 藍圖 `U5` 引導選擇器單次防黏連契約閉環 + 藍圖 `U3` `0xfa0080` Bank 0/1 DDR 非重疊校驗 + Phase 8 `cxd90057.dtb` FDT SoC 兼容與 `.ko` `vermagic` / `__versions` CRC 完整性核驗 + Stage-A RAM-Overlay CPIO + 四層防磚回退演練 + Tier-0 + 12 道安全門**：

| 模組路徑 | 覆蓋項 | 職責說明 |
| --- | :---: | --- |
| `outputs/fx6-on-fx3-closure/fx6_closure/elf_verify.py` | 基礎設施 | ELF64 AArch64 `PT_LOAD`（`ET_DYN`/`ET_EXEC`）與 `ET_REL`（`.ko` 節表）文件偏移映射器，強制校驗權限與 `NOBITS` 邊界。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py` | **P1, P3, P4, P8, P9, Fan** | 7 個目標二進制組件兼容適配規範、冪等啟動掛載片段生成器與 100% SHA-256 逆向回滾校驗器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/vfat_builder.py` | **P2** | `/etc/opelog` 純 Python 確定性 VFAT（FAT16 / FAT32）內存鏡像構建器與 BPB / 雙 FAT 表 / `/OPE/{00,01}` 目錄樹審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/nd_unicorn_verifier.py` | **P3, P4, P8, P9, Fan** | P3、P4（576 組參數笛卡爾掃描）、P8、P9（空指針回調防護）、Fan（溫控備份有效標誌）Unicorn AArch64 指令級驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/uipc_completion_verifier.py` | **P5, P6** | 隊列 `0x92840747` 上 `0x032d -> 0x132d`（P5）與 `0x0400/0x0402/0x0404/0x0152 -> 0x1400/0x1402/0x1404/0x1152`（P6）精確字節級 12B 完結回執合成器與 `send_and_wait_cmp_i` Unicorn 驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/backup_bridge_verifier.py` | **P7** | 內核態 Backup Sync100 地址無關橋接核驗器：雙內核 `pcidma_transfer_async` 16B 序言、`api+0x160` / `api+0x10` Unicorn 跳板、`dst=0x903e0811`/`op=0x30` 40B 請求與同步 `backupfile_cb_getcp(0, NULL)` DMA 回調契約。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/feature_routing_verifier.py` | **藍圖 §3 五大功能路由** | **維度 A**：10 核心庫 ELF64 `DT_NEEDED`（43 節點全傳遞閉包，0 缺失）與 `.dynsym` 導入/導出審計；**維度 B**：Sony `17^3`/`33^3` `.cube` 生成/校驗器、FX3 `p30`（`48 MiB`）16 組 LUT 簇容量預算證明與 `libInfraSetupFile.so` `RcvThread`（`0x196c8..0x196e0`）掛載鏈核驗；**維度 C**：Cine EI / E 卡口 AF 契約與 `set_eye_af_mode_i` + `libmpr.so` `libXavcMxfGetSlotTypeFromMediaId`（`+0x53c850`）Unicorn 實跑驗證。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/backup_mount_tolerance_verifier.py` | **藍圖 `U4` + RAM-Shadow `BK4\0`** | **維度 A（關閉 `U4`）**：`libInfraSetupFile.so`（`RcvThread` `@ 0x19650`）與 `libInfraKikiLogGenerator.so`（`KikiLogGenerator_res_ope` `@ 0x3cb0`）掛載返回碼與降級控制流靜態指令釘選 + Unicorn AArch64 實跑核驗；**維度 B**：FX6 6.01 vs FX3 7.02 `libbackup.so` / `BK4\0` 跨機型鍵模式審計與零寫閃存 RAM-Shadow `BK4\0` 容器合成/校驗器（兼容 `fx3_safety.boot_contracts.parse_bk4_record`）。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/boot_selector_and_bank_verifier.py` | **藍圖 `U5` + 藍圖 `U3`** | **維度 A（關閉 `U5`）**：`up.sh`、`ud_send_lsi.elf`（`0x400990..0x400ad8` 靜態釘選 + Unicorn AArch64 全 7 模式實跑捕獲 `0x804b0376` 4B 載荷）與 `loader_nor.bin`（`0xFE049000` 雙重引導仲裁）單次防黏連契約核驗；**維度 B（推進 `U3`）**：FX3 / FX6 `0xfa0080` Bank 0 / Bank 1 全 64 槽位（`64 x 144 = 9,216 B`）DDR 區間兩兩 **0 重疊**證明與 `+0xE0000` / `+0x14000` 校準偏移審計。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/kernel_dtb_compatibility_verifier.py` | **Phase 8 FDT + `.ko` 完整性** | **維度 A**：純 Python Devicetree v0.4（`0xd00dfeed`）解析器與 FX3 vs FX6 `cxd90057.dtb`（68 節點 / 493 屬性 100% 逐字節一致）、`loadaddr.txt`（100% 一致）及 `kemco.txt`（7 段 `memrsv=` 100% 一致）SoC MMIO 兼容審計；**維度 B**：ELF64 `ET_REL` `.ko` `.modinfo`（`vermagic`）與 64B `struct modversion_info`（`__versions`）CRC 解析器，證明 `P9` `upm.ko` 100% 保留 `vermagic` 與 61 項符號 CRC，並量化跨內核混載 `.ko` 的 `vermagic` 與 `SHN_UNDEF` 風險。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/ram_overlay_packager.py` | **Stage-A CPIO** | 純 Python SVR4 `cpio newc`（`070701` 魔數、4 字節對齊、`TRAILER!!!` 哨兵）確定性歸檔封裝器與解析審計器，組裝 `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}`。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/rollback_drill.py` | **四層防磚演練** | Stage-A 啟動守衛確定性狀態機與 `PREFIX` 隔離沙盒 POSIX `/bin/sh` 子進程實跑演練器（覆蓋無授權標記、單次啟動+重啟恢復、SHA-256 失配/缺失回退、超時/非零退出回退與 eMMC 零寫入核驗）。 |
| `outputs/fx6-on-fx3-closure/native/tier0_backup_worker.c` & `tier0_unicorn_verifier.py` | **Tier-0** | 零外部 `UND` 符號、零動態重定位 AArch64 Linux 雙遍只讀備份組件與 Unicorn 系統調用審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py` & `__main__.py` | **12-Gate 聯調** | `TemporaryDirectory` 端到端離線候選包乾跑組裝器與 `fx3-safety` 12 道安全門評估器 CLI（含 `verify-feature-routing`、`verify-backup-mount-contracts`、`verify-boot-selector-banks`、`verify-kernel-dtb` 與 `run-rollback-drill` 子命令）。 |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py` | 全矩陣單測 | 完整自動化單元測試套件（**40 項測試**，外加 `outputs/fx3-safety/tests` **13 項測試**）。 |

---

## 2. 二進制兼容適配矩陣（P1 / P3 / P4 / P8 / P9 / Fan）偏移與 SHA-256 回滾表

| 規範 ID | 變更字節數 | 原始基準 SHA-256 | 適配後 SHA-256 | 逆向回滾 SHA-256 | 100% 還原 |
| --- | ---: | --- | --- | --- | :---: |
| `P1_libInfraSetupFile` | 1 B | `b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357` | `69bf006e4efb7bbb236bc313e5c6ff7e7935f8899136db7d06ca5405ebe45c4b` | `b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357` | PASS |
| `P1_libInfraMediaCommon` | 1 B | `acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd` | `d9466fa9211dd31101aef80286913a961cfe3bfc81420150d7243a955ba6acc3` | `acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd` | PASS |
| `P1_libInfraMediaConfig` | 1 B | `9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3` | `295a34e274bbb2e660bf56b438bf0f858e66d699463c62dbf1a626951ce3ffc0` | `9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3` | PASS |
| `P3_libInfraAppRemoteBoard` | 16 B | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | `2426911919397ab51ef35a914feb89674d35522cb928280bae510b4f06723572` | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | PASS |
| `P1_P4_P8_appFw_combined` | 17 B | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `95f46b6c1e3738b3f89ef2c4a3cae4160455114cb35cf0542ab71f117436d9f0` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | PASS |
| `P9_upm_ko` | 4 B | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | `5be2aa0b6d6c0a31bb7802400fcd688a980583a08e945245adad7700b9882994` | `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e` | PASS |
| `Fan_libfan` | 8 B | `d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850` | `456c3da53257c0266c9773264091fbcd928cb2fe9c3c169ab7fb986aa8fdc1b8` | `d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850` | PASS |

---

## 3. P2 `/etc/opelog` VFAT 鏡像與 P5 / P6 UIPC / P7 Backup Sync100 驗證摘要

1. **P2 8 MiB RAM VFAT (`8m_ram`)**：`FAT16`、`8,388,608 B`（`16,220` 簇）、雙 FAT 完全鏡像、預建 `/OPE/{00,01}`，確定性 SHA-256 `48c2123efbfb93da4b797190c2e223ac76dbe47a80c2f4efe7d7fc07127663e4`。
2. **P5 / P6 UIPC 完結回執（隊列 `0x92840747`）**：Unicorn 實跑 `send_and_wait_cmp_i`（`0x20ef604..0x20ef7ec`）與 `0x20edd1c` 狀態映射器，5 組正向命令（`0x032d`、`0x0400`、`0x0402`、`0x0404`、`0x0152`）斷言行 `1075` 命中 **0 次** 且 AP 狀態均為 `0`；負向故障注入精準捕獲行 `1075` 與 `0x6f` 錯誤映射。
3. **P7 內核態 Backup Sync100 橋接**：FX3（`0xffffff80083220c8`）與 FX6（`0xffffff8008322f70`）`pcidma_transfer_async` 前 32B 簽名完全一致（`65eb42727e89bfd745f3c40a2625bb10bd7ef8f01de5f5a881525976c4eb07f2`），Unicorn 跳板雙內核 `api+0x160` / `api+0x10` 驗證通過，`dst=0x903e0811` / `op=0x30` 鎖定–1,369,580B DMA 同步回調–解鎖全閉環通過。

---

## 4. Phase 4：Stage-A 零寫閃存 RAM-Overlay CPIO `newc` 封裝與四層防磚回退演練

- **確定性歸檔大小與 SHA-256**：`19,696 B`（`19696 % 4 == 0`），跨次構建 100% 重現 SHA-256：`1871c6a0832f2c750a2ad675dea65bad5cd8567f953875f7b565a47d326895f6`。
- **四場景沙盒 `/bin/sh` 實跑演練**：覆蓋 `S1`（未放置令牌啟動原機 FX3）、`S2`（單次令牌啟動前即刪 + 二次重啟自動回退原機）、`S3a/S3b`（SHA-256 失配 / 組件缺失回退）、`S4a/S4b`（子進程 `exit 139` / `1s` 看門狗超時回退），模擬只讀 eMMC 分區（`sector0/p2/p6/p15/p18`）全程寫入次數 **0 次**。

---

## 5. Phase 5：五大核心相機功能路由與跨機型 ELF 動態符號閉包核驗（藍圖 §3）

### 5.1 核驗維度 A：10 大核心相機功能庫 `DT_NEEDED` 與 `.dynsym` 動態符號閉包審計

結合 FX6 用戶態庫目錄（`nflasha15-files/lib`）、FX6 initrd 基礎庫（`nested-files/nflasha1-initrd/lib`）與宿主 `im.elf` 進行全圖傳遞依賴與符號解析：
- **傳遞依賴閉包**：共解析 **43 個** ELF64 共享對象，`missing_transitive_needed = ()`（**0 缺失**）。
- **核心符號規模**：10 大核心庫合計導出 **10,223** 個動態符號，強導入 **2,419** 個動態符號（解析 **2,315** 個；其中 **8 個核心庫強導入解析率 100.0%**，僅 `appFw.so` 與 `libmpr.so` 存在少量未調用廣播/消費級 SDK 惰性 PLT 槽位且均確認 `bind_now = False`）。
- **19 個五大核心功能關鍵接口符號 VMA 與文件偏移 100% 精確核驗通過**：

| 核心庫名稱 | 文件大小 | `DT_NEEDED` 數 | 缺失依賴 | `.dynsym` 導出數 | 強導入數（已解析） | 代表性已核驗核心符號與 VMA |
| --- | ---: | :---: | :---: | ---: | ---: | --- |
| `appFw.so` | 50,520,424 B | 13 | 0 | 1 | 900 (882) | 導入 `mpr::SetLutData`、`GRM_fbrmUnlockSwap`、`ux::wgtsys::Widget` |
| `libuxengine.so` | 742,128 B | 21 | 0 | 3,476 | 427 (427) | `ux::gfxeng::Screen::setAreaInFramebuffer` (`0x7b66c`), `Widget::setSize` (`0xa2368`) |
| `libgrm.so` | 265,376 B | 10 | 0 | 1,119 | 192 (192) | `grm::FrameBuffer::setSize` (`0x2303c`) |
| `libInfraSetupFile.so` | 202,664 B | 10 | 0 | 602 | 115 (115) | `SetupFile::RcvThread` (`0x19650`), `MOUNT_PATH` (`0x25e90`), `LutFileIntMemory::HOME_PATH` (`0x286c8`) |
| `libInfraLensCommunicator.so` | 14,544 B | 7 | 0 | 27 | 20 (20) | `LensCommunicator::LensCommunicator` (`0x16e0`), `FinalizeCmd` (`0x18a4`), `LensCommunicator_Exit` (`0x229c`) |
| `libInfraMediaMount.so` | 65,392 B | 7 | 0 | 133 | 100 (100) | `IMM_Mount` (`0x819c`), `InfraMediaMountThread::StartThread` (`0xaa38`) |
| `libInfraMediaCommon.so` | 402,624 B | 7 | 0 | 473 | 101 (101) | `mcmn_drv_nvme_ioctl_io_cmd` (`0x31d50`), `mcmn_drv_scsi_open` (`0x3e530`) |
| `libInfraMediaConfig.so` | 52,312 B | 7 | 0 | 101 | 53 (53) | `IMCFG_Offset2MediaId` (`0x7210`), `InfraMediaConfig::GetMediaNum` (`0x4610`) |
| `libmpr.so` | 28,921,824 B | 8 | 0 | 4,271 | 490 (404) | `mpr::SetLutData` (`0x1505a8`), `mpr::ExecuteSetLutData` (`0x150358`) |
| `libfan.so` | 31,176 B | 7 | 0 | 20 | 21 (21) | `fan_infra_init` (`0x1c80`), `fan_i_bkup_is_valid` (`0x1dec`) |

### 5.2 核驗維度 B：16 組用戶 3D `.cube` LUT 規格校驗、FX3 `p30`（48 MiB）容量預算與 `RcvThread` 掛載鏈

1. **確定性 Sony `.cube` 生成與嚴格語法校驗器**：支持 `17^3`（`4,913` 組浮點 RGB 三元組，`137,730 B`）與 `33^3`（`35,937` 組浮點 RGB 三元組，`1,006,406 B`）標準網格，強制校驗雙引號 `TITLE`、`LUT_3D_SIZE`、`DOMAIN_MIN < DOMAIN_MAX` 及三通道定義域邊界，並攔截 `LUT_1D_SIZE`、非標尺寸、行數截斷與越界浮點值。
2. **FX3 `p30`（`0x00018000` 扇區 = `48.00 MiB` = `50,331,648 B`）VFAT 簇分配數學證明**（以 `8 KiB` 簇計）：
   - VFAT 系統開銷（32 保留扇區 + 雙份 FAT 表 + 根目錄與 `/usr/data/lut` 目錄簇 + 64 簇系統索引預留）：`615,424 B`（`0.59 MiB`），可用數據區 `49,716,224 B`（`47.41 MiB`）。
   - **16 組滿規格 `33^3` `.cube` 標準文件簇佔用**：`16,121,856 B`（`15.38 MiB`），剩餘可用空間 **`33,594,368 B`（`32.04 MiB`，餘量 `66.75%`）**。
   - **16 組極端冗長註釋版 `33^3` `.cube`（`1.44 MiB`/個）簇佔用**：`23,068,672 B`（`22.00 MiB`），剩餘可用空間 **`26,647,552 B`（`25.41 MiB`，餘量 `52.94%`）**。
3. **`libInfraSetupFile.so` `SetupFile::RcvThread`（`0x19650`）掛載調用鏈二進制核驗**：
   - `0x196c8..0x196e0` 精確裝載 `x0 = [GOT 0x3ffb8]`（`_ZN14InfraSetupFile9SetupFile10MOUNT_PATHE` @ `0x25e90`：源值 `"/dev/nflasha20"`，經 P1 適配為 `"/dev/nflasha30"`）、`x1 = [GOT 0x3fd70]`（`_ZN14InfraSetupFile16LutFileIntMemory9HOME_PATHE` @ `0x286c8`：`"/usr/data/lut/"`）、`x2 = "vfat"`（`0x2665d`）、`x3 = 0xc0ed0480`、`x4 = "posix_attr"`（`0x26652`），並於 `0x196e0` 調用 `bl 0x144f0`（`mount@plt`）。

### 5.3 核驗維度 C：Cine EI / E 卡口自動對焦契約與雙卡槽 `libmpr.so` Unicorn AArch64 實跑驗證

1. **`appFw.so` 與 `libInfraLensCommunicator.so` 契約核驗**：
   - `set_base_picture_setting_procam_i`（`0x21126d8`，序言 `0xa9ba7bfd`，`cmp w0, #3` 校驗 Cine EI / Cine EI Quick / Custom 拍攝基準模式枚舉，簽名串 `0x261bf40`）。
   - `set_user_lut_binary_data_procam_i`（`0x2112b10`，序言 `0xa9be7bfd`，簽名串 `0x261c0c0`）串聯 `libmpr.so` `_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE`（`0x1505a8`）。
   - `set_af_area_i`（`0x211066c`，`cmp w0, #6`，簽名串 `0x261cc98`）與 `set_eye_af_mode_i`（`0x2110e44`，簽名串 `0x26191e8`）：Unicorn AArch64 實跑 `set_eye_af_mode_i` 證明 `mode=0 -> [x1+8]=1`、`mode=1 -> [x1+8]=0` 零斷言且 `SP` 守恆，`mode=2` 精確觸發 `0x2167784` 斷言輔助函數。
2. **`libmpr.so` 雙卡槽映射函數 `libXavcMxfGetSlotTypeFromMediaId`（`+0x53c850`）Unicorn AArch64 實跑結果**：

| 輸入 `media_id` | 物理語義 | Unicorn 原始返回枚舉 (`MEDIASLOTTYPE`) | 歸一化槽位索引 (`slot_index`) | 斷言觸發 (`assert_hit`) | 斷言位置與函數簽名 | `SP` 守恆 |
| :---: | --- | :---: | :---: | :---: | --- | :---: |
| `0x1000` | CFexpress Type A / SDXC **Slot A** | `1` | **`0`** | `False` | — | `True` |
| `0x1010` | CFexpress Type A / SDXC **Slot B** | `2` | **`1`** | `False` | — | `True` |
| `0x0000` | 未初始化 `media_id` | — | — | **`True`** | `libXavcMxf.cpp:274` (`MEDIASLOTTYPE libXavcMxfGetSlotTypeFromMediaId(uint32_t)`) | — |
| `0x2000` | 非法越界 `media_id` | — | — | **`True`** | `libXavcMxf.cpp:274` (`MEDIASLOTTYPE libXavcMxfGetSlotTypeFromMediaId(uint32_t)`) | — |

---

## 6. Phase 6：存儲掛載容錯審計（關閉藍圖 `U4`）與跨機型 RAM-Shadow `BK4\0` 備份合成核驗

### 6.1 核驗維度 A：存儲掛載返回碼與降級契約靜態釘選 + Unicorn AArch64 實跑（關閉 `U4`）

針對 FX6 只讀源庫 `libInfraSetupFile.so`（`202,664 B`，SHA-256 `b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357`）與 `libInfraKikiLogGenerator.so`（`27,256 B`，SHA-256 `be7abc37ceb019b203a3853eba633d5d703d86d9a24ec2a6081b74873dd71917`），完成完整指令字級釘選與 Unicorn AArch64 控制流微執行：

| 目標庫與函數 | 關鍵 VMA | 機器碼字（LE u32） | 匯編指令與參數語義 | `mount_rc = 0`（啟用 P1 / P2）行為 | `mount_rc = -1`（`ENOENT=2` / `EINVAL=22`）行為 |
| --- | :---: | :---: | --- | --- | --- |
| `libInfraSetupFile.so`<br>`SetupFile::RcvThread`<br>(`0x19650..0x197f4`) | `0x196c8`<br>`0x196d0`<br>`0x196d8`<br>`0x196dc`<br>`0x196e0`<br>`0x196e4`<br>`0x196e8`<br>`0x196f0`<br>`0x19710`<br>`0x19744` | `0xd2809003`<br>`0xf946bb01`<br>`0xf947dc00`<br>`0xf2b81da3`<br>`0x97ffeb84`<br>`0x34000180`<br>`0x97ffedc2`<br>`0x97ffeb18`<br>`0x97ffec08`<br>`0x97ffeac9` | `mov x3, #0x480`<br>`ldr x1, [x24, #0xd70]` (`"/usr/data/lut/"`)<br>`ldr x0, [x0, #0xfb8]` (`"/dev/nflasha20"` -> P1 `"/dev/nflasha30"`)<br>`movk x3, #0xc0ed, lsl #16` (`0xc0ed0480`)<br>`bl 0x144f0 <mount@plt>`<br>`cbz w0, 0x19714`<br>`bl 0x14df0 <__errno_location@plt>`<br>`bl 0x14350 <strerror@plt>`<br>`bl 0x14730 <SetupFileLogTextRec@plt>` (line `304`)<br>`bl 0x14270 <osal_rcv_msg_tmo@plt>` (`0x01de05a5`) | `cbz w0, 0x19714` 直接跳過錯誤分支，**0 次錯誤日誌**，進入 `osal_rcv_msg_tmo(0x01de05a5)` 正常消息循環，`/usr/data/lut/` VFAT 持久化完全可用。 | 讀取 `*errno` -> `strerror` -> 記錄 1 條 `[InfraSetupFile][ERR]:SetupFile::RcvThread:304: mount error.`，隨後**自然順序落入 `0x19714 -> 0x19744` 消息循環**（零異常/零崩潰，僅缺失 LUT VFAT 持久化）。 |
| `libInfraKikiLogGenerator.so`<br>`KikiLogGenerator_init_ope` (`0x3dfc`) -> `KikiLogGenerator_res_ope` (`0x3cb0..0x3df8`) | `0x3d04`<br>`0x3d34`<br>`0x3d3c`<br>`0x3d48`<br>`0x3d4c`<br>`0x3d6c`<br>`0x3d70`<br>`0x3d7c`<br>`0x3d80`<br>`0x3df0` | `0x97fff907`<br>`0xd2809203`<br>`0xf2b81da3`<br>`0x97fff8ba`<br>`0x910da280`<br>`0x97fff8ed`<br>`0x340000a0`<br>`0x7100441f`<br>`0x54000301`<br>`0xd65f03c0` | `bl 0x2120 <mkdir@plt>` (`"/etc/opelog/"`, `0770`)<br>`mov x3, #0x490`<br>`movk x3, #0xc0ed, lsl #16` (`0xc0ed0490`)<br>`bl 0x2030 <mount@plt>` (`"/dev/nflasha21"`, `"/etc/opelog/"`, `"vfat"`)<br>**`add x0, x20, #0x368`**（直接覆蓋 `x0`，未檢查 `mount` 返回值）<br>`bl 0x2120 <mkdir@plt>` (`"/etc/opelog/logs/"`)<br>`cbz w0, 0x3d84`<br>`cmp w0, #0x11` (`EEXIST`)<br>`b.ne 0x3de0`（乾淨尾聲）<br>`ret` | `mount` 成功後 `mkdir("/etc/opelog/logs/")` 返回 `0`，按 Backup 鍵 `0x0110000c` 創建 `/etc/opelog/logs/000/`..`002/` 並於 `0x3df0` 乾淨返回（`SP` 守恆）。 | `0x3d4c` 忽略 `mount = -1`，隨後 `mkdir("/etc/opelog/logs/")` 在只讀根文件系統返回 `-1`（`EROFS=30 != 0x11`），由 `0x3d80 b.ne 0x3de0` **乾淨跳轉函數尾聲並於 `0x3df0` 返回**（零異常/零崩潰，僅停用運行日誌落盤）。 |

Unicorn AArch64 全部 6 組微執行場景結果匯總（`u4_closed = True`）：

| 庫名 | Unicorn 場景 ID | `mount_rc` / `errno` | 錯誤分支 / 日誌計數 | 後續控制流落點 / 創建目錄 | `abort_or_fault` | 結論 |
| --- | --- | :---: | :---: | --- | :---: | :---: |
| `libInfraSetupFile.so` | `P1_ADAPTED_MOUNT_OK` | `0` / `0` | `False` / `0` | `osal_rcv_msg_tmo(0x01de05a5)` | `False` | PASS |
| `libInfraSetupFile.so` | `UNADAPTED_P20_MOUNT_ENOENT` | `-1` / `2 (ENOENT)` | `True` / `1` (`line 304`) | 落入 `0x19714 -> osal_rcv_msg_tmo(0x01de05a5)` | `False` | PASS |
| `libInfraSetupFile.so` | `UNADAPTED_P20_MOUNT_EINVAL` | `-1` / `22 (EINVAL)` | `True` / `1` (`line 304`) | 落入 `0x19714 -> osal_rcv_msg_tmo(0x01de05a5)` | `False` | PASS |
| `libInfraKikiLogGenerator.so` | `P2_LOOPBACK_MOUNT_OK` | `0` / `0` | `False` / `0` | 創建 `/etc/opelog/logs/{000,001,002}/` -> `0x3df0 ret` (`SP` 守恆) | `False` | PASS |
| `libInfraKikiLogGenerator.so` | `UNADAPTED_P21_MOUNT_ENOENT_EROFS` | `-1` / `2 -> 30 (EROFS)` | `mkdir != EEXIST` | `0x3d80 -> 0x3de0 -> 0x3df0 ret`（`subdirs=()`，`SP` 守恆） | `False` | PASS |
| `libInfraKikiLogGenerator.so` | `UNADAPTED_P21_MOUNT_EINVAL_EROFS` | `-1` / `22 -> 30 (EROFS)` | `mkdir != EEXIST` | `0x3d80 -> 0x3de0 -> 0x3df0 ret`（`subdirs=()`，`SP` 守恆） | `False` | PASS |

### 6.2 核驗維度 B：跨機型 `BK4\0` 備份模式審計與零寫閃存 RAM-Shadow `BK4\0` 合成校驗器

1. **跨機型 Backup 庫與數據種子契約核驗**：
   - **ABI 兼容性**：FX6 6.01 `libbackup.so`（`14,232 B`，SHA-256 `e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f`，導出 **56 個** `Backup_*`/`backup_*` 符號）為 FX3 `libbackup.so`（`18,344 B`，SHA-256 `5c1ede86e363bbc718063299833b905985f4a254f5b4d25ad81fce62e253daeb`，導出 **58 個**符號）的 **100% 嚴格子集**（`missing_in_fx3 = ()`，FX3 僅新增 `Backup_protect_data_ash` 與 `Backup_sync_protect_data`）；同時核驗 `libBackupManager.so`（`10,272 B`，SHA-256 `ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e`）導出 `_Z11BkDmn_writejPKvi` 與 `backup-section-audit.json`（`.text+0x75c` = 文件偏移 `0x7c4`）。
   - **關鍵跨機型差異定位**：對比 FX6 `CX95898_NTSC.bin`（`2,253,333 B`，`840` 子系統 / `40,647` 鍵）與 FX3 `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`819` 子系統 / `35,668` 鍵）及 `backup-key-values.txt`：
     - **存儲槽位映射（`0x00cf0000..0x00cf00bf` + `0x807b002b`）**：FX3 在第 3 組槽位（`0x00cf0080`）攜帶 `mediaId = 0x1002`（`devId = 0xd51b`），而 FX6 `libmpr.so`（`libXavcMxfGetSlotTypeFromMediaId`）僅允許雙卡槽 `{0x1000, 0x1010}`（遇 `0x1002` 觸發斷言）；RAM-Shadow 覆蓋層保留 `0x1000`（Slot A）與 `0x1010`（Slot B）並將第 3 槽清零裁剪為 `0x0000`，同時提供 16B `0x807b002b` Dual-Slot 描述符。
     - **顯示面板路由（`0x02cf0214` / `0x02cf0218`）**：FX6 為 1 字節枚舉（`00` / `01`），FX3 為 4 字節重複值（`16161616` / `19191919`），RAM-Shadow 覆蓋層精確提供 FX6 契約的 1B `0x00` / `0x01`。
2. **零寫閃存 RAM-Shadow `BK4\0` 容器合成與雙重校驗結果**：
   - **確定性產物**：容器總長 **`20,588 B`**，跨 840 個子系統描述符合成 **199 個**冷啟動與雙槽兼容屬性鍵，確定性 SHA-256 為 **`e87030488731ed5133ddd727f6213d9984adfddc88ed12b782a180b8c6aa0d41`**。
   - **雙層校驗和與安全不變量**：外層 16 字節 `BK4\0` 頭通過 `loader_nor.bin`（`0xfe04d514`）32 位字節累加校驗和與 `fx3_safety.boot_contracts.parse_bk4_record` 核驗；內層全部變長屬性通過 `CRC-16/CCITT-FALSE`（`attr = 0x00c0`）逐鍵校驗；強制鎖定 `flash_write_allowed = False`（物理 `p2:/setting/Backup.bin` 零修改）且 `0x00fa0080` 偏移 `8` 選擇字節恆為 **`0x00`**（Normal Boot `p3`：`\av-cam.bin` / `\initrd.img` / `\vmlinux.bin`，`strict_loader_selectable = False`），並包含 `0x00fa0028 = 0x429200000` 與 `0x00fa005d = 0x100000` FixedArea 契約。
   - **6 項負向突變攔截全通過**：篡改魔數（`BK3\0`）、截斷載荷、篡改外層 32 位校驗和、將 `0x00fa0080` byte 8 改為 `0x01`（Update Mode 紅線）、注入非法媒體槽位 ID（`0x1002` / `0x2000`）以及置位 `flash_write_allowed = True` 均被 `audit_ram_shadow_bk4` 100% 攔截。

---

## 7. Phase 7 維度 A：引導選擇器單次防黏連契約核驗（關閉藍圖 `U5`：`up.sh` + `ud_send_lsi.elf` + `loader_nor.bin`）

### 7.1 只讀源工件跨機型 SHA-256 與 `PT_LOAD` 完全一致證明

- `up.sh`（`6,572 B`，SHA-256 `c774320a0ab92c13b467b9219e1f60262a1effa0b551ba3b713514a36dadc402`）與 `common.src`（`3,287 B`，SHA-256 `3d5334ab1698d67176f8fd35ffd4d7a9a9b85a1625b20cf128ba091f752b90a0`）。
- 三份 `ud_send_lsi.elf`（均為 `10,248 B`、`ET_EXEC`、`e_entry = 0x400ae0`）：FX6 `p15:/bin/ud_send_lsi.elf`（`d0ece6ca...`）與 FX6 `p1-initrd:/usr/bin/ud_send_lsi.elf` / FX3 `2.05:/usr/bin/ud_send_lsi.elf`（`9fb4bd02...`）在**全部可裝載段 `PT_LOAD`（文件偏移 `0x0000..0x2070`）100% 逐字節一致**，全文件僅在非裝載 `.comment` 節相差 **7 字節**（編譯器日期字符串 `20240928` vs `20180315`）。
- `loader_nor.bin`（`101,888 B`，鏈接基址 Octal-SPI NOR SRAM `0xFE049000`，SHA-256 `4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`）與 `LdrBkupList.txt`（`650 B`，**65 個冷啟動備份鍵**，與 `loader_nor.bin` `0xFE0615D8` 處 `LBK_LIST(...)` 完全一致）。

### 7.2 `ud_send_lsi.elf`（`main` `@ 0x400990..0x400ad8`）與 `loader_nor.bin`（`0xFE049000`）關鍵指令 VMA 表

| 目標二進制 | 虛擬地址 (VMA) | 文件偏移 | 機器碼字 (LE u32) | 匯編指令與引導選擇器語義 |
| --- | :---: | :---: | :---: | --- |
| `ud_send_lsi.elf` | `0x400994` | `0x0994` | `0x7100081f` | `cmp w0, #2`（校驗 `argc == 2`，否則 `bl 0x400950 <exit@plt>` 返回 `1`） |
| `ud_send_lsi.elf` | `0x4009b4`..`0x4009b8` | `0x09b4` | `0x52a00960` / `0x97ffffde` | `mov w0, #0x4b0000; bl 0x400930 <Backup_read@plt>`（讀取 1B `lsi_type` 鍵 `0x004b0000`） |
| `ud_send_lsi.elf` | `0x4009e0`..`0x4009ec` | `0x09e0` | `0x51000400`..`0x540001e8` | `sub w0, w0, #1; uxtb w0, w0; cmp w0, #1; b.hi 0x400a28`（僅 `lsi_type in {1 (LSI_MAIN), 2 (LSI_SUB)}` 發送 UIPC；出廠冷種子 `0x03` 乾淨跳過並返回 `0`） |
| `ud_send_lsi.elf` | `0x4009f4`..`0x400a04` | `0x09f4` | `0x52806ec0`..`0x97ffffbf` | `osal_valloc_msg_wait(dst=0x804b0376, &msg, size=4, wait=1)`（低 16 位隊列號 `0x0376`） |
| `ud_send_lsi.elf` | `0x400a3c`..`0x400a44` | `0x0a3c` | `0x52806f21`..`0x97ffffa3` | `osal_set_msg_src(msg, src=0x004b0379)`（應答隊列 `0x004b0379`） |
| `ud_send_lsi.elf` | `0x400a4c`..`0x400a64` | `0x0a4c` | `0x97ffffb1`..`0x97ffff9f` | `atoi(argv[1])` -> `str w0, [x19]`（寫入 **4 字節小端 `uint32` 模式載荷**）-> `osal_snd_msg(0x804b0376, msg)` |
| `ud_send_lsi.elf` | `0x400aa4`..`0x400ab8` | `0x0aa4` | `0x52817702`..`0x12807fa0` | `osal_rcv_msg_tmo(0x004b0379, &msg, 3000)`，容忍 `0` 與 `-0x3fe`（`-1022` `OSAL_E_TMO`），隨後 `osal_free_msg` |
| `loader_nor.bin` | `0xFE054AF8`..`0xFE054B00` | `0x0BAF8` | `0x34000088` / `0x320007f6` | 優先檢查 Sub-LSI ANK 鎖存標誌：若非零則直接鎖定 `BootMode[3] = "updater"` |
| `loader_nor.bin` | `0xFE053CA0`..`0xFE053D08` | `0x0ACA0` | `0x52800514`..`0xb9000280` | 檢查黏連寄存器 `0xFE170028`，掛載 FAT `p2:/setting` 並探測 `\updater\mode`（`0xFE05EDAB`），存在則寫入 `[0xFE170028] = 1` 進入 `p1` 更新模式（`0xFE057FFC` / `0xFE058014` 同步過濾 `\updater\mode` 與 `\mode\cmode`） |
| `loader_nor.bin` | `0xFE04C7A8` -> `0xFE04D584` | `0x037A8` | `0x320003e2`..`0x7100051f` | 嚴格 `BK4\0` 記錄選擇器（`w2 = 1`：要求 `word4 == 0xaaaaaaaa` 且 `byte8 == 1`） |

### 7.3 `up.sh` 全 7 種模式與 `ud_send_lsi.elf` Unicorn AArch64 實跑封包佈局表

| `up.sh` 參數 / 分支 | `p2:/setting/updater/` 標誌文件操作 | `mode_num` | Unicorn 捕獲 `dst_queue` -> `src_queue` | Unicorn 捕獲 4B 載荷 (Hex LE) | `timeout_ms` / 返回碼 | `SP` 守恆 |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| 無參切換（清理分支） | `rm -f /setting/updater/mode*` | **`0`** | `0x804b0376` -> `0x004b0379` | **`00000000`** | `3000 ms` / `0` | `True` |
| `up.sh user`（UFP） | `touch mode` | **`2`** | `0x804b0376` -> `0x004b0379` | **`02000000`** | `3000 ms` / `0` | `True` |
| `up.sh serv`（Service） | `touch mode mode3` | **`3`** | `0x804b0376` -> `0x004b0379` | **`03000000`** | `3000 ms` / `0` | `True` |
| 無參切換（置位分支） | `touch mode mode1` | **`4`** | `0x804b0376` -> `0x004b0379` | **`04000000`** | `3000 ms` / `0` | `True` |
| `up.sh ms`（MS Crypt） | `touch mode mode5` | **`5`** | `0x804b0376` -> `0x004b0379` | **`05000000`** | `3000 ms` / `0` | `True` |
| `up.sh ver`（Ver Skip） | `touch mode mode6` | **`6`** | `0x804b0376` -> `0x004b0379` | **`06000000`** | `3000 ms` / `0` | `True` |
| `up.sh file`（File Crypt） | `touch mode mode7` | **`7`** | `0x804b0376` -> `0x004b0379` | **`07000000`** | `3000 ms` / `0` | `True` |
| `p1` 鏡像 + `LSI_SUB=2` + `-0x3fe` | — | **`0`** | `0x804b0376` -> `0x004b0379` | **`00000000`** | `OSAL_E_TMO` 容忍 / `0` | `True` |
| 出廠冷種子 `0x004b0000 = 3` | — | `4` | 不分配/不發送 UIPC | `""`（安全空操作） | — / `0` | `True` |
| 非法參數 `argc != 2` | — | — | `exit(1)` 立即攔截 | `""` | — / `1` | — |

- **關閉藍圖 `U5` 核心證明**：
  1. **RAM-Only `p7` 覆蓋層天然零黏連風險**：全程對 `p1:/updater` 寫入 **0 字節**、對 `p2:/setting/updater/mode*` 寫入 **0 字節**、發送非零 `ud_send_lsi.elf` 封包 **0 次**、且 RAM-Shadow `BK4\0` 偏移 `8` 恆為 `0x00`，`loader_nor.bin` 三條更新觸發路徑（Sub-LSI ANK、`p2:\updater\mode` -> `0xFE170028`、`BK4\0` `byte8==1`）全部保持未武裝狀態。
  2. **`p1` 恢復環境強制雙步復位序列**：`up.sh` 第 295–301 行含 `test -e /root/IAMUPDATER && exit 0` 早退陷阱，在 `p1` 內直接調用 `up.sh` 會在執行 `ud_send_lsi.elf 0` 前退出，遺留 Sub-LSI ANK 鎖存！因此任何未來 `p1` 恢復退出必須原子執行雙步復位：**(Step 1)** `rm -f /setting/updater/mode* && sync` + **(Step 2)** 顯式執行 `/usr/bin/ud_send_lsi.elf 0`（向 `0x804b0376` 發送 `00000000`）。

---

## 8. Phase 7 維度 B：`0xfa0080` Bank 0 / Bank 1 DDR 裝載區間非重疊證明與校準偏移審計（推進藍圖 `U3`）

### 8.1 Bank 0 與 Bank 1 全槽位（`64 x 144 = 9,216 B`）DDR 區間兩兩零重疊表

`loader_nor.bin`（`0xFE054614..0xFE054688`）讀取備份鍵 `0x00fa0080`（上限 `0x2400 = 9,216 B` = **64 槽位 × 144 字節步長**），FX3 `bank0-fa0080.bin`（`7211bc04...`）與 `bank1-fa0080.bin`（`33e39fc7...`）分別與 `FX3-CX95900_ALLLANG-Backup.bin` Record 0 / Record 1 100% 逐字節一致。四張描述符表全部通過 **0 字節兩兩 DDR 重疊**、分區號 `1..30` 邊界與 Bank 0 `byte8 == 0x00` 核驗：

| Bank 編號與機型 | 槽位 `[idx]` / 分區 | `mode` 標誌 | 有效 DDR 半開區間 `[start, end_excl)` | 跨度 (`span`) | 鏡像路徑與跨機型偏移說明 |
| --- | :---: | :---: | :---: | ---: | --- |
| **Bank 0**（FX3 獨有 Sub/BT 4 項） | `[8]` `p3` / `[6]` `p3` / `[7]` `p3` / `[5]` `p2` | `0x08000001` / `0x08000000` | `[0x00fe300000, 0x00fe310000)`、`[0x00fe310000, 0x00fe320000)`、`[0x00fe320000, 0x00fe330000)`、`[0x00fe380000, 0x00fe3c0000)` | `64 KiB` ×3 + `256 KiB` | `\wole_app.bin`、`\btfw32a.tlv`、`\btnv32.bin`、`\bt_conf.cnf`（SRAM 區無重疊） |
| **Bank 0**（FX3 & FX6 共享 AP 5 項） | `[1]` `p2` | `0x01000000` | `[0x0400001000, 0x0400002000)` | `0x1000` (`4 KiB`) | `\kemco.txt`（跨機型偏移 **`0x0`**） |
| **Bank 0**（FX3 & FX6 共享 AP 5 項） | `[4]` `p2` | `0x01000000` | `[0x0400002000, 0x0400006000)` | `0x4000` (`16 KiB`) | `\cxd90057.dtb`（跨機型偏移 **`0x0`**） |
| **Bank 0**（FX3 & FX6 共享 AP 5 項） | `[3]` `p3` | `0x81000000` | `[0x0400080000, 0x0400600000)` | `0x580000` (`5.5 MiB`) | `\vmlinux.bin`（跨機型偏移 **`0x0`**） |
| **Bank 0**（FX3 & FX6 共享 AP 5 項） | `[0]` `p3` | `0x05000000` | `[0x0401000000, 0x0402000000)` | `0x1000000` (`16 MiB`) | `\av-cam.bin`（跨機型偏移 **`0x0`**） |
| **Bank 0**（FX3 & FX6 共享 AP 5 項） | `[2]` `p3` | `0x01000000` | `[0x0408000000, 0x0409000000)` | `0x1000000` (`16 MiB`) | `\initrd.img`（跨機型偏移 **`0x0`**） |
| **Bank 1**（FX3 `[2]` / FX6 `[2]`） | `p8` | `0x07000000` | `[0x0800100000, 0x0800108000)` | `0x8000` (`32 KiB`) | `\tomco.txt`（偏移 **`0x0`**） |
| **Bank 1**（FX3 `[6]` / FX6 `[6]`） | `p8` | `0x81000000` | `[0x0800108000, 0x0802108000)`（原始 `size=0` 動態哨兵 `end=0x0800107fff`，按 32 MiB 保守包絡校驗） | `0x2000000` (`32 MiB`) | `\cpapp-b.bin`（偏移 **`0x0`**，距下一段仍留 `>102 MiB` 安全間隙） |
| **Bank 1**（FX3 `[9]` -> FX6 `[8]`） | `p2` | `0x05000000` | FX3 `[0x0808730000, 0x0808c30000)` -> FX6 `[0x0808810000, 0x0808d10000)` | `0x500000` (`5 MiB`) | `\psd.bin`（校準裝載地址上移 **`+0xE0000` = `+917,504 B`**） |
| **Bank 1**（FX3 `[10]` -> FX6 `[9]`） | `p18` | `0x05000000` | FX3 `[0x0808c30000, 0x0808cb0000)` -> FX6 `[0x0808d10000, 0x0808d90000)` | `0x80000` (`512 KiB`) | `\lensfile.bin`（校準裝載地址上移 **`+0xE0000` = `+917,504 B`**） |
| **Bank 1**（FX3 `[4]` -> FX6 `[5]`） | `p8` | `0x05000000` | FX3 `[0x0808eb0000, 0x0808f1ddd0)` -> FX6 `[0x0808f90000, 0x0808ffddd0)` | `0x6ddd0` (`439.5 KiB`) | `\OldAmtCL.bin`（校準裝載地址上移 **`+0xE0000` = `+917,504 B`**） |
| **Bank 1**（FX3 `[1]`/`[0]` == FX6 `[1]`/`[0]`） | `p3` | `0x05000000` | `[0x0809108000, 0x0809139000)`、`[0x0809139000, 0x0809179000)` | `0x31000` + `0x40000` | `\bonobo.bin`、`\sabin\idt_cam.bin`（偏移 **`0x0`**） |
| **Bank 1**（機型專有槽位） | FX3 `[8]` `p8` vs FX6 `[4]` `p3` | `0x05000000` | FX3 `\cpImg.dat` `[0x0809179000, 0x0809479000)` vs FX6 `\cmrbnb.bin` `[0x0809179000, 0x080918d000)` | `3 MiB` vs `80 KiB` | FX6 以 `80 KiB` (`0x14000`) `\cmrbnb.bin` 取代 FX3 `3 MiB` `\cpImg.dat`（及 `[5]` `\SysSound.bin`） |
| **Bank 1**（FX3 `[7]` -> FX6 `[7]`） | `p2` | `0x05000000` | FX3 `[0x0809479000, 0x0809979000)` -> FX6 `[0x080948d000, 0x080998d000)` | `0x500000` (`5 MiB`) | `\defdet.bin`（校準裝載地址上移 **`+0x14000` = `+81,920 B`**） |
| **Bank 1**（FX3 `[3]` -> FX6 `[3]`） | `p8` | `0x05000000` | FX3 `[0x0809a08e00, 0x0809a21e00)` -> FX6 `[0x0809a1ce00, 0x0809a35e00)` | `0x19000` (`100 KiB`) | `\DmmCfg.bin`（校準裝載地址上移 **`+0x14000` = `+81,920 B`**） |

- **推進藍圖 `U3` 關鍵結論**：FX3 原生 RTOS（`\cpapp-b.bin`）與物理 `p2:/setting/{psd.bin,defdet.bin}`、`p18:/lensfile.bin` 的硬編碼指針嚴格綁定 FX3 Bank 1 DDR 基址（`0x0808730000`、`0x0808c30000`、`0x0809479000`），而 FX6 Bank 1 存在精確 **`+0xE0000`** 與 **`+0x14000`** 雙段平移；因此保留 FX3 物理 `Backup.bin`（Bank 0 / Bank 1 零修改）並在 Linux 用戶態使用 RAM-Shadow `BK4\0` 是保障傳感器/鏡頭校準區零錯位的唯一正確設計。同時審計器對注入 `4 KiB` 重疊、越界分區 `p31`、區間反轉與 Bank 0 `byte8 != 0` 實現 100% 攔截。

---

## 9. Phase 8 維度 A：扁平設備樹（`cxd90057.dtb`，`0xd00dfeed`）SoC MMIO / Carveout 兼容審計

### 9.1 純 Python Devicetree v0.4 解析結果與跨機型 100% 逐字節一致證明

無第三方依賴純 Python FDT（`0xd00dfeed`）解析器嚴格校驗大端文件頭（`version = 17`、`last_comp_version = 16`、`totalsize = 17,131 B`、`off_mem_rsvmap = 40`、`off_dt_struct = 56`、`size_dt_struct = 16,284`、`off_dt_strings = 16,340`、`size_dt_strings = 791`）、4B/8B 對齊、`/memreserve/` 雙零終止符、平衡節點棧與字符串表邊界。對比 FX3 與 FX6 只讀源 `cxd90057.dtb`、`loadaddr.txt` 及 `kemco.txt`：

- **`cxd90057.dtb`（`17,131 B`，SHA-256 `87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca`）**：FX3 與 FX6 **100% 逐字節完全一致**（全部 **68 個 FDT 節點**、**493 項屬性**、**0 項差異**，`mem_rsvmap = ()`）。
- **`loadaddr.txt`（`48 B`，SHA-256 `8c7cc8eb65c40311172f4bf1dc591fe3bcbc1efe689ededdd225142139881452`）**：FX3 與 FX6 **100% 逐字節一致**（`0x400080000,0x408000000,0x400001000,0x400002000`：Kernel `@ 0x400080000`、Initrd `@ 0x408000000`、`kemco.txt` `@ 0x400001000`、DTB `@ 0x400002000`）。

| FDT 節點路徑 | `compatible` / 關鍵屬性 | 物理基址與窗口跨度 (`reg`) | FX3 vs FX6 對比結論 |
| --- | --- | --- | :---: |
| `/` | `compatible = "cxd,cxd90057"`, `model = "CXD90057"`, `#address-cells = 2`, `#size-cells = 2` | SoC 根節點 (`interrupt-parent = <0x1>`) | **100% 一致（0 差異）** |
| `/chosen` | `stdout-path = "serial0:460800n8"`（無內聯 `bootargs`，由引導器自 `0x400001000` `kemco.txt` 注入） | 綁定 `serial0` (`0xf1000000`) `460800 8N1` | **100% 一致（0 差異）** |
| `/memory@400000000` | `device_type = "memory"` | `[0x400000000, 0x600000000)`（`8 GiB` SoC 孔徑，經 `kemco.txt` `mem=2G` 限幅為 `2 GiB`） | **100% 一致（0 差異）** |
| `/esram@0xfe000000`、`/iomem@0xf0000000`、`/iomem2@0xf0000000` | `compatible = "cxd,cxd90057-iomap"`（DTB 無 `/reserved-memory`，靜態映射 + `kemco.txt` `memrsv=`） | `0xfe000000+16MiB` (`memtype=3`)、`0xf0000000+224MiB` (`memtype=1`)、`0xff000000+16MiB` (`memtype=1`) | **100% 一致（0 差異）** |
| `/pcie_ep_dummy` | `phandle = <0x7>`（供全部 5 個 `cxd900xx-pcie-ep` 節點 `memory-region = <0x7>` 引用） | `[0x400000000, 0x400001000)`（`4 KiB` 首頁保留） | **100% 一致（0 差異）** |
| `/cpus/cpu@0`..`cpu@3` + `l2-cache` | `compatible = "arm,cortex-a35"`, `enable-method = "spin-table"` | 4 核 Cortex-A35 SMP (`reg = 0..3`, `next-level-cache = <0xd>`) | **100% 一致（0 差異）** |
| `/interrupt-controller@f13A0000` | `compatible = "arm,gic-400"`, `#interrupt-cells = 3` | GICD `0xf13a1000+4K`、GICC `0xf13a2000+8K`、GICH `0xf13a4000+8K`、GICV `0xf13a6000+8K` | **100% 一致（0 差異）** |
| `/soc/serial@f1000000`..`f1004000` | `compatible = "arm,pl011", "arm,primecell"` (`serial0`..`serial4`) | `0xf1000000..0xf1004000`（各 `4 KiB`，SPI IRQ `0xda..0xde`） | **100% 一致（0 差異）** |
| `/soc/emmc0` | `compatible = "arasan,sdhci"` | eMMC 主控制器節點 | **100% 一致（0 差異）** |
| `/soc/pcie_{c,i,m0,m1,n}` & `*_ep` | 5× `snps,dw-pcie` + 5× `cxd900xx-pcie-ep` (`memory-region = <0x7>`) | 跨核 PCIe / UIPC IPC 硬件通道 | **100% 一致（0 差異）** |

### 9.2 `kemco.txt` 啟動參數與全部 7 段 `memrsv=` DDR Carveout 對比表

對比 FX3 `kemco.txt`（`934 B`，SHA-256 `eb184157...`）與 FX6 `p1` `kemco.txt`（`933 B`，SHA-256 `e7763ad9...`）：33 行參數中 **31 行（含 `mem=2G`、`boottime=0x00020000@0x400020000`、`klog.addr=0x400040000`、`klog.size=0x00040000` 以及全部 7 段兩兩無重疊 `memrsv=` DDR 保留區）100% 逐字一致**，僅 `p1` 更新器鏡像的 `ramdisk_size`（`16384` vs `8192`）與 `initrd` 長度上限（`0x408000000,0x2000000` vs `0x408000000,0x1000000`）存在預期差異：

| `kemco.txt` `memrsv=` 序號 | 物理基址 (`base_addr`) | 保留大小 (`size_bytes`) | 屬性標誌 | 用途與對齊區域 | FX3 vs FX6 |
| :---: | :---: | :---: | :---: | --- | :---: |
| `#0` | `0x400000000` | `0x00001000` (`4 KiB`) | Cached | 對齊 `/pcie_ep_dummy` 首頁保留 | **100% 一致** |
| `#1` | `0x400020000` | `0x00060000` (`384 KiB`) | Cached | 覆蓋 `boottime` (`128K`) + `klog` (`256K`) | **100% 一致** |
| `#2` | `0x403e00000` | `0x00200000` (`2 MiB`) | `:uc` (Uncached) | 跨核共享非緩存 IPC 窗口 | **100% 一致** |
| `#3` | `0x404000000` | `0x02000000` (`32 MiB`) | Cached | 系統共享保留區 | **100% 一致** |
| `#4` | `0x410000000` | `0x00200000` (`2 MiB`) | Cached | IPC 描述符保留區 | **100% 一致** |
| `#5` | `0x410200000` | `0x01e00000` (`30 MiB`) | `:uc` (Uncached) | UIPC / PCIe DMA 非緩存共享池 | **100% 一致** |
| `#6` | `0x47c000000` | `0x04000000` (`64 MiB`) | `:uc` (Uncached) | 頂部 `2 GiB` 邊界非緩存 DMA 保留池 | **100% 一致** |

同時負向故障注入測試確認：篡改魔數（`!= 0xd00dfeed`）、截斷 `totalsize`、`off_dt_struct` 非 4 字節對齊、抹除結尾 `FDT_END`（`0x00000009`）、字符串偏移 `nameoff` 越界及未終止 `/memreserve/` 表均 100% 拋出 `FdtFormatError` 阻斷。

---

## 10. Phase 8 維度 B：內核模組（`.ko`）`vermagic` / `__versions` CRC 完整性與跨內核 ABI 核驗

### 10.1 Sony `!CONFIG_MODVERSIONS` 實證與 `P9`（`upm.ko` `.text+0x136b8`）100% 元數據及 CRC 守恆證明

遍歷 FX3 與 FX6 全部只讀 `.ko` 內核模組確認：Sony 編譯 `4.9.337-scel+` 與 `4.9.186-scel` 內核時均未啟用 `CONFIG_MODVERSIONS`（`.modinfo` 的 `vermagic` 不含 `modversions` 標記，且 ELF64 `ET_REL` 不含 `__versions` 節）。為同時覆蓋原生 `!CONFIG_MODVERSIONS` 與標準 Linux `CONFIG_MODVERSIONS`（64 字節 `struct modversion_info`：`8B LE crc + 56B NUL-padded name`）雙重契約，核驗器對兩類鏡像均完成嚴格驗證：

1. **原生 FX3 `upm.ko`（`453,896 B`，`ba0cca76...` -> `P9` `5be2aa0b...`）**：應用 `P9`（`.text+0x136b8` 4 字節空指針防護適配）後，`.modinfo`（`111 B`，`vermagic = "4.9.337-scel+ SMP preempt mod_unload aarch64"`）SHA-256 **100% 不變**、`.gnu.linkonce.this_module`（`768 B`，`name = "upm"`）SHA-256 **100% 不變**、全部 **60 個 `SHN_UNDEF` 內核導入符號**與 **1 個 `__ksymtab` 導出符號** 100% 不變，且逆向回滾 100% 還原 `ba0cca76...`。
2. **`CONFIG_MODVERSIONS` 儀表化 `upm.ko`（注入 `module_layout` `0x67a19e4b` + 60 個導入符號共 **61 條** 64B `modversion_info` 記錄）**：應用 `P9` 前後 **61 / 61 條 `modversion_info` CRC 100% 逐字節守恆**，證明 `init_module` / `insmod` 絕不可能觸發 `ENOEXEC`（`disagrees about version of symbol`）。

### 10.2 FX3 宿主 9 大 `.ko` 模組與 FX6 運行時（`p15`/`p3`）/ 更新器（`p1`）跨內核對比表

| 模組文件名 | FX3 文件大小 / SHA-256 前綴 | `depends` 依賴閉包 | FX3 `vermagic` | FX6 `p15`/`p3` `vermagic` | FX6 `p1` initrd `vermagic` | `SHN_UNDEF` / 導出數 (FX3 vs FX6) | 跨內核符號 ABI 差異說明 |
| --- | --- | :---: | :---: | :---: | :---: | :---: | --- |
| `backup.ko` | `144,976 B` (`8a8d8c94...`) | `()` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `65/48` vs `65/49` | **ABI 分歧**：FX6 多導出 `Backup_sync_subsystem_for_senser_local` |
| `devno.ko` | `6,344 B` (`cca1d9ac...`) | `()` | `4.9.337-scel+ ...` | 一致 (`p3`) | **`4.9.186-scel ...`（失配）** | `0/1` vs `0/1` | 100% 符號集一致 |
| `osal_uipc.ko` | `76,168 B` (`6aa0f5c8...`) | `('devno',)` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `47/30` vs `47/30` | 100% 符號集一致 |
| `osal_ulogio.ko` | `68,528 B` (`dd65dfdc...`) | `('backup', 'osal_uipc')` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `56/1` vs `56/1` | 100% 符號集一致 |
| `osal_utm.ko` | `10,688 B` (`f6679c64...`) | `()` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `18/9` vs `18/9` | 100% 符號集一致 |
| `stream.ko` | `7,032 B` (`38cadfaf...`) | `()` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `12/1` vs `12/1` | 100% 符號集一致 |
| `udate.ko` | `37,544 B` (`a3cbb997...`) | `('backup',)` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `39/3` vs `39/3` | 100% 符號集一致 |
| `upm.ko` | `453,896 B` (`ba0cca76...`) | `()` | `4.9.337-scel+ ...` | 一致 | 未打包於 `p1` | `60/1` vs `62/1` | **ABI 分歧**：FX6 導入 `Backup_sync_subsystem_for_senser_local`、`pcie_link_width_check_dev_state_ch0` 等 5 符號，缺失 FX3 `pcie_get_link_speed` 等 3 符號 |
| `utimer.ko` | `33,904 B` (`42740030...`) | `('osal_uipc',)` | `4.9.337-scel+ ...` | 一致 | **`4.9.186-scel ...`（失配）** | `38/1` vs `38/1` | 100% 符號集一致 |

- **為何 Stage-A 必須保持「FX3 原生宿主 `.ko` 棧 + P9 適配版 FX3 `upm.ko`」的定量證明**：
  1. **風險一（`p1` 跨版本 `vermagic` 硬阻斷）**：FX6 `p1` initrd 內全部 8 個對應 `.ko` 的 `vermagic` 均為 `4.9.186-scel SMP preempt mod_unload aarch64`，在 FX3 `4.9.337-scel+` 宿主內核上加載會立即因 `vermagic` 失配返回 `ENOEXEC`。
  2. **風險二（`p15` 同 `vermagic` 下的 `SHN_UNDEF` 跨內核符號漂移）**：儘管 FX6 `p15` `.ko` 同樣標註 `4.9.337-scel+`，若將 FX6 `upm.ko` 混載入 FX3 宿主內核與 FX3 `backup.ko` 環境，內核模組加載器將因找不到 `Backup_sync_subsystem_for_senser_local` 與 `pcie_link_width_check_dev_state_ch0` 直接返回 `ENOENT`（`Unknown symbol in module`）！因此保持 FX3 宿主原生 `.ko` 模組集並僅對 FX3 `upm.ko` 施加 4B `P9` 空指針防護，是唯一零符號失配且零 `ENOEXEC`/`ENOENT` 的正確工程方案。

---

## 11. 端到端候選包乾跑、12 道安全門聯調與驗收測試結果

| 聯調場景 | `verified_matrix_items` | `verified_gate_count` | 阻斷安全門 ID | `candidate_ready` | `persistent_write_release` |
| --- | --- | :---: | --- | :---: | :---: |
| **合法完整候選包乾跑（含五大功能路由 + `U4` 掛載容錯 + RAM-Shadow `BK4\0` + `U5` 引導選擇器 + `U3` Bank DDR + Phase 8 `cxd90057.dtb` / `.ko` 完整性 + Stage-A CPIO + 四場景回退演練）** | `P1..P9 + Fan`（10/10 全齊） | **12 / 12** | `()`（12 門全綠通過） | `True` | `False`（硬件持久寫入紅線鎖定） |
| 缺失任一 Tier-0 備份項（`p12_cert`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 系統調用軌跡注入源設備寫標誌（`O_RDWR`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 篡改 `init2_guard.sh` 四層防磚清除鎖（`/tmp/mod_arm_once`） | `P1..P9 + Fan` | 10 / 12 | `G11`, `G12` | `False` | `False` |
| 損壞 `opelog.vfat`、P5/P6 UIPC、P7 橋接、Stage-A CPIO、五大功能路由、`U4`/RAM-Shadow `BK4\0`、`U5`/`U3` 引導選擇器與 Bank DDR 或 **Phase 8 `cxd90057.dtb` / `.ko` 完整性契約（`BLOCKED_BY_KERNEL_OR_DTB_REDLINE`）** | 對應項阻斷 | 11 / 12 | `G12` | `False` | `False` |

### 驗收測試匯總

1. `PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v`：**40 / 40 OK**
2. `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v`：**13 / 13 OK**
3. CLI `verify-kernel-dtb`、`verify-boot-selector-banks`、`verify-backup-mount-contracts`、`verify-feature-routing`、`run-rollback-drill` 與 `dry-run-candidate`：返回碼 `0`，`kernel_dtb_ok = true`、`dtb_byte_identical = true`、`p9_ko_integrity_ok = true`、`boot_selector_and_banks_ok = true`、`u5_closed = true`、`u3_advanced = true`、`backup_mount_tolerance_ok = true`、`u4_closed = true`、`all_12_gates_verified = true`、`rollback_drill_emmc_writes = 0`。
4. 工作區二進制殘留核驗：零 `.so`、`.bin`、`.img`、`.vfat`、`.ko`、`.cpio`、`.pyc` 文件留存。
