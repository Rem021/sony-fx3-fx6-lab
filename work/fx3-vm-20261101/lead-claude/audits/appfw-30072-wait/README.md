# AppFw 0x30072 与启动等待对象审计

结论：**AP77a 的 AppFw 最可能仍阻塞在处理 0x30072 所触发的 `model::model_future::wait()`，等待 `sequence_boot` 的完成通知。** 这条消息是 AppFw 自发的启动事件；处理链构造栈上的 `std::condition_variable`，把事件指针交给 boot sequence，随后等待通知。通知者的原码位于 `sequence_boot::run()+0x5c`（`2b6838c → 2aa1668`），在 boot 主体返回之后。当前 boot 线程 tid327 的 timecode 等待阻止它走到通知；正常推进还需 get-func、四任务屏障及其后的初始化。[发送/分派：`16f22a8..22b8、2380778..0794`；等待/通知：`285e3fc..e42c、2b68370..838c`；AP77a serial 行7773–7783、7963、8065–8145、21314–21320、30370–30430。]

上述**等待 API 和静态事件传递链是 A 级直接证据；当前 futex 对象归属及通知线程的对应为 B 级有约束推断**。已有快照只保存内核栈、syscall/SP/PC，没有该时刻完整的用户态栈和事件指针内存。不能把“第二条已出队”写成“第二条已处理完成”。[原生接收后探针在 `16f217c`，处理调用在 `16f2188`，其后还有分派；本轮第二条仅见 serial 行7963。]

审计日期：2026-11-01。只读原 ELF、已有 serial/printk、计数读回和观察器源码；只写本目录三个文件，未启动 QEMU、未改 runtime/STATE/原件、未操作设备。A=原指令/重定位/捕获直接证据，B=受约束推断，U=未证实。下述 VA 均为原 ELF image VA，运行地址须加各 run 的映射基址；行号为原始 `serial.log` **按 LF 分行，保留 CR/NUL**。[可复跑证明](appfw-30072-proof.json) 保存原始字节、完整选定窗口、RTTI、来源 SHA256、七轮快照及计算过程。

## 1. 发送者、时机与 payload

**A：发送者是 AppFw 主循环自身（tid289），发生在初始化返回之后、循环第一次 `processSystemMessage` 前。** `16f2250` 初始化后，`16f2298..22b0` 清零28B消息并写 type=`0x30072`，`16f22b8 → 27381b8` 指定长度 `0x1c`，尾调 `2eacc48`；后者复制 payload，`2eacd30..38` 设置固定 source=`0x830128`，`2eacd40..48` 发到 `0x5503e0`。serial 行7773–7781 的实际发送栈有返回地址 `2eacd4c ← 16f22bc ← 16f0144`，行7782的独立发送记录为：

```text
tid=289  target=0x5503e0  source=0x830128  bytes=28
72000300000000000000000000000000000000000000000000000000
```

**A：`0x830128` 是该内部消息封装固定写入的来源标记，不能据此把发送者叫作某个外部服务或 sequence 线程。** AppFw 自发30072和后台timer代理tid205发150000都使用它；两个实际发送者可由线程号与调用栈区分。[`2eacd30..38`；serial 行7763–7772、7773–7783。] 本条 payload 为 type 后24字节全零，没有 boot 句柄、服务地址或 timecode 数据。[`16f2298..22b0`；serial 行7782；脚本逐字断言。]

## 2. 分派入口与原处理函数

**A：0x30072 进入普通内部消息分派，最终到 `scr0039_boot_controller` 的消息处理虚函数。** 路径为：

```text
AppFw 16f2694 → 16f2098 接收队列5503e0
  16f217c [实际接收成功观测点] → 16f2188 → 16f1d08
    检查source830128；16f1e24..e40复制为内部category=1
  16f2590..25b4 → 16f2534..2540 → 219209c
    → 2192274 → 21916b0
    → 2191910..191c 调 controller vtable+88
    → 2380778 比较message+8==30072 → 2380794 → 237fe28
      原日志字符串3135aa0 = "process_power_on"
    → 2380700 → 285f3b4 → 285f41c → 285dc98
```

虚表header=`455b220`、slot=`455b2b8`，原RTTI=`23scr0039_boot_controller`，slot值=`2380778`。[proof.vtables及上述VA原码。] **运行中确实进入此路径**：出队在serial行7963；其后的同线程30184通知栈（行8065–8079）含 `2191920 ← 2380798 ← 2380704 ← 285f420 ← 285e3f8`。这里是对同线程实际调用链的证据，没有将邻近其他线程的timer帧当成handler栈。

