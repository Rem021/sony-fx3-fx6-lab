# FX6 混合前沿：CP/CAPID/GRM 已过，I-AppRemoteBoar 空指针异常

**结论：FX6 系统仍未成功开机。CP、CAPID、GRM 与 `I-AppRemoteBoar` 异常均已越过；当前硬停点变成 FX6 appFw 的 **用户态库闭包**：`liblibra.so` 需要 FX6 `libstella.so` 的 `_ZTIN6stella11ImageBufferE`，而 CPIO 仍是 FX3 版本。尚未取得 FX6 菜单。**

## 已越过的关卡

- CP helper：FX6 地址 `0xffffff8008322f70` 绑定，`FX3_SYNC100_BACKEND_BOUND`，`FX3_BACKUP_CP_INSMOD_RC=0`。
- FX6 appFw：`/usr/lib/appFw.so` 实际装载并执行。
- CAPID：`FX3_CAPID_AUDIO_PREINIT` + `FX3_HDMI_AUDIO_COMMIT command=0x32d completion=0x132d raw_status=0x580000`，原 `assert at ...:1075` 不再出现。
- GRM：真实 FX6 `libgrm.so`/`libma.so`/`libgrm_bmp.so` 已装载，`GRM_*` 未定义符号错误消失；FX6 `grm_ma.ko` 也测试过。

## 当前硬停点

