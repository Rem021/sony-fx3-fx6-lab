# FX6-on-FX3 P1–P9（9/9）全矩陣兼容適配、Tier-0 雙遍只讀備份與 12 道安全門乾跑驗證報告（Phase 3 全閉環）

- **日期**：2026-11-10
- **正式受控工程包路徑**：`outputs/fx6-on-fx3-closure/`（同步鏡像：`work/fx6-on-fx3-p1p2p4-closure-20261110/`）
- **對接安全評估套件**：`outputs/fx3-safety/`
- **運行時與潔淨室約束**：全離線內存與 `tempfile.TemporaryDirectory()` 驗證；零 QEMU 進程操作、零 USB/硬件交互、倉庫零 `.so` / `.bin` / `.img` / `.vfat` / `.ko` 二進制產物留存；兼容 macOS 系統 `/usr/bin/python3`（Python 3.9.6）與 Unicorn AArch64 2.1.4。

---

## 1. 正式受控工程包結構與 P1–P9（9/9）全覆蓋矩陣

全部純源碼模組集中受控於 `outputs/fx6-on-fx3-closure/`，完整閉合 **P1 至 P9 全 9 項（9/9）+ Fan + Tier-0 + 12 道安全門**：

| 模組路徑 | 覆蓋項 | 職責說明 |
| --- | :---: | --- |
| `outputs/fx6-on-fx3-closure/fx6_closure/elf_verify.py` | 基礎設施 | ELF64 AArch64 `PT_LOAD`（`ET_DYN`/`ET_EXEC`）與 `ET_REL`（`.ko` 節表）文件偏移映射器，強制校驗權限與 `NOBITS` 邊界。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py` | **P1, P3, P4, P8, P9, Fan** | 7 個目標二進制組件兼容適配規範、冪等啟動掛載片段生成器與 100% SHA-256 逆向回滾校驗器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/vfat_builder.py` | **P2** | `/etc/opelog` 純 Python 確定性 VFAT（FAT16 / FAT32）內存鏡像構建器與 BPB / 雙 FAT 表 / `/OPE/{00,01}` 目錄樹審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/nd_unicorn_verifier.py` | **P3, P4, P8, P9, Fan** | P3、P4（576 組參數笛卡爾掃描）、P8、P9（空指針回調防護）、Fan（溫控備份有效標誌）Unicorn AArch64 指令級驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/uipc_completion_verifier.py` | **P5, P6** | 隊列 `0x92840747` 上 `0x032d -> 0x132d`（P5）與 `0x0400/0x0402/0x0404/0x0152 -> 0x1400/0x1402/0x1404/0x1152`（P6）精確字節級 12B 完結回執合成器，及 `appFw.so` `send_and_wait_cmp_i`（`0x20ef604`..`0x20ef7ec`）+ `0x20edd1c` 狀態映射器 Unicorn 驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/backup_bridge_verifier.py` | **P7** | 內核態 Backup Sync100 地址無關橋接核驗器：雙內核 `pcidma_transfer_async` 16B 序言（`b4000b00, a9bb7bfd, 910003fd, a90153f3`）、`api+0x160` / `api+0x10` Unicorn 跳板、`dst=0x903e0811`/`op=0x30` 40B 請求與同步 `backupfile_cb_getcp(0, NULL)` DMA 回調契約。 |
| `outputs/fx6-on-fx3-closure/native/tier0_backup_worker.c` & `tier0_unicorn_verifier.py` | **Tier-0** | 零外部 `UND` 符號、零動態重定位 AArch64 Linux 雙遍只讀備份組件與 Unicorn 系統調用審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py` & `__main__.py` | **12-Gate 聯調** | `TemporaryDirectory` 端到端離線候選包乾跑組裝器（覆蓋 `P1..P9 + Fan + Tier-0`）與 `fx3-safety` 12 道安全門評估器 CLI。 |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py` | 全矩陣單測 | 完整自動化單元測試套件（**21 項測試**）。 |

---

## 2. 二進制兼容適配矩陣（P1 / P3 / P4 / P8 / P9 / Fan）偏移與 SHA-256 回滾表

### 2.1 ELF64 段/節偏移與指令映射核驗表

| 適配組 | 目標組件（ELF 類型 / 大小） | 適配點 ID | 映射段/節（權限） | VMA / 節內偏移 | 文件偏移 | 原始字節 (hex) $\rightarrow$ 適配字節 (hex) | 工程語義 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **P1** | `libInfraSetupFile.so` (`ET_DYN`, `202,664 B`) | `P1_setupfile_nflasha20_to_30` | `PT_LOAD[0]` (`R-X`) | `0x25e9c` | `0x25e9c` | `32` $\rightarrow$ `33` | `"/dev/nflasha20"` $\rightarrow$ `"/dev/nflasha30"` |
| **P1** | `libInfraMediaCommon.so` (`ET_DYN`, `402,624 B`) | `P1_mediacommon_nflasha20_to_30` | `PT_LOAD[0]` (`R-X`) | `0x4dfcb` | `0x4dfcb` | `32` $\rightarrow$ `33` | `"/dev/nflasha20"` $\rightarrow$ `"/dev/nflasha30"` |
| **P1** | `libInfraMediaConfig.so` (`ET_DYN`, `52,312 B`) | `P1_mediaconfig_nflasha20_to_30` | `PT_LOAD[0]` (`R-X`) | `0x86fe` | `0x86fe` | `32` $\rightarrow$ `33` | `"/dev/nflasha20"` $\rightarrow$ `"/dev/nflasha30"` |
| **P1** | `appFw.so` (`ET_DYN`, `50,520,424 B`) | `P1_appfw_nflasha20_to_30` | `PT_LOAD[0]` (`R-X`) | `0x25896ce` | `0x25896ce` | `32` $\rightarrow$ `33` | `"/dev/nflasha20"` $\rightarrow$ `"/dev/nflasha30"` |
| **P3** | `libInfraAppRemoteBoard.so` (`ET_DYN`, `10,448 B`) | `P3_remoteboard_execRcvMsg` | `PT_LOAD[0]` (`R-X`) | `0x157c` | `0x157c` | `fd7bbea901008012` $\rightarrow$ `00008052c0035fd6` | `execRcvMsg` 收斂為 `mov w0, #0; ret` |
| **P3** | `libInfraAppRemoteBoard.so` (`ET_DYN`, `10,448 B`) | `P3_remoteboard_MainThread` | `PT_LOAD[0]` (`R-X`) | `0x1700` | `0x1700` | `fd7bbca960348052` $\rightarrow$ `00008052c0035fd6` | `MainThread` 收斂為 `mov w0, #0; ret` |
| **P4** | `appFw.so` (`ET_DYN`, `50,520,424 B`) | `P4_appfw_set_nd_filter_mode_clear` | `PT_LOAD[0]` (`R-X`) | `0x2111358` | `0x2111358` | `81000035` $\rightarrow$ `1f2003d5` | `cbnz w1, #0x2111368` $\rightarrow$ `nop`（固定 Clear `4`） |
| **P4** | `appFw.so` (`ET_DYN`, `50,520,424 B`) | `P4_appfw_set_nd_filter_value_clear` | `PT_LOAD[0]` (`R-X`) | `0x21113f0` | `0x21113f0` | `61030034` $\rightarrow$ `1b000014` | `cbz w1, #0x211145c` $\rightarrow$ `b #0x211145c`（固定 `(1, 1)`） |
| **P8** | `appFw.so` (`ET_DYN`, `50,520,424 B`) | `P8_appfw_async_log_wait_nonblocking` | `PT_LOAD[0]` (`R-X`) | `0x2159c50` | `0x2159c50` | `fd7bbaa9fd030091` $\rightarrow$ `00008052c0035fd6` | 異步日誌等待入口非阻塞返回 `mov w0, #0; ret` |
| **P9** | `upm.ko` (`ET_REL`, `453,896 B`) | `P9_upm_sensor_callback_null_guard` | `.text` `[2]` (`A-X`) | `.text+0x136b8` | `0x13720` | `40003fd6` $\rightarrow$ `00008052` | `blr x2` (`0xd63f0040`) $\rightarrow$ `mov w0, #0` (`0x52800000`) |
| **Fan** | `libfan.so` (`ET_DYN`, `31,176 B`) | `Fan_libfan_bkup_is_valid_true` | `PT_LOAD[0]` (`R-X`) | `0x1dec` | `0x1dec` | `fd7bbda920018052` $\rightarrow$ `20008052c0035fd6` | `_Z19fan_i_bkup_is_validv` 收斂為 `mov w0, #1; ret` |