**A：`GraphicsEngine::processSystemMessage` 返回两次不代表30072处理结束。** 它的调用点是 `16f22c8`；返回探针 `16f22cc` 的两次样本在serial行7784、7952，第二条出队在其后行7963。30072业务处理由另一接收/分派路径进入，末次停在内部等待；不要将“processSystemMessage返回2次”改写成“30072返回”。[上述VA及三个serial位置；原观察器 `helpers/fx3-ui-gate-v1.c:41,59` 绑定id11到 `16f217c`。]

## 3. 等待 API、对象与 futex 地址

**A：原处理路径使用自定义 `model_future` 加条件变量，当前 syscall 确实属于 `pthread_cond_wait`。** `285dcec` 将 `x19=本帧FP+0x108`；`285e3fc..e400` 在 `x19+8` 构造 `std::condition_variable`，`285e408..e40c → 2aa1648` 将事件组织为：

| 对象 | 原布局/操作 |
|---|---|
| event+0 | 完成字节；`2aa164c` 清0，`2aa1688..168c` 置1 |
| event+4 | 结果整数；`2aa1650` 清0；带结果版本 `2aa16b4..16e4` 可写 |
| event+8 | `std::condition_variable`；`285e400` 构造，`2aa16a4..16b0` notify_one |
| model_future | 三个指针 `{event, event+4, event+8}`；`2aa1654..165c` 写入 |

`285e428..e42c → 2aa222c` 的原日志字符串 `3801f18` 为 `void model::model_future::wait()`，文件串 `3801ea0` 为 `model_mutex.cpp`。`2aa225c` 获取使用全局mutex `8e29cf0` 的unique_lock，检查事件字节，`2aa228c..2294` 调导入的 `std::condition_variable::wait(unique_lock&)`。原libstdc++实现 `b3600..b361c` 转调pthread条件等待；其PLT `8a780` 绑定 `pthread_cond_wait`。[proof.blocks/checked_instructions/strings。]

**U：本轮尚不能区分model_future内部的简单等待与协作调度等待分支。** `2aa2284..2288` 的线程上下文标志可选择协作分支，后者在 `2aa23a4` 也等待同一个event cv，另有 `2aa2464` 等待堆上的线程协调cv。保存的syscall没有调用者LR；栈地址拟合支持event cv，仍须在libstdc++入口记录LR排除其他分支。不能只因为看到“future”就省略这层线程协调。[完整 `2aa222c..2518` 原码。]

**A：AP77a三个快照都在同一条件等待的futex syscall。** serial行14065、28239、41393均为：

```text
98 0x7f483dc418 0x80 0x0 0x0 0x0 0x7f483de150 0x7f483dc170 0x7f9ce775f0
```

这里98是十进制syscall号，op=`0x80`为本进程私有FUTEX_WAIT，expected=0、timeout=NULL；SP=`7f483dc170`，PC=`7f9ce775f0`。该run的libpthread映射基址在serial行9551，为 `7f9ce6a000`，故PC相对=`d5f0`，正是原 `pthread_cond_wait` 中 `d5ec svc #0` 的下一条指令。内核栈为 `futex_wait_queue_me → futex_wait → do_futex → SyS_futex`（行14066–14072等）。这排除了把本次阻塞归到 `pthread_mutex_lock` 的内部慢路径、信号量或OSAL收包；上层模型名字虽为future，本条调用链也不是标准 `std::future::get`。[原pthread `d4d8..d7c0`。]

**B：该futex最符合 `285dc98` 本帧的boot完成事件，地址和栈深度精确吻合。** 原pthread帧大小=`0xd0`，libstdc++ wait帧=`0x10`，model_future wait帧=`0x90`；因此推算外层 `285dc98` FP=`7f483dc2e0`，与serial行8075/8101附近已经捕获的同一handler外层FP一致。事件=`FP+108 = 7f483dc3e8`，cv=`7f483dc3f0`；glibc `d54c..d558` 等待cv的 `+28+4*g`，首次group0给出：

```text
SP + d0 + 10 + 90 + 108 + 8 + 28 = SP + 2a8
7f483dc170 + 2a8 = 7f483dc418     # 与保存syscall完全一致
```

group选择的原码在pthread `d50c,d548..d558`；group1会再加4。**没有保存该时刻group字段、用户帧内容或事件指针值，故精确拟合仍标B，不写成已完成用户栈展开。** [上述VA；serial行8065–8105、14065。]

