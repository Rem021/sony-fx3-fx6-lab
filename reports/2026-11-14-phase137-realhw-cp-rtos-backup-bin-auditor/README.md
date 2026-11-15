# Phase 137 — 27th Unified `fx3-firmware-lab` Auditor: Real-Hardware Unknowns `U2` (`cpapp-b.bin` CP RTOS & Route-1 vs Route-2) & `U3` (`Backup.bin` `819->840`, `0x00fa0080` Bank 0/1 Boot Descriptors & Per-Body Calibration)
# 第 137 阶段 — 第 27 个统一 `fx3-firmware-lab` 审计器：真机未知项 `U2`（`cpapp-b.bin` CP RTOS 与路线一/二架构证明）及 `U3`（`Backup.bin` `819->840`、`0x00fa0080` Bank 0/1 启动描述符与单机校准防护）

- **Date / 日期**: 2026-11-14
- **Module / 模块**: [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cp_rtos_and_backup_bin_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cp_rtos_and_backup_bin_auditor.py)
- **CLI Subcommand / CLI 子命令**: `audit-realhw-cp-backup` (integrated as #27 in `audit-all`)
- **Tests / 单元测试**: [`outputs/fx3-firmware-lab/tests/test_realhw_cp_rtos_and_backup_bin.py`](../../outputs/fx3-firmware-lab/tests/test_realhw_cp_rtos_and_backup_bin.py) (**42/42** passing in both modes; full suite **835/835** passing in both modes)
- **Wave-17 Web Intelligence Sync / 情报同步**: [`reports/2026-11-14-global-sony-wave17-realhw-installer-jiritsu-intel/README.md`](../2026-11-14-global-sony-wave17-realhw-installer-jiritsu-intel/README.md)

---

## English Technical Summary

### 1. Verification Results & Deterministic Digests

| Verification Gate | Mode / Scope | Result | Runtime | Digest / Count |
| :--- | :--- | :--- | :--- | :--- |
| `analyze_realhw_cp_rtos_and_backup_bin(clean_room=False)` | `LOCAL_DONOR_VERIFIED` (18 donor files `os.O_RDONLY`) | `all_checks_passed = True` | `0.2084 s` (`< 0.25 s`) | `report_sha256 = 8fb5fc388a2ad399851ec0d7fa27d989ab31623f24ce52a8175581ea5020c5c8` |
| `analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)` | `CLEAN_ROOM_SYNTHETIC` | `all_checks_passed = True` | `0.0020 s` (`< 0.02 s`) | `report_sha256 = f168e74ba463832baa1e100d15ab13be485b8e244ef81f9478b757f0894e540f` |
| `audit-all --json` (Local Donor) | All 27 auditors | `all_checks_passed = True` (`27/27`) | `9.735 s` | `27/27` green (`675,526 B`) |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... audit-all --json` | All 27 auditors (Clean-Room) | `all_checks_passed = True` (`27/27`) | `0.574 s` | `27/27` green (`619,222 B`) |
| `unittest` Phase 137 suite | Local Donor / Forced Clean-Room | `OK` (`42/42` each) | `0.792 s` / `0.412 s` | `42` tests |
| `unittest discover` (full suite) | Local Donor / Forced Clean-Room | `OK` (`835/835` each) | `26.425 s` / `14.399 s` | `835` tests |
| `scripts/run_all_lab_tests.py --clean-only` | Binary / `.pyc` / `git status` hygiene | `CLEAN` | `0.04 s` | `0` forbidden artifacts |

### 2. Verified Local Donor Artifacts (`os.O_RDONLY` + `mmap.ACCESS_READ`, Zero Mutations)

1. **FX3 `v7.02` (`PRODUCT_MODEL_ALCIN_UUD`)**:
   - `cpapp-b.bin`: `15,980,568 B` (`sha256[:16] = c90d00d807874a53`)
   - `tomco.txt`: `710 B` (`42f1785422bce152`) · `kemco.txt`: `1,736 B` (`555454e8b7db1461`)
   - `FX3-CX95900_ALLLANG-Backup.bin`: `2,229,740 B` (`bf3a9d851f9853fd`)
   - `LdrBkupList.txt`: `650 B` (`ae537183ecce42fb`) · `pformat_config.txt`: `1,274 B` (`21cd5b29dd165c32`) · `loader_nor.bin`: `101,888 B` (`4358c839cfb1f22d`)
2. **FX6 `v6.01` (`PRODUCT_MODEL_CHAPLIN`)**:
   - `cpapp-b.bin`: `17,952,816 B` (`sha256[:16] = 60de0ab5544749dd`)
   - `tomco.txt`: `810 B` (`36566d47fe61e956`) · `kemco.txt`: `1,788 B` (`6a609ee6b96c2ed0`)
   - `CX95898_UC.bin`: `2,253,333 B` (`ec67687d1e2dc397`)
   - `nor_loader_writer.sh`: `9,106 B` · `us_spi_firmup.sh`: `1,180 B` · `us_darwin_firm.sh`: `478 B`
   - `big_backup.conf`: `37 B` · `ud_keep_backup.elf`: `10,224 B` · `mew.bin`: `6,692,572 B` · `darwin_core.bin`: `126,956 B`

### 3. Resolution of Unknowns `U2` & `U3` Across Four Audited Pillars

1. **Pillar 1 — Unknown `U2` (`cpapp-b.bin` TOPPERS RTOS & `tomco.txt`/`kemco.txt` Divergence)**:
   - Both FX3 and FX6 `cpapp-b.bin` load at `0x00108000` with identical ARM32 startup words `[0xe59f1004, 0xe2811004, 0xe1a0f001, 0x0010800c, 0xe3a000d3, 0xe12ff000]` and an **exact byte-identical `131,072 B` (`0x20000`) boot stub**, sharing `TOPPERS` (`16`), `FMP` (`14`), `C_ImagerCtrl_IMX510` (`1`), `osal_uipc` (`2`), `SET_CA_TALLY` (`1`), `SET_FAN_EQ_ID` (`2`), `FAN_R` (`1`), `PANELEVF` (`52`), and `kbd: select vgrip` (`1`).
   - Binary divergence begins cleanly at `0x20000`: FX6 embeds `Darwin` (`1` vs `0` in FX3), `VariableNd` (`6` vs `0`), `Mew` (`4` vs `0`), and `MoniFpga` (`48` vs `0`).
   - `tomco.txt` shares identical uncached CP DDR pools (`1,724.00 MiB` across `0x400000@0x04C00000:uc`, `0x7000000@0x09000000:uc`, `0x24800000@0x1B800000:uc`, `0x40000000@0x80000000:uc`), IPC interrupts (`296`, `307`), and `460800` UART baud, while FX6 sets `wdt_on=0`, `exception_reboot=Y`, `xreset_req_port=0:22`. `kemco.txt` diverges on `cfg.uart=1` (FX3) vs `cfg.uart=9` (FX6), `error.led=18,0` vs `13,3`, `gpio.port=0x5 gpio.bitmask=0x10`, and `wbimem` pool (`0x00BA0000` vs `0x01919000`).
2. **Pillar 2 — Route-1 vs Route-2 Architecture & Brick-Hazard Proof**:
   - Audits `nor_loader_writer.sh` (`bksb.elf`, `ud_nor_pformat.elf`, `ud_cp_firmup.elf`, LEDs `0x51/0x52/0x53/0x92`), `us_spi_firmup.sh` (`ud_spirom_firmup.elf`, `mew.bin`, LED `0x68`), `us_darwin_firm.sh` (`ud_darwin_firmup.elf`, `darwin_core.bin`, LED `0x63`), and `pformat_config.txt` (`loader_nor.bin`, `LdrBkup.bin`, `DGU.bin`, `MIS.bin`, `cpapp-b.bin`, `pcie_phy_fw.bin`).
   - Proves **Route-1 (`Stock FX3 loader_nor.bin` + `Stock FX3 p3 Kernel` + `Stock FX3 p8/cpapp-b.bin` + `Stock FX3 p2:/Backup.bin` + `Reversible /usr Stage-B Overlay`)** preserves 100% native FX3 `IMX510` CMOS/ISP/IBIS/AF/XAVC while eliminating all Route-2 SPI NOR / `mew.bin` FPGA / `darwin` ND brick hazards (`BLOCKED_ROUTE2_SPI_NOR_AND_FPGA_BRICK_HAZARD`).
3. **Pillar 3 — Unknown `U3` (`Backup.bin` `819 -> 840`, `0x00fa0080` Bank 0/1 & Per-Body Calibration)**:
   - Verifies both `BK4\x00` dual records with valid 32-bit byte-sum checksums: FX3 (`819` subsystems, `2,229,740 B`, Rec 0 `0x018adbdb`, Rec 1 `0x09443bb1`) vs FX6 (`840` subsystems, `2,253,333 B`, Rec 0 `0x01a7b01c`, Rec 1 `0x09638f0e`).
   - Decodes `0x00fa0080` (`64 x 144 B = 9,216 B`):
     - **Bank 0 (AP)**: Slots `0..4` (`\av-cam.bin`, `\kemco.txt`, `\initrd.img`, `\vmlinux.bin`, `\cxd90057.dtb`, `0x400001000..0x408ffffff`) are **100% identical**; FX3 adds slots `5..8` (`\bt_conf.cnf`..`\wole_app.bin` `@ 0xfe300000..0xfe3bffff`).
     - **Bank 1 (CP)**: Core entries (`\sabin\idt_cam.bin`, `\bonobo.bin`, `\tomco.txt`, `\cpapp-b.bin`) match identically; `\DmmCfg.bin` and `\defdet.bin` shift `+0x14000` (tracking `p8:\cpImg.dat` `0x809179000..0x809478fff` vs FX6 `p3:\cmrbnb.bin` `0x809179000..0x80918cfff`); `\OldAmtCL.bin`, `\psd.bin`, `\lensfile.bin` shift `+0xe0000`; all active DDR windows are strictly non-overlapping.
   - Enforces `LdrBkupList.txt` (`65` loader keys across `0x51, 0x5d, 0x92, 0xf9, 0xfa`), `big_backup.conf` (`/setting/psd.bin`, `/setting/defdet.bin`), `ud_keep_backup.elf -r` (`BK_PROTECT_ADJ_RST_USER_FIRMUP`), and hard-blocks cross-camera `Backup.bin`/`psd.bin`/`defdet.bin` overwriting.
4. **Pillar 4 — Volatile RAM Staging & Zero `eMMC` / `SPI NOR` Write Authorization**:
   - Allows only volatile `/tmp/`, `ram://`, `/ramdsk/` staging, blocks `/dev/nflasha*`, `/dev/cnflasha*`, `/dev/mmcblk0*`, `/dev/mtd*`, `spi_nor://`, `p2:/Backup.bin`, `psd.bin`, `defdet.bin`, `mew.bin`, and `darwin_core.bin`, and keeps `persistent_emmc_writes_authorized = False`, `spi_nor_write_authorized = False`, `emmc_mutation_bytes = 0`, `spi_nor_mutation_bytes = 0`, `calibration_mutation_bytes = 0`, and `0` raw proprietary byte slices in JSON.

### 4. Owned Files (Strict 7-File Scope)

1. [`reports/2026-11-14-global-sony-wave17-realhw-installer-jiritsu-intel/README.md`](../2026-11-14-global-sony-wave17-realhw-installer-jiritsu-intel/README.md)
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cp_rtos_and_backup_bin_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cp_rtos_and_backup_bin_auditor.py)
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)
4. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)
5. [`outputs/fx3-firmware-lab/README.md`](../../outputs/fx3-firmware-lab/README.md)
6. [`outputs/fx3-firmware-lab/tests/test_realhw_cp_rtos_and_backup_bin.py`](../../outputs/fx3-firmware-lab/tests/test_realhw_cp_rtos_and_backup_bin.py)
7. [`reports/2026-11-14-phase137-realhw-cp-rtos-backup-bin-auditor/README.md`](./README.md)