### 2.2 原始基準、適配後與逆向回滾 SHA-256 100% 還原核驗表

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

## 3. P2 `/etc/opelog` VFAT 內存鏡像幾何與 BPB 校驗矩陣

| 預設模式 | 文件系統類型 | 總容量（字節 / 扇區） | `SecPerClus` | `RsvdSecCnt` | `FATSz`（扇區） | 數據簇數 `CountofClusters` | 確定性鏡像 SHA-256 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `8m_ram` | `FAT16` | `8,388,608 B` (`16,384`) | 1 | 4 | 64 | `16,220` (`4085..65524`) | `48c2123efbfb93da4b797190c2e223ac76dbe47a80c2f4efe7d7fc07127663e4` |
| `16m_log` | `FAT16` | `16,777,216 B` (`32,768`) | 1 | 4 | 127 | `32,478` (`4085..65524`) | `bd289a5718c64e952eb5a92b9aab25b111cbc9642fd2f57a38e6e845fc9bd396` |
| `44.5m_log` | `FAT16` | `46,661,632 B` (`91,136`) | 2 | 4 | 178 | `45,372` (`4085..65524`) | `16b5c91008a3e173f36cf012801214c5e0f10d8d5a4841f253f0877fd745dfbe` |
| `44.5m_fat32` | `FAT32` | `46,661,632 B` (`91,136`) | 1 | 32 | 701 | `89,702` ($\ge 65525$) | `582defdfe2ce1828a7c11776ce854f3cc204364587a1215ce7c618871f822475` |

