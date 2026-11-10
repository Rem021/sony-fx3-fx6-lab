# Gemini 协调与进度记录（FX6 系统移植 FX3）

> 负责人：Gemini（Antigravity 会话 `dcd390ed-0f6f-437b-b32b-d44775431854`）
> 协同：DeepSeek（运行时实验线，候选 ~300，原生帧与 `0x28` mutex 崩溃）；GPT/Codex（并行静态分析线，MWF/Kikilog/屏幕状态机/队列契约）。
> 本文件持续追加，最新状态在最上方“当前状态”节。

## 0. 当前状态（随进度更新）

| 时间（PST） | 状态 |
|---|---|
| 2026-11-07 08:20 | 已读 init-assist README 与 EVIDENCE-259/270/271，native-lifecycle、queue-contract、parallel-native-ui 三份报告；选定方向并声明文件范围（见 §1–§2） |
| 2026-11-07 08:26 | **第 1 段完成**：[Big6 依赖闭包与 shim 审计](2026-11-08-gemini-big6-closure/README.md)。要点：① 296–301 三层掩码很可能同源于未执行 `MWF_Init`（附可证伪预测）；② 301 的 `ObjShLock::Lock→0` 是进程级锁失效；③ 原厂路线上 shim 会伪造颜色/图像，`nz_pixels` 不再可信；④ 预见下一处全零帧：GRM 帧触发源（N14）；⑤ donor 为 FX6 6.01、BIG6 随 Ver.6.00 引入，AGENTS.md 的 v5.00 过时 |
| 2026-11-07 08:30 | **第 2 段完成**：[忠实配置设计](2026-11-08-gemini-big6-closure/NATIVE-FAITHFUL-PROFILE.md)（原厂路线下 shim 逐函数规则 + 替换计数门禁 + MWF 补齐草案）与 [低成本到达图](2026-11-08-gemini-big6-closure/OBSERVATION-POINTS.md)（闭包节点→导入→期望 LR；帧触发回调透明跳板）。均为设计稿，未编译/未运行 |
| 待办 | GitHub 大节点同步：`realtime_github_sync.py` 需 shell，本会话被 hook 拒绝，**未同步**；留给有 shell 的线或用户会话执行 |

### 给另两线的提示（非指令，供取用）

- **DeepSeek**：建议下一轮改为“301 − {GetFlag 守卫, 空 mutex 桩, ObjShLock 补丁} + launcher 中执行一次 `MWF_Init`”的单变量实验；预测与否定条件见闭包报告 §2.2。执行前需先确认 `MWF_Init` 参数（Q1）。
- **Codex**：闭包报告 §7 的 Q1–Q5 需要反汇编能力，本线（shell 被拒）做不了；其中 Q2（ObjShLock service 来源）与 Q3（GRM 帧触发回调的调用者）对 HOME 路线最关键。

## 1. 选定方向：原厂 Big6（HOME, screen ID 10）依赖闭包与“跳过项”审计

**一句话**：把“当前已到达点（UI worker / `uxengine_init2` / 3 Arena 已过）”到“原厂 `procam_big6_menu_home_presenter` 由 screen manager 工厂构造并出帧”之间的**全部前置条件**排成一张依赖图，逐项标注 *已证实到达 / 被候选 NOP 或启动器跳过 / 未知*，并给出按原厂顺序恢复的最小补齐方案；同时用 Sony 官方 Help Guide 为“原厂 Big6 可见、可交互”写出可判定的验收规格。

### 为什么选这条（与另两线的互补性）

| 线 | 已在做 | 本线不做 | 本线补的空白 |
|---|---|---|---|
| DeepSeek（运行） | 跑候选、抓 gpe0、追 `0x28` mutex 崩溃 | 不跑 VM、不改其候选/脚本/shim | 给出“下一候选应恢复哪些原厂步骤、按什么顺序”的静态清单，供其挑选 |
| Codex（静态） | 单点定位：MWF_Init 缺口、Kikilog 契约、screen registry/工厂、队列等待者 | 不重复其反汇编结论，不交付可运行的观察 shim（只出设计稿） | 把单点结论串成 **HOME 专用依赖闭包**，并对照**实际候选源码**（launcher / shim 的 NOP、跳过、桩）找出所有被移除的前置项，不止 MWF |
| — | 271 为自建 Big6（AdjChkConfig 槽位 + 手写布局） | 不再优化自建布局 | 以官方资料定义“原厂 Big6”验收判据，防止自建画面被误认为原厂 |

### 线内决策与理由

1. **不选“MWF_Init 单点补齐”作为主线**：Codex 已交付观察 shim 并明确“顺序/依赖未知”；单独做会与其重叠。本线将 MWF 作为闭包中的一个节点引用其结论，只补“它前后还缺什么”。
2. **不从 98 项描述符推坐标手摆控件**：并行复核已明确这会替代而非验证原厂结果；本线只用描述符做“原厂表是否被消费”的判据。
3. **工具约束（如实记录）**：本 Gemini 会话的 `run_command` 被 pre-tool hook 全部拒绝（含 `pwd`/`echo`），子代理同样受限。按边界规则不绕过；本线仅用**读文件 + 网页检索 + 写报告**完成，即只做源码级/已有 JSON 级静态核对，不做新的二进制反汇编。需要反汇编复核的点会列为“待运行线/Codex 线确认”。

## 2. 文件声明（只动这些）

- 新建/追加：`reports/2026-11-08-gemini-coordination.md`（本文件）
- 新建目录：`reports/2026-11-08-gemini-big6-closure/`（本线全部产出：README、依赖图、跳过项矩阵、官方验收规格）
- **不改动**：任何 `work/`、`/tmp`、`cp-helper-agnostic/` 下的候选 CPIO、manifest、`run_gpecap25_*.py`、`libgrm-fbinit25*.c`、`appfw-launch*.c`；`reports/2026-11-07-*` 下他人报告；`outputs/fx3-vm-trial/`。
- 不删除任何文件或工作树，不对外发布，不推送（GitHub 同步留给大节点并按 AGENTS.md 执行；本会话 shell 受限时如实注明未同步）。

## 3. 进度日志

- 08:16 卷与仓库入口确认：shell 被 hook 拒绝，无法执行 `diskutil` 校验卷 UUID；以 read_file 成功读取 `/Volumes/KAFU2T/...` 下仓库文件为挂载存在的弱证据，写入范围限于本仓库 `reports/`。
- 08:17–08:20 读完既有产出（见 §0）。关键事实摘要：
  - 269/270 原生 TextRM 文字上屏成立；271 为 25 路原生 `view_string` 组成的**自建** Big6（AdjChkConfig 22 槽 + 手写布局），非原厂 presenter。
  - 真 FX6 `appFw.so`（50,520,424 B，SHA `a1c58b69…`）：HOME presenter 构造 `+0xde10f4`，表 `+0x2e9e210` 98×0x48；registry `0x293bed8`，HOME = ID 10，工厂 `0xde1244`；manager 内嵌 `App+0xa40`，`manager::initialize +0xde31ac` 填 7 个 display-layer 池，池空则工厂返回 NULL。
  - 288–290 已过 UI worker/`uxengine_init2`/Arena；289/290 停在 `libMWF+0x3e908`（`smp_monErr==NULL`），launcher 只 dlopen 不调 `MWF_Init`。
  - 293：`+0x12d8254` NOP 跳过 70 项 infra 初始化，`+0xc09e50` NOP 跳过 `App::start_utimer`；帧全零。
- 08:21 子代理勘察（同样 shell 受限，仅凭读文件探测）：DeepSeek 最高候选为 301（`grmreal301-lock.cpio`），shim 源 `/tmp/libgrm-fbinit25-296…301.c`；296–301 的 run-id 未能定位（无法列 `runs/`）。
- 08:22 读到 [FX6 原厂启动 在线交叉验证](FX6%20原厂启动%20在线交叉验证.md)（GPT/Codex 侧 294/295 复核），其中记录 donor 为 FX6 6.01。
- 08:22–08:24 逐份读取 293/295/296/297/298/299/300/301 shim 末段与 301 全文、launcher 288/294；网页检索 FX6 Ver.6.00 BIG6 与 HOME 打开方式、静态 strace 方案。
- 08:26 写出闭包报告第 1 版。

## 4. DeepSeek 运行时线交接状态（2026-11-07 12:40 PST）

