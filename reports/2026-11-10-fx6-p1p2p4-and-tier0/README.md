# FX6-on-FX3 P1–P9（9/9）全矩陣兼容適配、五大核心功能路由 ELF 閉包核驗、Stage-A CPIO 封裝與 12 道安全門驗證報告（Phase 5）

- **日期**：2026-11-10
- **正式受控工程包路徑**：`outputs/fx6-on-fx3-closure/`（同步鏡像：`work/fx6-on-fx3-p1p2p4-closure-20261110/`）
- **對接安全評估套件**：`outputs/fx3-safety/`（`verify_failsafe_hook_script` 與 `evaluate_12_safety_gates`）
- **運行時與潔淨室約束**：全離線內存與 `tempfile.TemporaryDirectory()` 驗證；POSIX `/bin/sh` 演練全程以 `PREFIX` 隔離沙盒根目錄（絕不觸碰宿主機真實 `/dev` 或 `/tmp`）；零 QEMU 進程操作、零 USB/硬件交互、倉庫零 `.so` / `.bin` / `.img` / `.vfat` / `.ko` / `.cpio` 二進制產物留存；兼容 macOS 系統 `/usr/bin/python3`（Python 3.9.6）與 Unicorn AArch64 2.1.4。

---

## 1. 正式受控工程包結構與全矩陣覆蓋表

全部純源碼模組集中受控於 `outputs/fx6-on-fx3-closure/`，完整閉合 **P1 至 P9 全 9 項（9/9）+ Fan + 藍圖 §3 五大核心相機功能路由與 ELF 動態符號閉包核驗 + Stage-A RAM-Overlay CPIO + 四層防磚回退演練 + Tier-0 + 12 道安全門**：

| 模組路徑 | 覆蓋項 | 職責說明 |
| --- | :---: | --- |
| `outputs/fx6-on-fx3-closure/fx6_closure/elf_verify.py` | 基礎設施 | ELF64 AArch64 `PT_LOAD`（`ET_DYN`/`ET_EXEC`）與 `ET_REL`（`.ko` 節表）文件偏移映射器，強制校驗權限與 `NOBITS` 邊界。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py` | **P1, P3, P4, P8, P9, Fan** | 7 個目標二進制組件兼容適配規範、冪等啟動掛載片段生成器與 100% SHA-256 逆向回滾校驗器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/vfat_builder.py` | **P2** | `/etc/opelog` 純 Python 確定性 VFAT（FAT16 / FAT32）內存鏡像構建器與 BPB / 雙 FAT 表 / `/OPE/{00,01}` 目錄樹審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/nd_unicorn_verifier.py` | **P3, P4, P8, P9, Fan** | P3、P4（576 組參數笛卡爾掃描）、P8、P9（空指針回調防護）、Fan（溫控備份有效標誌）Unicorn AArch64 指令級驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/uipc_completion_verifier.py` | **P5, P6** | 隊列 `0x92840747` 上 `0x032d -> 0x132d`（P5）與 `0x0400/0x0402/0x0404/0x0152 -> 0x1400/0x1402/0x1404/0x1152`（P6）精確字節級 12B 完結回執合成器與 `send_and_wait_cmp_i` Unicorn 驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/backup_bridge_verifier.py` | **P7** | 內核態 Backup Sync100 地址無關橋接核驗器：雙內核 `pcidma_transfer_async` 16B 序言、`api+0x160` / `api+0x10` Unicorn 跳板、`dst=0x903e0811`/`op=0x30` 40B 請求與同步 `backupfile_cb_getcp(0, NULL)` DMA 回調契約。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/feature_routing_verifier.py` | **藍圖 §3 五大功能路由** | **維度 A**：10 核心庫 ELF64 `DT_NEEDED`（43 節點全傳遞閉包，0 缺失）與 `.dynsym` 導入/導出審計；**維度 B**：Sony `17^3`/`33^3` `.cube` 生成/校驗器、FX3 `p30`（`48 MiB`）16 組 LUT 簇容量預算證明與 `libInfraSetupFile.so` `RcvThread`（`0x196c8..0x196e0`）掛載鏈核驗；**維度 C**：Cine EI / E 卡口 AF 契約與 `set_eye_af_mode_i` + `libmpr.so` `libXavcMxfGetSlotTypeFromMediaId`（`+0x53c850`）Unicorn 實跑驗證。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/ram_overlay_packager.py` | **Stage-A CPIO** | 純 Python SVR4 `cpio newc`（`070701` 魔數、4 字節對齊、`TRAILER!!!` 哨兵）確定性歸檔封裝器與解析審計器，組裝 `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}`。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/rollback_drill.py` | **四層防磚演練** | Stage-A 啟動守衛確定性狀態機與 `PREFIX` 隔離沙盒 POSIX `/bin/sh` 子進程實跑演練器（覆蓋無授權標記、單次啟動+重啟恢復、SHA-256 失配/缺失回退、超時/非零退出回退與 eMMC 零寫入核驗）。 |
| `outputs/fx6-on-fx3-closure/native/tier0_backup_worker.c` & `tier0_unicorn_verifier.py` | **Tier-0** | 零外部 `UND` 符號、零動態重定位 AArch64 Linux 雙遍只讀備份組件與 Unicorn 系統調用審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py` & `__main__.py` | **12-Gate 聯調** | `TemporaryDirectory` 端到端離線候選包乾跑組裝器與 `fx3-safety` 12 道安全門評估器 CLI（含 `verify-feature-routing` 與 `run-rollback-drill` 子命令）。 |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py` | 全矩陣單測 | 完整自動化單元測試套件（**28 項測試**）。 |

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

## 6. 端到端候選包乾跑與 12 道安全門聯調

| 聯調場景 | `verified_matrix_items` | `verified_gate_count` | 阻斷安全門 ID | `candidate_ready` | `persistent_write_release` |
| --- | --- | :---: | --- | :---: | :---: |
| **合法完整候選包乾跑（含五大功能路由核驗 + Stage-A CPIO + 四場景回退演練）** | `P1..P9 + Fan`（10/10 全齊） | **12 / 12** | `()`（12 門全綠通過） | `True` | `False`（硬件持久寫入紅線鎖定） |
| 缺失任一 Tier-0 備份項（`p12_cert`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 系統調用軌跡注入源設備寫標誌（`O_RDWR`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 篡改 `init2_guard.sh` 四層防磚清除鎖（`/tmp/mod_arm_once`） | `P1..P9 + Fan` | 10 / 12 | `G11`, `G12` | `False` | `False` |
| 損壞 `opelog.vfat`、P5/P6 UIPC、P7 橋接、Stage-A CPIO 或 **五大核心功能路由閉包** | 對應項阻斷 | 11 / 12 | `G12` | `False` | `False` |

---

## 7. 驗收測試結果

1. `PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v`：**28 / 28 OK**
2. `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v`：**10 / 10 OK**
3. CLI `verify-feature-routing`、`run-rollback-drill` 與 `dry-run-candidate`：返回碼 `0`，`feature_routing_ok = true`，`all_12_gates_verified = true`，`rollback_drill_emmc_writes = 0`。
4. 工作區二進制殘留核驗：零 `.so`、`.bin`、`.img`、`.vfat`、`.ko`、`.cpio`、`.pyc` 文件留存。
