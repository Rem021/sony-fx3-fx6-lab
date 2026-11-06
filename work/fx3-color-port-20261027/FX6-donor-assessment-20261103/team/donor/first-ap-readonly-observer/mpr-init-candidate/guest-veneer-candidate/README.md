# FX6 AP → 固定 FX3 MPR：guest 诊断桥候选

**结论：已交叉编译并离线审计，尚未装载或执行。** 新 `guest-veneer.cpio` SHA `8abed37418a0f07e8193228ca2242f185103b6b5f98959b98821bbeeb3ad3b5d`，453184500B，保留固定 FX3 Image/QEMU/完整 DTB/env/`/init`/Backup/17 helpers。相对已审三入口 CPIO SHA `bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02`，1140 个原成员仅 `usr/lib/appFw.so` payload 变化，新增 `usr/lib/libfx6diag.so` 一项；其余 1139 项的 newc header、payload、顺序和权限一致。bsdtar 独立列出 1141 项，零填充恢复原 initrd 总长度。见 [static-receipt.json](static-receipt.json)、[receipt.json](receipt.json)。本轮没有启动 QEMU、占锁、刷写或访问设备。

## 客体软件合同

| 原件与接缝 | 固定字节与做法 | 仍未知 |
|---|---|---|
| FX6 `appFw.so` 原 SHA `a1c58b69…086067` | 复制件 SHA `c31bc293…44db1`，仅 3 个许可范围共 75B 变化：`0xc0d3`/`0xce44` 的动态字符串、文件 `0x2ed10f0` 所在动态表的一个备用 `DT_NULL`。AP `0x212f7b8` 的原 BL 字 `429fa797` 及 `JUMP_SLOT 0x2ef1368` 保留，导入改为 `fx6diag_mpr_init`；EnterRec `JUMP_SLOT 0x2ef2670` 改为 `fx6diag_mpr_enterrec`；新增 `DT_NEEDED libfx6diag.so`。完整范围见 [ap-patch.json](ap-patch.json)。 | Sony loader 的实际解析和运行时全局符号作用域未实测。 |
| 原 FX3 `libmpr.so` SHA `9aeef3b9…1b57c` | `bridge_runtime.c` 用 `RTLD_NOLOAD` 取得已装载原库，`dlsym` 精确原 mangled Init；要求基址+`0xb6844`、原首字 `fd7bb2a9`、原文件全 SHA 与大小一致，失败即停。唯一原调用经桥 `fx6diag_call_original+8` 的 `blr x1`，原返回原样保留，非零不改为成功。 | 真实 `NOLOAD` 命名空间与返回值。 |
| 历史真实 Init 参数 SHA `585d8918…5430cf1` | [genuine-input.bin](genuine-input.bin) 656B：count=2、活跃槽 `4096/4112`、其余槽 0、源 `+0x28a` u16=1440。`bridge_core.c` 将已证 FX3 Xavcs Init 所需 u16 暂填 780，保留 57 个源回调与 18 个 FX6 专有回调；46 个原非空共有槽改为互异 thunk，11 个原空槽保持空。单次原子状态 `0→1→2(发布)→3(原调用)→4(返回)`，数据在原 Init 前发布。 | 本轮输入可能不同；Mxf、PowerOn 所有权与异步回调语义未闭合。780 不许视为 Mxf 等价。 |
| 57 个回调与录制入口 | 每个 `fx6diag_slot_00..56` 第一条是不同 `BRK #0x600..638`，第二条自环；`fx6diag_mpr_enterrec` 第一条 `BRK #0x7f0`，`fx6diag_failstop` 为 `BRK #0x7fe`。不解引用 payload、不返回、不吞事件。 | BRK 本身不保证宿主捕获；必须先通过下述 Z1 门。录制不可放行。 |

桥 ELF SHA `b5d546eb…5b2428b`，AArch64 ELF64；`PT_LOAD` 文本 VA `0x11c40` ↔ 文件 `0x1c40`。原字举例：Init VA `0x120d0`/file `0x20d0` `fd7bbaa9`；slot00 VA `0x12c5c`/file `0x2c5c` `00c020d4`；`blr x1` VA `0x12e3c`/file `0x2e3c` `20003fd6`；EnterRec VA `0x12e24`/file `0x2e24` `00fe20d4`。`audit_elf.py` 验证桥仅依赖固定 guest `libdl.so.2/libc.so.6`，6 个 `GLIBC_2.17` 强导入，6 个 `R_AARCH64_JUMP_SLOT`、70 个 `R_AARCH64_RELATIVE`，57 个独立导出；这仍是静态 ELF 合同，不是 guest ABI 通过。参见 [elf-audit.json](elf-audit.json)、[cross-build.json](cross-build.json) 和 [source-sha256.json](source-sha256.json)。AArch64 ELF 重定位定义参照 [Arm AAELF64](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst)。