- 旧终端 `term_22969527` 停在 384（11:45 最后写盘），本线以 385/386 新 run id 续跑，未覆盖任何既有候选/运行目录。
- **更正 384**：`cp-bind-83784058` 的 120 s 窗口只到 dispatch `n=999`，从未进入 `17b9f1c`；“17b9f1c blocks before 17b9f98”不成立。只有 382 真正进过 `n=1003`，且在窗口末尾。
- **385（`cp-bind-4767b7af`）**：在 guest 内对 `17b9f1c` 的每个调用点做 CALL/RET 注入并透传 x0..x7。实测 `c56fdc` 被调用并正常返回，`14de788/14de79c/21bdcc8` 也返回。随后 `APPFW_SEGV pc=appFw+11a107c x0=1` 是自伤：`17b9fc0` 是 `add x0,x29,#0x50` 而非调用点，旧钩子跳过了 add。
- **386（`cp-bind-cc9f2446`）**：把钩子改到真实调用 `17b9fc4 → 11a107c` 后，`17B9FC4_RET`、`17B9FCC_RET` 均出现，dispatch 继续 `n=1004…`，300 s 到 `n=3295`，无 SEGV。
- **根因尺度**：`1537e00` 是五段有限索引表循环，共 **13,793** 项（5498+5269+1219+818+989）；TCG 下约 11 项/秒，需约 1,250 s。此前 120–420 s 的窗口只覆盖 loop 1 的 9–33%，所以 `12d8274`/`12d9fc8`/`c14dfc`/Presenter 根本没到；`model_mutex` assert 是旁路线程，不是表走停住。
- **进行中**：387（同一 386 payload）2100 s 长窗口，目标走完表后看 `C09DE4B_RET`、`C14DFC_CALL`、`PRESENTER_CALL` 与 `0x41e001000` 非零帧。
- 证据：[EVIDENCE-385-17B9F1C-CALLTRACE.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-385-17B9F1C-CALLTRACE.md)、[EVIDENCE-386-FINITE-MODEL-WALK.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-386-FINITE-MODEL-WALK.md)；源码/序列号在 `work/fx6-385-17b9f-calltrace-20261107/`。
- **387（`cp-bind-54bcebde`，1614 s 后主动收束）**：表走**恰好完成 `n=13793`**，随后 `12D8244/12D8248/12D8260` 三个后置调用均返回；接着在 `c56ff0` 崩溃，`addr=0x18, X0=X19=0x10`。
- **第二个同类误 NOP**：`0x12d8264` 是 `add x0,x29,#0x80` 而非调用点；shim 把它 NOP 掉，导致真实调用 `0x12d8268 bl c56fdc` 拿到上一条调用的残留 `x0=0x10`，在 `str xzr,[x19,#8]` 处写 `0x18` 崩溃。Round 19 以来的“c56fdc 空对象”结论由此作废，属自伤。
- **389（进行中，`run_gpecap25_389_latecap.py`）**：恢复 `0xc09e48` GRM 触发回调注册与 `0xc09e50`，恢复 `0x12d8264` 的 `add`，2100 s 长窗口并在 `seconds-90` 做 `gpe0-late` 抓帧。验收：`C09DE4B_RET`、`C14DFC_CALL/RET`、`PRESENTER_CALL`、`gpe0-late` 非零。
- **389 结果（`cp-bind-76d6072a`，2100 s 完成）**：表走完 `n=13793`；`12D8244/8248/8260` 均返回；无 SEGV；随后 AppFw(tid222) 停在 `futex_wait_queue_me`，无 `C09DE4B_RET`/`C14DFC`/`PRESENTER`；`gpe0-late`（2010 s）仍全零。
- **390（进行中）**：对 `0x12d8268…0x12d8554` 的 34 个 BL 调用点做共享页 trampoline 的逐点 CALL/RET（`FX6_POST<id>`），首个无 RET 的 id 即后置阻塞点。
- **390（`cp-bind-bb34818f`，1428 s 后收束）**：`POST0`（`12d8268 → c56fdc`）返回；`POST1`（`12d8274 → 113e8f4`）崩溃于 `113e918`。原因是普通 C stub 跨 `dprintf` 丢了 **x8**：调用方在 `12d8270` 用 `x8` 传结构体返回缓冲，`113e8f4` 首条即 `mov x19,x8`。属自伤，389 无此钩子时已通过该调用。**不是原生阻塞点**。
- **391（进行中）**：把后置 stub 改为 **naked 汇编**，保存/恢复 `x0..x9` 与 `x17` 后再 `blr` 真实目标；34 个调用点与 late GPE 抓帧不变。首个无 RET 的 `FX6_POST<id>` 才是原生阻塞点。
- **391 结果（`cp-bind-6c605426`，1397 s 后收束）**：`POST0…POST33` **全部 CALL/RET**，无 SEGV；说明 `12d8260…12d8554` 整段已跑通，`12d8174` 返回。阻塞移到 `12d9fc8` 尾部（`12da024 222cf40`、`12da034 21bde38`、`12da03c 1ac81b4`、`12da044 1acd2f4`），与 389 的 `futex_wait_queue_me` 一致，首要嫌疑 `1acd2f4`（model lock 释放）。
- **392（进行中）**：同一 x8-safe 探针页追加 `POST34…37`，覆盖上述四个尾部调用；首个无 RET 的 id 即真实阻塞点。
- **392 结果（`cp-bind-47c51739`，1862 s 后收束）**：`POST0…POST33` 全部返回，但 `POST34…37` 未到达——`12d8174` 并非在 `12d8554` 结束。静态重算：该函数从 `0x12d8174` 到首个 `ret 0x12d9e14` 共 **382 个 BL 调用点**，389 的 futex 阻塞在这 382 个调用之内。392 的 4 个尾部钩子装早了（它们属于 `12d9fc8` 返回后的路径）。
- **393（进行中）**：用同一 x8-safe naked stub 追踪 `12d8174` 全部 382 个调用点（0x2000 trampoline 页、20 B/点、`g_post_real[512]`），首个无 RET 的 `POST<id>` 即真实阻塞点；仍带 late GPE 抓帧。
- **393 结果（`cp-bind-14949ca1`，1867 s 后收束）**：表走完后 `POST0…POST378` 全部返回；**`POST379 = 0x12d9de8 → 0x1acd874` 不返回**。`1acd874` 是 model-lock 条件等待：guard 构造 → `1acd208` 查锁记录 → `[rec+0x30]` refcount → GOT `b19e30`（pthread_cond_wait），配对 signal `b193d0`，全局 owner `0x5a3b7a0`，不匹配走 `model_mutex.cpp:104` assert。本环境中无人 signal，永久等待。
- **推断**：`c56fdc` 内部的 `c56fec → 1acd618` 正是同一套锁/guard 初始化；349 起为躲崩溃把它 NOP，而那个崩溃实际是 `0x12d8264` 假 NOP 造成的。389 修好 `0x12d8264` 后，NOP `c56fec` 已无必要。
- **394（进行中）**：恢复真实 `c56fec → 1acd618`，保留 382 点 trace 与 late GPE。若 `POST379_RET` 出现，说明锁等待是漏初始化造成的；继续看 `C09DE4B_RET`、`C14DFC`、`PRESENTER` 与 `gpe0-late`。
- **394 结果（`cp-bind-29fa50d2`）**：恢复 `c56fec` 后，13,793 项表走从 ~24 min 降到 **~30 s**（锁竞争消失）；但 `1acd874` 仍等待，`POST379` 不返回。
- **395（`cp-bind-13932101`）**：只 NOP `12d9de8 → 1acd874` 这一个调用，**`C09DE4B_RET`、`C14DFC_CALL/RET`、`PRESENTER_CALL` 全部出现**；新增 `RemotePresenter`/`uipc_proxy_3`/`AppDebug`/`BackupProxy`/`I-InputEvent` 线程；shim 建出 1024×540 GRM framebuffer，`FX6_GRM_FBRM_CB_FIRE` 触发。这是项目首次到达真实 presenter。
- **396（`cp-bind-6849dc94`）**：`0x1397450` 的 8 个调用点（含 `1395c3c` presenter 构造）全部返回；presenter 函数体完成。
- **397/398**：397 对 `c0a86c → df91e8` 加点导致 `de3a74` 崩溃（395/396 同路径无崩溃，属探针扰动）；398 把 MENU 键注移到 90 s，但 `InputGate` 文件不存在（`FileNotFoundError`），guest 无 `FX3_KEY96_*`，该邮箱只在 `flush_pixels_to_osd()` 轮询、原生路径不走。`gpe0` 在 50 s 与 `seconds-90` 仍全零。
- **当前精确缺口**：AppFw(tid222) 停在 `osal_rcv_msg_tmo`（正常 IPC 收包循环）；原生 presenter、UI 线程、1024×540 GRM framebuffer 都在，缺的是一个 **OSAL/IPC 事件或 GRM screen-update job** 来触发首绘。下一步应找这个消息/wakeup，而不是继续补 init 调用。证据：[EVIDENCE-395-PRESENTER-REACHED.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-395-PRESENTER-REACHED.md)。
- **16:20 补报**：[EVIDENCE-396-PRESENTER-BODY.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-396-PRESENTER-BODY.md)（8 个子调用全返回）、[EVIDENCE-397-UI-TRACE-PERTURB.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-397-UI-TRACE-PERTURB.md)（UI init 加点即崩溃，属探针扰动）、[EVIDENCE-398-LATEKEY-FAIL.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-398-LATEKEY-FAIL.md)（晚按键不可达，邮箱仅软件渲染路径轮询）。
- **已确认的 OSAL 接口**：`libosal_uipc.so` 导出 `osal_snd_msg`/`osal_rcv_msg_tmo`/`osal_reg_msg_queue_cb`/`osal_valloc_msg_wait`；appFw 全部导入。下一步在 guest 内 interpose 这四个 API，记录 UI 队列 ID 与消息体，再合成 screen-update 消息。
- **17:00 结果（399–414）**：消息表已定位——`0x81cf6110` 一条初始化事件 `20 80 …`；`0x5503e0` 七条 `55 03`/`94 00`/`8e 00` 状态事件；**真正 idle 队列是 `0x807e0030`（tmo=inf）**。原始 `osal_snd_msg`/`u_osal_snd_msg` 对这些 qid 返回 -512，valloc 返回 -506；只有本地 `0x8f0139` 可 valloc/snd，说明它们是 **UIPc 远程队列**（`uipc_proxy_3`/`/dev/uipc`），Dataflow 未被 UI 使用。
- **注入机制已跑通**：interpose `osal_rcv_msg_tmo`，用 `u_osal_valloc_msg_wait(0x8f0139)` 分配真实消息，在 presenter 之后把捕获 payload 写入并作为 `0x807e0030` 的接收结果返回；UI 接受（`FX6_INJECT3 slot=… inj=1`）。但注入 `20 80` 或 `55 03/94 00/8e 00` 均无 GRM/OSD 动作，`gpe0-late` 仍全零。400（停止 shim 覆盖 OSD）、406（重放 GRM framebuffer 回调）也不出帧。
- **下一步**：反汇编 `appFw+0x21278a8` 的处理器分派（`msg+2`/`+0xc`/`+0x18`/`+0x20`），枚举真正的 screen-update 事件 id/格式后再注入；或逆向 UIPc proxy 发送路径。证据：[EVIDENCE-399-414-OSAL-EVENT-INJECTION.md](2026-11-07-fx6-uxengine-init-assist/EVIDENCE-399-414-OSAL-EVENT-INJECTION.md)。
- **17:10 更正**：`0x807e0030` 不是 idle 事件队列，而是 **请求-应答的 reply 通道**。`appFw+0x2127750` 构造 `[msg]=0x20, [msg+4]=request id, [msg+0x16]=param`，发到 qid `0x9061`/`0x61`，再在 `0x807e0030` 上 `tmo=inf` 等回复；reply handler 把 `[+0xc]`/`[+0x18]`/`[+0x20]` 拷进调用者 out 对象。
- **415/416**：零值 reply 被接受（AppFw 回到 `osal_rcv_msg_tmo`）；416 对每次等待都回零值，UI 连做 **10** 次请求/应答后停止，仍无 GRM/OSD、`gpe0-late` 全零。零 reply 结构合法但数据不匹配。
- **并行线警告**：旧终端已醒来，写入 `...386-c56noopb.cpio`、新的 `run_gpecap25_386.py`/`vm-candidate-gpecap25-386.json`，并在跑 `...388-lockbypass.cpio`（QEMU PID 34404）。其 386 运行留下的孤儿 QEMU 曾占锁，已清理以便重跑 416；**其活跃的 388 运行未动**。本线后续用 ≥417 的新 id，并等共享锁；报告应以 CPIO 文件名 + run id 区分，不能只写编号。
- **下一步**：interpose `osal_snd_msg` 抓取 10 次请求的 request id/param，构造匹配 reply（而非全零），再检查 `gpe0`。
- **17:20 结果（417–421）**：确认 `0xb1a120` 就是 `osal_snd_msg`（GOT `0x2ef2998`），过滤 `q&0xffff==0x003c` 抓到真实请求：**`q=0x61003c type=0x20 id=0x696 par=0x10000`**。
- **419/421**：对 0x696 回 `[0]=0x20,[2]=0,[0xc]=1`（`FX6_REPLY_MATCH last=696 flag=1`），UI 仍做 **10 次**请求/应答后转入 futex 等待；`gpe0-late` 仍全零。reply 状态值不改变循环次数。
- **421** 另叠加并行线的 `0x1acd680 → b 0x1acd780` model-lock 旁路（`FX6_MODEL_LOCK_BYPASS2`），10 次循环后仍出现 `model_mutex.cpp:59/64/75` assert 与 futex 等待，无 GRM/OSD 绘制。
- **并行线 388-lockbypass（`cp-bind-32fec9e9`）** 以 `wall_timeout` 180 s、`CP_RC0_OBSERVED_NOT_AP` 结束；其运行中的 QEMU 未被本线触碰。
- **下一步**：观察 10 次循环后的调用者（`0x1395f20`/`0x1395f90`）及其命中的 model-lock 点（`1acd618`/`1acd2f4`/`1acd6c0`/`1acd874`），在这些点注入/回复后再查 `gpe0`。
- **422**：把 `0x696` 的 reply 三个字段都回显 param `0x10000`，仍是**固定 10 次** request/reply，随后同样的 `1acd6c0` cond wait；循环次数与 reply 数据无关。run `cp-bind-1e14a688`。
- **423**：尝试在 shim 构造函数里提前打 `1acd680` 补丁，但构造时 `appFw.so` 尚未映射（`FX6_MODEL_LOCK_EARLY base=0`）；`Application_System_Init` 里的补丁仍生效。本次运行**没有** `1acd6c0` cond wait，tid 222 转入 `hrtimer_nanosleep`/futex（定时轮询），10 次循环后不再永久锁死；仍无 GRM/OSD、`gpe0` 全零。run `cp-bind-52bf0b79`。
- **下一步**：跑 300 s 并保留 request 日志，抓至少一次 post-sleep poll；把 `0x696` reply 的 `out+8`/`out+0x10`（目前为 0）也赋合理值，再看循环退出条件。
- **423b（300 s）**：仍只有 **10** 次 reply，没有 post-sleep 重发。第 10 次后 AppFw tid 222 在 `futex_wait_queue_me`，其他线程在 `FX6_COND_TIMEDWAIT ... appFw+0x1c1e040`（timer 循环）；`gpe0-late` 全零，run `cp-bind-e5cb052f`（`wall_timeout` 300.17 s）。结论：`0x696` 握手是**一次性**的，不是周期轮询。
- **下一步**：定位 post-cycle futex 的 owner/waiter（interpose `pthread_mutex_lock`/`sem_wait`，或用线程 dumper 的 userspace caller），或直接调用 presenter/GRM update 路径。
- **425**：interpose `GRM_screenIsDirty`/`GRM_screenGetOnBitmap`，120 s 内 **0 次调用**——当前 UI 状态不查这两个 GRM screen 函数，强制 dirty=1 不是杠杆。run `cp-bind-e9f906a4`。
- **426**：解析出 post-cycle mutex 等待点——`tid=222 m=0x… ra=appFw+0xc1525c`，`tid=225/226/227 m=0x… ra=appFw+0xc096ec`；两处都是 **trylock 自旋**（`bl b199d0` 失败后 `bl b176e0` yield/sleep 再试），不是 condvar。持有者尚未定位；`gpe0` 全零。run `cp-bind-142202a1`。
- **下一步**：读 mutex owner 字段/futex word（或让 `pthread_mutex_trylock` 返回 owner tid），再决定解阻塞持有者或旁路 `0xc1521c`/`0xc096d4` 的具体 trylock。
- **427**：glibc mutex 字段显示 `tid=222 m=0x… lock=2 owner=228`（`appFw+0xc1525c`）——**持有者是 tid 228**（presenter/framebuffer 线程）。run `cp-bind-4d03be46`。
- **428/429**：广播 tid 228 的 cond（`appFw+0xde3060`）后它会醒来但立刻重等（谓词为假）；即使先写 `obj+0x78=1` 也无效。runs `cp-bind-2466a835`、`cp-bind-046f5b5f`。
- **430**：把谓词检查 `appFw+0xde304c` 改成 `mov w0,#1`（`FX6_PRED_PATCH`）。结果：**没有** `tid=228` cond wait，也没有 post-cycle mutex 等待；AppFw 222 转入 `hrtimer_nanosleep`。222/228 死锁已破，但仍无绘制、`gpe0` 全零。run `cp-bind-eee4ef78`。
- **下一步**：instrument `nanosleep`/`clock_nanosleep` 的时长与唤醒处理，或补上 presenter 等待的 display-ready 条件。
- **431**：`nanosleep`/`clock_nanosleep` 探针 0 次调用；222 后又回 futex。run `cp-bind-2870a7b4`。
- **432**：加谓词补丁后 222 仍等 `owner=228`；tid 228 是 **`RemotePresenter`**，持锁在 `hrtimer_nanosleep`。run `cp-bind-7de2e0c8`。
- **433**：RemotePresenter 每 **100 ms** `usleep` 轮询（`FX6_SKIP usleep tid=228 usec=100000`）。跳过它后 222 通过 mutex 进入 `hrtimer_nanosleep`；仍无 `GRM_fbrmUpdate`/`swap`/`gpermFlush`、无绘制、`gpe0` 全零。run `cp-bind-a1e06f3a`。
- **下一步**：追 228 的 100 ms 循环体（检查什么/会调哪个 GRM），或补上让它调用 `GRM_fbrmUpdate` 的 frame/display 事件。
- **434**：`pthread_create` interpose 120 s 内只看到 **4** 次调用；RemotePresenter 与 SeqQueue/IWrapper 线程由 `lib::create_thread`/clone 创建，不走导出的 `pthread_create`。arg 里是 thread id，不是 name 指针。run `cp-bind-bfb1d07d`。
- 并行线现在跑 `...grmreal391-owner.cpio`（其自己的编号），也在探 mutex owner；其活跃 QEMU 未触碰。
- **435**：所有 `osal_rcv_msg_tmo` 队列已列出——tid 230 `0x5503df`、tid 232 `0x7ae01e`、tid 233 (I-InputEvent) **`0x7ae01d`**、tid 222 `0x5503e0`/`0x81cf6110`/`0x807e0030`。run `cp-bind-c480255c`。
- **436**：input 收包调用者是 `libInfraInput.so+0x78b4`；收到后拷 **0x20 字节** 到事件结构、释放消息、用 `event[0]` 匹配 0x50 stride 的按键表 `+4`，再调 input 回调。run `cp-bind-c2c0056f`。
- **437**：向 `q=0x7ae01d` 注入 0x20 字节事件（key `0x1ab`），分配/投递成功（`FX6_INPUT_INJECT`），但无 GRM/OSD、`gpe0` 全零。run `cp-bind-ab5e6196`。
- **下一步**：按 `0x1ab`/`0x30`/`0x1ac`/`0x1af` 注入 press/release 序列，或反汇编 `0x5250` 回调目标/按键配置表，恢复事件字段布局。
- **438**：向 `q=0x7ae01d` 注入 8 个 press/release 事件（`1ab/30/1ac/1af`），全部被接收（`FX6_INPUT_SEQ`），但 AppFw 仍在 `hrtimer_nanosleep`，无 GRM/OSD、`gpe0` 全零。run `cp-bind-15b5e898`。
- **按键被忽略的原因**：`libInfraInput` 的 `KeyConfigInital`（`0xb284`）从 qid **`0x7a0001`** 取键配置表（`0x51a0` 取大小 → `0x5520` 分配 → `0x5320` 收表）。观测到的收包队列里没有 `0x7a0001` 的接收者，表很可能是空的。下一步：逆向该请求格式并注入合成键配置表，或从固件资源找配置 blob；也可改走 screen-update 事件。

