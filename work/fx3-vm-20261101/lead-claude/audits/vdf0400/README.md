# 0x0400：SYS/TCUB 时间码模式配置审计

**捕获请求 `0d2000040a0001800000` 可由显式软件配置后端接受，精确成功回复为 `0d2000140c00018000000000`（1400/12B/status32=0）。** 本命令虽发到公共 BB 目的 `92840747`，实际是 `sys_set_timecode_tcmode`，走 SYS/TCUB 过程式处理；**没有旧 VDF `2001` 命令、RTTI Validate/Execute 链，也不 OR `590000`**。把0152或0165的显示域状态照搬到这里会丢失原协议区别。（AP `2df264c..26dc`；CP `b71d24→1a8078、1acb9e→1acbf0、1a8f92→1a9a3c、1b910c→1b944c、1aabae→1ab192、1adf5c..84`；AP85r4 serial **21807–21809**。）

**本 sequence 的正常路径在0400之后没有其他同步请求。** 它记录Success后返回SeqQueueCommon；后面的动态排队任务与完成观察者没有heap快照，因此无法诚实列出它们的命令和固定成功字节，详见第7节的完整边界清单。解除此等待仍需本轮AP自然消费/返回回执；本次没有运行QEMU或实现runtime。（AP `2dcae3c..80、2bd7750..7788`；serial **21792–21809、52731–52814**。）

只写本目录的 [audit_vdf0400.py](audit_vdf0400.py)、[vdf0400-proof.json](vdf0400-proof.json)、本文。未修改runtime/STATE、锁、原件或Git，未启动QEMU、执行CP代码或访问相机。AP地址为appFw.so ELF VA；CP为Thumb VA，文件偏移=VA−`108000`。下文serial均为 `menu-repair-01/runtime/runs/ap85r4osdring-5dcb8371/serial.log` 的原始LF行号，保留CR/NUL；A=直接字节/捕获，B=有界推断，U=未证实。

## 1. AP85r4捕获与逐字段含义

**A：原请求在21807行，21809行才是Skip747诊断。** 目的92840747、10B、metadata source=`81cf61c2`；源ID只属于此次动态reply队列，不能跨运行硬编码。原栈tid346的六个AP相对返回地址如下，九帧完整值保存在proof.runtime.frames；穿插的UI门控行没有被当作栈帧。（serial **21792–21809**。）

```text
send_and_wait_cmp_i +2de7264
  ← sys_set_timecode_tcmode wrapper +2df26c0
  ← instrumentation wrapper +2dd1f40
  ← sequence_sys_set_timecode_tcmode::run +2dcae3c
  ← SeqQueue dispatch +2bd76fc
  ← thread wrapper +2f71ba0
```

| 偏移 | 字节 | 已证含义和证据 |
|---:|---|---|
| 0..1 | `0d20` | type200d，AP `2df2660/266c` |
| 2..3 | `0004` | command0400，AP `2df2670/2678` |
| 4..5 | `0a00` | 长度10，AP `2df267c/2680` |
| 6..7 | `0180` | flags8001，AP `2df2684/2688` |
| 8 | `00` | 时间码TCMODE值0；CP日志 `1a80b8`=`[TC]:SET_TIMECODE_TCMODE[%d]`；CP `1a807e/808e`读byte并保存为u32 |
| 9 | `00` | AP先清零的保留字节；CP0400 parser没有读取它（AP `2df2674`；CP `1a8078..80b6`） |

mode来自sequence输入 `+1bc` 的32位值，经FP+30交给wrapper；正常构造只接受0/1，0保持清零值，1写byte8。其他值走诊断/`usleep(100000)`/错误处理；如果错误处理返回，会回到发送点并保留默认0，不能把该路径称为可靠输入拒绝机制。本次软件合同严格冻结完整10B，连CP未读取的保留字节也不放宽。（AP `2dcae0c..38、2df2654、2df268c..2698、2df26e0..276c`。）

**U：0/1的原UI枚举名称未证实。** 原字符串仅证明TCMODE，不能仅凭两个值就命名Rec Run/Free Run。本次也没有wrapper输入结构的额外内存readback；mode0是wire直接捕获事实，输入来源是代码推导。（AP字符串 `3960c90、3968a40`；CP字符串 `1a80b8、1ba648`；serial **21807**。）

## 2. AP sequence、回复检查与失败后果

完整run入口为 **2dcadd0**，函数名字符串 **3960c90**=`virtual void model::sequence_sys_set_timecode_tcmode::run()`；源文件字符串 **3960c5e**；发送日志 **3960c2b**明确 `Send sys_set_timecode_tcmode[InPrm1:%08x]`。`2dcae38→2dd1f14→2df264c`与捕获返回地址一一对应，不借相邻sequence推断父流程。（serial **21794–21799**；proof.strings和sequence_calls保存完整14个直接调用。）

