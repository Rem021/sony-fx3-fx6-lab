# FX6-on-FX3 全矩陣二進制兼容適配、Tier-0 雙遍只讀備份與 12 道安全門乾跑驗證報告（Phase 2 全閉環）

- **日期**：2026-11-10
- **正式受控工程包路徑**：`outputs/fx6-on-fx3-closure/`（同步鏡像：`work/fx6-on-fx3-p1p2p4-closure-20261110/`）
- **對接安全評估套件**：`outputs/fx3-safety/`
- **運行時與潔淨室約束**：全離線內存與 `tempfile.TemporaryDirectory()` 驗證；零 QEMU 進程操作、零 USB/硬件交互、倉庫零 `.so` / `.bin` / `.img` / `.vfat` / `.ko` 二進制產物留存；兼容 macOS 系統 `/usr/bin/python3`（Python 3.9.6）與 Unicorn AArch64 2.1.4。

---

## 1. 正式受控工程包結構與 CLI 入口

由於倉庫 `.git/info/exclude` 排除 `work/`，全部純源碼工程包已晉升至 Git 正式追蹤路徑 `outputs/fx6-on-fx3-closure/`：

| 模塊路徑 | 職責說明 |
| --- | --- |
| `outputs/fx6-on-fx3-closure/README.md` | 工程包架構、潔淨室邊界、CLI 子命令與測試運行指南。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/__main__.py` | `python3 -m fx6_closure` CLI 入口，提供 `verify-donors`、`run-unicorn-audit`、`dry-run-candidate` 三大子命令。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/elf_verify.py` | ELF64 AArch64 `PT_LOAD`（`ET_DYN`/`ET_EXEC`）與 `ET_REL` 可重定位內核模塊節表（`.text` 等）文件偏移映射器，強制校驗段/節權限與 `NOBITS` 邊界。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py` | 完整二進制兼容適配矩陣（P1、P3、P4、P8、P9 `upm.ko`、Fan `libfan.so`）、啟動掛載片段生成器與 100% SHA-256 逆向回滾校驗器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/vfat_builder.py` | P2 `/etc/opelog` 純 Python 確定性 VFAT（FAT16 / FAT32）內存鏡像構建器與 BPB / 雙 FAT 表 / `/OPE/{00,01}` 目錄樹審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/nd_unicorn_verifier.py` | P3、P4（576 組參數笛卡爾掃描）、P8、P9（空指針回調防護）、Fan（溫控備份有效標誌）Unicorn AArch64 指令級驗證器。 |
| `outputs/fx6-on-fx3-closure/native/tier0_backup_worker.c` | 零外部 `UND` 符號、零動態重定位 AArch64 Linux 雙遍只讀 Tier-0 校準與分區備份組件（內置純 C FIPS 180-4 SHA-256）。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/tier0_unicorn_verifier.py` | 臨時目錄調用 Zig `aarch64-linux-musl` 編譯 `tier0_backup_worker.c`、加載 ELF64 `PT_LOAD` 至 Unicorn AArch64 並執行正向與故障注入系統調用審計。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py` | 在 `tempfile.TemporaryDirectory()` 中串聯全量 7 個二進制目標適配與回滾、8 MiB `opelog.vfat` 生成、Unicorn 實跑 Tier-0 產出真實 11 項 `manifest.json` 並對接 `outputs/fx3-safety` 12 道刷前安全門評估器。 |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py` | 完整自動化單元測試套件（17 項測試）。 |

---

## 2. 完整二進制兼容適配矩陣（P1 / P3 / P4 / P8 / P9 / Fan）偏移與 SHA-256 回滾表

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
| `P1_appFw` | 1 B | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `20a749af317ae1479f2995b58d126a17dce6b68091d5852e4b50a0cab6a764e6` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | PASS |
| `P3_libInfraAppRemoteBoard` | 16 B | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | `2426911919397ab51ef35a914feb89674d35522cb928280bae510b4f06723572` | `c7d666093b42713eecf601ddacbfa879b255d0f953a9e77929eb12b916e6b0a6` | PASS |
| `P4_appFw` | 8 B | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `5cf36474efe19b2d94cd0257d4f1d0d3e7e042a3e0ecab256afc758b1e983113` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | PASS |
| `P8_appFw` | 8 B | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | PASS |
| `P1_P4_appFw_combined` | 9 B | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `5acaf711724aa54fdd1750353bb22a9e34b87ead3fd099205b6b30d3304f5520` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | PASS |
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

## 4. P3 / P4 / P8 / P9 / Fan Unicorn AArch64 指令級驗證矩陣