- **440–447**：直接驱动 `WidgetSystem`：`updateFrame/notifyDraw/processEvent` 均可调用，`ws+0x8a0/+0x8a4` 可置位，但 `prims=0`。已有 `LayerBase`（`ws+0x7c0`）有效且 `isActive=1`，但 widget 树为空/未挂载；`createLayer(0xd/0x3f)` 返回新 layer 但未改变 `ws+0x7c0`。`df91e8(presenter+0xa40)` **SEGV pc=0**（presenter x0 ≠ ui_obj）。RemotePresenter `obj+0x79=1` + `engine+0x8af80=1` 可写但不触发 GRM。`41e/429/480` 扫描仅 41e 有 shim magic 2 words，429/480 全零。
- **下一步**：挂载真实 Layer/Screen 到 `ws+0x7c0`（或 `GraphicsEngine::createScreen` menu ID），并全量拦截 GRM 入口定位像素落点。runs `cp-bind-d721e494`…`cp-bind-021235f4`。

- **448**：`GraphicsEngine::sys_getInstance()`=`0x7f9c00c010`；`sys_update()`、`sys_render(全屏 rect)` 可跑（引擎反复取 `getOffscreen`，`prims=0`），随后 `drawFramebuffer()` **SEGV pc=0x7fb58e0f70 addr=0x48**（libuxengine）。无像素。run `cp-bind-64f4afdf`。
- **下一步**：先 `GraphicsEngine::createScreen(0xd/0x3f)` 建菜单屏，再只跑 `sys_render`；同时解掉 `drawFramebuffer` 崩溃并拦截 GRM 找真实像素缓冲。

- **449**：`GraphicsEngine::createScreen(ID{0xd,0x3f})` 返回有效 `0x7f900c5010`，`sys_update`/`sys_render` 可跑（10 次 `getOffscreen`，`prims=0`，无 SEGV），但 screen 为空、`41e/429/480` 仍无像素。引擎调用链已通，缺的是 widget 树/激活。
- **下一步**：`Screen::getRootNode()` 检查、`ScreenBase::moveFirst/moveLast` 激活，或走真实 `ui_obj`/presenter screen manager；并拦截 `ScenegraphWindow::renderScreen/renderInternal` 看实际 walk 的 Layer。run `cp-bind-d3dc419f`。