七轮19份快照复核如下；每份均有kernel栈，PC均为libpthread+d5f0、futex−SP均为2a8。除AP77a外六轮没有本轮同等级的逐条出队探针，不能仅靠此表认定它们的具体消息身份。[proof.runs保存每份完整快照及映射行。]

| run | AppFw syscall行 | 首份 futex / SP |
|---|---|---|
| AP70 `ap70lcd-f61554d9` | 13339 | `7f617fd4a8 / 7f617fd200` |
| AP75 final1 `a67fe198` | 13589、26449、38966 | `7f5085d438 / 7f5085d190` |
| AP75 final2 `4d01e9f8` | 14461、26993、39524 | `7f2d6e4438 / 7f2d6e4190` |
| AP76 sync `fe30bc21` | 13997、28130、41262 | `7f58804438 / 7f58804190` |
| AP76 corr `316e20b7` | 14024、28160、41283 | `7f351e8438 / 7f351e8190` |
| AP77a `f63dd39e` | 14065、28239、41393 | `7f483dc418 / 7f483dc170` |
| AP77b `b9abfcab` | 14014、28057、41091 | `7f4505d438 / 7f4505d190` |

## 4. 谁通知、与启动屏障有何关系

**A：事件由AppFw栈拥有，boot sequence持有指针；没有“某线程持有这个futex锁”的证据。** 条件等待会释放其unique_lock；通知者用相同 `8e29cf0` mutex置完成字节后解锁，再notify_one。当前等的是事件，futex字为0不能当mutex owner TID解释。[`2aa222c..2294、2aa1668..16b0`；pthread `d52c..d53c`。]

事件的cv由等待方在 `285e434` 析构，随后沿handler返回；它不是需要另一线程free的堆消息。boot只负责置位/通知，原等待方负责栈对象生命周期。[`285e430..e438`、`2b68388..838c`。]

**A：静态通知链已闭合到 `sequence_boot`，不是未知CP服务直接唤醒AppFw的futex：**

```text
285e410 保存event指针 → 285e420 → 273b240
  → 271a368 构造command0x1f（node+10复制event指针）
  → 27391b4 消费命令；2739310..9324 查函数表
  → table4029370 = 2718424
  → 2c214f0 → 2c20ce8（sequence_boot构造）
      2c20d18..d20 保存 event* 到 sequence+1b8
      GOT47a8a70→vtable46e4fd0，原RTTI model::sequence_boot
  → [原sequence调度线程执行]
      vtable+10=2b68330 run()
      2b68370 → 2b638b8 启动主体
      2b68388 取 sequence+1b8
      2b6838c → 2aa1668 置 event[0]=1；cv=event+8 → notify_one
```

**B：AP77a最可能通知者为 SeqQueueCommon tid327，对应已观测的boot对象 `7f8819daa0`。** 该线程在serial行21294–21318，以此对象创建license/volume/beep；原创建函数指针分别由GOT `472c3c0/472b2d0/474f098` 解析为 `2b61efc/2b5fae4/2b61a90`。同一线程随后发送9059000e（行21320），第二/三次快照停在 `osal_rcv_msg_tmo`（行30370–30430、43524–43584）。第一次快照行16197–16255还在另一条件等待，不能把三次SeqQueueCommon快照都写成timecode等待。运行内存中 `sequence+1b8` 尚未读取，因此该run的通知者/事件对应仍B。

**A静态 / B运行归因：timecode等待位于通知之前，正常路径的get-func与四任务屏障也位于通知之前。** boot主体 `2b66f28 → 2dd0754 → 2dd077c → 2debbb4`；`2debc48..54` 发送到9059000e，`2debc58..64 → 2e10c80` 接收12B回复，`2e10cc4` 传timeout=-1给Dataflow `ReceiveASync`。后续第四任务创建点为 `2b67674`，GOT `47a6698→2b60208`（get-func）；`2b67a6c` 调四句柄屏障 `2b6353c`。AP77a前3个任务完成入队见serial行21390–21391、22104–22105、22164–22165；已保存gate计数的第四任务创建点及屏障入口均0，不能把这3次入队说成屏障消费完成。具体9059000e协议由相邻 [svc-9059000e审计](../svc-9059000e/) 负责；本审计没有构造或发送回复。

**A：notify只表示boot主体已经返回，不保证正常boot成功。** `2b68370` 调用之后无成功值判断便取事件并通知；主体中存在错误早退/共同返回路径（例如 `2b68328 → 2b640b0`）。因此“正常四任务与后续步骤完成”是正常路径要求；错误提前返回也可能唤醒UI。不得以notify、UI继续出队、或清屏代替正常启动验收。[`2b68370..8390`；proof保存整个 `2b638b8..2b6832c` 主体。]

