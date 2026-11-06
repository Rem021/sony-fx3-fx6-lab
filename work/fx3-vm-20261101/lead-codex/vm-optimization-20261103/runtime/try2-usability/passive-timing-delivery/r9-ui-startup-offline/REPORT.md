# FX3 原生 UI 启动链：第 63 条配置发送、timer、首次 FillRect

2026-11-04。**可定位的分叉已前移到 UI 更新/timer 回调入口之前，根因仍未知。** 失败 A 有 63 条 GUI 发送、两次 config 返回，未捕获 timer/Fill；成功 r3 和新 B 均在原 timer 的 ID 与 timerInfo 门通过后发出第 64 条 `0x1004`，随后出现不同线程的原绘制调用。第 9 包高 16 位非零也出现在成功 B，不能据此判损坏；原生产者的 `strh` 及本项目实际消费者源码已提供 16 位操作码的具体证据，超出了“只知 observer memcpy32”的阶段，但完整原厂 CP schema 仍未证。

仅审查现存源码、原 ELF、日志及少量指定 CPIO 成员；没有运行 VM、历史测试、编译 helper、改 guest/平台/旧候选/r7，或操作设备。本目录的 [EVIDENCE.json](EVIDENCE.json) 给出 LF 行号、原始字节偏移、字段、哈希和指令导出参数；[analyze_startup.py](analyze_startup.py) 是本次离线分析脚本。所有行号按 LF 分行，保留串口交错碎片，不把别的 marker 插入或行尾黏连修饰成理想日志。

## 输入和绑定：先确认实际装入版本

路径缩写均相对 `/Volumes/KAFU2T/AI/Projects/Mac/`：

- `H = work/fx3-vm-20261101/menu-repair-01/runtime/helpers/`。
- `L = work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/`。
- `T = work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/`。
- `P = T/passive-timing-delivery/`，`M = T/mss-all-key-contrast/passive-timing-next/`。

旧成功 r3=`T/runs/v25diag-web-r3-91001f82`；新失败 A=`T/runs/v25diag-web-r6-0dfbd0ab`；新成功 B=`T/runs/v25procdiag-web-r6-d4254d75`。A/B 共用宿主，A 为原 r3 CPIO，B 为新增 procdiag 的 r4e CPIO；这是两次既有单轮结果，不构成调度或 helper 的因果结论。此前 r4e/r6 各 63 条的事实沿用 [原有对照报告](../r6-zero-frame-offline-review/REPORT.md) 和对应 COMPARISON，不重做 1139 成员比较。

本次仅对两份 CPIO 各 **9 个指定成员** seek/读取并哈希，不解包或复制镜像。下表每一项在两份 CPIO 中均匹配；源码/输出哈希也与列出的构建回执匹配。

| CPIO 别名 | 实际源码与构建绑定 | 装入 ELF SHA-256 |
| --- | --- | --- |
| `simulation/ioctl-trace.so` | `H/ioctl-trace-v12.c`；`ioctl-trace-v12-build.json` | `f2799333d67b4b118634e273f50f7d48106a228c1c40132075d923f040ca0b74` |
| `simulation/fx3-timer-observe-v1.so` | **v3**：`H/fx3-timer-observe-v3.c`；`fx3-timer-observe-v3-build.json` | `3b828ba31352492ab4bd4b76857ece4b30cef5241bb8ed0223fb75f9b7153b1b` |
| `simulation/fx3-ui-gate-v1.so` | **v11**：`H/fx3-ui-gate-v11.c`；同名 build JSON | `54eeed923a6412cd2c6743f6e8c968d1ede71b92aa79aca4575868ebccc4a9ec` |
| `simulation/fx3-preset-context-v2-screen.so` | `M/src/fx3-preset-context-v6-save102-timing.c`；`M/build-receipt.json` 的 ap row | `52ed3b5b2cdadc46e1c78c596a60d06a3fd865bb9bb5420a0bb5f2492df12392` |
| `simulation/fx3-osd-headless-v5.so` | `P/v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c`；该候选 build-receipt 与 FREEZE-r3 | `67155b38fbbe23c3b6273c64ce8fc4676e59ad98da4a30a238508c26d9b5fba8` |