wrapper在 `2df269c..26bc`指定destination92840747、input10B、output12B，清零本地reply槽，调用 `2de70a8`；共同封装在 `2de7260`发送，在 **2de72fc**置timeout=`-1`、**2de7300**调用导入 `osal_rcv_msg_tmo`。没有有限超时/重试；本轮tid346后续快照仍在内核收包路径、状态S、名称SeqQueueCommon。结合捕获栈，这是仍被0400等待阻塞的强B证据；快照没有用户态LR/队列内容，不能把它扩成无损全局消息跟踪。（serial **21807–21809、52731–52814**；AP `2de70a8..7344`。）

收包后共同封装**固定memcpy 12B**再 `osal_free_msg`，没有核对收到的command/header/实际长度，也没有检查接收调用的返回值。wrapper只取reply+8的u32经BB转换器 `2de4574`；其 `2de45c4→2de46cc`把裸0转本地0。此宽松消费不授权发短包、错命令或省略回复。（AP `2de7304..7320、2df26c0..26d0`；imports与指令均在proof。）

本地结果0走Success日志 **3934d30**；非0走Failure日志 **3934d59**、断言诊断、100000µs sleep、`2ebf3b0`错误处理，随后存在回到run收尾的分支。不能声称任何非0必杀进程：该helper自身也有返回分支；其外部错误观察者的具体后果U。缺回复时上述两条结果分支都尚不可达。（AP `2dcae40..80、2dcae84..2dcaf5c、2ebf3b0..448`；serial **52731–52814**。）

## 3. CP入口、两级表及SYS/TCUB生命周期

下表每个目标均由脚本读取原表项并重算，未用表数据的偶然反汇编当代码。（proof.tables、parser_table；CP VA如下。）

| 层级 | 槽位→目标 | 作用 |
|---|---|---|
| 接收分类TBH | **1a6bc8→1a6c1e** | wire0400属于category0；TBB `1a6d00[0]=05`→1a6d0a，`1a6d0e/18/1a`以r2=1/r3=0调用1ac9c8 |
| parser登记表 | **b71d24**=`0400,1a8079` | `1ac9dc..de→5c7ff4`先按command查119项parser表，调用1a8078 |
| 第一级wire TBH | **1acb9e→1acbf0** | 写internal **3e**；1ad050..70排至内部92840748，当前r3=0不携带VDF阶段指针 |
| 第二级phase0 TBH | **1a8f92→1a9a3c** | decoder `1a8f0a..12`用internal作索引；3e走TCUB event0，经1a9fd0→5cada6→1b9090 |
| 完成TBH | **1ad1ca→1ad21c** | callback0400→internal **23f**，1ad6b6..d0排到内部92840748 |
| 回复分派TBH | **1aabae→1ab192** | internal23f→1adf2c，构造AP1400/12B |

parser在 **1a807e**读取原请求+8，保存到singleton **19eafb8+42c=19eb3e4**；`1a80a0→5ce2f8`将dirty byte **1438dd5=1**。它没有Validate类方法，没有检查mode范围，也未读取帧地址/传感器像素。parser返回1是内部处理返回值，不能解释成AP业务失败status1。（CP `1a8078..80b6、5c7ff4..8022、5ce2f8..304`。）

第二级处理把event0交给TCUB。`1b9090`先以9调用同步helper `1c2d44`，event0表项落到 **1b90de**；后者设置 **11cbd58 bit0**，随后立即在 **1b910c**置command400，经 **1b944a**置status0并调用 **5c68de→1ad1a4**。它在同一请求路径中是“配置已保存、待计数器后端处理”的确认；没有等待真实timecode递增/录制/live-view完成。（CP `5cada6..adba、1b9090..90ae、1b90de..9110、1b944a..9450、5c68de..68ee`。）

异步后端 `1b95c0`读取该singleton；bit0处理分支 **1b995a..99aa**将desired+42c写到 **11cbd98**（原日志 `1ba648`=`sCmdTcMode`），清掉11cbd58 bit0，并设置后续更新标记。另一路状态切换也在 `1ba4a4..4c4`读取desired并调用 `5cd34e/5cd40c`。这些是后续计数器配置流程，不能把AP1400消费说成它们已运行，更不能说物理计数器、帧元数据或HDMI时间码已生效。（CP `1b95ca..ce、1b9972..99aa、1ba49e..4c8`；本轮无CP运行回执。）

### 为什么旧VDF命令、RTTI和Validate/Execute在此不适用