| 驗證項 | 執行入口與條件 | 實測結果 | 結論 |
| --- | --- | --- | :---: |
| **P3 `libInfraAppRemoteBoard.so`** | `execRcvMsg(0x0)` @ `0x157c` & `MainThread(0xdeadbeef)` @ `0x1700` | 各自 2 條指令返回 `w0 = 0`（合計 4 條指令，零空指針異常） | PASS |
| **P4 `set_nd_filter_mode_i`** | `0x2111358` 全笛卡爾 `576` 組參數掃描 | 未適配觸發 `300` 次斷言（行號 `9236, 9247`）；適配後 **`576 / 576`** 輸出 Clear `4`、**`0`** 斷言 | PASS |
| **P4 `set_nd_filter_value_i`** | `0x21113d8` 全笛卡爾 `576` 組參數掃描 | 未適配觸發 `312` 次斷言（行號 `9353, 9370, 9382`）；適配後 **`576 / 576`** 輸出 `(1, 1)`、**`0`** 斷言、`SP`/`X19` 保持 | PASS |
| **P8 `appFw.so` 異步日誌等待** | `0x2159c50` 非阻塞返回驗證 | 2 條指令返回 `w0 = 0`、`SP` 完全保持 | PASS |
| **P9 `upm.ko` 空回調防護** | `.text+0x136b4..0x136c0`（`[x2+0x10] = NULL`） | 未適配執行 `blr x2` 觸發 `UC_ERR_FETCH_UNMAPPED`；適配後 `mov w0, #0` 乾淨返回 `w0 = 0` | PASS |
| **Fan `libfan.so` 溫控備份校驗** | `_Z19fan_i_bkup_is_validv` @ `0x1dec` | 2 條指令返回 **`w0 = 1`**、`SP` 完全保持 | PASS |

---

## 5. Tier-0 只讀備份組件與端到端候選包 12 道安全門聯調（`candidate_builder.py`）

### 5.1 Tier-0 雙遍只讀備份 Unicorn 審計

- 臨時目錄編譯產物 `40,496 B`，`undefined_imports = ()`（零外部符號依賴），`relocations = ()`（零動態重定位）。
- 正向雙遍讀取 11 項 `TIER0_REQUIRED_BACKUPS`（合計 `145,648,640 B` SHA-256 計算）：返回 `WORKER_OK (0)`，重入二次調用返回 `ERR_REENTRANT_LOCK (10)`；`verify_tier0_backup_manifest` `valid == True`（11/11 全綠）；`audit_tier0_worker_syscalls` `valid == True`（`3,451` 次系統調用，`first_path_op_unlink_libjit == True`，`dev_write_open_count == 0`，`source_fd_write_count == 0`）。
- 故障注入阻斷：Pass-2 單比特翻轉返回 `25`、`sector0` 頭部損壞返回 `18`（0 輸出文件）、`BK4\0` 頭部損壞返回 `19`、`boot0 != boot1` 返回 `16`、`O_EXCL` 衝突返回 `20`，均拒絕生成 `manifest.json`。

### 5.2 端到端離線候選包乾跑與 12 道安全門聯調矩陣

`run_offline_candidate_dry_run()` 在 `tempfile.TemporaryDirectory()` 中完成全量 7 個二進制適配與回滾、8 MiB `opelog.vfat` 構建、Unicorn 實跑 Tier-0 清單生成及 `evaluate_12_safety_gates` 聯調，退出時自動銷毀全部臨時二進制（`temp_dir_cleaned == True`）：

| 聯調場景 | `verified_gate_count` | 阻斷安全門 ID | `candidate_ready` | `persistent_write_release` |
| --- | :---: | --- | :---: | :---: |
| **合法完整候選包乾跑** | **12 / 12** | `()`（12 門全綠通過） | `True` | `False`（硬件持久寫入紅線保持鎖定） |
| 缺失任一 Tier-0 備份項（如 `p12_cert`） | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 系統調用軌跡注入源設備寫標誌（`O_RDWR`） | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 篡改 `init2` 四層防磚清除鎖（`/tmp/mod_arm_once`） | 10 / 12 | `G11`, `G12` | `False` | `False` |
| 損壞 `opelog.vfat` BPB 簽名 | 11 / 12 | `G12` | `False` | `False` |

---

## 6. 驗收測試結果

1. `PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v`：**17 / 17 OK**
2. `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v`：**10 / 10 OK**
3. 工作區二進制殘留核驗：零 `.so`、`.bin`、`.img`、`.vfat`、`.ko` 文件留存。
