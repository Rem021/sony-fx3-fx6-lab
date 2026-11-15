# Phase 136｜实机主线第一阶段：Stage-288 `libJiritsu.so` `SET_FILE2` P0 加固、`U4/U5/U6` 二进制反汇编闭环与 Tier-0 只读冷备份阻断门

> **一句话结论（实测边界严格区分）**：已完成基于 `os.O_RDONLY` + `mmap.ACCESS_READ` 只读供体取证、纯 Python AArch64 指令解码器（Capstone 不可用时的确定性回退）、Stage-288 §4 P0 六项加固、`U4`/`U5`/`U6` 二进制闭环及 Tier-0 完整冷备份阻断门（[`realhw_jiritsu_and_tier0_dumper_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/outputs/fx6-on-fx3-closure/fx6_closure/realhw_jiritsu_and_tier0_dumper_auditor.py)），**44/44 项双模式单测在本地供体模式（`LOCAL_DONOR_O_RDONLY`）与无供体净室模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）下全部通过**；安全红线硬锁 `persistent_emmc_writes_authorized = False`、`usb_device_attach_executed = False`、`persistent_write_release = False`。**物理 FX3 真机 USB/PTP 联机、实际 eMMC 分区回读与实机冷启动未在本阶段执行**。

---

## 1. 四大核心支柱与实测结论总览

| 支柱 | 验证目标 | 关键二进制/策略实测事实 | 状态（仅离线/只读验证） |
| :--- | :--- | :--- | :---: |
| **Pillar 1 (`JIRITSU_0X40_DISPATCH_AND_STAGE288_P0_HARDENING`)** | `U6` 全分发表闭环 + Stage-288 `SET_FILE2` P0 (1..6) 加固 | FX3 `7.02` `libJiritsu.so`（`225,200 B`，SHA-256 `bdef58b2...`）`.rodata` `0x2c124..0x2c67b` 共 `19` 项 `0x1001` 命令，**`0` 个内置操作码直接导出 `/setting` 或 `/dev/nflasha*`**（仅引用 `/dev/nflasha6`）；16 处关键 AArch64 指令与预期完全一致；`ld-2.25.so` 强制 `PT_LOAD p_align=0x10000 (64 KiB)`；`devno.ko` + `emmc.ko` + `setup_nflash` 验证 `/dev/pnflasha*` → `/dev/nflasha` 整盘符号链接；6 项 P0 加固及 8B `J0 + u16 len + u32 CRC32` 帧校验闭环 | **CLOSED（离线只读）** |
| **Pillar 2 (`U4_ZERO_SECTOR0_NFLASHA20_21_BRIDGE`)** | `U4` 调用方行为 + Strategy-A 零 Sector 0 改写桥接 | FX6 `libInfraSetupFile.so`、`appFw.so`（引用 `/dev/nflasha20`）与 `libInfraKikiLogGenerator.so`（引用 `/dev/nflasha21`）均有 Unicorn 挂载失败容错证明；`kikilog.ko`（`352f9b8a...`）**0 次引用 `/dev/nflasha21`**，仅读写 `/etc/opelog/logs/`；Strategy-A 通过 `/dev/nflasha20 -> /dev/nflasha30`（`48 MiB`）+ `tmpfs /etc/opelog` 完全避免 `edisx.elf` 重分区，保持 FX3 `Sector 0`、`p12:/cert`（`40 MiB`）与 `p18:/lens`（`20 MiB`）`0 B` 修改 | **CLOSED（离线只读）** |
| **Pillar 3 (`U5_P1_ONESHOT_SELECTOR_AND_P3_FALLBACK`)** | `U5` `p1` 单次切换与 `p3` Normal Boot 回退契约 | `loader_nor.bin`（`4358c839...`）检测 `\mode\cmode`、`\updater\mode`、`BK4\0` byte-8 及粘性寄存器 `0xFE170028`；`up.sh`（`c774320a...`）与 `ud_send_lsi.elf`（队列 `0x804b0376`）控制全部 7 种模式；FX3/FX6 `cpapp-b.bin` 对 `updater/mode*` 与 `0x804b0376` 均为 **0 次引用**（CP 侧完全被动） | **CLOSED（离线只读）** |
| **Pillar 4 (`TIER0_COMPLETE_COLD_BACKUP_STOP_GATE`)** | Tier-0 完整冷备份停机门禁 | 校验 11 项 `TIER0_REQUIRED_BACKUPS`（`sector0` `"8246"`/`"2.00"` 30 分区、`boot0`、`boot1`、`p1_updater`、`p2_backup_bin` `>=262144 B`、`p2_psd_bin`、`p2_defdet_bin`、`p6_jiritsu`、`p12_cert`、`p18_lensfile`、`spi_nor_ddrtraining`）及 6 项额外探针（`p1_dat2=91030080`、`p1_dat3`、`p2_cxd90057.dtb` `0xd00dfeed`、`p8_tomco.txt`、`p5_wbi_header.bin` `WBI2`、`spi_nor_loader`），5 项负向故障注入全数拦截 | **PASS（离线沙箱；真机备份待采集）** |

---

## 2. 二进制取证与加固细节（只读核验）

### 2.1 `U6`：`libJiritsu.so`（FX3 `7.02`）`0x40 AdjustControl` 分发表与线协议门控

- **供体对象**：`libJiritsu.so`（`225,200 B`，SHA-256 `bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9`）。
- **分发表闭合**：`.rodata` `0x2c124..0x2c67b`（步长 `72 B`）完整枚举 `0x01 JIRITSU_MODE` .. `0x12 JIRITSU_FILE_DELETE2`（`flag=0x40`）与 `0x13 JIRITSU_TEST_UI_VIEW`（`flag=0x00`），共计 `19` 项。除 `0x02 JIRITSU_MOUNT` / `0x11 JIRITSU_GET_FILE2` 操作 `/dev/nflasha6`（`/tmp/jiritsu`）或 `/mnt` 外，没有任何内置命令直接暴露 `/setting` 或其他 `nflasha*` 分区。
- **关键 AArch64 钉扎指令**（经 `decode_aarch64_insn` 解码与文件字节比对）：
  - `0x8a1c`: `3940a280` (`ldrb w0, [x20, #0x28]`) — `SET_FILE_PATH` 强制首字节 `0x00`；
  - `0x95a4`: `7100081f` (`cmp w0, #2`) — `adj_cmd_set_file2 @ 0x9528` 拒绝 selector `0x02`；
  - `0x976c..0x977c`: `adrp x0, 0x30000` -> `bl sys_file_chk_exist@plt` -> `cbz w0, 0x9944` — 若 `/tmp/jbusy` 存在直接跳转 `0x9944` 返回 `0x10000011`；
  - `0x9908` / `0x9928`: `dlopen@plt` / `dlclose@plt` — 仅在 `jbusy` 不存在时写入并加载 `/tmp/jiritsu/libJit.so`；
  - `0x9efc`: `121e7800` (`and w0, w0, #~2`) — `adj_cmd_get_file2 @ 0x9e74` 拒绝 `0x00/0x02` 选择子，仅允许 `00 ff 00` 帧。

### 2.2 Stage-288 §4 P0（1..6）载荷契约与 `64 KiB` ELF 对齐

1. **P0-1 入口自删除**：构造器进入后立即执行 `unlinkat(AT_FDCWD, "/tmp/jiritsu/libJit.so", 0)`（AArch64 `mov x8, #35` + `svc #0`），避免残留在 `p6:/tmp/jiritsu` 或阻碍二次测试。
2. **P0-2 读失败不截断**：在确认目标只读打开及完整 `read` 校验通过前，绝不以 `O_TRUNC` 清空输出文件。
3. **P0-3 固定 8 字节输出头**：`<2sHI`（`b"J0"` + `u16 payload_len` + `u32 zlib.crc32(payload)`），配合 `GET_FILE2` 单帧回传防截断与防静默损坏。
4. **P0-4 整盘节点确认**：核验 FX6/FX3 同源 `devno.ko`（`2baa1028...`）、`emmc.ko`（`2c170204...`）、`setup_nflash`（`375 B`，SHA-256 `055cb3db...`）及 `setup_nflash.sh`（`611 B`，SHA-256 `cc71a751...`），确认 `[ -r /dev/pnflasha ] && ln -sf /dev/pnflasha /dev/nflasha` 产生整盘节点 `/dev/nflasha` 及 `/dev/nflasha1..30`。
5. **P0-5 `p6` 持久化边界**：显式确认 `SET_FILE2` 写入 `/tmp/jiritsu/libJit.so`（`nflasha6`）必须在入口自删后清理现场，不可留下常驻脚本。
6. **P0-6 `64 KiB` 页对齐与动态表 containment**：FX3 `ld-2.25.so`（`90b4fe73...`）与 FX6 `ld-2.25.so`（`8eeed290...`）均采用 `PT_LOAD p_align = 0x10000`；审计器拒绝 `4 KiB (0x1000)` RW/RX 同页合并风险、`DT_HASH`/`DT_SYMTAB`/`DT_STRTAB` 越界及非 `(1, 1, 0, 0)` `DT_HASH`。

### 2.3 `U4`（Strategy-A 零 Sector 0 桥接）与 `U5`（`p1` 单次回退）

- **`U4` 零 Sector 0 改写证明**：FX3 原厂 Sector 0 中 `p20=0 B`、`p21=0 B`、`p30=48 MiB`（`50,331,648 B`）。Strategy-A 在内存运行期将 `/dev/nflasha20` 符号链接至 `/dev/nflasha30`，并将 `/etc/opelog` 挂载为 `tmpfs`，完全消除 `edisx.elf` 重分区需求，`Sector 0`、`p12:/cert`、`p18:/lens` 零触碰。
- **`U5` 回退证明**：`loader_nor.bin`（`4358c839...`）、`up.sh`（`c774320a...`）、`ud_send_lsi.elf`（FX3 `9fb4bd02...` / FX6 `d0ece6ca...`）与 `cpapp-b.bin`（FX3 `c90d00d8...` / FX6 `60de0ab5...`）联合证实：仅当 `/setting/updater/mode*` 清空、`BK4\0` byte-8 为 `0x00` 且 Sub-LSI 模式为 `0` 时，下一次冷启动无条件回到未改动的 FX3 `p3` Normal Boot。

---

## 3. 交付文件与 CLI/测试验证记录

- **本阶段仅修改/新增以下 6 个文件**：
  1. [`realhw_jiritsu_and_tier0_dumper_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/outputs/fx6-on-fx3-closure/fx6_closure/realhw_jiritsu_and_tier0_dumper_auditor.py)
  2. [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
  3. [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（新增 `verify-realhw-jiritsu-tier0` 子命令）
  4. [`outputs/fx6-on-fx3-closure/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/outputs/fx6-on-fx3-closure/README.md)
  5. [`test_phase136_realhw_jiritsu_tier0.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/outputs/fx6-on-fx3-closure/tests/test_phase136_realhw_jiritsu_tier0.py)（44 项正/负向双模式测试）
  6. [`reports/2026-11-14-phase136-realhw-jiritsu-setfile2-tier0-dumper/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h144-phase136-realhw-jiritsu-setfile2-tier0-u4u5u6/reports/2026-11-14-phase136-realhw-jiritsu-setfile2-tier0-dumper/README.md)

- **CLI 验证入口**：
```sh
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
  /usr/bin/python3 -B -m fx6_closure verify-realhw-jiritsu-tier0 [--clean-room] [--json] [--output PATH] [--tier0-bundle-dir DIR]
```

- **后续待办（需在真机冷备份获得真实硬件束后推进）**：
  1. 在物理 FX3 (`7.02`) 上执行只读 Tier-0 全量回读并落盘完整 `backup-manifest.json`，使用 `verify-realhw-jiritsu-tier0 --tier0-bundle-dir <DIR>` 放行停机门禁。
  2. 进入实机主线下一阶段前，保持 `persistent_emmc_writes_authorized = False`，严禁跨机型整分区刷写。