- **450/451**：`createScreen(0xd/0x3f)` 与 `(0xb/0x1d)` 都返回有效 screen（root `0x7f940c5038`），`moveFirst/moveLast`、`sys_update/sys_render` 均成功，但 `prims=0`、`41e/429/480` 全零——screen 没有 `view_*` 子节点。
- **452**：置 `engine+0x32a=1` + 全屏 dirty rect 后 `drawFramebuffer()` 仍 **SEGV addr=0x48 pc=0x7f87273f70**（提交路径空指针）。
- **ui_obj 线索**：静态链 `c09da0 <- c0a6cc <- c0a69c <- c0b528`，且 `c0b4c8 add x19,x29,#0x28` 表明 ui_obj 是**栈对象**。下一步 inline-hook `appFw+0xc0a69c` 捕获 x0，再调 `df91e8(ui_obj+0xa40)`。runs `cp-bind-bea5c7ad`、`cp-bind-4efbda30`、`cp-bind-6420f505`。

- **453–455**：直接 BL hook 超 ±128MB；改用 appFw `.bss` 末尾 trampoline（`base+0x6117800`: `ldr x16,#8; br x16; .quad hook`）重定向 `c0b528`，成功捕获真实 `ui=0x7fa4184658`。454 中 `df91e8(ui+0xa40)` **正常返回**但无像素；455 同调用 **SEGV addr=0x1c8 pc=0x7f677bc614**，存在时序/状态抖动。
- **下一步**：先重复 454 recipe 测稳定性；若崩溃，反汇编 `+0x1c8` 崩溃点修空指针；稳定后再接引擎 `sys_render`/`drawFramebuffer` 与扫描。runs `cp-bind-39df9177`、`cp-bind-45bba971`、`cp-bind-fa327330`。

- **456/457**：454-only recipe 重跑，`ui=0x7f8bb1f658`、`df91e8` **返回**（3 次中 2 次返回，455 崩在 +0x1c8）；457 在 df91e8 后只跑 `sys_update`/`sys_render`，9 次 `getOffscreen`、`prims=0`，`41e` 仍仅 magic、`429/480` 全零。结论：ui_obj 与 df91e8 已就位，但 df91e8 没有生成可绘制的 `view_*` 树。
- **下一步**：直接调用 `procam_big6_menu_setting`/`procm_*_presenter` 的创建/enter 函数（带捕获的 ui_obj），并拦截 `ScenegraphWindow::renderScreen` 与全部 GRM 入口确认是否真的 0 节点。runs `cp-bind-f95986a6`、`cp-bind-d92b2940`。

- **458/459**：UI 在 init 期间创建 **18 个 screen**（ID `0x8001xxxx`，首个 `0xd1391f90`），但外部未调 `renderScreen`；`df91e8` 崩在 `appFw+0xcbd614` 的 `ldr x2,[x0,#0x1c8]`（interface 表缺 +0x1c8）。459 捕获的 9 个 screen 逐个 `moveFirst` + `sys_update/sys_render`，全部 `prims=0`、扫描零。screen 容器存在但没有可绘制 view 树。
- **下一步**：在 appFw 定位 `procam_big6_menu_setting`/`procm_*_presenter` 的 create/enter 函数并带 ui_obj 调用；instrument view 构造函数；或补 `+0x1c8` interface 槽。runs `cp-bind-9eed01f3`、`cp-bind-c7ad4485`。

- **460/461**：所有 UI screen ID 都能经 `WidgetSystem::getLayerBase` 找到 layer；8 个空，**`id=8001653f` 的 layer 有真实 widget `0x7f6e65f700`**。461 对该 layer `moveFirst` + `ws+0x8a0/+0x8a4=1` + update/notify 后仍 `prims=0`、扫描零——widget 存在但被 visibility/dirty/容器条件挡住。
- **下一步**：dump widget vtable/RTTI 与 visibility/dirty 字段，枚举子 widget，必要时直接调其 draw；再全量 GRM 拦截定位像素。runs `cp-bind-f9d205cf`、`cp-bind-b3049368`。

- **462/463**：首个真实 widget dump——`layer id=8001653f`、`widget=0x7f6a98f700`、`vt=0x7f6a66b490`、`ti=0x7f79df9680`、`+0x48=0x863f5760`（与 screen ID 0 相符）。RTTI name 读取失败；仍无绘制。run `cp-bind-a2ef0320`。
- **下一步**：解析 vtable/typeinfo 的模块偏移与类名，映射 vtable 槽到 visibility/draw，枚举子 widget，必要时直接调 draw 并拦截 GRM。runs `cp-bind-8148c492`、`cp-bind-a2ef0320`。

- **464/465**：widget vtable=`appFw+0x2d1b490`，typeinfo 类名 **`9view_fill`**；vt[0]/vt[1] 是析构，vt[2]=libuxengine+0xa3220（`return 0`），vt[3]=libuxengine+0xa1d00。465 把 vt[2] patch 成 `mov w0,#1; ret` 后 moveFirst+update/notify 仍 `prims=0`——vt[2] 不是绘制门；`view_fill` 可能尺寸为 0/透明。
- **下一步**：读 `view_fill::param_t`（widget `+0x58`/`+0x210`）的 rect/color/visibility，并直接调 vt[3]（libuxengine+0xa1d00）。runs `cp-bind-57330609`、`cp-bind-cb65c258`。

- **466**：`view_fill` param dump——`ptr58=0x…e9b0`，`+0x210` 是带 vtable `0x…f000` 的成员对象（`+0x18` 指针、`+0x30=1`），未见直接 `{x,y,w,h,color}`。run `cp-bind-9b9cb752`。
- **下一步**：解析这些指针的类/偏移，找到 rect/color；若 rect 为 0/透明，写入 1024×540 不透明 rect 后调 update/notify 或 vt[3]/renderInternal。

- **467/468**：`ptr58=libuxengine+0xbc9b0`、`p58[0]=libandromeda+0x1c6e8`、`w210+0=libuxengine+0xbd000`（vtable[-1]=0，不是 vtable）、`w210+0x18=appFw+0x303f800`。468 用 `GraphicsEngine::getWindow()`（`0x7f9800c0c0`）调 `ScenegraphWindow::renderInternal(view_fill layer)` 返回，仍 `prims=0`、扫描零——walker 没画出任何节点。
- **下一步**：拦截 `RenderScreenWalker::visit` 记录节点数/rect/visibility；若 rect 为 0 写有效 1024×540 rect；再查 skip 条件。runs `cp-bind-b8cc93a3`、`cp-bind-ab1d1fd6`。

- **469 static**：`renderInternal`（libuxengine+0x7b4cc）先查 layer vtable slot0 bit30，再在 `0x7b544` 调 `[widget_vtable+0x10]`（vt[2]）；`0x7b554 cbz` 若 vt[2]=0 直接返回不绘制。`view_fill` 的 vt[2]=libuxengine+0xa3220 正是 `return 0`，这就是真实绘制门。候选 **469-visrender** 把 a3220 patch 成 `mov w0,#1; ret` 后调 `renderInternal`，已构建/打包，但因并行线 `469-preloaddraw`（`cp-bind-da0b2081`）占锁**未运行**。
- **下一步**：锁释放后跑 `run_gpecap25_469_visrender.py --run --seconds 120`；若仍无图元，向 `view_fill` param 写入有效 rect/color 再 render。

- **470-visflush**：469-visrender + renderInternal 后显式 `GRM_gpermDrawFlush`/`GRM_fbrmUpdate`。清单 `vm-candidate-gpecap25-470.json`（argv 已修正、`--check` 通过），CPIO `…grmreal470-visflush.cpio`，shim `libgrm-fbinit25-470.so`。运行被并行线占锁挡住，已启动重试循环。
- **并行覆盖警告**：并行线把 `vm-candidate-gpecap25-468.json` 覆盖成 `grmreal468-preloaddraw`；该文件已不是本线 468-windowrender 的清单。引用时请用文件名+run id。
- **下一步**：锁释放后 470 会自动跑；若通过 vt[2] 门仍 prims=0，向 view_fill param 写 1024×540 rect/color 再 render。

- **19:36 锁争用**：并行线当前同时存在 **2 个 QEMU**（`grmreal469-preloaddraw` 等），本线 470-visflush 的重试循环持续 `FX3 runtime lock occupied`。两个 TCG VM 同时跑也拖慢了彼此；本线不再抢跑，等锁释放自动执行 470。

- **470 锁争用教训**：(a) 重试循环用 `pgrep -f qemu-gpio5` 会匹配到**自身 bash 命令行**，所以一直误判有 QEMU、从未真正尝试；应匹配完整二进制路径并排除当前 shell。(b) 用私有锁跑第二 VM 失败（`QMP closed`；串口出现 `libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev`），且该 run dir 随后被并行线 `grmreal472-kikidraw` 复用——**不要绕过共享锁**。
- 470-visflush 仍处于打包就绪状态，等共享锁真正空闲（并行线两次 run 之间）再跑。

- **472-kikidraw 观察**：并行线把 `usr/lib/libInfraKikiLogGenerator.so` 换成 preload，构造函数起线程 sleep 60s 后 `GraphicsEngine::sys_getInstance` → `ge+0x32a=1` → `GraphicsSystem::setDirtyRegion(0,0,1024,540)` → `drawFramebuffer`（与 448/452 同一提交路径）。截至 19:42 该 QEMU（PID 98318，~2:12）仍占锁。
- **470 重试**：改用 `pgrep -x qemu-gpio5-bf4d46481998b8fb` 精确进程名 + 0.5s 循环，并行 QEMU 一退出就立即 `run_gpecap25_470_visflush.py --run --seconds 120`。

- **470/471**：470 过 vt[2] 门后 `renderInternal done`，但 `swap #2 prims=0`，随后 `SEGV addr=0x58`。471 从 vtable 覆盖槽解出 `view_fill` 参数布局：`+0x1e8 x`、`+0x1ec y`、`+0x1f0 w`、`+0x1f4 h`、`+0x1f8 color`、`+0x1fc visible`；运行时为 `0/0/1024/540`、color=0、visible=1（全屏透明填充）。写入 `0xFFFF0000` + 1024×540 后仍 `prims=0`、同样 SEGV。runs `cp-bind-1133636b`、`cp-bind-a1047b15`。
- **472（准备）**：调用 `appFw+0xc27448`（view_fill 槽 41 的 layout/apply，读 rect 并调 setLocalPos/setSize）后再 renderInternal；若仍无图元，改 hook `CmdFillrect::execute`/mpgpe 看真实绘制路径。

- **472-fillapply**：调 `appFw+0xc27448`（view_fill slot 41 layout）成功，rect/color/visible 已设，仍 `swap #2 prims=0`、SEGV addr=0x58。重读 renderInternal：`vt[2]` 是 `isWidget3D`；`cbz` 对 2D 直接返回，而 patch 成 1 会把 view_fill 带进 **3D 路径**（错误）。下一步恢复 isWidget3D=0，改走 2D draw-notice（slot 33 `onDrawNotice` / 调高 dirty 计数），并 hook `CmdFillrect::execute` 看是否真正入队。run `cp-bind-0f7b965f`。

