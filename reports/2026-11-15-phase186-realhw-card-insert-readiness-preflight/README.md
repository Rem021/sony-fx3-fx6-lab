# Phase 186 真实硬件插卡前最终预检器（`preflight-card-insert`）交付报告

- **任务编号**：Task H202 — Phase 186 (`realhw_card_insert_readiness_verifier.py` / CLI `preflight-card-insert`)
- **目标机型**：物理 Sony ILME-FX3（`Ver. 7.02`，`PRODUCT_MODEL = 0x91030080`）
- **安全处置基线**：默认严格阻断（`GO_NO_GO = "BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT"`），硬锁定 `card_insert_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 1. 交付文件清单（Strictly 6 Owned Files）

1. 核心校验器：[realhw_card_insert_readiness_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/realhw_card_insert_readiness_verifier.py)
2. 包导出更新：[__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
3. CLI 入口注册（`preflight-card-insert`）：[__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)
4. 模块文档更新：[README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/README.md)
5. 54 项双模式单元测试：[test_realhw_card_insert_readiness_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/tests/test_realhw_card_insert_readiness_verifier.py)
6. 本阶段报告：[README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/reports/2026-11-15-phase186-realhw-card-insert-readiness-preflight/README.md)

---

## 2. 核心架构与 4 项插卡前硬门控（`C1..C4`）

| 模块/门控 | 检验边界与实测机制 | 关键契约与阻断阈值 |
| --- | --- | --- |
| **有界只读 Donor 校验 & Clean-Room 回退** | [`inspect_card_insert_donors_bounded`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/realhw_card_insert_readiness_verifier.py) 严格以 `os.O_RDONLY \| O_NOFOLLOW` 检查 `im.elf`、`libJiritsu.so`、`appFw.so`、`libWlanResource.so`、`upm.ko`；支持 `--force-clean-room` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 离线综合回退。 | 实测耗时 `< 0.001s`（严格低于 `< 0.15s` 上限），`raw_firmware_bytes_leaked == 0`。 |
| **`C1_SLOT1_EXFAT_GEOMETRY_AND_HYGIENE`** | [`evaluate_c1_slot1_exfat_geometry_and_hygiene`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/realhw_card_insert_readiness_verifier.py) 校验证书扇区 `EXFAT   ` OEM ID、Cluster `>= 128 KiB`、12 扇区 `BootChecksum`、`VolumeDirty == 0`；拒绝 FAT32/NTFS/APFS/HFS+、`FX6_STAGEB/` 内 macOS `._*`/`.DS_Store`、Slot-1 共存 `BODYDATA.DAT`/`BODYDATA (1).DAT` 及软链接；验证 ARM64 ELF64（`EM_AARCH64 == 183`）头与 SHA-256。 | `libJit.so <= 65,536 B`（`64 KiB`）且 `PT_LOAD p_align == 0x10000`；禁止任何 OTA/重分区触发器（`edisx.elf`、`nor_loader_writer.sh` 等）。 |
| **`C2_PER_CAMERA_TIER0_DUAL_MEDIA_BINDING`** | [`evaluate_c2_tier0_dual_media_binding`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/realhw_card_insert_readiness_verifier.py) 校验证据双份 `528 B FX3RCPT1` 冷备份回执（`os.fstat` `st_dev_a != st_dev_b`）、CRC32/SHA-256 一致性、`model_id == 0x91030080`、`body_fw == "7.02"`（`>= 2.04` 下限）及 `H0` 关键面基准。 | 强制覆盖 8 项 `H0` 基准：`p1`、`p2:/setting/{psd.bin,defdet.bin,Backup.bin}`、`p5:/wbi`、`p12:/cert/RQ_LIC.DAT`、`p15:/usr`、`p18:/lens/LENSFILE.BIN`。 |
| **`C3_ELECTRICAL_CABLE_THERMAL_INTERLOCK`** | [`evaluate_c3_electrical_cable_thermal_interlock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/realhw_card_insert_readiness_verifier.py) 强约束供电、热起点与 Multi-USB 引脚互斥。 | `NP-FZ100 >= 80%`（`>= 7.6V` 且 `<= 8.5V`）、机身起点 `< 45.0°C`、若接入 `1.8V` UART RX 则 `VMC-BNCM1` LTC 必须断开（`Pin 8/9/10` 冲突锁）、HDMI Type-A/USB-PD 被动安全（`0` USB 发包）。 |
| **`C4_ESCAPE_HATCH_AND_CLEAN_UNINSTALL_DRYRUN`** | [`evaluate_c4_escape_hatch_and_uninstall_dryrun`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h202-phase186-closure-card-insert-readiness-preflight/outputs/fx6-on-fx3-closure/fx6_closure/realhw_card_insert_readiness_verifier.py) 在内存预演 `EH1`、`EH2`、`EH3` 与 `H0 -> H1 -> H2 -> H3` 16 面零漂移恢复。 | `EH1` 拔卡旁路 `< 50 us`（`47 us`）、`EH2` `DISP+MENU+SHUTTER` 冷启回退、`EH3` 1-byte `libJit.so` CRC32 篡改 `< 1 ms` 回退、`16/16` 存储面 `H0 == H3` 位级一致。 |

---

## 3. 事实与未执行物理动作严格区分

### 已验证事实（`O_RDONLY` 本地 Donor + Clean-Room 离线沙箱）
- **`preflight-card-insert --dry-run-simulated`（`LOCAL_DONOR_O_RDONLY`）**：`4/4` 门控通过，`go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`card_insert_auth=False`，`report_sha256=a36c58f447666951...`（JSON 与摘要一致性校验通过）。
- **`preflight-card-insert --force-clean-room --dry-run-simulated`（`CLEAN_ROOM_SYNTHETIC`）**：`4/4` 门控通过，`go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`card_insert_auth=False`，`report_sha256=e43bbb95c4c73b1b...`。
- **默认未提供物理 Tier-0 回执模式（`preflight-card-insert`）**：退出码 `1`，`go_no_go=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，`gates=2/4`，`card_insert_auth=False`。
- **54 项双模式单元测试**：本地模式 `Ran 54 tests in 0.109s (OK)`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 54 tests in 0.104s (OK)`，远低于 `6.0s` 时限。
- **向后兼容验证**：`verify-milestone-175 --clean-room`、`verify-milestone-147 --clean-room`、`preflight-realhw-bench --clean-room --simulate-ready-bench` 及 `scripts/run_all_lab_tests.py --clean-only` 全部通过，`git status` 无任何 `__pycache__` 或二进制残留。

### 尚未执行的物理实机台架动作（需人工上机与实物连接后执行）
- 真实物理 Sony ILME-FX3（`Ver. 7.02`）实机上电、USB/UART 物理接线与实卡插入 Slot 1 均**尚未执行**。
- 在获得实际分立设备（`st_dev_a != st_dev_b`）保存的双份真实 `528 B FX3RCPT1` Tier-0 冷备份回执、实测电池电量/温度及真卡 ExFAT VBR 目录输入之前，禁止解除 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` 阻断状态。
