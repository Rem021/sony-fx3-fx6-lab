# GPE 完成队列 unfetched：原语义与时序审计

2026-11-02（America/Los_Angeles）。**原代码否定“首次 `rcv` 才 fetch，因此软件完成太早被拒”的前提。** `fetch` 对应动态 ID 的领取：同步 GPE 在发送绘制命令前调用 `osal_dynamic_id(0x2a,0x82,&Q)`，内核已经把队列 `q+0x30` 写为非零；`rcv` 不设置该字段。AP103 Flush437 的真实失败条件是完成发送时这个字段为零，但**是哪一代队列、谁使其归零，现有回执未证实**。（libgpe VA `0xa398..0xa3d0、0xa7ac..0xa834`；libosal_uipc VA `0x7600、0x7980`；osal_uipc.ko `.text+0x5b28..0x5b88、0x3470..0x34b4、0x4198..0x448c`。）

因此本审计不批准“等到原 `rcv` 入口再发送”的修正。首次接收不是该门的必要条件，已释放的队列也不会因再次接收而重新领取；应先抓本次领取、完成、释放的身份与顺序。本文给出可执行的观测位置及保守交付合同，没有实现适配层修复。（osal_uipc.ko `.text+0x5b4c、0x59b0、0x5c80、0x43a4`；libgpe VA `0xa410..0xa41c`。）

## 复现、范围与地址约定

在项目根执行已有 capstone/pyelftools venv：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/gpe-completion-unfetched/audit_unfetched.py
```

退出 0，重建本目录 `unfetched-proof.json`。脚本检查四份原件 SHA256、64 条指令锚点、重定位/虚表、七组符号化分支案例，以及 AP103 候选 CPIO 中四份原件的逐字一致性；提取既有 serial/printk 回执与当前适配源哈希。分支案例是**由原指令约束的 Python 符号化计算**，没有执行原内核，也不是 QEMU 或实机测试。仅写相邻 proof JSON；没有启动 QEMU、拿运行锁、修改 runtime、原件、STATE 或 Git。

`libgpe` / `libObj` / `libosal_uipc` 地址为 ET_DYN 链接 VA，运行地址加各自加载基址。内核模块是 **ET_REL**：本文 `K+偏移` 均表示原 `osal_uipc.ko` 的 `.text+偏移`，运行 VA 必须加这份模块实际加载的 `.text` 基址；不是 Linux 内核固定 VA。proof 保存原指令字节和未链接的 relocation，避免把重定位前 `bl #当前地址` 误认成递归。

| 原件 | SHA256 |
|---|---|
| osal_uipc.ko | `6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38` |
| libosal_uipc.so | `09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3` |
| libgpe.so | `363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464` |
| libObj.so | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |

AP103-r4 receipt 指向 `runtime/ap103-r2-soft-ldec/candidate.json`，其 CPIO SHA256 为 `b6d0df66f1bb860d40a5068169dd4a83feb61d9550ca40d8f8ec9bbe54fecb21`。这四份成员与上述原件逐字一致；旧成员名 `simulation/fx3-gpe-observe-v7.so` 实际为 v24-serial102，SHA256 `ba0bc2753730bf3097fdaa2860b228dc36e99d67a02172dedf134cdbfbbc81bb`。这只核实启动输入，没有证明运行中没有其他内存写入。

方法参考 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html)，2026-11-02 查阅；该网页只支持工具用法。Sony 的队列与 GPE 语义来自上述本地原件。

## 1. 内核的确切判定

`osal_valloc_msg_wait` 在 `K+0x4500` 进入私有 `alloc_msg`（`K+0x3248`）。队列按 `QID & 0x7fff` 查找；已有节点路径 `K+0x2938`，无节点时可由 `K+0x2ee8` 建立。**有节点不等于已领取动态 ID。** 节点创建先清零，索引 `0x6000..0x7fff` 时将 `q[0]` 的 bit3 置 1（`K+0x3024..0x3034、0x3080..0x3098`）。