preset 原始 v6、OSD 原始 v7 的输出**不等于**装入版本；不能直接以它们的 build JSON 充当当前绑定。实际 preset timing 源 SHA=`8b6d64e307dbfd8dc3ffd3b7ca961516bc0c2833450fc4e2bfb2ff970a5981ec`，实际 OSD v25-r3 源 SHA=`1c4d2b420a40d006d22d2e60510df18d6dbbd7c51cd219735f1252f17c5956eb`。timer v3 源 SHA=`1b3135edb19e8d7577d3b0a3f361ccb807f90fa67f054045bfe305dbaa0cd85d`；本次没有构建这些源。

原厂 ELF 同样与 CPIO 中指定成员逐一匹配：

| ELF（L 下） | SHA-256 |
| --- | --- |
| `appFw.so` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| `libObj.so` | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |
| `libosal_uipc.so` | `09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3` |

下文地址均为这些 ELF 的未重定位虚拟地址；ASLR 后日志 app_base/obj_base 不直接作为固定地址。

## 消息宽度：observer 的 tag1 不是原 schema 声明

`H/ioctl-trace-v12.c:152–185` 在原 ioctl **之前**快照 16B body；`:193–195` 调用原 ioctl，之后把本地副本交给 `send_unique`。`:40–44` 要求 op 4..6、body 读满 16B，再将 body[0..3]、[4..7] 各 memcpy 到 32 位 unsigned int，打印 `tag1/tag2`。UI_WIRE 在 unique 的锁/去重/256 容量门之前，故不受该 unique 门压掉；仍受快照成功、目标条件、执行/串口留存影响。

原 `libosal_uipc.so:u_osal_snd_msg` 在 `0x3a34/0x3a38` 建立 `{u32 destination, +8 pointer}` 外层参数，`0x3a48` 调 ioctl；返回 0 直接返回。它解释的是**原 ioctl 返回值**，不证明消费者已经收到、处理或提交像素。[指令片段](libosal-send-recv-ioctl.txt)。

原 appFw 已知生产者与发送路径提供了更窄的 schema：

| 原位置 | 可证字段/操作 |
| --- | --- |
| `0x16ee7d8–0x16ee828` | 构造 GUI `0x1000`：`strh` 写 body+0，`strh wzr` 写 body+4；从 body 复制发送 80B；当前函数片段未显式初始化 body+2..3 |
| `0x16ee730/0x16ee73c` | config 函数构造 `0x1001`，同样用 `strh` 写 body+0；经 `0x16ee6f0` 发送 96B |
| `0x176fbc4–0x176fbe4` | timer 构造 `0x1004`，`strh` 写 body+0、半字零写 body+4，body+8 写 `input_time - stored_time` 的 64 位差；发送 16B |
| `0x16ee598–0x16ee660` | `osal_valloc_msg_wait(0x8280074d,…,bytes,1)` → memcpy body → source=`0x9088076b` → `osal_snd_msg(0x8280074d,body)`；该函数没有随后接收 GUI 回复的调用 |

对应 [GUI 构造/发送](app-gui-send.txt) 与 [timer 1004](app-timer-1004.txt)。这证明这些原生产者把首字段作为 **16 位操作码**写入，不支持将 observer 的整个 tag1 当 32 位 opcode。`0x1000` 构造片段未写高半字，提示它可能来自栈上残余/未初始化邻接字节；但**没有第 9/63 包的原生产者 PC/完整消息身份，不能把每一包都直接归到该构造器，亦未证明高半字的完整原厂语义**。

实际软件消费者 v25-r3 使用 `H/fx3-osd-owner-core-v1.h:13` 的 `qo_GUI`，按 `ho_u16(body)` 判断 GUI 1000/1001/1004，匹配来源、长度 80/96/16 和部分后续字段；不以 body+2..3 为 GUI opcode 高位。`H/fx3-osd-core-v4-frame.h:17–18` 定义了该 u16/u32 读取。**这是当前软件 CP endpoint 的已知合同，不是原厂 CP 全部消费者 schema。** 尤其 HO_AP 来源的 `0x1002` 发表包另有 body[2..7] 全零约束，不能套到 `0x9088076b` 来源的 GUI 配置包。

第 9 包原始 tag1：r3=`0x1000`，A=`0x09831000`，B=`0xe5d41000`。B 随后有真实绘制及首帧，故高 16 位非零不是这三样本中的零帧预测条件，更不是损坏/根因证明。

## 可证生产链与等待关系

### 63 → timer → 64

三轮第 63 条均为 `target=0x8280074d, op=4, tag1=0x1000, result=0`。r3 在 LF 18969，A 在 30840，B 在 19942；这些只证明各次原 ioctl 已返回 0，没有消费回执。