---

## 简体中文技术报告

### 一、 双模式实测验证结果

- **本地 Donor 模式**（`os.O_RDONLY` + `mmap.ACCESS_READ`，只读扫描 18 份 FX3 `v7.02` 与 FX6 `v6.01` 二进制/脚本资产）：单项审计耗时 **`0.2084 s`**（低于 `0.25 s` 上限），`all_checks_passed = True`，`report_sha256 = 8fb5fc388a2ad399851ec0d7fa27d989ab31623f24ce52a8175581ea5020c5c8`。
- **Clean-Room 合成模式**（`FX3_FX6_FORCE_CLEAN_ROOM=1`）：耗时 **`0.0020 s`**，`all_checks_passed = True`，`report_sha256 = f168e74ba463832baa1e100d15ab13be485b8e244ef81f9478b757f0894e540f`。
- **`audit-all --json` 全量集成（27/27 全绿）**：本地 Donor 模式 **`9.735 s`**（`675,526 B`）；Clean-Room 模式 **`0.574 s`**（`619,222 B`）。
- **单元测试**：Phase 137 专项 **`42/42`** 双模式全过（Donor `0.792 s` / Clean-Room `0.412 s`）；`outputs/fx3-firmware-lab` 全套 **`835/835`** 双模式全过（Donor `26.425 s` / Clean-Room `14.399 s`）；`scripts/run_all_lab_tests.py --clean-only` 返回 **`ALL GREEN in 0.04s`**。