旧VDF二级分派 `1ab68c..6a2` 的internal3e槽 **1ab6e4→1ab878**是unknown/default诊断；本命令实际走上表phase0路径。不能为满足“VDF”目录名而强行绑定最近的同名类。（CP `1a8ef4..1a8f12、1ab878..892`；proof.tables保存这个反证槽。）

原件确有 `N3VDF21VdfSrvcCmdSetTimeCodeE`（字符串 **b3dc70**、typeinfo **b7ea3c**、vtable **b7ea24**），其ID/Activate/Execute为 **5f80e2/5f80f2/5f8158**。但ID函数明确是 **2001/0205**，回复1205，属于[既有36B Dataflow timecode设置](../svc-9059000e/README.md)，不是0400。旧VDF2001/1400又被 `1ad912..91e`映到internal287，最终 `1ac592→1ac64c→5c95b4`回的是 **1138**；它也不是这里的AP1400。以上两个容易误配的路径均独立在本次proof中重读，未声称0205类Validate适用于0400。（CP `5f80e2..8170、5c95d2`；proof.old_VDF_RTTI_exclusion。）

## 4. 成功回复、状态域和硬件依赖

原SYS完成器 **1adf2c**收到的r1来自internal完成消息+8；由 `1b944a`明确传0。它在 **1adf5c..7e**写type200d/command1400/length12/flags8001，**原样复制r1到+8**，经 `1aef1c`找internal3e的原关联source。这个链没有调用旧VDF的 `1adbd4/1adcda` 状态域OR函数。（CP `1ad6b8..bc、1aab2a、1ab192..19c、1adf36..84、1aef1c..7c`。）

| 字段 | LE值 | 精确字节 |
|---|---:|---|
| type | 200d | `0d20` |
| command | 1400 | `0014` |
| length | 000c | `0c00` |
| flags | 8001 | `0180` |
| status32 | 00000000 | `00000000` |
| **完整成功回复** | **12B** | **`0d2000140c00018000000000`** |

status归属SYS raw callback；不是“590000被归零”，而是原路径本来就传0。非0完成器能保留任意传入错误码，但本0400成功调用点没有已证业务失败码，故**不提供猜测的拒绝回复包**。不支持的请求应保留拒绝/委派或显式实现可证明的失败策略，不能借AP初始reply槽为零假装成功。（CP `1b944a、1adf7e`；AP `2df26b4..c4`。）

**A：原请求接受与1400确认不依赖live-view像素/传感器帧。B：可定义无头软件配置后端。U：真实计数器/录制/输出结果。** 接受链只保存mode、dirty与pending bit，立即发确认；后续计数器更新是另一条生命周期。软件后端可以接受mode0并保持counter/hardware pending，不必造帧，不代表原CP设备功能完整实现。（CP `1a8078..80b6、1b90de..9110、1b995a..99aa`；本轮只有AP请求serial **21807**。）

## 5. 最小诚实软件合同与拒绝集

脚本中的 `software_accept` 是可验证的纯软件合同，**未安装runtime**。限定profile=`headless_sys_timecode_mode`、destination92840747、完整10B捕获值和本次原请求的唯一lease/source。保存desired mode0、reserved0、`software_config_accepted=true`、`pending_counter_backend=true`、`physical_timecode_verified=false`；成功外形仅表达这层软件配置接受。不得声称已读取/递增timecode、启动录制、产生live-view帧或更新HDMI/GPE/OSD。（配置依据CP `1a808e、5ce2f8、1b9106`；确认依据 `1adf2c`；捕获serial **21807**。）

真实adapter必须先stage，再分配独立12B reply，metadata source92840747，投给**本次**request source；send接受后提交shadow/完成lease。分配或发送失败丢弃stage、释放自有reply、保留错误；不转移/重复释放原request所有权，已交付reply由AP `2de7320`自然释放。并发重入、重复pointer/generation或source错配不得完成。脚本的固定generation1只是有限证明域，不是可直接用于后续请求的全局计数器。（CP `1aef2c..7c`关联/分配/复制路径；AP `2de7318..20`；pure-contract实现及20项拒绝在proof.software_contract。）

脚本验证**20项拒绝且state不变**：10个请求byte分别改变、截短、追加、错误destination、缺source、source与lease不符、缺lease、错误profile、分配失败、发送失败、同generation重放。mode1虽在AP正常输入域内，本审计仍拒绝，因为未在本次捕获；拒绝集不是对原CP宽松parser的兼容声明。真正运输层并发锁、unique request pointer、free/send故障实测仍待adapter接入验收。（AP `2df268c..2698`；CP `1a807e`；serial **21807**；proof.software_contract。）

## 6. 运行事实和验收边界

前一0152在同tid346由独立peaking sequence发送，serial **21709**记software commit、**21712**记CONSUMED；之后才进入本TCMODE run。不能把先前0152的独立栈/显示域状态沿用到0400。（serial **21696–21714、21792–21809**；AP `2d95a18`对比 `2dcae3c`。）