## 单轮只读观察门（待 coordinator 审核与 VM 窗口）

[run_guest_once.py](run_guest_once.py) 继承既有单 owner 双锁、固定平台完整 `verify()`、34 项参数中仅 `20`（新日志）和 `31`（本候选 initrd）变化、零按键、观察 120 秒/总 180 秒及自有进程回收。独立差分在 [runner-diff.patch](runner-diff.patch)。先从完整 early IM maps 定位原 IM，命中原 `0x406284` type4 记录，再由同记录 `dlsym` 返回和原 AP 入口 VA 算当前 AP bias；在 **AP `0x212f7b8` 调用尚未执行**的硬断点上，从 IM 原 `DT_DEBUG` VA `0x418ec0` 读取当前 `r_debug/link_map`，用桥、MPR 本轮 `l_addr` 和当前 CPU ELF 头/PHDR/原指令确认身份。名字读取逐 16B、跨页前截断，上限 256B；链最多 192 节点。

停在 AP 调用点时，必须全部取得 57 个 thunk Z1、EnterRec、failstop、桥原调用 `blr`、原 MPR Init、已定位阈值读取 `0x11fac8` 与 AP 返回，共 **63 个**成功回执，才允许移除 AP 调用点断点并用 addressless `c` 继续。任何安装、身份、QMP/RSP 或地址失败，保持暂停直接 quit/reap；不能进入原 Sony Init。首次 thunk 命中记录 slot、`x0–x7/SP/LR`、TLS、vCPU 和原指令；vCPU 仅为观测值，不能当 Linux 线程 ID。同调用由 TLS、参数、原 `blr` 返回链及 AP 帧核对，允许同 TLS 跨 vCPU；错误 TLS/帧拒绝。`0x11fac8` 是**已定位**的 FX3 writer 阈值消费点，不证明它是全程序首读；如先于录制阻止门命中即终止观测。

首次诊断轮**无论 Init 返回何值均不移除保护后继续执行**：移除 Z1 后仍保持全 VM 暂停，直接 QMP quit/reap 自有进程。API16 恢复因此故意未执行，回执分别给 `diagnostic_captured` 与 `lifecycle_healthy=false`；不得把前者写成启动或功能验收。正式生命周期恢复需先证明异步 thunk 受控且 EnterRec 获真正支持。QEMU 官方 [gdbstub 文档](https://www.qemu.org/docs/master/system/gdb.html) 说明 TCG system 模拟宣告无限硬件辅助断点；本机固定 QEMU `gdbstub/system.c:626` 和 `accel/tcg/tcg-accel-ops.c:126–145` 证实 Z1 转发至每 CPU `BP_GDB`，但**本候选的 63 个同时安装及真实命中仍待运行**。

## 离线复核与下一步

在本目录依次运行 `python3 -B build_guest.py`、`python3 -B audit_elf.py`、`python3 -B audit_candidate.py`、`python3 -B test_guest_host.py`、`python3 -B run_guest_once.py --preflight`。`build_guest.py` 在同目录临时构建并逐字节重现桥 ELF；`audit_candidate.py` 对照原 CPIO 逐成员流式哈希和 bsdtar；[host-tests.json](host-tests.json) 的 6 例覆盖 63 个 Z1 中途拒绝、同 TLS 跨 vCPU、错 TLS/帧、link_map 页边界和不恢复故障。既有观察器 18 例和 MPR 6 例本轮另行重跑，均 `PASS_NO_QEMU`；[core-tests.txt](core-tests.txt) 记录真实参数与负例。`--preflight` 已检查外盘 UUID、冻结平台所有文件 SHA 与现有三入口合同，见 [preflight.json](preflight.json)，没有启动 VM。

**下一最小运行**：coordinator 审定本候选源码 SHA 后，由唯一 runtime owner 在双锁空闲时仅运行一次 `python3 -B run_guest_once.py --reviewed-run`；新私有 run 目录收集原始 RSP 停包、当前 ELF/PHDR/原字、桥状态/原返回或首未知 callback，任何首故障即止，不自动重跑。若 `DT_DEBUG` 尚未可读、桥未装载、`NOLOAD` 不成立或 Z1 未全装，准确记第一拒绝点，不能猜造成功。此次观察前不生成录制候选，不更改固定 FX3 平台或 17 helpers。
