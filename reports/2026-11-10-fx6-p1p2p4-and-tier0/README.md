# FX6-on-FX3 P1–P9（9/9）全矩陣兼容適配、Stage-A RAM-Overlay CPIO 封裝、四層防磚回退演練與 12 道安全門驗證報告（Phase 4）

- **日期**：2026-11-10
- **正式受控工程包路徑**：`outputs/fx6-on-fx3-closure/`（同步鏡像：`work/fx6-on-fx3-p1p2p4-closure-20261110/`）
- **對接安全評估套件**：`outputs/fx3-safety/`（`verify_failsafe_hook_script` 與 `evaluate_12_safety_gates`）
- **運行時與潔淨室約束**：全離線內存與 `tempfile.TemporaryDirectory()` 驗證；POSIX `/bin/sh` 演練全程以 `PREFIX` 隔離沙盒根目錄（絕不觸碰宿主機真實 `/dev` 或 `/tmp`）；零 QEMU 進程操作、零 USB/硬件交互、倉庫零 `.so` / `.bin` / `.img` / `.vfat` / `.ko` / `.cpio` 二進制產物留存；兼容 macOS 系統 `/usr/bin/python3`（Python 3.9.6）與 Unicorn AArch64 2.1.4。

---

## 1. 正式受控工程包結構與全矩陣覆蓋表

全部純源碼模組集中受控於 `outputs/fx6-on-fx3-closure/`，完整閉合 **P1 至 P9 全 9 項（9/9）+ Fan + Stage-A RAM-Overlay CPIO + 四層防磚回退演練 + Tier-0 + 12 道安全門**：