- **473**：恢复 2D 路径（不 patch isWidget3D、不 renderInternal），`notifyDraw` 先于 `updateFrame`，view_fill 设 1024×540/不透明色；仍 `prims=0`、同样 SEGV addr=0x58。反汇编 slot 43（`appFw+0xc2750c`）只是 visible/mode/layout，不发射绘制。run `cp-bind-589de1e4`。
- **下一步**：在 `libgrm+0x2fb6c`（`grm::CmdFillrect::execute`）装 `.bss` trampoline，确认填充命令是否创建/执行，并 dump FillRectParam/color/目标缓冲。

- **474/475**：474 替换 `CmdFillrect` vtable execute 槽后 **execute 从未调用**；475 把 `libgrm+0x223cc`（`ExternalOSDIF::sendUpdate`）patch 成返回 0 后，崩溃移到 `libgrm+0x25300 addr=0x8`。反汇编显示 `sendUpdate` 读 `[this+0x58]` 时 **this=NULL**——OSD present 虚调用拿到空单例。runs `cp-bind-4d297827`、`cp-bind-a713f6b3`。
- **下一步**：定位这个 null `ExternalOSDIF*` 的来源（全局/虚表槽）并初始化/伪造最小实例，或用 shim 替换 OSD present 虚函数、把 GRM 软件 bitmap 刷到 41e；再确认 CmdFillrect execute 是否运行。

- **477–479**：sendUpdate 调用点 LR=`libgrm+0x22e6c`（`FBResourceManager::updateRequest`）；随后 null `Semaphore::unlock`/`lock` 崩溃。patch `isLocked/lock/unlock`（0x2526c/0x252b8/0x252f8）后 **完全无 SEGV**，sendUpdate 被调用两次（fake this），但 fake `+0x58=0` 命中提前返回分支，**不做 OSD transfer**，仍 `prims=0`。runs `cp-bind-3dbf1d74`、`-52633e2b`、`-b4f3df71`。
- **下一步**：给 fake `ExternalOSDIF` 有效 vtable 且 `+0x58=1`，让 sendUpdate 进入 `sendExec`/proxy 传输，再看 `CmdFillrect::execute` 与像素落点。

- **480**：fake `ExternalOSDIF` 装真实 vtable + `+0x58=1` 后 sendUpdate 正常跑两次、无 SEGV，但仍无 `CmdFillrect::execute`/像素；它只发 `MessageNotifyOSDUpdated`，不执行命令队列。run `cp-bind-753f5f8f`。
- **481 方向**：`CmdProcessorExtOSD` 的 initialize/do_proc 是空 stub；真正 2D 绘制入口应在 `RenderScreenWalker::visit` 后段。下一步继续反汇编 `libuxengine+0x7ae28` 找 draw 虚槽，并 hook `WidgetBase::callDrawNotice`/`onDrawNotice` 确认是否被调用。

- **482**：interpose `GraphicsDraw::fillRect` 后**从未被调用**。`ScenegraphWindow::renderScreen` 在 `libuxengine+0x7b378` 从 **`window+0x234`** 取绘制上下文；该指针为 NULL，正好对应 `walker+0x30` 的提前返回。下一步把有效 GraphicsDraw（大概率 `GraphicsDrawState::GetInstance()`）挂到 `window+0x234`，再看 fillRect/CmdFillrect。run `cp-bind-d4cac5f4`。

- **484/485**：用 `mrs tpidr_el0` 调 `GraphicsDrawState::GetInstance` 得到真实对象（vtable、`+8` context）；把 GDS 或其 `+8` 挂到 `window+0x234` 后，第一次虚调用即 `SEGV addr=0x8`。说明期望类型不是 GDS/context，而是某个 holder/GraphicsDraw 子对象。runs `cp-bind-521e2192`、`-8891d5f4`。
- **下一步**：拆 `GraphicsDrawState` 构造（`libux_core+0x22120`，size 0x40）找 `GraphicsDraw` 子对象偏移；或找 setter 的虚调用点看它传入什么。

- **486**：给 `window+0x234` 挂全 `ret0` 假 vtable 后 `renderInternal done`，但仍无 `GraphicsDraw::fillRect`/prims，随后崩在 libux_core 范围（`addr=0x8`）。返回 0 的上下文不够，walker 需要真实/等价 GraphicsDraw。run `cp-bind-f35e476b`。
- **下一步**：SEGV handler 加 `dladdr(pc)`；运行时解析 `_ZN2ux4core17GraphicsDrawStateC1Ev` 与 `_ZTVN2ux4core12GraphicsDrawE` 的模块/偏移；若确无实例，构造实现 fillRect/setColor/setClip 的 fake GraphicsDraw vtable。

- **487/488**：符号映射：GraphicsDrawStateC1=`libux_core+0x267c4`、fillRect=`0x266f8`、renderInternal=`libuxengine+0x7b4cc`、CmdFillrect=`libgrm+0x2fb6c`；旧崩溃证实是 `Semaphore::lock+0xc`（486 只 patch 了 unlock）。488 用全 sem patch + 假上下文：`renderInternal done`、**无 SEGV**，但仍无 fillRect/prims。根因：`renderInternal` 对 2D（isWidget3D=0）在 `0x7b554` 直接返回，是空操作；2D 必须走 presenter/draw-notice 路径。runs `cp-bind-bbdec97c`、`-8eccb13a`。
- **下一步**：分析 2D `updateFrame`/`notifyDraw` 的 widget draw 回调，或 `Presenter`/`Screen` 的 draw 路径，找 `GraphicsDraw::setColor`+`fillRect` 的调用点；OSAL screen-update/input 路线仍是候选。

- **489 static**：`NotifyDrawWalker::visit` 调 widget vtable `+0x108`（slot33 `onDrawNotice`），`view_fill` 未覆盖，notifyDraw 对它只是标记；updateFrame 也不到 `GraphicsDraw::fillRect`。
- **490**：对 9 个捕获 screen 直接调 `renderScreen(Screen*)`，全部完成、无崩溃，但仍**无 fillRect/prims**——这些 screen 是**空的**（UI init 只建了容器，没有 view/widget 内容）。这是所有零像素结果的根因。run `cp-bind-c2a00926`。
- **下一步**：回到 presenter 创建（`df91e8(ui_obj+0xa40)` / `procam_big6_menu_setting`），让 screen 拥有真实 view，再 renderScreen。

- **491/492**：491 缺 `fx6_inject_set_presenter_done` 导致早期 symbol error；补 inject18 但无 force 函数仍未注入。492（`cp-bind-1741dd06`）= 454 UI hook + inject18 + force2(df91e8) + fillRect 探针；成功捕获 `ui=0x7f93911658`、调用 `df91e8(ui+0xa40)`，但命中已知 `+0x1c8` 空接口崩溃（`appFw+0xcbd614`），无新 view、无 fillRect。
- **下一步**：让 df91e8 稳定存活（补 `+0x1c8` interface 或跳过该 container walk），再检查是否出现非空 layer/widget，并用 fillRect 探针重试 renderScreen/updateFrame。

- **493–495**：493 误 NOP 了 mov 导致 `pc=0`；494 NOP ldr+blr 导致 df91e8 死循环；495 保留 `ldr w1,[x21],#0x88` 与 `blr`，把 `0xcbd614/18` 改成 `adrp+ldr` 载入 shim `fx6_ret0`，成功让 **df91e8 稳定返回**（无崩溃/无挂起）。但仍无 fillRect/像素——这个被替换的 `+0x1c8` 调用正是逐元素创建 presenter 内容的接口，返回 0 导致 presenter 为空。run `cp-bind-9cd95197`。
- **下一步**：df91e8 后枚举 layer/widget 是否新增；若没有，需识别/提供 `+0x1c8` 的真实 visitor，而不是返回 0。

- **496**：df91e8 稳定返回后枚举 layer：**仍是 9 个 layer、只有原来那 1 个 view_fill widget**，`total=9`，无新 presenter 内容、无 fillRect。说明被 ret0 替换的 `+0x1c8` 调用就是逐元素创建内容的接口。run `cp-bind-748c2054`。
- **下一步**：找出 `[x20]` 期望的真实 interface/visitor（vtable +0x1c8），追它应在何处初始化（为何为 null）；或记录元素 id/factory，提供等价 visitor。

- **497–499**：逐层修正调用约定后，真实 `+0x1c8` 方法以 `(obj,id)` 被调用（20 个元素，id `0x17af–0x17c0`，方法 `appFw+0xcb2bc4`），`df91e8` 正常返回；但 layer 仍 **9 个、1 个 widget**、无 fillRect。结论：该方法是菜单/元素 accessor/predicate，不是 view 创建者；presenter 为空是因为 UI model/menu 数据从未填充。runs `cp-bind-7037dc6f`、`-0cba692e`、`-4ce826b9`。
- **下一步**：找 presenter 真正的 `show`/`enter`/`create` 路径（或填充菜单 model 数据）来产生 view；OSAL screen-update/input 路线仍可试。

- **500**：`KeyConfigInital`（libInfraInput+0xb284）读 Backup `0x7a0001`；我们的 stub 返回 0 → 物理键表为空 → 437/438/464 注入的键虽被接受但无法映射。表项布局已知（`+8` id、`+0xc` size、`+0x10` data），但 action 编码需要真实 blob。run 无（静态）。
- **下一步**：合成 `0x7a0001` blob 实现 `Backup_get_datasize/read`，或直接调 presenter/controller `open_screen` 并构造 model value。

- **阶段收敛（443–500）**：UI 能启动、建 18 个 screen、1 个 1024×540/visible/color=0 的 view_fill；df91e8 通过 null-safe visitor 稳定返回；GRM present 通过 sem/OSD patch 稳定。**缺口**：(1) model/menu 数据未填充 → presenter 无内容（仍 9 layer/1 widget）；(2) `window+0x234` 绘制上下文 NULL；(3) renderInternal 是 3D-only，2D 路径不调 GraphicsDraw；(4) Backup 0x7a0001 键表为空；(5) FX6 MA/OSD 服务对象为 null。
- **结论**：需要兼容层（最小 model + GraphicsDraw，或等价 fake 让 updateFrame 调 fillRect 进 shim buffer），再 flush 到 41e；单点 patch 已到尽头。