原 timer `appFw+0x176fb4c`：在 `0x176fb78` 调 IDeq，低字节假则 `0x176fb80` 退出；在 `0x176fbb8` 调 getTimerInfo，低字节假则 `0x176fbc0` 退出；两门通过才构造/发送 1004。v3 helper `:10–14、16–28、30–44、52–58` 包裹原调用、校验四个入口 16B 前缀；绑定位置包括 app timer `0x176fb4c`、app config `0x16ee6f8`、libObj timer table `0x176ab0` 和 Fill `0x100c48`。

| 首次动态顺序（同轮 LF） | r3 | 新成功 B | 失败 A |
| --- | ---: | ---: | --- |
| timer ENTRY | 21857，tid376，input_time43614 | 23919，tid377，input_time44077 | 无 |
| ID 比较 | ID/expected 均 0x1e4，result1 | ID/expected 均 0x1e4，result1 | 无 |
| table/info | result1，stored_time23479 | result1，stored_time24338 | 无 |
| 第 64 条 UI_WIRE 1004 | 21863，tid376 | 23936，tid377 | 无第64条 |
| timer RETURN | 紧随1004，同 seq3/tid376 | 紧随1004，同 seq3/tid377 | 无 |
| 首 Fill EXEC | 21941，tid277 | 24001，tid284 | 无 |

该原函数具备明确 1004 生产路径，动态 marker 的线程/序号区间与之吻合；没有逐包 producer PC/完整 payload 与接收 identity，仍不应声称完成了每个消息的端到端配对。UI_WIRE 的 1004 **不是 FillRect 绘图请求本身**。

### timer 之前的原 UI 门与字段来源

[原 UI 门](app-main-gate.txt)：`0x16f2478` 读 root+0xa18，`0x16f247c cmp w0,#2` 后 `0x16f2480` 是 **signed b.le** 到 `0x16f25ec`；否则读取 root+0xa12，非零同样进入该路径。若 signed counter>2 且 a12=0，则走 `0x16f248c` 的另一支，绕过本轮时限比较/更新阶段。不能把全域条件改写为 unsigned <=2；负数/回绕是否实际发生未知。

进入该路径后，`0x16f2600` 比较时间差与原阈值 `0x62f4`，通过后仍有后续条件；`0x16f2640` 调 `0x16f1998`。后者依次包含 WidgetSystem::updateCurrentTime、processEvent、资源处理，以及条件性的 notifyDraw / GraphicsEngine::drawFramebuffer（[原更新链](app-update-and-draw.txt)）。并非只过 backlog 门就保证产生 timer 或绘制。

| 字段/观察点 | 直接可证的原 writer 或来源 | 仍未知 |
| --- | --- | --- |
| root+0xa18；gate id5 | producer `0x16f1a68–74` 读/加1/写；随后分配并发送 28B 内部消息 `type=0x150000, source=0x830128, dst=0x5503e0` | 各实际 producer 的完整调用来源/速率及失败核算，非原内核队列长度的独立读数 |
| root+0xa18；id10 | `0x16f1d30–68` 先验证 source=0x830128 和 body 32 位 type=0x150000，再减1写回 | 本轮每个加/减/alloc/send/recv 的身份配对、负值/回绕/计数不平衡是否发生 |
| root+0xa12；id6 | 主更新返回后 `0x16f2644` 明确清零；gate 在 `0x16f2484` 读取该 byte | A 中该根对象的初始化、设置非零的直接 writer/业务原因未绑定 |
| 其他 a12 偏移命中 | `0x21dfa54`、`0x21f1170` 也 strb 到 x20+0xa12，值来自 `0x2947390` 返回指针的首 byte | 两处 x20 **未证**就是被测 UI root，不能当作本轮 a12 的已知设置者 |

参见 [加计数/发送](app-backlog-producer.txt)、[消费/减计数](app-backlog-consumer.txt)、[候选 writer1](app-a12-candidate-writer1.txt)、[候选 writer2](app-a12-candidate-writer2.txt)。内部 `0x150000` 消息与外发 GUI `0x1004` 是不同 schema，不可混同。

v11 helper `:75–88、105–108`：id5 从真实分支输入 r0 保存 TLS `decision_a18`；id6 重新读取 root 内存 a18 时它可能已被其他线程改变，所以优先使用 decision_a18 和 id6 的 r0。id7 对应时间比较前，id8 对应更新调用前。普通日志只打印 n<=50 或 n%1000==0，不是穷尽轨迹。