| 字段 | 已证实语义 | 原地址 |
|---|---|---|
| `q+0:u8` bit3 (`0x08`) | 该节点属于动态队列范围；不是“接收者正在等待” | `K+0x3080..0x3098` |
| `q+2:s16` | 已分配消息计数，分配时增加；领取扫描及释放检查使用 | `K+0x331c..0x3340、0x5854、0x59a4` |
| `q+8:u64` | 接收等待/回调链表头；`rcv` 将等待记录挂在此处 | `K+0x42c8..0x42f0` |
| `q+0x10:u64` | 消息链表头，接收可直接取已有消息 | `K+0x423c..0x425c` |
| `q+0x30:u64` | 动态队列领取者 token；零表示未领取/已释放 | `K+0x5b48..0x5b58、0x59b0、0x5c80` |
| `q+0x38:u64` | 队列锁指针 | `K+0x422c..0x4230、0x4260..0x4264` |

对本次 `QID=0x808261c0`，bit31=1、bit28..30=0，实际分支为：

```text
K+3298  tbnz w24,#31 -> 3470
K+3470  tst x24,#0x70000000
K+3474  b.ne 34b8              # 非本次分支
K+3478  ldrb w0,[x21]
K+347c  tbz w0,#3,34b8        # 非动态节点则继续分配
K+3480  ldr x0,[x21,#0x30]
K+3484  cbnz x0,34b8          # 已领取则继续分配
K+3488..3498                   # 打印 unfetched dynamic queue
K+349c                         # print_task_info
K+34a4  mov w0,#-0x3fa        # -1018
```

若调试选项 `uipc_opt` 所指结构的 `+0x17` 非零，该路径在 `K+0x34b4` `brk`，而非正常返回；既有回执显示本次走到 `-1018` 返回。错误字符串由 `K+0x3530` 的 ABS64 relocation 指向 `.rodata.str1.8+0x520`，不是凭运行日志猜出的函数位置。

精确到 `alloc_msg` 的一般门：在已通过参数及节点查找后，`(q[0]&8) && owner==0 && (!(QID&0x80000000) || !(QID&0x70000000))` 进入此诊断。非 bit31 路径见 `K+0x329c..0x32a0、0x33f8..0x33fc`；bit31 且带远端域位的路径在 `K+0x3474` 绕过这个本地检查。对 `808261c0` 简化为 **动态 bit3 已置位且 owner 为零**，没有检查 `q+8` 等待链表、是否首次接收或是否已睡眠。（`K+0x3294..0x32a4、0x33f8..0x3400、0x3470..0x34b4`。）

`libosal_uipc` 对该 QID 的 bit15=0 调用内核分配包装（VA `0x67e0、0x6860`）；原 ioctl 包装将 libc 的 `-1/errno` 还原为 OSAL 负返回码（VA `0x3e98..0x3f24`）。因此内核 `-1018`、用户态 `errno=1018` 与原 `SendDrawComp` 返回 false 相符。`libgpe+0xd6dc` 分配失败后直接走 `0xd700..0xd714` 返回 false，**没有消息被提交，也不能当作完成已交付**。

## 2. fetch 的置位与清除

GPE 的 `osal_dynamic_id(0x2a,0x82,&Q)` 通过 libosal VA `0x7600` 的 bit1 分支至 `0x7980`，调用 `u_osal_dynamic_id`；内核 ioctl `K+0x818..0x828` 保留原 flags，不添加“首接收”步骤。`0x2a` 选择普通消息动态池 `.data+0x680`（起始索引 `0x6000`，4096 项；由 `.data+0x640` 描述符数组基址加 `0x40` 取得）。（libgpe VA `0xa39c..0xa3b0`；libosal VA `0x3fb0..0x403c`；K `+0x57cc..0x57e8、0x59e8`，descriptor relocation 在 `K+0x5cf8`。）

领取选出空闲 ID 后，`K+0x5b30` 合并 module 和索引，`K+0x5b4c` **先写 `q+0x30`**，`K+0x5b54` 再给返回 Q 加 bit31，`K+0x5b64..0x5b88` 登记分配位图，然后解锁/返回。对于返回值 `0x808261c0`，owner token 为 `0x008261c0`。它不包含 TID，也不是接收次数；不能把 `q+0x30` 当一个独立的 bool fetch 标志。（`K+0x5818、0x5b28..0x5b88`。）