| 模組路徑 | 覆蓋項 | 職責說明 |
| --- | :---: | --- |
| `outputs/fx6-on-fx3-closure/fx6_closure/elf_verify.py` | 基礎設施 | ELF64 AArch64 `PT_LOAD`（`ET_DYN`/`ET_EXEC`）與 `ET_REL`（`.ko` 節表）文件偏移映射器，強制校驗權限與 `NOBITS` 邊界。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/patcher.py` | **P1, P3, P4, P8, P9, Fan** | 7 個目標二進制組件兼容適配規範、冪等啟動掛載片段生成器與 100% SHA-256 逆向回滾校驗器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/vfat_builder.py` | **P2** | `/etc/opelog` 純 Python 確定性 VFAT（FAT16 / FAT32）內存鏡像構建器與 BPB / 雙 FAT 表 / `/OPE/{00,01}` 目錄樹審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/nd_unicorn_verifier.py` | **P3, P4, P8, P9, Fan** | P3、P4（576 組參數笛卡爾掃描）、P8、P9（空指針回調防護）、Fan（溫控備份有效標誌）Unicorn AArch64 指令級驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/uipc_completion_verifier.py` | **P5, P6** | 隊列 `0x92840747` 上 `0x032d -> 0x132d`（P5）與 `0x0400/0x0402/0x0404/0x0152 -> 0x1400/0x1402/0x1404/0x1152`（P6）精確字節級 12B 完結回執合成器與 `send_and_wait_cmp_i` Unicorn 驗證器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/backup_bridge_verifier.py` | **P7** | 內核態 Backup Sync100 地址無關橋接核驗器：雙內核 `pcidma_transfer_async` 16B 序言、`api+0x160` / `api+0x10` Unicorn 跳板、`dst=0x903e0811`/`op=0x30` 40B 請求與同步 `backupfile_cb_getcp(0, NULL)` DMA 回調契約。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/ram_overlay_packager.py` | **Stage-A CPIO** | 純 Python SVR4 `cpio newc`（`070701` 魔數、4 字節對齊、`TRAILER!!!` 哨兵）確定性歸檔封裝器與解析審計器，組裝 `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}`。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/rollback_drill.py` | **四層防磚演練** | Stage-A 啟動守衛確定性狀態機與 `PREFIX` 隔離沙盒 POSIX `/bin/sh` 子進程實跑演練器（覆蓋無授權標記、單次啟動+重啟恢復、SHA-256 失配/缺失回退、超時/非零退出回退與 eMMC 零寫入核驗）。 |
| `outputs/fx6-on-fx3-closure/native/tier0_backup_worker.c` & `tier0_unicorn_verifier.py` | **Tier-0** | 零外部 `UND` 符號、零動態重定位 AArch64 Linux 雙遍只讀備份組件與 Unicorn 系統調用審計器。 |
| `outputs/fx6-on-fx3-closure/fx6_closure/candidate_builder.py` & `__main__.py` | **12-Gate 聯調** | `TemporaryDirectory` 端到端離線候選包乾跑組裝器與 `fx3-safety` 12 道安全門評估器 CLI（含 `run-rollback-drill` 子命令）。 |
| `outputs/fx6-on-fx3-closure/tests/test_closure.py` | 全矩陣單測 | 完整自動化單元測試套件（**24 項測試**）。 |

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

### 4.1 確定性 `cpio newc`（`070701`）封裝包審計結果

- **歸檔格式**：SVR4 `newc`（110 字節 ASCII 十六進制頭、魔數 `070701`、頭+路徑與數據段嚴格 4 字節零填充對齊、尾部 `TRAILER!!!` 哨兵、固定時間戳 `1700000000` 與確定性 inode `300000+`）。
- **確定性歸檔大小與 SHA-256**：`19,696 B`（`19696 % 4 == 0`），跨次構建 100% 重現 SHA-256：`1871c6a0832f2c750a2ad675dea65bad5cd8567f953875f7b565a47d326895f6`。
- **封裝條目清單**：
  1. `etc`（`040755`）
  2. `etc/fx6_overlay`（`040755`）
  3. `etc/fx6_overlay/setup_fx6_compat.sh`（`100755`，整合 P1 `/dev/nflasha20 -> p30` 符號鏈接與 P2 `/dev/loop7` `opelog.vfat` 掛載）
  4. `etc/fx6_overlay/init2_guard.sh`（`100755`，100% 通過 `fx3_safety.preflight.verify_failsafe_hook_script` 四項安全契約核驗）
  5. `etc/fx6_overlay/overlay_manifest.json`（`100644`，完整記錄 `P1..P9 + Fan` 全 10 項適配矩陣、7 項 ELF 組件原始/適配/回滾 SHA-256 及 10 項運行時啟動前 SHA-256 校驗清單）

### 4.2 四層防磚故障自動回退狀態機與 POSIX `/bin/sh` 沙盒實跑演練矩陣

演練全程在 `tempfile.TemporaryDirectory()` 沙盒內通過 `PREFIX` 環境變量運行真實 `/bin/sh`，並對模擬只讀 eMMC 分區（`sector0`、`p2`、`p6`、`p15`、`p18`）進行前後 SHA-256 + `mtime_ns` + 沙盒攔截日誌三重零寫入審計：

| 演練場景 ID | 注入條件 | 實際執行分支 `BOOT_BRANCH` | 診斷碼 `DIAG_CODE` | 令牌狀態（執行前即刪） | 殘留覆蓋掛載 / Loop 數 | eMMC 分區寫入次數 (`sector0/p2/p6/p15/p18`) | 狀態機一致性 |
| --- | --- | :---: | --- | :---: | :---: | :---: | :---: |
| **場景 1** (`S1_unarmed_stock_boot`) | 未放置 `/tmp/mod_arm_once` 授權標記 | `STOCK_FX3` | `STOCK_UNARMED` | 無標記 | `0` / `0` | **0** | PASS |
| **場景 2 — 首次啟動** (`S2_boot1_armed`) | 放置 `mod_arm_once` + 10 項 SHA-256 全匹配 | `ADAPTED_FX6_OVERLAY` | `OK_ADAPTED_SINGLE_BOOT` | **子進程啟動前已刪除** (`CHILD_OBSERVED_TOKEN_ABSENT=1`) | `3` / `1`（RAM 掛載生效） | **0** | PASS |
| **場景 2 — 斷電二次重啟** (`S2_boot2_reboot_revert`) | 模擬斷電重啟（不重新放置令牌） | `STOCK_FX3` | `STOCK_UNARMED` | 已無標記（杜絕死循環） | `0` / `0` | **0** | PASS |
| **場景 3a** (`S3a_sha256_mismatch`) | 篡改 `appFw.so` 1 字節導致 SHA-256 不匹配 | `STOCK_FX3_FALLBACK` | `ERR_MANIFEST_SHA256_MISMATCH:lib/appFw.so` | 已刪除 | `0` / `0`（臨時目錄已清理） | **0** | PASS |
| **場景 3b** (`S3b_component_missing`) | 移除 `libfan.so` 模擬組件缺失 | `STOCK_FX3_FALLBACK` | `ERR_MANIFEST_COMPONENT_MISSING:lib/libfan.so` | 已刪除 | `0` / `0`（臨時目錄已清理） | **0** | PASS |
| **場景 4a** (`S4a_child_nonzero_139`) | 適配子進程異常退出（`exit 139`） | `STOCK_FX3_FALLBACK` | `ERR_CHILD_NONZERO_FALLBACK:139` | 已刪除 | `0` / `0`（自動卸載清理） | **0** | PASS |
| **場景 4b** (`S4b_watchdog_timeout`) | 子進程卡死超時未寫入心跳（`1s` 看門狗觸發） | `STOCK_FX3_FALLBACK` | `ERR_WATCHDOG_TIMEOUT_FALLBACK` | 已刪除 | `0` / `0`（自動卸載清理） | **0** | PASS |

---

## 5. 端到端候選包乾跑與 12 道安全門聯調

| 聯調場景 | `verified_matrix_items` | `verified_gate_count` | 阻斷安全門 ID | `candidate_ready` | `persistent_write_release` |
| --- | --- | :---: | --- | :---: | :---: |
| **合法完整候選包乾跑（含 Stage-A CPIO + 四場景回退演練）** | `P1..P9 + Fan`（10/10 全齊） | **12 / 12** | `()`（12 門全綠通過） | `True` | `False`（硬件持久寫入紅線鎖定） |
| 缺失任一 Tier-0 備份項（`p12_cert`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 系統調用軌跡注入源設備寫標誌（`O_RDWR`） | `P1..P9 + Fan` | 9 / 12 | `G10`, `G11`, `G12` | `False` | `False` |
| 篡改 `init2_guard.sh` 四層防磚清除鎖（`/tmp/mod_arm_once`） | `P1..P9 + Fan` | 10 / 12 | `G11`, `G12` | `False` | `False` |
| 損壞 `opelog.vfat`、P5/P6 UIPC、P7 橋接或 Stage-A CPIO 魔數 | 對應項阻斷 | 11 / 12 | `G12` | `False` | `False` |

---

## 6. 驗收測試結果

1. `PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v`：**24 / 24 OK**
2. `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v`：**10 / 10 OK**
3. CLI `run-rollback-drill` 與 `dry-run-candidate`：返回碼 `0`，`all_12_gates_verified = true`，`rollback_drill_emmc_writes = 0`。
4. 工作區二進制殘留核驗：零 `.so`、`.bin`、`.img`、`.vfat`、`.ko`、`.cpio`、`.pyc` 文件留存。
