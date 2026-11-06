# FX6 CP helper 地址无关候选（仅离线）

**状态：离线候选 + 一次真实 VM 测试；CP helper 已在 FX6 原内核上绑定，AP natural bootin 已开始；完整 FX6 开机/菜单仍未验。** 目标是让 FX6 原内核能在固定 FX3 平台上越过固定 CP helper 的 FX3 地址门；这是对既有 `fx3-cp-backup-v5-native101` 的最小局部改造。

## 改动

原 helper 在 `fx3-backup-sync101-v1.h` 中：

- 要求 `kallsyms_lookup_name("pcidma_transfer_async")` 恰为 FX3 `0xffffff80083220c8`；
- `sync100_native_fallback` 硬编码 FX3 fallback `0xffffff8008322228` / `0xffffff80083220d8`。

候选只改这两处：

1. 入口接受 FX3 `0xffffff80083220c8` **或** FX6 `0xffffff8008322f70`，并继续核验 16 字节入口 `b4000b00/a9bb7bfd/910003fd/a90153f3`；两版前 0x200 字节已逐字节相同。
2. fallback 改为运行时计算 `api+0x160` / `api+0x10`，由 `.text` 中的字面量指向 `.bss` 全局，启动时写入；不再硬编码 FX3 绝对地址。
3. 模块内部名改为 `fx6_cp_backup_sync100_agnostic_v1`，CPIO 成员路径 `simulation/fx3-cp-backup-reset-v1.ko` 不变，`/init` 无需改动。

未改动：`os/dma` 目标 schema、CP bank 物理 `0x4040d2000`、Backup、固定 QEMU/DTB/kernel、FX3 `/init`、其他 1140 个 CPIO 成员。

## 构建与宿主验证

- 编译器：项目内 `zig-aarch64-macos-0.17.0/zig`；`-g0` 去掉调试节，模块 66,552 B。
- 新 CPIO：453,184,500 B；仅目标成员由 190,648 B 变为 66,552 B；其他 1140 个成员逐字节相同；尾部 124,096 B 零填充；`TRAILER!!!` 保留。
- 宿主测试：`host_test_agnostic.c` 以 `TEST_API_BASE` 分别设 FX3/FX6 地址，读取 `cp101-native-file-bank-fixture.bin`，两轮均 exit 0，覆盖 40B schema、DMA copy、锁、回滚、错误路径、非目标 fallback 与 cleanup restore；两轮均额外断言 fallback 全局等于 `base+0x160` / `base+0x10`。
- 模块 ABI：ELF64 AArch64 relocatable；`.modinfo` 为 `license=GPL`、`depends=osal_uipc`、`vermagic=4.9.337-scel+ SMP preempt mod_unload aarch64`；`__this_module` 的 init/cleanup 重定位在 `0x158`/`0x2b8`。

## 2026-11-05 真实运行（唯一一次 Start）

- 运行：`runs/cp-bind-fc2ad401`；QEMU exit 0、process reaped、双锁 released；host 18.257 s。
- 绑定：`FX3_SYNC100_API_BIND phase=original api=ffffff8008322f70`（FX6 地址）→ `FX6_SYNC100_AGNOSTIC_BIND fallback_zero=...30d0 fallback_nonzero=...2f80` → `FX3_SYNC100_API_BIND phase=bound` → `FX3_SYNC100_BACKEND_BOUND`。
- CP helper：`FX3_BACKUP_CP_INSMOD_RC=0`（原始串口；严格整行解析因交织漏记）、`FX3_BACKUP_CP_PUBLIC_OWNER result=0`、`initcall ... returned 0`。
- 后续：`FX3_UTIMER_RC=0`、`FX3_BACKUP_ORIGINAL_SEED_BEGIN`、`FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN/END`、`FX3_AP_NATURAL_BOOTIN_BEGIN`、`FX3_AP_BOOTIN_LAUNCH_PID=227`、`FX3_BACKUP_CP_LIVE_OBSERVER_PID=228`。
- 按预设在 AP guard 处停止；没有 AP 初始化/菜单证据。运行回执与串口哈希见 `runs/cp-bind-fc2ad401/RESULT.json`、`RUN-REPORT.md`、`RUN-SHA256SUMS`。


## 2026-11-05 第三次运行（FX6 appFw + FX6 内核）

- 新 CPIO：`guest-hybrid-fx6kernel.cpio`，来源 `hybrid-ap-candidate/guest-three-entry.cpio`（`bb618bd2…3fff02`），仅替换 CP helper；总长 453,184,500 B，其他 1139 个成员逐字节一致。
- 运行 `runs/cp-bind-6e83a14a`：QEMU exit 0、reaped、双锁 released；host 180.16 s；serial 4,006,697 B。
- CP helper 绑定成功；`/usr/lib/appFw.so` 已映射并出现 `FX3_PROFILE_FRAME ... module=/usr/lib/appFw.so`、`FX3_PROVIDER_CALLER`。
- 停在已知 `assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075`：`send_and_wait_cmp_i` 向 `0x92840747` 发送 10B `0d202d030a0001800000`（source `0x81cf6196`）后发送非零，未进入 `osal_rcv_msg_tmo`；无 `FX3_AP89_SCREEN_CREATE`/菜单。
- 这不是 CP 失败；是 FX6 AP 的 CAPID 发送/初始化断言。下一步需只读观测 CAPID 分支/字段，再做字段级初始化/回复适配；不得手填成功。

## 未做与限制

已执行两次独立单次 VM：第一次 FX6 内核 + 固定 FX3 CPIO 到达 AP natural bootin；第二次 FX6 内核 + FX6 appFw 实际执行到 CAPID `assert1075`。仍未取得 AP 初始化成功或 FX6 菜单，完整开机未完成。下一关是 CAPID 初始化/回复；不得手填 `initialized=1` 或伪造回复。

## 文件

- `fx6-cp-backup-sync100-agnostic.c` / `fx3-backup-sync101-v1.h` / `fx6-cp-backup-sync100-agnostic-module-unit.c`
- `fx6-cp-backup-sync100-agnostic-g0.ko`
- `guest-cp-helper-agnostic.cpio`
- `build_cpio.py`、`verify_cpio.py`、`host_test_agnostic.c`
- `CPIO-BUILD.json`、`CPIO-VERIFY.json`、`HOST-FX3/6-STDOUT.txt`