### 原绘制与 OSD 接收：不存在“先消费1004才允许首Fill”的已识别实现

`libObj+0x100c48` 是 timer helper 绑定的原绘制入口；`0x100c80` 读 command+0x78 bitmap，`0x100c88` 调原 GRM_bitmapGetPhysicalAddress，`0x100cc4` 调 mpgpe::GpermFillRect。[原 Fill 指令](libObj-original-fill.txt)。`UI_FILL_EXEC` 在原调用前，`UI_FILL_RETURN` 在返回后；它们和后续 GPE adapter 的返回、OSD commit 是不同阶段，序号也不能混用。

当前实际 OSD 源 `P/v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c:111–121` 在 queue_owner 模式下，只在 **HO_AP=0x8288076c 来源、HO_CONTROL=0x8280074d 目标、符合 qo_publication 的 1002 发表**成功后初始化环、创建 worker；GUI 1000/1001/1004 不满足该启动条件。`:103–104` 的 worker 才以原 `osal_rcv_msg_tmo` 读取队列，`qo_GUI` 命中时保存配置并原 free，**不生成 GUI 回复，也不调用 FillRect**。

运行证据亦支持这一方向：r3 首 Fill LF21941，owner BOUND/START 为23900/23901，control recv begin为23930；B 首 Fill24001，BOUND/START26063/26065，control recv begin26093。现存链路是先出现原绘制，再有原 GRM 发表驱动软件 CP endpoint 开始取队列；不能把其稍后的 1004 消费当作先前首 Fill 的前置等待。

`H/ioctl-trace-v12.c:29–37、191–195` 的 RECV_BEGIN 在原 ioctl7 **之前**，trylock 可直接丢记录，并只对每个(tid,queue)发一次；这不是 receive 完成。旧 ExternalOSDIF tid274/B tid278 对 `0x8288076c` 的等待，与后来的软件 owner tid807/B tid882 对 `0x8280074d` 的取包也是不同角色，线程 comm 相同不代表同一消费者。`OSD_OWNER_GUI` 才在 hreceive 返回成功、size/source读取及匹配后打印；该日志也有前30/每100的采样门，不能逐包等同第63/64条。完整原厂 CP 消费及其等待关系仍未知。

## A/B 累计计数与采样：分叉前移，但不能宣布饥饿根因

A 的最后一个已打印 TIMER_SNAPSHOT 是 LF30839（**就在第63条发送之前**）：bound1、patch_mask0xf、timer_entry/id_compare/info/table各0、config/config_target各2、fill0、event_seq2。v3 `:11` 在原 timer 调用之前 atomic++timer_calls，`:62–64` 同时检查入口 patch mask 并打印累计数；因此这不仅是少一条 ENTRY 行，而是在该 snapshot 时刻 observer 尚未计入 timer 入口。此 snapshot 没有 guest ns、也不是终止时额外读取，不能把它外推为整个后续观察窗的末端全域计数。

B 最后 snapshot：上述四个 timer 计数各7、config各2、fill3、event_seq33；全日志 Fill EXEC为4，说明最后 snapshot之后还可有事件，不能强求它等于文件结束总数。旧 r3 全轮（含后续16次按键）的107次 timer、151次 Fill 不与短 B 的累计次数作性能对比。

| 证据 | 失败 A | 成功 B |
| --- | --- | --- |
| id5 普通日志样本 | 51条，最后n1000；signed decision范围23..2010，未采到<=2 | 50条，全部样本7..302，同样未采到<=2 |
| id6 普通日志样本 | 51条，采到的 a12/r0 为0 | 50条，采到的 a12/r0 为0 |
| id7/id8 普通日志 | 均0 | 各8；首次的 decision_a18=2，当前内存a18却为3/4，印证要使用分支快照 |
| 已存最终 UI gate bank | **无文件**，故不能给累计id7/8下零结论 | counts[4..11]=925,925,917,8,8,913,898,925 |
| B bank进一步交叉验证 | 不适用 | gate_hist=[0,0,8,77,301,539]，backlog_skip917，time_pass8，time_skip0，peak_gate352，a12_nonzero0 |

B 的 bank SHA=`df00afe099c49b1980106613c034fbe3f86a33ed1492692cffaadf794a50b8c2`，header magic/version2、active bank0、serial6514、pid238。**8次值为2的低水位均被普通id5采样漏掉**，因此不能用 A 的 logged signed<=2 数为0排除未采样机会。旧 r3 保存的最终bank另有 id5=23111、id6=19138、id7=3973、id8=3719，仍只代表其整个长轮次。