### 二、 未知项 `U2` 与 `U3` 核心二进制实证结论

1. **支柱一 — 未知项 `U2`（`cpapp-b.bin` TOPPERS RTOS 与 `tomco.txt`/`kemco.txt` 差异定位）**：
   - FX3（`15,980,568 B`）与 FX6（`17,952,816 B`）`cpapp-b.bin` 均以 `0x00108000` 为装载基址，共享完全相同的 ARM32 启动向量及 **`131,072 B`（`0x20000`）前缀**，共用 `TOPPERS`/`FMP`/`C_ImagerCtrl_IMX510`/`osal_uipc`/`SET_CA_TALLY`/`SET_FAN_EQ_ID`/`PANELEVF`；差异严格从 `0x20000` 开始，FX6 独有 `Darwin`（`1` vs `0`）、`VariableNd`（`6` vs `0`）、`Mew`（`4` vs `0`）、`MoniFpga`（`48` vs `0`）。
   - `tomco.txt` 共享 4 段 `1,724.00 MiB` uncached 内存池及 `296`/`307` 中断号、`460800` 波特率，仅看门狗/异常重启不同；`kemco.txt` 在串口通道（`cfg.uart=1` vs `cfg.uart=9`）、故障灯 GPIO（`18,0` vs `13,3`）与 `wbimem`（`0x00BA0000` vs `0x01919000`）严格分叉。