本次冻结AP85r4 serial前缀 **5,426,282B**、SHA256 **c493986a68c7dc4d8f05e24167c9eee3808e99a2087a01d92f370921b7306d8e**（原文件当前64234个LF），脚本重建核此前缀，不吞入后续追加。该前缀没有`0d200014` raw marker；观察器有界/可能去重，零计数仅指未记录，不能证明全局无消息。没有1400被AP消费、Success日志、原sequence返回或后续队列继续的本轮验收。（serial **21807–21809、52731–52814**；proof.runtime。）

## 7. 之后所有同步请求：已闭合集合与未闭合集合一次列清

这里把“同一个run尾段”和“队列继续调度”分开，才能给出可复核的穷尽边界。本sequence完整范围是 **2dcadd0..2dcaf5c**，下一个函数从2dcaf60开始；proof保存其中全部14个直接call。Success分支只有日志和函数收尾，没有其他wrapper、创建worker或等待屏障。（AP `2dcae3c..80`；proof.sequence_calls。）

| 次序/范围 | 后续同步请求全集 | 精确回复/状态 |
|---|---|---|
| 当前0400 | **SYS0400/10B**，本次mode0 | **`0d2000140c00018000000000`**，软件配置接受后发送；AP `2df26bc` / CP `1adf5c..84` |
| 同一个run的成功尾段 | **空集，已闭合** | 无额外wire reply；Success→return，AP `2dcae44..80` |
| 同一个run的失败尾段 | 诊断、sleep、外部错误处理；外部错误观察者行为**未闭合** | 无已证后续正常业务reply；禁止造错误通知或跳过handler，AP `2dcaf54..5c、2ebf3b0..448` |
| 当前task完成后 | 完成观察者/析构；具体观察者列表**未闭合** | 无固定成功字节；`2bd7754→2bd1ecc`读取task+158/+160列表，后者有间接调用，AP `2bd1f04..200c` |
| SeqQueueCommon下一项及更后排队任务 | **命令、数量、输入和同步性均未闭合**；不是一个静态顺序函数尾段 | 无固定成功字节；AP `2bd7788→2bd763c`重新取队列节点，`2bd76f8`虚调用下一run；本轮没有queue heap内容（serial **21792–21809、52731–52814**） |
| TCUB计数器后端工作 | CP内部配置更新，不是本AP sequence新发的同步请求 | 不新增AP回复/伪造TC事件，CP `1b995a..99aa` |

因此**本审计不声称“整个SeqQueueCommon之后全部同步回复已齐”**，也没有证据把SYS0401/0402、旧VDF0205、启动0165/HDMI/0328等作为这个run的下一条。需要一次有界只读采集才能补齐动态集合：当前queue对象x19的 `+10`节点链、`+20`队列长度、`+88`活动task，逐个排队节点+10 task的vtable与 `+1bc`等原输入，以及当前task的completion observer列表 `+158/+160`；再对真实vtable的run逐项静态枚举。这里只提出最小观测位置，没有执行QEMU/内存采样。（AP `2bd7688..76f8、2bd7750..7788、2bd1f04..10`；捕获栈serial **21799**只给返回地址，未给queue对象/链表。）

## 8. 重建、来源与明确未证实项

在Mac项目根运行既有capstone venv：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/vdf0400/audit_vdf0400.py
```

退出0重建proof；固定AP SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`、CP `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`；核对52条关键指令、7个TBH槽、parser表、同名RTTI排除、14个sequence调用、AP85r4完整原栈/末次tid346收包快照与20项拒绝。可传 `AP:2df264c:124 CP:1adf2c:64`只输出反汇编，不重写proof。Thumb长区间可能含literal/TBB数据；决定性映射均另读表、关键指令另断言。（脚本CHECKS/TABLES及proof对应字段。）

明确未证实：原CP/计数器完整动态运行、mode0/1原UI名称、物理timecode和帧元数据、实际1400消费和sequence自然完成、动态队列/observer全部后继请求、底层OSAL取消/全局队列关联完整规则、adapter并发和分配/发送失败实测、菜单像素/按键/待机/实机验收。以上不是用“回复字节可构造”补齐的功能。（AP `2de7300、2bd76f8、2bd1f6c..2008`；CP `1b995a..99aa`；serial **52731–52814**。）

本轮2026-11-02联网核对了[Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)的`Cs`/`disasm`与`CsInsn`字段用法；它仅说明工具方法，不提供Sony私有协议语义。有效Sony协议结论均由本文VA和冻结serial独立重建；静态proof与纯软件合同通过不等于guest、菜单或实机通过。
