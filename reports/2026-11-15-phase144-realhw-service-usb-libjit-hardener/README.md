# Phase 144 — 真机主线 Part 6（Pillar 18）：`MSC (054C:0DA1) -> SERVICE (054C:0336)` 独占会话、`op=0xFF` 零挂载 RAM 金丝雀与 Stage-288 §4 (1..6) 加固 ARM64 `libJit.so` ELF 门禁

- **日期**: `2026-11-15`
- **分支**: `codex/h154-phase144-realhw-service-usb-libjit-hardener`
- **目标包**: `outputs/fx3-recovery-adapter/fx3_recovery/`
- **核心模块**: [`realhw_service_usb_session_and_libjit_elf_hardener.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py)
- **强安全红线（硬锁定）**: `LIVE_USB_IOKIT_TRANSMIT_ENABLED = False`、`USB_TX_PACKETS_EMITTED = 0`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`PHYSICAL_DEVICE_WRITES = 0`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`。

---

## 1. 结论先行与事实边界划分

> [!IMPORTANT]
> **严格区分“离线/二进制/Unicorn 实测事实”与“未执行的物理真机动作”**：
> 1. **已实测（Host-only / `os.O_RDONLY` / Unicorn ARM64 / Clean-Room）**：已在本地双模式（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）闭环验证 Stage-285/286 `054C:0DA1 -> 054C:0336` 9 步会话契约、`op=0xFF` 零挂载 RAM 金丝雀门禁、Stage-288 §4 (1..6) 加固 ARM64 `libJit.so`（`8,345 B`）静态反汇编与 Unicorn CPU 仿真，以及被动 `ioreg` XML/文本拓扑解析（`usb_tx_packets_emitted == 0`）。
> 2. **未执行（Physical Camera Session = NOT EXECUTED）**：本任务**未打开任何物理 IOKit USB 设备、未向任何实体 ILME-FX3 (`7.02`) 相机发送 USB 控制/批量包、未执行物理 eMMC 读取/写入或 `/tmp/jiritsu` 上机注入**；真机 Tier-0 冷备份回读仍须在人工显式授权与前置门禁全部通过后单独实施。

---

## 2. 双模式供体核验（`O_RDONLY` vs `FX3_FX6_FORCE_CLEAN_ROOM=1`）

通过 [`inspect_service_usb_and_libjit_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L3285-L3410) 严格以 `os.open(..., os.O_RDONLY)` 核验本地参考 ELF（并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换至确定性净室结构描述符，`.to_dict()` / JSON 中 **0 字节** Sony 专有镜像泄露）：

| 供体构件 | 大小 (B) | SHA-256 前缀 | ELF64 `PT_LOAD` 对齐 | 实测关键符号 / 状态 |
| :--- | :---: | :--- | :---: | :--- |
| FX3 `libJiritsu.so` | `225,200` | `bdef58b24a3b67b4...` | `[65536, 65536]` (`64 KiB`) | 5 个锚点符号全部检出（`adj_cmd_set_file_path`、`adj_cmd_set_file2`、`adj_cmd_get_file2`、`cmd_high_capacity_send_file`、`cmd_high_capacity_get_file`） |
| FX3 `libsencore.so` | `377,328` | `a2907111c4a22314...` | `[65536, 65536]` (`64 KiB`) | 3 个锚点符号全部检出（`AdjustControlFunc`、`Inconcurrent::resource_t::lock`、`TransactionStart`） |
| Stage-288 `libJit_test.so` | `8,345` | `05000a0ecceaa500...` | `[4096, 4096]` (`4 KiB`) | 预加固样本：触发 §4 全部 6 项拒绝码（含 `4 KiB` 段对齐、缺少首条 `unlinkat`、先开输出文件风险、缺少 `FX3S0OK`/`FX3S0ERR` 帧、缺少 `/proc/partitions` 回退等），明确标为未放行上机 |

---

## 3. 两大核心技术支柱实现

### 3.1 支柱 A — Stage-285/286 `054C:0DA1 -> 054C:0336` 独占 `SERVICE` 会话与 `op=0xFF` 零挂载 RAM 金丝雀（`8/8`）

实现于 [`ServiceSessionStateMachine`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L862-L1153)、[`parse_passive_ioreg_usb_topology`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L1198-L1306) 与 [`run_pillar_a_service_usb_session_8_scenario_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L1366-L1680)：

1. **9 步完整会话契约**：`MSC (054C:0DA1)` 7 轮握手 → 同物理端口切换至 `SERVICE (054C:0336)` 并强制 `USBDeviceOpenSeize` 单航道独占互斥（对应 `libsencore.so` `Inconcurrent::resource_t::lock` @ `0xdd00`）→ 7 轮认证到达 Level 2/3（[`check_auth_level_for_category_0x1001`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L704-L735)：`*0x6aee0` 放行 `flags & 0xe000 == 0x4000`，`0xfe48` 拒收 Level 1）→ `ProductInfoFunc`（`pFunc=0x0010` `read0`：12B 请求 + `version=3, res=1` 12B 响应头 + 88B 体）。
2. **`SenserPacket` 与 OSAL/DMM `1 -> 4 -> 16` 生命周期 + 强制 `op=0xFF` 前置门槛**：
   - `AdjustControl (pFunc=0x0040, category=0x1001)` 自动跟踪 `0x124`（`292 B`）内联参数/DMM 阈值与 `Phase 1 (TransactionStart) -> Phase 4 (DoExecute) -> Phase 16 (~SubsystemCommunicationCommand / dmm_free)` 转换。
   - **在放行任何 `op=0x00`（`/dev/nflasha6` `/tmp/jiritsu`）指令前**，必须先通过 `SET_FILE2 / GET_FILE2 op=0xFF`（`slot <= 0x11`、`size <= 5 MiB` @ `*0x46bd8`、零 `sys_mount`、零 `dlopen`）RAM 往返校验；硬拒绝 `slot > 0x11`、`size > 5 MiB`、单航道并发重叠 `seq`，以及缺失 `STOP (0336:7) -> release (0336:8) -> 054C:0DA1 return (0da1:9)` 收尾序列。
3. **纯被动 `ioreg` 拓扑干跑解析器**：兼容 XML plist 与文本 `ioreg -p IOUSB -l -w 0` 快照，零 IOKit 句柄打开，零 USB 帧发送（`usb_tx_packets_emitted == 0`）。

### 3.2 支柱 B — Stage-288 §4 (1..6) 加固 ARM64 `libJit.so` ELF64 构建与静态/Unicorn 门禁（`8/8`）

实现于 [`build_hardened_libjit_elf64`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L2149-L2258)、[`verify_hardened_libjit_elf64`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L2412-L2724) 与 [`emulate_hardened_libjit_in_unicorn`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py#L2726-L2926)：

1. **§4.1 构造函数首条自删除**：静态反汇编核验第一条系统调用必为 `unlinkat(AT_FDCWD=-100, "/tmp/jiritsu/libJit.so", 0)`（AArch64 `x8=35; svc #0`），防止 `p6` 遗留 root 属主 `.so`。
2. **§4.2 先读后建、拒绝 `0 B` 截断**：源节点强制以 `O_RDONLY | O_CLOEXEC` 打开并读取验证 `== 512 B` 之后，才允许打开/写出 `/tmp/jiritsu/sector0.bin`，避免失败时 `O_TRUNC` 产生 `0 B` 歧义。
3. **§4.3 528 B 强校验输出帧**：`8 B` `b"FX3S0OK\x00"` + `<II(512, crc32_ieee)` + `512 B` `Sector 0`（magic `"8246"`、version `"2.00"`、`n_partitions == 30`、`p1 == (0x80, 0xbf80)`）。
4. **§4.4 整盘节点校验、`/proc/partitions` 回退与 `16 B` `FX3S0ERR` 回执**：`newfstatat` 校验 `/dev/nflasha` `S_ISBLK`，异常时探测 `/proc/partitions` 与 `/dev/nflasha1`，并写出 `16 B` `b"FX3S0ERR" + <ii(stage, errno)` 结构化失败回执；已在 Unicorn ARM64 仿真中实测正常读盘、短读不截断与缺少 `/dev/nflasha` 三条路径。
5. **§4.6 `64 KiB` 页对齐与 `DT_*` 边界约束**：强制 `ET_DYN`（`e_machine = 183`、`< 16 KiB`、`8,345 B`）、非重叠 `R|E` 与 `R|W` `PT_LOAD`（`p_align = 0x10000`、严禁 `W+X`）、`DT_HASH`（`nbucket >= 1, nchain >= 1`）以及 `DT_SYMTAB` / `DT_STRTAB` / `DT_HASH` / `DT_INIT` 严格落在文件与 `PT_LOAD` 内（捕获历史 `0x2100 > 0x2099` 越界缺陷）。
6. **静态系统调用与危险令牌防火墙**：扫描 ELF 符号/字符串与 AArch64 `svc #0` 寄存器追踪，拦截针对 `/dev/nflasha*` / `/dev/cnflasha*` / `/dev/pnflasha*` / `/dev/mtd*` / `/setting` 的 `O_WRONLY` / `O_RDWR` / `write` / `pwrite64` / `ioctl` / `mount`，以及 `edisx` / `uc_mkfs` / `nor_loader_writer` 危险字串。

---

## 4. 实测验证回执

| 命令 / 测试范围 | 运行模式 | 实测结果 | 耗时 |
| :--- | :--- | :--- | :---: |
| `/usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_service_usb_session_and_libjit_elf_hardener.py` | Local Donor (`os.O_RDONLY`) | `46/46` 通过 (`OK`) | `2.567s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_service_usb_session_and_libjit_elf_hardener.py` | Clean-Room | `46/46` 通过 (`OK`) | `2.325s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | Recovery 全套 (Local Donor) | `775` run (`OK`, `skipped=1`) | `59.317s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | Recovery 全套 (Clean-Room) | `717` run (`OK`, `skipped=9`) | `26.197s` |
| `/usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_phase130_milestone_master_gate.py` | Phase 130 里程碑总门禁 | `42/42` 通过 (`OK`) | `4.705s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-service-usb-libjit`（及 `--clean-room`） | CLI 单支柱门禁 | `PA=8/8, PB=8/8, hardened_elf_bytes=8345, usb_tx_packets_emitted=0, all_passed=True` | `<0.5s` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-all-recovery --with-phase94 ... --with-phase144` | 18 支柱全开（默认无参数仍 `7/7`） | `pillars=18/18, all_passed=True, passive_tx_bytes_emitted=0` | `<1.0s` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净与二进制/pyc 审计 | `ALL GREEN` (`CLEAN`) | `0.05s` |

> 注：上述全套发现测试使用 `PYTHONPATH=outputs/fx3-recovery-adapter`，系因既有测试 `test_ab_bank_and_interrupted_ota_verifier.py` 直接 `import fx3_recovery`；本阶段新增的 `test_realhw_service_usb_session_and_libjit_elf_hardener.py` 本身无论是否设置 `PYTHONPATH` 均可直接通过（`46/46`）。

---

## 5. 专有修改文件清单（严格 6 个文件）

1. [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/realhw_service_usb_session_and_libjit_elf_hardener.py)
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)
4. [`outputs/fx3-recovery-adapter/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/README.md)
5. [`outputs/fx3-recovery-adapter/tests/test_realhw_service_usb_session_and_libjit_elf_hardener.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/outputs/fx3-recovery-adapter/tests/test_realhw_service_usb_session_and_libjit_elf_hardener.py)
6. [`reports/2026-11-15-phase144-realhw-service-usb-libjit-hardener/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/reports/2026-11-15-phase144-realhw-service-usb-libjit-hardener/README.md)

## 关联参考文档

- [Stage-286 线协议与 `op=0xFF` RAM 金丝雀审计](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/README.md)
- [Stage-288 Jiritsu 只读载荷与 §4 加固清单](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h154-phase144-realhw-service-usb-libjit-hardener/work/sony-firmware-20261024/stage288-jiritsu-readonly-payload/README.md)