v11 mirror 逐字段 atomic load，probe又在原store之前；bank不是同一瞬间所有业务状态的事务快照。B count9-count10=15而last_a18=14、bucket与不同位置计数不完全对应，都不能据此称损坏或核算错误。现存 B/A 都没有足以闭合原计数每次加减的逐事件账。

A 无 ui-gate-counters.bin 的宿主原因已核源码：`P/v25-r9-ab-host/run_trial_v25_diag_r3.py:733–763` 把optional reads放在diag_snapshot.consistent条件内；`quiesced_diag_readback.py:26–39` 先保存完整16MiB，再parse成功才返回consistent。A全零环parse抛错后跳过全部optional snapshots。故**文件缺失不是 guest 没建计数**；本任务没有修该宿主问题。A已存独立观察回执记录screen0 ns153012348992到停止决策poll213605768000共60.593419008 guest秒，首commit/frame为空；更晚清理poll不用于增加这个观察窗。

## 假设、最少缺口和下一次仅观察方案

**事实**：A采到多次 timer pending 门的 bypass 条件，且未采到更新/timer/绘制；B有明确低水位、更新、timer与绘制。**机制假设**：启动阶段内部150000消息积压可能长期阻止进入更新链；它与现有A样本一致，但原producer速率、消费进度、分支未采样区间、其他等待及宿主/observer时序影响未闭合，不能定为唯一根因。新增procdiag既不是零帧的必要条件（A无它也失败），也不是必然阻断条件（B有它能出帧），更不能据一轮B成功宣布它修复了问题。

下一次先补结束时的一组既有bank，证据不足再升级观察，不先追未进入的 ID/getTimerInfo 内部分支：

1. **首先只在既有结束/清理暂停时独立读 UI gate 64KiB**：相同固定平台/已有probe下保存 `0x41dc00000` 的既有双bank、magic/version/serial及guest CLOCK_MONOTONIC时间，不依赖 OSD 环parse成功；screen0时刻沿用已有串口。优先取得 signed decision、a12、id5..8累计状态，不增加screen0中途暂停，不把当前a18替代真实cmp输入。该采集是下一实验方案，当前未执行，宿主缺失快照修复由协调端另派。
2. **只有结束bank仍不足时再升级**：才考虑screen0后/结束前两时点计数及已知 UI TID/PC、有限栈/寄存器或已有task状态，区分门前、time比较、updateCurrentTime/processEvent和原等待；中途暂停可能改变线程调度/启动时序，不能当作无扰动对照。原计数来源优先使用现有 id9/id10/id11、150000/source830128自然消息及原alloc/send/recv返回，配同根对象/线程身份；必要的只观察停点只记录原PC、参数、返回，不写计数或跳条件。若需认定某个GUI包归属，再补原producer PC、size/source/前16B和receive返回，不能只靠可复用指针或独立发送序号配对。

可证伪预期：若失败样本独立bank的id7/id8确实增长，则“从未获得通过backlog门的机会”被否定，应继续看更新链内部/调度与timer登记；若id5增长、id7/id8不增长，结合PC与a12可支持停在门前的阶段定位，但仍不能断言原计数不平衡。若timer入口增长而ID/info失败，才进入内部两门审查；若两门成功仍无1004，才查本次原valloc/send的进入/返回。任何分支均不允许靠重放通知、keepalive、改消息、高位归零、写a18/a12、改定时器/5000ms阈值或放宽帧门绕过。

## 本次验证回执与未完成项

本次分析脚本实际完成：3份原串口（含新增B）解析，raw marker次数/按LF记录数并列保存；两份CPIO各9个指定成员绑定；原ELF固定地址反汇编；现存r3/B计数bank解析；所有登记输入哈希在分析前后相同。没有重新运行旧测试、重做共同成员全比较或复制镜像。产物哈希见 [SHA256SUMS](SHA256SUMS)，入口见 [README](README.md)。

仍未完成：A最终累计gate状态、该根对象a12所有writer归属、内部timer消息逐次核算、第63/64包完整生产消费身份、完整原厂CP schema，以及零帧根因。真实菜单可用性、VM新运行、物理显示/相机均不是本任务验证结果；A/B清理通过与存储查询无匹配也不能替代这些结论。