- 串口：`[current task] program: im.elf(I-AppRemoteBoar) (pid: ..., cpu:3)`；`signal 7`，`DABT (lower EL) at 0x0`；随后 `Entering exception monitor` / `Exception>`，`im.elf` 进入 `T (stopped)`。
- 这不是 GRM 符号缺失，也不是 CP/CAPID 发送失败；是 FX6 appFw 的 AppRemoteBoard 线程对空函数指针/空对象的调用。
- FX3 基线内核＋同一 CPIO（`cp-bind-267c2c46`）与 FX6 内核（`cp-bind-0ac9bbad`/`cp-bind-c4848b38`）都复现，说明不是内核地址/CP 绑定问题。
- 未出现 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH` 或 FX6 菜单；FX3 AP 对照运行 `cp-bind-9d22099a` 的菜单属于 FX3 AP，不能当作 FX6 开机。

## 关键运行

| 运行 | 停止原因 | 关键结果 |
|---|---|---|
| `cp-bind-6e83a14a` | `ap_guard_observed_continue` | FX6 appFw 执行，旧 assert1075 |
| `cp-bind-3f90423f` | `ap_guard_observed_continue` | CAPID 预初始化通过，出现 `GRM_*` 未定义符号 |
| `cp-bind-0a652515` | `cp_helper_no_rc_40s`（解析误停） | GRM 窄桩，`I-AppRemoteBoar` 首次 DABT |
| `cp-bind-c4848b38` | `ap_guard_observed_continue` | 真实 libgrm/libma/libgrm_bmp，仍 DABT |
| `cp-bind-0ac9bbad` | `ap_guard_observed_continue` | 真实 libgrm + FX6 grm_ma，仍 DABT |
| `cp-bind-267c2c46` | `ap_guard_observed_continue` | FX3 基线内核＋同一 CPIO，仍 DABT |

序列哈希：
- `cp-bind-267c2c46/serial.log` `799012354d23e9588e51c6c30d5100bf5000b9dac7dc85de8c91c78281844323`
- `cp-bind-0ac9bbad/serial.log` `eb68fd9c43008420ec1beb561e1060719501eb8606a699071c019a7f4e1342bd`
- `cp-bind-c4848b38/serial.log` `2c9b5f9760140b70bc8fbb7016623578c295f06b4a5e257bdfa61f7401d01bfc`

## 关键 CPIO

- `guest-hybrid-fx6kernel-capid-grmreal3.cpio` `f7fd2c4f8d4e87d36015fba44cb4655a1764eb506c8b475c2c5bb9a92fefefcd`（FX3 grm_ma + 真实 libgrm/libma/libgrm_bmp + CAPID 预初始化）
- `guest-hybrid-fx6kernel-capid-grmreal4.cpio` `3d5191fca33d773c499515cc5f06d6c9e92a16cd3407bf4cee2d2826ed93f11f`（再替换 FX6 grm_ma.ko）

两者均 453,184,500 B，固定平台 QEMU/DTB/Backup 未变；其他成员逐字节保留。


## 2026-11-05 诊断串口尝试（尚未取得回栈）

- `runs/diag-5a0b8659`：QEMU 在启动前退出，`-chardev` 的 Unix socket 路径超过 104 字节；没有 guest 启动。
- `runs/diag-de8697fb`：改用 `/tmp` 短路径，QEMU exit 0、双锁 released，但 writable chardev 收到 0 字节串口，未捕获 `Exception>`，因此没有发送 `help/bt/regs`。
- 结论：当前 chardev 串口回读路径未打通；下一步改用直接 `-serial unix:...`/pty，或 QEMU GDB 读取故障 vCPU/内存；在拿到 PC/LR/回栈前不再重复同一 VM。

- `runs/diagstd-d8ca2c1d`：改用 `-serial stdio`，QEMU exit 0、双锁 released，但 stdout 串口仍为 0 字节，未捕获 `Exception>`；stdio 回读同样未打通。

## 下一步

下一关是 `libgrm.so` 的空对象：反汇编 `libgrm.so` 偏移 `0x2303c` 附近，确认被解引用的 GRM 全局/对象由哪个初始化调用建立；若是 FX3 VM 缺少的 GRM 服务，做只在 AppFw 线程生效的最小只读/安全桩，而不是继续逐库替换。UX 闭包与 FX3 `/init` 的共存已验证到 `AppFw` 线程。

## UX 闭包与 FrameBuffer::setSize 空 this

- 在 AppRemoteBoard、liblibra、libstella 之后，加入 FX6 媒体/UI peer 闭包：`libux_core`、`libtriones`、`libandromeda`、`libgemini(-grm)`、`libalcor`、`libtextrm`、`libwtle`、`libitype`，以及 `libuxengine`/`libux_wgtlay`；`cp-bind-2f0f312b` 首次到达 `im.elf(AppFw)`。
- 再替换 FX6 `grm_ma.ko` 的 `cp-bind-d33c1fe5` 仍在同一处崩溃；异常为 `im.elf(AppFw)` `SEGV PC=0x7fa9c4103c`、`DABT at 0x14`。
- 对 FX6 `libgrm.so` 的 `0x2303c` 反汇编：该地址是 `grm::FrameBuffer::setSize(unsigned short, unsigned short)`，首指令 `strh w1, [x0, #0x14]`；`DABT at 0x14` 说明 `x0 == 0`，即调用者传入空 `FrameBuffer*`。
- 因此不是 libgrm 指令错误，而是 AppFw 的 GRM 屏幕/FrameBuffer 对象未建立。`FX3_UI` 有 2181 条，但无 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH`/FX6 菜单。
- 关键 CPIO：`grmreal9` `802c0639d804e0d744d4853b06d479dc890397d670116a0a643a43bfa0435f59`；`grmreal10` `066425ae5fb2acb6beb59a9dc7cb6519c055f7eb4a8444a89bcd3d910fe61b5c`。
- 最新运行 `cp-bind-d33c1fe5` serial `b3418cfc74b95ec2c5bfc9fd60c1cf22ff2e3976d3f30a40cef21a6aeb9ff78e`。

## 空 this 的上游：FBResourceManager::initializeFrameBuffer

- 对 `libgrm.so` 继续反汇编：`setSize` 的调用点在 `0x22ab0`，属于
  `grm::FBResourceManager::initializeFrameBuffer(unsigned short, unsigned short, GRM_PixelFormat)`。
  该处先 `ldr x0, [x19, #0x8]` 再 `bl setSize`；`x19` 是 FBResourceManager，`[x19+8]` 即它的 framebuffer 字段，当前为 0。
- `GRM_screenGetOnBitmap`（`0x2368c`）走 `FBResourceManager::getInstance` → `getOnscreen`；与 framebuffer 未建立一致。
- 因此根因不是 AppFw 直接传空，而是 FX3 VM 上 FX6 `libgrm` 的 FBResourceManager/framebuffer 没有被 GPE/GRM 初始化建立；空 `setSize` 桩只会掩盖第一处访问。
- 下一步应检查 FX3 GPE 模拟 helper 与 FX6 `libgrm`/`grm_ma`/GPE 的 screen 创建路径，或做一个最小的 FrameBuffer 对象初始化；不再空桩 setter。

## 懒建 FrameBuffer 的结果：FBResourceManager::initialize 内 Abort

- 新增 `libgrm-fbinit.so`（`df8257f0c5237a1ae995eb89cce5ec95529a96e9a62aabc534e1a11f98d854e2`）：在 `FBResourceManager::getInstance` 里发现 `[manager+8]==0` 时调用真实 `FBResourceManager::initialize`。
- `cp-bind-45ece898` 串口出现 `FX6_GRM_FB_LAZY_INIT before manager=0x… fb=(nil)`，但没有 `after`；随后 AppFw 线程在 `FBResourceManager::initialize` 内部 `Abort (PC=0x7f7d7ef07c)`，`address=0x0`。
- 说明只创建 FrameBuffer 对象不够：`initialize` 还会创建 `FrameBuffer` 并调用 `FrameBuffer::initialize`/BMP/GPE 后端，在 FX3 VM 上该后端初始化失败并 abort。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal11.cpio` `b9158aeb70057ce9a72d5d740be23a0254b32ae605eff67db19e97b3e837d502`；运行 `cp-bind-45ece898` serial `18b092a894ddac0f401395288ecaf31a8fe3296bf5756d3b33f322ba75a36eaf`。
- 因此下一关不是“对象为空”，而是 FX6 `libgrm` 的 GRM/GPE/BMP 后端初始化；需要 FX6 图形服务适配或可验证的 emulation，不能再用空桩。

- 进一步映射：`Abort (PC=0x7f7d7ef07c)` 落在 `/lib/libc-2.25.so` 的 `raise` 内（offset `0x3107c`，`rt_sigprocmask` 后），是 `abort()`/`std::terminate()` 触发的 SIGABRT，不是非法内存访问。
- 因此真实 `FBResourceManager::initialize` 在创建 ResultWorker/ExternalOSDIF/FrameBuffer 或启动线程/OSAL/GPE/BMP 后端时主动 abort；`FX6_GRM_FB_LAZY_INIT after` 未出现。
- 下一步必须取得 abort 的调用者/栈（或绕开完整 initialize，只构造最小 FrameBuffer 并验证后续方法），不能再把它当作空对象问题。

## 最小 FrameBuffer 与 update 跳过：仍然 Abort

- `libgrm-fbinit2.so` 只调用真实 `FrameBuffer` 构造函数并写入 manager+0x8；`cp-bind-3cf8d722` 串口出现 `FX6_GRM_FB_MINIMAL before/after`，说明对象构造成功（vptr 有效）。
- `libgrm-fbinit3.so` 再加 `FrameBuffer::update` 空实现；`cp-bind-7bf93f4d` 出现 `FX6_GRM_FB_UPDATE_SKIP`，但随后仍 `Abort`。
- `libgrm-fbinit4.so` 再拦截 manager/FrameBuffer 的 `initialize`；`cp-bind-351f87d4` 的 `FX6_GRM_MANAGER_INIT_SKIP`/`FX6_GRM_FB_INIT_SKIP` 均为 0（这两个符号未被 AppFw 走 PLT 调用），随后仍 `Abort`（libc `raise`）。
- 当前 CPIO：`grmreal12` `048d7a97e459f08784ece0a4400619cb3b253da19d84a532690f42d213f54197`；`grmreal13` `29a44443f1fa4ea892e7249afb728ff2508282ec36d4005abac302fd55bace2f`；`grmreal14` `506ad36e58c9257fd529dfabbc0429e697131a72f3359a2c294b6dd8bc6f961c`。
- 最新运行 `cp-bind-351f87d4` serial `db58eafecbed9ade07c398929abe96d2b9ac22b2a593591d5fb0a22b3a831256`；`FX6_GRM_FB_UPDATE_SKIP` 后、`FX3_AP89_SCREEN_CREATE` 前仍 Abort，说明当前路径不只是 update。
- 下一步：定位这次 Abort 的直接调用者（很可能是 `FrameBuffer::getOnscreen`/`getOnscreenHandle` 解引用 +0x68 的空 BMP 指针，或其他 manager 方法），再决定是安全 getter 还是完整 GRM/GPE 后端；不再是空对象/update 问题。

## UXEngine 零尺寸 panic 与 640×480 回退

- abort 回栈 `f1=0x7f9937e6ac` 映射到 `libuxengine.so` offset `0x7b6ac`，即 `ux::gfxeng::Screen::setAreaInFramebuffer(short,short,unsigned short,unsigned short)`；当宽或高为 0 时调用 `ux::core::sys_panic()`（SIGABRT）。
- `libgrm-fbinit6.so` 在 AppFw 传 0 时替换为 640×480；`cp-bind-039c89e5` 串口记录 9 次 `FX6_UX_SCREEN_AREA … w=0 h=0`，随后在 guest 时间约 948s 出现
  `Internal error: : 0 [#1] PREEMPT SMP`，PC 在 `Backup_nread`/`backup_put_cp_wt_data`/`uipc_oom` 路径；没有菜单。
- 这说明盲目替换屏幕尺寸会把 UX/AppFw 带入一条 backup/UIPC 异常路径，不能作为有效适配。
- 最新 CPIO `guest-hybrid-fx6kernel-capid-grmreal16.cpio` `6a3bd8dbb4ab625fbb5a8c50c4d1e690640ed6bfeb44637966fc7062cece2240`；运行 `cp-bind-039c89e5` serial `11eb8be2e59bc0e6ac897c05f9abaacda32ea8a4e3ab62418be733ff87867a09`。
- 后续应回到 `grmreal14` 的安全 getter 路径，先解决 `setAreaInFramebuffer` 的真实 Screen 来源或 backup/UIPC 保护，而不是再改尺寸。

## 1024×540 回退同样触发内核错误

- `libgrm-fbinit8.so` 在 `FrameBuffer::setSize` 与 `Screen::setAreaInFramebuffer` 两处都提供 1024×540（AppFw 自己 setSize 的实值）；`cp-bind-…` 仍在约 31s 出现 `Internal error: : 0 [#1] PREEMPT SMP`，调用路径仍是 `Backup_nread`/`backup_put_cp_wt_data`/`uipc_oom`，无菜单。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal18.cpio` `c48f11cbd49264e55b7e1bd0416a5e2d71fb36a2374d8276ef7197916ccc985c`；serial `c63e19a0930122a311ca8357fc14745f0bb03f77253959f74a0457ee212f6b34`。
- 结论：无论 640×480 还是 1024×540，后期替换 UX Screen 尺寸都会把 AppFw 带入 kernel backup/UIPC 异常；这不是有效初始化路径。应回到 `grmreal14` 的安全 getter 路径，寻找真实 Screen 来源或先保护 backup/UIPC 请求。

## 零尺寸 Screen 跳过仍触发同一 kernel backup/UIPC 错误

- `libgrm-fbinit9.so` 在 `Screen::setAreaInFramebuffer` 遇到 0 尺寸时直接返回（不替换成任何尺寸）；`cp-bind-2de20ca9`/最新零尺寸运行仍在约 31s 出现 `Internal error: : 0 [#1] PREEMPT SMP`，调用路径仍是 `Backup_nread`/`backup_put_cp_wt_data`/`uipc_oom`。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal19.cpio` `2a0a54a76a85c3f73c0a87c4d731c04a2a4cc7b25c8ad11bc5929fa8dc67f3fe`；serial `86e4d2be20ca5fbe394773ef208150e2461e299ddd5192a49c086480fa844d54`。
- 这说明 kernel backup/UIPC `Internal error` 与 UX 屏幕尺寸替换无直接关系，是 AppFw 到达 backup 路径后的独立问题；继续改 Screen 尺寸不会解决。

## 1024×540 UX + backup BUG 跳过：不再崩溃，但 AppFw 停等

- `guest-hybrid-fx6kernel-capid-grmreal21.cpio` 在 `grmreal20` 的 backup BUG 跳过基础上，把 UX Screen 0 尺寸替换为 1024×540；`cp-bind-9e6527aa` 不再出现 kernel `Internal error`/user `Abort`/`Exception Syndrome`。
- 串口仍有 `FX6_UX_SCREEN_AREA_1024` 9 次、`FX3_UI` 3224 条；AppFw PID 375 保持 `S (sleeping)`，UIPC 在 `0x807e0030` 队列等待；但没有 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH`，仍无 FX6 菜单。
- CPIO `238ff1b7a7f2afd2231b4994e28e5b29d037bc5fa2fc7fc17c76a63640f73e6d`；serial `a6ab2d46059e1b522477b14e87705059675a072c91110070fd9004274260ebc2`。
- 这说明“backup BUG 跳过 + 1024 UX 面积”可以让 AppFw 存活，但下一步是 AppFw 在等哪个服务/事件，而不是继续改尺寸或补丁。

## AppFw 最终等待：共享内存 futex

- `cp-bind-9e6527aa` 的 `FX3_TASK_SNAPSHOT_375` 显示 AppFw 内核栈：
  `futex_wait_queue_me` → `futex_wait` → `do_futex` → `SyS_futex`。
- `/proc/375/syscall` 行给出 futex 地址 `0x7f3c41e2f0`、op 0（FUTEX_WAIT）、val `0x80000000`。
- 该地址位于匿名映射 `0x7f3c000000-0x7f3c4e9000`（约 5.1MB，rw-p），不是 UIPC 0x807e0030；说明 AppFw 已越过 UIPC 收包，最终在共享内存的 UX/AppFw futex 上等待，没有 screen/media/menu 标记。
- 因此当前不是 UIPC provider 缺失，而是共享内存事件/锁未由 UX/GRM/GPE 侧触发；下一步应检查该匿名映射的创建者、futex owner 和 `uxengine_res1` 等线程，而不是继续改 Screen/UIPC。

## UX worker 与 AppFw 同映射 futex 等待

- `FX3_TASK_SNAPSHOT_375`（AppFw）等待 futex `0x7f3c41e2f0`；`FX3_TASK_SNAPSHOT_376`（`uxengine_res1`）等待 futex `0x7f3c410e48`；两者都在匿名映射 `0x7f3c000000-0x7f3c4e9000`，且 `uxengine_res1` 只有 1 次 voluntary context switch。
- 说明 UX worker 线程存在但空闲等待，AppFw 在同一个 UX 共享映射的另一个 futex 上等待；不是 UIPC provider 缺失，而是 UXEngine 的 job/condition 没有由初始化侧提交/触发。
- 这与前面的 `Screen::setAreaInFramebuffer` 0 尺寸、`FBResourceManager` 未完整 initialize 的结论一致：fake FrameBuffer/Screen 让 AppFw 存活，但 UXEngine 资源/任务链没有真正建立。
- 最新运行 `cp-bind-9e6527aa`；CPIO `238ff1b7a7f2afd2231b4994e28e5b29d037bc5fa2fc7fc17c76a63640f73e6d`；serial `a6ab2d46059e1b522477b14e87705059675a072c91110070fd9004274260ebc2`。
- 下一步应由真实 `UXEngine::initialize`/Screen/framebuffer 后端建立 UX job 与 worker 唤醒，而不是继续 fake 尺寸或 stub。

## UX futex 等待者清单（3 个快照稳定复现）

- `FUTEX-WAITERS.json` 从 `cp-bind-9e6527aa` 的 3 次任务快照提取同一匿名映射 `0x7f3c000000-0x7f3c4e9000` 的等待者：9 条记录、3 个唯一线程。
- 唯一等待者：
  - `AppFw` TID 375：`0x7f3c41e2f0`
  - `uxengine_res1` TID 376：`0x7f3c410e48`
  - `uxengine_res2` TID 377：`0x7f3c410f98`
- 三次快照中三者的 futex 地址完全不变、均为 `S (sleeping)`；没有同映射内的运行 owner。说明 AppFw 等 worker 结果、两个 UX worker 等 job 队列，但没有生产者/初始化把 job 推入。
- 这进一步支持：fake FrameBuffer/Screen 虽让 AppFw 存活，但 UXEngine 的 job 生产者没有建立；下一步应恢复/调用真实 UXEngine 初始化或显式提交最小 screen job，而不是继续改尺寸。

## pthread 诊断：MWF cond 等待，换 FX6 libMWF 仍无 screen

- `libpthread-diag.so` 日志显示 UX 映射内的 cond wait 调用者 `0x7f78542778` 落在 `/usr/lib/libMWF.so`；`0x7f3c...` 的 cond/mutex 对多来自 MWF 工作线程。
- 但把 `usr/lib/libMWF.so` 换成 FX6 版本（`3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782`）后，`cp-bind-5f0aebb8` 仍无 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH`、无 Abort/Exception；FX3_UI 2988 条，AppFw 仍等待。
- 因此 MWF 的 cond 等待更像正常 worker 空闲，不是根因；根因仍是 UXEngine job/初始化没有建立。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal23.cpio` `90929b9fcbc41b1ea345b7da5c1047cc5395d8d0d172950482eab720c72dca85`；运行 serial `087919f4df939cc4f8e4a0bcf38e4f44e283f506b07ecdcf1209141ab5c43b59`。
- 下一步回到 UXEngine 初始化/job 生产者，不再替换 MWF。

## QMP screendump 不可用：fixed QEMU 无图形控制台

- 用当前最佳 `grmreal21` 运行 QMP `screendump`，QEMU 返回：
  `GenericError: There is no console to take a screendump from`。
- 固定命令使用 `-display none`，FX6 appFw 的 GRM/UX framebuffer 不是 QEMU 图形控制台，因此不能靠 QMP 截图验证菜单。
- 后续若需画面证据，只能走 guest 侧 framebuffer/OSD helper 的文件导出，或串口/内部 screen 标记；不能把 QMP screendump 当验收手段。
- 该诊断运行在 QMP 错误后由收尾逻辑退出；无 screen 文件。

## UXEngine::initialize 路径与缺失的 draw/job

- `libuxengine.so` 的 `UXEngine::initialize`（0x74d70）依次调用：
  `ux::core::Kernel::sys_initialize` → `ux::resmgr::ResourceManager::sys_initialize` → `ux::gfxeng::GraphicsEngine::sys_initialize` → `AnimationEngine::sys_initialize` → `WidgetSystem::sys_initialize` → `stella::Mutex::initialize`。
- 它本身不提交 screen job；实际绘制在独立的 `beginDrawOnMultiTsk`/`execDrawOnMultiTsk`（0x74fb4/0x75024），后者才调用 `ResourceManager::processCommands`、`WidgetSystem::notifyDraw`、`GraphicsEngine::drawFramebuffer`。
- 当前 AppFw/`uxengine_res1/2` 都停等，说明初始化后半段的 draw/job 触发没有发生；不是 MWF 或尺寸问题。
- 下一步：确认 `UXEngine::initialize` 是否返回成功、`ResourceManager::sys_initialize`/`WidgetSystem::sys_initialize` 的 worker event 是否建立，以及 AppFw 为何没有进入 `execDrawOnMultiTsk`。不再改尺寸/库替换。

## UXEngine 公共 API 探针未命中：实际调用在 MWF/内部路径

- `libuxdiag.so` 拦截 `UXEngine::initialize`、`ResourceManager/GraphicsEngine/WidgetSystem::sys_initialize`、`beginDrawOnMultiTsk`、`execDrawOnMultiTsk`、`sys_invokeWorkerEvent`；`cp-bind-f3c450fb` 串口这 11 类探针全部为 0。
- 说明 AppFw 没有通过可被 LD_PRELOAD 拦截的公共 PLT 调用这些 UXEngine API；`uxengine_res1/2` 线程和 MWF cond 等待是 MWF/内部路径创建和使用的，MWF 才是实际调用者/owner。
- 因此继续对 `UXEngine` 公共符号加探针无效；下一步应检查 `libMWF` 的 worker/job 或 AppFw 内部直接调用，而不是 UXEngine API。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal24.cpio` `76be520123a22427799ed5430823b1165e11592e71250dde1aaff34a36ec106c`；运行 serial `4023888436cb49583eb882abfd892195637f3eaf4f992c7349f7eaa6a1d09094`。
- 本轮仍无 screen/media/menu；AppFw 与 UX worker 继续等待。

## AppFw futex 的 syscall PC/SP

- `cp-bind-28762ee1` 的 `/proc/375/syscall` 保存 `PC=0x7f7f4bb504`、`SP=0x7f4a7fc6d0`。
- PC 位于 `/lib/libc-2.25.so` 代码段（futex 系统调用包装），SP 位于匿名 8MB 线程栈 `0x7f4a001000-0x7f4a800000`。
- 因此内核栈只显示 `futex_wait`，用户态调用者不在内核栈里；要定位 AppFw 具体等待对象，需要读取 `/proc/375/mem` 在 SP 附近的用户栈或使用能切换进程页表的 GDB 读取。
- 现有证据已足够排除“UIPC provider 缺失/MWF 库版本/屏幕尺寸”作为唯一原因；下一步应做用户栈/共享内存对象读取。

## AppFw 用户栈：实际等待是 osal_snd_sync_msg（不是 UX job）

- 通过 `read-ux-stack3` 在 `cp-bind-6c6911a1` 抓到 AppFw 用户栈（`sp=0x7f517fc6a0`、`pc=0x7f7e4d4658`）。
- 栈中的 appFw 返回地址集中在 `Application_System_Init`：
  `0x13a748c`、`0x13a7700`、`0x13a81e4`、`0x13abb50`、`0x1adc9ec`、`0x1bd74a8`、`0x215ccf0` 等；另有 `libosal_uipc.so+0x3c14`。
- 内核栈对应 `__osal_snd_sync_msg+0x17c` / `osal_snd_sync_msg+0x14`；`Application_System_Init` 在 `0x13a7484` 载入 `w0=0x41e` 后调用 `0x1acbdf8`，随后等待同步回复。
- 串口 `FX3_UIPC_SYNC_RETURN target=0x80924127` 多次出现 `errno=1020/1024/2/19`；说明 AppFw 卡在向 `0x80924127` 的同步 UIPC 请求/应答，而不是 UX/MWF 的 job 队列。
- 新 helper/CPIO：`read-ux-stack3` `6e7e0b91550e05214f2b06328d10b890a29b0188ae3334a94cd82fa272c315c3`；`guest-hybrid-fx6kernel-capid-grmreal27.cpio` `e727804ed43bc13b1f9d466abbeb3722ca7df13f8625eb77ea4cf4c55185476a`。
- 对应用例 `cp-bind-6c6911a1` serial `c25980ad2755214b7e318c225f3ad706f7cadfdd040c6c62d74ce56aa141ebc9`。
- 下一步应解析 target `0x80924127`、消息 `0x41e` 的提供者/应答合同；不是继续查 UXEngine/MWF。

## FX6 upm.ko 在 FX3 内核上缺 backup 符号

- 把 `usr/kmod/upm.ko` 换成 FX6 版本（`34d5bca76b6750f2af36f34404c305aaef71aeabab1d3ae52a9e00b65c6b7970`，414720 B）后，`cp-bind-44d2562d` 在 `insmod` 处失败：
  `upm: Unknown symbol Backup_sync_subsystem_for_senser_local (err 0)`，`FX3_UPM_RC=2`；init 进入等待循环，AP guard 不出现。
- 说明 FX6 upm.ko 需要 FX6 backup 的 `Backup_sync_subsystem_for_senser_local` 符号；当前 FX3 backup/CP helper 不导出该符号，不能直接替换。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal28.cpio` `f00e4bcf88365f0d16918db25f21c6239f6143a121d49b9f01981ee5b9651acd`；serial `8c5eddccd769bb98b5462b05b8722c504e3cc0ecfd93ad4501e0e54d56276d61`（89827 B）。
- 下一步：给 CP helper/backup 增加该符号的最小 stub/alias，或确认 FX3 backup 是否有可重命名的等价符号；否则不要再用 FX6 upm.ko。
- 当前最佳仍是 grmreal21；本轮无 screen/menu。

## upm 符号重命名可加载，但 AppFw 仍等待

- 将 FX6 `upm.ko` 的未定义符号 `Backup_sync_subsystem_for_senser_local` 原位重命名为 FX3 backup 导出的 `Backup_sync_subsystem`（`upm-renamed.ko` `87e36f1205ff348995334a5283468100ab46d632c320143b4652c7087e9be6fb`），`cp-bind-15463863` 的 `FX3_UPM_RC=0`、不再报 unknown symbol，AP guard 也出现。
- 但 AppFw 仍为 `S (sleeping)`、仍停在 futex（`PC` 在 libc），无 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH`，FX3_UI 2988 条；说明仅做符号别名只解决加载，不满足 UPM 的 sensor-local 语义。
- 新 CPIO `guest-hybrid-fx6kernel-capid-grmreal29.cpio` `8ef0a7803ce336400cbeab455c1ba584c73712349434814814dbd546bc2e69da`；serial `375233b8dbc1fbc11273cbb768194cb26bdaab79e1b3ec82417fc5ae0ef136be`。
- 下一步：实现真正的 `Backup_sync_subsystem_for_senser_local` stub/语义，或给 target `0x80924127` 的 UPM 请求提供应答；简单重命名不够。

## upm 零返回补丁：AppFw 阻塞点前移

- 修正后的 `upm-nocall.ko`（`27cc11e5b5d72e40888edc8f10d758dce72d054ab69c0b35d66ce872c5522517`）删除 `.text+0x1174c` 的 sensor-local 调用重定位并改成 `mov w0,#0`；`cp-bind-8d1af3cf` 的 `FX3_UPM_RC=0`、AP guard 出现。
- 但 AppFw 仍无 screen/media/menu；用 `grmreal32` 再抓用户栈，等待点已从旧的 `Application_System_Init` UPM 同步帧（`0x13a748c` 等）前移到新函数：
  `0x1b18c74`（返回 `0x1bdf530`），内部使用 `0x2167df8`/`0x2167e54` 的 mutex/cond 辅助和 `0x14fe668`，更像等待 worker/event，而不是 UPM sync。
- 新 CPIO：`grmreal31` `634591019fa521242bf30d83ddbd711288274595bf347e8c2247ffeadf169cba`；`grmreal32`（含栈 helper）`095df34788796d411773cb9a1929f97575b08ce1955a87e8d4a251f3b45100b9`。
- 对应用例：`cp-bind-8d1af3cf` serial `a965b560b204992d1dea7bafac1a63d994efe0eb3dbe86c8b782c39209840655`；`cp-bind-8f28f056` serial `e263efc9af22d0b38ede6b6c8b15d1a4f32e9f91adcbcde9ec157d2851a394ec`。
- 结论：UPM 模块的 sensor-local 调用曾是一个阻塞点，但不是唯一；现在应追 `0x1b18c74` 等待的 worker/condition 及其 signaller。
- 当前仍无 FX6 菜单。

## upm 补丁后新阻塞点：backup 读写

- 反汇编 `0x1b18c74`（upm 补丁后 AppFw 的等待函数）发现它调用：
  - `0x2167df8`：`Backup_nread` 包装，key `0x2cf1841`、size 4；
  - `0x2167e54`：`Backup_write` 包装，key `0x2cf1842`、size 4；
  - `0x14fe668`：返回一个全局对象 getter。
- 这两个包装都通过 `Backup_nread@plt`/`Backup_write@plt` 进入用户态 backup 库/垫片；随后 AppFw 仍在 futex 等待。
- 因此 UPM 的 sensor-local 调用只是第一个阻塞点；现在 AppFw 已推进到 **backup 读写**，等待点在用户态 backup 路径，而不是 UPM/UXEngine。
- 下一步：检查 `Backup_nread`/`Backup_write` 的实现（`libBackupManager`/`fx3-backup-return-v1`/CP helper）为何阻塞，特别是 key `0x2cf1841/0x2cf1842` 的读/写响应。
- 对应 CPIO `grmreal31/32`；运行 `cp-bind-8f28f056` serial `e263efc9af22d0b38ede6b6c8b15d1a4f32e9f91adcbcde9ec157d2851a394ec`。

## Backup_nread stub 命中 AppFw 键，但仍未出 screen

- 广谱 `Backup_nread`/`Backup_write` stub 被大量调用（nread 219、write 5417），但 `Backup_write` 的部分调用点使用 `(service,key,data)` 签名，被误读成 `(key,buf,size)`，出现负 size；广谱 interpose 不安全。
- 改为只拦截 `Backup_nread`，并对 AppFw 的键 `0x2cf1841`/`0x2cf1842` 返回 0/1；`cp-bind-86fc6dc1` 确认命中这两个键（size 4），但 AppFw 仍 `S (sleeping)`，无 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH`，FX3_UI 3007 条。
- 说明仅仅合成 0/1 不能解除 `0x1b18c74` 的等待；该函数可能还需要真实 backup 值/worker condition，或等待点不在 nread 返回值。
- CPIO：`grmreal33` `01c33e5d5bad9a04e3d372bd8621d688879a12a3273c7cc8f8bbaa4d4ccdbc8c`；`grmreal34` `b64ad4f75ba9fb52389531df79a1985aad6ac828c7096b2eb85a281ebb171471`。
- 运行：`cp-bind-bb36086d` serial `72733d0eec59e16d27d991cc6fa22906270373485bcdf2418bfc552879b7342a`；`cp-bind-86fc6dc1` serial `c8ea3bd7457d348ca05836aae0fcd171780b69be24d9cc609cc68f2348b582d8`。
- 下一步：不要广谱 interpose；检查 `0x2cf1841/42` 的原生/真实值或 `0x1b18c74` 的 worker condition，再决定最小 stub。

## 0x1b18c74 的真正阻塞原语：std::condition_variable::wait

- `0x1b18c74` 在 `0x1b18d10` 调用 `0x1acd618`；后者在 `0x1acd6bc` 调用
  `_ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE@plt`。
- 同一函数 `0x1acd2f4` 在 `0x1acd3b8` 调用 `_ZNSt18condition_variable10notify_oneEv@plt`。
- 因此 AppFw 当前不是卡在 `Backup_nread` 的返回值，而是卡在一个 C++ condition_variable；`0x2cf1841/42` 的 nread 只是该函数内的前置检查，0/1 stub 无法满足。
- 下一步：找 `0x1acd2f4` 的调用者/notify 线程（或该 condition_variable 对应的 worker）为什么没有运行；不再对 backup 返回值做广谱猜测。
- 当前最佳仍是 `grmreal31/32`；无 screen/menu。

## CVDIAG：两个未配对的 condition_variable

- `libcvdiag.so` 记录 `std::condition_variable::wait/notify_one` 的 `this`/caller；`cp-bind-249f6e0a` 共 120 次 wait、88 次 notify_one、4 次 notify_all。
- caller 映射到 AppFw `0x1acd6c0`（wait 包装）的三组共享 CV：
  - `0x7f6441cec0`：29 waits / 29 notifies，平衡。
  - `0x7f94000a80`：29 waits / 28 notifies；最后一次 wait 在 serial 行 12090，最后一次 notify 在 12087，之后无 notify → **卡住**。
  - `0x7f6003bae0`：2 waits / 1 notify；唯一 notify 在行 11589（caller `0x1acd97c`），最后一次 wait 在行 12102 → **卡住**。
- 另有大量 `0x7efacd...` 单次 wait、0 notify 的 worker CV（caller `0x1e2520c`/`0x20c4560`），更像正常一次性 worker 等待。
- 结论：AppFw 当前至少有一个共享 CV 在最后一次 notify 之后继续 wait；下一步要定位 `0x7f94000a80`/`0x7f6003bae0` 的生产者/回调为何少通知一次。
- CPIO `grmreal35` `77ddab7611d0b4153db67d3f31bd841cd0576a2bb16011fae77d8d9b09dc851d`；serial `9eb606114d982e6c628ef0b4ddc5dfe6556a110d3de56e423dd44455f804a5a1`。

## CV caller1：未配对 CV 属 worker，AppFw 主线程不在其中

- `libcvdiag2.so` 记录 wait/notify 的 caller1；`cp-bind-cab3fbcb` 中未配对 CV：
  - `0x7f84000a80`：76 waits / 75 notifies；最后 wait 行 12216（caller1 `0xd398b0`），最后 notify 行 12212（caller1 `0xde3180`）。
  - `0x7f641fd1b0`：2 waits / 1 notify；最后 wait 行 12230（caller1 `0xc56ff0`），唯一 notify 行 11513（caller1 `0x12d9dec`）。
- 这些 caller1 偏移都不是 AppFw 主等待路径 `0x1b18d14`/`0x1b18e58`，更像 worker 线程的 condition；AppFw 主线程的 `0x1b18c74` 不在未配对 CV 的 caller1 列表中。
- 因此主线程更可能在 `0x1adc90c` → `0x20e46cc` 的 once/guard/retry 路径上等待（含 `usleep`/mutex），而不是这些 worker CV。
- 下一步：拆 `0x20e46cc` 或拦截 `pthread_once`/`std::call_once`/pthread mutex，定位主线程真正等待的 guard/owner；不要继续追 worker CV。
- CPIO `grmreal36` `6eaf98eabb6911ebe390b1f30b66038fca940b339de8729273c74850a83f979d`；serial `a1ffa69065d6ea8eec3b20341f499dba486548cbd5244ef428dcf1d37f22676f`。

## AppFw 主线程不在 CV wait：转查 logging mutex

- `cp-bind-cab3fbcb` 中 AppFw 映射基址 `0x7eeb33f000`；理论上主等待 caller1 应为 `0x1b18d14`，但 120 条 CV wait 中没有该 caller1（也没有 `0x1b18e58`）。
- 因此 AppFw 主线程不在 `std::condition_variable::wait`，之前抓到的未配对 CV 都是 worker；主线程的 futex 是别的 mutex/guard。
- `0x1adc90c` 调用的 `0x20e46cc` 不是 once：它把 `w0=27` 传给 `0x21bdf44`，再调用 `0x215cf34`（内部有 `snprintf@plt`），更像 **log/format** 辅助；主线程可能卡在 logging mutex 或另一个 guard。
- 下一步：拦截 `pthread_mutex_lock`/`pthread_once`/`__cxa_guard_acquire`，记录主线程 caller1 与 mutex 地址；重点看 logging/`snprintf` 路径，而不是 worker CV。
- 当前仍无 screen/menu。

## AppFw 主 futex 不是 mutex/once/guard，更像 pthread_join

- `libmutexdiag.so` 记录 168 次 contended mutex、49 次 pthread_once、22 次 __cxa_guard。
- AppFw 的 `/proc` syscall futex 地址 `0x7f5843adb0` 在这些日志中 **0 次命中**；因此主线程不是等 pthread mutex/once/guard。
- 该 futex 的 `FUTEX_WAIT` val 为 `0x80000000`，更符合 glibc 线程 join/退出状态字；AppFw 还导入 `_ZNSt6thread4joinEv` 与 `osal_wait_thread_exit`。
- 结合 `uxengine_res1/2` 一直空闲在 worker CV，主线程很可能在 join 一个永不退出的 worker：worker 等 job、主线程等 worker 退出，形成死锁。
- 下一步：拦截 `pthread_join`/`_ZNSt6thread4joinEv`，记录目标 TID 与 caller1；确认被 join 的 worker，再决定补 job/退出条件。
- CPIO `grmreal37` `e03087540226b92db8a57c8be67fed1e1a1371881c46c332091e0ed5db29ab47`；serial `765285826294421489f5a36822aa9080100c7c7cf481efdcf55906a3029636ae`。

## join 诊断未命中主 futex

- `libjoindiag.so` 运行 `cp-bind-c1267a16`：仅 5 次 `pthread_join`、0 次 `std::thread::join`。
- join 目标为 `0x7f597ff050`/`0x7f58fe4050` 等，caller1 为 `0x7f6c0156e8` 或 `0x4026c0` 等；均不与 AppFw 主 futex `0x7f5843adb0` 对应。
- 因此“主线程 join worker”假设未获证据支持；主 futex 更像 semaphore/osal 等待（val `0x80000000`）。
- 下一步：拦截 `sem_wait`/`osal_wai_sem_tmo`/`pthread_cond_wait`，记录主线程 `m`/caller1；不要再只查 join。
- CPIO `grmreal38` `d96ba705846f6f29583649d820985d0155fc7843d0775cff18ee9bf166727699`；serial `d6970eddc1d99f2ec5606c0f51c84a502a2a94c886db1917ba0fb801b2f3a4b7`。
- 仍无 screen/menu。

## osal_wai_sem_tmo 签名与主栈排除

- `osal_wai_sem_tmo` 在 `libosal_uipc.so+0x4858`，签名为 `(sem_id, timeout)`：先 `check_dynamic_sem_id`/`get_bsem`/`osal_lock`，再 `do_sleep_tmo`；没有直接 `sem_wait`。
- AppFw 主线程用户栈此前只映射到 appFw/libc，没有 `libosal_uipc` 帧；因此主 futex 很可能不是 `osal_wai_sem_tmo`，而是 AppFw/stella 自定义 mutex 或 logging lock。
- 下一步：拦截 `stella::Mutex::lock`/`unlock` 或 `ux::core` 自定义等待原语；`osal_wai_sem_tmo` 只作为次要候选。
- 当前仍无 screen/menu；最佳仍是 `grmreal21` 系列。

## 主线程真正阻塞：std::future 等待异步任务

- `libatomicdiag.so` 命中唯一一次主 futex：
  `self=futex=0x7f4443ab80 val=0x80000000 c0=0x7eda61e104 c1=0x7edaa0abd8`。
- 映射：c0 = appFw `0x1d6d104`，c1 = appFw `0x2159bd8`。
- `0x1d6d0a8` 的代码是 future 状态字的 `_M_futex_wait_until`：读 `[state]`，若 `state&0x7fffffff != 1` 就置 `0x80000000` 并等待；`0x2159bb0` 随后检查 `exception_ptr` 并可能 `rethrow_exception`，是 `std::future::get` 形态。
- 因此 AppFw 主线程不是等 mutex/CV/join/osal，而是在等一个 **std::future 的异步任务**；该任务的 shared state 未 ready，producer 没有 set_value/return。
- 下一步：找 `0x2159bb0` 的调用者/创建 future 的代码，确认异步任务及其线程为何不完成（很可能又是未启动/未完成的 UX/媒体 worker）。
- CPIO `grmreal40` `1b09a169fd0727f3e2840ceb97917094e600223401b8d3933e3a40e824a9f6fe`；serial `ab5d18527b0aa0d5bcb718542c6845370d67f35ce40d546c12ba929df0c1f463`。

## future 来源：logging wrapper 的异步任务

- `0x2159c50`（future::get helper）只有唯一调用者 `0x20eca84`，位于 `0x20eca5c` 的 logging wrapper。
- 该 wrapper 先 `w0=0x40/w1=4` 调 `0x21bdf44`，再 `0x2159c50` 取 future，最后 `0x21be004`；同一簇函数（`0x20eca0c/0x20eca34/0x20eca5c`）都带 `0x21bdf44`/`0x21be004` 日志对。
- 因此主线程等的 `std::future` 很可能是一个**异步 logging 任务**；logger 的 future 未 ready，导致 `Application_System_Init` 卡住。
- 下一步：检查 logging wrapper 的 future producer/线程（异步日志队列 worker）为何不完成；这是比 UX/backup 更靠前的阻塞。
- 仍无 screen/menu；CPIO `grmreal40` `1b09a169fd0727f3e2840ceb97917094e600223401b8d3933e3a40e824a9f6fe`。

## appFw future 跳过：推进到 MEDIA_START，但 upm 传感器 Oops

- `appFw-future-skip.so` 把 `0x2159c50`（future::get helper）改成 `mov w0,#0; ret`，跳过异步 logging future 的等待。
- `cp-bind-d520ae61` 首次出现 `FX3_MEDIA_START_BRANCH eid=20 ...`，说明 logging future 确实是阻塞点，绕过它后 AppFw 进入 media start。
- 但 34s 时内核 Oops：
  `Unable to handle kernel paging request at virtual address ffffff8a00905856`
  `Internal error: Oops: 96000005 [#1] PREEMPT SMP`
  `pc : upm_senser_dfs_measurement+0x4a4/0x738 [upm]`
  `PID 214 Comm: UPM_TSK_FRAMEWO`
- 新阻塞点是 FX3 `upm.ko` 的 `upm_senser_dfs_measurement`（sensor/DFS 测量）空指针/无效地址；不是之前的 UX/future。
- 新 CPIO `grmreal41` `c1f154730c5d463b293ba3bb840a44eb66e101dda65d42d9e0a7207b512c634a`；serial `f1b3284217efd8e0baf85f0d347d80db35add4e44b602a44051b93a1d5af76da`。
- 下一步：跳过/补丁 `upm_senser_dfs_measurement`，或给 FX6 upm.ko 补 `Backup_sync_subsystem_for_senser_local` 真实语义；保留 appFw future skip 作为推进手段。

## upm DFS 入口跳过未消除 Oops

- 按 `FX3_UPM_TEXT_BASE=0xffffff80008cc000` 与 LR `0xffffff80008df6bc` 计算：`LR-base-0x4a4 = 0x13218`，即 `upm_senser_dfs_measurement` 入口。
- `upm-dfs-skip.ko` 在 VMA `0x13218` 改为 `mov w0,#0; ret`（`8858489ef6053c587e61cf519d2eb020e961a99f9692fb30cfa420bfa5fc4390`）；`objdump` 已确认符号/入口。
- `grmreal44`（grmreal41 + DFS-skip）运行 `cp-bind-e50e3a30` 仍出现 `Internal error: Oops`/`LR is at upm_senser_dfs_measurement+0x4a4`，仍有 `FX3_MEDIA_START_BRANCH`，无菜单。
- 说明 Oops 不是简单从该入口进入，或 LR 只是 caller、真正 PC 在别处；需要干净的 PC/call trace 再定位。
- CPIO `grmreal44` `90270cb4ad3394600f1f5f87f96f2c2f847f76280c017009cf6934acfa2846c6`；serial `ef0bee056c7341295a96e9c94fe32066fb6f7f9f8ac4651e06ce635aeecbc065`。
- 下一步：从 Oops 干净取 PC/栈，确认 crash 函数；或换 FX6 upm.ko + symbol 语义；保留 appFw future skip。

## 首次 180s 无 Oops：upm DFS call-site skip 成功

- `upm-callsite-skip.ko` 把 `upm_senser_dfs_measurement+0x4a0` 的 `blr x2` 改成 `mov w0,#0`，跳过 fault callee；`grmreal46` 由 grmreal41（appFw future skip）+ 此 upm 组成。
- 60s `cp-bind-9989d071`：无 Oops/Internal error，`FX3_MEDIA_START_BRANCH` 出现，AppFw 稳定。
- 180s `cp-bind-66ed0f78`：仍 `fault_markers=[]`，serial 5,508,980 B；`FX3_MEDIA_START_BRANCH` 2 次、`FX3_UI` 3265、`FX3_GPE` 170；AppFw 一直 `S`。
- 仍无 `FX3_AP89_SCREEN_CREATE`/FX3 OSD；该标记是 FX3 AP 专用，不能直接证明 FX6 无菜单，但也没有 FX6 菜单证据。
- 这是目前最稳候选：`grmreal46` `3a08f89d89cfc6db8b12158a0a1147410e42d98713c445c3c38c07eefad8d03b`；180s serial `377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e`。
- 下一步：guest 侧 framebuffer/UI 证据或按键/事件检查，确认 FX6 是已显示菜单还是停在某个 UI/UIPC 等待；不再优先打 kernel 补丁。

## 180s 稳定但 AppFw 主线程仍 futex

- `cp-bind-66ed0f78` 180s 无 Oops，但任务快照：
  - AppFw TID 375：`futex_wait`，syscall 参数 `futex=0x7f40033528`，仍 `S`。
  - `uxengine_res1/2`：仍 `futex_wait`。
  - `im.elf` 主线程、`IWrapperUPM`：`osal_rcv_msg_tmo`。
- 因此“无 Oops + media start”是稳定里程碑，但不能证明已进入 UI 事件循环；没有 screen/menu 证据。
- 下一步：在 `grmreal46` 上重跑 atomic/future 诊断，定位主线程 `0x7f40033528` 的等待对象/调用者；再决定 GUI 证明或最后服务。

## grmreal46 + atomicdiag：0 命中，主 futex 已换类型

- `grmreal47`（grmreal46 + `libatomicdiag.so`）运行 `cp-bind-61c20eab`：`ATOMICDIAG_WAIT` 0 次。
- AppFw 主 futex 为 `0x7f68033948`，不再是 libstdc++ atomic futex；future skip 已把原先的 future/atomic 等待绕开，现在主线程等的是另一类 futex（mutex/cond/osal/uipc）。
- 180s `grmreal46` 的 `fault_markers=[]`、MEDIA_START 仍是当前最稳里程碑；但没有 screen/menu 证据。
- 下一步：对 `grmreal46` 的主 futex 逐一排除 mutex/cond/osal/uipc，或转 guest 侧 framebuffer/UI 证据。

## 180s 稳定但仍有 unhandled CP/media 消息

- `cp-bind-66ed0f78`（180s）虽无 Oops、media start，但串口仍有大量：
  `FX3_BACKUP_CP_UNHANDLED destination=0x92a208fc/0x9092083f/0x928708f7 ...`
  以及 `FX3_BACKUP_CP_UNHANDLED_SOURCE ... no_reply=1 no_free=1 terminal_unproven=1`。
- 这些未处理的 CP/媒体目标可能是 AppFw 主线程继续 futex 等待的原因；当前“稳定”不等于所有服务已就绪。
- 下一步：处理这些 CP destination 的最小 provider/reply，或先抓 guest 侧 framebuffer/UI 证明；两条都可推进。

## DMM 物理抓取尝试：首段全零、80MB QMP 超时

- QMP/HMP `pmemsave` 用相对文件名可写文件；`0x480000000` 的 2MB 段成功抓取但**全零**。
- 尝试 `0x480200000` 80MB 时 QMP 超时/closed，后续段 broken pipe；该运行 serial 也为 0，不能据此判断画面。
- 说明 DMM 抓取路径可用，但需要更小切片、更长 QMP 超时，或确认 appFw 是否真的启动到可显示状态。
- 下一步：抓 16MB 切片/延长超时，或走 guest 侧 framebuffer/OSD；当前最稳仍是 `grmreal46` 的 180s 无 Oops/media start。
- 仍无 FX6 菜单证据。

## CP unhandled 源码：未知 destination 只记录不回复

- `cp-helper-agnostic/fx6-cp-backup-sync100-agnostic.c` 的 `cp_reset_send_backup100_prior` 只处理 `dst==0x903e0811`；其他 destination 进入：
  `cp_raw("UNHANDLED",...)` + `FX3_BACKUP_CP_UNHANDLED_SOURCE ... no_reply=1 no_free=1`，直接 `return 0`。
- 当前 unhandled `0x92a208fc`/`0x9092083f`/`0x928708f7` 因此没有 reply/free；如果要让 AppFw 的这些请求有响应，需要给未知 destination 加 fallback reply + free，并重编 CP helper 内核模块。
- 该目录只有打包/校验脚本，没有 CP helper 的 kbuild 环境；重编前需找 Sony 内核头/Module.symvers 与原来的编译参数。
- 当前最稳仍是 `grmreal46` 的 180s 无 Oops/media start；无菜单证据。

## CP fallback 重建：insmod invalid module format

- 用 zig 重建了带 fallback reply/free 的 CP helper（`cp-fallback.ko` 57,656 B，`7307778de23453d71e229a4701da2644c94b3e6c2b4d057ef6cf855000a54343`），.modinfo/vermagic 与已知模块字符串一致。
- `grmreal48` 运行 `cp-bind-1ec42a96` 在 CP insmod 处失败：`insmod: can't insert '/simulation/fx3-cp-backup-reset-v1.ko': invalid module format`，`FX3_BACKUP_CP_INSMOD_RC=8`；无 AP。
- 说明当前 zig 重建的 section/relocation/格式与可加载模块仍有差异；需要复现原构建 flags/处理 `.text.unlikely`/relocation，暂不能用。
- 当前最稳仍是 `grmreal46`：180s 无 Oops、MEDIA_START，但无菜单证据。
- 下一步：对比已知/重建模块的 section 与 relocation，复现原构建；或改走 guest UI 证据。

## CP fallback 可加载但导致 AP 回退到 IM_ENDMAPS

- `-mcmodel=large -mgeneral-regs-only` 重建的 CP fallback（`cp-fallback3.ko` 68,440 B，`5012c5db46ebc3036ca06f6200c01e2f63243b4a38e87bc67d363626d48ea171`）不再有 unsupported relocation，`FX3_BACKUP_CP_INSMOD_RC=0`。
- 但 `grmreal50` 运行 `cp-bind-...` 只到 `FX3_AP_IM_ENDMAPS`，没有 `FX3_RM_NATIVE_FREE`/`FX3_MEDIA_START_BRANCH`，serial 仅 1.3MB；AP 明确回退。
- 说明对未知 destination 的 **reply/free fallback 协议不正确**，会消费/破坏应继续路由的消息；比原来的 no_reply/no_free 更差。
- 回退到 `grmreal46`（原 CP helper，180s 无 Oops/media start）作为最佳候选；CP fallback 不再使用。
- 下一步：保持原 CP 行为，只做 guest UI 证据或精确处理个别 destination，不再广谱 reply。

## 真实 FrameBuffer::update 回归：无 MEDIA_START

- `libgrm-fbinit10.so` 把 `FrameBuffer::update` 从 skip 改为调用真实函数；`grmreal51` 运行 `cp-bind-...`（120s）。
- 结果：`fault_markers=[]`，但 AP markers 只有 `FX3_AP_IM_ENDMAPS`/`FX3_RM_NATIVE_FREE`，没有 `FX3_MEDIA_START_BRANCH`；serial 2.48MB。真实 update 让 AP 停在 media 之前，轨迹与 skip 版明显不同。
- 说明当前 fake/minimal FrameBuffer 下，`update` 必须 skip 才能推进；直接调用真实 update 不会产生画面，反而停滞。
- 回退到 `grmreal46`（update skip）作为最佳：180s 无 Oops、MEDIA_START，但无菜单证据。
- 下一步：只在真实 FB/manager 完整时启用 update；当前 candidate 保持 update skip。

## 真实 manager（移除 fbinit）也无 MEDIA_START

- `grmreal52` 从 `grmreal46` 的 LD_PRELOAD 移除 `libgrm-fbinit9.so`，让 AppFw 走真实 `FBResourceManager`/`FrameBuffer`。
- 运行 60s：`fault_markers=[]`，但 AP markers 只有 `FX3_AP_IM_ENDMAPS`/`FX3_RM_NATIVE_FREE`，没有 `FX3_MEDIA_START_BRANCH`；serial 2.07MB。
- 说明真实 manager 路径同样让 AP 停在 media 前；当前更新/执行链仍依赖 fbinit 的 minimal/skip，真实 GRM 后端未建立。
- 最佳仍是 `grmreal46`：180s 无 Oops、MEDIA_START，但无菜单证据。
- 下一步：保持 fbinit/update skip；只做 guest UI 证据或精确 CP destination，不再切真实 manager/update。

## 主 futex 匹配 FX3 UI gate 模拟垫片

- `libconddiag` 在 `grmreal46` 上抓到主 futex `0x7f44014ee8`；对应 `pthread_cond` `c=0x7f44014ec0`、`m=0x7f04d6e7a8`；caller1 映射到 `/simulation/fx3-ui-gate-v1.so+0x2c40`。
- 该 cond 记录 1 次 wait、0 次 signal：AppFw 卡在 **FX3 UI gate 模拟垫片**，不是 AppFw/MWF 自身。
- 从 `grmreal46` 的 LD_PRELOAD 移除 `/simulation/fx3-ui-gate-v1.so` 得到 `grmreal54`；120s 无 Oops、仍有 `FX3_MEDIA_START_BRANCH`，serial 4.46MB，但无菜单/无 `FX3_AP89_SCREEN_CREATE`。
- 说明 UI gate 是一个真实阻塞点，但移除它只是换到后续等待/正常 UI 状态，仍缺画面证据。
- 下一步：查 grmreal54 的下一个主 cond/UI shim，或做 guest 侧画面证据；当前最佳候选可为 `grmreal54` 或 `grmreal46`（均无菜单）。

## 移除 UI gate 后：主等待转入 AppFw 自身 cond

- `grmreal54 + conddiag`（`grmreal55`）运行 `cp-bind-cef6f626`：AppFw 主 futex `0x7f48014d18`。
- 匹配 `CONDDIAG_WAIT c=0x7f48014cf0 m=0x7f0057a7a8`，caller1 映射到 `appFw.so+0x1acd988`。
- 反汇编 `0x1acd984` 正是 `std::condition_variable::wait@plt`；该 cond 仅 1 次 wait、0 次 signal。
- 说明移除 FX3 UI gate 后，主线程不再卡在模拟垫片，而是转入 AppFw 自身的 condition_variable/worker 队列；仍无菜单。
- 下一步：定位该 AppFw cond 的 producer/队列（`0x5a3b7a0` 附近状态），或继续 guest UI 证据；当前最佳仍无菜单。

## 纠正：UI gate 是观察器，真正主 cond 在 AppFw

- `fx3-ui-gate-v1.so` 导出 `_ZNSt18condition_variable4wait...` 并打印 `FX3_BOOT_CV_WAIT`/`FX3_BOOT_EVENT_LINK`；它是 `observed_only=1` 的**观察器**，不是 signaler/阻塞源。
- conddiag 在 `grmreal46` 上看到的 caller1 `fx3-ui-gate+0x2c40` 只是 wrapper；移除它后，caller1 变为 `appFw.so+0x1acd988`，对应 appFw `0x1acd984` 的 `std::condition_variable::wait`。
- 该 AppFw cond 记录 1 wait / 0 signal；主线程真正等的是 AppFw 的 boot/UI 事件。移除 UI gate 只是去掉观察器，不解决等待。
- 当前最佳 `grmreal54`/`grmreal55` 仍无菜单；下一步应找 boot event/key producer，而不是继续移除 UI gate。
- 这解释了此前 UI gate 移除后仍有主 futex 的原因。

## Host key 注入成功：MENU 键被 native 接收，但无 screen/menu

- 用 `gate_input96.InputGate` 通过 QEMU GDB physical mode 写 `0x41df00000` 的 key worker 控制块：step1、key `0x1ab`(MENU)、hold 100ms；写入/回读均匹配。
- key worker 接受：`FX3_KEY95_STEP_DONE` 1 次；`FX3_KEY96_POLL ... done=1 control_step=1 key=0x1ab last_send=0 native_receiver_queue_exists=1` 持续 25 行；说明 host→native input 路径真实打通。
- 但运行 60s 仍无 `FX3_AP89_SCREEN_CREATE`/菜单；serial 3.23MB，无 fault，`FX3_MEDIA_START_BRANCH` 2 次，`FX3_UI` 3067；screen/update 仍无证据。
- 可能原因：0x1ab 不是 FX6 菜单入口、UI 尚未到可接收状态，或 fake FrameBuffer/update skip 使画面不产生。key 路径本身已验证。
- 当前最佳仍 `grmreal54`（无菜单）；下一步可试 key 序列/其他键，或在真实 screen 路径上重试。
- 运行 `cp-bind-90cfb3b1`；serial SHA `b9d247c360f7d1df983b324869ed61e021a1772a124b362d256ef925b6ff7c03`。

## Key 序列 MENU/DOWN/UP/LEFT 均被接收，仍无 screen

- 在 `grmreal54` 上通过 QMP stop/cont + GDB physical gate 依次发送：step1 `0x1ab`(MENU)、step2 `0x30`(DOWN)、step3 `0x1ac`(UP)、step4 `0x1af`(LEFT)。
- 四步全部成功：`FX3_KEY95_STEP_DONE` 4 次、`FX3_KEY_CACHE` 4 次、`native_input_queue=1`、`wait_result=0`；无 fault，`FX3_MEDIA_START_BRANCH` 2 次。
- 但 `FX3_AP89_SCREEN_CREATE` 仍为 0，`FX3_UI` 3071，无菜单/画面证据。
- 结论：host→native input 路径已完整验证；剩余缺口是 screen/framebuffer 渲染，不是按键。
- 当前最佳 `grmreal54`；下一步应解决真实 screen/update，而不再加按键。
- 运行 `cp-bind-75cdd20e`；serial SHA `9a3d8ddce0d81b3f67aac3e7cdfa2b15622faf2a412adad5ba34876f9f999932`。

## FrameBuffer 对象转储：像素 buffer 指针为空

- `libgrm-fbinit11` 在 `FrameBuffer::update` 打印对象字段；`grmreal56` + key 序列运行 `cp-bind-f3a1012b`。
- 对象 `self=0x7faf3bf3c0`：word0 vtable `0x7faf028e90`，word1 像素 buffer 指针 = **0**，word2 `0x021c040000000000` 含 1024x540，word3=1；其余为 0。
- `setSize(1024,540)` 已被调用，但 shim 只记录不分配；`update` skip；因此 AppFw 从未拿到可绘制的像素 buffer，`FX3_AP89_SCREEN_CREATE` 0、无菜单。
- 这解释了“keys 全接收但无画面”：不是输入，而是 FrameBuffer 没有 backing store。
- 下一步：在 `setSize` 分配 1024x540x4、写入对象 word1，让 AppFw draw，再把 buffer 落到 reserved RAM/交给 host 读，做真正的 guest 侧抓屏。
- 运行 serial SHA `f80224accfe02ab830e304d26900ce912e28bb28147ce3b86f1bc418bc136982`。

## fake FrameBuffer 的 getOnscreen/getOffscreen 返回 NULL

- 源码 `libgrm-fbinit9.c`：`getOnscreen`/`getOffscreen` 均 `result=NULL`，`getOnscreenHandle=0`；`setSize` 只写 `+0x14/+0x16` 的宽高，不分配像素/BMP。
- 因此 AppFw 的 draw 路径没有 BMP backing；对象 word1 像素指针=0、BMP 指针也为空；`update` skip 只是让流程继续，不会产生画面。
- key 序列 4 个全部被 native 接收，进一步说明“输入通、画面无”的根因在 fake FB/BMP，不在按键。
- 要出画面必须提供真实 BMP/GRM/GPE backing；真实 manager/update 在此 VM 已回归（无 MEDIA_START），当前 fake 路径无法绘制。
- 当前最佳 `grmreal54`/`grmreal56`；无菜单证据。

## 真实 FB initialize/getOnscreen/setSize 回归

- `libgrm-fbinit12`：`FrameBuffer::initialize`/`getOnscreen`/`setSize` 改调真实函数，`FBResourceManager::initialize` 仍 skip；`grmreal57` + key 序列运行 `cp-bind-d76c4edc`。
- 结果：serial 仅 985KB；`FX3_MEDIA_START_BRANCH` 0、`FX3_RM_NATIVE_FREE` 0；`FX6_GRM_FB_INIT_REAL`/`GET_ONSCREEN_REAL` 0；`FX3_KEY95_STEP_DONE` 0；key 线程报 `host-step software identity/order mismatch`。
- 说明 AppFw 在到达真实 FB init 之前就被真实 `setSize`/initialize 路径拖停；fake `setSize` + `getOnscreen=NULL` 是当前能到 MEDIA_START 的必要条件。
- 真实 FB 路径不可用；fake 路径无 BMP/像素，mac VM 的屏幕证据仍缺。
- 当前最佳仍 `grmreal54`/`grmreal56`；无菜单。

## 延迟真实 initialize 未触发：AppFw 没到 FrameBuffer 调用

- `fbinit13` 在第一个 `FrameBuffer::update` 才调真实 initialize；`grmreal58` + key 序列运行 `cp-bind-40f9594d`。
- 结果：serial 2.92MB；`FX6_GRM_FB_INIT_LATE` 0、`UPDATE_LATE` 0、`GET_ONSCREEN_REAL` 0；`FX3_MEDIA_START_BRANCH` 0；`FX3_UI` 4059、`FX3_RM_NATIVE_FREE` 11；keys 4 步仍被接收。
- 说明这条 AppFw 路径根本没有调用 FrameBuffer 的 update/getOnscreen；延迟 initialize 没机会执行，也没有 BMP/画面。
- fake `grmreal54`（到 MEDIA_START）仍是当前最佳；真实/延迟 FB 都会在不同阶段回归。
- 下一步只能接受 headless AppFw，或另找真正被调用的 screen 接口。

## fake setSize + 真实 init/getOnscreen：initialize/getter 未被调用

- `fbinit14` 保留 fake `setSize`，只把 `FrameBuffer::initialize`/`getOnscreen` 改真实；`grmreal59` + key 序列运行 `cp-bind-dd94986e`。
- 结果：serial 3.29MB；`SET_SIZE` 1、`INIT_REAL` 0、`GET_ONSCREEN_REAL` 0；`FX3_MEDIA_START_BRANCH` 2、`FX3_UI` 3062、`FX3_KEY95_STEP_DONE` 4；`FX3_AP89_SCREEN_CREATE` 0。
- 说明 AppFw 的 media 路径根本不调用 `FrameBuffer::initialize`/`getOnscreen`；改真实方法也没机会执行，仍无 BMP/画面。
- 当前最佳 `grmreal54`/`grmreal59` 都能到 media + native keys，但没有 screen；goal 仍 active。

## GPE surface 抓到但全零

- 在 `grmreal54` 上按 `FX3_GPE_RESOURCE_REGISTER` 的 `type=0x403` 资源做 QMP `pmemsave`：`gpe.bin` 1,310,720 B（0x140000）成功写出。
- 但该文件 **全零**（nonzero=0, unique=1）；本次 `logical=0x7f3c508000`、`phys=0x43ae96000`、`bytes=0x140000`。
- 结合 `FX3_GPE_MODEL_INIT mode=request_capture physical_engine=0`，这个 surface 是请求捕获用的缓冲，不是已渲染的屏幕；物理读取没有像素。
- 至此 fake FrameBuffer（getOnscreen=NULL）、真实 FrameBuffer（回归）、GPE surface（全零）三条屏幕路径都没有像素。
- 当前唯一稳定的是 headless AppFw：MEDIA_START + native keys；无菜单证据。
- 运行 `cp-bind-bdd01051`；serial SHA `12333bd7764bbf1f82877a879104efd64985d0b49b5e8eaa0cec94544290b405`。

本轮所有 VM 均单 Start；最新运行 QEMU exit 0、process reaped、双锁 free。目标保持 active，未完成。

## 可见菜单尝试（rounds 7-10）

- `grmreal56`：仅把 `appFw.so+0x1acd984` 的 `bl` 改 NOP，media/keys 正常，但两个 GPE surface 仍全零。
- `grmreal57`：再移除 `fx3-osd-headless-v5.so`、`FX3_OSD_HEADLESS=native`，AppFw 回退：`FX3_MEDIA_START_BRANCH=0`、`FX3_KEY95_STEP_DONE=0`。
- 结论：固定 FX3 平台是 headless；GPE `type=0x403` 两个 surface 是 `request_capture` 缓冲，全零；没有可读 scanout。可见菜单需要真实显示/scanout 后端。
- 运行 `cp-bind-05ae9342`、`cp-bind-c851d98c`；无 Oops，但无像素。


## appFw DMM 线索（round 14）

- 从 `usr/lib/appFw.so` 提取字符串，确认 AppFw 使用 **DMM（display memory manager）** 作为真实显示缓冲：
  - `dmm_alloc_and_open`、`dmm_open`、`dmm_mmap`、`dmm_get_unit_size`、`set_dmm_info`；
  - 错误串：`dmm virtual address nullptr`、`DMM[unit_type:0x%x] alloc failed`、`Failure dmm_mmap`。
- 这解释了 GPE `type=0x403` 两个 surface 全零：它们是 `request_capture` 缓冲，不是 scanout；AppFw 的显示路径走 **DMM**。
- 下一步：在 FX3 官方 OSS kernel 中找 `dmm` 驱动，确认 `unit_type`、物理地址和 `dmm virtual address nullptr` 的触发条件（很可能与 headless shim/虚拟地址映射有关）。

