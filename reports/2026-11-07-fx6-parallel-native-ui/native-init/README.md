# FX6 Candidate 287 原生 UI 初始化静态复核

时间：2026-11-07。只读固件与已存在运行产物；没有启动、暂停、修改虚拟机或 donor，没有改 live shim。

## 结论

1. Candidate 287 CPIO 的 `usr/lib/appFw.so` 确为 50,520,424 B 的 FX6 donor，SHA-256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`，与 donor 原件逐字节一致。`+0xc0b044` 与 `+0xc0b470` 初始化链属于这份实际输入。
2. 287 实际 shim 不是仓库当前 `libgrm-fbinit25.c` 的同一构建证明。CPIO 成员 `usr/lib/libgrm-fbinit9.so` 为 72,296 B、SHA-256 `46161fe7ff7fe40edb9b5fc1648e9b5c5ac23994d8e73e3d4ed2a2ac6ef7fe75`；其 `.symtab` 编译单元名为 `libgrm-fbinit25-287.c`。对应源码已定位 `/tmp/libgrm-fbinit25-287.c`，58,024 B、SHA-256 `64241d9d0067f816bd181624c30b3051e8ce6903578fdb21d76dc2473fd5a6e4`。文件名与包装函数反汇编相符；缺少完整构建命令/编译回执，因此不把它单独视为可重建的源码绑定证明。
3. 当前 `FX6_APP_CONFIG_HOLD real_returned` 只证明真实入口返回。它不能区分 OSAL 创建线程失败、原厂线程 trampoline 阻塞、或 `uxengine_init2` 内阻塞。把该 marker 当作 UI 初始化成功会漏掉真实失败。

## 原厂入口与线程 ABI（已证实）

`Application_System_Init` (`+0xc0b044`) 将参数写入 `+0x303d990`，加载 `*(base+0x2ef00e8) = base+0xc0b470`，随后在 `+0xc0b118` 调用 `+0x222dd58`，参数为 `(UI_worker, NULL, thread_type=0)`。

该入口最终走 `+0x222dc1c`，在 `+0x222dcf4` 通过 PLT 调用 `osal_create_waitable_thread(param, &handle)`。精确参数布局：

| param 偏移 | 值/语义 |
|---|---|
| `+0x00` | 线程名指针，线程类型 0 表项为 `AppFw` |
| `+0x08` | 调度类别 `4` |
| `+0x10` | 原厂 trampoline `base+0x222dbc0`，并非直接 UI_worker |
| `+0x18` | 原厂线程状态对象 `base+0x6116778` |
| `+0x20` | `uint16_t 0x01cf` |
| `+0x24` | 表项调度优先级 `1` |

类型 0 的固定表位于 `+0x2d196f0`，含优先级 `1`、CPU 参数 `15`、flag `1`。不能把 CPU 参数 15 直接解释为第 15 号 CPU；现阶段只记录原始值。

原厂 trampoline 在 `+0x222dc00` 先调用 `+0x21be660`，然后才在 `+0x222dc08` 调用 UI_worker。直接另起 pthread 调 `+0xc0b470` 会跳过这段原厂线程上下文初始化，不适合作为“最小恢复”。

## OSAL 失败的静默路径（已证实，尚未证实为本轮根因）

CPIO `usr/lib/libosal_utm.so` 为 10,216 B、SHA-256 `a7ced89e69b0efef4d993f89793992eae69afc346018fe712eb93307c7a1dfa2`。

`osal_create_waitable_thread` 位于 `libosal_utm+0x11d0`，将 `param` 交给 native pthread wrapper `+0x1090`。该 wrapper 先调用 `prctl(PR_SET_NAME, ...)`，随后按调度类别选择 `sched_setscheduler`；本次类别 4 走请求优先级 1、策略 `SCHED_FIFO` 的路径。

失败分支 `+0x110c` 将共享返回状态写为 `-1024`，解锁并 `pthread_exit`，**不调用 AppFw trampoline**。pthread_create 自身失败返回 `-1023`。成功时共享状态保留 Linux TID；因此诊断不能写成 `rc == 0` 才算成功。

原厂 `+0x222dcf4` 调用方没有检查负返回值，随后可能调用 `osal_set_cpu`，最终仍返回 handle。外层 287 包装把原函数声明成 `void (*)(const char *)`，调用后无条件打印 `real_returned`。所以运行日志没有区分线程创建失败与后续 UI 阻塞的能力。

本轮 **没有运行期 errno 或返回值证据**，不能据此宣称 `sched_setscheduler` 就是根因，也不建议直接绕过它。

## UI worker 与 Arena

UI worker (`+0xc0b470`) 顺序为 `uxengine_init2` → `+0xc0b258` 注册 Arena → `sys_setCurrentDirectory` → `setDatabase` → 构造本机应用上下文 → `+0xc0a69c`。具体 PLT 解析见 JSON。

Arena 描述符 `+0x2ef2b88` 的三项为 8 MiB `mpMemoryHeap`、4 MiB `mpMemoryHeap2`、12 MiB `mpTextHeap`，合计 `0x1800000`。287 临时源码的 Backup bridge 确实提供 `0x2000000`（32 MiB）；这已满足静态容量条件。`calloc` 成功、Arena 实际注册和 UI worker 到达仍需运行证据。

## 最小下一步（候选建议，未实施）

只增加带 caller/module 归属的日志，不改 AppFw 字节、不改 thread 参数、不另起 UI worker：

- 在 `osal_create_waitable_thread` 观察 shim 中记录匹配 caller `appFw+0x222dcf4` 的 param 字段、真实函数来自哪个 DSO、返回值与 handle；参数复制/回调 trampoline 应保持原值。
- 观察与这条线程对应的 `prctl`、`sched_setscheduler` 失败返回和当时 errno，避免只在创建函数返回后读取已经被其他调用覆盖的 errno。
- 在原厂 callback 进入、`uxengine_init2` 进入/返回、第一条 Arena 日志、`ResourceManager::setDatabase` 进入/返回分别留下 marker。精确匹配 caller，避免全进程线程噪声。

判别结果：负 OSAL 返回 → 先修具体 OSAL/调度失败；OSAL成功但 callback无到达 → 检查原厂 trampoline 的 `+0x21be660`；到达 `uxengine_init2` 无返回 → 定位该初始化内部；Arena注册完成后才调查资源数据库与真实 FX6 presenter。顺序能避免再用手工线程/控件替换去掩盖前面的未完成初始化。

## 本次运行快照范围

读取现有 `cp-bind-810b960b/serial.log`（117,647 B、SHA-256 `9a07fc21e1d4beab71e79e4839c5b6d402156c03d540535c8fc4290bf884015c`），只出现 `FX6_APP_CONFIG_ENTRY` 和 `FX6_APP_CONFIG_HOLD real_returned` 两条相关 marker。未假定这份快照代表最新/最终运行结论。

## 可重跑工具

`inspect_native_init.py` 仅只读解析用户自备 appFw 与 CPIO 成员，将摘要和调用目标输出到 stdout，不导出固件字节。依赖 `pyelftools`、`capstone`。用 `--appfw`、`--cpio`、可选 `--source`、`--serial` 指定输入；`inspection-287.json` 为本次结果。CPIO reader 只搜索第一段 newc archive，遇到首个 `TRAILER!!!` 即停止；它不是完整串联容器验证器。全容器/后续同名覆盖检查由协调者的独立工具承担。

自编 shim 源码已只读复制至本目录 `libgrm-fbinit25-287.c`（相同 SHA-256），以免 `/tmp` 清理后失去当时输入。此源码不包含原厂固件二进制；仍需补齐构建命令及工具链回执。`AppConfig.so` 在真实入口中作为模式选择字符串使用；未将它对应路径不存在误判成缺库。

本轮没有证明原厂 FX6 屏幕、交互或实机兼容；以上为初始化链静态结果和下一轮可区分失败位置的观测建议。
