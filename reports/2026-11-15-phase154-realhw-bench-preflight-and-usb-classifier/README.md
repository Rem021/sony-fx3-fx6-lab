# Phase 154 报告：主机侧只读物理实验台预检 CLI、被动 USB 模式分类器（`0DA1 / 0336 / MTP / UVC`）、SD 暂存防火墙与双副本 `FX3RCPT1` Go/No-Go 回执生成器（`preflight-realhw-bench`）

## 1. 结论先行
- **交付状态**：已在 `outputs/fx6-on-fx3-closure/` 完成 **Phase 154 (`preflight-realhw-bench`)**，提供 **100% 被动、零 USB 发包（`usb_packets_emitted == 0`）、零 IOKit 句柄打开（`iokit_handles_opened == 0`）、零物理设备写入（`persistent_emmc_writes_authorized == False`）** 的主机预检工具链。
- **双模式验证通过**：本地 BYOF Donor (`LOCAL_DONOR_O_RDONLY`) 与无 Donor 洁净室 (`CLEAN_ROOM_SYNTHETIC` / `FX3_FX6_FORCE_CLEAN_ROOM=1`) 均已实测通过；Phase 154 新增 `46` 项单元测试、Phase 147 主控门 `46` 项单元测试（合计 `92` 项 `OK`）以及 `scripts/run_all_lab_tests.py --clean-only` 洁净室卫生审计全绿。
- **物理相机边界声明**：本报告严格区分**已实测的离线/被动主机主机验证事实**与**尚未执行的真实物理 ILME-FX3 (`7.02`) 相机联机操作**；当前工作站实机被动 `ioreg` 探测返回 `NO_SONY_CAMERA_ATTACHED` (`NO_GO_BENCH_BLOCKED`)，尚未接入真实相机或执行物理 Tier-0 冷备份与 Stage-B 实验。

---

## 2. 四大核心支柱实现与文件清单

| # | 文件路径（可点击链接） | 作用说明 |
|---:|---|---|
| 1 | [realhw_bench_preflight_and_usb_classifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py) | Phase 154 核心模块：BYOF 只读就绪检查、被动 USB 状态机、SD 暂存/禁区防火墙、双副本 `528 B FX3RCPT1` 校验与 Go/No-Go 回执引擎 |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) | 导出 Phase 154 全部公开常量、数据类、审计函数与回执校验器 |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) | 新增 CLI 子命令 `preflight-realhw-bench`（支持 `--probe-host-usb`、`--usb-snapshot`、`--sd-dir`、`--sd-receipt`、`--vault-receipt`、`--simulate-ready-bench`、`--clean-room`、`--json`、`--markdown-out`、`--output`） |
| 4 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/README.md) | 更新 Phase 154 模块架构说明与 CLI 用法 |
| 5 | [test_phase154_realhw_bench_preflight_cli.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/tests/test_phase154_realhw_bench_preflight_cli.py) | `46` 项双模式单元测试（覆盖 6 类 USB 状态、`O_RDONLY` SD 防火墙、双副本 `FX3RCPT1`、防篡改校验与 CLI 端到端测试） |
| 6 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/reports/2026-11-15-phase154-realhw-bench-preflight-and-usb-classifier/README.md) | 本 Phase 154 交付报告 |

### 关键符号与安全硬锁
- **安全硬锁（代码内不可变常量）**：`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`SD_PHYSICAL_MEDIA_WRITTEN = False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED = False`、`USB_PACKETS_EMITTED = 0`、`IOKIT_HANDLES_OPENED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`RAW_FIRMWARE_SLICES_EMITTED = 0`。
- **支柱 1 [`inspect_bench_donor_readiness`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L491-L600)**：通过 `os.O_RDONLY | O_NOFOLLOW` 校验 FX3 `im.elf`、`libJiritsu.so`、FX6 `appFw.so`、`libWlanResource.so`、`62` 个 `.uxc` 资产与 `13/13` Stage-B 锁定表；显式 `synthetic_clean_room=False` 且缺失 Donor 时 Fail-Closed 拦截；JSON 零原始固件字节输出。
- **支柱 2 [`classify_passive_usb_snapshot`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L761-L917) / [`parse_ioreg_usb_snapshot`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L714-L737)**：同时兼容 macOS `ioreg -p IOUSB -l -w 0` 文本树（含 `|` 树形管道与十进制 VID/PID）与 XML Plist（`ioreg -a -p IOUSB -l -w 0`），零发包精准分类全部 6 种物理状态：
  1. `NO_SONY_CAMERA_ATTACHED`：输出 `NP-FZ100 >= 80%`、移除 `VMC-BNCM1`、设置 `Setup -> USB -> USB Connection Mode -> Mass Storage` 及直连 USB-C 数据线检查表；
  2. `READY_MSC_054C_0DA1`：确认有效 FX3 Mass Storage (`054C:0DA1`) 挂载；
  3. `STRANDED_SERVICE_054C_0336`：立即触发 `ALERT_SERVICE_MODE_STRANDED` (`hard_abort=True`) 并给出 `STOP (0336:7) -> release (0336:8) -> 0da1:9` / 安全断电恢复手册；
  4. `WRONG_USB_MODE_MTP_REMOTE_OR_UVC`（`054C:0DA2`/`0DA3`/`0DA4`、MTP/PTP/RNDIS/UVC 接口类）：提示切换相机菜单至 `Mass Storage`；
  5. `MULTIPLE_SONY_DEVICES_AMBIGUOUS`：硬件硬中止（`hard_abort=True`），防止误操作多台 Sony 设备；
  6. `UNSUPPORTED_MODEL_PID`：硬件硬中止（`hard_abort=True`），阻止对 `FX30`/`FX6`/`ILCE-*` 等非 FX3 机身触发后续动作。