---

## 4. P5 / P6 UIPC 完結回執合成與 `send_and_wait_cmp_i` Unicorn 驗證矩陣

在 Unicorn AArch64 中映射 `appFw.so` `send_and_wait_cmp_i`（`0x20ef604`..`0x20ef7ec`）、五組真實調用包裝函數及狀態映射器 `0x20edd1c`，攔截 PLT 上的 `osal_valloc_msg_wait`、`osal_set_msg_src`、`osal_snd_msg`、`osal_rcv_msg_tmo`、`osal_free_msg`、`osal_dynamic_id`：

| 適配項 | 目標隊列 | 請求命令 / 長度 | 典型請求字節 (hex) | 12B 完結回執 (hex) | `send_and_wait_cmp_i` 執行結果 | `0x20ef7b4` (行 1075) 命中 | AP 映射狀態 (`0x20edd1c`) |
| :---: | :---: | :---: | --- | --- | :---: | :---: | :---: |
| **P5** | `0x92840747` | `0x032d` (`10 B`) | `0d202d030a0001800000` | `0d202d130c00018000005800` | 正常返回、`SP` 保持、緩衝零洩漏 | **0 次** | `0` |
| **P6** | `0x92840747` | `0x0400` (`10 B`) | `0d2000040a0001800000` | `0d2000140c00018000000000` | 正常返回、`SP` 保持、緩衝零洩漏 | **0 次** | `0` |
| **P6** | `0x92840747` | `0x0402` (`10 B`) | `0d2002040a0001800000` | `0d2002140c00018000000000` | 正常返回、`SP` 保持、緩衝零洩漏 | **0 次** | `0` |
| **P6** | `0x92840747` | `0x0404` (`12 B`) | `0d2004040c00018000000000` | `0d2004140c00018000000000` | 正常返回、`SP` 保持、緩衝零洩漏 | **0 次** | `0` |
| **P6** | `0x92840747` | `0x0152` (`14 B`) | `0d2052010e000180030020000000` | `0d2052110c00018000000000` | 正常返回、`SP` 保持、緩衝零洩漏 | **0 次** | `0` |
| **負向 A** | `0x92840747` | `osal_snd_msg` 非零 (`-19`) | `0d202d030a0001800000` | —（未送達） | 精確捕獲跳轉至斷言 `0x2167784` | **命中（行號 `1075`）** | — |
| **負向 B** | `0x92840747` | 嚴格回執校驗阻斷 (`status=-1`) | `0d202d030a0001800000` | 阻斷提交 (`rc=-7`) | 精確捕獲跳轉至斷言 `0x2167784` | **命中（行號 `1075`）** | — |
| **負向 C** | `0x92840747` | 原始異常回執透傳 (`status=-1`) | `0d202d030a0001800000` | `0d202d130c000180ffffffff` | 精確命中錯誤分支 `0x20ede04` | 0 次 | `0x6f` (`111`) |