释放 `osal_dynamic_id(0x4a,0,(void*)Q)` 在 `K+0x5914..0x5954` 核对范围和分配位图，随后检查消息/等待状态与计数，`K+0x59b0` 清零 owner，再于 `K+0x5a00..0x5a2c` 释放位图。**发现 pending 状态的警告分支也会清零**：`K+0x5c64..0x5c80` 打印 `QID[%x] M=%d C=%d S=%d A=%d`，清零后继续释放；故不能把这条日志当作“拒绝释放、对象仍安全存活”。

`osal_rcv_msg_tmo` 的完整函数 `K+0x4198..0x448c` 只查找/必要时建立节点、取已有消息或挂等待记录、等待/超时/移除等待记录，**没有向 `q+0x30` 写领取 token**。首次调用时还没消息可以正常睡眠，已有消息也可直接取出；一个已领取但尚无接收者的队列允许原 `alloc_msg` 分配完成报文。（`K+0x423c..0x4280、0x4288..0x4304、0x4390..0x43b4`；分配门 `K+0x3480..0x3484`。）

## 3. 发起方与原硬件完成链

`libObj` 的 `grm_gpe` 名称在 VA `0x1e0231`，构造函数 `0xf4278` 使用它。原 RELATIVE relocation 将其 CmdWorker vptr 绑定到 `0x252d50`，虚表 slot `+0x18`（relocation VA `0x252d68`）指向 `0xf4348`；worker 在 `0xf4378..0xf4398` 取命令并调用该命令的 slot `+0x18`。Finish 命令对应虚表记录 `0x253770 -> 0x100dac`，在 `0x100dc0` 调用 `GpermFinish`。（proof `obj_virtual_binding` 及对应指令。）

普通 Fill/Blit 命令从 `libObj+0x100cc4 / 0x101174` 调 GPE 包装器；async 字段由上层参数决定，原包装器分别在 `libgpe+0xa474 / 0xa558` 判断。`GpermFinish+0xa83c` 构造全零 24B Flush 参数，因而 async=0，调用 `GpermFlush`。（`libgpe+0xa83c..0xa860`；libObj fill async 构造 `0x101910..0x101924`。）

| 次序 | 原行为 | 原地址 |
|---|---|---|
| 1 | 同步调用先领取本次动态完成 Q；async 非零跳过领取、source=0 | libgpe `0xa7ac..0xa7ec`，Fill `0xa474..0xa4b4`，Blit `0xa558..0xa598` |
| 2 | 16B 头 `+8` 写 Q，再提交绘制消息到原 GPE FIFO | libgpe `0xa800、0xa824、0xd814..0xd848` |
| 3 | 发起方调用 ReceiveDrawComp，等待真实完成，timeout=-1 | libgpe `0xa834 -> 0xa3d4 -> 0xd89c -> 0xd774`；`0xd7a0` |
| 4 | 原 Flush 注册 `{sequence,Q,callback,arg}` 并提交硬件命令 | libgpe `0xc7b8..0xc7dc -> 0xaf08 / 0xaf30`；`0x9f64..0x9fbc` |
| 5 | 完成线程等待原硬件中断消息的相应 indication bit，然后发 opcode5 回 Main | libgpe `0xda64..0xdb04`；`0xdac4 -> 0x13430 -> 0x14d34`，`0x14d7c、0x14db4`；`0xdafc` |
| 6 | Main 处理 opcode5，弹出 CallbackInfo，先 callback，再同步完成 status=0 | libgpe `0x9cc8..0x9cd4 -> 0xc800 -> 0xa158`；`0xa1c0..0xa1d4 -> 0xa110 -> 0xd888` |
| 7 | 发起方复制实际 4B status、释放实际消息，然后释放本次 Q | libgpe `0xd7e0..0xd80c`；`0xa410..0xa41c` |

原硬件链确实比当前适配器多出硬件 indication 和回入 FIFO 的调度，但**原程序没有要求第 3 步先于第 6 步才允许投递**。领取必须在第 2 步前完成，队列也能暂存先到的完成消息；真机 IRQ 的绝对延迟及通常是否已睡眠，本次没有实测。（领取 `K+0x5b4c`；分配门 `K+0x3480..0x3484`；接收已到消息 `K+0x423c..0x425c`。）

每次同步调用都执行 `0xa398` 的领取，再于 `0xa41c` 释放；**逻辑上是每次单独领取，底层节点与数值 ID 可以复用**，并非一个永久固定完成队列。日志出现相同 `808261c0` 不能证明同一代领取仍存活。（libgpe `0xa47c、0xa560、0xa7b4、0xa410..0xa41c`；K `+0x5820..0x589c、0x5a00..0x5a2c`。）