## 5. 最小运行观测与解除后的预期

以下仅供运行链持有者加入有界被动探针，本worker未运行。**最小闭合证据是同一个event地址从构造、保存、等待到通知返回完全相等**；地址必须用当前run基址重算。[以下各VA原指令已保存。]

| VA | 最小寄存器/只读字段 | 关闭的问题 |
|---|---|---|
| `285e42c` | x20指向model_future；读 `[x20]` event、`[x20+10]` cv；byte[event] | 实际等哪个事件 |
| `2c20d20` | x19=sequence_boot，x0=event，记录TID | 谁持有该event指针 |
| `2aa2294` | x0=cv、x1=unique_lock、LR、TID | 是否进入这次condition wait |
| libstdc++ `b3600` | x0=cv、x30=返回地址（`2aa2298/23a8/2468`）、TID | 区分简单/协作/协调cv等待 |
| `2b68374` | x19=sequence、`[x19+1b8]` | boot主体是否真正返回 |
| `2aa1668` | x0=event、LR=`2b68390`、byte[event] | 本boot实例是否置位 |
| `2aa16b0` | x0应为同一event+8 | 是否通知同一个cv |
| `2aa2298` / `285e430` | TID、event身份 | wait是否返回 |
| `16f2698` / `16f217c` | 接收处理返回/后续消息type与source | handler与主循环是否继续 |
| `16f2640` | x0、a18/a12/a13 | 是否实际调用timer/draw |

AP77a仅作历史预期值：event=`7f483dc3e8`，cv=`7f483dc3f0`；若boot对象确为 `7f8819daa0`，则可只读 `7f8819dc58`（sequence+1b8）核对是否等于该event。**这两个地址尚未运行读取，不能当作实测值。** [快照SP拟合与serial行21294/21316的对象地址；静态 `2c20d20`。]

**B预期：**若9059000e正常回复被原代码消费，tid327应先越过 `2b66f2c`，继续原服务步骤，在 `2b67674` 创建get-func（其内仍需真实0325能力回复），并在 `2b67a6c` 正常消费四句柄完成；还需主体余下ADF/path/notify等调用返回，才到 `2b68374/838c` 唤醒UI。随后AppFw从 `2aa2298 → 285e430` 继续初始化，最终应再返回外层事件循环。**仅解除timecode不承诺立即唤醒，也不承诺菜单出现。** [boot完整主体、`2b67674、2b67a6c、2b67aa0、2b67b2c、2b67b70`；这些后续回复尚无本轮完成回执。]

**A机制 / U后果：**恢复消费后仍可能遇到 `16f2478..2488` 的 `a18>2 && !a12` 积压门。AP77a已保存计数为生产11381、消费1、门控跳过1、实际UI调用0，不能从一次唤醒推断积压能排空。首绘、1004、GPE命令/PNG、可操作菜单仍需各自运行证据。[serial行7858–7859；`ap77a-gate-readback.json`/原RAM已记SHA256；绘制调用 `16f2640`。]

## 6. 重建证明与验收边界

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B \
  work/fx3-vm-20261101/lead-claude/audits/appfw-30072-wait/audit_appfw_30072.py
```

本轮退出0，重建 [appfw-30072-proof.json](appfw-30072-proof.json)：固定校验原appFw/libpthread/libstdc++三库哈希，完整解码选定窗口，断言发送/分派/command/事件保存/通知指令及两张RTTI虚表，校验AP77a两条出队/28B payload，逐份计算七run、19份快照的相对PC与futex拟合。可用 `...audit_appfw_30072.py dis appFw.so 285e3f8 40` / `xref appFw.so 2aa1668` 只读复核。它没有执行固件，也没有改变等待对象或模拟成功；计数使用既有解码文件并记录原RAM哈希，未声称重新独立解码全部计数。

U保留：本run的sequence+1b8与AppFw栈事件内存相等；等待瞬间完整用户栈/帧指针及model_future简单/协作分支；boot实际return/notify/后续主循环返回；解除timecode后各服务原回复、get-func和四句柄正常完成；积压排空、Widget timer、绘制与菜单验收。已保存内核stack可用，AP77a/b目录中没有单独wchan/stack/snapshot文件；本脚本输入没有可补全用户栈的dump，未向正在运行的guest取证。[proof.runs及本目录脚本输入集合。]

方法资料仅用于工具与通用同步语义：[Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)、[Linux man-pages维护者futex说明](https://man7.org/linux/man-pages/man2/futex.2.html)（本轮核对）。Sony调用与对象归属以本地原字节和保存回执为依据。