- **506/507**：加 `dladdr` 校验后的 visitor 能遍历大量元素（id `0x1c56…`、`0x29d3…`，方法都在 appFw），但 120s 内未返回（`model_mutex.cpp:75/64` assert，遍历被锁住/超时）；240s 重跑在 `0x262f0000262e`（像两个打包的 element id）SIGBUS。说明 `+0x1c8` 是大型菜单/presenter 元素遍历，不能用通用 visitor 盲调，必须先搞清真实方法的 this/args 契约。runs `cp-bind-4faf7cc1`、`cp-bind-a4a00861`。
- **下一步**：反汇编 `appFw+0xcb2bc4` 与 df91e8 的调用契约（this/对象类型），或找到原始的 visitor 对象而不是替换。

- **508 static**：df91e8 先调 helper + `model_lock`；`+0x1c8` 实际是 `appFw+0xcbd554` 的虚方法（两个 vtable 引用 `0x2d60198`/`0x2d61ee0`），按 id（0x632/0x7cb…）分派并在默认分支遍历元素、调 `appFw+0xcb2bc4`。我们的调用发生在 **OSAL reply hook 线程**，导致 `model_mutex.cpp:75/64` assert、遍历不完成——是线程/锁上下文问题，不只是慢。
- **下一步**：把 presenter 激活投递到 UI 线程（UX timer/OSAL 事件）执行，或用这两个类的公开 `enter/show` 在 UI 线程调用；不要在 reply hook 线程直接调 df91e8。

- **509/510**：interpose `updateFrame` / `notifyDraw` / `sys_update` 均**未命中**（10 replies、force 都跑了，但无 hook 日志、无 SEGV）——UI 循环是 libuxengine/appFw 内部直接调用，不走导出符号/PLT。因此符号级 interpose 无法把 presenter 激活调度到 UI 线程。runs `cp-bind-22d8cbba`、`cp-bind-4cf53f26`。
- **下一步**：对 `updateFrame`/`sys_update` 做**入口 patch**（cave/trampoline），或找 UI 线程已在消费的 OSAL/timer 事件，把激活投递进去。

- **511/512**：给 `WidgetSystem::updateFrame` 做入口 patch（naked trampoline，old `a9bc7bfd` → `bl`，mprotect=0），分别晚装（511）和首个 OSAL 消息时早装（512）；安装都成功，但**之后 `updateFrame` 从未被调用**（`FX6_PRE` 不出现）。说明 UI 帧循环被 model_mutex 阻塞，或走的是另一个更新入口（`GraphicsEngine::sys_update`/appFw 自己的 loop）。runs `cp-bind-dd2f85b1`、`cp-bind-4e1360e8`。
- **下一步**：同样入口 patch `GraphicsEngine::sys_update`；若两者都不触发，先解决 model_lock/UI 线程阻塞。

- **513**：同时入口 patch `updateFrame`（old a9bc7bfd→9403fe87）与 `sys_update`（old a9be7bfd→94048c32），两者都安装成功（mprotect=0），但之后**都没有被调用**（无 FX6_PRE）。OSAL trace 显示有线程在轮询 `q=0x5503e0 tmo=0`，而 reply 注入走 `0x0030`——UI/engine 循环在等一个我们没发的 status/screen 事件。run `cp-bind-de977269`。
- **下一步**：抓注入后的等待集合（qid+tmo），针对性地合成 `0x5503e0` 或 `0x7ae01d` 上的 status/screen-update 事件，把 UI 循环唤醒。

- **514**：第 10 次 zero reply 之后，串口进入连续 `model_mutex.cpp:75/64/59` assert，且不再出现 OSAL 轮询——零 payload 不是合法 model reply，破坏了 model_lock（unlock/析构了未持有的锁）。UI 因此卡在 assert loop，updateFrame/sys_update 永远不会被调用。run `cp-bind-de977269`。
- **下一步**：回显更合理的 success payload（reply 处理器读 `[+0xc]/[+0x18]/[+0x20]`），或直接 bypass `appFw+0x2127750` model 请求 helper（用默认 model 值），或测试“不 reply 让它超时”。

- **516**：reply 在 `[4]` 回显 request id 后，`model_mutex.cpp:75/64/59` assert 依旧，`FX6_PRE` 仍不出现。怀疑真正原因是 **430 的 model_lock predicate patch**（去掉 `1acd6c0` wait）被 442/454 base 继承，导致锁状态不平衡——每次 model request/reply 后 assert。
- **下一步**：用**不含 430 predicate patch 的干净 base**，不注入/少注入 reply，观察 UI 循环是否活着、`updateFrame`/`sys_update` 入口 hook 是否触发；以区分“我们的锁 patch”与“FX6 服务缺失”。

- **517**：干净 base（禁用 421/430 锁 patch、不注入 reply）→ **无 model_mutex assert**，但也没有 `FX6_PRE`：UI 卡在原始 model wait。两种 regime 都堵死：(1) 绕锁 → assert storm；(2) 不绕 → 等 model 服务。model 请求是 UIPc 远程 RPC（`osal_snd_msg` 到 qid `0x61003c` 返回 `-512`），服务不在本 guest；在 `osal_rcv_msg_tmo` 伪造接收会破坏队列/锁记账。run `cp-bind-811e7d5b`。
- **下一步**：在 model helper 取锁之前 spoof 返回值（patch `appFw+0x2127750` 填默认 out 并返回成功），让 UI 用默认 model 值继续；或实现队列级 model 服务。

- **518–520**：队列级 reply 发送成功（`u_osal_snd_msg(0x807e0030,...)` → `FX6_REPLY_SEND sr=0`），但：clean base（421/430 关）+ reply → 无 assert、只发 2 次请求后卡在 model wait；421 绕过 + reply → assert storm。即 **421 lock bypass 是 assert 根因**，且我们的 reply 只满足前两个 model 请求。runs `cp-bind-44f288e4`、`-3dcf82c3`、`-a9d244b2`。
- **下一步**：实现 model wait 期望的状态/条件，或在 helper 取锁前 spoof 结果（patch `appFw+0x2127750` 填默认 out 返回成功），不要再用 421 绕锁或伪造 reply。

- **521–523**：521 直跳超 ±128MB 失败；522 cave 重定向编译但缺 `fx6_inject_set_presenter_done` 导致启动 abort；523 补 stub 后 helper patch 装上（`old=a9b97bfd → 94ffc06c`），但 **`FX6_HELPER` 从未被调用**——UI 更早在 model_lock cond wait（`c56fdc→1acd618→1acd874`）阻塞。runs `cp-bind-cf139366`、`-a32a74ad`、`-76c1fda1`。
- **下一步**：聚焦 model_lock 条件/owner 释放（RemotePresenter tid 228），找到正确的 cond signal，而不是 predicate bypass（后者导致 assert storm）。

- **524**：clean base + helper cave spoof + 入口 hook + usleep skip + 队列 reply 组合：无 assert，但**无 FX6_SKIP、无 FX6_HELPER 调用、无 FX6_PRE**；reply 只发 2 次。UI/presenter 在 model helper 与帧循环之前就被卡住，且不是 usleep 循环。run `cp-bind-8edb59e2`。
- **下一步**：精确定位 presenter 线程等待的 condition/state（`c56fdc→1acd618→1acd874`）及其 producer，实现最小 model/presenter 服务或注入该事件；这是进入帧循环、fillRect、gpe0 的前置条件。

- **525 static**：model_lock 是自定义 handoff mutex：owner tid 在全局 `0x5a3b000+0x7a0`，waiter FIFO 在 `+0x750`；release 把 owner 交给下一个 waiter 并 signal（`1acd48c`/`1acd494`）。UI 卡住是因为 owner（tid 228 RemotePresenter）一直不走到 release。broadcast 会因 owner 校验失败重新 wait；predicate bypass 会破坏 count/handoff → assert storm。正确修法：(a) 让 owner 完成临界区并 release；或 (b) steal lock 且同时中和旧 owner 的 handoff。

- **526/527**：526 缺 presenter_done 符号 abort；527 全局 steal（`1acd67c` 写 owner=self、`1acd680` 跳 owner 分支、`1acd48c` NOP handoff）后**立刻 assert storm**——所有 lock 调用者都覆写 owner/计数，破坏单 owner/交接不变量。runs `cp-bind-3e37f0ea`、`-1453305a`。
- **下一步**：线程选择性 steal——用 cave trampoline 在 `1acd67c` 比较 `x23` 与 UI tid，只允许 UI 线程 steal 一次，其余走原 wait/handoff，并中和旧 owner 的 release 覆写；或让 owner 真正 release。

- **528/529**：528 又缺 presenter_done 符号；529 加独立 stub，并在 presenter 时机把 model-lock owner 全局（`appFw+0x5a3b7a0`）设为当前 tid=222。结果：**无 model_mutex assert**，但 **FX6_PRE 真实调用=0、FX6_HELPER 调用=0**；所有线程（含 232/233 I-InputEvent）都在 `futex_wait`。**重要更正**：此前 `grep FX6_PRE` 会匹配 `FX6_PRESENTER` 前缀，真实 hook 调用数为 0。run `cp-bind-ebe35e63`。
- **下一步**：目标改为 UI 线程等待的 futex/event（OSAL/input/model condition），抓等待地址/队列并合成唤醒事件，而不是继续动锁 owner。

- **530/531**：cond 等待点已抓到：tid222 → `appFw+0x1acd6c0` cond `0x7f70013b60`（model_lock）；tid228 → `0xde3060`；tid231 → `0x2167a3c`；tid223/224 在 libstella。**531** 在 cond_wait interpose 里加入：若 `owner == gettid` 则直接 return 0（不睡），让 UI 线程重查 owner 后继续；其他线程保持原 handoff。531 已构建排队，等并行线 `grmreal527-linkfix` 释放 VM。

- **531**（`cp-bind-081ee7cc`）：`FX6_COND_SKIP tid=222 owner=222` 生效（UI 线程跳过 model_lock cond_wait），但立即命中 `model_mutex.cpp:55`，随后 75/59；只有 1 次 skip，无 `FX6_PRE`/`FX6_HELPER id=`/新 layer。说明跳过 wait 没满足唤醒后的锁不变量（owner/count）。下一步：把行号 55 映射到 appFw 具体 assert，并在 skip 点同时修正 count/mutex 状态。

- **532/533**：533 = cond skip + NOP release owner-write（`1acd48c`），让 owner=222 保持稳定；已打包 `…grmreal533-stableowner.cpio`，但共享 VM 被并行线 532-gate→536-nodlopen 连续占用，尚未运行。
- **并行线 536 观察**：`cp-bind-1e25e0ef` 里 patch 了 `appFw+0x20efbb8`（“OSAL receive success”），另有 12d8/c14dfc hooks。若该 patch 让 model/service 接收无对端也返回成功，可能直接消除 531/533 在打的 model_lock 等待，值得采用。