## 4. 当前适配器与既有失败回执

当前 v24-serial102 保留原 Main/FIFO，光栅副本把 async 置 1 并清 callback，后端 v8 不负责实际 Sony 完成。adapter 在像素提交、屏障、后验和解除映射后直接调用 callback，再对 `!async && source` 调原 `SendDrawComp(source,&status0,4)`；false 映射为 `GPE_DELIVERY`、返回 5，并设置粘滞失败。原 Main 随后对同步失败再尝试一次 4B 非零 status。（`helpers/fx3-gpe-observe-v24-serial102.c`，proof `model_completion_source`；原接口 VA `libgpe+0xd888、0xd6b0..0xd770`；原 Main `0x9cbc..0x9cc4 -> 0x9c3c..0x9c4c`。）

| 已有证据 | 观察及限制 |
|---|---|
| AP70 `ap70lcd-f61554d9/serial.log`，行 7655 | tid229 `grm_gpe` 在 `808261c0` 接收；确认接收者归属，不能确定 AP103 的领取代次。原接收接口 VA `libgpe+0xd89c`。 |
| AP103-r4 `ap103v4ldec600-71ce5752/serial.log`，行 28861 / 62162 | tid274 `grm_gpe` 已分别在 `808261c0 / 808261c1` 进入接收；它们是**按 (tid,QID) 去重的首次日志**，不是每一代接收日志。去重实现见 `helpers/ioctl-trace-v12.c:28..37、191`；原接收 VA `libgpe+0xd774、K+0x4198`。 |
| AP103-r4 serial 行 81985 / 82011；独立 printk records 2830 / 2837 | 两次 `alloc_msg ... QID[808261c0] size[4]`；print_task_info 为 `MPGRM_GPE0 pid=275`，内核返回 -1018。对应原错误门 `K+0x3488..0x34b4`。 |
| AP103-r4 serial 行 81998 / 82000 | Flush seq437 async0，`reason=8 errno=1018 result=5`。原完成发送分配入口 `libgpe+0xd6dc`，失败返回 false；与后续 Main 再试错误状态的两次分配失败相符，但缺逐事务关联 marker，不能仅按邻接行断言第二次调用者栈。 |
| AP102-r2 `ap102r2save600-e15f61fb/serial.log`，行 141573 / 141581 | 同一数值 QID 的两次 unfetched 及 MPGRM_GPE0；同样没有本代领取/释放完整日志。对应 `K+0x3488..0x34b4`。 |

上述 serial 行号采用 Python `splitlines()`，包含 CR/LF 分割；proof 为每个摘录保存原文件 SHA256、行号及原文，并另保存 AP103 已有 printk 解码记录。串口多线程输出有交错，不能将跨线程文本顺序当作严格 happens-before。

`ap103-runtime-review-v1.json` 仍明确 `overall_health_pass=false`，full600/save 未完成，第四轮 API16 恢复读回不同。静态输入逐字一致不关闭这些运行验收，也不消除运行时内存改变这一未证实因素。

## 5. 假设裁决与最小诚实下一步

**否定特定因果假设，保留实际根因未证实。** 若该同步命令按原路径成功领取且尚未释放，即使软件比原硬件更快，在调用者首次 `rcv` 前完成也会通过分配门。观测到的零 owner 更符合“本代领取丢失/已释放或状态被改”的问题类别，尚不能在提前释放、重复完成、其他线程、ID 复用或内存破坏之间定因。（GPE 领取先于发送 `0xa7b4 / 0xa824`；K 领取写入 `+0x5b4c`；错误门 `+0x3480..0x3484`；释放清零 `+0x59b0 / +0x5c80`。）

本任务要求的“证实后延迟到 fetch”条件没有成立，故没有提交该修正。只在原 `rcv` **入口**记 ready 也不可靠：入口不修改 owner，历史 `(tid,QID)` 又无法区分复用代次。等待 `rcv` **返回**再投递更会形成循环依赖。禁止补调 dynamic_id 领取这个数值 ID、手写 owner、把发送失败改成功或吞掉完成。（原 `K+0x4198..0x448c`；libgpe 等待后才释放 `0xa3f0..0xa41c`。）