2. **支柱二 — 路线一 vs 路线二架构与变砖风险证明**：
   - 提取并验证 `nor_loader_writer.sh`（`bksb.elf`/`ud_nor_pformat.elf`/`ud_cp_firmup.elf`，错误码 `0x51/0x52/0x53/0x92`）、`us_spi_firmup.sh`（`mew.bin` `0x68`）、`us_darwin_firm.sh`（`darwin_core.bin` `0x63`）与 `pformat_config.txt` 6 项镜像契约，定量证明**路线一（原厂 FX3 `loader_nor.bin` + 原厂 `p3` 内核 + 原厂 `p8/cpapp-b.bin` + 原厂 `p2:/Backup.bin` + 可逆 `/usr` Stage-B 叠加）**在 100% 保留 FX3 `IMX510` 成像/防抖/对焦/XAVC 硬件链路的同时彻底规避 SPI NOR、FPGA 与电子 ND 变砖风险。
3. **支柱三 — 未知项 `U3`（`Backup.bin` `819->840`、`0x00fa0080` Bank 0/1 与单机校准保护）**：
   - 双记录 `BK4\x00` 校验和全通过：FX3 `819` 子系统（Rec 0 `0x018adbdb` / Rec 1 `0x09443bb1`）vs FX6 `840` 子系统（Rec 0 `0x01a7b01c` / Rec 1 `0x09638f0e`）。
   - 解析 `0x00fa0080`（`64 × 144 B`）：Bank 0（AP）前 5 槽位地址跨机型完全一致，FX3 另含蓝牙/WOLE 槽位 `5..8`；Bank 1（CP）中 `\DmmCfg.bin`/`\defdet.bin` 精确偏移 `+0x14000`（源于 `p8:\cpImg.dat` vs FX6 `p3:\cmrbnb.bin`），`\OldAmtCL.bin`/`\psd.bin`/`\lensfile.bin` 精确偏移 `+0xe0000`，且 DDR 区间全部互不重叠。强制 `LdrBkupList.txt`（65 键）、`big_backup.conf` 与 `ud_keep_backup.elf -r`（`BK_PROTECT_ADJ_RST_USER_FIRMUP`）单机校准保留，严禁跨机覆写 `Backup.bin`/`psd.bin`/`defdet.bin`。
4. **支柱四 — 易失 RAM 暂存与零 `eMMC` / `SPI NOR` 写授权**：
   - `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`，实测 `emmc_mutation_bytes = 0`、`spi_nor_mutation_bytes = 0`、`calibration_mutation_bytes = 0`，JSON 输出零原始专有字节切片。