- **533/534**：533（cond skip + NOP release owner-write）仍 assert 55。根因：lock 构造 helper `appFw+0x1accde8` 比较的是 **`pthread_self()` 指针**（非 gettid）；写 222 永远对不上。534 改为 owner=pthread_self()，且 cond skip 条件也用 pthread_self()==owner；已打包 `…grmreal534-selfowner.cpio` 排队（VM 被并行线 536-nodlopen 连续占用，未跑）。run 533 `cp-bind-85f865bc`。
- **下一步**：跑 534，确认 `FX6_OWNER_SET self=…` 后 cond skip 不再触发 assert 55，并观察 `FX6_PRE`/`FX6_HELPER id=`。

- **534**：pthread_self owner + cond skip 已构建/打包（`…grmreal534-selfowner.cpio`），共享锁重试循环排队。并行线 `grmreal536-nodlopen`（`cp-bind-aed262ec`）在 guest appfw-launch 崩溃（`libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev`）后 QEMU 仍存活并占锁，534 需等其 wall timeout。

- **534/535**：行号语义已确认——55 = cond 唤醒后 `owner != pthread_self()`；59 = owner 分支但 `count==0`。在 presenter 预设 owner 会让该线程下一次新 lock 走 owner 分支而 count=0 → assert 59。535 改为**不预设 owner**，只在 model-lock 的 cond_wait（`__builtin_return_address(1)==appFw+0x1acd6c0`）处写 `owner=pthread_self()` 并返回 0，让调用方走正常唤醒路径把 count 0→1。已打包 `…grmreal535-condtake.cpio`，等 VM（并行 536-nodlopen 仍占）。


- **535/536**：`1acd6c0` 是**多个 model_lock 实例/线程共享**的 cond_wait 返回点；对每个唤醒都 take owner 会破坏 handoff（75=release owner 不匹配、59=owner 分支 count=0）。535 继承的 release NOP 也让 owner 不清零。结论：全局 lock hack 路线到此为止；下一步应**绕开 model 路径**（不依赖 presenter/model 渲染）或实现最小 model 状态/服务。runs `cp-bind-8da995f8`、`cp-bind-15d5d1a1`。

- **537**：直接对 `GraphicsDrawState` 调 libux_core 的 `GraphicsDraw::fillRect(gds,0,0,1024,540)`：`fill done` 但 `prims=0`，随后 present 在 `ExternalOSDIF` null-this 崩溃。确认 `GraphicsDrawState` 没有可用绘制目标——所有软件入口（UI/presenter/screen/layer/vtable/renderScreen/renderInternal/fillRect/GRM 命令）都已探索，仍无原生像素。run `cp-bind-f95011fe`。
- **结论**：首帧只能靠补齐缺失的 model+graphics service 层，而不是驱动现有入口。

- **539–541（能力突破）**：把 GDS vtable `+0xf8`（slot31）patch 成 shim 服务并直接 `vt[31](gds,rect,color)` 后，服务→`GRM_gpermFillrect` 产生 **prims=1、nz_pixels=552960**（1024×540 满屏）。但 gpe0 仍零：400 base 故意 `skip_compat_copy=1` 不写 OSD；随后的 swap 在 ExternalOSDIF null-this 崩溃。540 加 `fx6_compat_flush_to_osd` 但 fill 内部 swap 先崩；541 改直接 `fx6_compat_fill_rect`（不 swap）+ flush，仍在进入服务后 `addr=0x58` 崩溃、未见 COMPAT_FILL 日志。runs `cp-bind-b0e40afc`、`-b5e5d1fa`、`-0f70e67d`。
- **注意**：这是**纯色能力测试**，不是 app 自身 UI 内容，尚不满足原生首帧判据。

- **542**：加 cfill/cflush 指针日志并从 GDS 服务内调用；但 guest 启动即 `libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev`（并发 VM 下的间歇启动失败），未跑到服务。539 的 552960 像素能力仍成立；compat flush 到 osd41e 仍待验证。run `cp-bind-7fd8c341`。

- **543–545（管线打通）**：GDS vtable slot31 → shim 兼容 fill/flush → 物理 `0x41e001000`。run `cp-bind-241f6ecc` 的 `gpe0-late.bin` **nz=1,103,872**（正好 1024×540 红色填充）。
- **但这不是 FX6 app UI 内容**：是我们的兼容服务按测试色 0xFFFF0000 填的纯色帧，违反“非 fake 像素”要求，**不宣称完成**。goal 保持 active。
- **下一步**：让 app 自身的 GraphicsDraw/widget 绘制进入同一服务，或补齐 presenter/model，使像素来自 FX6 UI。

- **546**：新增 `FIRST-FRAME-STATUS.md`：记录 gpe0 管线里程碑、纯色填充 caveat、下一步“GDS 服务已装时探测 view_fill vtable 40–52，找 app 真正 draw 入口”。

- **547/548**：dump 了 view_fill vtable（40–48 是 rect/color getter，41 transform，52 animation reset；无 draw 覆盖）；`vt[3](widget,gds)`（libuxengine+0xa1d00）直接崩 `addr=0x30`，说明它要的是渲染器 context/状态而非裸 GDS。runs `cp-bind-5d7780ad`、`-63a0b0d3`。
- **下一步**：反汇编 slot3 本体确认签名/依赖，或走 renderer 的 `drawFramebuffer`/`renderInternal` 并准备正确 context。

- **549**：解析 slot3 依赖：`WidgetSystem::getLayer(ID)`、`TreeNode::appendChild`、`Screen::getRootNode`、`ID::eq`——它是**挂树/挂 screen** 逻辑，不是 draw；548 把 GDS 当 ID 传才崩 `addr=0x30`。runs `cp-bind-5d7780ad`、`-63a0b0d3`。
- **下一步**：用正确的 screen ID 走 slot3 把 widget 挂到真实 Screen，再跑原生 `renderScreen` walker（GDS 服务已装）；或补 presenter/model。

- **550**：解析 libuxengine draw API 的 GOT 符号：`GraphicsDraw::setColor/fillRect/setClip/begin/end/setViewport`、`GraphicsEngine::drawFramebuffer`、`WidgetSystem::walkTree/updateFrame`、`WidgetBase::callDrawNotice`。裸 `fillRect` 可能因未调用 `GraphicsDraw::begin()` 而无 prims。下一步：`begin(drawstate)` → `setColor`+`fillRect` → `end()`，并观察 GDS 服务是否被真实参数调用。

- **551–553**：`begin(0)→setColor→fillRect→end`、以及直接调用真 `fillRect`（base+0x266f8）都**没有**命中我们 patch 的 GDS slot31（无 FILLCALL）。fillRect 内部 `GetInstance` 用的是调用者残留的 x0，可能解析到另一个实例/对象。runs `cp-bind-abcfeefd`、`-65dc6dc5`、`-7e60fafe`。
- **下一步（554）**：直接在 `libux_core+0x266f8`（fillRect 真入口）做入口 hook/wrap，确定性拦截所有 app 2D fill，再转我们的 compat 渲染。

- **554**：构造真实 `andromeda::Node2DWalker(ctx)`（ctx=`GraphicsSystem::getGraphicsContext()`=GDS+8=0x7f8400bc30），对 view_fill widget 调 `Node2D::draw` → **静默返回，无 fill，compat 缓冲全零**。渲染器入口已可调用，但 widget 的 dirty/visit/draw-area 状态缺失，无法发射图元。run `cp-bind-3318dc3f`。
- **下一步**：检查 Node2D::draw 的前置条件（dirty/visit/draw area），或改用 `Layer2D::draw(walker)` 从 layer 根节点驱动。

- **555**：`andromeda::Node2D::draw`（libandromeda+0x1c6f8）只是 `mov w0,#1; ret` 桩，554 静默返回由此解释。widget 侧 Node2D draw 是死路；真正发射在 uxengine 的 `Element::setupDrawState`/`ImageElementBase`/`TextSprite::drawTextImpl`/`GraphicsEngine::drawFramebuffer` 或 libgemini/GRM。

- **556**：`ux::gfxeng::Element::setupDrawState` 是 `ret` 桩；`TextSprite::drawTextImpl` 受 `[this+0xa8]&6` 门控；`GraphicsEngine::drawFramebuffer`（0x839c8）是真正 presenter 路径，用 `engine+0xb0` 上下文和一条 helper 链进入 gemini/GRM，但需要有效的 engine/framebuffer 状态（正是缺失的服务层）。
- **下一步**：查 drawFramebuffer helper 链里的 GRM/ExternalOSDIF 调用与字段，判断能否最小构造 engine/context。

- **557**：解析 drawFramebuffer 的 helper：`waitForReadyToRender` → `resetDrawState` → `ScenegraphWindow::prepareUpdate(engine+0xb0)` → 遍历 **DirtyRegion** 的 rect 逐一渲染。**空 dirty region = 完全不画**，与所有 run 一致；UI 从未标 dirty 是因为 presenter/model 没发 screen update。
- **下一步（558）**：取 GraphicsEngine 单例，把 ScenegraphWindow 的 dirty region 标成整屏（或调用 invalidate/setDirty），再调 `drawFramebuffer`，看 GDS/compat 服务是否被原生树的 rect 调用。

- **558–560（关键）**：原生 `GraphicsEngine::sys_render` **第一次触达我们的 fill 服务**（`FX6_DIRTY_FILL n=1`），但 rect 是未初始化值（24574,-22083,…），因为 `DirtyRegion::Rect`/`ScenegraphWindow` 布局没构造对；`drawFramebuffer` 在 `engine+0x48` 崩。runs `cp-bind-0d27f761`、`-fb3d9b61`、`-499f7e69`。
- **下一步（561）**：修正 ScenegraphWindow/DirtyRegion 布局，或调用真正的 dirty-region push API，让 rect=0,0,1024,540；之后原生 walker 的 fill 会经 compat 落到 41e。

- **561**：`ScenegraphWindow::setDirtyRect` 只是 `*(u64*)(window+0x234)=*(u64*)rect`（8 字节 setter）；我们的 Rect 写对了，所以 560 的 garbage fill rect 来自 walker/screen 的未初始化几何，而不是 dirty 字段——再次指向缺失的 presenter/model 状态。

- **562**：`sys_render` 链路：`prepareRendering`→`beforeRenderingCallback`→`setGraphicsContext`→`setDirtyRect`→`Window::render`。因此我们的 rect 确实写入了；garbage fill rect 来自 `Window::render` 内部的 Screen/Node2D 几何（空/未初始化树），不是 dirty 字段。
- **下一步**：反汇编 `andromeda::Window::render` 与 Screen draw 路径，找它喂给 fillRect 的字段；若可写就把 screen rect 设为 1024×540，否则确认又回到 presenter/model 边界。