---

## 5. P7 內核態 Backup Sync100 地址無關橋接與雙內核簽名核驗

`backup_bridge_verifier.py` 對照 `fx6-cp-backup-sync100-agnostic.c`、`fx3-modules-vs-fx6-kernel.json` 與 `contract-evidence.json` 完成四維核驗：

1. **雙內核 `pcidma_transfer_async` 16B 序言與相對回退地址核驗**：
   - FX3 基址 `0xffffff80083220c8`（文件偏移 `0x2a20c8`）與 FX6 基址 `0xffffff8008322f70`（文件偏移 `0x2a2f70`）前 32 字節 SHA-256 完全一致（`65eb42727e89bfd745f3c40a2625bb10bd7ef8f01de5f5a881525976c4eb07f2`），入口 4 字節指令均為 `0xb4000b00, 0xa9bb7bfd, 0x910003fd, 0xa90153f3`（首條 `cbz x0, #0x160` 解碼偏移精確等於 `+0x160`）。
   - Unicorn 實跑 `sync100_native_fallback` 重定位跳板：在 FX3 與 FX6 雙基址下，`x0 == 0` 100% 跳轉至 `fallback_zero = api + 0x160`（`SP` 不變）；`x0 != 0` 分配 `0x50` 棧幀、保存 `x19/x20` 並跳轉至 `fallback_nonzero = api + 0x10`；16B 補丁與 `sync100_restore` 100% 逐字節還原。
2. **40B `op=0x30` 請求結構與同步 DMA 回調狀態機核驗**：
   - 嚴格校驗 `dst == 0x903e0811`、`op == 0x30`、動態隊列 `Q`（`0x803e0001..0x803e7fff`）、24B OSAL 前置頭與首尾金絲雀（`0x55555555` / `0x77777777`）。
   - 完整驗證 `mode=3`（加鎖快照，返回 4096B 且 `+32=1`）$\rightarrow$ 目標調用點 `backupfile_get_cp_data + 0x90` 之 40B DMA 描述符（`CP_BANK_BYTES = 1,369,580`、`0x404000000 -> 0x4040d2000`）拷貝並同步單次調用 `backupfile_cb_getcp(0, NULL)` $\rightarrow$ `mode=0`（解鎖返回 4096B 且 `+32=0`）；非目標調用者無損轉發原生 `fallback`，未完成 DMA 前解鎖立即阻斷（`-7`）。
3. **用戶態契約交叉校驗**：核驗 `libbackup.so` SHA-256（`e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f`）及 CHAPLIN 模板四組 ID（`0xfa0191`, `0xfa0192`, `0xfa01a3`, `0xfa01a4`）邊界與校驗和全部匹配。

---

## 6. P3 / P4 / P8 / P9 / Fan Unicorn 驗證、Tier-0 備份與 12 道安全門乾跑聯調

| 聯調場景 | `verified_matrix_items` | `verified_gate_count` | 阻斷安全門 ID | `candidate_ready` | `persistent_write_release` |
| --- | --- | :---: | --- | :---: | :---: |
| **合法完整候選包乾跑** | `P1..P9 + Fan`（10/10 全齊） | **12 / 12** | `()`（12 門全綠通過） | `True` | `False`（硬件持久寫入紅線鎖定） |
| 缺失任一 Tier-0 備份項（`p12_cert`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 系統調用軌跡注入源設備寫標誌（`O_RDWR`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 篡改 `init2` 四層防磚清除鎖（`/tmp/mod_arm_once`） | `P1..P9 + Fan` | 10 / 12 | `G11`, `G12` | `False` | `False` |
| 損壞 `opelog.vfat` BPB 或 P5/P6 UIPC 或 P7 橋接 | 對應項移除 | 11 / 12 | `G12` | `False` | `False` |

---

## 7. 驗收測試結果

1. `PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v`：**21 / 21 OK**
2. `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v`：**10 / 10 OK**
3. 工作區二進制殘留核驗：零 `.so`、`.bin`、`.img`、`.vfat`、`.ko`、`.pyc` 文件留存。