`osal_stat_msgq` 不能作为只读 fetch 查询：它经 `K+0x4d44 -> 0x3160`，无节点时 `K+0x3228 -> 0x2ee8` 会创建节点；返回的是消息数、有效等待/回调数、broadcast 与 pending 回调状态，不返回 owner 或分配代次。（`K+0x3194..0x31f8`；libosal VA `0x6e08..0x6e50`。）

下一轮最小动作是**观测原领取/释放与完成状态，不先改变时序**。若后续证据确实发现合法的延期需求，交付队列必须以 `(原领取 epoch,QID,GPE sequence)` 绑定身份，状态依次 pending→sending→delivered；固定容量、有序、callback 单次、真实发送成功后才退役。达到期限或身份已释放时留下明确失败/未交付回执并停止推进，不能等待同一数值 QID 被另一代复用后误投；也不能让 adapter 返回非零触发 Main 发送另一条状态而同时保留一个延后 status0。这里是设计约束，**没有实现或验证这种队列**。（原无 generation 的 4B 接收 ABI：libgpe `0xd89c、0xd7e0..0xd80c`；原 Main 非零自动回复 `0x9c3c..0x9c4c`；原 ID 复用链 K `+0x5a00..0x5a2c`。）

## 6. 运行验证点（本次未执行）

1. **逐代领取与释放**：在原 `osal_dynamic_id` 入口/返回观测 flags、module、tid、QID、实际返回值；仅当 `0x2a` 真正返回 0 时建立观察 epoch，`0x4a` 精确结束它。抓原调用者 VA，不能只记录 numeric QID。（libgpe `0xa3b0、0xa41c`；libosal `0x75b8、0x3fb0`；K `+0x5780`。）
2. **原状态只读快照**：原 `K+0x5b4c` 写 owner 之后、`K+0x3480` 读取之前、`K+0x59b0 / 0x5c80` 清零之前，记录 queue pointer、flag、owner、计数、位图、caller/序号与 epoch；用这份模块实际 `.text`/`.bss` 绑定校验。若在适配层提供查询，应让内核在原锁/领取生命周期内观察已有节点；不能用可能创建节点的 `osal_stat_msgq`，不能在用户态猜内核指针。（查找根 `.bss+0x2640`；纯 lookup `K+0x2938`。）
3. **完整一次完成链**：SendDraw 之前记录 header+8 与 seq，`SendDrawComp` 入口/返回记录 destination、4B实际 status、tid、bool、errno；接收成功后记录真实消息和释放返回。这样才可区分“成功0后 Main误再发5”“未交付时先释放”“另线程释放”。（libgpe `0xa800、0xa824、0xd888、0xd6dc、0xd73c、0xa3f0、0xa41c`；Main `0x9c4c`。）
4. **调度反例**：在原 ID 领取仍有效的条件下覆盖“尚未进入 rcv 就完成”“接收者先等待”“数字 QID 复用”“合法发送失败”。应每代恰好消费一条真实 4B status，旧代完成绝不进入新代。前两种都应通过原 owner 门；不预设 sleep 或强制接收。（K `+0x3480..0x3484、0x423c..0x425c`；libgpe `0xd7e0..0xd80c`。）
5. **运行验收**：由独占运行链执行既有输入/截图计划，跑到原定 600s，Flush 与所有同步调用自然返回，零 unfetched/重复完成，队列计数无泄漏；另查 assert/exception/SIGABRT 与 API16 恢复逐字匹配。菜单、日期/普通设置落盘各凭原回执单独验收。本审计不关闭这些门。（同步返回 libgpe `0xa424..0xa42c`；实际既有运行限制见 supplied runtime review。）

## 明确未证实

- Flush437 的本代动态 ID 领取/释放日志、失败时原 queue pointer/owner 快照，以及使 owner 变零的实际写入者均缺失；未证明竞争、重复完成、提前释放或内存破坏中的任何一种。
- 真机中断延迟与请求线程先睡眠的统计规律未实测；静态硬件完成链只证明等 indication 的依赖。
- 未实现延迟投递、只读查询或观测补丁；本次没有运行 QEMU、相机或内核模块。
- full600、日期/普通设置保存和 AP103-r4 API16 恢复仍未验收，不能由本报告或 proof 的退出 0 代替。