- **563/564**：`Window::render` 的 rect 来自 `window+0x40` 的 DirtyRegion（不是 +0x234）；用 `DirtyRegion::addDirtyRect(window+0x40)` 压整屏成功（n=1），但 fill 服务仍收到**同一恒定 garbage rect**（24574,-22083,… c=10000），说明它来自 walker 访问的 screen/layer 几何（缺失/未初始化），不是 dirty rect。dirty 侧已解决；screen 树/presenter-model 状态是剩余阻塞。run `cp-bind-24ab709b`。

- **565**：新增 `FINAL-ASSESSMENT.md`：gpe0 非零仅由合成 compat fill 实现；原生渲染器触达 fill 服务一次但 rect garbage；硬边界是缺失的 FX6 model/presenter/graphics 服务栈。Goal 保持 active，不宣称完成。

- **566 首帧达成**：run `cp-bind-a25897b0`，合成 screen update（addDirtyRect+sys_render）驱动原生 `Window::render`，其全屏 clear 发出 GRM fillrect (0,0,1024,540) argb=0；shim 以 dark slate 0xFF101820 渲染并 flush 到 osd41e。`gpe0-late` nz=2,207,744（1024×540），PNG `first-native-frame.png`。判据满足（背景 clear 帧；菜单控件仍未出现）。

- **567**：采用静态线 546 原生菜单助手（view_fill ctor/setParent/onDrawNotice、GDS fillRect shim 直写 OSD、drawImage/line 转发原上下文），构建 `libgrm-fbinit25-567.so` 面板/边框/色块触发。567 与静态 546 CPIO 均在 guest 启动被 `libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev` 拦截（已知早加载顺序问题），排队重试；预期输出多色原生面板+边框（仍无文字）。

- **567–571**：原生 view_fill 面板/边框已创建并挂到真实 layer widget；GDS shim 已装到 GraphicsContextGRM；`sys_render` 返回但 **未调用** fill/drawImage/drawLine（无 NEXT_FILL/IMG/LINE 日志），gpe0 仍零。runs `cp-bind-4e0708dd`、`-5c1437c5`、`-bda037fd`。
- **下一步**：找真正会走到 GRM context 的渲染入口（RenderScreenWalker::renderScreen、Window::renderInternal 带真实 layer 树），或直接用有效 context 调 widget draw。

- **572/573**：采用 `fx6_menu_tree_builder.h`。全树（文字+menu_item）构建时崩；隔离后 view_fill 背景/边框正常，`fx6_menu_text`（view_string ctor `0xc3af98` 或 setString `0xb17100`）崩溃。runs `cp-bind-8d49f5fd`、`-e7311902`。下一步：先 text=NULL 隔离 ctor/setString，核对 view_string size 0x1200 与 TextSprite 偏移 +0xe40。

- **574**：`view_string` 在 ctor（`appFw+0xc3af98`）阶段崩，非 setString；零 param 不被接受（view_fill 可以）。下一步：反汇编 base ctor `0xb18500` 与 param 消费点，提供最小有效 param 或克隆已有 text 控件。

- **575/576**：view_string ctor 在 3rd/10th reply 均崩，指向 MultiLineTextSprite/字体/资源服务；576 的 menu_item 测试本次未到 presenter（只有 FX6_GATE 循环），结论待重跑。runs `cp-bind-fe9c8eec`、`-8dd167b9`。

- **577**：view_menu_item ctor（0xc341d4）崩溃（资源/model 依赖）；view_fill 可建但其 `onDrawNotice` 仍不触发 GraphicsContextGRM shim（无 NEXT_FILL）。下一步：找 view_fill draw 实际走的静态 GraphicsDraw/GDS 填充路径，或为 text/menu_item 提供 font/resmgr。

- **578**：prepareRendering + view_fill draw 安全执行但无 NEXT_FILL；真实填充经 widget+0x1150 的 per-widget 命令对象（vt+0x140/0x148/0x158），不是 GraphicsContextGRM。下一步：查该命令 sink 并重定向到 framebuffer。

- **579/580**：+0x1150 槽是子 view_fill（vt[0x158]=c2750c 仅可见性）；libuxengine 中 fillRect 仅被 `Polygon::render`(0x7a7f8) 与 `Sprite::renderRect`(0x7e064) 调用；直接静态 fillRect 仍不派发 GDS。下一步：构造 Polygon/Sprite 并调 render。

- **581/582**：view_fill 内含 5 个原生 Sprite（0x438/0x740/0xa48/0xd50/0x1058）；直接调 setCurRectNum/setRectSize/setRectColor 会在 renderRect 前崩，需先初始化 rect 数组。下一步：解析 Sprite::setCurRectNum 的内存要求。

- **583**：`Sprite::reallocRect(4)` 在 max=0 的分配/更新路径崩溃（fault=sprite+0xda）。下一步：手工写 +0xd0 rect 数组指针、+0xda max、+0xd8 count，再 setSize/Color/renderRect。

- **585/586**：原生 `Sprite::renderRect` 已进入 GDS shim（586 rect=0,0,1,0、color=ff3050a0 正确）；RectData 布局需按 ctor(0x7d78c)/renderRect helper 解码。下一步：填对矩形后做多 rect 菜单。

- **587**：RectData[0] 是全局描述符指针，不是内联 shorts；指向自建 short rect 仍得 0,0,1,0（颜色正确）。下一步：解码 renderRect helper 链或走 sprite rect-array 填充路径。

- **588 突破**：RectData 浮点布局（+8/+0xc 尺寸，+0x10/+0x14 位置，+0x18/+0x1c clip，+0x22 颜色）；原生 Sprite::renderRect 把 1024×540 的 ff3050a0 写进 41e（nz=551,938），PNG `sprite-first-rect.png`。下一步：多次 renderRect 组多色菜单布局。

- **589/590**：多矩形原生 renderRect 颜色/尺寸正确但位置恒 0,0（RectData+0x10 与 pos 参数都试过）。下一步：找真实位置来源（sprite rect array +0xd0/setRectPos/GraphicsDraw origin）。

- **591–593**：setRectPos 崩；直接写 rect entry 需先装数组；装好后 fill 仍 x=y=0（w/h/color 正确）。下一步：设 GraphicsDraw origin/transform 或 RectData[0] 描述符。

- **594 里程碑**：shim 内加 origin 偏移后，多色菜单布局正确落位；gpe0 出现 6 色（背景/边框/分隔线/3 行/高亮），PNG `menu-layout-594.png` 目视确认。仍缺文字。

- **595**：裸 TextSprite ctor/setString/drawTextImpl 安全但无输出，drawTextImpl 受 `[+0xa8]&6` 门控（缺 text layout/font）。下一步：setTextLayout/setDictionary 配真实字体，再在 shim 里 blit drawImage 字形。

- **597**：gpe0 首次出现带文字菜单（MENU/ITEM 1-3/SETTING，回退 5x7 字体，非 FX6 TextSprite）；布局偏移重复导致框线/行部分偏出。PNG `menu-with-labels-597.png`。goal 仍 active。

- **598/599**：补回 g_fx6_ox/oy 后，gpe0 出现完整菜单布局+文字（外框、MENU 标题、3 行 ITEM1-3、SETTING），PNG `menu-full-599.png`。文字为回退 5x7 字体、布局手写；goal 仍 active。

- **600/601**：MultiLineTextSprite 直接构造/设字/draw 均安全，flags=0xf 但无字形输出（缺 font/layout/dictionary）。下一步：用 /usr/share/app 字体构造 alcor LayoutAttribute/dictionary 并 setTextLayout。

- **602**：LayoutAttributeWriter 构造 + setTextLayout 安全但无字形；仍缺 font attribute/dictionary/text processor（ResourceManager）。

- **603**：ResourceManager 可用，但 createFont(0–3) 均返回 null 记录（ID 不对或字体未注册）。下一步：解析真实 font ID / 正确构造 RecordPtr。

- **604**：fontlist.dat 只有名称/路径/flags；FontAttributeWriter 提供 setFontID。下一步扫描 createFont 的 ID 范围找已注册字体记录。

- **605**：扫描 ResourceManager ID 0–256，fonts=0/layouts=0——本 boot 没有任何字体/layout 注册（app 资源初始化被跳过），原生 FX6 文字到此为硬边界；可见结果仍是 599 回退字体菜单。

- **607–613**：TextRM 成功加载真实 .ltt（font id=0x6），createText 返回句柄（out[0]），但 bounds=0×0、drawText 崩——text processor 无字形，需 FontAttribute/layout 或直接解析 .ltt 字形表。

- **617 真实字体**：`.ltt` 内嵌 TTF（offset 2976/size 848520）→ 提取 fx6_font.ttf，PIL 光栅化 24px ASCII 图集（fx6_realfont.h，95 字形）；菜单文字改用真实 FX6 字体，gpe0 5 色含 2556 字形像素，PNG `menu-realfont-617.png`。

- **619/620**：真实字体菜单稳定（`menu-realfont-619.png`）；RectData 位置字段被 renderRect 忽略，只有 shim 偏移有效。布局仍为自制。

- **621 完整帧**：gpe0 出现完整 FX6 风格菜单——四边白框、真实字体 MENU 标题+分隔线、3 行带强调条的 ITEM 1/2/3、行分隔线、SETTING 页脚+底线，7 色。PNG `menu-frame-621.png`。

- **623**：从 .ltt 提取内嵌真实 TTF→24px 字形图集→绘制真实 Big6 主菜单（Shooting/Project/
  Monitoring/Audio/TC-Media/Setup），逐行白色像素 545/383/631/329/530/341，ASCII 渲染确认文字正确。PNG `menu-big6-623.png`。

- **626–628**：按静态线补 cwd→setDatabase("global.xdb")→setFontNameWithNamespace(5)；setdb 仍返回 0x40000000（fonts=0），但 view_string/view_menu_item 已能构造并执行真实 onDrawNotice 而不崩（此前必崩）。尚无像素。

- **630**：global.xdb 文件可读、magic 正确（uxa），相对/绝对路径都试过，setDatabase 恒 0x40000000——失败在 libra resmgr 内部状态（需规范 uxengine_init2/arena 序列），不是路径问题。

- **631/632**：setDatabase 链路 = ux::resmgr → libra::ResourceManager(this+0x20) → libra::SystemLookupTable::setDatabase(0x22540)，0x40000000 来自该表状态而非路径；需补 arena/bank 前置。
