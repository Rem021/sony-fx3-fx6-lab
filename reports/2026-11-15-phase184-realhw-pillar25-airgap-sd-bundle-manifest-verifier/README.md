# Phase 184（Pillar 25）— 真机气隙实验台 SD/CFexpress BYOF 清单验签、双介质 `FX3RCPT1` 交叉绑定与零联网暂存护栏报告

> **结论**：已按 [Task H201] 完成 Pillar 25 实现、CLI `verify-airgap-sd-bundle` 集成、50 项双模式单元测试及完整向后兼容验证；**严守离线安全红线，未执行任何真实相机插卡上电、USB 传输或持久分区写入动作**。

---

## 1. 交付文件（严格限定 6 项自有文件）

1. **[`realhw_airgap_sd_bundle_manifest_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_airgap_sd_bundle_manifest_verifier.py)**：Pillar 25 核心验签器（`O_RDONLY` 有界供体核验 + 净室回退、Pillar 25A `FX3BNDL1` 8 场景、Pillar 25B ExFAT/AppleDouble/`ELF64`/`BODYDATA.DAT` 8 场景、统一 `run_airgap_sd_bundle_manifest_suite`）。
2. **[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)**：导出 Phase 184 Pillar 25 全部常量、错误码、数据类与入口函数（零符号遮蔽）。
3. **[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)**：新增 `verify-airgap-sd-bundle`（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`），保持 `verify-22pillar-recovery` 与 `verify-24pillar-recovery` 100% 不变。
4. **[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/outputs/fx3-recovery-adapter/README.md)**：补充 Phase 184 Pillar 25 文档与 CLI 示例。
5. **[`test_realhw_airgap_sd_bundle_manifest_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/outputs/fx3-recovery-adapter/tests/test_realhw_airgap_sd_bundle_manifest_verifier.py)**：50 项双模式单元测试（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）。
6. **[本报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/reports/2026-11-15-phase184-realhw-pillar25-airgap-sd-bundle-manifest-verifier/README.md)**。

---

## 2. 实测事实（`O_RDONLY` 本地供体核验与净室模式）vs 未执行的物理台架动作

### 2.1 已实测验证的本地事实（`os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` + 净室回退）

- **本地供体有界只读审计（`inspect_phase184_donors_readonly`）**：实测耗时 `0.002339 s`（远低于 `0.15 s` 上限），`donor_files_inspected = 7`、`raw_firmware_bytes_leaked = 0`，`snapshot_sha256 = a6d59bc35231315c203bb170f93329eeaf58bba0e557e67549109706ab4e8624`：
  - `libgrm-fbinit9.so`：`7,664 B`（ELF64 LSB `ET_DYN` `EM_AARCH64=183`，SHA-256 `e273a4fe254bc212db2c1b0914bb5788da67262acd10104724f7e974bac78991`）
  - `libJit_test.so`：`8,345 B`（`<= 64 KiB` 上限，SHA-256 `05000a0ecceaa5004385b71fbeb2b15859bda7418e227a3d90238da31bc4cd7a`）
  - `libJiritsu.so`：`225,200 B`（SHA-256 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`）
  - `partinf.conf`：`3,999 B`（30 分区表含 FX3 `LensData @ 0x0031C000`，SHA-256 `3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189`）
  - `nflasha5.img`：`209,112,512 B`（有界 `4 KiB` 头 `WBI2\x00...`，4K 头 SHA-256 `e6e241c79507d275caaa79e673893ed690a7431edb4cae253920b9be43129f6a`）
  - `nflasha15.img`：`479,846,400 B`（有界 `4 KiB` 头 ext2 `0xEF53`，4K 头 SHA-256 `6d05ebbd28c554d1d9dcc54503face9af111170befaf2ca2a19c52d7bd8910d6`）
  - `fx3-7.02-BODYDATA.DAT`：`811,876,768 B`（有界 `4 KiB` 头 `\x89UFU\r\n\x1a\n`，4K 头 SHA-256 `fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404`）
- **支柱 25A — 每台机身绑定 `FX3RCPT1` 与 `FX3BNDL1`（8/8 场景实测通过）**：
  - 将 `FX3BNDL1`（IEEE CRC32 + HMAC-SHA256）绑定至 [`build_fx3rcpt1_receipt`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h201-phase184-pillar25-airgap-sd-bundle-manifest-verifier/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py) 生成的双份 `528 B` `FX3RCPT1` 回执（`serial_hash`、`model_id == 0x91030080`、`body_fw == "7.02"`、5 项 Tier-0 `H0` 摘要 `p2`/`p5`/`p12`/`p15`/`p18`、`st_dev_primary != st_dev_secondary`）；fail-closed 拦截跨机插卡（`CAMERA_SERIAL_RECEIPT_MISMATCH`）、FX30 `0x91030084` / FX6 `0x91020080`、`< 7.02` 固件、单介质冷备以及 CRC32/HMAC 篡改。
- **支柱 25B — ExFAT 卫生、AppleDouble（`._*`）清洗、`ELF64` Shim 与 `BODYDATA.DAT` 防火墙（8/8 场景实测通过）**：
  - 在隔离临时目录树上验证拒绝与清洗（`scrub_exfat_staging_tree_tempdir_dry_run`，禁止系统临时目录外调用）`.DS_Store`、`.Spotlight-V100`、`.fseventsd`、`.Trashes`、`.TemporaryItems` 与 `._*` AppleDouble；校验 `FX6_STAGEB/` 下 `fx6-stage-a-verify`、`libJit.so <= 64 KiB`、`libgrm-fbinit9.so` 的 ELF64 小端 `EM_AARCH64=183` 与精确 SHA-256；拦截卡根 `BODYDATA.DAT` / `BODYDATA (1).DAT` 共存，并通过 `socket.socket` 禁用断言证明 `airgap_sockets_opened == 0`。
- **硬锁定安全不变量**：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`、`airgap_sockets_opened = 0`。

### 2.2 尚未执行的物理相机台架动作（超出本离线验证范围）

- 尚未将任何 CFexpress Type A / SDXC V90 实卡插入真实物理 `Sony ILME-FX3`（`7.02`）机身的卡槽；
- 尚未在真实相机内核（`4.9.337-scel+`）上执行 `fx6-stage-a-verify`、`libJit.so` 或 `libgrm-fbinit9.so`；
- 尚未对真实物理相机执行任何 eMMC、SPI NOR、EL3 SRAM 或 USB 协议帧读写。

---

## 3. 全量实测命令与结果

| 验证项 | 命令 | 结果 |
| --- | --- | --- |
| Pillar 25 CLI | `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-airgap-sd-bundle --json` | `status=VERIFIED_PILLAR25_AIRGAP_SD_BUNDLE_MANIFEST`, `mode=LOCAL_DONOR_O_RDONLY`, `25A=8/8`, `25B=8/8`, `elapsed=0.0123s`, `suite_sha256=f9b2804172622cdaa72751129203e1e3d40800195e556eb35efd74156c7d3ba5` |
| Pillar 25 单测（默认模式） | `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest -v outputs/fx3-recovery-adapter/tests/test_realhw_airgap_sd_bundle_manifest_verifier.py` | **50/50 OK** (`5.371s` `< 6.0s`) |
| Pillar 25 单测（净室模式） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest -v outputs/fx3-recovery-adapter/tests/test_realhw_airgap_sd_bundle_manifest_verifier.py` | **50 tests, OK (skipped=1)** (`5.149s` `< 6.0s`) |
| 适配器全量单测（默认模式） | `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **1119 tests, OK (skipped=1)** (`147.541s`) |
| 适配器全量单测（净室模式） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **1061 tests, OK (skipped=12)** (`107.564s`) |
| 全仓净室合规审计 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN in 0.05s`（无 `.pyc` / 二进制污染） |