- **支柱 3 [`audit_sd_staging_directory`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L1217-L1487)**：严格 `O_RDONLY | O_NOFOLLOW` 遍历（拒绝符号链接），硬拦截 `BODYDATA.DAT`、`edisx.elf`、`nor_loader_writer.sh`、`us_spi_firmup.sh`、`us_darwin_firm.sh` 及 `setting/updater/mode*` / `updater/mode*` 触发器；校验 `FX6_STAGEB_BOOT.MANIFEST` 签名、`13/13` Stage-B SHA-256 锁定、`< 50 us` SD 弹出旁路启动器哈希（`2bf27da4d9c99ad5a1c32e5185a35e081ec444e21a3ad7954c04c3740e420291`）、`BK4\0` shadow seed、`uninstall_restore_stock.manifest` 及 `>= 2 GiB`（`2,147,483,648 B`）可用空间配额。
- **支柱 4 [`verify_dual_copy_tier0_receipts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L1562-L1664) & [`run_realhw_bench_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L1767-L1953)**：校验证书双副本（`SD ExFAT` + `Mac Host Vault`）`528 B FX3RCPT1` 的 `CRC32`、全文件 `SHA-256`、16 关键存储面摘要一致性、非平凡 `camera_cid_sha256` 一致性与 `MANIFEST.SHA256` 16 项清单一致性，并配合 [`verify_phase154_report`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h166-phase154-realhw-bench-preflight-usb-cli/outputs/fx6-on-fx3-closure/fx6_closure/realhw_bench_preflight_and_usb_classifier.py#L1956-L2008) 进行 Fail-Closed 篡改检测。

---

## 3. 实测验证结果（已验证事实 vs 未执行实机会话）

### 3.1 已实测的离线与被动主机验证事实
1. **Local Donor + Phase 147 主控门联测**：
   - 命令：`PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase154_realhw_bench_preflight_cli.py outputs/fx6-on-fx3-closure/tests/test_phase147_realhw_milestone_master_gate.py`
   - 结果：`Ran 92 tests in 12.198s — OK`（Phase 154 `46` 项 + Phase 147 `46` 项全部通过）。
2. **Clean-Room 无 Donor 模式测试 (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**：
   - 命令：`FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase154_realhw_bench_preflight_cli.py`
   - 结果：`Ran 46 tests in 0.884s — OK (skipped=1)`（跳过的 1 项为显式依赖本地 Donor 的 `test_39_simulate_ready_bench_local_donor_when_available`）。
3. **洁净室二进制与字节码卫生检查**：
   - 命令：`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`
   - 结果：`[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.04s)` — `ALL GREEN`。
4. **CLI 实测摘要**：
   - `--clean-room --simulate-ready-bench`：`verdict=GO_READONLY_BENCH_PREFLIGHT mode=CLEAN_ROOM_SYNTHETIC bench_go=True usb_state=READY_MSC_054C_0DA1 usb_pkts=0 iokit_handles=0 sd_ok=True locks_13=13/13 rcpt_ok=True emmc_writes_auth=False`（退出码 `0`）。
   - `--simulate-ready-bench`（本地 Donor）：`verdict=GO_READONLY_BENCH_PREFLIGHT mode=LOCAL_DONOR_O_RDONLY bench_go=True usb_state=READY_MSC_054C_0DA1 usb_pkts=0 iokit_handles=0 sd_ok=True locks_13=13/13 rcpt_ok=True emmc_writes_auth=False`（退出码 `0`）。
   - `--probe-host-usb`（当前宿主机真实 `ioreg` 被动采样）：`verdict=NO_GO_BENCH_BLOCKED mode=LOCAL_DONOR_O_RDONLY bench_go=False usb_state=NO_SONY_CAMERA_ATTACHED usb_pkts=0 iokit_handles=0 sd_ok=False locks_13=0/13 rcpt_ok=False emmc_writes_auth=False`（退出码 `1`，真实反映无 Sony 相机接入）。

### 3.2 尚未执行的真实物理 ILME-FX3（`7.02`）实验台会话（未验证部分）
- 尚未把真实物理 ILME-FX3 (`7.02`) 通过 USB-C 线缆连接至宿主机，未捕获实机 `054C:0DA1` / `054C:0336` 硬件描述符。
- 尚未在物理相机上执行人类操作员授权的只读 Tier-0 16 存储面冷备份会话（`AdjustControl 0x40`），尚未从实机 SDXC 卡写入或读回真实机身 `FX3RCPT1` 与主机保险库副本。
- 仅在人类操作员于实际实验台完成真机接入、SDXC 备卡准备与双副本 Tier-0 冷备份验证并获显式授权后，方可执行下一阶段只读真机采集流程（严禁任何未授权写入或跨机型刷写）。
